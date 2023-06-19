# check for safe password
#import os
from password_strength import PasswordPolicy

from .app import bcrypt, db
from .models import BadPasswords, OldPasswords
from .extensions import environ

forgive = environ.get('FORGIVE_BAD_PASSWORDS')
#forgive = True

policy = PasswordPolicy.from_names(
    length     = environ['PASSWORD_LENGTH'],
    uppercase  = environ['PASSWORD_REQUIRE_UPPERCASE'],
    nonletters = environ['PASSWORD_REQUIRE_NON_LETTERS'],
    strength   =(environ['PASSWORD_REQUIRE_STRENGTH'], environ['PASSWORD_REQUIRE_ENTROPY_BITS'])
)

def cleanpassword(password,verify):
    # forgive bad passwords for debugging
    if forgive:
        return True

    # do they match?
    if not password == verify:
        flash ("Passwords don't match")
        return False

    # are they on the list of 10k really bad passwords?
    bad = BadPasswords.query.filter(BadPasswords.baddie == password).first()
    if bad:
        flash('Password '+ password +' is on the list of really bad passwords.','error')
        return False

    # are they on the list old passwords?
    oldies = OldPasswords.query.all()
    for o in oldies:
        if bcrypt.check_password_hashpassword ( o.oldie, password ):
            flash('Password '+ password +' is on the list of previous passwords.','error')
            return False

    # use the quality tests      
    test = policy.test(password)
    if test:
        for t in test:
            fault = t.name()
            if fault == 'length':
                flash('Password needs at least '+ str(t.length) +' letters.','error')
            if fault == 'uppercase':
                flash('Password needs at least '+ str(t.count)  +' upper-case letters.','error')
            if fault == 'nonletters':
                flash('Password needs at least '+ str(t.count)  +' non-letter characters.','error')
            if fault == 'strength':
                flash('Password needs more entropy.')#
        return False

    # seems to have passed all the tests
    return True
    