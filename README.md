# fluffy-waffle

Redid the repository with some changes. App now can run from SQLite practice database with the MySQL code commented out in app.py. I don't keep up with the tables is SQLite, so db.create_all() will be needed. I have a bash script (excluded by gitignore) that sets passwords and account info as environmental variables. export_config is an empty version of this script. I tried to put comments with end runs near near most places in the code that need an environmental variable.

The __init__.py is empty. app.py initializes and extensions.py prevents circular imports. 

Send, recieve, and list sms messages from a cell phone works. It won't look right until 
I can work in SSE and a pretty front end.

Error tracking is fine. Some Twilio situations break the program rather than throw a catchable exception. There Alarm utility doesn't seem to stop this. I'm trying to make all the 'reasonable' user errors and catch the ones I can for flash messages and do overs.

Next is the ability to create named client groups.

By then I hope I have learned enough about SSE to work that in to the chat function.

Then remaining tasks are real front end for the sms chat and more profesional 'look and feel'.

I would appreciate feedback regarding style, readability and potential security vulnerabilities. 
