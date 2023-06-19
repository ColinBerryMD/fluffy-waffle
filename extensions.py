from os import environ
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from twilio.rest import Client as TwilioClient


db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
class twilio_config():
	account_sid = environ['TWILIO_ACCOUNT_SID']
	otp_sid 	= environ['TWILIO_OTP_SERVICE_SID']
	auth_token 	= environ['TWILIO_AUTH_TOKEN']
	my_cell 	= environ['MY_CELL_NUMBER']

v_client = TwilioClient(twilio_config.account_sid, twilio_config.auth_token)