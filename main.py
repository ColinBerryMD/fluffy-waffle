# main.py

# These veiws are expected to be just landing pads for our four most likely scenarios.
# The substance of our app is in the other blueprints. Much of that html is unstyled.
# These were written afterwards with the focus on style rather than development.
# CB 7/2023

from .extensions import Blueprint, render_template, redirect, url_for, flash,\
                        login_required, current_user

main = Blueprint('main', __name__,template_folder="templates")

# the general public lands here
@main.route('/')
def index():
    return render_template('index.html')

# our contact information
@main.route('/contact/')
def contact():
    return render_template('contact.html')

# an sms from a potential client (ie not registered) generates a response
# with a link to this
@main.route('/client/')
def client():
    return render_template('client.html')

# most user logins will land here to use the sms server
@main.route('/user/')
@login_required
def user():
    return render_template('user.html')

#  this is the admin maintenance dashboard
@main.route('/admin/')
@login_required
def admin():
    # require admin access
    if not current_user.is_admin:
        flash('You need administrative access for this.','error')
        return redirect(url_for('main.index'))

    # display dashboard
    return render_template('admin.html')



