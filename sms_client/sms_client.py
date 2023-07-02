import os
from datetime import datetime
from flask import Flask, Blueprint, render_template, request, url_for, flash, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, or_

from .phonenumber import cleanphone

from .extensions import v_client, twilio_config, db, environ, sql_error
from .models import SMSClient
from .auth import login_required, current_user

sms_client = Blueprint('sms_client', __name__, url_prefix='/client', template_folder='templates/sms_client')

@sms_client.route('/welcome')
def welcome():
    return render_template('welcome.html')

@sms_client.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        translate = False
        if request.form.get('translate'):
            translate = True
        
        firstname = request.form['firstname']
        lastname  = request.form['lastname']
        dob_str   = request.form['dob']
        email     = request.form['email']
        phone     = cleanphone(request.form['phone'])
        translate = translate
        blocked   = False

        session['firstname'] = firstname 
        session['lastname']  = lastname
        session['dob']       = dob_str
        session['email']     = email   
        session['phone']     = phone   
        session['translate'] = translate 
        session['blocked']   = blocked
                          
        # check for empty fields
        if not firstname or not lastname or not email or not phone:
            flash('One or more required fields is empty.')
            return render_template('create.html')

        # check fo valid date string
        if not (bool(datetime.strptime(dob_str, '%m/%d/%Y'))):
            flash('Date of birth is misformatted.','error')
            return render_template('create.html')

        existing_sms_client=False  #for testing
        #try:
        #   existing_sms_client = SMSClient.query.filter(or_(SMSClient.email==email, SMSClient.phone==phone)).first()
        #except sql_error as e:   
        #    return redirect(url_for(errors.mysql_server, error = e))
        
        # if this returns a client, then the email or phone already exists in database
        if existing_sms_client : # if a client is found, we want to redirect back to signup page so they can try again
            if existing_sms_client.blocked: # but what if they are blocked and this wasn't a mistake
                flash('This client account cannot sent SMS messages at this time.', 'info')
                return redirect(url_for('main.index'))
            else:
                flash('Client with this email or phone already exists','error')
                return render_template('create.html')
        
        # send verification code from twilio to proposed sms number
        try:
            verification = v_client.verify.v2.services( twilio_config.otp_sid ).verifications \
                            .create(to= phone, channel='sms')
        except: # wrong numbers throw an untracable exception
                return redirect(url_for('errors.twilio_server'))
                
        if not verification == 'pending':
            return redirect(url_for('errors.twilio_server'))

        return redirect(url_for('sms_client.terms'))
    
    return render_template('create.html')

# two factor authentication at signup will prove them not to be a spam bot
# and give documentation that they read our terms and conditions
@sms_client.route('/terms', methods= ('GET', 'POST'))
def terms():
    if request.method == 'POST':
        OTP = request.form['one_time_password']

        datetime_obj = datetime.strptime(session['dob'],'%m/%d/%Y')

        new_sms_client = SMSClient( firstname = session['firstname'], 
                                    lastname = session['lastname'],
                                    dob = datetime_obj,
                                    email = session['email'],
                                    phone = session['phone'],
                                    translate = session['translate'],
                                    blocked = session['blocked'])

        # check OTP with Twilio and flash on error
        try: 
            verification_check = v_client.verify.v2.services( twilio_config.otp_sid ).verification_checks \
                                  .create(to= new_sms_client.phone, code=OTP)
    
        except: # delayed entry, tried twice, and never sent -- all those errors throw the same untracable exception
            return redirect(url_for('errors.twilio_server'))
                
        if verification == 'pending': # probably wrong code entered
            flash('Are you sure that was the correct code?','error')
            return redirect(url_for('sms_client.terms'))

        if not verification_check.status == 'approved':  # I don't think this can happen
            flash('One time code verification failed.','error')
            return redirect(url_for('sms_client.terms'))

        try:            # add to database on success
            db.session.add(new_sms_client)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        # announce success
        flash('Passcode accepted.','info')
        flash('You can close the page any time.','info')
        flash('Send us that text message now.','info')
        return redirect(url_for('sms_client.welcome'))

    return render_template('terms.html')

