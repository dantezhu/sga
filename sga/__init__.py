__version__ = '0.1.29'

from .ga_agent import GAAgent
try:
    from .django_ga import DjangoGA
except:
    pass
try:
    from .flask_ga import FlaskGA
except:
    pass