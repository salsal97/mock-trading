# Setup Git Hooks for Mock Trading Application
# This script configures Git to automatically run fast quality checks before commits

Write-Host "🔧 Setting up Git hooks for Mock Trading Application..." -ForegroundColor Green

# Check if .git directory exists
if (-not (Test-Path ".git")) {
    Write-Host "❌ Error: Not in a Git repository!" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Yellow
    exit 1
}

# Create hooks directory if it doesn't exist
$hooksDir = ".git/hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

# Create pre-commit hook (PowerShell)
$preCommitHook = @"
# Git pre-commit hook for Mock Trading Application (PowerShell)
# This hook runs fast quality checks before each commit

Write-Host "🔍 Running pre-commit quality checks..." -ForegroundColor Cyan

try {
    # Run the simplified pre-commit checks
    `$result = & powershell.exe -ExecutionPolicy Bypass -File "./test-before-commit.ps1"
    `$exitCode = `$LASTEXITCODE
    
    if (`$exitCode -eq 0) {
        Write-Host "✅ Pre-commit checks passed! Proceeding with commit..." -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ Pre-commit checks failed!" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 To skip this check: git commit --no-verify" -ForegroundColor Yellow
        Write-Host "💡 To force through: git commit --no-verify" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "⚠️  Error running pre-commit checks: `$(`$_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Please run checks manually: .\test-before-commit.ps1" -ForegroundColor Yellow
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
    
    Write-Host "✅ PowerShell pre-commit hook created successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Error creating hook: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "✅ Basic hook created - may need manual configuration." -ForegroundColor Green
}

Write-Host ""
Write-Host "🎯 Git Hook Configuration Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "What happens now:" -ForegroundColor Cyan
Write-Host "- Before each commit, Git will run fast quality checks (~3-5 seconds)" -ForegroundColor White
Write-Host "- Checks: Frontend build + critical test + Django system check" -ForegroundColor White
Write-Host "- If checks pass: commit proceeds normally" -ForegroundColor Green
Write-Host "- If checks fail: commit is blocked" -ForegroundColor Red
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  git commit -m 'message'     # Normal commit (runs checks)" -ForegroundColor White
Write-Host "  git commit --no-verify      # Skip hook (when needed)" -ForegroundColor White
Write-Host "  .\test-before-commit.ps1    # Manual check run" -ForegroundColor White
Write-Host ""
Write-Host "💡 To test the hook, try making a commit now!" -ForegroundColor Gray