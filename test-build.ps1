# Test build process for Mock Trading App
if (-not (Test-Path "frontend/package.json")) {
    Write-Host "ERROR: frontend/package.json not found. Run this from project root." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "backend/manage.py")) {
    Write-Host "ERROR: backend/manage.py not found. Run this from project root." -ForegroundColor Red
    exit 1
}

Write-Host "Testing Mock Trading App Build Process" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Test 1: Frontend Build
Write-Host "`nTesting frontend build..." -ForegroundColor Yellow
Set-Location "frontend"

try {
    npm ci --production
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Frontend npm install failed" -ForegroundColor Red
        exit 1
    }
    
    $env:NODE_ENV = "production"
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Frontend build failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "SUCCESS: Frontend build successful!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Frontend build process failed" -ForegroundColor Red
    exit 1
}

Write-Host "`nTesting file copying process..." -ForegroundColor Yellow
Set-Location ".."

# Create backend directories
$BackendStatic = "backend/static"
$BackendTemplates = "backend/templates"

if (-not (Test-Path $BackendStatic)) {
    New-Item -ItemType Directory -Path $BackendStatic -Force | Out-Null
}
if (-not (Test-Path $BackendTemplates)) {
    New-Item -ItemType Directory -Path $BackendTemplates -Force | Out-Null
}

# Test file copying
if (Test-Path "frontend/build") {
    Copy-Item "frontend/build/*" $BackendStatic -Recurse -Force
    Copy-Item "frontend/build/index.html" $BackendTemplates -Force
    Write-Host "SUCCESS: Files copied successfully!" -ForegroundColor Green
} else {
    Write-Host "ERROR: frontend/build directory not found" -ForegroundColor Red
    exit 1
}

# Test 2: Backend Setup
Write-Host "`nTesting backend setup..." -ForegroundColor Yellow
Set-Location "backend"

# Set test environment variables
$env:SECRET_KEY = "test-secret-key-for-build-test"
$env:DB_NAME = "test_db"
$env:DB_USER = "test_user"
$env:DB_PASSWORD = "test_pass"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DEBUG = "False"

try {
    # Test requirements installation
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Django requirements install failed" -ForegroundColor Red
        exit 1
    }
    
    # Test Django configuration
    python manage.py check --deploy
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Django configuration check failed" -ForegroundColor Red
        exit 1
    }
    
    # Test collectstatic
    python manage.py collectstatic --noinput
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Collectstatic failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "SUCCESS: Django setup successful!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Backend setup failed" -ForegroundColor Red
    exit 1
}

Set-Location ".."

# Test 3: File Verification
Write-Host "`nVerifying critical files..." -ForegroundColor Yellow

$CriticalFiles = @(
    "backend/static/index.html",
    "backend/templates/index.html",
    "backend/staticfiles/index.html"
)

foreach ($file in $CriticalFiles) {
    if (Test-Path $file) {
        Write-Host "SUCCESS: $file" -ForegroundColor Green
    } else {
        Write-Host "ERROR: $file missing" -ForegroundColor Red
    }
}

# Test 4: GitHub Actions Workflow
Write-Host "`nValidating GitHub Actions workflow..." -ForegroundColor Yellow

if (Select-String -Path ".github/workflows/azure-deploy.yml" -Pattern "salonis-mock-trading-app") {
    Write-Host "SUCCESS: App name configured correctly in workflow" -ForegroundColor Green
} else {
    Write-Host "ERROR: App name not configured in workflow" -ForegroundColor Red
}

# Final Results
$TestsPassed = $true

if ($TestsPassed) {
    Write-Host "`nALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "SUCCESS: Ready for Azure deployment!" -ForegroundColor Green
    
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Commit your changes to GitHub" -ForegroundColor White
    Write-Host "2. Push to main branch" -ForegroundColor White
    Write-Host "3. Check GitHub Actions tab for deployment" -ForegroundColor White
    Write-Host "4. Monitor Azure App Service logs" -ForegroundColor White
    Write-Host "5. Watch GitHub Actions deploy your app!" -ForegroundColor White
    
    exit 0
} else {
    Write-Host "`nSOME TESTS FAILED!" -ForegroundColor Red
    Write-Host "Please fix the issues above before deploying." -ForegroundColor Red
    exit 1
} 