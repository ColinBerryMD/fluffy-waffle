from os import environ
from flask import Blueprint, render_template, redirect, request, flash, url_for, abort, current_app, session
from flask_login import LoginManager,  login_required, login_user, current_user, logout_user
from flask_bcrypt import Bcrypt


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError as sql_error
from sqlalchemy.sql import func, or_, and_
from sqlalchemy import text as sql_text

from twilio.rest import Client as TwilioClient

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
##### at least the sms sid and phone number will be account specific and retrieved
##### from database
try:
	class twilio_config():
		account_sid = environ['TWILIO_ACCOUNT_SID']
		otp_sid 	= environ['TWILIO_OTP_SERVICE_SID']
		sms_sid		= environ['TWILIO_MSG_SERVICE_SID']
		auth_token 	= environ['TWILIO_AUTH_TOKEN']
		twilio_phone= environ['TWILIO_PHONE_NUMBER']
		my_cell 	= environ['MY_CELL_NUMBER']
except KeyError:
	print("Error on initial twilio configuration. Did you set the environmental variables?")
	abort(401)

try:
	v_client = TwilioClient(twilio_config.account_sid, twilio_config.auth_token)
except:
	print("Error on initial twilio connection.")
	abort(401)