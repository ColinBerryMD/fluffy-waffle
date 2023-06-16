# fluffy-waffle

Redid the repository with some changes. App now runs  from SQLite practice database with the MySQL code commented out. I have a bash script (excluded by gitignore) that sets passwords and account info as environmental variables. At this point we dont access these so it runs fine without. I tried to put comments with end runs near anywhere that needs an environmental variable.

I also made a requirements.txt file.

The __init__.py is empty. app.py initializes and extensions.py prevents circular imports. 

The app compiles and runs as it is. @auth.route('/list') is one of the routes I want to reserve for admin users. If you uncomment #@admin_permission.require() it stops working. 

If I cant make flask-principal work for me, 'if current_user.is_admin:' will serve, but remember that the whole point here is for me to learn, rather than end run, flask best practices. That said, the paucity of tutorials and examples for flask-principals by comparision to the more popular flask modules makes me wonder.

