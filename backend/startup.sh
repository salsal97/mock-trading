#!/bin/bash

echo "🚀 Starting Mock Trading App on Azure..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "🗃️ Running database migrations..."
python manage.py migrate

# Collect static files
echo "📊 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist (for initial setup)
echo "👤 Setting up admin user..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@mocktrading.com', 'admin123')
    print('✅ Admin user created: admin/admin123')
else:
    print('✅ Admin user already exists')
"

# Start Gunicorn server
echo "🌟 Starting Gunicorn server..."
exec gunicorn mock_trading.wsgi:application --bind=0.0.0.0:$PORT --workers=2 --timeout=120 