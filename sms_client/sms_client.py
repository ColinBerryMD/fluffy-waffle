from datetime import datetime
import json
from flask_sse import sse

from models import SMSClient, Client_Group_Link
from extensions import v_client, twilio_config, db, sql_error, sql_text, login_required, current_user, flask_response,\
                       session, func, or_, and_, not_, Blueprint, render_template, request, url_for, flash, redirect

from utils.phonenumber import cleanphone
from utils.dict_from import dict_from
from utils.cleandob import cleandob

sms_client = Blueprint('sms_client', __name__, url_prefix='/sms_client', template_folder='templates')


@sms_client.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        translate = False
        if request.form.get('translate'):
            translate = True
        
        firstname = request.form['firstname']
        lastname  = request.form['lastname']
        dob   = request.form['dob']
        email     = request.form['email']
        phone     = cleanphone(request.form['phone'])
        translate = translate
        blocked   = False

                   
        # check for empty fields
        if not firstname or not lastname or not email or not phone:
            flash('One or more required fields is empty.','error')
            return render_template('sms_client/create.html')

        # check fo valid date string
        dob = cleandob(dob)
        if not dob:
            flash('Date of birth is misformatted.','error')
            return render_template('sms_client/create.html')

        #existing_sms_client=False  #for testing
        try:
           existing_sms_client = SMSClient.query.filter(or_(SMSClient.email==email, SMSClient.phone==phone)).first()
        except sql_error as e: 
            locale="checking for duplicate clients"  
            return redirect(url_for(errors.mysql_server, error = e,locale=locale))
        
        # if this returns a client, then the email or phone already exists in database
        if existing_sms_client : # if a client is found, we want to redirect back to signup page so they can try again
            if existing_sms_client.blocked: # but what if they are blocked and this wasn't a mistake
                flash('This client account cannot sent SMS messages at this time.', 'info')
                return redirect(url_for('main.index'))
            else:
                flash('Client with this email or phone already exists','error')
                return render_template('sms_client/create.html')
        
        # send verification code from twilio to proposed sms number
        try:
            verification = v_client.verify.v2.services( twilio_config.otp_sid ).verifications \
                            .create(to= phone, channel='sms')
        except: # wrong numbers throw an untracable exception
            e= "Error sending verification code"
            locale="sending verification to new client in create()"
            return redirect(url_for('errors.twilio_server',error=e,locale=locale))
                
        session['firstname'] = firstname 
        session['lastname']  = lastname
        session['dob']       = dob
        session['email']     = email   
        session['phone']     = phone   
        session['translate'] = translate 
        session['blocked']   = blocked

        return redirect(url_for('sms_client.terms'))
    
    return render_template('sms_client/create.html')

# create fake client for testing
@sms_client.route('/fake', methods=('GET', 'POST'))
def fake():
    if request.method == 'POST':
        translate = False
        if request.form.get('translate'):
            translate = True
        
        new_sms_client = SMSClient( 
            firstname = request.form['firstname'],
            lastname  = request.form['lastname'],
            dob   = cleandob(request.form['dob']),
            email     = request.form['email'],
            phone     = cleanphone(request.form['phone']),
            translate = translate,
            blocked   = False )

        
        try:            # add to database on success
            db.session.add(new_sms_client)
            db.session.commit()
        except sql_error as e:
            locale="adding new fake client to database" 
            return redirect(url_for('errors.mysql_server', error = e,locale=locale))
        
        flash('Fake client added','info')       
        return redirect(url_for('main.index'))
    
    return render_template('sms_client/create.html')


# two factor authentication at signup will prove them not to be a spam bot
# and give documentation that they read our terms and conditions
@sms_client.route('/terms', methods= ('GET', 'POST'))
def terms():
    if request.method == 'POST':
        OTP = request.form['one_time_password']

        new_sms_client = SMSClient( firstname = session['firstname'], 
                                    lastname = session['lastname'],
                                    dob = session['dob'],
                                    email = session['email'],
                                    phone = session['phone'],
                                    translate = session['translate'],
                                    blocked = session['blocked'])

        # check OTP with Twilio and flash on error
        try: 
            verification_check = v_client.verify.v2.services( twilio_config.otp_sid ).verification_checks\
                                  .create(to= new_sms_client.phone, code=OTP)
    
        except: # delayed entry, tried twice, and never sent -- all those errors throw the same untracable exception
            flash('One time code verification failed.','error')
            return redirect(url_for('sms_client.terms'))

        if not verification_check.status == 'approved':  # I don't think this can happen
            flash('One time code verification not approved.','error')
            return redirect(url_for('sms_client.terms'))

        try:            # add to database on success
            db.session.add(new_sms_client)
            db.session.commit()
        except sql_error as e:
            locale="adding new client to database" 
            return redirect(url_for('errors.mysql_server', error = e,locale=locale))

        # announce success
        flash('Passcode accepted.','info')
        flash('You can close the page any time.','info')
        flash('Send us that text message now.','info')
        return redirect(url_for('main.client'))

    return render_template('sms_client/terms.html')

