#!/bin/bash
cd /home/colin/python-source
source cbmd/env/bin/activate
source cbmd/private_config
gunicorn cbmd.app:app --worker-class gevent --bind 127.0.0.1:8000

