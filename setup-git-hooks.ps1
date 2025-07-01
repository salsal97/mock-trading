# Setup Git Hooks for Mock Trading Application
# Configures comprehensive testing locally to save GitHub Actions costs

Write-Host "Setting up comprehensive Git hooks for Mock Trading Application..." -ForegroundColor Green
Write-Host "This will run the same tests as GitHub Actions locally to save CI/CD costs!" -ForegroundColor Yellow

# Check if .git directory exists
if (-not (Test-Path ".git")) {
    Write-Host "Error: Not in a Git repository!" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Yellow
    exit 1
}

# Create hooks directory if it doesn't exist
$hooksDir = ".git/hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

# Create comprehensive pre-commit hook (PowerShell)
$preCommitHook = @"
# Git pre-commit hook for Mock Trading Application (PowerShell)
# Runs comprehensive tests locally to save CI/CD costs and catch issues early

Write-Host "Running comprehensive pre-commit test suite..." -ForegroundColor Cyan
Write-Host "This mirrors GitHub Actions to save CI/CD costs" -ForegroundColor Gray
Write-Host ""

try {
    # Run comprehensive test suite (skip integration tests for speed)
    `$result = & powershell.exe -ExecutionPolicy Bypass -File "./test-before-commit.ps1" -SkipIntegration
    `$exitCode = `$LASTEXITCODE
    
    if (`$exitCode -eq 0) {
        Write-Host ""
        Write-Host "Pre-commit tests passed! Proceeding with commit..." -ForegroundColor Green
        Write-Host "Your code meets GitHub Actions standards locally." -ForegroundColor Green
        exit 0
    } else {
        Write-Host ""
        Write-Host "Pre-commit tests failed!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Options to proceed:" -ForegroundColor Yellow
        Write-Host "  git commit --no-verify                    (skip all hooks)" -ForegroundColor Gray
        Write-Host "  .\test-before-commit.ps1 -Force           (force through)" -ForegroundColor Gray
        Write-Host "  .\test-before-commit.ps1                  (run with integration tests)" -ForegroundColor Gray
        exit 1
    }
} catch {
    Write-Host "Error running pre-commit tests: `$(`$_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run tests manually: .\test-before-commit.ps1" -ForegroundColor Yellow
    exit 1
}
"@

# Write the hook file
$hookPath = "$hooksDir/pre-commit"
$preCommitHook | Out-File -FilePath $hookPath -Encoding UTF8

# Set file attributes for Git hook (PowerShell method)
try {
    # Git on Windows will recognize .ps1 files as PowerShell hooks
    $hookPathPs1 = "$hooksDir/pre-commit.ps1"
    $preCommitHook | Out-File -FilePath $hookPathPs1 -Encoding UTF8
    
    # Also create the standard hook file that calls PowerShell
    $hookWrapper = @"
#!/bin/sh
# Git pre-commit hook wrapper - calls PowerShell script
powershell.exe -ExecutionPolicy Bypass -File ".git/hooks/pre-commit.ps1"
"@
    $hookWrapper | Out-File -FilePath $hookPath -Encoding UTF8
    
    Write-Host "Comprehensive pre-commit hook created successfully!" -ForegroundColor Green
} catch {
    Write-Host "Error creating hook: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Basic hook created - may need manual configuration." -ForegroundColor Green
}

Write-Host ""
Write-Host "Git Hook Configuration Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "What happens now:" -ForegroundColor Cyan
Write-Host "- Before each commit, Git will run comprehensive tests locally" -ForegroundColor White
Write-Host "- Tests: Backend Django + Frontend React + Business Rules" -ForegroundColor White
Write-Host "- Same tests as GitHub Actions (saves CI/CD costs!)" -ForegroundColor Green
Write-Host "- Integration tests skipped by default for speed" -ForegroundColor White
Write-Host "- If tests pass: commit proceeds normally" -ForegroundColor Green
Write-Host "- If tests fail: commit is blocked" -ForegroundColor Red
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  git commit -m 'message'                      # Normal commit (runs tests)" -ForegroundColor White
Write-Host "  git commit --no-verify                       # Skip hook (when needed)" -ForegroundColor White
Write-Host "  .\test-before-commit.ps1                     # Manual full test run" -ForegroundColor White
Write-Host "  .\test-before-commit.ps1 -SkipIntegration    # Manual test run (faster)" -ForegroundColor White
Write-Host ""
Write-Host "Benefits:" -ForegroundColor Green
Write-Host "- Saves GitHub Actions minutes and costs" -ForegroundColor White
Write-Host "- Catches issues before pushing to remote" -ForegroundColor White
Write-Host "- Ensures code quality matches CI/CD standards" -ForegroundColor White
Write-Host ""
Write-Host "To test the hook, try making a commit now!" -ForegroundColor Gray