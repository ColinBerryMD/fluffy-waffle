from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_required, current_user

from .models import WebUser
from .app import db
from .phonenumber import cleanphone
from .cleanpassword import cleanpassword

main = Blueprint('main', __name__)
@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile', methods=(['GET']))
@login_required
def profile():
    return render_template('profile.html', name=current_user.first)

@main.route('/<int:user_id>/edit/', methods=('GET', 'POST'))
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
            return render_template('edit.html', user=user)
        
        if not email == current_email: # new email address
            existing_user = WebUser.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
            if existing_user : # if a user is found, we want to redirect back to signup page so user can try again
                flash('New email address already exists', 'error')
                return render_template('edit.html', user=user)
        
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
    return render_template('edit.html', user=user)
