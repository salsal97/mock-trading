param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Mock Trading Application Management Script

# Set local development flag
$env:MOCK_TRADING_LOCAL_DEV = "true"
Write-Host "Running in local development mode..." -ForegroundColor Cyan

# Function to check if a command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Function to create superuser if none exists
function Create-SuperUser {
    Write-Host "`nChecking for superuser..." -ForegroundColor Yellow
    # Load environment variables
    & ".\setup-env.ps1"
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
    # Load environment variables
    & ".\setup-env.ps1"
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
    try:
        is_verified = user.profile.is_verified if hasattr(user, 'profile') else False
        verification_date = user.profile.verification_date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(user, 'profile') and user.profile.verification_date else 'Never'
        verified_by = user.profile.verified_by.username if hasattr(user, 'profile') and user.profile.verified_by else 'None'
    except:
        is_verified = False
        verification_date = 'Never'
        verified_by = 'None'

    user_data.append({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_verified': is_verified,
        'verification_date': verification_date,
        'verified_by': verified_by,
        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'
    })

print('\nUser Database Information:')
print('=' * 100)

for user in user_data:
    print('\\nUser ID: {}'.format(user['id']))
    print('Username: {}'.format(user['username']))
    print('Email: {}'.format(user['email']))
    print('Name: {} {}'.format(user['first_name'], user['last_name']))
    print('Status:')
    print('  - Active: {}'.format(user['is_active']))
    print('  - Staff: {}'.format(user['is_staff']))
    print('  - Superuser: {}'.format(user['is_superuser']))
    print('  - Verified: {}'.format(user['is_verified']))
    if user['is_verified']:
        print('  - Verified on: {}'.format(user['verification_date']))
        print('  - Verified by: {}'.format(user['verified_by']))
    print('Date Joined: {}'.format(user['date_joined']))
    print('Last Login: {}'.format(user['last_login']))
    print('-' * 100)
"@
    python -c $pythonCode
    Set-Location ..
}

# Function to run migrations
function Run-Migrations {
    Write-Host "`nRunning migrations..." -ForegroundColor Yellow
    # Load environment variables
    & ".\setup-env.ps1"
    Set-Location backend
    .\venv\Scripts\activate
    python manage.py makemigrations
    python manage.py migrate
    Set-Location ..
}

