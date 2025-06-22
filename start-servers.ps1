# Start both servers and apply migrations
Write-Host "Starting Mock Trading Application..." -ForegroundColor Green

# Get the script's directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load environment variables (only in local development)
if (Test-Path (Join-Path $scriptPath "setup-env.ps1")) {
    Write-Host "Loading local development environment variables..." -ForegroundColor Yellow
    & (Join-Path $scriptPath "setup-env.ps1")
} else {
    Write-Host "No local environment setup found - using system environment variables" -ForegroundColor Gray
}

# Function to check if a command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Check if Python is installed
if (-not (Test-Command python)) {
    Write-Host "Python is not installed or not in PATH. Please install Python." -ForegroundColor Red
    exit 1
}

# Check if Node.js is installed
if (-not (Test-Command node)) {
    Write-Host "Node.js is not installed or not in PATH. Please install Node.js." -ForegroundColor Red
    exit 1
}

# Set paths
$backendPath = Join-Path $scriptPath "backend"
$frontendPath = Join-Path $scriptPath "frontend"
$venvPath = Join-Path $backendPath "venv"

# Install backend dependencies
Write-Host "`nInstalling Backend Dependencies..." -ForegroundColor Yellow
Set-Location $backendPath

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment and install requirements
& "$venvPath\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
# Write-Host "`nInstalling Frontend Dependencies..." -ForegroundColor Yellow
# Set-Location ..\frontend
# npm install

# Return to root directory
Set-Location ..

# Start backend server
Write-Host "`nStarting Backend Server..." -ForegroundColor Yellow
$backendCommand = "cd '$backendPath'; & '$venvPath\Scripts\Activate.ps1'; python manage.py migrate; python manage.py runserver"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand

# Wait a moment for the backend to start
Start-Sleep -Seconds 5

# Start frontend server
Write-Host "`nStarting Frontend Server..." -ForegroundColor Yellow
$frontendCommand = "cd '$frontendPath'; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand

Write-Host "`nServers are starting..." -ForegroundColor Green
Write-Host "Backend will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend will be available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C in each terminal window to stop the servers" -ForegroundColor Yellow 