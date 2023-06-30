from flask import Flask, Blueprint, render_template, request, url_for, flash, redirect, session
from flask_sqlalchemy import SQLAlchemy

from .extensions import  db, sql_error
from .models import SMSClient, Client_Group_Link, SMSGroup
from .auth import login_required, current_user

group = Blueprint('group', __name__, url_prefix='/group')

@login_required
@group.route('/create', methods=('GET', 'POST'))
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
            return render_template('group.html')

        try:
           existing_group = SMSGroup.query.filter(SMSGroup.name == name).first()
                       
        except sql_error as e:   
            return redirect(url_for(errors.mysql_server, error = e))
        
        # if this returns a group we are creating a duplicate
        if existing_group : 
            flash('Group with this name already exists','error')
            return render_template('group.html')
        
        new_group = SMSGroup (name = name, comment = comment)
        try:            # add to database on success
            db.session.add(new_group)
            db.session.commit()
        except sql_error as e: 
            return redirect(url_for(errors.mysql_server, error = e))        

        return redirect(url_for('main.index'))
    
    return render_template('group.html')

@login_required
@group.route('/select', methods=('GET', 'POST'))
def select():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        current_group_id = request.form['selection']
        session['current_group_id'] = current_group_id
        group_selected = SMSGroup.query.get_or_404(current_group_id)
        session['group_name'] = group_selected.name

        return redirect(url_for('main.index'))

    try: # get the list of current groups
        groups = SMSGroup.query.all()
    except (MySQLdb.Error, MySQLdb.Warning) as e:
        print(e)
        return redirect(url_for(errors.mysql_server, error = e))

    return render_template("current_group.html", groups=groups)

@group.route('/link')
@login_required
def link():

    pass


@group.post('/delete')
@login_required
def delete():
    # require sms access
    if not current_user.is_sms:
        flash('You need messaging access for this.','error')
        return redirect(url_for('main.index'))

    sms_group_id = request.form['selection']
    try:
        group_to_delete = SMSGroup.query.get(sms_group_id)
        db.session.delete(group_to_delete)
        db.session.commit()
    except sql_error as e:
        return redirect(url_for(errors.mysql_server, error = e))

    # delete from Client_Group_Link where group_id == sms_group_id
    #try:
#        db.session.query(Client_Group_Link).filter(Client_Group_Link.group_id == sms_group_id).delete()
#        db.session.commit()
#    except sql_error as e:
#        return redirect(url_for(errors.mysql_server, error = e))

    flash('Group '+group_to_delete.name +' deleted.','info')
    return redirect(url_for('main.index'))
