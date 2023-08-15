# fluffy-waffle

 App can run from SQLite practice database with the MySQL code commented out in app.py. I don't keep up with the tables is SQLite, so db.create_all() will be needed and the database file database.db (almost certianly out of date) is excluded from this repository. 

 I have a bash script (excluded by gitignore) that sets passwords and account info as environmental variables. export_config is an empty version of this script. I tried to put comments with end runs near near most places in the code that need an environmental variable. I also trap the first 'key error' for a smooth landing if critical environmental variables aren't set.

Some Twilio situations break the program rather than throw a catchable exception. Their Alarm utility doesn't seem to stop this. I'm trying to make all the 'reasonable' user errors and catch the ones I can for flash messages and do overs. I do verify that webhook posts are from them and track the progress of
outgoing messages from queued to sent to delivered (or undelivered or failed).

We now have the ability to create named client groups. The active group is used to facilitate sending messages to one or more clients of current clinical
importance from a set of tabs on the right side (bottom with a phone sized screen) of the messaging dashboard.

Works with multiple phone numbers (ie accounts). 
- Each account has an owner (assigned at creation) and multiple users who are added on later. A client can message any account they like.
- On login, a user's account or default account will be 'activated' -- session['active_account'] = .... Those with multiple accounts can 'select' another.

A note on directory structure. The blueprint layout is after https://realpython.com/flask-blueprint/. 
The root (cbmd) has app.py and the other backend modules. main.py has the veiws for our front end. It was written last, with its focus on styling. I plan for it to revolve around four dashboards: one for admin, one for a user who mostly needs to work with messages (but someday there should be some other tools for them), one for clients to enroll and maybe browse around, and one for visitors -- mostly a billboard. 
The other blueprints were constructed to test functionality during development. They were born unstyled. I suppose many will remain that way unless they prove to have a purpose in the production environment. I'll try and delete them as they outlive their utility.
	
- account: 
	- create -- a new sms twilio account
	- edit
	- list -- all the accounts
	- activate -- set active_account session variable
	- profile -- details of one account
	- select -- for multi account users
	- default -- set current active account as the current users default
	- add_user -- to the current active account by user_id
	- delete_user -- remove from the current active account (see auth.delete() to actually delete a user)
	- delete -- an account
			
- auth		
	- login -- this whole blueprint culminates in a successful user login
	- create -- set the stage by admin inviting a user (off line) and creating their username    
	- lookup -- our invited user looks up and claims the name
	- register -- our invited user has found their username. Here they create their profile
	- two_factor -- periodically prove yourself
	- change_password -- uses cleanpassword to enforce password hygiene
	- profile -- details of one user
	- edit
	- list -- all users
	- select -- search first and last names of users
	- logout
	- delete -- a user

- errors: custom error pages

- groups: groups of clients. Not mass messages, but promptly notify several people of the same information.
	- create
	- select -- user picks a group belonging to one of their accounts
	- activate -- set active_group session variable
	- add_client -- to the group
	- profile -- describe the group
	- default -- set the current active group as the current users default group
	- delete_client -- from a group
	- delete -- the group

- message: send and recieve sms messages with the active account
	- list -- the messaging dashboard
	- send -- a sms 
	- receive -- an sms via webhook
	- status -- recieve a status update via webhook
	- archive -- label a message for archiving
	
- sms_client		
	- create -- enter a client profile
	- terms -- use two factor auth to veiw terms and conditions and prove your humanity
	- list -- all cllients
	- profile -- a client
	- edit -- clients dont have a login, so corrections will need to be made by authorized users in their stead
	- select -- search for a single client. Hopefully there will be far too many to just look down a list.
	- block -- deleting a client wont help (they can just create a new client profile). Here we keep them in the DB in a blocked status.
	- delete -- a client

Messaging requires server sent events, which wont work on the flask development server. Upgraded to a combination of gunicorn, redis and nginx (none of which I understand that well but seem to be working).

At that point the front end is styled mostly with w3css. Needed some bootstrap and jquery to make it responsive. Time will tell how much more I will need.

Working hard to keep the local styling and javascript to a minimum. The general local css should be static/css/cbmd.css. The css for the messaging dashboard is in chat.css. The only local js is in static/javascript/sms.js. This does the dynamic modification of the message dashboard. There is a little js to listen for sse events at the bottom of base.html. At this point that is the only javascript in the project. The tiny jquery to make the nested phone menus work is also at the bottom of base.html.

Still to do: debug the status updates. Style the status updates. Write the archiving feature. Write the translator. Better responsive style. Cohesive overall color scheme. Write the content prose.

## I would appreciate feedback regarding style, readability and potential security vulnerabilities. 
