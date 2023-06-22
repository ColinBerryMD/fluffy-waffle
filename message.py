#import os
from datetime import datetime
from flask import Flask, render_template, request, url_for, flash, redirect, Blueprint, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import desc
from twilio.request_validator import RequestValidator

from .models import Message
from .extensions import db, v_client, twilio_config, sql_error
from .phonenumber import cleanphone

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