# as in the other blueprints, list lists all the clients
@sms_client.route('/list')
@login_required
def list():

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        clients = SMSClient.query.all()
    except sql_error as e: 
        return redirect(url_for(errors.mysql_server, error = e))

    return render_template('list.html', clients=clients)

# and select narrows the list to a client or a select list
@sms_client.route('/select', methods=('GET', 'POST'))
def select():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname  = request.form['lastname']
        dob_str   = request.form['dob']
    
    try: ###### we need to create a query here
        clients = SMSClient.query.all()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    # if only one
        return render_template('profile.html', client=client)

    # else we have a list
        return render_template('list.html', clients=clients)
    
    return render_template('select.html')

# since they have no login, the clients can't make corrections themselves
# but any use with a login can do it for them
# an edit session always unblockes a blocked client
@sms_client.route('/<int:sms_client_id>/edit/', methods=('GET', 'POST'))
@login_required
def edit(sms_client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        client_to_edit = SMSClient.query.get_or_404(sms_client_id)
    except sql_error as e: 
        return redirect(url_for(errors.mysql_server, error = e))

    if client_to_edit.dob:
        dob_str = client_to_edit.dob.strftime('%m/%d/%Y')
    else:
        dob_str = None

    if request.method == 'POST':
        firstname   = request.form.get('firstname')
        lastname    = request.form.get('lastname')
        dob_str     = request.form.get('dob_str')
        email       = request.form.get('email')
        phone       = cleanphone(request.form.get('phone'))
        
        if request.form.get('translate'):
            translate = True
        else:
            translate = False

        # check for empty fields
        if not firstname or not lastname or not email or not phone:
            flash('One or more required fields is empty.','error')
            return render_template('edit.html', client=client_to_edit, dob_str=dob_str)

        # check fo valid date string
        if not (bool(datetime.strptime(dob_str, '%m/%d/%Y'))) or not dob_str:
            flash('Date of birth is misformatted or blank.','error')
            return render_template('edit.html', client=client_to_edit, dob_str=dob_str)
        else:
            dob_obj = datetime.strptime(dob_str,'%m/%d/%Y')

        conflicting_sms_client=False # for testing
        #try:
        #   conflicting_sms_client = SMSClient.query.filter(or_(SMSClient.email==email, SMSClient.phone==phone)).first()
        #except sql_error as e:
        #   return redirect(url_for(errors.mysql_server, error = e))
        
        if conflicting_sms_client : # if a user is found, we want to redirect back to signup page so user can try again
            flash('New email address or phone number already exists', 'error')
            return render_template('edit.html', client=client_to_edit, dob_str = dob_str)
        
        # ok. We passed all the tests, now lets update the DB with our new info
        client_to_edit.firstname = firstname
        client_to_edit.lastname = lastname
        client_to_edit.dob = dob_obj
        client_to_edit.email = email
        client_to_edit.phone = phone
        client_to_edit.translate = translate
        client_to_edit.blocked = False  # doesn't make sense to update their info and leave them blocked

        try:
            db.session.add(client_to_edit)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        flash('SMS client updated.','info')
        return redirect(url_for('main.index'))

    return render_template('edit.html', client=client_to_edit, dob_str= dob_str)

# We might also need a list of numbers to block from jump street
# without an invitation to sign up
# but this is for folks who violate the terms of use
# probably nice people, but we can't SMS with them anymore
@sms_client.post('/<int:client_id>/block/')
@login_required
def block(client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    client_to_block = SMSClient.query.get_or_404(client_id)
    client_to_block.blocked = True
    try:
        db.session.add( sms_client_to_block)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    flash('Client '+client_to_block.firstname +' '+client_to_block.lastname+' blocked.','info')
    return redirect(url_for('main.index'))

# more of a clean up function
# once deleted they can sign up again
@sms_client.post('/<int:client_id>/delete/')
@login_required
def delete(client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        client_to_delete = SMSClient.query.get_or_404(client_id)
        db.session.delete(client_to_delete)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    flash('Client '+client_to_delete.firstname +' '+client_to_delete.lastname+' deleted.','info')
    return redirect(url_for('main.index'))
