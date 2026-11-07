"""Explicit PostgreSQL test-only settings; never load the application's DB settings."""
import os
from django.core.exceptions import ImproperlyConfigured
from .test_settings import *

host = os.environ.get('REVIVAL_TEST_PG_HOST', '127.0.0.1')
if host not in ('127.0.0.1', 'localhost', '::1'):
    raise ImproperlyConfigured('PostgreSQL tests require an isolated local server')
user = os.environ.get('REVIVAL_TEST_PG_USER')
password = os.environ.get('REVIVAL_TEST_PG_PASSWORD')
if not user or not password:
    raise ImproperlyConfigured('Provide dedicated REVIVAL_TEST_PG_USER and REVIVAL_TEST_PG_PASSWORD')
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'revival_isolated',
    'USER': user, 'PASSWORD': password, 'HOST': host,
    'PORT': os.environ.get('REVIVAL_TEST_PG_PORT', '55432'),
    'TEST': {'NAME': 'test_revival_isolated'}}}
