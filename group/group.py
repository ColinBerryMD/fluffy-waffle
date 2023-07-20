from cbmd.extensions import  db, sql_error, Blueprint, render_template, request, url_for, flash, redirect,\
                             session, login_required, current_user, func, or_, and_

from cbmd.models import SMSClient, User_Account_Link, Client_Group_Link, SMSGroup, SMSAccount, WebUser

group = Blueprint('group', __name__, url_prefix='/group',template_folder='templates')

@group.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    # require an active account
    try:
        account_active = session['account_id']
    except KeyError:
        account_active = False
    if not account_active:
        flash('You need an active account for this.','error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        
        name = request.form['name']
                          
        # check for empty fields
        if not name:
            flash('Name Field cannot be empty.','error')
            return render_template('group/create.html')

        try:
           existing_group = SMSGroup.query.filter(SMSGroup.name == name).first()
                       
        except sql_error as e:   
            return redirect(url_for('errors.mysql_server', error = e))
        
        # if this returns a group we are creating a duplicate
        if existing_group : 
            flash('Group with this name already exists','error')
            return render_template('group/create.html')
        
        new_group = SMSGroup (name = name, account_id = session['account_id'])
        try:            # add to database on success
            db.session.add(new_group)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for('errors.mysql_server', error = e))     

        return redirect(url_for('main.index'))
    
    return render_template('group/create.html')

# no need to edit a group -- just delete and start over
# @group.route('/select')

# we expect a small number of groups
# so this veiw constructs a radio button based list 
# to combine the list and select tools in other blueprints
@group.route('/select', methods=('GET', 'POST'))
@login_required
def select():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))
    
    try: # get the list of  groups in accounts of this user
        groups = db.session.query(
            SMSGroup
            ).join(
            SMSAccount, SMSGroup.account_id == SMSAccount.id
            ).join(
            User_Account_Link, User_Account_Link.account_id == SMSAccount.id
            ).filter(
            User_Account_Link.user_id == current_user.id
            ).all()
            
    except sql_error as e: 
            return redirect(url_for('errors.mysql_server', error = e))
 
    if request.method == 'POST':
        selected_group_id = request.form['selection']
        group_selected = SMSGroup.query.get_or_404(selected_group_id)
  
        session['group_id'] = selected_group_id
        session['group_name'] = group_selected.name

        
        return redirect(url_for('group.profile',group_id=selected_group_id))

    # handle GET requests
    return render_template("group/select.html", groups=groups)

# Veiw group details
@group.route('/<int:group_id>/profile')
@login_required
def profile(group_id):
    group = SMSGroup.query.get(group_id)
    account = SMSAccount.query.get(group.account_id)

    # limit access to users of the relevant account
    try:
        has_access = db.session.query(
            User_Account_Link.user_id
            ).filter(
            User_Account_Link.account_id == account.id
            ).filter(
            User_Account_Link.user_id == current_user.id
            ).first()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))
    
    if not (has_access or current_user.is_admin):
        flash('You need access to account: '+ account.name + ' for this.','error')
        return redirect(url_for('main.index'))

    # link name from SMSClient to this group via Client_Group_link Join for a list of clients
    try:
        clients = db.session.query(
            SMSClient
            ).join(
            Client_Group_Link, SMSClient.id == Client_Group_Link.client_id
            ).filter(
            Client_Group_Link.group_id == group_id
            ).all()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    return render_template("group/profile.html", group=group, account=account, clients=clients)

# Make this our active group
@group.route('/<int:group_id>/activate')
@login_required
def activate(group_id):
    # limit access to sms users 
    group = SMSGroup.query.get_or_404(group_id)

    if not current_user.is_sms:
        flash('Group selection is not available to you.','error')
        return redirect(url_for('main.index'))

    session['group_id'] = group.id
    session['group_name'] = group.name
    return redirect(url_for('main.index'))

# Close our active group
@group.post('/close')
@login_required
def close():
    # limit access to sms users 
    if not current_user.is_sms:
        flash('Group selection is not available to you.','error')
        return redirect(url_for('main.index'))

    group_name=session['group_name']
    session['group_id'] = None
    session['group_name'] = None
    flash('Group :'+group_name+' closed.','info')
    return redirect(url_for('main.index'))


# add a client the current group
@group.route('/<int:client_id>/<int:group_id>/add_client')
@login_required
def add_client(client_id,group_id):
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    # limit access to users of the relevant account

    try:
        group = SMSGroup.query.get(group_id)
        has_access = User_Account_Link.query.filter(and_(
                                    User_Account_Link.user_id == current_user.id, 
                                    User_Account_Link.account_id == group.account_id )).first()
        already_enrolled = Client_Group_Link.query.filter(and_(
                                    Client_Group_Link.client_id == client_id, 
                                    Client_Group_Link.group_id == group.id )).first()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))
    
    if not ( has_access or current_user.is_admin):
        flash('You need access to account: '+ session['account_name'] + ' for this.','error')
        return redirect(url_for('main.index'))

    if already_enrolled:
        flash('That client is already enrolled.','info')
        return redirect(url_for('main.index'))

    new_link = Client_Group_Link(client_id = client_id, group_id = group.id)
    try:
        db.session.add(new_link)                
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    flash('Client added to '+ session['group_name'] +'.','info')
    return redirect(url_for('main.index'))

# delete a client from the current group
@group.post('/<int:client_id>/<int:group_id>/delete_client')
@login_required
def delete_client(client_id,group_id):
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        db.session.query(Client_Group_Link).filter(and_(
                         Client_Group_Link.group_id == group_id,
                         client_id == client_id
                        )).delete()
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    flash('Client removed from '+ session['group_name'] +'.','info')
    return redirect(url_for('main.index'))

# delete a whole client group
@group.post('/<int:group_id>/delete/')
@login_required
def delete(group_id):
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        group_to_delete = SMSGroup.query.get(group_id)
        db.session.delete(group_to_delete)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    # unlink the group from its clients
    try:
        links = Client_Group_Link.query.filter(Client_Group_Link.group_id == group_id).all()
        if links:
            db.session.delete(links)
            db.session.commit()
    except sql_error as e:
        return redirect(url_for('errors.mysql_server', error = e))

    flash('Group '+group_to_delete.name +' deleted.','info')
    return redirect(url_for('main.index'))