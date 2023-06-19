# fluffy-waffle

Redid the repository with some changes. App now can run from SQLite practice database with the MySQL code commented out in app.py. I don't keep up with the tables is SQLite, so db.create_all() will be needed. I have a bash script (excluded by gitignore) that sets passwords and account info as environmental variables. export_config is an empty version of this script. I tried to put comments with end runs near near most places in the code that need an environmental variable.

The __init__.py is empty. app.py initializes and extensions.py prevents circular imports. 

The remaining tasks are real front end for the sms chat and more profesional 'look and feel'.

I would appreciate feedback regarding style, readability and potential security vulnerabilities. 