# as in the other blueprints, list lists all the clients
@sms_client.post('/list')
@login_required
def list():

    client_id = request.form.get('selection')
    if client_id:
        return redirect( url_for( 'sms_client.profile', client_id = client_id ))

    clients = request.form.get('clients')
    return render_template('sms_client/list.html', clients = clients )

# publish sse of a single client profile back to message dashboard
@sms_client.post('/sse_select')
@login_required
def sse_select():
    try:
        client_id = request.form['client_id']
    except:
        flash('No selection passed','error')
        return flask_response(status=204)
    
    client = SMSClient.query.filter(SMSClient.id == client_id).one()

    msg_dict = dict_from(client)
    message_json = json.dumps(msg_dict)
    sse.publish(message_json, type='client_profile')
    return flask_response(status=204)

@login_required
@sms_client.route('/<int:client_id>/profile')
def profile(client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    client = SMSClient.query.filter(SMSClient.id == client_id).one()

    return render_template('sms_client/profile.html', client = client )

# and select narrows the list to a client or a select list
@sms_client.route('/select', methods=('GET', 'POST'))
def select():
    if request.method == 'POST':
        if request.form.get('select_all') == 'on':
            clients = SMSClient.query.all()
        else:
            firstname = request.form['firstname']
            lastname  = request.form['lastname']
            dob   = request.form['dob']
            if dob:
                dob = cleandob(dob)
                if not dob:
                    flash('Date of birth is misformatted.','error')
                    return render_template('sms_client/select.html')
                     
         # clients where firstname sounds like firstname and lastname sounds like lastname -- or -- dob == dob 
            if firstname and lastname:
                name_query = "SOUNDEX(SMSClient.firstname)=SOUNDEX('"+ firstname +"') AND SOUNDEX(SMSClient.lastname)=SOUNDEX('"+ lastname +"')"
                if dob:
                    name_query += " OR SMSClient.dob ='"+dob+"'"
            elif dob:
                name_query = "SMSClient.dob ='"+dob+"'"
            else:
                flash('Not enough information for search.','error')
                return render_template('sms_client/select.html')
            
            try: 
                clients = SMSClient.query.filter(sql_text(name_query)).all()
                                                        
            except sql_error as e:
                locale="text() search for client"
                return redirect(url_for('errors.mysql_server', error = e,locale=locale))  

        if clients:
            if len(clients) == 1:     # if only one
                return render_template('sms_client/profile.html', client=clients[0])
            elif len(clients) >1:                     # else we have a list
                return render_template('sms_client/list.html', clients=clients)
            else:
                flash('No clients found.','info')
                return render_template('sms_client/select.html')
    
    return render_template('sms_client/select.html')

# search is like select, but works with javascript and sse dynamically
# from the message dashboard
@sms_client.post('/search')
def search():        
    firstname = request.form['firstname']
    lastname  = request.form['lastname']
    dob   = request.form['dob']
    if dob:
        dob = cleandob(dob)
        if not dob:
            flash('Date of birth is misformatted.','error')
            return redirect(url_for('message.list'))

    # clients where firstname sounds like firstname and lastname sounds like lastname -- or -- dob == dob 
    if firstname and lastname:
        name_query = "SOUNDEX(SMSClient.firstname)=SOUNDEX('"+ firstname +"') AND SOUNDEX(SMSClient.lastname)=SOUNDEX('"+ lastname +"')"
        if dob:
            name_query += " OR SMSClient.dob ='"+dob+"'"
    elif dob:
        name_query = "SMSClient.dob ='"+dob+"'"
    else:
        flash('Not enough information for search.','error')
        return redirect(url_for('message.list'))    

    try: 
        clients = SMSClient.query.filter(sql_text(name_query)).all()

    except sql_error as e:
        locale="text() search for client"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))  

    if len(clients) == 1:     # if only one
        msg_dict = dict_from(clients[0])
        message_json = json.dumps(msg_dict)
        sse.publish(message_json, type='client_profile')
        return flask_response(status=204)
    elif len(clients) >1:    # a list of client objects
        msg_dict = []
        for c in clients: 
            msg_dict.append(dict_from(c))
        message_json = json.dumps(msg_dict) 
        sse.publish(message_json, type='client_list')
        return flask_response(status=204)         
    else:                     # nothing found 
        flash('No clients found.','info')
        return flask_response(status=204)
                

