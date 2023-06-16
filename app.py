import os
from flask import Flask
from flask import Blueprint
from config import Config

# https://pythonhosted.org/Flask-Principal/
from flask_principal import Identity, AnonymousIdentity, identity_changed, \
RoleNeed, UserNeed, Permission, identity_loaded, Principal

from .extensions import db, bcrypt, login_manager, permit
from .models import WebUser
from .extensions import current_user


   
def create_app(config_class=Config):
    app = Flask(__name__)  
    
# Get essential configuration from environment

    app.config['SECRET_KEY'] = os.environ['WTF_SECRET']
    #app.config['SECRET_KEY'] = 'not_very_secret_key'

    # uncomment this to use SQLite for development
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_url = 'sqlite:///' + os.path.join(basedir, 'database.db')

    # uncomment this to use mysql for real
    #db_password = os.environ.get('MYSQL_WEBSERVER_PASSWORD')
    #db_url = 'mysql+pymysql://webserver:'+db_password+'@localhost/mysql'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# initialize extensions
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    db.init_app(app)
    permit.init_app(app)
    bcrypt.init_app(app)
    

# Register blueprints here
    from .main import main as main_bp
    app.register_blueprint(main_bp)
    
    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)  


    @login_manager.user_loader
    def load_user(user_id):
        return WebUser.query.get(int(user_id))


    
    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        
        # Set the identity user object
        identity.user = current_user
        
        # Add the UserNeed to the identity
        
    #    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))    
        # Assuming the User model has a list of roles, update the
        # identity with the roles that the user provides
    #    if hasattr(current_user, 'roles'):
    #        for role in user.roles:
    #        identity.provides.add(RoleNeed(role.name))
        if current_user.is_admin:
            identity.provides.add(RoleNeed("admin")) 
        if current_user.is_sms:
            identity.provides.add(RoleNeed("sms_user"))  

    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host = '0.0.0.0')