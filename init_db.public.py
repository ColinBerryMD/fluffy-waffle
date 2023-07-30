# re-initialize the database with a single admin user
from app import db
from models import WebUser

db.drop_all()
db.create_all()

adam_the_admin = WebUser(
	User = 'admin',
    password = 'password',
    password_expires = None,
    first = 'Colin',
    last = 'Berry',
    email = 'colin.berry.md@gmail.com',
    sms = '+15555555555',
    voice = '+15555555555',
    is_admin = True,
    is_sms = True ,
    default_account = None,
    default_group = None,
    translate = False,
    two_fa_expires = None )

db.session.add(adam_the_admin)

db.session.commit()