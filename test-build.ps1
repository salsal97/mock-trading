# Test Build Script for Mock Trading App
Write-Host "🧪 Testing Mock Trading App build process..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "frontend/package.json")) {
    Write-Host "❌ Error: frontend/package.json not found. Run this from project root." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "backend/manage.py")) {
    Write-Host "❌ Error: backend/manage.py not found. Run this from project root." -ForegroundColor Red
    exit 1
}

Write-Host "`n📁 Current directory structure:" -ForegroundColor Yellow
Get-ChildItem -Directory | Select-Object Name

# Test 1: Frontend build
Write-Host "`n📦 Testing frontend build..." -ForegroundColor Yellow
cd frontend

Write-Host "Installing dependencies..." -ForegroundColor Gray
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend npm install failed" -ForegroundColor Red
    exit 1
}

Write-Host "Building React app..." -ForegroundColor Gray
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Frontend build successful!" -ForegroundColor Green
cd ..

# Test 2: Manual file copy (Windows)
Write-Host "`n🛠️ Testing file copying process..." -ForegroundColor Yellow

# Create directories
Write-Host "Creating required directories..." -ForegroundColor Gray
New-Item -ItemType Directory -Path "backend/static" -Force | Out-Null
New-Item -ItemType Directory -Path "backend/templates" -Force | Out-Null
New-Item -ItemType Directory -Path "backend/staticfiles" -Force | Out-Null

# Copy React build files
if (Test-Path "frontend/build") {
    Write-Host "Copying React build files..." -ForegroundColor Gray
    Copy-Item -Path "frontend/build/index.html" -Destination "backend/templates/" -Force
    if (Test-Path "frontend/build/static") {
        Copy-Item -Path "frontend/build/static/*" -Destination "backend/static/" -Recurse -Force
    }
    Copy-Item -Path "frontend/build/*" -Destination "backend/staticfiles/" -Recurse -Force
    Write-Host "✅ Files copied successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ frontend/build directory not found" -ForegroundColor Red
    exit 1
}

# Test 3: Django setup
Write-Host "`n🐍 Testing Django setup..." -ForegroundColor Yellow
cd backend

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Gray
& "venv\Scripts\Activate.ps1"

# Install requirements
Write-Host "Installing Django dependencies..." -ForegroundColor Gray
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Django requirements install failed" -ForegroundColor Red
    exit 1
}

# Test Django configuration
Write-Host "Testing Django configuration..." -ForegroundColor Gray
python manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Django configuration check failed" -ForegroundColor Red
    exit 1
}

# Test collectstatic
Write-Host "Testing collectstatic..." -ForegroundColor Gray
python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Collectstatic failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Django setup successful!" -ForegroundColor Green
cd ..

# Test 4: Verify file structure
Write-Host "`n📁 Verifying deployment file structure..." -ForegroundColor Yellow

$requiredFiles = @(
    "backend/templates/index.html",
    "backend/static",
    "backend/staticfiles",
    ".github/workflows/azure-deploy.yml",
    "backend/startup.sh",
    "build-frontend.sh"
)

$allFilesExist = $true
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file missing" -ForegroundColor Red
        $allFilesExist = $false
    }
}

# Test 5: GitHub Actions workflow validation
Write-Host "`n🔍 Validating GitHub Actions workflow..." -ForegroundColor Yellow
$workflowContent = Get-Content ".github/workflows/azure-deploy.yml" -Raw
if ($workflowContent -match "salonis-mock-trading-app") {
    Write-Host "✅ App name configured correctly in workflow" -ForegroundColor Green
} else {
    Write-Host "❌ App name not configured in workflow" -ForegroundColor Red
    $allFilesExist = $false
}

# Final results
$separator = "=" * 60
Write-Host "`n$separator" -ForegroundColor Cyan

if ($allFilesExist) {
    Write-Host "🎉 ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "✅ Ready for Azure deployment!" -ForegroundColor Green
    
    Write-Host "`n📋 Next steps:" -ForegroundColor Yellow
    Write-Host "1. Download publish profile from Azure Portal:" -ForegroundColor White
    Write-Host "   https://portal.azure.com → salonis-mock-trading-app → Deployment Center" -ForegroundColor Gray
    Write-Host "2. Add publish profile to GitHub Secrets as 'AZURE_WEBAPP_PUBLISH_PROFILE'" -ForegroundColor White
    Write-Host "3. Run: git commit -m 'Setup Azure deployment'" -ForegroundColor White
    Write-Host "4. Run: git push origin main (or current branch)" -ForegroundColor White
    Write-Host "5. Watch GitHub Actions deploy your app! 🚀" -ForegroundColor White
    
    Write-Host "`n🌐 Your app will be live at:" -ForegroundColor Cyan
    Write-Host "https://salonis-mock-trading-app.azurewebsites.net" -ForegroundColor Cyan
} else {
    Write-Host "❌ SOME TESTS FAILED!" -ForegroundColor Red
    Write-Host "Please fix the issues above before deploying." -ForegroundColor Red
}

Write-Host $separator -ForegroundColor Cyan 