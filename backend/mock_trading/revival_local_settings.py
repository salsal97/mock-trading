"""Explicitly isolated local development settings; never reads DB connection settings."""
from pathlib import Path
from .test_settings import *
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'revival-local.sqlite3'}}
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
CORS_ALLOWED_ORIGINS = ['http://localhost:3100', 'http://127.0.0.1:3100']
ROOT_URLCONF = 'mock_trading.revival_local_urls'
