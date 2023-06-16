from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session
from flask_login import login_user, login_required, logout_user, current_user
from flask_principal import Identity, AnonymousIdentity, identity_changed, \
RoleNeed, UserNeed, Permission, identity_loaded

# database models
from .models import WebUser

# my own modules
from .phonenumber import cleanphone
from .cleanpassword import cleanpassword

#app factory products
from .app import db, bcrypt, permit
from .extensions import admin_permission

auth = Blueprint('auth', __name__)


@auth.route('/login', methods= ( 'GET','POST'))
def login():
    if request.method == 'POST':
    # login code goes here 
        User = request.form.get('User')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = WebUser.query.filter_by(User=User).first()

        # check if the user actually exists
        # take the user-supplied password, hash it, and compare it to the hashed password in the database
        if not user or not bcrypt.check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page

        # if the above check passes, then we know the user has the right credentials
        # I think this is where the permissions go
        login_user(user, remember=remember)

        # Tell Flask-Principal the identity changed
        identity_changed.send(current_app._get_current_object(),identity=Identity(user.id))

        return redirect(url_for('main.profile'))

    # GET request
    return render_template('login.html')


@auth.route('/lookup', methods = ('GET','POST'))
def user_name_lookup():
    if request.method == 'POST':
        user_name = request.form.get('user_name')

        # check for empties
        if not user_name:
            flash('Need a user name to continue.','error')
            return render_template('claim_username_lookup.html')

        # exclude too short usernames
        if len(user_name) < 5:
            flash('Your user name needs to be at least five characters.','error')
            return render_template('claim_username_lookup.html')
        
        # if this returns a user, then we can proceed with claim
        found = WebUser.query.filter_by(User=user_name).first() 
        if found: # if a user is found, we want to redirect to claim route
            return redirect(url_for('auth.claim',user_id=found.id))
        else:
            flash('That username is not allowed. ','error')
            return render_template('claim_username_lookup.html')

    # Handle GET requests
    return render_template('claim_username_lookup.html')

@auth.route('/create', methods=('GET','POST'))
@admin_permission.require()
def create():
    if request.method == 'POST':
        user_name = request.form.get('user_name')

        # check for empties
        if not user_name:
            flash('Need a user name to continue.','error')
            return render_template('create_username.html')

        # exclude too short usernames
        if len(user_name) < 5:
            flash('Your user name needs to be at least five characters.','error')
            return render_template('create_username.html')
        
        # if this returns a user, then they already exist in database
        current_user = WebUser.query.filter_by(User=user_name).first() 
        if current_user: # if a user is found, we want to redirect to login
            flash('That user already exists. ','error')
            return render_template('create_username.html')

        # create a new user name and id -- we will add the rest of the data later
        new_user = WebUser(User = user_name)

        # add the new user to the database
        db.session.add(new_user)
        db.session.commit()
        flash('User '+ user_name + ' created.','info')
        return redirect(url_for('main.index'))        

    # Handle GET requests
    return render_template('create_username.html')

@auth.route('/<int:user_id>/claim', methods=('GET','POST'))
def claim(user_id):
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
        
        sms = cleanphone(sms)
        if voice:
            voice = cleanphone(voice)
        else:
            voice = sms
        
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
            return render_template('claim.html',user_id=user_id)

        # test password quality
        if cleanpassword(password,repeat_password):
            pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        else:
            return render_template('claim.html',user_id=user_id)

        # need a unique email
        existing_user = WebUser.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
        if existing_user : 
            flash('That email address is taken.', 'error')
            return render_template('claim.html',user_id=user_id)

        user.first = first
        user.last = last
        user.email = email
        user.password = pw_hash
        user.sms = sms
        user.voice = voice
        user.is_sms = is_sms
        user.translate = translate
        
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('auth.login'))

    # handle GET request
    return render_template('claim.html',user=user)

@auth.route('/list')
#@admin_permission.require()
def list():
    webusers = WebUser.query.all()
    return render_template('user_list.html', webusers=webusers)

@auth.route('/logout')
@login_required
def logout():
    logout_user()

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())

    return redirect(url_for('main.index'))


@auth.route('/<int:user_id>/delete/', methods=(['POST']))
@admin_permission.require()
def delete(user_id):
    u = WebUser.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    flash('User '+ u.User + ' deleted.','info')
    return redirect(url_for('main.index'))
