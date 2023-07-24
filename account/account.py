# account.py
# routes for creating and maintaning Twilio messaging accounts

from models import WebUser, SMSAccount, User_Account_Link
from extensions import db, v_client, twilio_config, sql_error, render_template, request,\
                            url_for, flash, redirect, Blueprint, abort, session, func, or_, and_,\
                            login_required, current_user

from phonenumber import cleanphone

account = Blueprint('account', __name__, url_prefix='/account', template_folder='templates')


# process starts with admin creating a Twilio SMS account and assigning ownership to a user
@login_required
@account.route('/create', methods=('GET','POST'))
def create():
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        owner_user_name = request.form.get('owner_user_name')
        account_name = request.form.get('account_name')
        number = cleanphone(request.form.get('number'))
        sid = request.form.get('sid')

        if not owner_user_name or not account_name or not number or not sid:
            flash('Need complete information to continue.','error')
            return render_template('account/create.html')

        try:
            owner = WebUser.query.filter(WebUser.User == owner_user_name).first()
                           
        except sql_error as e:   
            return redirect(url_for('errors.mysql_server', error = e))    
        
        if not owner or not owner.is_sms:
            flash('That user is not allowed.','error')
            return render_template('account/create.html')

        existing_account=False  #for testing
#        try:
#           existing_account = SMSAccount.query.filter(or_(SMSAccount.name  == account_name, 
#                                                         SMSAccount.number== number,
#                                                         SMSAccount.sid   == sid )).first()
#                           
#        except sql_error as e:   
#            return redirect(url_for('errors.mysql_server', error = e))

        # if this returns an account we are creating a duplicate
        if existing_account : 
            flash('Conflict with existing account','error')
            return render_template('account/create.html')

        new_account = SMSAccount (name = account_name, 
                                  number = number,
                                  sid = sid )

        # add the new account to the database
        try:
            db.session.add(new_account)
            db.session.commit()
            new = SMSAccount.query.filter(SMSAccount.name == account_name).first()
        except sql_error as e: 
            return redirect(url_for('errors.mysql_server', error = e))

        # add the owner as first user account to the database
        owner_link = User_Account_Link( user_id = owner.id, is_owner = True, account_id = new.id )
        try:
            db.session.add(owner_link)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for('errors.mysql_server', error = e))

        # make this our active account
        session['account_id'] = new.id
        session['account_name'] = new.name
        
        # announce success
        flash(account_name + ' created.','info')
        return redirect(url_for('main.index'))        

    # Handle GET requests
    return render_template('account/create.html')

