# auth.py
# authorize logins
# CB 6/23

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime

# database models
from cbmd.models import WebUser, OldPasswords

# my own modules
from cbmd.phonenumber import cleanphone
from .cleanpassword import cleanpassword

#app factory products
from cbmd.extensions import db, bcrypt, v_client, twilio_config, sql_error
from cbmd.app import password_lifetime, two_fa_lifetime

auth = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates')


# this whole blueprint culminates in a successful login
@auth.route('/login', methods= ( 'GET','POST'))
def login():
    if request.method == 'POST':
    # login code goes here 
        User = request.form.get('User')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        try:
            user = WebUser.query.filter_by(User=User).first()
        except sql_error as e:
            return redirect(url_for('errors.mysql_server', error = e)) 

        # check if the user actually exists
        # take the user-supplied password, hash it, and compare it to the hashed password in the database
        if not user or not bcrypt.check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return render_template('auth/login.html')  # if the user doesn't exist or password is wrong, reload the page

        # if the above check passes, then we know the user has the right credentials
        login_user(user, remember=remember)

        if user.password_expires < datetime.now():
            flash('Your password has expired.','info')
            return redirect(url_for('auth.change_password', user_id = user.id))

        if not user.two_fa_expires or user.two_fa_expires < datetime.now(): # time for new two factor

            try:
                verification = v_client.verify \
                            .v2 \
                            .services( twilio_config.otp_sid ) \
                            .verifications \
                            .create(to= user.sms, channel='sms')
            except:
                return redirect(url_for('errors.twilio_server'))

            flash('Sending a new one time pass code to '+ user.sms +'.','info')
            return redirect(url_for('auth.two_factor', user_id = user.id))

        # two factor is in date 
        #### need to set a default SMS account here
        
        return redirect(url_for('auth.profile',user_id=user.id ))

    # GET request
    return render_template('auth/login.html')

# set the stage by admin inviting a user and creating their username    
@auth.route('/create', methods=('GET','POST'))
@login_required
def create():
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        user_name = request.form.get('user_name')

        # check for empties
        if not user_name:
            flash('Need a user name to continue.','error')
            return render_template('auth/create.html')

        # exclude too short usernames
        if len(user_name) < 5:
            flash('Your user name needs to be at least five characters.','error')
            return render_template('auth/create.html')
        
        # if this returns a user, then they already exist in database
        try:
            current = WebUser.query.filter_by(User=user_name).first() 
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        if current: 
            flash('That user already exists. ','error')
            return render_template('auth/create.html')

        # create a new user name and id -- they will add the rest of their profile later
        new_user = WebUser(User = user_name)

        # add the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        flash('User '+ user_name + ' created.','info')
        return redirect(url_for('main.index'))        

    # Handle GET requests
    return render_template('auth/create.html')


# admin started the process by creating a username
# now our invited user looks up and claims the name; they will soon create a profile and log in
# this same form can also be used to veiw a user profile with a redirect from the html
@auth.route('/lookup', methods = ('GET','POST'))
def lookup():
    if request.method == 'POST':
        user_name = request.form.get('user_name')

        # check for empties
        if not user_name:
            flash('Need a user name to continue.','error')
            return render_template('auth/lookup.html')

        # exclude too short usernames
        if len(user_name) < 5:
            flash('Your user name needs to be at least five characters.','error')
            return render_template('auth/lookup.html')
        
        # if this returns a user, then we can proceed with claim
        try:
            found = WebUser.query.filter_by(User=user_name).first() 
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        if found: # if a user is found, we want to redirect to register route to create their profile
            return redirect(url_for('auth.register',user_id=found.id))
        else:
            flash('That username is not in our database. ','error')
            return render_template('auth/lookup.html')

    # Handle GET requests
    return render_template('auth/lookup.html')


# our invited user has found their username. Here they create a profile
@auth.route('/<int:user_id>/register', methods=('GET','POST'))
def register(user_id):
    user = WebUser.query.get_or_404(user_id)

    # handle PUT request
    if request.method == 'POST':
        password = request.form.get('password')
        repeat_password = request.form.get('repeat_password')
        first = request.form.get('first')
        last = request.form.get('last')
        email = request.form.get('email')
        sms = request.form.get('sms')
        voice = request.form.get('voice')
        
        # correct normal phone strings to international +18885551234 format
        sms = cleanphone(sms)
        if voice:
            voice = cleanphone(voice)
        else:
            voice = sms
        
        # why this is "on" rather than true.....
        if request.form.get('is_sms') == 'on':
            is_sms = True
        else:
            is_sms = False

        if request.form.get('translate') == 'on':
            translate = True
        else:
            translate = False

        # check for empties
        if not first or not last or not email or not sms:
            flash('Invalid empty fields.','error')
            return render_template('auth/register.html',user=user)

        # test password quality
        # os.environ.FORGIVE_BAD_PASSWORDS=True avoids the tedium of rigorous passwords in development
        if cleanpassword(password,repeat_password):
            pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        else:
            return render_template('auth/register.html',user=user)

        # demand a unique email, not certian why at this point
        try:
            existing_user = WebUser.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        if existing_user : 
            flash('That email address is in use already.', 'error')
            return render_template('auth/register.html',user=user)

        user.first = first
        user.last = last
        user.email = email
        user.password = pw_hash
        user.password_expires = datetime.now() + password_lifetime
        user.sms = sms
        user.voice = voice
        user.is_sms = is_sms
        user.translate = translate
        
        try:
            db.session.add(user)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))

        # store old password to prevent re-use
        try:
            old_password = OldPasswords(oldie = user.password, created = datetime.now())
            db.session.add(old_password)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))
        
        # time to log in
        return redirect(url_for('auth.login'))

    # handle GET request
    return render_template('auth/register.html',user=user)

