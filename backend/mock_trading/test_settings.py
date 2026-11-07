import os
os.environ.setdefault('SECRET_KEY', 'isolated-test-key')
for name in ('DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST'):
    os.environ.setdefault(name, 'unused')
from .settings import *
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MIDDLEWARE = [m for m in MIDDLEWARE if 'whitenoise' not in m]
ALLOWED_HOSTS = ['testserver', 'localhost']
