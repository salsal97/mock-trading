# Mock Trading App - Azure Deployment Script
# This script builds the frontend, integrates with Django, and deploys to Azure

param(
    [string]$ResourceGroup = "mock-trading-rg",
    [string]$AppName = "salonis-mock-trading-app",
    [string]$Location = "East US",
    [switch]$SkipBuild = $false,
    [switch]$LocalOnly = $false
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output
$Green = "Green"
$Yellow = "Yellow" 
$Red = "Red"
$White = "White"

try {
    Write-Host "Starting deployment process..." -ForegroundColor $Green
    Write-Host "Resource Group: $ResourceGroup" -ForegroundColor $White
    Write-Host "App Name: $AppName" -ForegroundColor $White
    Write-Host "Location: $Location" -ForegroundColor $White
    
    # Get current directory
    $ProjectRoot = Get-Location
    
    # Step 1: Build Frontend (unless skipped)
    if (-not $SkipBuild) {
        Write-Host "Building frontend..." -ForegroundColor $Yellow
        
        # Check if frontend directory exists
        if (-not (Test-Path "frontend")) {
            throw "Frontend directory not found. Make sure you're in the project root."
        }
        
        # Navigate to frontend and build
        Set-Location "frontend"
        
        # Install dependencies and build
        npm ci --production
        $env:NODE_ENV = "production"
        npm run build
        
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed"
        }
        
        Write-Host "   Frontend build completed" -ForegroundColor $Green
        Set-Location $ProjectRoot
    } else {
        Write-Host "Skipping frontend build" -ForegroundColor $Yellow
    }
    
    # Step 2: Copy frontend build to backend
    Write-Host "Copying frontend build to backend..." -ForegroundColor $Yellow
    
    # Create backend static directories
    $BackendStatic = "backend/static"
    $BackendTemplates = "backend/templates"
    
    if (-not (Test-Path $BackendStatic)) {
        New-Item -ItemType Directory -Path $BackendStatic -Force | Out-Null
    }
    if (-not (Test-Path $BackendTemplates)) {
        New-Item -ItemType Directory -Path $BackendTemplates -Force | Out-Null
    }
    
    # Clean previous builds
    Remove-Item "$BackendStatic/*" -Recurse -Force -ErrorAction SilentlyContinue
    
    # Copy React build files
    Copy-Item "frontend/build/*" $BackendStatic -Recurse -Force
    Copy-Item "frontend/build/index.html" $BackendTemplates -Force
    
    Write-Host "   Frontend files copied to backend/static" -ForegroundColor $Green
    
    # Step 3: Collect Django static files
    Write-Host "Collecting Django static files..." -ForegroundColor $Yellow
    
    Set-Location "backend"
    
    # Set environment variables for collectstatic
    $env:SECRET_KEY = "temp-secret-for-collectstatic"
    $env:DB_NAME = "temp"
    $env:DB_USER = "temp"
    $env:DB_PASSWORD = "temp"
    $env:DB_HOST = "temp"
    $env:DEBUG = "False"
    
    # Run collectstatic
    python manage.py collectstatic --noinput
    
    if ($LASTEXITCODE -ne 0) {
        throw "Django collectstatic failed"
    }
    
    Write-Host "   Django static files collected" -ForegroundColor $Green
    Set-Location $ProjectRoot
    
    # Step 4: Create deployment package
    Write-Host "Creating deployment package..." -ForegroundColor $Yellow
    
    $DeploymentZip = "deployment-package.zip"
    
    # Remove existing package
    if (Test-Path $DeploymentZip) {
        Remove-Item $DeploymentZip -Force
    }
    
    # Create zip package (excluding unnecessary files)
    $FilesToExclude = @("node_modules", ".git", "frontend/build", "*.zip", "__pycache__", "*.pyc")
    
    # Use PowerShell compression
    Compress-Archive -Path "backend/*" -DestinationPath $DeploymentZip -Force
    
    Write-Host "   Deployment package created: $DeploymentZip" -ForegroundColor $Green
    
    # Step 5: Deploy to Azure (unless LocalOnly)
    if (-not $LocalOnly) {
        Write-Host "Deploying to Azure..." -ForegroundColor $Yellow
        
        # Deploy using Azure CLI
        try {
            az webapp deployment source config-zip --resource-group $ResourceGroup --name $AppName --src $DeploymentZip
            
            if ($LASTEXITCODE -ne 0) {
                throw "Azure deployment command failed"
            }
            
            Write-Host "   Deployed to Azure successfully" -ForegroundColor $Green
        } catch {
            Write-Host "   Azure deployment failed: $_" -ForegroundColor $Red
            throw
        }
        
        # Step 6: Restart the app service
        Write-Host "Restarting app service..." -ForegroundColor $Yellow
        try {
            az webapp restart --resource-group $ResourceGroup --name $AppName
        } catch {
            Write-Host "   App restart failed, but deployment may still work" -ForegroundColor $Yellow
        } else {
            Write-Host "   App service restarted" -ForegroundColor $Green
        }
    }
    
    # Step 7: Cleanup
    if (Test-Path $DeploymentZip) {
        Remove-Item $DeploymentZip -Force
        Write-Host "   Deployment package cleaned up" -ForegroundColor $Green
    }
    
    # Success message
    Write-Host "Deployment completed successfully!" -ForegroundColor $Green
    Write-Host "Your app should be available at: https://$AppName.azurewebsites.net" -ForegroundColor $White
    
    Write-Host "Next steps:" -ForegroundColor $Yellow
    Write-Host "1. Check the Azure portal for deployment status" -ForegroundColor $White
    Write-Host "2. Monitor application logs for any issues" -ForegroundColor $White
    Write-Host "3. Test the application functionality" -ForegroundColor $White
    Write-Host "4. Set up custom domain if needed" -ForegroundColor $White
    
} catch {
    Write-Host "Deployment failed: $_" -ForegroundColor $Red
    exit 1
} finally {
    # Always return to project root
    Set-Location $ProjectRoot
} 