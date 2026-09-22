<#
.SYNOPSIS
    CrystalPilot uninstaller (the Apps & features entry points here).

.DESCRIPTION
    Removes what the installer put on the Windows side: the program folder,
    the desktop and Start-menu shortcuts, the projects drive letter, the
    Apps & features entry and the installer's own state.

    The Linux runtime holds your PROJECTS. It is removed only when it was
    created by the CrystalPilot installer AND you say so here; a distribution
    you already had is never touched (CrystalPilot's files inside it are
    stopped and left in place).

    Unattended:  CrystalPilot-Uninstall.ps1 -Silent [-RemoveRuntime | -KeepRuntime]
#>
param(
    [switch]$Silent,
    [switch]$RemoveRuntime,
    [switch]$KeepRuntime
)
$ErrorActionPreference = "Continue"
$env:WSL_UTF8 = "1"
$Here = $PSScriptRoot
if (-not $Here) { $Here = Split-Path -Parent $MyInvocation.MyCommand.Path }

$cfg = @{}
$cfgPath = Join-Path $Here "crystalpilot.cfg"
if (Test-Path $cfgPath) { foreach ($line in (Get-Content $cfgPath)) { if ($line -match '^([A-Z_]+)=(.*)$') { $cfg[$matches[1]] = $matches[2].Trim() } } }
$distro = [string]$cfg.DISTRO
$inst = [string]$cfg.INSTALL_DIR; if (-not $inst) { $inst = Split-Path -Parent $Here }
$drive = [string]$cfg.DRIVE
$ownsRuntime = ($cfg.RUNTIME_CREATED -eq "1")
$projWin = [string]$cfg.PROJECTS_WIN

if (-not $Silent) { Add-Type -AssemblyName System.Windows.Forms }
function Ask([string]$text, [string]$buttons, [string]$icon) {
    if ($Silent) { return "Yes" }
    return [string]([System.Windows.Forms.MessageBox]::Show($text, "Remove CrystalPilot", $buttons, $icon))
}
function Say([string]$text) { Write-Host $text }

# ── 1. what to do with the runtime ──────────────────────────────────────────
# (not $removeRuntime: PowerShell names ignore case, that would overwrite the -RemoveRuntime switch)
$dropRuntime = $false
if ($distro -and $ownsRuntime) {
    if ($RemoveRuntime) { $dropRuntime = $true }
    elseif ($KeepRuntime) { $dropRuntime = $false }
    elseif ($Silent) { $dropRuntime = $false }
    else {
        $a = Ask ("CrystalPilot will be removed from this computer.`n`nThe Linux runtime '" + $distro + "' was created by the CrystalPilot installer and holds your PROJECTS (" + $projWin + ").`n`nRemove the runtime as well, with everything in it?`n`n    Yes  = remove the runtime and all projects in it`n    No   = keep the runtime and the projects`n    Cancel = do nothing") "YesNoCancel" "Warning"
        if ($a -eq "Cancel") { exit 0 }
        $dropRuntime = ($a -eq "Yes")
        if ($dropRuntime) {
            $b = Ask ("Really delete the runtime '" + $distro + "' and every project in it? This cannot be undone.") "YesNo" "Warning"
            if ($b -ne "Yes") { exit 0 }
        }
    }
} else {
    $what = if ($distro) { "The Linux distribution '" + $distro + "' was not created by CrystalPilot and is kept." } else { "" }
    $a = Ask ("CrystalPilot will be removed from this computer (program, shortcuts, drive letter). " + $what + "`n`nContinue?") "YesNo" "Question"
    if ($a -ne "Yes") { exit 0 }
}

# ── 2. stop the server ──────────────────────────────────────────────────────
if ($distro) {
    Say "Stopping CrystalPilot in '$distro' ..."
    & wsl.exe -d $distro -e /usr/local/bin/crystalpilot stop 2>$null | Out-Null
}

