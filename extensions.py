from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_principal import Principal, Permission, RoleNeed

db = SQLAlchemy()
bcrypt = Bcrypt()
permit = Principal()
login_manager = LoginManager()

admin_role = RoleNeed('admin')
sms_role = RoleNeed('sms_user')


admin_permission = Permission(RoleNeed('admin'))
