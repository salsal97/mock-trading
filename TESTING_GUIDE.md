# 🧪 Mock Trading Application - Testing Guide

## Overview

This guide explains the comprehensive testing strategy for the Mock Trading Application, ensuring that local development testing matches GitHub Actions CI/CD pipeline exactly.

## 🎯 Testing Philosophy

Our testing approach focuses on **business rules validation** and **product functionality**, ensuring:
- ✅ All business rules are correctly implemented
- ✅ Market lifecycle works as expected
- ✅ User interactions follow proper constraints
- ✅ API endpoints behave correctly
- ✅ Frontend components render and function properly
- ✅ Database operations maintain data integrity

## 📊 Test Coverage

### GitHub Actions CI/CD Pipeline

The CI/CD runs **4 comprehensive test suites**:

1. **🐍 Backend Tests** - Django unit tests, model validation, database operations
2. **⚛️ Frontend Tests** - React component tests, UI functionality, accessibility
3. **🔗 Integration Tests** - Full-stack API tests, market activation, spread bidding
4. **🎯 Business Rules Tests** - Comprehensive validation of all 10+ business rules

### Local Development Testing

**Previously**: Only server startup, no systematic testing
**Now**: Complete test suite matching GitHub Actions exactly

## 🚀 Quick Start - Running Tests Locally

### 1. Comprehensive Test Suite (Matches GitHub Actions)
```powershell
.\run.ps1 test
```
This runs all 4 test suites exactly as GitHub Actions does.

### 2. Quick Tests (Fast feedback)
```powershell
.\run.ps1 quicktest
# OR
.\test-before-commit.ps1 -Quick
```

### 3. Individual Test Categories
```powershell
# Backend only
.\run.ps1 testbackend

# Frontend only  
.\run.ps1 testfrontend

# Business rules only
.\run.ps1 testbusiness

# API integration only
.\run.ps1 testapi
```

### 4. Pre-Commit Testing
```powershell
# Before committing
.\test-before-commit.ps1

# Quick pre-commit check
.\test-before-commit.ps1 -Quick

# Force commit despite failures (not recommended)
.\test-before-commit.ps1 -Force
```

## 📋 Test Suite Details

### 🐍 Backend Tests (`python manage.py test`)

**Location**: `backend/market/tests.py`, `backend/accounts/tests.py`

**Coverage**:
- ✅ Market model creation and validation
- ✅ Spread bidding mechanics
- ✅ No-bids delay functionality (NEW)
- ✅ User profile management
- ✅ Market activation logic
- ✅ Trading restrictions
- ✅ Settlement calculations
- ✅ Database relationships and constraints

**Key Business Rules Tested**:
- Market creators cannot bid on their own markets
- Only verified users can participate
- Spread bids must be positive numbers
- Market maker cannot trade after activation
- Balance tracking for virtual money

### ⚛️ Frontend Tests (`npm test`)

**Location**: `frontend/src/App.test.js`

**Coverage**:
- ✅ Authentication form rendering
- ✅ Oxford branding and styling
- ✅ Form validation and accessibility
- ✅ Component structure and routing readiness
- ✅ User interaction handling
- ✅ Responsive design elements

**Command Used**: `npm test -- --coverage --watchAll=false --testTimeout=30000`
(Exactly matches GitHub Actions)

### 🔗 Integration Tests (`test_trading_api.py`)

**Coverage**:
- ✅ Full API endpoint testing
- ✅ Authentication flow
- ✅ Market creation by admins
- ✅ Spread bidding by users
- ✅ Market activation scenarios
- ✅ Trading execution
- ✅ Error handling

**Environment**: Starts real Django server, tests actual HTTP requests

### 🎯 Business Rules Tests (`test_business_rules.py`)

**Coverage**: All 10+ core business rules:

