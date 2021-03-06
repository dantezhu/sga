# -*- coding: utf-8 -*-

from kola import Kola
from sga.kola_ga import KolaGA

app = Kola()
ga = KolaGA(dict(
    GA_ID='UA-46303840-3',
    GA_ALLOW_PATHS=[r'^index'],
    GA_HACK_PATHS=[
        (r'in(\S+)', r'\g<1>/ok'),
        ]
), app)


@app.route()
def index(request):
    pass


app.run('127.0.0.1', 5500)
