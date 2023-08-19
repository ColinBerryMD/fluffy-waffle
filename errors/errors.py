from flask import Flask, Blueprint, render_template, request, redirect, url_for
import webbrowser
from twilio.twiml.messaging_response import MessagingResponse

    
errors = Blueprint('errors', __name__, url_prefix='/errors',template_folder='templates')

@errors.app_errorhandler(404)
def page_not_found(error):
    return render_template('errors/404.html'), 404

@errors.app_errorhandler(405)
def page_not_found(error):
    return render_template('errors/405.html'), 405

@errors.app_errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

@errors.route('/twilio_server', methods=('GET','POST'))
def twilio_server():
    locale = request.args.get('locale')
    return render_template('errors/twilio.html',locale=locale)

@errors.route('/mysql_server', methods=('GET','POST'))
def mysql_server():
    error = request.args.get('error')
    locale = request.args.get('locale')
    return render_template('errors/mysql.html',error=error,locale=locale)
