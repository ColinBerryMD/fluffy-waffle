from datetime import datetime
from flask import Flask, render_template, request, url_for, flash, redirect, Blueprint, abort, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, or_, and_
from sqlalchemy import desc
from twilio.request_validator import RequestValidator

from .models import Message, WebUser, SMSAccount
from .extensions import db, v_client, twilio_config, sql_error
from .phonenumber import cleanphone
from .auth import login_required, current_user

message = Blueprint('message', __name__,url_prefix='/message')

@message.route('/')
def list():
    try:
        messages = Message.query.all()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    return render_template('message_list.html', messages=messages)

@message.route('/send', methods=('GET','POST'))
def send():
    if request.method == 'POST':
        SentTo   = cleanphone(request.form['SentTo'  ])
        Body = request.form['Body']

        if not SentTo:
            flash('Valid SMS Number is Required!','error')
            return render_template('send_message.html')

        if not Body:
            flash('Message content is required!','error')
            return render_template('send_message.html')

        # post the message via twilio
        try:
            sms = v_client.messages.create(
                 body=Body,
                 messaging_service_sid=twilio_config.sms_sid,
                 to=SentTo)
        except:
            return redirect(url_for('errors.twilio_server'))
    
# even undeliverable messages go out with an initial status of 'Sent' 
# once SSE works we will need to use Status Call Back to know what really happened       
#        if sms.status == 'accepted':
#            flash('That phone number is not working.','info')
#            return render_template('send_message.html')
#        elif not sms.status == 'Sent':
#            print ('SMS failure with status: '+ sms.status )
#            return redirect(url_for('errors.twilio_server'))

        # insert into database
        message = Message(SentFrom = twilio_config.twilio_phone,
                          SentTo = SentTo, 
                          SentAt = datetime.now(), 
                          Body = Body)
        try:
            db.session.add(message)
            db.session.commit()
        except sql_error as e:
            return redirect(url_for('errors.mysql_server', error = e)) 

        return redirect(url_for('message.list'))

    return render_template('send_message.html')

@message.route('/recieve', methods=['POST'])
def recieve():

    # make sure this is a valid twilio text message
    validator = RequestValidator(twilio_config.auth_token)
    if not validator.validate(request.url, request.form, request.headers.get('X-Twilio-Signature')):
        abort(401)

    # get the parts we care about
    SentFrom = request.form.get('From')
    Body     = request.form.get('Body')
    SentTo   = twilio_config.twilio_phone


    message = Message(SentFrom = SentFrom, SentTo = SentTo, SentAt = datetime.now(), Body = Body)
    try:
        db.session.add(message)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    print('SMS recieved at '+ message.SentAt +'.')
    return("<Response/>")

@login_required
@message.route('/account', methods=('GET','POST'))
def account():
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        user_name = request.form.get('user_name')
        account_name = request.form.get('account_name')
        comment = request.form.get('comment')
        number = cleanphone(request.form.get('number'))
        sid = request.form.get('sid')

        if not user_name or not account_name or not number or not sid:
            flash('Need complete information to continue.','error')
            return render_template('account.html')

        try:
            owner = WebUser.query.filter(WebUser.User == user_name).first()
                           
        except sql_error as e:   
            return redirect(url_for(errors.mysql_server, error = e))    
        
        if not owner or not owner.is_sms:
            flash('That user is not allowed.','error')
            return render_template('account.html')

        existing_account=False  #for testing
#        try:
#           existing_account = SMSAccount.query.filter(or_(SMSAccount.name  == account_name, 
#                                                         SMSAccount.number== number,
#                                                         SMSAccount.sid   == sid )).first()
#                           
#        except sql_error as e:   
#            return redirect(url_for(errors.mysql_server, error = e))

        # if this returns an account we are creating a duplicate
        if existing_account : 
            flash('Conflict with existing account','error')
            return render_template('account.html')

        new_account = SMSAccount (owner_id = owner.id,
                                  name = account_name, 
                                  comment = comment,
                                  number = number,
                                  sid = sid )

        # add the new account to the database
        try:
            db.session.add(new_account)
            db.session.commit()
            new = SMSAccount.query.filter(SMSAccount.name == account_name).first()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        # make this our active account
        session['current_account_id'] = new.id
        session['account_name'] = new.name
        
        # announce success
        flash(account_name + ' created.','info')
        return redirect(url_for('main.index'))        

    # Handle GET requests
    return render_template('account.html')

