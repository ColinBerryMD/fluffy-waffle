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


from utils.phonenumber import cleanphone
from utils.dict_from import dict_from
from utils.google_translate import to_spanish, is_english

message = Blueprint('message', __name__, url_prefix='/message', template_folder='templates')

# reflect user activity in our database on any message related http request
@message.before_request
def activity():
    try:
        user_id = current_user.id
    except:
        user_id = None

    if user_id:
        user = WebUser.query.filter(WebUser.id == user_id).one()
        user.last_active = datetime.now()
        try:
            db.session.add(user)
            db.session.commit()
        except sql_error as e:
            locale = "updating activity"
            print("Error "+locale)
            abort(401)

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


# list all messages aka the messaging dashboard
@message.route('/')
@login_required
def list():
    try:
        group_id = session['group_id']
    except KeyError:
        group_id = None

    try:
        messages = db.session.query(Message).filter(not_(Message.archived == True)).all()
        if group_id:
            group = SMSGroup.query.filter(SMSGroup.id == group_id).one()
        else:
            group = None

    except sql_error as e:
        locale = "getting messages for list"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 

    return render_template('message/list.html', messages = messages, group = group )

# send an sms message
@message.post('/<int:client_id>/send')
@login_required
def send(client_id):
    sms_client = SMSClient.query.filter(SMSClient.id == client_id).one()

    Body = request.form['Body']
    if not Body:
        flash('Message content is required!','error')
        return redirect( url_for('message.list'))

    # translate to spanish if requested
    if sms_client.translate and is_english(Body):
        body_to_send = to_spanish(Body)
        Body = body_to_send +' ('+Body+') '
    else:
        body_to_send = Body

    account = SMSAccount.query.filter(SMSAccount.id == session['account_id'] ).one()
    if not account:
        flash('Active account is required.','error')
        return redirect( url_for('message.list'))

    # post the message via twilio

    try:
        sms = v_client.messages.create(
             body = body_to_send,
             messaging_service_sid = account.sid,
             status_callback= twilio_config.status,
             to = sms_client.phone
             )
        sms_sid = sms.sid
        sms_status = None
    except:
        sms_status = 'failed'
        sms_sid = None
        
    # insert into database
    message = Message(SentFrom = account.number,
                      SentTo   = sms_client.phone, 
                      SentAt   = datetime.now(tzlocal()).isoformat(), 
                      Body     = Body,
                      Outgoing = True,
                      archived  = False,
                      sms_sid  = sms_sid,
                      sms_status = sms_status,
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
@login_required
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

        # translate to spanish if requested
        if sms_client.translate and is_english(Body):
            body_to_send = to_spanish(Body)
            this_body = body_to_send +' ('+Body+') '
        else:
            this_body = Body
            body_to_send = Body
        try:
            sms = v_client.messages.create(
                 body = body_to_send,
                 messaging_service_sid = account.sid,
                 status_callback= twilio_config.status,
                 to = sms_client.phone
                 )
            sms_sid = sms.sid
            sms_status = None
        except:
            sms_status = 'failed'
            sms_sid = None
            
        # insert into database
        message = Message(SentFrom = account.number,
                          SentTo   = sms_client.phone, 
                          SentAt   = datetime.now(tzlocal()).isoformat(), 
                          Body     = this_body,
                          Outgoing = True,
                          archived  = False,
                          sms_sid  = sms_sid,
                          sms_status = sms_status,
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

# archive an sms message
@message.route('/<sms_id>/archive')
@login_required
def archive(sms_id):
    try:
        message = Message.query.filter(Message.id == sms_id).one()
        message.archived = True
        db.session.add(message)
        db.session.commit()
    except sql_error as e:
        locale="archiving sms message"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    return flask_response(status=204)

    # publish SSE to message list
    
    status_dict ={}
    status_dict['sms_sid']   = sms_sid
    status_dict['sms_status']= sms_status

    #status_dict = dict_from(message_to_update)
    status_json = json.dumps(status_dict)
    sse.publish(status_json, type='sms_status')

    return flask_response(status=204)
