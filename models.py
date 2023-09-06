from flask_login import UserMixin

from datetime import datetime
from extensions import db, relationship

class WebUser(UserMixin,db.Model):
    __tablename__="WebUser"
    id = db.Column(db.Integer, primary_key=True) 
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
    default_account = db.Column(db.Integer)
    default_group = db.Column(db.Integer)
    two_fa_expires = db.Column( db.DateTime() )
    last_active = db.Column( db.DateTime() )  
    last_notification = db.Column( db.DateTime() )  
    owned_accounts = relationship("SMSAccount", back_populates="owner")
    accounts = relationship('SMSAccount', secondary = 'User_Account_Link', viewonly=True )

class SMSClient(db.Model):
    __tablename__ ="SMSClient"
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    dob = db.Column(db.String(10))
    email = db.Column(db.String(80))
    phone = db.Column(db.String(15))
    translate = db.Column(db.Boolean)
    blocked = db.Column(db.Boolean)
    groups = relationship("SMSGroup", secondary ="Client_Group_Link",viewonly=True )
    messages = relationship("Message",back_populates="sms_client")

class Message(db.Model):
    __tablename__ ="Message"
    id = db.Column(db.Integer, primary_key=True)
    SentFrom = db.Column(db.String(14))
    SentTo = db.Column(db.String(14))
    SentAt =db.Column(db.String(50))
    Body = db.Column(db.String(325))
    Outgoing = db.Column(db.Boolean)
    sms_sid = db.Column(db.String(40))
    sms_status = db.Column(db.String(20))
    archived = db.Column(db.Boolean)
    Account = db.Column(db.Integer,db.ForeignKey('SMSAccount.id'))
    sms_account = relationship('SMSAccount', back_populates='messages')
    Client = db.Column(db.Integer, db.ForeignKey('SMSClient.id'))  # this is stored in DB
    sms_client = relationship('SMSClient', back_populates='messages') # this simplifies access in our templates


class SMSAccount(db.Model):
    __tablename__ ="SMSAccount"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))
    number = db.Column(db.String(12))
    owner_id = db.Column(db.Integer, db.ForeignKey('WebUser.id'))
    owner = relationship("WebUser", back_populates="owned_accounts")
    sid = db.Column(db.String(36))
    messages = relationship("Message" ,back_populates="sms_account")
    groups = relationship(  "SMSGroup",back_populates="sms_account")
    users = relationship('WebUser', secondary = 'User_Account_Link', viewonly=True)

class SMSGroup(db.Model):
    __tablename__ ="SMSGroup"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('SMSAccount.id') )
    name = db.Column(db.String(40))
    comment = db.Column(db.String(160))
    sms_account = relationship("SMSAccount", back_populates="groups")
    clients = relationship("SMSClient", secondary = "Client_Group_Link", viewonly=True)

class Client_Group_Link(db.Model):
    __tablename__ ="Client_Group_Link"
    client_id = db.Column(db.Integer, db.ForeignKey(SMSClient.id), primary_key=True )
    group_id  = db.Column(db.Integer, db.ForeignKey(SMSGroup.id ), primary_key=True )

class User_Account_Link(db.Model):
    __tablename__ ="User_Account_Link"
    user_id    = db.Column(db.Integer, db.ForeignKey(WebUser.id)   ,primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey(SMSAccount.id),primary_key=True)


class BadPasswords(db.Model):
    __tablename__ = 'BadPasswords'
    id = db.Column(db.Integer, primary_key=True) 
    baddie = db.Column(db.String(25)) 

class OldPasswords(db.Model):
    __tablename__='OldPasswords'
    id = db.Column(db.Integer, primary_key=True) 
    oldie = db.Column(db.String(255)) 
    created = db.Column(db.DateTime)
