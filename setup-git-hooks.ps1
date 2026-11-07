# Install a local hook that runs the isolated checks.
$hooks = Join-Path (git rev-parse --git-dir) 'hooks'
if ($LASTEXITCODE -ne 0) { throw 'Not in a Git repository' }
New-Item -ItemType Directory -Force -Path $hooks | Out-Null
$hook = "#!/bin/sh`npowershell.exe -NoProfile -ExecutionPolicy Bypass -File ./test-before-commit.ps1`nexit `$?`n"
[IO.File]::WriteAllText((Join-Path $hooks 'pre-commit'), $hook, [Text.UTF8Encoding]::new($false))
Write-Host 'Installed pre-commit hook for isolated checks.'
