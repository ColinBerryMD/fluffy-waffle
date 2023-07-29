# initiate database with single admin user
from app import db
from models import WebUser

db.drop_all()
db.create_all()

my_account = WebUser(
	User = 'admin'
    password = '*******'
    password_expires = None
    first = db.Column(db.String(50))
    last = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    sms = db.Column(db.String(12))
    voice = db.Column(db.String(12))
    is_admin = db.Column( db.Boolean() )
    is_sms = db.Column( db.Boolean() )
    default_account = db.Column(db.Integer)
    default_group = db.Column(db.Integer)
    translate = db.Column( db.Boolean() )
    two_fa_expires = db.Column( db.DateTime() ))

db.session.commit()