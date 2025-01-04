"""
WSGI config for gmtisp2 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Add appshere to the Python path if needed
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'appshere'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gmtisp2.settings')

application = get_wsgi_application()