# since they have no login, the clients can't make corrections themselves
# but any use with a login can do it for them
# an edit session always unblockes a blocked client
@login_required
@sms_client.route('/<int:sms_client_id>/edit/', methods=('GET', 'POST'))
def edit(sms_client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        client_to_edit = SMSClient.query.filter(SMSClient.id == sms_client_id).one()
    except sql_error as e: 
        locale="getting client to edit"
        return redirect(url_for(errors.mysql_server, error = e,locale=locale))

    if request.method == 'POST':
        firstname   = request.form.get('firstname')
        lastname    = request.form.get('lastname')
        dob         = request.form.get('dob')
        email       = request.form.get('email')
        phone       = cleanphone(request.form.get('phone'))
        
        if request.form.get('translate'):
            translate = True
        else:
            translate = False

        # check for empty fields
        if not firstname or not lastname or not email or not phone:
            flash('One or more required fields is empty.','error')
            return render_template('sms_client/edit.html', client=client_to_edit)

        # check fo valid date string
        dob = cleandob(dob)
        if not dob:
            flash('Date of birth is misformatted.','error')
            return render_template('sms_client/edit.html', client=client_to_edit)

        #conflicting_sms_client=False # for testing
        try:
           conflicting_sms_client = SMSClient.query.filter(and_(
                                                                or_(
                                                                    SMSClient.email==email,
                                                                    SMSClient.phone==phone
                                                                ), not_(
                                                                    SMSClient.id == sms_client_id
                                                                ))).first()
        except sql_error as e:
           return redirect(url_for(errors.mysql_server, error = e))
        
        if conflicting_sms_client : # if a user is found, we want to redirect back to signup page so user can try again
            flash('New email address or phone number already exists', 'error')
            return render_template('sms_client/edit.html', client=client_to_edit)
        
        # ok. We passed all the tests, now lets update the DB with our new info
        client_to_edit.firstname = firstname
        client_to_edit.lastname = lastname
        client_to_edit.dob = dob
        client_to_edit.email = email
        client_to_edit.phone = phone
        client_to_edit.translate = translate
        client_to_edit.blocked = False  # doesn't make sense to update their info and leave them blocked

        try:
            db.session.add(client_to_edit)
            db.session.commit()
        except sql_error as e: 
            locale="updating client after edit"
            return redirect(url_for('errors.mysql_server', error = e,locale=locale))

        flash('SMS client updated.','info')
        return redirect(url_for('main.index'))

    return render_template('sms_client/edit.html', client=client_to_edit)

# We might also need a list of numbers to block from jump street
# without an invitation to sign up
# but this is for folks who violate the terms of use
# probably nice people, but we can't SMS with them anymore
@login_required
@sms_client.route('/<int:client_id>/block/')
def block(client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    client_to_block = SMSClient.query.filter(SMSClient.id == client_id).one()
    client_to_block.blocked = True
    try:
        db.session.add( client_to_block)
        db.session.commit()
    except sql_error as e:
        locale="blocking a client"
        return redirect(url_for(errors.mysql_server, error = e,locale=locale))

    flash('Client '+client_to_block.firstname +' '+client_to_block.lastname+' blocked.','info')
    return redirect(url_for('main.index'))

# more of a clean up function
# once deleted they can sign up again
@login_required
@sms_client.route('/<int:client_id>/delete/')
def delete(client_id):

    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))
    
    try:
        db.session.query(Client_Group_Link).filter(
                         Client_Group_Link.client_id == client_id
                        ).delete()
        db.session.commit()
    except sql_error as e:
        locale="deleting client links"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))

    try:
        client_to_delete = SMSClient.query.filter(SMSClient.id == client_id).one()
        db.session.delete(client_to_delete)
        db.session.commit()
    except sql_error as e:
        locale="deleting a client"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))

    flash('Client '+client_to_delete.firstname +' '+client_to_delete.lastname+' deleted.','info')
    return redirect(url_for('main.index'))
