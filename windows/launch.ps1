<#
.SYNOPSIS
    Starts CrystalPilot (inside WSL) and opens it in the Windows browser.

.DESCRIPTION
    Double-click CrystalPilot.bat (or the desktop shortcut).  The server runs
    inside this window; close the window or press Ctrl+C to stop it.
    If a newer build (files\xds-gui-v*.py) exists it is picked up automatically.

.PARAMETER Distro    WSL distribution (default: your default distro).
.PARAMETER Port      Override the port from the WSL configuration.
.PARAMETER NoBrowser Do not open the browser automatically.
#>
[CmdletBinding()]
param(
    [string]$Distro = $env:CRYSTALPILOT_DISTRO,
    [int]$Port = 0,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Continue"
$env:WSL_UTF8 = "1"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Host.UI.RawUI.WindowTitle = "CrystalPilot"

$Here = $PSScriptRoot
if (-not $Here) { $Here = Split-Path -Parent $MyInvocation.MyCommand.Path }
$Root = Split-Path -Parent $Here

# crystalpilot.cfg (written by the installer) remembers which WSL distribution
# holds CrystalPilot and the port, unless overridden by parameters / environment.
$cfgFile = Join-Path $Here "crystalpilot.cfg"
$ProjectsDrive = ""; $ProjectsWinCfg = ""
if (Test-Path $cfgFile) {
    foreach ($line in Get-Content $cfgFile) {
        if ($line -match '^\s*DISTRO\s*=\s*(.+?)\s*$' -and -not $Distro) { $Distro = $Matches[1] }
        if ($line -match '^\s*PORT\s*=\s*(\d+)\s*$' -and $Port -le 0) { $Port = [int]$Matches[1] }
        # DRIVE is "P:\Projects" (drive letter + folder inside the runtime's root share) or "P:"
        if ($line -match '^\s*DRIVE\s*=\s*([A-Za-z]:\S*)\s*$') { $ProjectsDrive = $Matches[1].Substring(0, 1).ToUpper() + $Matches[1].Substring(1).TrimEnd('\') }
        if ($line -match '^\s*PROJECTS_WIN\s*=\s*(.+?)\s*$') { $ProjectsWinCfg = $Matches[1] }
    }
}
# Tell the app (inside WSL) which drive letter shows the projects folder, so it
# can display P:\... paths and open Explorer there.  WSLENV forwards the variable.
if ($ProjectsDrive) {
    $env:CRYSTALPILOT_DRIVE = $ProjectsDrive
    $env:WSLENV = if ($env:WSLENV) { $env:WSLENV + ":CRYSTALPILOT_DRIVE" } else { "CRYSTALPILOT_DRIVE" }
}

function Get-DistroArgs { if ($Distro) { return @("-d", $Distro) } else { return @() } }
function Get-WslOutput {
    param([string[]]$WslArgs)
    $all = @(Get-DistroArgs) + $WslArgs
    $out = & wsl.exe @all 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($out | Where-Object { $_ -ne $null -and $_.ToString().Trim() -ne "" })
}
function ConvertTo-WslPath([string]$WinPath) {
    $p = Get-WslOutput @("-e", "wslpath", "-u", $WinPath)
    if (-not $p) { return $null }
    return ($p | Select-Object -First 1).ToString().Trim()
}
function Find-NewestApp {
    $files = @()
    foreach ($d in @((Join-Path $Root "files"), $Root, $Here)) {
        if (Test-Path $d) { $files += Get-ChildItem -Path $d -Filter "xds-gui-v*.py" -File -ErrorAction SilentlyContinue }
    }
    if ($files.Count -eq 0) { return $null }
    $sorted = $files | Sort-Object -Property @{Expression = {
        $m = [regex]::Match($_.BaseName, 'v(\d+)')
        if ($m.Success) { [int]$m.Groups[1].Value } else { 0 }
    }} -Descending
    return $sorted[0].FullName
}
function Wait-Key([string]$prompt) {
    Write-Host ""
    Write-Host ("  " + $prompt) -ForegroundColor DarkGray
    try { $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") } catch { Start-Sleep -Seconds 8 }
}
function Fail([string]$msg) {
    Write-Host ""
    Write-Host ("  " + $msg) -ForegroundColor Red
    Wait-Key "Press any key to close..."
    exit 1
}
function Get-ServerState {
    # "running" / "stopped" according to the WSL control script
    $s = Get-WslOutput @("-e", "/usr/local/bin/crystalpilot", "status")
    if ($s -and (($s -join " ") -match "running on")) { return "running" }
    return "stopped"
}
function Show-AlreadyRunning([string]$u) {
    Write-Host ""
    Write-Host "  CrystalPilot is already running (started from another window or earlier)." -ForegroundColor Green
    Write-Host ("  Interface: " + $u) -ForegroundColor Cyan
    Write-Host "  This window is not needed. The server keeps running until you close the window"
    Write-Host "  that started it, or run CrystalPilot-Stop.bat."
    if (-not $NoBrowser) { try { Start-Process $u } catch {} }
    Wait-Key "Press any key to close this window..."
    exit 0
}

# ── Shortcuts show the CrystalPilot icon ─────────────────────────────────────
# Installers before 0.6.7d gave them a stock Windows icon; each start puts the
# logo on every CrystalPilot shortcut that still has another one.
function Update-ShortcutIcons {
    $ico = Join-Path $Here "CrystalPilot.ico"
    if (-not (Test-Path $ico)) { return }
    $want = $ico + ",0"
    $bat = Join-Path $Here "CrystalPilot.bat"
    $changed = $false
    try {
        $shell = New-Object -ComObject WScript.Shell
        foreach ($dir in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"), $Root)) {
            if (-not $dir) { continue }
            $p = Join-Path $dir "CrystalPilot.lnk"
            if (-not (Test-Path -LiteralPath $p)) { continue }
            $l = $shell.CreateShortcut($p)
            if ($l.TargetPath -ne $bat -or $l.IconLocation -eq $want) { continue }
            $keep = @{ t = $l.TargetPath; a = $l.Arguments; w = $l.WorkingDirectory; d = $l.Description }
            # a new file, not a rewritten one: Explorer would keep showing the cached old icon
            Remove-Item -LiteralPath $p -Force -ErrorAction Stop
            $n = $shell.CreateShortcut($p)
            $n.TargetPath = $keep.t; $n.Arguments = $keep.a; $n.WorkingDirectory = $keep.w; $n.Description = $keep.d
            $n.IconLocation = $want
            $n.Save()
            $changed = $true
        }
    } catch { }
    if ($changed) { try { Start-Process -FilePath (Join-Path $env:SystemRoot "System32\ie4uinit.exe") -ArgumentList "-show" -WindowStyle Hidden } catch { } }
}
Update-ShortcutIcons

Write-Host ""
Write-Host "  Starting CrystalPilot ..." -ForegroundColor White
Write-Host "  The first start after Windows boots takes up to a minute (the Linux runtime starts);" -ForegroundColor DarkGray
Write-Host "  later starts take a few seconds. The browser opens a loading page meanwhile." -ForegroundColor DarkGray

# ── Is it installed? ─────────────────────────────────────────────────────────
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { Fail "WSL is not installed. Run CrystalPilot-Setup.bat first." }
$info = Get-WslOutput @("-e", "/usr/local/bin/crystalpilot", "info")
if (-not $info) { $info = Get-WslOutput @("-e", "sh", "-c", '"$HOME/.local/bin/crystalpilot" info') }
if (-not $info) { Fail "CrystalPilot is not set up in WSL yet. Run CrystalPilot-Setup.bat first." }
$cfg = @{}
foreach ($line in $info) { $kv = $line.ToString().Split("=", 2); if ($kv.Count -eq 2) { $cfg[$kv[0].Trim()] = $kv[1].Trim() } }
if ($cfg["INSTALLED"] -ne "yes") { Fail "CrystalPilot is not set up in WSL yet. Run CrystalPilot-Setup.bat first." }
if ($Port -le 0) { $Port = [int]($cfg["PORT"]); if ($Port -le 0) { $Port = 8000 } }
$url = "http://localhost:$Port"

# ── Already running?  Then just open the browser and say so ──────────────────
# ("info" already checked for a running server; a second wsl call would only add seconds)
if ($cfg["RUNNING"] -eq "yes") { Show-AlreadyRunning $url }

# ── Open the browser right away on the loading screen ────────────────────────
# splash.html shows the program name, version and credits, polls the server
# and switches to the interface as soon as it answers.
$job = $null
if (-not $NoBrowser) {
    $splash = Join-Path $Here "splash.html"
    if (Test-Path $splash) {
        $splashUrl = "file:///" + ($splash -replace '\\', '/') + "?url=" + [uri]::EscapeDataString($url)
        try { Start-Process $splashUrl } catch { }
    } else {
        $job = Start-Job -ArgumentList $url -ScriptBlock {
            param($u)
            for ($i = 0; $i -lt 120; $i++) {
                try {
                    $r = Invoke-WebRequest -UseBasicParsing -Uri ($u + "/health") -TimeoutSec 2
                    if ($r.StatusCode -eq 200) { Start-Process $u; break }
                } catch { }
                Start-Sleep -Milliseconds 500
            }
        }
    }
}


# ── The drives Windows has (WSL does not always mount them itself) ──────────
# Network drives are never mounted by WSL, the local ones only when
# [automount] is on in the runtime's /etc/wsl.conf - and never a disk plugged
# in after it started.  Report every letter; the Linux side mounts the ones
# that are missing and leaves the rest alone.
$netArgs = @()
# Only the letters are read here.  Get-CimInstance Win32_LogicalDisk (used before
# 0.6.6e) asked every network drive for its size and waited for each disconnected
# one: 24 s before anything happened on a PC with four remembered, disconnected shares.
try {
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        if ($d.DriveType -ne [System.IO.DriveType]::Fixed -and $d.DriveType -ne [System.IO.DriveType]::Removable) { continue }
        $id = $d.Name.Substring(0, 2).ToUpper()
        # the projects drive is the runtime's own folder seen from Windows:
        # mounting it back into Linux would be a loop through the share
        if ($ProjectsDrive -and $id -eq $ProjectsDrive.Substring(0, 2).ToUpper()) { continue }
        # a card reader without a card: skipping it saves an 8-second mount timeout inside WSL
        if (-not $d.IsReady) { continue }
        $netArgs += @("--net", ($id + "="))
    }
} catch { }
# Network drives: "net use" knows which mappings are connected without asking the
# servers.  Disconnected ones are left out (mounting them could only time out).
try {
    foreach ($line in @(& net.exe use 2>$null)) {
        if ($line -match '^OK\s+([A-Za-z]:)\s+(\\\\.+?)(\s{2,}|$)') {
            $id = $matches[1].ToUpper(); $unc = $matches[2].Trim()
            if ($ProjectsDrive -and $id -eq $ProjectsDrive.Substring(0, 2).ToUpper()) { continue }
            # a letter that points at a WSL runtime itself (e.g. the P: projects drive)
            if ($unc -match '^\\\\wsl(\$|\.localhost)\\') { continue }
            $netArgs += @("--net", ($id + "=" + $unc))
        }
    }
} catch { }

# ── Newest build on the Windows side (developer convenience) ─────────────────
$appArgs = @()
$app = Find-NewestApp
if ($app) {
    $appW = ConvertTo-WslPath $app
    if ($appW) { $appArgs = @("--app", $appW) }
}
# The illustrated manual (docs\manual) is handed over the same way, so the app
# can serve it at /manual/ from inside the runtime.
$manual = Join-Path $Root "docs\manual"
if (Test-Path (Join-Path $manual "CrystalPilot-Manual.html")) {
    $manW = ConvertTo-WslPath $manual
    if ($manW) { $appArgs += @("--manual", $manW) }
}

Write-Host ""
Write-Host "  CrystalPilot" -ForegroundColor White
Write-Host "  ------------" -ForegroundColor DarkGray
Write-Host ("  Interface:        " + $url) -ForegroundColor Cyan
Write-Host ("  Projects folder:  " + $(if ($ProjectsDrive) { $ProjectsDrive + "\   (" + $cfg["PROJECTS_WIN"] + ")" } else { $cfg["PROJECTS_WIN"] }))
Write-Host ("  XDS: " + $cfg["XDS"] + "   Eiger/neggia: " + $cfg["NEGGIA"] + "   CCP4: " + $cfg["CCP4"])
if ($app) { Write-Host ("  Build:            " + (Split-Path $app -Leaf)) -ForegroundColor DarkGray }
Write-Host ""
Write-Host "  The server runs in this window. Close it (or press Ctrl+C) to stop CrystalPilot." -ForegroundColor Yellow
Write-Host "  Tip: Windows drives are under /mnt/c, /mnt/d ... in the app's file browser - or paste a path like D:\data\xtal1 into it." -ForegroundColor DarkGray
if ($netArgs.Count -gt 0) {
    $letters = @(); for ($k = 1; $k -lt $netArgs.Count; $k += 2) { $letters += ($netArgs[$k].Split("=")[0]) }
    Write-Host ("  Drives offered to Linux: " + ($letters -join ", ") + "  (those WSL has not mounted itself are added now)") -ForegroundColor DarkGray
}
Write-Host ""

# ── Run the server in the foreground ─────────────────────────────────────────
$wslArgs = @(Get-DistroArgs) + @("-e", "/usr/local/bin/crystalpilot", "start", "--port", "$Port") + $appArgs + $netArgs
& wsl.exe @wslArgs
$rc = $LASTEXITCODE

if ($job) { try { Stop-Job $job -ErrorAction SilentlyContinue; Remove-Job $job -Force -ErrorAction SilentlyContinue } catch {} }
# The control script returned at once because another instance won the race:
# the server is alive, so behave like the "already running" case.
if ((Get-ServerState) -eq "running") { Show-AlreadyRunning $url }
# 130/143 = stopped by Ctrl+C / the Stop script (SIGINT / SIGTERM): not an error.
if ($rc -ne 0 -and -not (@(130, 143) -contains $rc)) { Fail "CrystalPilot stopped with an error (code $rc). See the messages above." }
Write-Host ""
Write-Host "  CrystalPilot stopped." -ForegroundColor DarkGray
Start-Sleep -Seconds 2
exit 0
