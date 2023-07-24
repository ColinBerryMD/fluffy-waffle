from datetime import datetime
import json
from flask_sse import sse

#from sqlalchemy import desc
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from models import MessageSchema, Message, WebUser, SMSAccount, SMSGroup, SMSClient,\
                        Client_Group_Link
from extensions import db, v_client, twilio_config, sql_error, login_required, flask_response,\
                            current_user, render_template, request, url_for, flash,\
                            redirect, Blueprint, abort, session, func, or_, and_

from phonenumber import cleanphone
from mountain_time import mountain_time

message = Blueprint('message', __name__,url_prefix='/message', template_folder='templates')

       
# list all messages
@message.route('/')
def list():
    try:
        group_id = session['group_id']
    except KeyError:
        group_id = None

    try:
        messages = db.session.query(
                            Message,SMSClient
                            ).join(
                            SMSClient, Message.Client == SMSClient.id
                            ).all()
        if group_id:
            group = db.session.query(
                            SMSClient
                            ).join(
                            Client_Group_Link, SMSClient.id == Client_Group_Link.client_id
                            ).join(
                            SMSGroup, Client_Group_Link.group_id == SMSGroup.id
                            ).filter(
                            SMSGroup.id == session['group_id']
                            ).all()
        else:
            group = None

    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    return render_template('message/list.html', messages = messages, group = group )

# identical to list; but creates a selection
@message.route('/selection')
def selection():
    try:
        messages = Message.query.all()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    return render_template('message/list.html', messages=messages)

# send an sms message
@message.post('/<int:client_id>/send')
def send(client_id):
    sms_client = SMSClient.query.get_or_404(client_id)

    Body = request.form['Body']
    if not Body:
        flash('Message content is required!','error')
        return redirect( url_for('message.list'))

    account = SMSAccount.query.filter(SMSAccount.sid == session['account_id'] ).first()
    if not account:
        flash('Active account is required.','error')
        return redirect( url_for('message.list'))

    # post the message via twilio

    try:
        sms = v_client.messages.create(
             body = Body,
             messaging_service_sid = account.sid,
             to = sms_client.phone
             )
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
    message = Message(SentFrom = account.number,
                      SentTo   = sms_client.phone, 
                      SentAt   = mountain_time( datetime.now()), 
                      Body     = Body,
                      Outgoing = True,
                      Completed= False,
                      Confirmed= False,
                      Account  = account.id,
                      Client   = client_id 
                      )
    
    try:
        db.session.add(message)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 
    

    # publish SSE to message list
    # I need to insert client name in this as I create the json via dump
    message_schema = MessageSchema()
    message_json = message_schema.dump(message)
    sse.publish(message_json, type='sms_message')

    

    return flask_response(status=204)

# recieve a Twilio SMS message via webhook
@message.route('/recieve', methods=['POST'])
def recieve():

    # make sure this is a valid twilio text message
    validator = RequestValidator(twilio_config.auth_token)
    if not validator.validate(request.url, request.form, request.headers.get('X-Twilio-Signature')):
        abort(401)

    # get the parts we care about
    SentFrom = request.form.get('from')
    Body     = request.form.get('body')
    SentTo   = request.form.get('to')
    message_sid = request.form.get('sid')

    try:
        account = SMSAccount.query.filter(SMSAccount.sid == message_sid ).first().id
                           
    except sql_error as e:   
        return redirect(url_for(errors.mysql_server, error = e))

    # no account found. Don't know how this can happen
    if not account:
        return redirect(url_for('errors.twilio_server'))

    # is this from a registered client?
    try:
        sms_client = SMSClient.query.filter(SMSClient.phone == SentFrom).first()
                           
    except sql_error as e:   
        return redirect(url_for(errors.mysql_server, error = e))    
        
    if not sms_client: # reply with a request to sign up
        response = MessagingResponse()
        s = "Looks like you have yet to sign up for our text messaging service."
        s+= "Please re-send your message after signing up."
        response.message(s)
        return str(response)

    # or maybe they are blocked
    if sms_client.blocked: # reply with a request to go away
        response = MessagingResponse()
        s = "Looks like we cannot process your message."
        s+= "Please contact us by another method."
        response.message(s)
        return str(response)


    # ok. this is a valid message
    message = Message(
        SentFrom  = SentFrom,
        SentTo    = SentTo, 
        SentAt    = mountain_time( datetime.now() ), 
        Body      = Body,
        Outgoing  = False,
        Completed = False,
        Confirmed = False,
        Account   = account,
        Client    = sms_client.id
        )

    try: # add the message to the database
        db.session.add(message)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    # publish SSE to message list
    message_schema = MessageSchema()
    message_json = message_schema.dump(message)
    sse.publish(message_json, type='sms_message')

    #print('SMS recieved at '+ message.SentAt +'.')
    return("<Response/>")
