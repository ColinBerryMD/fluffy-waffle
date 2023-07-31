# account.py
# routes for creating and maintaning Twilio messaging accounts

from models import WebUser, SMSAccount, User_Account_Link
from extensions import db, v_client, twilio_config, sql_error, render_template, request,\
                            url_for, flash, redirect, Blueprint, abort, session, func, or_, and_, not_,\
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
            owner = WebUser.query.filter(WebUser.User == owner_user_name).one()
                           
        except sql_error as e: 
            locale="finding a potential account owner by user name"  
            return redirect(url_for('errors.mysql_server', error = e, locale=locale))    
        
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
#            locale= "testing for account duplicates"  
#            return redirect(url_for('errors.mysql_server', error = e, locale=locale))

        # if this returns an account we are creating a duplicate
        if existing_account : 
            flash('Conflict with existing account','error')
            return render_template('account/create.html')

        new_account = SMSAccount (name = account_name, 
                                  number = number,
                                  owner_id = owner.id,
                                  sid = sid )

        # add the new account to the database
        try:
            db.session.add(new_account)
            db.session.commit()
            db.session.refresh(new_account)
        except sql_error as e: 
            locale="adding new account"
            return redirect(url_for('errors.mysql_server', error = e, locale=locale))

        # add the owner as first user account to the database
        owner_link = User_Account_Link( user_id = owner.id, account_id = new_account.id )
        try:
            db.session.add(owner_link)
            db.session.commit()
        except sql_error as e: 
            locale="adding new owner as user"
            return redirect(url_for('errors.mysql_server', error = e, locale=locale))

        # make this our active account
        session['account_id'] = new_account.id
        session['account_name'] = new_account.name
        
        # announce success
        flash(account_name + ' created.','info')
        return redirect(url_for('main.index'))        

    # Handle GET requests
    return render_template('account/create.html')

