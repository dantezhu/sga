__version__ = '0.1.39'

from .ga_agent import GAAgent
try:
    from .django_ga import DjangoGA
except:
    pass
try:
    from .flask_ga import FlaskGA
except:
    pass

try:
    from .kola_ga import KolaGA
except:
    pass
