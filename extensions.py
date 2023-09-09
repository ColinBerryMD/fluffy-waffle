from os import environ
from dotenv import load_dotenv, find_dotenv

from flask import Blueprint, render_template, redirect, request, flash, url_for, abort, current_app, session, Response as flask_response
from flask_login import LoginManager,  login_required, login_user, current_user, logout_user
from flask_bcrypt import Bcrypt

from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError as sql_error
from sqlalchemy.sql import func, or_, and_, not_
from sqlalchemy import text as sql_text, ForeignKey, inspect

from twilio.rest import Client as TwilioClient

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
load_dotenv(find_dotenv())

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
try:
	class twilio_config():
		account_sid = environ['TWILIO_ACCOUNT_SID']
		otp_sid 	= environ['TWILIO_OTP_SERVICE_SID']
		sms_sid		= environ['TWILIO_MSG_SERVICE_SID']
		auth_token 	= environ['TWILIO_AUTH_TOKEN']
#		twilio_phone= environ['TWILIO_PHONE_NUMBER']
		status      = environ['TWILIO_STATUS_WEBHOOK']
#		my_cell 	= environ['MY_CELL_NUMBER']
except KeyError:
	print("Error on initial twilio configuration. Did you set the environmental variables?")
	abort(401)

try:
	v_client = TwilioClient(twilio_config.account_sid, twilio_config.auth_token)
except:
	print("Error on initial twilio connection. Are the SID and auth token correct?")
	abort(401)