@login_required
@account.route('/<int:account_id>/edit', methods=('GET','POST'))
def edit(account_id):
    try: 
        account = SMSAccount.query.filter(SMSAccount.id == account_id).one()
    except sql_error as e:
        locale="getting account to edit"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale)) 

    # require admin or owner access
    if not (current_user.is_admin or current_user.id == account.owner_id):
        flash('You need administrative or owner access for this.','error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        old_owner = account.owner_id
        owner_user_name = request.form.get('owner_user_name')
        account_name = request.form.get('account_name')
        number = cleanphone(request.form.get('number'))
        sid = request.form.get('sid')

        if not owner_user_name or not account_name or not number or not sid:
            flash('Need complete information to continue.','error')
            return render_template('account/edit.html',account=account) 

        if not  account.owner.User == owner_user_name:
            new_owner = WebUser.query.filter(WebUser.User == owner_user_name).one()

            if not new_owner.is_sms:
                flash('That user is not allowed to own account.','error')
                return render_template('account/edit.html', account=account)

        #existing_account=False  #for testing
        try:
           existing_account = SMSAccount.query.filter(or_(
                                                         SMSAccount.name  == account_name, 
                                                         SMSAccount.number== number,
                                                         SMSAccount.sid   == sid 
                                                         ),
                                                      and_(not_( SMSAccount.id == account_id))
                                                      ).first()
                           
        except sql_error as e: 
            locale="testing for duplicate accounts"  
            return redirect(url_for('errors.mysql_server', error = e, locale=locale))
        
        # if this returns an account we are creating a duplicate
        if existing_account : 
            flash('Conflict with existing account','error')
            return render_template('account/edit.html', account=account)

        account.name = account_name 
        account.number = number
        if new_owner:
            account.owner_id = new_owner.user_id
        else:
            account.owner_id = old_owner

        account.sid = sid 

        # add the updated account to the database
        try:
            db.session.add(account)
            db.session.commit()
            db.session.refresh(account)
        except sql_error as e: 
            locale="updating edited account"
            return redirect(url_for('errors.mysql_server', error = e, locale=locale))

        # add new owner as user if needed

        if  not account in new_owner.accounts: 
            try: 
                new_owner_link = User_Account_Link(user_id=new_owner.id,account_id=account.id)
                db.session.add(new_owner_link)
                db.session.commit()

            except sql_error as e: 
                locale="adding new account owner to account"
                return redirect(url_for('errors.mysql_server', error = e, locale=locale))
                print("mysql error on delete ownership link")

        # make this our active account
        session['account_id'] = account.id
        session['account_name'] = account.name
        session['account_owner']= account.owner_id
        
        # announce success
        flash(account.name + ' updated.','info')
        return redirect(url_for('main.index'))        

    # Handle GET requests
          

    return render_template('account/edit.html', account=account)

# Make this our active account
@login_required
@account.route('/<int:account_id>/activate')
def activate(account_id):
    # limit access to sms users on the account or owner or admin
    try:
        account = SMSAccount.query.filter(SMSAccount.id == account_id).one()
    except sql_error as e:
        locale="getting account from id"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))


    if not (current_user.is_admin or  account.owner.is_sms):
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
       account = SMSAccount.query.filter(SMSAccount.id == account_id).one()
    except sql_error as e:
        locale="opening account for profile"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))        

    return render_template("account/profile.html", account=account)

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
            accounts = SMSAccount.query.filter(current_user in SMSAccount.users).all()

    except sql_error as e:
        locale="getting accounts for selection list"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))
  
    if request.method == 'POST':
        current_account_id = request.form.get('selection')

        if not current_account_id:
            flash('You need to select an account.','info')
            return redirect(url_for('account.select'))

        try:
            session['account_id'] = current_account_id
            account_selected = SMSAccount.query.filter(SMSAccount.id == current_account_id)
            session['account_name'] = account_selected.name
        except sql_error as e:
            locale= "selecting account"
            return redirect(url_for('errors.mysql_server', error = e, locale=locale))
        
        if account_selected.owner:
            session['account_owner'] = account_selected.user_id
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
    current_account = SMSAccount.query.filter(SMSAccount.id == session['account_id']).one()

    user = WebUser.query.filter(WebUser.id == user_id).one()

    if not current_user.is_admin and not current_account in user.owned_accounts:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    if user in current_account.users:
        flash( user.User +' is already on account: ' + current_account.name, 'info' )
        return redirect(url_for('main.index'))

    link_to_add = User_Account_Link( user_id=user_id, account_id = current_account.id )
    try:
        db.session.add(link_to_add)
        db.session.commit()
    except sql_error as e:
        locale="adding user to account"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    # announce success
    flash(user.User +' added to account: '+ current_account.name,'info')
    return redirect(url_for('main.index'))

# here the owner of an SMS account can remove a user from that account
@login_required
@account.route('/<int:user_id>/<int:account_id>/delete_user')
def delete_user(user_id,account_id):

    # get user and account
    user_to_delete = WebUser.query.filter(Webuser.id == user_id).one()
    current_account = SMSAccount.query.filter(SMSAccount.id == account_id)
    
    # attempt to delete owner can't work
    if user_to_delete.id == current_account.owner_id:
        flash('You cannot unlink the owner from an account','error')
        return redirect(url_for('main.index'))
    
    if not current_user.is_admin and not current_user.id == current_account.owner_id:
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
        locale="deleting user from account"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))

    # announce success
    flash(user_to_delete.User +' deleted from account.','info')
    return redirect(url_for('main.index'))

# and finally, the admin or owner of an account can delete the account
@login_required
@account.post('/<int:account_id>/delete_account')
def delete_account(account_id):
    account_to_delete = SMSAccount.query.filter(SMSAccount.id == account_id)

    # need authorization to edit account
    if not current_user.is_admin and not current_user.id == account_to_delete.owner_id:
        flash('You need admin access or account ownership for this.','error')
        return redirect(url_for('main.index'))

    try:
        db.session.delete(account_to_delete)
        db.session.commit()
    except sql_error as e:
        locale="deleting account"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    # I think this happens automatically  ################
    # We will need to unlink users with account access here
#    try:
#        links_to_delete = User_Account_Link.query.filter(User_Account_Link.account_id == account_id).all()
#        if links_to_delete:
#            db.session.delete(links_to_delete)
#            db.session.commit()
#    except sql_error as e:
#        return redirect(url_for('errors.mysql_server', error = e))

    flash(account_to_delete.name +'('+account_to_delete.number+') '+' deleted.','info')
    return redirect(url_for('main.index'))