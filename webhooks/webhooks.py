from datetime import datetime, timedelta
from dateutil.tz import tzlocal
import json
from flask_sse import sse

#from sqlalchemy import desc
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from models import Message, WebUser, SMSAccount, SMSGroup, SMSClient,\
                        Client_Group_Link
from extensions import environ, db, v_client, twilio_config, sql_error, login_required, flask_response,\
                        current_user, render_template, request, url_for, flash, redirect, \
                        Blueprint, abort, session, func, or_, and_, not_, ForeignKey, relationship, inspect


from phonenumber import cleanphone
from dict_from import dict_from

# we needed a separate blueprint to not conflict on before request
webhooks = Blueprint('webhooks', __name__, url_prefix='/webhooks')

# receive an outbound Twilio SMS message's status via webhook
@webhooks.post('/status')
def status():

    # make sure this is a valid twilio text message
    validator = RequestValidator(twilio_config.auth_token)
    if not validator.validate(request.url, request.form, request.headers.get('X-Twilio-Signature')):
        abort(401)

    # get the parts we care about
    sms_sid = request.form['SmsSid']
    sms_status     = request.form['SmsStatus']

    # update the database
    try: 
        message_to_update = Message.query.filter(Message.sms_sid == sms_sid).one()
    except sql_error as e:  
            locale="finding message for status update" 
            return redirect(url_for('errors.mysql_server', error = e,locale=locale))

    message_to_update.sms_status = sms_status
    message_to_update.sms_sid = sms_sid
    try:
        db.session.add(message_to_update)
        db.session.commit()
    except sql_error as e:
        locale="updating sms status"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    # publish SSE to message list
    
    status_dict ={}
    status_dict['sms_sid']   = sms_sid
    status_dict['sms_status']= sms_status

    #status_dict = dict_from(message_to_update)
    status_json = json.dumps(status_dict)
    sse.publish(status_json, type='sms_status')

    return flask_response(status=204)


# receive a Twilio SMS message via webhook
@webhooks.route('/receive', methods= ( 'GET','POST'))
def receive():

    # make sure this is a valid twilio text message
    validator = RequestValidator(twilio_config.auth_token)
    if not validator.validate(request.url, request.form, request.headers.get('X-Twilio-Signature')):
        abort(401)

    # get the parts we care about
    SentFrom = request.form['From']
    Body     = request.form['Body']
    SentTo   = request.form['To']
    message_service_id = request.form['MessagingServiceSid']
    
    try:
        account = SMSAccount.query.filter(SMSAccount.sid == message_service_id ).one()
                           
    except sql_error as e: 
        locale = "getting account number from twilio sid"  
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    # no account found. Don't know how this can happen
    if not account:
        e = "No mysql error thrown, but no twillio account found"
        locale = "finding sms account"
        return redirect(url_for('errors.twilio_server',error=e,locale=locale))#
    # is this from a registered client?
    try:
        sms_client = SMSClient.query.filter(SMSClient.phone == SentFrom).one()
                           
    except sql_error as e:  
        locale = "getting client info with phone. Do two clients have the same number?" 
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))    
        
   # if not sms_client or sms_client.blocked: # reply with a request to sign up
#        if not sms_client: # reply with a request to sign up
#            # reply with a link in the request
#            s = "Looks like you have yet to sign up for our text messaging service."
#            s+= "Please re-send your message after signing up through this link."
#            s+= environ['MY_CLIENT_DASHBOARD']
#        else: # or maybe they are blocked
#            s = "Looks like we cannot process your message."
#            s+= "Please contact us by another method."
#        try:
#            sms = v_client.messages.create(
#                         body = s,
#                         messaging_service_sid = account.sid,
#                         to = SentFrom
#                         )
#        except:
#            locale = "sending rejection"
#            return redirect(url_for('errors.twilio_server',locale=locale))
#        return("<Response/>")

    # ok. this is a valid message
    message = Message(
        SentFrom  = SentFrom,
        SentTo    = SentTo, 
        SentAt    = datetime.now(tzlocal()).isoformat(), 
        Body      = Body,
        Outgoing  = False,
        archived  = False,
        Account   = account.id,
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

    # unless we get very busy we need a heads up to the account owner that a message is waiting
    # we will only send one such message between logins
    #message_owner = WebUser.query.filter(WebUser.id == account.owner_id )
#    if message_owner.last_notification < message_owner.last_active: # they have been active since their last notification
#        if message_owner.last_active < datetime.now() - timedelta( minutes= environ['ACTIVITY_LIMIT_MINUTES']): # owner is probably offline
#            
#            # send a notification 
#            try:
#                sms = v_client.messages.create(
#                         body = "You have a new message at "+environ['MY_MESSAGE_DASHBOARD'],
#                         messaging_service_sid = account.sid,
#                         to = message_owner.sms
#                         )
#            except:
#                locale = "sending notification"
#                return redirect(url_for('errors.twilio_server',locale=locale))
#            
#            # update notification flag
#            message_owner.last_notification = datetime.now()
#            try:
#                db.session.add(message_owner)
#                db.session.commit()
#            except sql_error as e:
#                locale = "updating owner notification"
#                return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 

    # update dashboard if open
    sse.publish(message_json, type='sms_message')

    return("<Response/>")
