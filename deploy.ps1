#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Mock Trading App to Azure
.DESCRIPTION
    This script builds the frontend, copies files, and deploys to Azure App Service
.PARAMETER ResourceGroup
    Azure resource group name (default: mock-trading-rg)
.PARAMETER AppName
    Azure app service name (default: salonis-mock-trading-app)
.PARAMETER SkipBuild
    Skip frontend build step
#>

param(
    [string]$ResourceGroup = "mock-trading-rg",
    [string]$AppName = "salonis-mock-trading-app",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting deployment process..." -ForegroundColor Green

# Get script directory (project root)
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "📁 Project root: $ProjectRoot" -ForegroundColor Blue

# Step 1: Build frontend (unless skipped)
if (-not $SkipBuild) {
    Write-Host "🔨 Building frontend..." -ForegroundColor Yellow
    Set-Location "frontend"
    
    # Clean old build
    if (Test-Path "build") {
        Remove-Item -Recurse -Force "build"
        Write-Host "   Cleaned old build directory" -ForegroundColor Gray
    }
    
    # Build new version
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed"
    }
    Write-Host "   ✅ Frontend build completed" -ForegroundColor Green
    
    Set-Location $ProjectRoot
} else {
    Write-Host "⏭️  Skipping frontend build" -ForegroundColor Yellow
}

# Step 2: Copy frontend build to backend static
Write-Host "📋 Copying frontend build to backend..." -ForegroundColor Yellow
$FrontendBuild = Join-Path $ProjectRoot "frontend" "build"
$BackendStatic = Join-Path $ProjectRoot "backend" "static"

if (Test-Path $FrontendBuild) {
    # Ensure backend static directory exists
    if (-not (Test-Path $BackendStatic)) {
        New-Item -ItemType Directory -Path $BackendStatic -Force | Out-Null
    }
    
    # Copy all files from build to static
    Copy-Item -Path "$FrontendBuild\*" -Destination $BackendStatic -Recurse -Force
    Write-Host "   ✅ Frontend files copied to backend/static" -ForegroundColor Green
} else {
    throw "Frontend build directory not found. Run with -SkipBuild:$false to build first."
}

# Step 3: Collect Django static files
Write-Host "📦 Collecting Django static files..." -ForegroundColor Yellow
Set-Location "backend"

# Set required environment variables for collectstatic
$env:SECRET_KEY = "django-insecure-deployment-key-for-collectstatic-only"
$env:DB_NAME = "dummy"
$env:DB_USER = "dummy"
$env:DB_PASSWORD = "dummy"
$env:DB_HOST = "dummy"
$env:DB_PORT = "5432"

python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) {
    throw "Django collectstatic failed"
}
Write-Host "   ✅ Django static files collected" -ForegroundColor Green

Set-Location $ProjectRoot

# Step 4: Create deployment package
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow
$DeploymentZip = "deployment.zip"

if (Test-Path $DeploymentZip) {
    Remove-Item $DeploymentZip -Force
}

# Create zip with backend files
Compress-Archive -Path "backend\*" -DestinationPath $DeploymentZip -Force
Write-Host "   ✅ Deployment package created: $DeploymentZip" -ForegroundColor Green

# Step 5: Deploy to Azure
Write-Host "☁️  Deploying to Azure..." -ForegroundColor Yellow
Write-Host "   Resource Group: $ResourceGroup" -ForegroundColor Gray
Write-Host "   App Service: $AppName" -ForegroundColor Gray

try {
    az webapp deployment source config-zip --resource-group $ResourceGroup --name $AppName --src $DeploymentZip
    if ($LASTEXITCODE -ne 0) {
        throw "Azure deployment failed"
    }
    Write-Host "   ✅ Deployed to Azure successfully" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Azure deployment failed: $_" -ForegroundColor Red
    throw
}

# Step 6: Restart app service
Write-Host "🔄 Restarting app service..." -ForegroundColor Yellow
az webapp restart --resource-group $ResourceGroup --name $AppName
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ⚠️  App restart failed, but deployment may still work" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ App service restarted" -ForegroundColor Green
}

# Step 7: Clean up
Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
if (Test-Path $DeploymentZip) {
    Remove-Item $DeploymentZip -Force
    Write-Host "   ✅ Deployment package cleaned up" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host "🌐 Your app should be available at: https://$AppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Test the registration functionality" -ForegroundColor Gray
Write-Host "   2. Check Azure logs if there are issues: az webapp log tail --resource-group $ResourceGroup --name $AppName" -ForegroundColor Gray
Write-Host "   3. Monitor the app: https://$AppName.scm.azurewebsites.net" -ForegroundColor Gray 