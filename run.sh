#!/bin/bash
cd /home/colin/python-source/cbmd
source env/bin/activate
source private_config
gunicorn3 app:app --worker-class gevent --bind 127.0.0.1:8000

