# account.py
# routes for creating and maintaning Twilio messaging accounts

from datetime import datetime
from flask import Flask, render_template, request, url_for, flash, redirect, Blueprint, abort, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, or_, and_
from sqlalchemy import desc
from twilio.request_validator import RequestValidator

from cbmd.models import WebUser, SMSAccount
from cbmd.extensions import db, v_client, twilio_config, sql_error
from cbmd.phonenumber import cleanphone
from cbmd.auth.auth import login_required, current_user

account = Blueprint('account', __name__, url_prefix='/account', template_folder='templates')


# process starts with admin creating a Twilio SMS account and assigning ownership to a user
@login_required
@account.route('/create', methods=('GET','POST'))
def create():
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        owner_user_name = request.form.get('owner_user_name')
        account_name = request.form.get('account_name')
        comment = request.form.get('comment')
        number = cleanphone(request.form.get('number'))
        sid = request.form.get('sid')

        if not user_name or not account_name or not number or not sid:
            flash('Need complete information to continue.','error')
            return render_template('account/create.html')

        try:
            owner = WebUser.query.filter(WebUser.User == user_name).first()
                           
        except sql_error as e:   
            return redirect(url_for(errors.mysql_server, error = e))    
        
        if not owner or not owner.is_sms:
            flash('That user is not allowed.','error')
            return render_template('account/create.html')

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
            return render_template('account/create.html')

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
    return render_template('account/create.html')

# Veiw SMS Account details
@login_required
@account.route('/<int:account_id>/profile')
def profile(account_id):

    try: 
        account = SMSAccount.query.get(account_id)
        query = db.session.query(WebUser.id, WebUser.first, Webuser.last,\
                                 User_Account_Link.user_id, User_Account_Link.account_id)
        query = query.join(Webuser).join(User_Account_Link)
        users = query.filter(User_Account_Link.account_id == account_id).all()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))        

    return render_template("account/profile.html", account=account, users=users)

# list all accounts
@login_required
@account.route('/list')
def list():
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    try:
        accounts = SMSAccount.query.all()
    except (MySQLdb.Error, MySQLdb.Warning) as e:
        print(e)
        return redirect(url_for(errors.mysql_server, error = e))

    return render_template('account/list.html', accounts=accounts )


@login_required
@account.route('/select', methods=('GET', 'POST'))
def select():
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

    return render_template("account/select.html", accounts=accounts)

# having created an account or otherwise made it active
# we can add users to the active account
@login_required
@account.route('/add_user', methods=('GET', 'POST'))
def add_user():
    # we need an active account
    if not current_account.owner_id:
        flash('Current SMS Account not set.','error')
        return redirect(url_for('main.index'))

    # restrict access
    current_account = SMSaccount.query.get_or_404(session['current_account_id'])
    if not current_user.is_admin and not current_user.id == current_account.owner_id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # get user; check for empties; avoid duplicates
        user_name = request.form['user_name']
        if not user_name:
                flash('Need a user name to continue.','error')
                return render_template('account/add_user.html')
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
    
    # GET request
    return render_template("account/add_user.html")
    
# here the owner of an SMS account can remove a user from that account
@login_required
@account.post('/delete_user')
def delete_user():
    # restrict access
    current_account = SMSaccount.query.get_or_404(session['current_account_id'])
    if not current_user.is_admin and not current_user.id == current_account.owner_id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    # get user; check for empties
    user_name = request.form['user_name']
    if not user_name:
            flash('Need a user name to continue.','error')
            return render_template('account/add_user.html')
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

# and finally, the admin or owner of an account can delete the account
@login_required
@account.post('/delete_account')
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