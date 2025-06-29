# Pre-commit Test Script for Mock Trading Application
# Ultra-fast version - runs only critical syntax and structure checks

param(
    [switch]$Force
)

Write-Host "Pre-Commit Quality Checks" -ForegroundColor Green
Write-Host "Running ultra-fast essential checks..." -ForegroundColor Yellow

$testsPassed = $true
$startTime = Get-Date

try {
    # 1. Basic file structure checks
    Write-Host "`nStructure checks..." -ForegroundColor Cyan
    
    $hasPackageJson = Test-Path "frontend/package.json"
    $hasManagePy = Test-Path "backend/manage.py"
    $hasGitignore = Test-Path ".gitignore"
    
    if ($hasPackageJson -and $hasManagePy -and $hasGitignore) {
        Write-Host "  [OK] Project structure OK" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Missing critical files" -ForegroundColor Red
        $testsPassed = $false
    }
    
    # 2. Frontend - Quick syntax check only
    Write-Host "`nFrontend syntax..." -ForegroundColor Cyan
    Set-Location frontend
    
    # Check if package.json is valid JSON
    try {
        $packageJson = Get-Content "package.json" | ConvertFrom-Json
        Write-Host "  [OK] package.json valid" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] package.json invalid" -ForegroundColor Red
        $testsPassed = $false
    }
    
    Set-Location ..
    
    # 3. Backend - Quick Django check only
    Write-Host "`nBackend syntax..." -ForegroundColor Cyan
    Set-Location backend
    
    if (Test-Path "venv\Scripts\activate.ps1") {
        & "venv\Scripts\activate.ps1" 2>$null
        
        # Ultra-quick Django check
        python -c "import django; print('Django import OK')" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Django imports OK" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Django import failed" -ForegroundColor Red
            $testsPassed = $false
        }
    } else {
        Write-Host "  [SKIP] Backend venv not found - skipping" -ForegroundColor Yellow
    }
    
    Set-Location ..
    
    # 4. Git status check
    Write-Host "`nGit checks..." -ForegroundColor Cyan
    
    # Check if we're in a git repo and have staged changes
    $gitStatus = git status --porcelain 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Git repository OK" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Git repository issue" -ForegroundColor Red
        $testsPassed = $false
    }
    
} catch {
    Write-Host "[ERROR] Error during checks: $($_.Exception.Message)" -ForegroundColor Red
    $testsPassed = $false
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "`n" -NoNewline
if ($testsPassed) {
    Write-Host "All Checks Passed!" -ForegroundColor Green
    Write-Host "Duration: $($duration.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Gray
    Write-Host "Ready to commit!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Checks Failed!" -ForegroundColor Red
    Write-Host "Duration: $($duration.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Gray
    
    if ($Force) {
        Write-Host "Forcing commit despite failures..." -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "Commit blocked. Options:" -ForegroundColor Red
        Write-Host "   git commit --no-verify    (skip hook)" -ForegroundColor Gray
        Write-Host "   .\test-before-commit.ps1 -Force    (force through)" -ForegroundColor Gray
        exit 1
    }
} 