@login_required
@account.route('/<int:account_id>/edit', methods=('GET','POST'))
def edit(account_id):
    try: 
        account = SMSAccount.query.get(account_id)
        owner = db.session.query(
            WebUser.id, WebUser.User, WebUser.first, WebUser.last
            ).join(
            User_Account_Link, User_Account_Link.user_id == WebUser.id
            ).filter(and_(
            User_Account_Link.is_owner,
            User_Account_Link.account_id == account.id
            )).first() 
        users = db.session.query(
            WebUser.id, WebUser.first, WebUser.last
            ).join(
            User_Account_Link, WebUser.id == User_Account_Link.user_id
            ).filter( 
            User_Account_Link.account_id == account_id
            ).all()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e)) 

    # require admin or owner access
    if not (current_user.is_admin or current_user.id == owner.id):
        flash('You need administrative or owner access for this.','error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        old_owner = owner.id
        owner_user_name = request.form.get('owner_user_name')
        account_name = request.form.get('account_name')
        number = cleanphone(request.form.get('number'))
        sid = request.form.get('sid')

        if not owner_user_name or not account_name or not number or not sid:
            flash('Need complete information to continue.','error')
            return render_template('account/edit.html',account=account,owner=owner,users=users)   
        
        if not owner or not owner.is_sms:
            flash('That user is not allowed to own account.','error')
            return render_template('account/edit.html', account=account,owner=owner,users=users)

        existing_account=False  #for testing
#        try:
#           existing_account = SMSAccount.query.filter(or_(
#                                                         SMSAccount.name  == account_name, 
#                                                         SMSAccount.number== number,
#                                                         SMSAccount.sid   == sid 
#                                                         )
#                                                      and_(not_( SMSAccount.id == account_id))
#                                                      ).first()
#                           
#        except sql_error as e:   
#            return redirect(url_for('errors.mysql_server', error = e))

        # if this returns an account we are creating a duplicate
        if existing_account : 
            flash('Conflict with existing account','error')
            return render_template('account/edit.html', account=account, owner=owner, users=users)

        account.name = account_name, 
        account.number = number,
        account.sid = sid 

        # add the updated account to the database
        try:
            db.session.add(account)
            db.session.commit()
            update = SMSAccount.query.filter(SMSAccount.name == account_name).first()
        except sql_error as e: 
            return redirect(url_for('errors.mysql_server', error = e))

        if not owner.User == owner_user_name: # getting a new owner
            try: # break current ownership link (remains a user)
                old_owner_link = User_Account_Link.query(and_( user_id == owner.id, account_id == update.id ))
                old_owner_link.is_owner = False
                db.session.add(old_owner_link)
                db.session.commit()

            except sql_error as e: 
                return redirect(url_for('errors.mysql_server', error = e))
                print("mysql error on delete ownership link")
        
            try: # create new ownership link
                owner = WebUser.query( WebUser.User == owner_user_name )
                new_owner_link = User_Account_Link.query(and_( user_id == new_owner.id, account_id == update.id ))
                if new_owner_link: # update an current account member
                    new_owner_link.is_owner = True
                else:              # create a new member as owner
                    new_owner_link = User_Account_Link( user_id = new_owner.id, is_owner = True, account_id = update.id )
                db.session.add(new_owner_link)
                db.session.commit()

            except sql_error as e: 
                return redirect(url_for('errors.mysql_server', error = e))  

        # make this our active account
        session['account_id'] = update.id
        session['account_name'] = update.name
        session['account_owner']= owner.id
        
        # announce success
        flash(account_name + ' updated.','info')
        return redirect(url_for('main.index'))        

    # Handle GET requests
          

    return render_template('account/edit.html', account=account, owner=owner, users=users)

# Make this our active account
@login_required
@account.post('/<int:account_id>/activate')
def activate(account_id):
    # limit access to sms users on the account or owner or admin
    try:
        account = SMSAccount.query.get(account_id)
        is_auth_user = db.session.query(
            WebUser.is_sms, WebUser.id
            ).join(
            User_Account_Link, WebUser.id == User_Account_Link.user_id
            ).filter(and_(
            User_Account_Link.is_owner,
            User_Account_Link.account_id == account.id
            )).first()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))


    if not (current_user.is_admin or  is_auth_user):
        flash(account.name + ' is not available to you.','error')
        return redirect(url_for('main.index'))

    session['account_id'] = account.id
    session['account_name'] = account.name
    session['account_owner']= is_auth_user.id

    return redirect(url_for('main.index'))

# Close our active account
@account.route('/close')
@login_required
def close():
    # limit access to sms users 
    if not current_user.is_sms:
        flash('Group selection is not available to you.','error')
        return redirect(url_for('main.index'))

    account_name=session['account_name']
    session['account_id'] = None
    session['account_name'] = None
    session['account_owner']= None

    flash('Account: '+account_name+' closed.','info')
    return redirect(url_for('main.index'))

# Veiw SMS Account details
@login_required
@account.route('/<int:account_id>/profile')
def profile(account_id):
    try: 
       account = SMSAccount.query.get(account_id)
       users = db.session.query(
            WebUser.id, WebUser.first, WebUser.last, User_Account_Link.is_owner
            ).join(
            User_Account_Link, WebUser.id == User_Account_Link.user_id
            ).filter( 
            User_Account_Link.account_id == account_id
            ).all()

    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))        

    return render_template("account/profile.html", account=account, users=users)

