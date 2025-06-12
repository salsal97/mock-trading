# Start both servers and apply migrations
Write-Host "Starting Mock Trading Application..." -ForegroundColor Green

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

# Install backend dependencies
Write-Host "`nInstalling Backend Dependencies..." -ForegroundColor Yellow
Set-Location backend
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
Write-Host "`nInstalling Frontend Dependencies..." -ForegroundColor Yellow
Set-Location ..\frontend
npm install

# Return to root directory
Set-Location ..

# Start backend server
Write-Host "`nStarting Backend Server..." -ForegroundColor Yellow
$backendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; python manage.py migrate; python manage.py runserver" -PassThru

# Wait a moment for the backend to start
Start-Sleep -Seconds 5

# Start frontend server
Write-Host "`nStarting Frontend Server..." -ForegroundColor Yellow
$frontendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm start" -PassThru

Write-Host "`nServers are starting..." -ForegroundColor Green
Write-Host "Backend will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend will be available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C in each terminal window to stop the servers" -ForegroundColor Yellow 