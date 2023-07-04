from flask import Flask, Blueprint, render_template, request, url_for, flash, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, or_, and_

from cbmd.extensions import  db, sql_error
from cbmd.models import SMSClient, Client_Group_Link, SMSGroup
from cbmd.auth.auth import login_required, current_user

groups = Blueprint('groups', __name__, url_prefix='/groups',template_folder='templates/groups')

@login_required
@groups.route('/create', methods=('GET', 'POST'))
def create():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        
        name = request.form['name']
        comment  = request.form['comment']
                          
        # check for empty fields
        if not name:
            flash('Name Field cannot be empty.','error')
            return render_template('create.html')

        try:
           existing_group = SMSGroup.query.filter(SMSGroup.name == name).first()
                       
        except sql_error as e:   
            return redirect(url_for(errors.mysql_server, error = e))
        
        # if this returns a group we are creating a duplicate
        if existing_group : 
            flash('Group with this name already exists','error')
            return render_template('create.html')
        
        new_group = SMSGroup (name = name, comment = comment)
        try:            # add to database on success
            db.session.add(new_group)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))        

        return redirect(url_for('main.index'))
    
    return render_template('create.html')

# we expect a small number of groups
# so this veiw constructs a radio button based list 
# to combine the list and select tools in other blueprints
@login_required
@groups.route('/select_list', methods=('GET', 'POST'))
def select_list():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))
    
    try: # get the list of current groups
         ##### this should be limited to groups in accounts of this user
        groups = SMSGroup.query.all()
    except (MySQLdb.Error, MySQLdb.Warning) as e:
        print(e)
        return redirect(url_for(errors.mysql_server, error = e))
 
    if request.method == 'POST':
        current_group_id = request.form['selection']
        session['current_group_id'] = current_group_id
        group_selected = SMSGroup.query.get_or_404(current_group_id)
        session['group_name'] = group_selected.name

        
        return redirect(url_for('group.profile'))


    return render_template("select.html", groups=groups)

# Veiw group details
@login_required
@groups.route('/<int:group_id>/profile')
def profile(group_id):
    group = SMSGroup.query.get(group_id)
    account = SMSAccount.query.get(group.account_id)

    ###### limit access to users of the relevant account
    try:
        has_access = User_Account_Link.query.filter(and_(
                    user_id == current_user.id, account_id == account.id ))
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))
    if not has_access:
        flash('You need access to account: '+ account.name + ' for this.','error')
        return redirect(url_for('main.index'))

    # link name from SMSClient to this group via Client_Group_link Join for a list of clients
    try: 
        query = db.session.query(SMSClient.client_id, SMSClient.firstname, SMSClient.lastname,
                                 Client_Group_Link.client_id, Client_Group_Link.group_id)
        query = query.join(SMSClient).join(Client_Group_Link)
        clients = query.filter(Client_Group_Link.group_id == group_id).all()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    return render_template("profile.html", group=group, account=account, clients=clients)


# add a client the current group
@login_required
@groups.post('/<int:client_id>/add_client')
def add_client(client_id):
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    # limit access to users of the relevant account

    try:
        group = SMSGroup.query.get(session['current_group_id'])
        has_access = User_Account_Link.query.filter(and_(
                                        user_id == current_user.id, 
                                        account_id == group.account_id )).first()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))
    
    if not has_access:
        flash('You need access to account: '+ session['current_account_name'] + ' for this.','error')
        return redirect(url_for('main.index'))

    new_link = Client_Group_Link(client_id = client_id, group_id = group.id)
    try:
        db.session.add(new_link)                
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    flash('Client removed from '+ session['current_group_name'] +'.','info')
    return redirect(url_for('main.index'))

# delete a client from the current group
@login_required
@groups.post('/<int:client_id>/remove_client')
def delete_client(client_id):
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    try:
        db.session.query(Client_Group_Link).filter(and_(\
                         Client_Group_Link.group_id == session['current_group.id'],\
                         client_id == client_id\
                        )).delete()
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    flash('Client removed from '+ session['current_group_name'] +'.','info')
    return redirect(url_for('main.index'))

# delete a whole client group
@login_required
@groups.post('/<int:group_id>/delete/')
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
        return redirect(url_for(errors.mysql_server, error = e))

    # unlink the group from its clients
    try:
        links = Client_Group_Link.filter(Client_Group_Link.group_id == group_id)
        db.session.delete(links)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    flash('Group '+group_to_delete.name +' deleted.','info')
    return redirect(url_for('main.index'))
