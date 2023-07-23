from datetime import datetime
import json
from flask_sse import sse

#from sqlalchemy import desc
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from cbmd.models import MessageSchema, Message, WebUser, SMSAccount, SMSGroup, SMSClient,\
                        Client_Group_Link
from cbmd.extensions import db, v_client, twilio_config, sql_error, login_required,\
                            current_user, render_template, request, url_for, flash,\
                            redirect, Blueprint, abort, session, func, or_, and_

from cbmd.phonenumber import cleanphone
# from cbmd.auth.auth import 

message = Blueprint('message', __name__,url_prefix='/message', template_folder='templates')


# the whole point of the project is this messaging dashboard
# it will have tabs for each active chatting client
# a display of the client in focus's messages
# and a display of our current client group (ie the days patient list)
@ message.route('/dashboard')
@ login_required
def dashboard():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    return render_template('message/dashboard.html') 

# fake an sms message to test db and styling
@message.route('/fake', methods=('GET','POST'))
def fake():
    if request.method == 'POST':
        SentFrom   = cleanphone(request.form['SentFrom'])
        SentTo   = cleanphone(request.form['SentTo'  ])
        SentAt = SentAt = mountain_time(datetime.now())
        Body   = request.form['Body'  ]
        
        if request.form.get('Outgoing') == 'on':
            Outgoing   = True
        else:
            Outgoing = False

        Account = request.form['Account']
        Client = request.form['Client']

        # insert into database
        message = Message(SentFrom = SentFrom,
                          SentTo = SentTo, 
                          SentAt = SentAt, 
                          Body = Body,
                          Outgoing = Outgoing,
                          Account = Account,
                          Client = Client )

        try:
            db.session.add(message)
            db.session.commit()
        except sql_error as e:
            return redirect(url_for('errors.mysql_server', error = e)) 

        # I need to insert client name in this as I create the json via dump
        sms_client = SMSClient.query.get_or_404(message.Client)

        message_schema = MessageSchema()

        message_json = message_schema.dump(message)

        sse.publish(message_json, type='sms_message')

        flash("SMS Message Faked.","info")
        return render_template('message/fake.html')

    return render_template('message/fake.html')

       
# list all messages
@message.route('/list')
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

@message.route('/send_sms', methods=('GET','POST'))
def send_sms():
    if request.method == 'POST':
        SentTo   = cleanphone(request.form['SentTo'  ])
        Body = request.form['Body']
        SentAt = mountain_time(datetime.now())
        

        message = Message(SentFrom = "+12343455678", 
                          SentTo = SentTo, 
                          SentAt = SentAt, 
                          Body = Body,
                          Outgoing = True)

        message_json = message_schema.dump(message)
        sse.publish(message_json, type='sms_message')

        return render_template('create.html')

    return render_template('create.html')

# send an sms message
@message.route('/send', methods=('GET','POST'))
def send():
    if request.method == 'POST':
        SentTo   = cleanphone(request.form['SentTo'  ])
        Body = request.form['Body']

        if not SentTo:
            flash('Valid SMS Number is Required!','error')
            return render_template('message/send_message.html')

        if not Body:
            flash('Message content is required!','error')
            return render_template('message/send_message.html')

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

        ####### publish SSE to message dashboard

        ####### return 200

        return redirect(url_for('message.list'))

    return render_template('message/send_message.html')

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
    message = Message(SentFrom = SentFrom, SentTo = SentTo, SentAt = datetime.now(), Body = Body)
    try: # add the message to the database
        db.session.add(message)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    ####### publish SSE to message dashboard

    print('SMS recieved at '+ message.SentAt +'.')
    return("<Response/>")