# Function to create user profiles
function Create-UserProfiles {
    Write-Host "`nCreating user profiles..." -ForegroundColor Yellow
    # Load environment variables
    & ".\setup-env.ps1"
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

# Function to reset admin password
function Reset-AdminPassword {
    Write-Host "`nResetting admin password..." -ForegroundColor Yellow
    # Load environment variables
    & ".\setup-env.ps1"
    Set-Location backend
    .\venv\Scripts\activate
    $pythonCode = @"
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mock_trading.settings')
django.setup()

from django.contrib.auth.models import User

try:
    admin = User.objects.get(username='admin')
    admin.set_password('admin123')
    admin.save()
    print('Admin password has been reset to: admin123')
except User.DoesNotExist:
    print('Admin user not found. Creating new admin user...')
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('New admin user created!')
    print('Username: admin')
    print('Password: admin123')
"@
    python -c $pythonCode
    Set-Location ..
}

# Function to run comprehensive tests (matching GitHub Actions)
function Run-Tests {
    param([string]$TestType = "all")
    
    Write-Host "`nRunning Comprehensive Test Suite..." -ForegroundColor Green
    
    # Load environment variables
    & ".\setup-env.ps1"
    
    $testsPassed = $true
    
    if ($TestType -eq "all" -or $TestType -eq "backend") {
        Write-Host "`n🐍 Running Backend Tests..." -ForegroundColor Yellow
        Set-Location backend
        .\venv\Scripts\activate
        
        # Run Django unit tests
        Write-Host "Running Django unit tests..."
        python manage.py test --verbosity=2
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
        
        # Test database models
        Write-Host "Testing database models..."
        python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mock_trading.settings')
django.setup()
from django.contrib.auth.models import User
from market.models import Market, SpreadBid, Trade
from accounts.models import UserProfile
from django.utils import timezone
from datetime import timedelta
import uuid

print('=== Testing Model Creation ===')
username = f'testuser_{uuid.uuid4().hex[:8]}'
user, created = User.objects.get_or_create(
    username=username,
    defaults={'email': f'{username}@example.com', 'first_name': 'Test', 'last_name': 'User'}
)
if created:
    user.set_password('testpass')
    user.save()

profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={'balance': 1000.0, 'is_verified': True}
)
print(f'✓ Created user: {user.username}')

now = timezone.now()
market = Market.objects.create(
    premise=f'Test market {uuid.uuid4().hex[:8]}',
    unit_price=1.0,
    initial_spread=20,
    spread_bidding_open=now - timedelta(hours=1),
    spread_bidding_close_trading_open=now + timedelta(hours=1),
    trading_close=now + timedelta(hours=2),
    created_by=user
)
print(f'✓ Created market: {market.id}')
print('=== All model tests passed ===')
"
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
        
        Set-Location ..
    }
    
    if ($TestType -eq "all" -or $TestType -eq "frontend") {
        Write-Host "`n⚛️ Running Frontend Tests..." -ForegroundColor Yellow
        Set-Location frontend
        
        # Install dependencies if needed
        if (-not (Test-Path "node_modules")) {
            Write-Host "Installing frontend dependencies..."
            npm install
        }
        
        # Run tests with coverage (matching GitHub Actions)
        Write-Host "Running React tests with coverage..."
        npm test -- --coverage --watchAll=false --testTimeout=30000
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
        
        # Test build
        Write-Host "Testing frontend build..."
        $env:CI = "false"
        npm run build
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
        
        Set-Location ..
    }
    
    if ($TestType -eq "all" -or $TestType -eq "business") {
        Write-Host "`n🎯 Running Business Rules Tests..." -ForegroundColor Yellow
        
        # Set environment variables for business rules tests (NO HARDCODED PASSWORDS)
        if (-not $env:SECRET_KEY) {
            $env:SECRET_KEY = "test-secret-key-for-local-testing-only"
            Write-Host "⚠️  Using temporary SECRET_KEY for testing" -ForegroundColor Yellow
        }
        $env:DEBUG = "True"
        
        python test_business_rules.py
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
    }
    
    if ($TestType -eq "all" -or $TestType -eq "api") {
        Write-Host "`n🔗 Running API Integration Tests..." -ForegroundColor Yellow
        
        # Start backend server for API tests
        Write-Host "Starting backend server for API tests..."
        Set-Location backend
        .\venv\Scripts\activate
        
        # Start server in background
        $serverJob = Start-Job -ScriptBlock {
            param($BackendPath, $VenvPath)
            Set-Location $BackendPath
            & "$VenvPath\Scripts\Activate.ps1"
            python manage.py runserver 8000
        } -ArgumentList (Get-Location), ".\venv"
        
        Set-Location ..
        
        # Wait for server to start
        Write-Host "Waiting for server to start..."
        Start-Sleep -Seconds 10
        
        # Test server health
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8000/" -Method GET -TimeoutSec 5
            Write-Host "✓ Server is responding"
        } catch {
            Write-Host "⚠️ Server not responding, continuing with tests..."
        }
        
        # Run API tests
        $env:API_BASE_URL = "http://localhost:8000"
        $env:TEST_ADMIN_PASSWORD = "admin123"
        $env:TEST_USER_PASSWORD = "testpass123"
        
        python test_trading_api.py
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
        
        # Stop server
        Stop-Job $serverJob -Force
        Remove-Job $serverJob -Force
    }
    
    # Report results
    Write-Host "`n" -NoNewline
    if ($testsPassed) {
        Write-Host "🎉 All Tests Passed!" -ForegroundColor Green
        Write-Host "Your application is ready for deployment!" -ForegroundColor Green
    } else {
        Write-Host "❌ Some Tests Failed!" -ForegroundColor Red
        Write-Host "Please fix the failing tests before proceeding." -ForegroundColor Red
    }
    
    return $testsPassed
}

# Function to run specific test categories
function Run-QuickTests {
    Write-Host "`nRunning Quick Test Suite (Backend + Frontend only)..." -ForegroundColor Cyan
    return Run-Tests -TestType "backend,frontend"
}

# Function to show help
function Show-Help {
    Write-Host "`nMock Trading Application Management Script" -ForegroundColor Green
    Write-Host "Available commands:" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 start    - Start the application using start-servers.ps1" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 test     - Run comprehensive test suite (matches GitHub Actions)" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 quicktest - Run quick tests (backend + frontend only)" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 testbackend - Run backend tests only" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 testfrontend - Run frontend tests only" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 testbusiness - Run business rules tests only" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 testapi  - Run API integration tests only" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 users    - Show all users in the database" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 createsuperuser    - Create a superuser if none exists" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 migrate    - Run database migrations" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 createprofiles    - Create profiles for existing users" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 resetadmin    - Reset admin password to default" -ForegroundColor Cyan
    Write-Host "  .\run.ps1 help     - Show this help message" -ForegroundColor Cyan
}

# Main script logic
switch ($Command.ToLower()) {
    "start" { Start-Application }
    "test" { Run-Tests }
    "quicktest" { Run-QuickTests }
    "testbackend" { Run-Tests -TestType "backend" }
    "testfrontend" { Run-Tests -TestType "frontend" }
    "testbusiness" { Run-Tests -TestType "business" }
    "testapi" { Run-Tests -TestType "api" }
    "users" { Show-Users }
    "createsuperuser" { Create-SuperUser }
    "migrate" { Run-Migrations }
    "createprofiles" { Create-UserProfiles }
    "resetadmin" { Reset-AdminPassword }
    "help" { Show-Help }
    default { Show-Help }
} 