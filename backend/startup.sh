#!/bin/bash
echo "Starting Mock Trading App on Azure..."

# Set environment variables for production
export DJANGO_SETTINGS_MODULE=mock_trading.settings
export PYTHONPATH=/home/site/wwwroot

# Change to the application directory
cd /home/site/wwwroot

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
python manage.py shell << EOF
from django.contrib.auth.models import User
import os

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')
EOF

echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 mock_trading.wsgi:application 