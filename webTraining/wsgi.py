"""
WSGI config for webTraining project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sys

#path a donde esta el manage.py de nuestro proyecto Django
path = '/home/nbertaina/Training/webTraining'
if path not in sys.path:
    sys.path.append(path)

#Para varias instancias corriendo
os.environ['DJANGO_SETTINGS_MODULE'] =  'webTraining.settings'

#Prevenir UnicodeEncodeError
os.environ.setdefault('LANG', 'en_US.UTF-8')
os.environ.setdefault('LC_ALL', 'en_US.UTF-8')

from dotenv import load_dotenv
project_folder = os.path.expanduser('~/webTraining')  # adjust as appropriate
load_dotenv(os.path.join(project_folder, '.env'))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