# at their first login and then periodically, our new user will need to do a 2 factor auth    
@auth.route('/<int:user_id>/two_factor', methods=('GET','POST'))
@login_required
def two_factor(user_id):
    user = WebUser.query.get_or_404(user_id)

    # handle PUT request
    if request.method == 'POST':
        one_time_pass_code = request.form.get('one_time_pass_code')

        # check OTP via twilio
        try:
            verification_check = v_client.verify \
                                .v2 \
                                .services( twilio_config.otp_sid ) \
                                .verification_checks \
                                .create(to= user.sms, code=one_time_pass_code)
        except:
            return redirect(url_for('errors.twilio_server'))

        if not verification_check.status == 'approved':
            flash('Invalid pass code.','info')
            return render_template('two_factor.html',user=user)

        # update expiration
        user.two_fa_expires = datetime.now() + two_fa_lifetime
        
        db.session.add(user)
        db.session.commit()

        flash('Pass Code Accepted.','info')
        return redirect(url_for('auth.profile'))

    # handle GET request
    return render_template('auth/two_factor.html',user=user)

# the rest of these routes are not for our initial user experience
# change an expired or undesired password
@auth.route('/<int:user_id>/change_password', methods=('GET','POST'))
@login_required
def change_password(user_id):
    user = WebUser.query.get_or_404(user_id)

    # handle PUT request
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password     = request.form.get('new_password')
        verify_password  = request.form.get('verify_password')
        
        # check for empties
        if not current_password or not new_password or not verify_password:
            flash('Invalid empty fields.','error')
            return render_template('auth/change_password.html',user=user)

        # test old password
        if not bcrypt.check_password_hash(user.password, current_password):
            flash('Current Password does not match.','error')
            return render_template('auth/change_password.html',user=user)

        # test password quality
        if cleanpassword(new_password,verify_password):
            pw_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
        else:
            return render_template('auth/change_password.html',user=user)

        user.password = pw_hash
        user.password_expires = datetime.now() + password_lifetime
        
        try:
            db.session.add(user)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))
            
        try:
            old_password = OldPasswords(oldie = user.password, created = datetime.now())
            db.session.add(old_password)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))
        
        return redirect(url_for('auth.profile',user_id=user.id))

    # handle GET request
    return render_template('auth/change_password.html',user=user)

# veiw one user account
@auth.route('/<int:user_id>/profile')
def profile(user_id):
    user = WebUser.query.get_or_404(user_id) 
    return render_template('auth/profile.html',user=user)

@login_required
@auth.route('/<int:user_id>/edit/', methods=('GET', 'POST'))
def edit(user_id):
    user = WebUser.query.get_or_404(user_id)

    if not ( user_id == current_user.id or current_user.is_admin ):
        flash('You cannot edit that account.', 'error')
        return redirect(url_for('main.index'))

    current_email = user.email 

    if request.method == 'POST':
        first = request.form['first']
        last = request.form['last']
        email = request.form['email']
        sms = cleanphone(request.form['sms'])
        voice = cleanphone(request.form['voice'])
        if not voice:
            voice = sms
        
        if request.form.get('is_sms') == 'on':
            is_sms = True
        else:
            is_sms = False

        if request.form.get('translate') == 'on':
            translate = True
        else:
            translate = False
    
        # check for empty fields
        if not first or not last or not email or not sms:
            flash('One or more required fields is empty.','error')
            return render_template('auth/edit.html', user=user)
        
        if not email == current_email: # new email address
            existing_user = WebUser.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
            if existing_user : # if a user is found, we want to redirect back to signup page so user can try again
                flash('New email address already exists', 'error')
                return render_template('auth/edit.html', user=user)
        
        user.first = first
        user.last = last
        user.email = email
        user.sms = sms
        user.voice = voice
        user._is_sms = is_sms
        user.translate = translate
        
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.index'))

    # handle GET request    
    return render_template('auth/edit.html', user=user)



# list all users
@login_required
@auth.route('/list')
def list():
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    try:
        users = WebUser.query.all()
    except (MySQLdb.Error, MySQLdb.Warning) as e:
        print(e)
        return redirect(url_for(errors.mysql_server, error = e))

    return render_template('auth/list.html', users=users)

# logout
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# delete a user account
@auth.route('/<int:user_id>/delete/', methods=(['POST']))
@login_required
def delete(user_id):
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    u = WebUser.query.get_or_404(user_id)
    try:
        db.session.delete(u)
        db.session.commit()
    except (MySQLdb.Error, MySQLdb.Warning) as e:
        print(e)
        return redirect(url_for(errors.mysql_server, error = e))

    flash('User '+ u.User + ' deleted.','info')
    return redirect(url_for('main.index'))