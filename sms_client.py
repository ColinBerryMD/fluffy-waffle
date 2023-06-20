import os
from datetime import datetime
from flask import Flask, Blueprint, render_template, request, url_for, flash, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, or_

from .phonenumber import cleanphone

from .extensions import v_client, twilio_config, db, environ
from .models import SMSClient
from .auth import login_required, current_user

sms_client = Blueprint('sms_client', __name__, url_prefix='/client')


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
            return render_template('sms_client.html')

        # check fo valid date string
        if not (bool(datetime.strptime(dob_str, '%m/%d/%Y'))):
            flash('Date of birth is misformatted.','error')
            return render_template('sms_client.html')

        existing_sms_client=False  #for testing
        #existing_sms_client = SMSClient.query.filter(or_(SMSClient.email==email, SMSClient.phone==phone)).first()
        # if this returns a user, then the email or phone already exists in database
        if existing_sms_client : # if a user is found, we want to redirect back to signup page so user can try again
            flash('Client with this email or phone already exists','error')
            return render_template('sms_client.html')
        
        # send verification code from twilio to proposed sms number
        verification = v_client.verify.v2.services( twilio_config.otp_sid ).verifications \
                        .create(to= phone, channel='sms')

        return redirect(url_for('sms_client.terms'))
    
    return render_template('sms_client.html')

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
        verification_check = v_client.verify.v2.services( twilio_config.otp_sid ).verification_checks \
                             .create(to= new_sms_client.phone, code=OTP)
    
        if not verification_check.status == 'approved':
            flash('One time code verification failed.','error')
            return redirect(url_for('sms_client.terms'))

        else:
            # add to database on success
            db.session.add(new_sms_client)
            db.session.commit()
            flash('Passcode accepted.','info')
            return redirect(url_for('main.index'))

    return render_template('terms.html')

@sms_client.route('/list')
@login_required
def list():

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    clients = SMSClient.query.all()
    return render_template('client_index.html', clients=clients)

@sms_client.route('/<int:sms_client_id>/edit/', methods=('GET', 'POST'))
@login_required
def edit(sms_client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    client_to_edit = SMSClient.query.get_or_404(sms_client_id)
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
            return render_template('edit-client.html', client=client_to_edit, dob_str=dob_str)

        # check fo valid date string
        if not (bool(datetime.strptime(dob_str, '%m/%d/%Y'))) or not dob_str:
            flash('Date of birth is misformatted or blank.','error')
            return render_template('edit-client.html', client=client_to_edit, dob_str=dob_str)
        else:
            dob_obj = datetime.strptime(dob_str,'%m/%d/%Y')

        existing_sms_client=False # for testing
        #existing_sms_client = SMSClient.query.filter(or_(SMSClient.email==email, SMSClient.phone==phone)).first()
        if existing_sms_client : # if a user is found, we want to redirect back to signup page so user can try again
            flash('New email address or phone number already exists', 'error')
            return render_template('edit-client.html', client=client_to_edit, dob_str = dob_str)
        
        
        client_to_edit.firstname = firstname
        client_to_edit.lastname = lastname
        client_to_edit.dob = dob_obj
        client_to_edit.email = email
        client_to_edit.phone = phone
        client_to_edit.translate = translate
        client_to_edit.blocked = False

        db.session.add(client_to_edit)
        db.session.commit()

        flash('SMS client updated.','info')
        return redirect(url_for('main.index'))

    return render_template('edit-client.html', client=client_to_edit, dob_str= dob_str)

@sms_client.post('/<int:sms_client_id>/block/')
@login_required
def block(sms_client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    sms_client_to_block = SMSClient.query.get_or_404(sms_client_id)
    sms_client_to_block.blocked = True
    db.session.add( sms_client_to_block)
    db.session.commit()
    flash('Client '+sms_client_to_block.firstname +' '+sms_client_to_block.lastname+' blocked.','info')
    return redirect(url_for('main.index'))

@sms_client.post('/<int:sms_client_id>/delete/')
@login_required
def delete(sms_client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    sms_client_to_delete = SMSClient.query.get_or_404(sms_client_id)
    db.session.delete(sms_client_to_delete)
    db.session.commit()
    flash('Client '+sms_client_to_delete.firstname +' '+sms_client_to_delete.lastname+' deleted.','info')
    return redirect(url_for('main.index'))
