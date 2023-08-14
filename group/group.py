from extensions import  db, sql_error, Blueprint, render_template, request, url_for, flash, redirect,\
                             flask_response, session, login_required, current_user, func, or_, and_

from models import SMSClient, User_Account_Link, Client_Group_Link, SMSGroup, SMSAccount, WebUser

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
            locale="checking for duplicate group name" 
            return redirect(url_for('errors.mysql_server', error = e,locale=locale))
        
        # if this returns a group we are creating a duplicate
        if existing_group : 
            flash('Group with this name already exists','error')
            return render_template('group/create.html')
        
        new_group = SMSGroup (name = name, account_id = session['account_id'])
        try:            # add to database on success
            db.session.add(new_group)
            db.session.commit()
        except sql_error as e: 
            locale="creating new group"
            return redirect(url_for('errors.mysql_server', error = e,locale=locale))     

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
    
    if not session['account_id']:
        flash ('First select an Account','error')
        return redirect(url_for('account.select'))
    else:
        groups = SMSAccount.query.filter(SMSAccount.id == session['account_id']).one().groups
 
    if request.method == 'POST':
        try:
            selected_group_id = request.form['selection']
        except:
            flash('You need to select a group.','error')
            return redirect(url_for('main.index'))
        
        group_selected = SMSGroup.query.filter(SMSGroup.id == selected_group_id).one()
  
        session['group_id'] = selected_group_id
        session['group_name'] = group_selected.name

        
        return redirect(url_for('group.profile',group_id=selected_group_id))

    # handle GET requests
    return render_template("group/select.html", groups=groups)

# Veiw group details
@group.route('/<int:group_id>/profile')
@login_required
def profile(group_id):
    try:
        group = SMSGroup.query.filter(SMSGroup.id == group_id).one()
    except sql_error as e:
        locale=" getting group to profile"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))
    if not group:
        flash('No group found with that id.','error')
        return redirect(url_for('main.index'))

    # limit access to users of the relevant account    
    if not (current_user in group.clients or current_user.is_admin):
        flash('You need access to group: '+ group.name + ' for this.','error')
        return redirect(url_for('main.index'))

    return render_template("group/profile.html", group=group)

# Make this our active group
@group.route('/<int:group_id>/activate')
@login_required
def activate(group_id):
    try:
        group = SMSGroup.query.filter(SMSGroup.id == group_id).one()
    except sql_error as e:
        locale=" getting group to activate"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))
    if not group:
        flash('No group found with that id.','error')
        return redirect(url_for('main.index'))

    # limit access to sms users 

    if not current_user.is_sms:
        flash('Group selection is not available to you.','error')
        return redirect(url_for('main.index'))

    session['group_id'] = group.id
    session['group_name'] = group.name
    
    return flask_response(status=204)

# Make this our default group
@login_required
@group.route('/<int:group_id>/default')
def default(group_id):
    user_to_update = WebUser.query.filter(WebUser.id == current_user.id).one()
    user_to_update.default_group = group_id
    try:
        db.session.add(user_to_update)
        db.session.commit()
    except sql_error as e:
        locale="updating default group"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    return flask_response(status=204)


# Close our active group
@group.route('/close')
@login_required
def close():
    # limit access to sms users 
    if not current_user.is_sms:
        flash('Group selection is not available to you.','error')
        return redirect(url_for('main.index'))

    group_name=session['group_name']
    session['group_id'] = None
    session['group_name'] = None
    
    return flask_response(status=204)


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
        group = SMSGroup.query.filter(SMSGroup.id == group_id).one()
    except sql_error as e:
        locale=" getting group to add to"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))
    if not group:
        flash('No group found with that id.','error')
        return redirect(url_for('main.index'))

    try:
        client = SMSClient.query.filter(SMSClient.id == client_id).one()
    except sql_error as e:
        locale=" getting client to add to group"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))
    if not client:
        flash('No client found with that id.','error')
        return redirect(url_for('main.index'))

    
    if not (current_user.is_admin or current_user in group.sms_account.users):
        flash('You need access to account: '+ session['account_name'] + ' for this.','error')
        return redirect(url_for('main.index'))

    if client in group.clients:
        flash('That client is already enrolled.','info')
        return redirect(url_for('main.index'))

    new_link = Client_Group_Link(client_id = client_id, group_id = group.id)
    try:
        db.session.add(new_link)                
        db.session.commit()
    except sql_error as e:
        locale="adding client to group"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))

    flash('Client added to '+ session['group_name'] +'.','info')
    return redirect(url_for('main.index'))

# delete a client from the current group
@group.route('/<int:client_id>/<int:group_id>/delete_client')
@login_required
def delete_client(client_id,group_id):
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        db.session.query(Client_Group_Link).filter(and_(
                         Client_Group_Link.group_id  == group_id,
                         Client_Group_Link.client_id == client_id
                        )).delete()
        db.session.commit()
    except sql_error as e:
        locale="remove client from group"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    flash('Client removed from '+ session['group_name'] +'.','info')
    return redirect(url_for('main.index'))

# delete a whole client group
@group.route('/<int:group_id>/delete/')
@login_required
def delete(group_id):
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        db.session.query(Client_Group_Link).filter(
                         Client_Group_Link.group_id == group_id,
                        ).delete()
        db.session.commit()
    except sql_error as e:
        locale="unlink clients from group"
        return redirect(url_for('errors.mysql_server', error = e, locale=locale))

    try:
        group_to_delete = SMSGroup.query.filter(SMSGroup.id == group_id).one()
        db.session.delete(group_to_delete)
        db.session.commit()
    except sql_error as e:
        locale="removing group"
        return redirect(url_for('errors.mysql_server', error = e,locale=locale))

    session['group_id'] = None
    session['group_name'] = None

    flash('Group '+group_to_delete.name +' deleted.','info')
    return redirect(url_for('main.index'))