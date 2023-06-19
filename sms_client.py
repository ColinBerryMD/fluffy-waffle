import os
from flask import Flask, Blueprint, render_template, request, url_for, flash, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

from .phonenumber import cleanphone

from .extensions import v_client, twilio_config, db, environ
from .models import SMSClient

sms_client = Blueprint('sms_client', __name__)

@sms_client.route('/sms_client_list')
def sms_client_list():
    clients = SMSClient.query.all()
    return render_template('index.html', clients=clients)

@sms_client.route('/create_sms_client', methods=('GET', 'POST'))
def create_sms_client():
    if request.method == 'POST':
        translate = False
        if request.form.get('translate'):
            translate = True
        
        firstname = request.form['firstname']
        lastname  = request.form['lastname']
        email     = request.form['email']
        phone     = cleanphone(request.form['phone'])
        translate = translate
        blocked   = False

        session['firstname'] = firstname 
        session['lastname']  = lastname
        session['email']     = email   
        session['phone']     = phone   
        session['translate'] = translate 
        session['blocked']   = blocked
                          
        # check for empty fields
        if not firstname or not lastname or not email or not phone:
            flash('One or more required fields is empty.')
            return render_template('sms_client.html')

        existing_sms_client = SMSClient.query.filter_by(email = email).first() # if this returns a user, then the email already exists in database
        if existing_sms_client : # if a user is found, we want to redirect back to signup page so user can try again
            flash('Email address already exists')
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

        new_sms_client = SMSClient( firstname = session['firstname'], 
                                    lastname = session['lastname'],
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

@sms_client.route('/<int:sms_client_id>/edit-sms_client/', methods=('GET', 'POST'))
def edit_sms_client(sms_client_id):
    current_sms_client = SMSClient.query.get_or_404(sms_client_id)

    if request.method == 'POST':
        firstname   = request.form.get('firstname')
        lastname    = request.form.get('lastname')
        email       = request.form.get('email')
        phone       = cleanphone(request.form.get('phone'))
        
        if request.form.get('translate'):
            translate = True
        else:
            translate = False

        # check for empty fields
        if not firstname or not lastname or not email or not phone:
            flash('One or more required fields is empty.','error')
            return render_template('edit.html', current_sms_client=current_sms_client)
        
        existing_sms_client = SMSClient.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
        if existing_sms_client : # if a user is found, we want to redirect back to signup page so user can try again
            flash('New email address already exists', 'error')
            return render_template('edit.html', current_sms_client=current_sms_client)
        
        current_sms_client.firstname = firstname
        current_sms_client.lastname = lastname
        current_sms_client.email = email
        current_sms_client.phone = phone
        current_sms_client.translate = translate
        current_sms_client.blocked = False

        db.session.add(current_sms_client)
        db.session.commit()

        return redirect(url_for('main.index'))

    return render_template('edit.html', current_sms_client=current_sms_client)

@sms_client.post('/<int:sms_client_id>/block/')
def sms_client_block(sms_client_id):
    current_sms_client = SMSClient.query.get_or_404(sms_client_id)
    current_sms_client.blocked = True
    db.session.add(current_sms_client)
    db.session.commit()
    flash('Client blocked','info')
    return redirect(url_for('main.index'))

@sms_client.post('/<int:sms_client_id>/delete/')
def sms_client_delete(sms_client_id):
    current_sms_client = SMSClient.query.get_or_404(current_sms_client_id)
    db.session.delete(current_sms_client)
    db.session.commit()
    flash('Client deleted.','info')
    return redirect(url_for('main.index'))
