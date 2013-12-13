# -*- coding: utf-8 -*-

import time
from flask import Flask
from sga.flask_ga import FlaskGA

DEBUG = True

GA_ID = 'UA-46303840-3'
GA_ALLOW_PATHS = [r'^/ok']
GA_FORBID_PATHS = []

app = Flask(__name__)
app.config.from_object(__name__)

fga = FlaskGA(app)


@app.route('/ok')
def ok():
    time.sleep(1)
    return u'ok'


if __name__ == '__main__':
    app.run()
