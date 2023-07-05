from flask import Flask, Blueprint, render_template, request

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
    return render_template('errors/twilio.html')

@errors.route('/mysql_server', methods=('GET','POST'))
def mysql_server():
    error = request.args.get('error')
    return render_template('errors/mysql.html',error=error)

@errors.route('/twilio_alarm', methods=['POST'])
def twilio_alarm():
    pass

    # eventually validate and parse the Twilio post
    ## make sure this is a valid twilio text message
#    validator = RequestValidator(os.environ.get('TWILIO_AUTH_TOKEN'))
#    if not validator.validate(request.url, request.form, request.headers.get('X-Twilio-Signature')):
#        abort(400)#

#    # get the parts we care about
#    SentFrom = request.form.get('From')
#    SentTo = os.environ['TWILIO_PHONE_NUMBER']
#    Body = request.form.get('Body')
    return("<Response/>")