# select account from a radio button list
@login_required
@account.route('/select', methods=('GET', 'POST'))
def select():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))
    
    try: # get the list of current accounts
        if current_user.is_admin:
            accounts = SMSAccount.query.all()
        else:
            accounts = db.session.query(
                SMSAccount
                ).join(
                User_Account_Link, User_Account_Link.account_id == SMSAccount.id
                ).filter(
                User_Account_Link.user_id == current_user.id
                ).all()

    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))
  
    if request.method == 'POST':
        current_account_id = request.form.get('selection')

        if not current_account_id:
            flash('You need to select an account.','info')
            return redirect(url_for('account.select'))

        try:
            session['account_id'] = current_account_id
            account_selected = SMSAccount.query.get_or_404(current_account_id)
            session['account_name'] = account_selected.name
            owner = db.session.query(
                            User_Account_Link.user_id
                            ).filter(and_(
                                User_Account_Link.account_id  == account_selected.id,
                                User_Account_Link.is_owner
                            )).first()
        except sql_error as e:
            return redirect(url_for('errors.mysql_server', error = e))
        
        if owner:
            session['account_owner'] = owner.user_id
        else: 
            flash('Selected account has no owner.','error')
            return redirect(url_for('main.index'))
        return redirect(url_for('main.index'))

    return render_template("account/select.html", accounts=accounts)


# add user -- to current active account
@login_required
@account.route('/<int:user_id>/add_user')
def add_user(user_id):
    # restrict access
    current_account = SMSAccount.query.get_or_404(session['account_id'])

    user_name = WebUser.query.get_or_404(user_id).User
    link_exists = User_Account_Link.query.filter(
                         and_(\
                            User_Account_Link.user_id     == user_id, 
                            User_Account_Link.account_id  == current_account.id
                            )
                         ).first()
    is_auth_user= User_Account_Link.query.filter(
                         and_(\
                            User_Account_Link.user_id     == current_user.id, 
                            User_Account_Link.account_id  == current_account.id,
                            User_Account_Link.is_owner
                            )
                         ).first()

    if not current_user.is_admin and not is_auth_user:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    if link_exists:
        flash( user_name +' is already on account: ' + current_account.name, 'error' )
        return redirect(url_for('main.index'))

    link_to_add = User_Account_Link( user_id=user_id, account_id = current_account.id )
    try:
        db.session.add(link_to_add)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    # announce success
    flash(user_name +' added to account: '+ current_account.name,'info')
    return redirect(url_for('main.index'))

# here the owner of an SMS account can remove a user from that account
@login_required
@account.route('/<int:user_id>/<int:account_id>/delete_user')
def delete_user(user_id,account_id):

    # get user and account
    user_to_delete = WebUser.query.get_or_404(user_id)
    current_account = SMSAccount.query.get_or_404(account_id)
    

    # need authorization to edit account
    owner = db.session.query(
        WebUser.id
        ).join(
        User_Account_Link, WebUser.id == current_user.id
        ).filter(and_(
            User_Account_Link.account_id  == current_account.id,
            User_Account_Link.is_owner
        )).first()


    # attempt to delete owner can't work
    if user_to_delete.id == owner.id:
        flash('You cannot unlink the owner from an account','error')
        return redirect(url_for('main.index'))
    
    if not current_user.is_admin and not current_user.id == owner.id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    # find and remove the link
    try:
        link_to_delete = User_Account_Link.query.filter(
                         and_(
                            User_Account_Link.user_id     == user_to_delete.id, 
                            User_Account_Link.account_id  == current_account.id
                            )
                         ).first()

        db.session.delete(link_to_delete)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    # announce success
    flash(user_to_delete.User +' deleted from account.','info')
    return redirect(url_for('main.index'))

# and finally, the admin or owner of an account can delete the account
@login_required
@account.post('/<int:account_id>/delete_account')
def delete_account(account_id):
    account_to_delete = SMSAccount.query.get_or_404(account_id)

    # need authorization to edit account
    owner = db.select.query(
        Webuser.id
        ).link(
        User_Account_Link
        ).filter(and_(\
            User_Account_Link.user_id     == current_user.id, 
            User_Account_Link.account_id  == account_to_delete.id,
            User_Account_Link.is_owner
        )).first()
    
    if not current_user.is_admin and not current_user.id == owner.id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    try:
        db.session.delete(account_to_delete)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    # We will need to unlink users with account access here
    try:
        links_to_delete = User_Account_Link.query.filter(User_Account_Link.account_id == account_id).all()
        if links_to_delete:
            db.session.delete(links_to_delete)
            db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    flash(account_to_delete.name +'('+account_to_delete.number+') '+' deleted.','info')
    return redirect(url_for('main.index'))