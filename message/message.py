from datetime import datetime, timedelta
from dateutil.tz import tzlocal
import json
from flask_sse import sse

#from sqlalchemy import desc
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from models import Message, WebUser, SMSAccount, SMSGroup, SMSClient,\
                        Client_Group_Link
from extensions import db, v_client, twilio_config, sql_error, login_required, flask_response,\
                        current_user, render_template, request, url_for, flash, redirect, \
                        Blueprint, abort, session, func, or_, and_, ForeignKey, relationship, inspect


from phonenumber import cleanphone
from dict_from import dict_from


message = Blueprint('message', __name__,url_prefix='/message', template_folder='templates')

# a little jinja2 filter for the timestamp       
@message.app_template_filter()
def pretty_timestamp(iso_time): # actually a iso string -- not a timestamp (timestamps dont jasonify)
    iso_time = iso_time.replace('T',':')
    iso_time = iso_time.replace('-',':')
    t =  iso_time.split(':')

    try:
        msg_month = int(t[1])
        msg_dom = int(t[2])
        msg_date = t[1]+'/'+t[2]+'/'+t[0]
        msg_time = t[3]+':'+t[4]
    except:
        return iso_time  # give up - it isnt going to work

    today = datetime.now(tzlocal())
    t_dom = today.day
    t_month = today.month
    yesterday = today - timedelta(days = 1)
    y_dom = yesterday.day
    y_month = yesterday.month

    if t_dom == msg_dom and t_month == msg_month:
        stamp = msg_time
    elif y_dom == msg_dom and y_month == msg_month:
        stamp = "Yesterday at "+ msg_time
    else:
        stamp = msg_date

    return stamp

# list all messages
@message.route('/')
def list():
    try:
        group_id = session['group_id']
    except KeyError:
        group_id = None

    try:
        messages = db.session.query(Message).all()
        if group_id:
            group = SMSGroup.query.filter(SMSGroup.id == group_id).one()
        else:
            group = None

    except sql_error as e:
        locale = "getting messages for list"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 

    return render_template('message/list.html', messages = messages, group = group )

# create a fake sms message to populate our DB for testing
@message.route('/fake', methods= ( 'GET','POST'))
def fake():
    if request.method == 'POST':
        client_id = request.form['client_id']
        sms_client = SMSClient.query.filter(SMSClient.id == client_id).first()    
        if not sms_client:
            flash('Client not found.','error')
            return redirect( url_for('message.list'))   

        account = SMSAccount.query.filter(SMSAccount.id == session['account_id'] ).one()
        if not account:
            flash('Active account is required.','error')
            return redirect( url_for('message.list'))   

        Body = request.form['Body']
        if request.form.get('Outgoing') == 'on':
            Outgoing = True
            SentTo = sms_client.phone
            SentFrom = account.number
        else:
            Outgoing = False
            SentTo = account.number
            SentFrom = sms_client.phone


        # insert into database
        message = Message(SentFrom = SentFrom,
                          SentTo   = SentTo, 
                          SentAt   = datetime.now(tzlocal()).isoformat(), 
                          Body     = Body,
                          Outgoing = Outgoing,
                          Completed= False,
                          Confirmed= False,
                          Account  = account.id,
                          Client   = sms_client.id 
                          )
        
        try:
            db.session.add(message)
            db.session.commit()
        except sql_error as e:
            locale = "adding sent message to database"
            return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 
        
    #    # publish SSE to message list
    #    msg_dict = dict_from(message)
    #    msg_dict.update(dict_from(sms_client))
    #    message_json = json.dumps(msg_dict)
    #    sse.publish(message_json, type='sms_message') 

        flash('Message added', 'info') 

    return render_template('message/fake.html') 

# send an sms message
@message.post('/<int:client_id>/send')
def send(client_id):
    sms_client = SMSClient.query.filter(SMSClient.id == client_id).one()

    Body = request.form['Body']
    if not Body:
        flash('Message content is required!','error')
        return redirect( url_for('message.list'))

    account = SMSAccount.query.filter(SMSAccount.id == session['account_id'] ).one()
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
                      SentAt   = datetime.now(tzlocal()).isoformat(), 
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
        locale = "adding sent message to database"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 
    
    # publish SSE to message list
    msg_dict = dict_from(message)
    msg_dict.update(dict_from(sms_client))
    message_json = json.dumps(msg_dict)
    sse.publish(message_json, type='sms_message')

    return flask_response(status=204)

# send a group of sms messages
@message.route('/multiple_send', methods= ( 'GET','POST'))
def multiple_send():

    Body = request.form['MultiBody']
    if not Body:
        flash('Message content is required!','error')
        return redirect( url_for('message.list'))

    account = SMSAccount.query.filter(SMSAccount.id == session['account_id'] ).one()
    if not account:
        flash('Active account is required.','error')
        return redirect( url_for('message.list'))

    # post the messages via twilio
    
    selection = request.form.getlist('selected')

    for client_id in selection:
        sms_client = SMSClient.query.filter(SMSClient.id == client_id).one()
        try:
            sms = v_client.messages.create(
                 body = Body,
                 messaging_service_sid = account.sid,
                 to = sms_client.phone
                 )
        except:
            return redirect(url_for('errors.twilio_server'))    

        # insert into database
        message = Message(SentFrom = account.number,
                          SentTo   = sms_client.phone, 
                          SentAt   = datetime.now(tzlocal()).isoformat(), 
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
            locale = "adding sent message to database"
            return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 
            

        # publish SSE to message list
        msg_dict = dict_from(message)
        msg_dict.update(dict_from(sms_client))
        message_json = json.dumps(msg_dict)
        sse.publish(message_json, type='sms_message')

    
    return flask_response(status=204)

# receive a Twilio SMS message via webhook
@message.route('/receive', methods= ( 'GET','POST'))
def receive():

    # make sure this is a valid twilio text message
    validator = RequestValidator(twilio_config.auth_token)
    if not validator.validate(request.url, request.form, request.headers.get('X-Twilio-Signature')):
        abort(401)

    # get the parts we care about
    SentFrom = request.form['From']
    Body     = request.form['Body']
    SentTo   = request.form['To']
    message_sid = request.form['MessagingServiceSid']
    
    try:
        account = SMSAccount.query.filter(SMSAccount.sid == message_sid ).one().id
                           
    except sql_error as e: 
        locale = "getting account number from twilio sid"  
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    # no account found. Don't know how this can happen
    if not account:
        e = "No mysql error thrown, but no twillio account found"
        locale = "finding sms account"
        return redirect(url_for('errors.twilio_server',error=e,locale=locale))

    # is this from a registered client?
    try:
        sms_client = SMSClient.query.filter(SMSClient.phone == SentFrom).one()
                           
    except sql_error as e:  
        locale = "getting client info with phone. Do two clients have the same number?" 
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))    
        
    if not sms_client: # reply with a request to sign up
        ######### reply with a link in the request
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
        SentAt    = datetime.now(tzlocal()).isoformat(), 
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
        db.session.refresh(message)
    except sql_error as e:
        locale = "adding recieved message to database"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 

    
    # publish SSE to message list

    msg_dict = dict_from(message)
    msg_dict.update(dict_from(sms_client))
    message_json = json.dumps(msg_dict)

    sse.publish(message_json, type='sms_message')

    return("<Response/>")
