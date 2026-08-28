# stop-fcc-server.ps1
$InstallDir = "fcc-main"
$PidFile = Join-Path $InstallDir 'fcc-server.pid'
if (-not (Test-Path $PidFile)) { Write-Host "No PID file found at $PidFile"; exit 1 }
$pid = Get-Content $PidFile -ErrorAction SilentlyContinue
if (-not $pid) { Write-Host "PID file empty"; exit 1 }
try {
  Stop-Process -Id [int]$pid -Force -ErrorAction Stop
  Remove-Item $PidFile -ErrorAction SilentlyContinue
  Write-Host "Stopped process $pid"
} catch {
  Write-Host "Failed to stop process $pid: $($_.Exception.Message)"
  exit 2
}

