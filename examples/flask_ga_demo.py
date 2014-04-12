# -*- coding: utf-8 -*-

import time
from flask import Flask
from sga import FlaskGA

DEBUG = True

GA_ID = 'UA-46303840-3'
GA_FORBID_PATHS = [r'^/forbid']
GA_ALLOW_PATHS = [r'^/allow', r'/forbid']
GA_HACK_PATHS = [
    (r'/all(\S+)', r'/\g<1>/ok'),
]

app = Flask(__name__)
app.config.from_object(__name__)

fga = FlaskGA(app)


@app.route('/allow')
def allow():
    time.sleep(1)
    return u'ok'

@app.route('/forbid')
def forbid():
    time.sleep(1)
    return u'forbid'

if __name__ == '__main__':
    app.run()