# Veiw SMS Account details
@login_required
@message.route('/<int:account_id>/account_profile')
def account_profile(account_id):
    account = SMSAccount.query.get(account_id)
    owner = WebUser.query.get(account.owner_id)
    users = None # SQL Join from WebUser to User_Account_Link
    return render_template("account_profile.html", account=account, owner=owner, users=users)


@login_required
@message.route('/select_account', methods=('GET', 'POST'))
def select_account():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        current_account_id = request.form['selection']
        session['current_account_id'] = current_account_id
        account_selected = SMSaccount.query.get_or_404(current_account_id)
        session['account_name'] = account_selected.name

        return redirect(url_for('main.index'))

    try: # get the list of current accounts
         # need to modify this to only accounts for this user by filter
        accounts = SMSAccount.query.all()
    except (MySQLdb.Error, MySQLdb.Warning) as e:
        print(e)
        return redirect(url_for(errors.mysql_server, error = e))

    return render_template("current_account.html", accounts=accounts)

@message.post('/delete_account')
@login_required
def delete_account():
    # restrict access
    current_account = SMSaccount.query.get_or_404(session['current_account_id'])
    if not current_user.is_admin and not current_user.id == current_account.owner_id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    sms_account_id = request.form['selection']
    try:
        account_to_delete = SMSaccount.query.get(sms_account_id)
        db.session.delete(account_to_delete)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    # We will need to unlink users with account access here

    flash(account_to_delete.name +'('+account_to_delete.number+') '+' deleted.','info')
    return redirect(url_for('main.index'))

@message.post('/account_add_user')
@login_required
def account_add_user():
    # restrict access
    current_account = SMSaccount.query.get_or_404(session['current_account_id'])
    if not current_user.is_admin and not current_user.id == current_account.owner_id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))
    
    # get user; check for empties; avoid duplicates
    user_name = request.form['user_name']
    if not user_name:
            flash('Need a user name to continue.','error')
            return render_template('account_add_user.html')
    try:
        user_to_add = WebUser.query.filter(WebUser.User == user_name).first()
        link_exists = User_Account_Link.query.filter(
                         and_(\
                            User_Account_Link.user_id     == user_to_add.id, 
                            User_Account_Link.account_id  == current_account.id
                            )
                         ).first()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))
    
    if link_exists:
        flash('That user is already on the account.','info')
        return redirect(url_for('main.index'))

    # create and add the link
    link_to_add = User_Account_Link(user_id = user_to_add.id,account_id = current_account.id )
    try:
        db.session.delete(link_to_add)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))
        
    # announce success
    flash(user_to_add.name +' added to account.','info')
    return redirect(url_for('main.index'))

# here the owner of an SMS account can remove a user from that account
@message.post('/account_delete_user')
@login_required
def account_delete_user():
    # restrict access
    current_account = SMSaccount.query.get_or_404(session['current_account_id'])
    if not current_user.is_admin and not current_user.id == current_account.owner_id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    # get user; check for empties
    user_name = request.form['user_name']
    if not user_name:
            flash('Need a user name to continue.','error')
            return render_template('account_add_user.html')
    try:
        user_to_delete = WebUser.query.filter(WebUser.User == user_name).first()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    # attempt to delete owner can't work
    if user_to_delete.id == current_account.owner_id:
        flash('You cannot unlink the owner from an account','error')
        return redirect(url_for('main.index'))

    # find and remove the link
    try:
        link_to_delete = User_Account_Link.query.filter(
                         and_(\
                            User_Account_Link.user_id     == user_to_delete.id, 
                            User_Account_Link.account_id  == current_account.id
                            )
                         ).first()

        db.session.delete(link_to_delete)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    # announce success
    flash(user_to_delete.name +' deleted from account.','info')
    return redirect(url_for('main.index'))
