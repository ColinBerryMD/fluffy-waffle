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

class SMSClient(db.Model):
    __tablename__ ="SMSClient"
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    dob = db.Column(db.Date)
    email = db.Column(db.String(80))
    phone = db.Column(db.String(15))
    translate = db.Column(db.Boolean)
    blocked = db.Column(db.Boolean)

class Client_Group_Link(db.Model):
    __tablename__ ="Client_Group_Link"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer)
    group_id = db.Column(db.Integer)
    owner_id = db.Column(db.Integer)
    is_default = db.Column(db.Boolean)

class SMSGroup(db.Model):
    __tablename__ ="SMSGroup"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer)
    name = db.Column(db.String(40))
    comment = db.Column(db.String(160))

class SMSAccount(db.Model):
    __tablename__ ="SMSAccount"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer)
    name = db.Column(db.String(40))
    comment = db.Column(db.String(160))
    number = db.Column(db.String(12))
    sid = db.Column(db.String(36))

class User_Account_Link(db.Model):
    __tablename__ ="User_Account_Link"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    account_id = db.Column(db.Integer)
    is_default = db.Column(db.Boolean)

class Message(db.Model):
    __tablename__ ="Message"
    id = db.Column(db.Integer, primary_key=True)
    SentFrom = db.Column(db.String(14))
    SentTo = db.Column(db.String(14))
    SentAt =db.Column(db.String(50))
    Body = db.Column(db.String(160))
    Outgoing = db.Column(db.Boolean)
    Completed = db.Column(db.Boolean)
    Account = db.Column(db.Integer)

class BadPasswords(db.Model):
    __tablename__ = 'BadPasswords'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    baddie = db.Column(db.String(25)) # these are stored plain text

class OldPasswords(db.Model):
    __tablename__='OldPasswords'
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    oldie = db.Column(db.String(255)) # these are stored hashed
    created = db.Column(db.DateTime)
