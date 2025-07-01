# Comprehensive Pre-commit Test Suite for Mock Trading Application
# Mirrors GitHub Actions workflow to save CI/CD costs and catch issues early

param(
    [switch]$SkipIntegration,  # Skip integration tests for faster commits
    [switch]$Force
)

Write-Host ('======================================') -ForegroundColor Magenta
Write-Host ('   COMPREHENSIVE PRE-COMMIT TESTS    ') -ForegroundColor Magenta
Write-Host ('======================================') -ForegroundColor Magenta
Write-Host ('Running full test suite locally...') -ForegroundColor Yellow
Write-Host ('Started at: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
Write-Host ('')

$testsPassed = $true
$startTime = Get-Date
$testResults = @()

# Helper function to add test result
function Add-TestResult {
    param($Name, $Status, $Duration, $Details = "")
    $script:testResults += [PSCustomObject]@{
        Test = $Name
        Status = $Status
        Duration = $Duration
        Details = $Details
    }
}

# Helper function to show progress
function Show-Progress {
    param($Message)
    Write-Host ('  ⏳ ' + $Message) -ForegroundColor Cyan
}

# Helper function to show completion
function Show-Complete {
    param($Message, $Success = $true)
    $icon = if ($Success) { "✅" } else { "❌" }
    $color = if ($Success) { "Green" } else { "Red" }
    Write-Host ('  ' + $icon + ' ' + $Message) -ForegroundColor $color
}

try {
    # ===== 1. ENVIRONMENT SETUP =====
    Write-Host ('[1/6] Environment Setup') -ForegroundColor Cyan
    Write-Host ('Time: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
    $stepStart = Get-Date
    
    Show-Progress ('Checking project structure...')
    Start-Sleep -Milliseconds 500  # Brief pause to show progress
    
    # Check project structure
    $requiredFiles = @(
        "frontend/package.json",
        "backend/manage.py", 
        "backend/requirements.txt",
        ".gitignore"
    )
    
    foreach ($file in $requiredFiles) {
        Show-Progress ('Checking: ' + $file)
        if (!(Test-Path $file)) {
            Write-Host ('  [FAIL] Missing: ' + $file) -ForegroundColor Red
            $testsPassed = $false
        } else {
            Write-Host ('  [OK] Found: ' + $file) -ForegroundColor Green
        }
    }
    
    Show-Progress ('Setting up environment variables...')
    # Load environment variables from .env file or existing environment
    $env:MOCK_TRADING_LOCAL_DEV = "true"
    & ".\setup-env.ps1"
    
    # Fallback environment variables only if not already set
    if (-not $env:SECRET_KEY) {
        $env:SECRET_KEY = "test-secret-key-for-local-testing-only-not-production"
    }
    if (-not $env:DEBUG) {
        $env:DEBUG = "True"
    }
    # For testing, use test database name
    if ($env:DB_NAME -and $env:DB_NAME -ne "mock_trading") {
        # Keep existing DB_NAME if it's not the default
    } else {
        $env:DB_NAME = "mock_trading"  # Django will automatically create test_mock_trading for tests
    }
    
    # Validate that we have database connection info
    if (-not $env:DB_HOST -or -not $env:DB_USER -or -not $env:DB_PASSWORD) {
        Write-Host ('  [WARN] Database connection not fully configured. Tests may fail.') -ForegroundColor Yellow
        Write-Host ('  [WARN] Make sure your .env file contains: DB_HOST, DB_USER, DB_PASSWORD') -ForegroundColor Yellow
    } else {
        Write-Host ('  [OK] Database configuration loaded from environment') -ForegroundColor Green
        if ($env:DB_HOST -like "*.postgres.database.azure.com") {
            Write-Host ('  [OK] Using Azure PostgreSQL for testing') -ForegroundColor Green
        }
    }
    
    $stepDuration = (Get-Date) - $stepStart
    Add-TestResult "Environment Setup" "PASS" $stepDuration.TotalSeconds
    $durationStr = $stepDuration.TotalSeconds.ToString('F1')
    $message = "Environment setup completed " + $durationStr + " seconds"
    Show-Complete $message
    Write-Host ('')

    # ===== 2. BACKEND TESTS =====
    Write-Host ('[2/6] Backend Django Tests') -ForegroundColor Cyan
    Write-Host ('Time: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
    Write-Host ('Estimated duration: 30-60 seconds') -ForegroundColor Gray
    $stepStart = Get-Date
    
    Show-Progress ('Navigating to backend directory...')
    Set-Location backend
    
    # Activate virtual environment
    Show-Progress ('Checking for virtual environment...')
    if (Test-Path "venv\Scripts\activate.ps1") {
        Show-Progress ('Activating virtual environment...')
        & "venv\Scripts\activate.ps1"
        Show-Complete "Virtual environment activated"
    } else {
        Write-Host ('  [WARN] No virtual environment found, using system Python') -ForegroundColor Yellow
    }
    
    # Display database connection info for debugging
    Write-Host ('  [DB] Testing with: ' + $env:DB_HOST + ':' + $env:DB_PORT + '/' + $env:DB_NAME) -ForegroundColor Gray
    
    # Check Django installation
    Show-Progress ('Verifying Django installation...')
    python -c "import django; print(f'Django {django.get_version()} OK')" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ('  [FAIL] Django not available') -ForegroundColor Red
        $testsPassed = $false
    } else {
        Show-Complete "Django installation verified"
    }
    
    # Run migrations check
    Show-Progress ('Checking database migrations...')
    python manage.py makemigrations --check --dry-run 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ('  [WARN] Pending migrations detected') -ForegroundColor Yellow
    } else {
        Show-Complete "Migrations are up to date"
    }
    
    # Test database connection
    Show-Progress ('Testing database connection...')
    python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mock_trading.settings')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ('  [FAIL] Database connection test failed') -ForegroundColor Red
        $testsPassed = $false
    } else {
        Show-Complete "Database connection verified"
    }
    
    # Run Django system check
    Show-Progress ('Running Django system check...')
    python manage.py check --verbosity=1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ('  [FAIL] Django system check failed') -ForegroundColor Red
        $testsPassed = $false
    } else {
        Show-Complete "Django system check passed"
    }
    
    # Run all Django tests
    Show-Progress ('Running Django unit tests (this may take 30-60 seconds)...')
    Write-Host ('  [TEST] Progress: Starting test discovery...') -ForegroundColor Gray
    
    # Run tests with more verbose output (without parallel to avoid unique constraint issues)
    python manage.py test --verbosity=2 --keepdb
    $backendTestResult = $LASTEXITCODE
    
    Set-Location ..
    $stepDuration = (Get-Date) - $stepStart
    
    if ($backendTestResult -eq 0) {
        Add-TestResult "Backend Tests" "PASS" $stepDuration.TotalSeconds
        $durationStr = $stepDuration.TotalSeconds.ToString('F1')
        $message = "All backend tests passed " + $durationStr + " seconds"
        Show-Complete $message
} else {
        Add-TestResult "Backend Tests" "FAIL" $stepDuration.TotalSeconds
        Write-Host ('  [FAIL] Backend tests failed') -ForegroundColor Red
        $testsPassed = $false
    }
    Write-Host ('')

    # ===== 3. FRONTEND TESTS =====
    Write-Host ('[3/6] Frontend React Tests') -ForegroundColor Cyan
    Write-Host ('Time: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
    Write-Host ('Estimated duration: 20-40 seconds') -ForegroundColor Gray
    $stepStart = Get-Date
    
    Show-Progress ('Navigating to frontend directory...')
    Set-Location frontend
    
    # Check Node.js and npm
    Show-Progress ('Checking Node.js environment...')
    $nodeVersion = node --version
    $npmVersion = npm --version
    Write-Host ('  [PKG] Node.js: ' + $nodeVersion) -ForegroundColor Gray
    Write-Host ('  [PKG] npm: ' + $npmVersion) -ForegroundColor Gray
    
    # Install dependencies if needed
    Show-Progress ('Checking npm dependencies...')
    if (!(Test-Path "node_modules")) {
        Show-Progress ('Installing npm dependencies (this may take 1-2 minutes)...')
        npm install
        Show-Complete "npm dependencies installed"
    } else {
        Show-Complete "npm dependencies already installed"
    }
    
    # Run frontend tests with coverage
    Show-Progress ('Running React tests with coverage (this may take 20-40 seconds)...')
    Write-Host ('  [TEST] Progress: Starting Jest test runner...') -ForegroundColor Gray
    $env:CI = "true"
    npm test -- --coverage --watchAll=false --testTimeout=30000 --verbose
    $frontendTestResult = $LASTEXITCODE
    
    if ($frontendTestResult -eq 0) {
        Show-Complete "Frontend tests passed"
    } else {
        Write-Host ('  [FAIL] Frontend tests failed') -ForegroundColor Red
    }
    
    # Test frontend build
    Show-Progress ('Testing production build (this may take 10-20 seconds)...')
    Write-Host ('  [BUILD] Progress: Creating optimized production build...') -ForegroundColor Gray
    $env:CI = "false"
    npm run build
    $buildResult = $LASTEXITCODE
    
    Set-Location ..
    $stepDuration = (Get-Date) - $stepStart
    
    if ($frontendTestResult -eq 0 -and $buildResult -eq 0) {
        Add-TestResult "Frontend Tests" "PASS" $stepDuration.TotalSeconds
        $durationStr = $stepDuration.TotalSeconds.ToString('F1')
        $message = "Frontend tests and build passed " + $durationStr + " seconds"
        Show-Complete $message
    } else {
        Add-TestResult "Frontend Tests" "FAIL" $stepDuration.TotalSeconds
        Write-Host ('  [FAIL] Frontend tests or build failed') -ForegroundColor Red
        $testsPassed = $false
    }
    Write-Host ('')

    # ===== 4. BUSINESS RULES TESTS =====
    Write-Host ('[4/6] Business Rules Validation') -ForegroundColor Cyan
    Write-Host ('Time: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
    Write-Host ('Estimated duration: 10-20 seconds') -ForegroundColor Gray
    $stepStart = Get-Date
    
    Show-Progress ('Running business rules tests...')
    Write-Host ('  [RULES] Progress: Validating trading logic and constraints...') -ForegroundColor Gray
    python test_business_rules.py
    $businessRulesResult = $LASTEXITCODE
    
    $stepDuration = (Get-Date) - $stepStart
    
    if ($businessRulesResult -eq 0) {
        Add-TestResult "Business Rules" "PASS" $stepDuration.TotalSeconds
        $durationStr = $stepDuration.TotalSeconds.ToString('F1')
        $message = "Business rules validation passed " + $durationStr + " seconds"
        Show-Complete $message
    } else {
        Add-TestResult "Business Rules" "FAIL" $stepDuration.TotalSeconds
        Write-Host ('  [FAIL] Business rules validation failed') -ForegroundColor Red
        $testsPassed = $false
    }
    Write-Host ('')

    # ===== 5. INTEGRATION TESTS (Optional) =====
    if (-not $SkipIntegration) {
        Write-Host ('[5/6] Integration Tests') -ForegroundColor Cyan
        Write-Host ('Time: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
        Write-Host ('Estimated duration: 30-60 seconds') -ForegroundColor Gray
        $stepStart = Get-Date
        
        Show-Progress ('Running API integration tests...')
        Write-Host ('  [API] Progress: Testing API endpoints and workflows...') -ForegroundColor Gray
        $env:API_BASE_URL = "http://localhost:8000"
        python test_trading_api.py
        $integrationResult = $LASTEXITCODE
        
        $stepDuration = (Get-Date) - $stepStart
        
        if ($integrationResult -eq 0) {
            Add-TestResult "Integration Tests" "PASS" $stepDuration.TotalSeconds
            $durationStr = $stepDuration.TotalSeconds.ToString('F1')
            $message = "Integration tests passed " + $durationStr + " seconds"
            Show-Complete $message
        } else {
            Add-TestResult "Integration Tests" "FAIL" $stepDuration.TotalSeconds
            Write-Host ('  [FAIL] Integration tests failed') -ForegroundColor Red
            $testsPassed = $false
        }
    } else {
        Add-TestResult "Integration Tests" "SKIP" 0 "Skipped for faster commit"
        Write-Host ('[5/6] Integration Tests - SKIPPED') -ForegroundColor Yellow
        Write-Host ('Time: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
        Write-Host ('Use .\test-before-commit.ps1 (without -SkipIntegration) to run full suite') -ForegroundColor Gray
    }
    Write-Host ('')

    # ===== 6. FINAL VALIDATION =====
    Write-Host ('[6/6] Final Validation') -ForegroundColor Cyan
    Write-Host ('Time: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
    $stepStart = Get-Date
    
    # Check git status
    Show-Progress ('Checking git repository status...')
    git status --porcelain > $null
    if ($LASTEXITCODE -eq 0) {
        Show-Complete "Git repository is accessible"
    }
    
    # Validate project structure one more time
    Show-Progress ('Final project structure validation...')
    $hasBackendBuild = Test-Path "backend/static"
    $hasFrontendBuild = Test-Path "frontend/build"
    
    if ($hasFrontendBuild) {
        Show-Complete "Frontend build artifacts present"
    }
    
    Show-Progress ('Checking test artifacts...')
    $hasCoverage = Test-Path "frontend/coverage"
    if ($hasCoverage) {
        Show-Complete "Test coverage reports generated"
    }
    
    $stepDuration = (Get-Date) - $stepStart
    Add-TestResult "Final Validation" "PASS" $stepDuration.TotalSeconds
    $durationStr = $stepDuration.TotalSeconds.ToString('F1')
    $message = "Final validation completed " + $durationStr + " seconds"
    Show-Complete $message
    Write-Host ('')
} catch {
    Write-Host ('[ERROR] Exception during tests: ' + $($_.Exception.Message)) -ForegroundColor Red
    Write-Host ('Stack trace:') -ForegroundColor Gray
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    $testsPassed = $false
}

# ===== RESULTS SUMMARY =====
$endTime = Get-Date
$totalDuration = $endTime - $startTime

Write-Host ('======================================') -ForegroundColor Magenta
Write-Host ('           TEST RESULTS SUMMARY       ') -ForegroundColor Magenta
Write-Host ('======================================') -ForegroundColor Magenta
Write-Host ('Completed at: ' + (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Gray
Write-Host ('')

foreach ($result in $testResults) {
    $statusColor = switch ($result.Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "SKIP" { "Yellow" }
        default { "Gray" }
    }
    $duration = if ($result.Duration -gt 0) { ($($result.Duration.ToString('F1')) + 's') } else { "0s" }
    Write-Host ('  ' + $($result.Test.PadRight(20)) + ' [' + $($result.Status) + '] (' + $duration + ')') -ForegroundColor $statusColor
    if ($result.Details) {
        Write-Host ('    ' + $($result.Details)) -ForegroundColor Gray
    }
}

Write-Host ('')
Write-Host ('Total Duration: ' + $($totalDuration.TotalMinutes.ToString('F1')) + ' minutes') -ForegroundColor Gray
Write-Host ('Tests Run: ' + $($testResults.Count)) -ForegroundColor Gray
$passedTests = ($testResults | Where-Object { $_.Status -eq "PASS" }).Count
$failedTests = ($testResults | Where-Object { $_.Status -eq "FAIL" }).Count
$skippedTests = ($testResults | Where-Object { $_.Status -eq "SKIP" }).Count
Write-Host ('Passed: ' + $passedTests + ' | Failed: ' + $failedTests + ' | Skipped: ' + $skippedTests) -ForegroundColor Gray
Write-Host ('')

if ($testsPassed) {
    Write-Host ('SUCCESS: All tests passed! Ready to commit.') -ForegroundColor Green
    Write-Host ('Your code meets the same standards as GitHub Actions.') -ForegroundColor Green
    Write-Host ('[SAVED] You just saved GitHub Actions minutes!') -ForegroundColor Yellow
    exit 0
} else {
    Write-Host ('FAILURE: Some tests failed!') -ForegroundColor Red
    Write-Host ('')
    if ($Force) {
        Write-Host ('Forcing commit despite failures...') -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host ('Commit blocked. Options: ') -ForegroundColor Red
        Write-Host ('  git commit --no-verify           (skip all hooks)') -ForegroundColor Gray
        Write-Host ('test-before-commit.ps1 -Force  (force through)') -ForegroundColor Gray
        Write-Host ('  test-before-commit.ps1 -SkipIntegration  (skip integration tests)') -ForegroundColor Gray
        exit 1
    }
} 