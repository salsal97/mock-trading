$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
    $python = if (Test-Path '.venv/Scripts/python.exe') { '.venv/Scripts/python.exe' } else { 'python' }
    & $python backend/manage.py makemigrations --check --dry-run --settings=mock_trading.test_settings
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python backend/manage.py test accounts market --settings=mock_trading.test_settings
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Push-Location frontend
    try {
        $env:CI = 'true'
        npm test -- --watchAll=false --runInBand
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $env:CI = 'false'
        npm run build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally { Pop-Location }
} finally { Pop-Location }
