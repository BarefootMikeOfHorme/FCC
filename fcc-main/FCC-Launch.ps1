# FCC-Launch.ps1
# Usage: run with pwsh -NoProfile -ExecutionPolicy Bypass -File .\FCC-Launch.ps1
$ErrorActionPreference = 'Stop'
# --- uv version check (inserted) ---
try {
  $uvver = $null
  try { $uvver = (& uv --version 2>$null) -replace 'uv\s+','' } catch {}
  if (-not $uvver) {
    $venvUv = Join-Path $PSScriptRoot '.venv\Scripts\uv.exe'
    if (Test-Path $venvUv) { $uvver = (& $venvUv --version 2>$null) -replace 'uv\s+','' }
  }
  if ($uvver) {
    $parts = $uvver.Split(' ')[0]
    if ([version]$parts -lt [version]'0.11.16') {
      Write-Host "WARNING: uv on PATH is $parts — recommended >= 0.11.16. Launcher will continue."
    }
  } else {
    Write-Host "WARNING: uv not found on PATH or in venv."
  }
} catch {
  Write-Host "WARNING: Could not determine uv version: $($ErrorActionPreference = 'Stop'.Exception.Message)"
}
# --- end uv check ---
# --- uv version check (inserted) ---
try {
  $uvver = (& uv --version 2>$null) -replace 'uv\s+',''
  if ($uvver) {
    $parts = $uvver.Split(' ')[0]
    if ([version]$parts -lt [version]'0.11.16') {
      Write-Host "WARNING: uv on PATH is $parts — recommended >= 0.11.16. Launcher will continue."
    }
  } else {
    Write-Host "WARNING: uv not found on PATH."
  }
} catch {
  Write-Host "WARNING: Could not determine uv version: $($ErrorActionPreference = 'Stop'
# --- uv version check (inserted) ---
try {
  $uvver = $null
  try { $uvver = (& uv --version 2>$null) -replace 'uv\s+','' } catch {}
  if (-not $uvver) {
    $venvUv = Join-Path $PSScriptRoot '.venv\Scripts\uv.exe'
    if (Test-Path $venvUv) { $uvver = (& $venvUv --version 2>$null) -replace 'uv\s+','' }
  }
  if ($uvver) {
    $parts = $uvver.Split(' ')[0]
    if ([version]$parts -lt [version]'0.11.16') {
      Write-Host "WARNING: uv on PATH is $parts — recommended >= 0.11.16. Launcher will continue."
    }
  } else {
    Write-Host "WARNING: uv not found on PATH or in venv."
  }
} catch {
  Write-Host "WARNING: Could not determine uv version: $(  Write-Host "WARNING: Could not determine uv version: $($ErrorActionPreference = 'Stop'.Exception.Message)".Exception.Message)"
}
# --- end uv check ---.Exception.Message)"
}
# --- end uv check ---

$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $InstallDir

$Exe = Join-Path $InstallDir '.venv\Scripts\fcc-server.exe'
$Port = 8082
$LogDir = $InstallDir
$StdOut = Join-Path $LogDir 'fcc-server.run.log'
$StdErr = Join-Path $LogDir 'fcc-server.run.err.log'
$PidFile = Join-Path $LogDir 'fcc-server.pid'
$MaxKeep = 3

function Write-Status([string]$m) {
  $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Write-Host "[$t] $m"
}

if (-not (Test-Path $Exe)) {
  Write-Status "ERROR: Server executable not found: $Exe"
  exit 1
}

# Rotate logs
try {
  for ($i = $MaxKeep - 1; $i -ge 0; $i--) {
    $src = if ($i -eq 0) { $StdOut } else { "$StdOut.$i" }
    $dst = "$StdOut.$($i + 1)"
    if (Test-Path $src) {
      Move-Item -LiteralPath $src -Destination $dst -Force
    }
    $srcErr = if ($i -eq 0) { $StdErr } else { "$StdErr.$i" }
    $dstErr = "$StdErr.$($i + 1)"
    if (Test-Path $srcErr) {
      Move-Item -LiteralPath $srcErr -Destination $dstErr -Force
    }
  }
  # Remove oldest if beyond MaxKeep
  $old = "$StdOut.$MaxKeep"
  if (Test-Path $old) { Remove-Item -LiteralPath $old -Force -ErrorAction SilentlyContinue }
  $oldErr = "$StdErr.$MaxKeep"
  if (Test-Path $oldErr) { Remove-Item -LiteralPath $oldErr -Force -ErrorAction SilentlyContinue }
  Write-Status "Rotated logs, keeping $MaxKeep versions."
} catch {
  Write-Status "WARNING: log rotation failed: $($_.Exception.Message)"
}

# Start detached process and capture PID
try {
  $startInfo = @{
    FilePath = $Exe
    ArgumentList = @('--port', $Port)
    WorkingDirectory = $InstallDir
    RedirectStandardOutput = $StdOut
    RedirectStandardError  = $StdErr
    WindowStyle = 'Hidden'
  }
  $proc = Start-Process @startInfo -PassThru
  Start-Sleep -Seconds 1

  if ($proc -and $proc.Id) {
    $procId = $proc.Id
    Set-Content -Path $PidFile -Value $procId -Encoding ASCII
    Write-Status "Started fcc-server (PID $procId). Logs: $StdOut , $StdErr"
    Write-Status "Admin UI: http://127.0.0.1:$Port/admin (local-only)"
    exit 0
  } else {
    Write-Status "ERROR: Start-Process returned no PID."
    exit 2
  }
} catch {
  Write-Status "ERROR: Failed to start server: $($_.Exception.Message)"
  exit 3
}
