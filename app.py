from flask import Flask
from config import Config

from .extensions import db, bcrypt, login_manager, current_user, environ, Blueprint, session
from .models import WebUser

   

def create_app(config_class=Config):
    app = Flask(__name__)  
    
# Get essential configuration from environment

    app.config['SECRET_KEY'] = environ['WTF_SECRET']
    #app.config['SECRET_KEY'] = 'not_very_secret_key'

    # uncomment this to use SQLite for development
    #basedir = os.path.abspath(os.path.dirname(__file__))
    #db_url = 'sqlite:///' + os.path.join(basedir, 'database.db')

    # uncomment this to use mysql for real
    db_password = environ.get('MYSQL_WEBSERVER_PASSWORD')
    db_url = 'mysql+pymysql://webserver:'+db_password+'@localhost/sms'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    #app.config['SQLALCHEMY_ECHO'] = True

    app.config["REDIS_URL"] = "redis://localhost"

# initialize extensions
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # this doesn't throw exception with bad password
    db.init_app(app)
    
    bcrypt.init_app(app)

# Register blueprints here
    from .main import main as main_bp
    app.register_blueprint(main_bp)
    
    from .auth.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)  

    from .sms_client.sms_client import sms_client as sms_client_blueprint
    app.register_blueprint(sms_client_blueprint) 

    from .group.group import group as group_blueprint
    app.register_blueprint(group_blueprint) 

    from .message.message import message as message_blueprint
    app.register_blueprint(message_blueprint) 

    from .account.account import account as account_blueprint
    app.register_blueprint(account_blueprint) 

    from .errors.errors import errors as errors_blueprint
    app.register_blueprint(errors_blueprint) 

    app.register_blueprint(sse, url_prefix='/stream')

# Login manager
    @login_manager.user_loader
    def load_user(user_id):
        return WebUser.query.get(int(user_id))
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host = '0.0.0.0')