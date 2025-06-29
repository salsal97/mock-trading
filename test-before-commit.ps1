# Pre-commit Test Script for Mock Trading Application
# Run this before committing to ensure code quality

param(
    [switch]$Quick,
    [switch]$Force
)

Write-Host "🔍 Pre-Commit Test Suite" -ForegroundColor Green
Write-Host "Ensuring code quality before commit..." -ForegroundColor Yellow

# Set up environment
if (Test-Path "setup-env.ps1") {
    & ".\setup-env.ps1"
}

$testsPassed = $true
$startTime = Get-Date

# Quick tests (essential only)
if ($Quick) {
    Write-Host "`n⚡ Running Quick Tests..." -ForegroundColor Cyan
    
    # Frontend tests only
    Write-Host "Testing frontend..."
    Set-Location frontend
    npm test -- --watchAll=false --testTimeout=10000 --silent
    if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
    Set-Location ..
    
    # Backend model tests only
    Write-Host "Testing backend models..."
    Set-Location backend
    if (Test-Path "venv\Scripts\activate.ps1") {
        & "venv\Scripts\activate.ps1"
        python manage.py test market.tests.MarketTestCase.test_no_bids_delay_property --verbosity=1
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
    }
    Set-Location ..
    
} else {
    Write-Host "`n🧪 Running Comprehensive Tests..." -ForegroundColor Cyan
    
    # Frontend tests with coverage
    Write-Host "`n⚛️ Frontend Tests..."
    Set-Location frontend
    npm test -- --coverage --watchAll=false --testTimeout=30000
    if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
    Set-Location ..
    
    # Backend Django tests
    Write-Host "`n🐍 Backend Tests..."
    Set-Location backend
    if (Test-Path "venv\Scripts\activate.ps1") {
        & "venv\Scripts\activate.ps1"
        python manage.py test --verbosity=2
        if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
    }
    Set-Location ..
    
    # Business rules tests
    Write-Host "`n🎯 Business Rules Tests..."
    if (-not $env:SECRET_KEY) {
        $env:SECRET_KEY = "test-secret-key-for-pre-commit-only"
        Write-Host "⚠️  Using temporary SECRET_KEY for testing" -ForegroundColor Yellow
    }
    $env:DEBUG = "True"
    python test_business_rules.py
    if ($LASTEXITCODE -ne 0) { $testsPassed = $false }
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "`n" -NoNewline
if ($testsPassed) {
    Write-Host "✅ All Pre-Commit Tests Passed!" -ForegroundColor Green
    Write-Host "Duration: $($duration.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Gray
    Write-Host "🚀 Ready to commit!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Pre-Commit Tests Failed!" -ForegroundColor Red
    Write-Host "Duration: $($duration.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Gray
    
    if ($Force) {
        Write-Host "⚠️ Forcing commit despite test failures..." -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "🚫 Commit blocked. Fix tests or use -Force to override." -ForegroundColor Red
        Write-Host "💡 Run 'git commit --no-verify' to skip this check." -ForegroundColor Gray
        exit 1
    }
} 