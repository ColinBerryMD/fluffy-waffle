from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_required, current_user

from .models import WebUser
from .extensions import db
from .phonenumber import cleanphone
from .auth.cleanpassword import cleanpassword

main = Blueprint('main', __name__,template_folder="templates")

@main.route('/')
def index():
    return render_template('index.html')

