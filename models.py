from flask_login import UserMixin
from datetime import datetime
from .extensions import db

class WebUser(UserMixin,db.Model):
    __tablename__="WebUser"
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    User = db.Column(db.String(32))
    password = db.Column(db.String(255))
    password_expires = db.Column(db.DateTime())
    first = db.Column(db.String(50))
    last = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    sms = db.Column(db.String(12))
    voice = db.Column(db.String(12))
    is_admin = db.Column( db.Boolean() )
    is_sms = db.Column( db.Boolean() )
    translate = db.Column( db.Boolean() )
    two_fa_expires = db.Column( db.DateTime() )

class BadPasswords(db.Model):
    __tablename__ = 'BadPasswords'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    baddie = db.Column(db.String(25)) # these are stored plain text

class OldPasswords(db.Model):
    __tablename__='OldPasswords'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    oldie = db.Column(db.String(255)) # these are stored hashed
    created = db.Column(db.DateTime)