# ── 3. drive letter, shortcuts, Quick Access ────────────────────────────────
if ($drive -match '^([A-Za-z]):') {
    $letter = $matches[1].ToUpper() + ":"
    Say "Removing drive $letter ..."
    & net use $letter /delete /y 2>$null | Out-Null
}
$desktop = [Environment]::GetFolderPath("Desktop"); $programs = [Environment]::GetFolderPath("Programs")
foreach ($lnk in @((Join-Path $desktop "CrystalPilot.lnk"), (Join-Path $desktop "CrystalPilot Projects.lnk"), (Join-Path $programs "CrystalPilot.lnk"))) {
    # only shortcuts that belong to THIS installation (another copy may own them)
    if (Test-Path $lnk) {
        $mine = $true
        try { $t = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk).TargetPath; if ($t -and $inst -and $lnk -notlike "*Projects.lnk" -and -not $t.StartsWith($inst, [StringComparison]::OrdinalIgnoreCase)) { $mine = $false } } catch {}
        if ($mine) { Remove-Item -Force $lnk -ErrorAction SilentlyContinue }
    }
}
if ($projWin) {
    try { $sh = New-Object -ComObject Shell.Application; $ns = $sh.Namespace($projWin); if ($ns) { $ns.Self.InvokeVerb("unpinfromhome") } } catch {}
}

# ── 4. the runtime ──────────────────────────────────────────────────────────
if ($dropRuntime) {
    Say "Removing the Linux runtime '$distro' ..."
    & wsl.exe --unregister $distro 2>&1 | Out-Null
    # only what the installer put in the runtime folder (the user may have chosen
    # a folder that holds other files): the disk, the downloaded image, then the
    # folder itself if nothing else is left
    $rdir = [string]$cfg.RUNTIME_DIR
    if ($rdir -and (Test-Path $rdir)) {
        foreach ($n in @("ext4.vhdx", "ubuntu-24.04-wsl-rootfs.tar.gz", "ubuntu-24.04-wsl-rootfs.tar.gz.part")) { Remove-Item -Force (Join-Path $rdir $n) -ErrorAction SilentlyContinue }
        if (-not (Get-ChildItem $rdir -Force -ErrorAction SilentlyContinue)) { Remove-Item -Force $rdir -ErrorAction SilentlyContinue }
    }
}

# ── 5. registry, installer state, program folder ────────────────────────────
Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\CrystalPilot" -Recurse -Force -ErrorAction SilentlyContinue
$stateDir = Join-Path $env:LOCALAPPDATA "CrystalPilot"
if (Test-Path $stateDir) { Remove-Item -Recurse -Force $stateDir -ErrorAction SilentlyContinue }
# the Start-menu entry that continues setup after a restart, and the RunOnce
# entry earlier installers used for the same job
Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Programs")) "Continue CrystalPilot Setup.lnk") -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce" -Name "CrystalPilotSetup" -ErrorAction SilentlyContinue

$kept = if ($distro -and -not $dropRuntime) { "`n`nThe Linux runtime '" + $distro + "' and the projects in it were kept" + $(if ($projWin) { " (" + $projWin + ")" } else { "" }) + "." } else { "" }
if (-not $Silent) { [System.Windows.Forms.MessageBox]::Show("CrystalPilot was removed." + $kept, "Remove CrystalPilot", "OK", "Information") | Out-Null }
else { Say ("CrystalPilot was removed." + $kept) }

# The program folder holds this script: delete it after this process has ended.
# Only the parts the installer created are removed, then the folder if it is
# empty - a folder the user chose may hold other files (never "rmdir /s" on it).
if ($inst -and (Test-Path $inst) -and ($inst -notmatch '^[A-Za-z]:\\?$')) {
    $parts = @()
    foreach ($n in @("windows", "files", "docs\manual")) { $p = Join-Path $inst $n; if (Test-Path $p) { $parts += ('rmdir /s /q "' + $p + '"') } }
    foreach ($n in @("CrystalPilot.lnk", "dectris-neggia.so")) { $p = Join-Path $inst $n; if (Test-Path $p) { $parts += ('del /f /q "' + $p + '"') } }
    foreach ($x in @(Get-ChildItem $inst -Filter "XDS-*.tar.gz" -File -ErrorAction SilentlyContinue)) { $parts += ('del /f /q "' + $x.FullName + '"') }
    $parts += ('rmdir "' + (Join-Path $inst "docs") + '" 2>nul'); $parts += ('rmdir "' + $inst + '" 2>nul')
    Start-Process -WindowStyle Hidden cmd.exe -ArgumentList @("/c", ("ping -n 3 127.0.0.1 >nul & " + ($parts -join " & ")))
}
exit 0
