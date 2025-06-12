param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Mock Trading Application Management Script

# Function to check if a command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Function to create superuser if none exists
function Create-SuperUser {
    Write-Host "`nChecking for superuser..." -ForegroundColor Yellow
    Set-Location backend
    .\venv\Scripts\activate
    python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Creating one...')
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created successfully!')
    print('Username: admin')
    print('Password: admin123')
else:
    print('Superuser already exists.')
"
    Set-Location ..
}

# Function to show all users in the database
function Show-Users {
    Write-Host "`nFetching users from database..." -ForegroundColor Yellow
    Set-Location backend
    .\venv\Scripts\activate
    $pythonCode = @"
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mock_trading.settings')
django.setup()

from django.contrib.auth.models import User
from django.core import serializers
import json
from datetime import datetime

users = User.objects.all()
user_data = []

for user in users:
    user_data.append({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
    })

print('\nUser Database Information:')
print('=' * 80)

for user in user_data:
    print('\\nUser ID: {}'.format(user['id']))
    print('Username: {}'.format(user['username']))
    print('Email: {}'.format(user['email']))
    print('Name: {} {}'.format(user['first_name'], user['last_name']))
    print('Status:')
    print('  - Active: {}'.format(user['is_active']))
    print('  - Staff: {}'.format(user['is_staff']))
    print('  - Superuser: {}'.format(user['is_superuser']))
    print('Date Joined: {}'.format(user['date_joined']))
    print('Last Login: {}'.format(user['last_login']))
    print('-' * 80)
"@
    python -c $pythonCode
    Set-Location ..
}

# Function to run migrations
function Run-Migrations {
    Write-Host "`nRunning migrations..." -ForegroundColor Yellow
    Set-Location backend
    .\venv\Scripts\activate
    python manage.py makemigrations
    python manage.py migrate
    Set-Location ..
}

# Function to create user profiles
function Create-UserProfiles {
    Write-Host "`nCreating user profiles..." -ForegroundColor Yellow
    Set-Location backend
    .\venv\Scripts\activate
    python manage.py create_user_profiles
    Set-Location ..
}

# Function to start the application
function Start-Application {
    Write-Host "Starting application using start-servers.ps1..." -ForegroundColor Green
    Run-Migrations
    Create-UserProfiles
    .\start-servers.ps1
}

# Function to show help
function Show-Help {
    Write-Host "`nMock Trading Application Management Script" -ForegroundColor Green
    Write-Host "Available commands:" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 start    - Start the application using start-servers.ps1" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 users    - Show all users in the database" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 createsuperuser    - Create a superuser if none exists" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 migrate    - Run database migrations" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 createprofiles    - Create profiles for existing users" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 help     - Show this help message" -ForegroundColor Cyan
}

# Main script logic
switch ($Command.ToLower()) {
    "start" { Start-Application }
    "users" { Show-Users }
    "createsuperuser" { Create-SuperUser }
    "migrate" { Run-Migrations }
    "createprofiles" { Create-UserProfiles }
    "help" { Show-Help }
    default { Show-Help }
} 