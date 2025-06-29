# 🔐 Secure Environment Setup Guide

## Overview

This guide shows how to securely configure environment variables for the Mock Trading Application without hardcoding any passwords or credentials.

## 🚨 Security Rules

❌ **NEVER** hardcode passwords in source code  
❌ **NEVER** commit credentials to git  
❌ **NEVER** use SQLite for production-like testing  
✅ **ALWAYS** use environment variables for credentials  
✅ **ALWAYS** use Django's test database isolation  
✅ **ALWAYS** use PostgreSQL for consistency  

## 🗄️ Database Configuration

### Production Database
- **Name**: `mock_trading`
- **Purpose**: Live application data
- **Access**: Production environment only

### Test Database  
- **Name**: `test_mock_trading` (Django auto-creates)
- **Purpose**: Isolated testing
- **Access**: Automatically managed by Django

## 🔧 Environment Variable Setup

### Windows PowerShell (Recommended)

```powershell
# Core Django Settings
$env:SECRET_KEY = "your-secure-django-secret-key-here"
$env:DEBUG = "True"

# Azure PostgreSQL Database Credentials
$env:DB_NAME = "mock_trading"
$env:DB_USER = "your-database-username"
$env:DB_PASSWORD = "your-database-password"
$env:DB_HOST = "your-database-host.postgres.database.azure.com"
$env:DB_PORT = "5432"

# Optional: Test User Passwords (for GitHub Actions)
$env:TEST_ADMIN_PASSWORD = "your-test-admin-password"
$env:TEST_USER_PASSWORD = "your-test-user-password"

# Verify setup
.\run.ps1 help
```

### Linux/Mac Bash

```bash
# Core Django Settings
export SECRET_KEY="your-secure-django-secret-key-here"
export DEBUG="True"

# Azure PostgreSQL Database Credentials
export DB_NAME="mock_trading"
export DB_USER="your-database-username"
export DB_PASSWORD="your-database-password"
export DB_HOST="your-database-host.postgres.database.azure.com"
export DB_PORT="5432"

# Optional: Test User Passwords
export TEST_ADMIN_PASSWORD="your-test-admin-password"
export TEST_USER_PASSWORD="your-test-user-password"
```

### Using .env File (Alternative)

Create a `.env` file in the project root (make sure it's in `.gitignore`):

```env
SECRET_KEY=your-secure-django-secret-key-here
DEBUG=True
DB_NAME=mock_trading
DB_USER=your-database-username
DB_PASSWORD=your-database-password
DB_HOST=your-database-host.postgres.database.azure.com
DB_PORT=5432
TEST_ADMIN_PASSWORD=your-test-admin-password
TEST_USER_PASSWORD=your-test-user-password
```

## 🧪 Testing Configuration

### Local Testing
- **Development Server**: Connects to `mock_trading` (production database)
- **Running Tests**: Django creates `test_mock_trading` (isolated)
- **Safety**: Test data never affects production

### GitHub Actions Testing
- **Credentials**: Stored in GitHub Secrets
- **Database**: Fresh PostgreSQL container per test run
- **Isolation**: Complete separation from production

## 🚀 Getting Started

### 1. Set Environment Variables
Choose your method above and set all required variables.

### 2. Verify Configuration
```powershell
# Check environment setup
.\setup-env.ps1

# Should show warnings if any variables are missing
```

### 3. Run Tests
```powershell
# Quick test to verify database connection
.\run.ps1 testbackend

# Full test suite
.\run.ps1 test
```

### 4. Start Development
```powershell
# Start the application
.\run.ps1 start
```

## 🔍 Verification Checklist

✅ All environment variables set (no hardcoded values)  
✅ Database connection works  
✅ Tests create `test_mock_trading` database  
✅ Production data remains untouched during testing  
✅ No passwords visible in source code  
✅ `.env` file (if used) is in `.gitignore`  

## 🆘 Troubleshooting

### Missing Environment Variables
```
⚠️ WARNING: DB_USER not found in environment!
```
**Solution**: Set all required database environment variables.

### Database Connection Failed
```
Error: Could not connect to database
```
**Solution**: Verify database credentials and network access.

### Test Database Issues
```
Error: Permission denied for database test_mock_trading
```
**Solution**: Ensure database user has permission to create databases.

## 🔐 Security Best Practices

1. **Never commit credentials**: Use `.gitignore` for `.env` files
2. **Use strong passwords**: Generate secure random passwords
3. **Rotate credentials regularly**: Update passwords periodically
4. **Limit database access**: Use principle of least privilege
5. **Monitor access logs**: Track database connections
6. **Use Azure Key Vault**: For production credential management

---

**Remember**: Security is everyone's responsibility. Keep credentials secure and never hardcode sensitive information! 🛡️ 