import os
from flask import Flask
from flask import Blueprint
from config import Config
from datetime import datetime, timedelta

from .extensions import db, bcrypt, login_manager, current_user
from .models import WebUser

password_lifetime = timedelta( days = int(os.environ['PASSWORD_LIFE_IN_DAYS']))
two_fa_lifetime   = timedelta( days = int(os.environ['TWO_FA_LIFE_IN_DAYS']))
   
def create_app(config_class=Config):
    app = Flask(__name__)  
    
# Get essential configuration from environment

    app.config['SECRET_KEY'] = os.environ['WTF_SECRET']
    #app.config['SECRET_KEY'] = 'not_very_secret_key'

    


    # uncomment this to use SQLite for development
    #basedir = os.path.abspath(os.path.dirname(__file__))
    #db_url = 'sqlite:///' + os.path.join(basedir, 'database.db')

    # uncomment this to use mysql for real
    db_password = os.environ.get('MYSQL_WEBSERVER_PASSWORD')
    db_url = 'mysql+pymysql://webserver:'+db_password+'@localhost/mysql'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# initialize extensions
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    db.init_app(app)
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
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host = '0.0.0.0')