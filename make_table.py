# make table(s) from model one by one
from os import environ
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy()

# remember that the usual Webserver account is not privileged
db_password = environ.get('MYSQL_SMS_PRIVILEGED_PASSWORD')
db_url = 'mysql+pymysql://privileged:'+db_password+'@localhost/sms'	
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False	

db.init_app(app)

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

with app.app_context():
	#Client_Group_Link.__table__.drop(db.engine)
	User_Account_Link.__table__.create(db.engine)	

	SMSAccount.__table__.create(db.engine)
