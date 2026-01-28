"""
ASGI config for marsdevs project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marsdevs.settings')

application = get_asgi_application()
