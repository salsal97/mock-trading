param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Mock Trading Application Management Script

# Function to check if a command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Function to show all users in the database
function Show-Users {
    Write-Host "`nFetching users from database..." -ForegroundColor Yellow
    Set-Location backend
    .\venv\Scripts\activate
    python manage.py shell -c "
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

# Print header
print('\nUser Database Information:')
print('=' * 80)

# Print each user's information
for user in user_data:
    print(f'\nUser ID: {user[\"id\"]}')
    print(f'Username: {user[\"username\"]}')
    print(f'Email: {user[\"email\"]}')
    print(f'Name: {user[\"first_name\"]} {user[\"last_name\"]}')
    print(f'Status:')
    print(f'  - Active: {user[\"is_active\"]}')
    print(f'  - Staff: {user[\"is_staff\"]}')
    print(f'  - Superuser: {user[\"is_superuser\"]}')
    print(f'Date Joined: {user[\"date_joined\"]}')
    print(f'Last Login: {user[\"last_login\"]}')
    print('-' * 80)
"
    Set-Location ..
}

# Function to start the application
function Start-Application {
    Write-Host "Starting application using start-servers.ps1..." -ForegroundColor Green
    .\start-servers.ps1
}

# Function to show help
function Show-Help {
    Write-Host "`nMock Trading Application Management Script" -ForegroundColor Green
    Write-Host "Available commands:" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 start    - Start the application using start-servers.ps1" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 users    - Show all users in the database" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 help     - Show this help message" -ForegroundColor Cyan
}

# Main script logic
switch ($Command.ToLower()) {
    "start" { Start-Application }
    "users" { Show-Users }
    "help" { Show-Help }
    default { Show-Help }
} 