1. **Auto-activation**: Markets activate when bids exist and bidding window closes
2. **Bidding windows**: Cannot bid outside active windows
3. **Tie-breaker**: First-come-first-served for equal spread bids
4. **No financial requirements**: Balance ignored for spread bidding
5. **Positive spreads**: Spread values must be positive
6. **Market maker restrictions**: Market makers cannot trade
7. **Admin privileges**: Only admins create markets
8. **User restrictions**: Regular users cannot create markets
9. **Virtual money**: All transactions are virtual
10. **No-bids delay**: Markets delay activation if no bids received (NEW)

## 🔧 Test Environment Setup

### Environment Variables (NO HARDCODED PASSWORDS!)
```powershell
# Required for all environments
$env:SECRET_KEY = "your-secure-secret-key"
$env:DEBUG = "True"

# Database credentials (from your secure environment)
$env:DB_NAME = "mock_trading"
$env:DB_USER = "your-db-username"
$env:DB_PASSWORD = "your-db-password"
$env:DB_HOST = "your-db-host"
$env:DB_PORT = "5432"

# Optional test passwords (GitHub Actions uses secrets)
$env:TEST_ADMIN_PASSWORD = "your-test-admin-password"
$env:TEST_USER_PASSWORD = "your-test-user-password"
```

### Database Safety Rules
✅ **Production Database**: `mock_trading` (production data)  
✅ **Test Database**: `test_mock_trading` (Django auto-creates, isolated)  
❌ **NO SQLite**: Only PostgreSQL with proper test isolation  
❌ **NO Hardcoded Passwords**: All credentials from environment variables  

### How Django Test Database Works
1. **Development**: Connects to `mock_trading` (production database)
2. **Testing**: Django automatically creates `test_mock_trading`
3. **Isolation**: Test data never touches production data
4. **Cleanup**: Test database destroyed after tests complete

## 🐛 Troubleshooting Common Issues

### Frontend Test Failures
```
Error: Unable to find element with text: /welcome back/i
```
**Solution**: Update test expectations to match actual rendered content.

### Backend Test Failures
```
Error: UserProfile matching query does not exist
```
**Solution**: Ensure all test users have verified profiles created.

### Integration Test Failures
```
Error: Connection refused
```
**Solution**: Ensure Django server is running on port 8000.

### Business Rules Test Failures
```
Error: Market activation failed
```
**Solution**: Check market timing constraints and user permissions.

## 📈 Test Performance

### Typical Run Times
- **Quick Tests**: ~30 seconds
- **Frontend Only**: ~15 seconds  
- **Backend Only**: ~25 seconds
- **Full Suite**: ~2-3 minutes
- **GitHub Actions**: ~5-7 minutes (including setup)

### Optimization Tips
- Django's test database creation is fast and reliable
- Run quick tests during development
- Use full suite before commits
- Parallel test execution where possible

## 🎯 Business Rule Focus Areas

### Market Lifecycle Testing
- Market creation by admins only
- Spread bidding window enforcement
- Auto-activation logic
- Trading phase restrictions
- Settlement calculations

### User Permission Testing
- Admin vs regular user capabilities
- Verified vs unverified user restrictions
- Market creator vs bidder roles
- Trading eligibility rules

### Financial Logic Testing
- Virtual money balance tracking
- Spread bid validation
- Trade execution prices
- Profit/loss calculations
- No real money involved

### New Feature Testing
- **No-bids delay rule**: Comprehensive testing of 24-hour delays
- Market status display during delays
- Multiple delay accumulation
- Admin override capabilities

## 🚀 Continuous Improvement

### Adding New Tests
1. Identify business rule or feature
2. Add test case to appropriate file
3. Ensure test runs in both local and CI environments
4. Update this guide if needed

### Test Maintenance
- Review test coverage monthly
- Update tests when business rules change
- Ensure tests remain fast and reliable
- Keep local and CI environments in sync

## 📞 Support

If tests fail unexpectedly:
1. Check this guide for common solutions
2. Ensure environment variables are set correctly
3. Verify database state is clean
4. Run tests individually to isolate issues
5. Check GitHub Actions logs for CI-specific issues

---

**Remember**: The goal is to catch issues locally before they reach GitHub Actions, ensuring smooth deployments and maintaining high code quality. 🎯 