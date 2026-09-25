<#
.SYNOPSIS
    CrystalPilot installer for Windows (graphical wizard).

.DESCRIPTION
    Guides a user with no Linux knowledge through a complete installation:
      1. Welcome: what will be done (XDS is a Linux program, so the Windows
         Subsystem for Linux and an Ubuntu runtime are enabled/fetched) and the
         settings the express install will use.  One button, Customize...,
         opens the options page; otherwise it is never seen.
      2. Options (only via Customize): install folder, Linux runtime (a
         dedicated CrystalPilot runtime on a disk of your choice, or an existing
         distribution), projects folder inside the runtime, port, drive letter.
      3. Components: a checklist - XDS package, neggia reader, CCP4 - that fills
         itself from the package folder and Downloads; "Get it" opens the
         download page and the line turns green once the file is saved.
      4. Installation with a live log; elevation and a Windows restart are
         handled when WSL itself has to be enabled.
      5. Finish: summary, start CrystalPilot.
    Installs: program folder, desktop + Start-menu shortcuts, the projects
    folder as a drive letter, an Apps & features entry with an uninstaller.

    Unattended:  wizard.ps1 -Unattended -Config choices.json
    Preview:     wizard.ps1 -Preview C:\tmp   (renders the pages to PNG files)
#>
[CmdletBinding()]
param(
    [string]$Resume = "",
    [switch]$Unattended,
    [string]$Config = "",
    [string]$Preview = "",
    [switch]$NoLaunch,
    [string]$EnableWsl = "",     # internal: the elevated helper that only enables WSL, result written to this file
    [switch]$StartedHidden,      # internal: Setup.exe started this with a hidden start-up mode (see Add_Shown below)
    [string]$Probe = ""          # internal: look at this computer (WSL, disks, an installed CrystalPilot), write the default choices to this file, exit
)
$ErrorActionPreference = "Stop"
$env:WSL_UTF8 = "1"
$ScriptClock = [Diagnostics.Stopwatch]::StartNew()      # how long the first windows take (written to setup-start.txt)
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Here = $PSScriptRoot
if (-not $Here) { $Here = Split-Path -Parent $MyInvocation.MyCommand.Path }
$Root = Split-Path -Parent $Here
$WizardVersion = "1.2"
# CP_SETUP_TEST=1: a test installation (a throwaway runtime) that must not touch this
# computer's CrystalPilot: no shortcuts, no Apps & features entry, no drive letter,
# no Start-menu entry, its own state and log files.
$TestMode = ($env:CP_SETUP_TEST -eq "1")
$SetupDataDir = Join-Path $env:LOCALAPPDATA $(if ($TestMode) { "CrystalPilot-test" } else { "CrystalPilot" })
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}
# a proxy that asks for the Windows login (common at universities): BITS, used
# before 0.6.6e, sent it by itself; WebClient and HttpWebRequest only when told
try { $wp = [Net.WebRequest]::GetSystemWebProxy(); $wp.Credentials = [Net.CredentialCache]::DefaultNetworkCredentials; [Net.WebRequest]::DefaultWebProxy = $wp } catch {}
$script:Pump = {}              # the wizard sets this to DoEvents so long programs do not freeze the window
$RootfsUrl = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-24.04lts.rootfs.tar.gz"
$RootfsName = "ubuntu-24.04-wsl-rootfs.tar.gz"
$XdsUrl = "https://xds.mr.mpg.de/html_doc/downloading.html"
$NeggiaUrl = "https://github.com/dectris/neggia/releases"
$Ccp4Url = "https://www.ccp4.ac.uk/download/"

# ══════════════════════════════════════════════════════════════════════════════
#  Helpers (no UI)
# ══════════════════════════════════════════════════════════════════════════════
function Test-Admin {
    return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Get-ScriptPolicy {
    # The execution policy for the PowerShell windows this wizard starts itself.
    # RemoteSigned whenever it is enough: Setup.exe writes its files itself, so
    # they carry no download mark and RemoteSigned runs them.  Only files unpacked
    # from a downloaded zip keep Windows' "from the internet" mark, which
    # RemoteSigned refuses for an unsigned script - there Bypass is still needed.
    # "-ExecutionPolicy Bypass" on every command line is one of the things
    # antivirus heuristics score an installer on.
    try {
        if (Get-Item -LiteralPath $PSCommandPath -Stream Zone.Identifier -ErrorAction Stop) { return "Bypass" }
    } catch {}
    return "RemoteSigned"
}
function Invoke-WslLines {
    # Run wsl.exe and return its output lines (empty array on failure); never throws.
    # The window keeps painting while it waits: the first call can take many seconds
    # (the runtime starts), and a plain call froze the wizard for that long.
    param([string[]]$WslArgs)
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "wsl.exe"; $psi.Arguments = ConvertTo-ArgString $WslArgs
        $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
        $psi.StandardOutputEncoding = [Text.Encoding]::UTF8
        $psi.EnvironmentVariables["WSL_UTF8"] = "1"
        $p = [System.Diagnostics.Process]::Start($psi)
        $out = $p.StandardOutput.ReadToEndAsync(); $null = $p.StandardError.ReadToEndAsync()
        while (-not $p.WaitForExit(50)) { & $script:Pump }
        $p.WaitForExit()
        if ($p.ExitCode -ne 0) { return @() }
        $text = [string]$out.Result
    } catch { return @() }
    return @(($text -replace "`0", "") -split "`r?`n" | Where-Object { $_.Trim() -ne "" } | ForEach-Object { $_.Trim() })
}
function ConvertTo-ArgString([string[]]$list) {
    # one Windows command line from separate arguments (paths with blanks, quotes)
    return (@($list | ForEach-Object {
        $s = [string]$_
        if ($s -eq "") { '""' }
        elseif ($s -notmatch '[\s"]') { $s }
        else { '"' + (($s -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"' }
    }) -join ' ')
}
function Invoke-Live {
    # Runs a program and hands every output line to $Log as it arrives, while
    # the window keeps repainting (wsl --import and the Linux-side installer
    # are silent for minutes; a plain call froze the wizard: "Not responding").
    # Returns @{ rc = exit code; text = all output }.
    param([string]$Exe, [string[]]$ArgList, [scriptblock]$Log)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe; $psi.Arguments = ConvertTo-ArgString $ArgList
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    $psi.EnvironmentVariables["WSL_UTF8"] = "1"
    $p = [System.Diagnostics.Process]::Start($psi)
    $all = New-Object System.Text.StringBuilder
    $streams = @(
        @{ s = $p.StandardOutput.BaseStream; buf = (New-Object byte[] 8192); dec = [Text.Encoding]::UTF8.GetDecoder(); pend = ""; task = $null; done = $false },
        @{ s = $p.StandardError.BaseStream;  buf = (New-Object byte[] 8192); dec = [Text.Encoding]::UTF8.GetDecoder(); pend = ""; task = $null; done = $false })
    foreach ($st in $streams) { $st.task = $st.s.ReadAsync($st.buf, 0, 8192) }
    while (-not ($streams[0].done -and $streams[1].done)) {
        $busy = $false
        foreach ($st in $streams) {
            if ($st.done -or -not $st.task.IsCompleted) { continue }
            $busy = $true
            $n = 0; try { $n = $st.task.Result } catch { $n = 0 }
            if ($n -le 0) {
                $st.done = $true
                if ($st.pend.Trim()) { $null = $all.AppendLine($st.pend); & $Log ("    " + $st.pend.TrimEnd()) }
                continue
            }
            $chars = New-Object char[] ($n * 2)
            $k = $st.dec.GetChars($st.buf, 0, $n, $chars, 0)
            $st.pend += [string]::new($chars, 0, $k)
            $parts = $st.pend -split "`n"
            $st.pend = $parts[-1]
            for ($i = 0; $i -lt $parts.Count - 1; $i++) {
                $line = $parts[$i].TrimEnd("`r")
                $null = $all.AppendLine($line)
                if ($line.Trim()) { & $Log ("    " + $line) }
            }
            $st.task = $st.s.ReadAsync($st.buf, 0, 8192)
        }
        & $script:Pump
        if (-not $busy) { Start-Sleep -Milliseconds 60 }
    }
    $p.WaitForExit()
    return @{ rc = $p.ExitCode; text = $all.ToString() }
}
function Get-DownloadsDir {
    # the real Downloads folder (it is often moved, e.g. into OneDrive)
    try { $d = (New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path; if ($d -and (Test-Path $d)) { return $d } } catch {}
    return (Join-Path $env:USERPROFILE "Downloads")
}
function Get-WslState {
    # "missing" = wsl.exe absent / WSL not installed, "novm" = WSL answers but the
    # Virtual Machine Platform is not enabled yet (WSL 2 cannot start), "nodistro", "ok"
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { return "missing" }
    $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try { $null = & wsl.exe --status 2>$null; $rc = $LASTEXITCODE } catch { $rc = 1 } finally { $ErrorActionPreference = $prev }
    if ($rc -ne 0) { return "missing" }
    # vmcompute (Host Compute Service) comes with the Virtual Machine Platform;
    # without it every runtime fails to start, whatever wsl --status says
    if (-not (Get-Service vmcompute -ErrorAction SilentlyContinue)) { return "novm" }
    $d = @(Get-Distros)
    if ($d.Count -eq 0) { return "nodistro" }
    return "ok"
}
function Get-Distros { return @(Invoke-WslLines @("-l", "-q") | Where-Object { $_ -notmatch "docker-desktop" }) }
function Get-WslHome([string]$distro) {
    $a = @(); if ($distro) { $a += @("-d", $distro) }
    $a += @("-e", "sh", "-c", 'echo $HOME')
    $h = @(Invoke-WslLines $a)
    if ($h.Count -gt 0) { return [string]$h[0] } else { return "/root" }
}
function ConvertTo-WslPath([string]$winPath, [string]$distro) {
    $a = @(); if ($distro) { $a += @("-d", $distro) }
    $a += @("-e", "wslpath", "-u", $winPath)
    $p = @(Invoke-WslLines $a)
    if ($p.Count -gt 0) { return [string]$p[0] } else { return "" }
}
function Get-FixedDrives {
    $list = @()
    try {
        foreach ($d in (Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction Stop)) {
            $list += [pscustomobject]@{ Letter = $d.DeviceID; FreeGB = [math]::Round($d.FreeSpace / 1GB); SizeGB = [math]::Round($d.Size / 1GB); Label = $d.VolumeName }
        }
    } catch {}
    return $list
}
function Get-FreeGB([string]$path) {
    if (-not $path) { return $null }
    $drive = ($path -replace '^([A-Za-z]):.*$', '$1') + ":"
    $d = Get-FixedDrives | Where-Object { $_.Letter -eq $drive.ToUpper() } | Select-Object -First 1
    if ($d) { return $d.FreeGB } else { return $null }
}
function Find-Newest([string[]]$dirs, [string]$filter) {
    $hits = @()
    foreach ($d in $dirs) { if ($d -and (Test-Path $d)) { $hits += Get-ChildItem -Path $d -Filter $filter -File -ErrorAction SilentlyContinue } }
    if ($hits.Count -eq 0) { return "" }
    return ($hits | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}
function Find-App {
    $files = @()
    foreach ($d in @((Join-Path $Root "files"), $Root, $Here)) {
        if (Test-Path $d) { $files += Get-ChildItem -Path $d -Filter "xds-gui-v*.py" -File -ErrorAction SilentlyContinue }
    }
    if ($files.Count -gt 0) {
        return ($files | Sort-Object -Property @{Expression = { $m = [regex]::Match($_.BaseName, 'v(\d+)'); if ($m.Success) { [int]$m.Groups[1].Value } else { 0 } }} -Descending | Select-Object -First 1).FullName
    }
    foreach ($c in @((Join-Path $Here "crystalpilot.py"), (Join-Path $Root "crystalpilot.py"))) { if (Test-Path $c) { return $c } }
    return ""
}
function Test-Ccp4Bin {
    # any of the programs CrystalPilot runs is enough - an installation
    # without f2mtz is still a CCP4
    param([string]$Dir)
    if (-not $Dir) { return $false }
    foreach ($n in @("pointless.exe", "aimless.exe", "ctruncate.exe", "f2mtz.exe", "cad.exe")) {
        if (Test-Path (Join-Path $Dir $n)) { return $true }
    }
    return $false
}
function Find-WindowsCcp4 {
    $bases = @()
    foreach ($d in (Get-FixedDrives)) { $bases += ($d.Letter + "\") }
    # CCP4 9 is installed by unpacking a zip and running install_ccp4.exe from
    # it, so the folder is often still in Downloads or on the Desktop.
    foreach ($b in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA, $env:USERPROFILE,
                     (Get-DownloadsDir),
                     (Join-Path $env:USERPROFILE "Downloads"), (Join-Path $env:USERPROFILE "Documents"),
                     (Join-Path $env:USERPROFILE "Desktop"), $env:CCP4)) {
        if ($b -and (Test-Path $b)) { $bases += $b }
    }
    $roots = @()
    if ($env:CCP4 -and (Test-Ccp4Bin (Join-Path $env:CCP4 "bin"))) { $roots += $env:CCP4 }
    foreach ($b in ($bases | Select-Object -Unique)) {
        foreach ($c in (Get-ChildItem -Path $b -Filter "CCP4*" -Directory -ErrorAction SilentlyContinue)) {
            if (Test-Ccp4Bin (Join-Path $c.FullName "bin")) { $roots += $c.FullName }
            foreach ($sub in (Get-ChildItem -Path $c.FullName -Directory -ErrorAction SilentlyContinue)) {
                if (Test-Ccp4Bin (Join-Path $sub.FullName "bin")) { $roots += $sub.FullName }
            }
        }
    }
    if ($roots.Count -eq 0) { return "" }
    return ($roots | Sort-Object -Descending | Select-Object -First 1)
}
$SearchDirs = @($Root, $Here, (Get-DownloadsDir))
function Find-XdsTar   { return (Find-Newest $SearchDirs "XDS-*Linux_x86_64.tar.gz") }
function Find-Neggia   { return (Find-Newest $SearchDirs "dectris-neggia.so") }
function Find-Ccp4Tar  { $t = Find-Newest $SearchDirs "ccp4-*linux*.tar.gz"; if (-not $t) { $t = Find-Newest $SearchDirs "ccp4-*.tar.gz" }; if ($t -and $t -match 'win') { $t = "" }; return $t }

function Get-ShortcutFolders {
    # the folders the CrystalPilot shortcuts start from (...\windows): an installation
    # is found there wherever it was put, also when an older setup did not register it
    $dirs = @()
    try {
        $sh = New-Object -ComObject WScript.Shell
        foreach ($l in @((Join-Path ([Environment]::GetFolderPath("Desktop")) "CrystalPilot.lnk"),
                         (Join-Path ([Environment]::GetFolderPath("Programs")) "CrystalPilot.lnk"),
                         (Join-Path ([Environment]::GetFolderPath("CommonDesktopDirectory")) "CrystalPilot.lnk"))) {
            if (Test-Path $l) { $t = [string]$sh.CreateShortcut($l).TargetPath; if ($t -match 'CrystalPilot\.bat$') { $dirs += (Split-Path $t -Parent) } }
        }
    } catch {}
    return @($dirs | Select-Object -Unique)
}
function Get-InstalledConfig {
    # A re-run keeps the settings of the installed copy: the launcher's
    # crystalpilot.cfg says where everything is.  Looked for next to this script,
    # at the folder Apps & features knows, behind the CrystalPilot shortcuts
    # (setups before 0.6.6e did not always register themselves), and in the
    # default install folder.
    $sysDrive = $env:SystemDrive; if (-not $sysDrive) { $sysDrive = "C:" }
    $places = @((Join-Path $Here "crystalpilot.cfg"))
    try {
        # the installer registers itself in Apps & features with its folder
        $reg = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\CrystalPilot" -ErrorAction Stop
        if ($reg.InstallLocation) { $places += (Join-Path ([string]$reg.InstallLocation) "windows\crystalpilot.cfg") }
    } catch {}
    foreach ($d in (Get-ShortcutFolders)) { $places += (Join-Path $d "crystalpilot.cfg") }
    $places += (Join-Path $sysDrive "CrystalPilot\windows\crystalpilot.cfg")
    foreach ($p in $places) {
        if (Test-Path $p) {
            $cfg = @{}
            foreach ($line in (Get-Content $p)) { if ($line -match '^([A-Z_]+)=(.*)$') { $cfg[$matches[1]] = $matches[2].Trim() } }
            if ($cfg.DISTRO) { $cfg.SOURCE = $p; return $cfg }
        }
    }
    return $null
}
function Get-WslInstall([string]$distro) {
    # CrystalPilot as installed inside a Linux distribution: version, port, projects
    # folder - or $null when that distribution has no CrystalPilot
    $script = 'f=/root/.crystalpilot/crystalpilot.py; [ -f "$f" ] || exit 3; grep -m1 "^VERSION" "$f"; [ -f /root/.crystalpilot/config.env ] && . /root/.crystalpilot/config.env; echo "PORT=${PORT:-}"; echo "PROJECTS=${PROJECTS_DIR:-}"'
    $lines = @(Invoke-WslLines @("-d", $distro, "-u", "root", "-e", "sh", "-c", $script))
    if ($lines.Count -eq 0) { return $null }
    $r = @{ VERSION = ""; PORT = ""; PROJECTS = "" }
    foreach ($l in $lines) {
        if ($l -match '^VERSION\s*=\s*"([^"]+)"') { $r.VERSION = $matches[1] }
        elseif ($l -match '^(PORT|PROJECTS)=(.*)$') { $r[$matches[1]] = $matches[2].Trim() }
    }
    return $r
}
function Get-AppVersion([string]$path) {
    if (-not $path -or -not (Test-Path $path)) { return "" }
    try { $m = [regex]::Match((Get-Content $path -TotalCount 60) -join "`n", 'VERSION\s*=\s*"([^"]+)"'); if ($m.Success) { return $m.Groups[1].Value } } catch {}
    return ""
}
function Format-Elapsed($ts) { return ("{0}:{1:00}" -f [int][math]::Floor($ts.TotalMinutes), $ts.Seconds) }
function Save-Download {
    # Downloads $Url to $Dest while the window stays responsive: MB, speed and time
    # left on the progress line, a note in the log when no data arrives for a
    # minute, and a clear error after five.  (Replaces BITS: its job reports an
    # unknown size as 18 million terabytes, which drew the bar at 0 % - the
    # "progress bar does not work" of 0.6.6d - and it waited in its own queue.)
    param([string]$Url, [string]$Dest, [scriptblock]$Log, [scriptblock]$Progress, [string]$What)
    $total = [long]0
    try {
        $rq = [System.Net.HttpWebRequest]::Create($Url); $rq.Method = "HEAD"; $rq.Timeout = 20000
        $rs = $rq.GetResponse(); $total = [long]$rs.ContentLength; $rs.Close()
    } catch { $total = 0 }
    $tmp = $Dest + ".part"
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
    $wc = New-Object System.Net.WebClient
    $task = $wc.DownloadFileTaskAsync($Url, $tmp)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $lastSize = [long]-1; $lastChange = [long]0; $lastShow = [long]-1000; $warned = $false
    while (-not $task.IsCompleted) {
        & $script:Pump
        Start-Sleep -Milliseconds 50
        $ms = [long]$sw.ElapsedMilliseconds
        if ($ms - $lastShow -lt 500) { continue }
        $lastShow = $ms
        $have = [long]0; try { $fi = New-Object IO.FileInfo $tmp; if ($fi.Exists) { $have = [long]$fi.Length } } catch {}
        if ($have -ne $lastSize) {
            $lastSize = $have; $lastChange = $ms
            if ($warned) { & $Log "    data is arriving again"; $warned = $false }
        }
        $idle = ($ms - $lastChange) / 1000
        if ($idle -ge 60 -and -not $warned) { & $Log "    no data for a minute - still trying (check the internet connection)"; $warned = $true }
        if ($idle -ge 300) { $wc.CancelAsync(); throw "The download of $What stopped: no data for five minutes. Check the internet connection (or proxy) and run the installer again." }
        $mb = [math]::Round($have / 1MB)
        $rate = 0.0; if ($ms -gt 1000) { $rate = ($have / 1MB) / ($ms / 1000.0) }
        if ($total -gt 0) {
            $eta = ""
            if ($rate -gt 0.05) { $left = (($total - $have) / 1MB) / $rate; $eta = if ($left -ge 90) { ", about " + [math]::Ceiling($left / 60) + " min left" } elseif ($left -ge 1) { ", about 1 min left" } else { "" } }
            & $Progress ([int][math]::Min(100, 100 * $have / $total)) ("Downloading {0}: {1} of {2} MB ({3:0.0} MB/s{4})" -f $What, $mb, [math]::Round($total / 1MB), $rate, $eta)
        } else {
            & $Progress -1 ("Downloading {0}: {1} MB ({2:0.0} MB/s)" -f $What, $mb, $rate)
        }
    }
    if ($task.IsFaulted) { throw ("Downloading $What failed: " + $task.Exception.GetBaseException().Message + " (check the internet connection or proxy, then run the installer again)") }
    if ($task.IsCanceled) { throw "The download of $What was cancelled." }
    Move-Item -Force $tmp $Dest
    & $Log ("    downloaded {0} MB in {1}" -f [math]::Round((Get-Item $Dest).Length / 1MB), (Format-Elapsed $sw.Elapsed))
}
function Get-BestDrive {
    # the fixed disk with the most free space: where the Linux runtime (2 to 13 GB) goes
    $d = Get-FixedDrives | Sort-Object FreeGB -Descending | Select-Object -First 1
    if ($d) { return $d.Letter } else { $sd = $env:SystemDrive; if ($sd) { return $sd } else { return "C:" } }
}
function New-DefaultState {
    $wslState = Get-WslState
    $distros = @(); if ($wslState -eq "ok") { $distros = @(Get-Distros) }
    $sysDrive = $env:SystemDrive; if (-not $sysDrive) { $sysDrive = "C:" }
    # Express defaults: a dedicated runtime - nothing is installed into a Linux
    # distribution the user keeps for other work - on the disk with the most
    # room, the projects inside it, shown in Explorer as P:\Projects.
    $newName = "CrystalPilot"
    $installDir = (Join-Path $sysDrive "CrystalPilot")
    $runtimeDir = (Join-Path (Get-BestDrive) "CrystalPilot\runtime")
    $projects = "/root/crystalpilot_projects"; $port = 8000
    if ($TestMode) {
        # a test installation next to the real one: its own folder, runtime and port
        $installDir = Join-Path $SetupDataDir "app"; $newName = "CPTest"
        $runtimeDir = (Join-Path (Get-BestDrive) "CPTest\runtime"); $port = 8097
    }
    # a test installation (CP_SETUP_TEST) must never pick up the real one:
    # only runtimes named CPTest* count as installed there
    $cfg = if ($TestMode) { $null } else { Get-InstalledConfig }
    if ($TestMode) { $distros = @($distros | Where-Object { $_ -like "CPTest*" }) }
    $wslInst = $null
    if ($cfg -and ($distros -contains $cfg.DISTRO)) { $wslInst = Get-WslInstall ([string]$cfg.DISTRO) }
    elseif (-not $cfg) {
        # no launcher settings found: an installation inside a distribution is still an installation
        foreach ($d in ($distros | Select-Object -First 6)) {
            $i = Get-WslInstall ([string]$d)
            if ($i) { $wslInst = $i; $cfg = @{ DISTRO = [string]$d; PORT = $i.PORT; PROJECTS = $i.PROJECTS; SOURCE = "wsl:$d" }; break }
        }
    }
    $mapDrive = $true; $driveLetter = "P"; $update = $false
    if ($cfg) {
        # updating an installation: same folders, same runtime, same port
        if ($cfg.INSTALL_DIR) { $installDir = $cfg.INSTALL_DIR }
        if ($cfg.RUNTIME_DIR) { $runtimeDir = $cfg.RUNTIME_DIR }
        if ($cfg.PORT) { $port = [int]$cfg.PORT }
        if ($cfg.PROJECTS) { $projects = $cfg.PROJECTS }
        if ($distros -contains $cfg.DISTRO) { $newName = $cfg.DISTRO }
    }
    if ($cfg -and ($distros -contains $cfg.DISTRO)) {
        # the runtime it lives in is there: update it in place - no new runtime,
        # no download, the drive letter as it was (none if there was none)
        $update = $true
        $mapDrive = [bool]([string]$cfg.DRIVE)
        if ([string]$cfg.DRIVE) { $driveLetter = ([string]$cfg.DRIVE).Substring(0, 1) }
    }
    $existing = ""; if ($distros.Count -gt 0) { $existing = [string]$distros[0] }
    if ($update) { $existing = [string]$cfg.DISTRO }
    $winCcp4 = Find-WindowsCcp4
    $ccp4Tar = Find-Ccp4Tar
    $ccp4Mode = "skip"; if ($ccp4Tar) { $ccp4Mode = "linux" } elseif ($winCcp4) { $ccp4Mode = "windows" }
    # an update keeps the CCP4 it has (wsl-install.sh reads it from config.env);
    # a Linux CCP4 tarball still in Downloads would otherwise be unpacked again (10 GB)
    if ($update) { $ccp4Mode = "skip" }
    $app = Find-App
    return @{
        installDir   = $installDir
        runtimeMode  = $(if ($update) { "existing" } else { "dedicated" })   # existing | dedicated
        update       = $update                     # an installed CrystalPilot is updated in place
        installedVersion = $(if ($wslInst) { [string]$wslInst.VERSION } else { "" })
        installedFrom = $(if ($cfg) { [string]$cfg.SOURCE } else { "" })
        newVersion   = (Get-AppVersion $app)
        distros      = @($distros)
        vpNote       = (Get-VirtualizationProblem)
        distro       = $existing                   # existing distribution name (Customize)
        newDistro    = $newName                    # name of the dedicated runtime
        runtimeDir   = $runtimeDir
        projects     = $projects
        port         = $port
        app          = $app
        xdsTar       = (Find-XdsTar)
        neggia       = (Find-Neggia)
        ccp4Mode     = $ccp4Mode                   # windows | linux | skip
        ccp4Win      = $winCcp4
        ccp4Tar      = $ccp4Tar
        launch       = (-not $NoLaunch)
        mapDrive     = $mapDrive                   # show the projects folder as a Windows drive
        driveLetter  = $driveLetter
        wslState     = $wslState
        acknowledged = $false
        runtimeCreated = ($cfg -ne $null -and $cfg.RUNTIME_CREATED -eq "1")   # the uninstaller may remove a runtime we made
        stage        = "start"
    }
}
function Save-State($state, [string]$path) { ($state | ConvertTo-Json -Depth 4) | Set-Content -Path $path -Encoding UTF8 }
function Load-State([string]$path) {
    $j = Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
    $s = @{}; foreach ($p in $j.PSObject.Properties) { $s[$p.Name] = $p.Value }
    return $s
}
$UpdateText = @"
CrystalPilot is already installed on this computer. This updates it in place:

   - the new program files are copied to the program folder
   - CrystalPilot is updated inside the Linux distribution it already uses (its Python packages are checked; XDS, neggia and CCP4 stay as they are)
   - your projects, the port, the drive letter and the shortcuts stay the same

No new Linux runtime is created and nothing large is downloaded. The update takes about 5 minutes; the progress bar and a clock keep moving while it works.

To install into a different Linux runtime or folder instead, click Customize.
"@
$DisclosureText = @"
CrystalPilot drives XDS, which exists only as a Linux program. To run it on Windows, this installer will enable the Windows Subsystem for Linux (a Microsoft component of Windows) and use a Linux runtime (Ubuntu) that runs invisibly in the background. You will not need to use Linux yourself.

This requires administrator approval once and may require one restart of Windows.

Approximate disk space:
   - Windows Subsystem for Linux and Ubuntu runtime:   about 2 GB
   - CrystalPilot and its Python components:             about 0.5 GB
   - XDS and the Eiger reader:                            under 0.1 GB
   - CCP4 (optional: POINTLESS, AIMLESS, CTRUNCATE):      about 10 GB

Time: 15 to 30 minutes on a new computer (a 340 MB download, then the Linux runtime is set up); the progress bar and a clock keep moving while it works.

Downloads: about 1 GB, plus 4 GB if CCP4 is installed from the Linux package. Your data and results live in the projects folder you choose and are not counted here.

XDS and the neggia reader are free for academic use but must be obtained from their authors; this installer opens the download pages for you and picks the files up from your Downloads folder.
"@

# ══════════════════════════════════════════════════════════════════════════════
#  Installation pipeline (shared by the wizard and unattended mode)
# ══════════════════════════════════════════════════════════════════════════════
function Get-DistroName($state) { if ($state.runtimeMode -eq "dedicated") { return [string]$state.newDistro } else { return [string]$state.distro } }

function Enable-WslPlatform([scriptblock]$Log) {
    # Needs administrator rights.  Returns "ok", "reboot" or "error: <text>".
    & $Log "Enabling the Windows Subsystem for Linux (Microsoft download, a few minutes) ..."
    $r = Invoke-Live "wsl.exe" @("--install", "--no-distribution") $Log
    if ($r.rc -ne 0) {
        # older Windows 10 builds do not know --no-distribution: switch the features on directly
        & $Log "wsl --install returned $($r.rc); enabling the Windows features directly ..."
        try {
            Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All -NoRestart -ErrorAction Stop | Out-Null
            Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart -ErrorAction Stop | Out-Null
        } catch { return ("error: " + $_.Exception.Message) }
    }
    $null = Invoke-Live "wsl.exe" @("--update") $Log
    # The Virtual Machine Platform only becomes active after a restart.  wsl.exe
    # itself may already answer, so ask Windows for the feature state instead of
    # trusting wsl --status (which is what let the old installer go on and fail).
    try {
        $vmp = (Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -ErrorAction Stop).State
        & $Log "    Virtual Machine Platform: $vmp"
        if ([string]$vmp -ne "Enabled") { return "reboot" }
    } catch {}
    if ((Get-WslState) -in @("missing", "novm")) { return "reboot" }
    return "ok"
}
if ($EnableWsl) {
    # elevated helper started by the wizard: only this step runs as administrator;
    # everything else (runtime, shortcuts, drive letter) stays with the real user
    $lines = New-Object System.Collections.ArrayList
    $res = "error: unknown"
    try { $res = Enable-WslPlatform { param($m) Write-Host $m; [void]$lines.Add($m) } } catch { $res = "error: " + $_.Exception.Message }
    @("RESULT=$res") + @($lines) | Set-Content -Path $EnableWsl -Encoding UTF8
    exit 0
}

function Get-VirtualizationProblem {
    # "" when fine or unknown; a sentence when the firmware says virtualization is off
    try {
        $cpu = @(Get-CimInstance Win32_Processor -ErrorAction Stop)[0]
        if ($cpu.VirtualizationFirmwareEnabled -eq $false -and -not (Get-CimInstance Win32_ComputerSystem).HypervisorPresent) {
            return "Virtualization is switched off in this computer's firmware (BIOS/UEFI). WSL 2, and so XDS on Windows, needs it: restart, open the BIOS/UEFI setup, enable 'Intel Virtualization Technology (VT-x)' or 'SVM Mode' (AMD), save, and run the installer again."
        }
    } catch {}
    return ""
}
function Explain-WslError([string]$text, [string]$rdir) {
    # wsl.exe error text -> what the user has to do
    if ($text -match 'HCS_E_HYPERV_NOT_INSTALLED|0x80370102|Virtual Machine Platform|virtuali[sz]ation') {
        return "Windows cannot start the Linux runtime: virtual machines are not available. Restart Windows once (enabling WSL finishes at restart); if it still fails, enable virtualization (Intel VT-x / AMD SVM) in the BIOS/UEFI setup. Then run the installer again."
    }
    if ($text -match 'ERROR_ALREADY_EXISTS|0x800700b7|already exists') {
        return "The folder $rdir already holds a Linux runtime from an earlier attempt. Choose another runtime folder (Customize) or delete that folder, then run the installer again."
    }
    if ($text -match 'ERROR_FILE_COMPRESSED|compress|encrypt|0x8007018a|0xc03a001a') {
        return "Windows cannot keep the runtime disk in $rdir because the folder is compressed or encrypted. Choose another runtime folder (Customize)."
    }
    if ($text -match 'ACCESS_DENIED|0x80070005|Access is denied') {
        return "Windows refused to write the runtime to $rdir (access denied). Choose a folder you own, for example on another drive (Customize)."
    }
    $first = (($text -split "`n") | Where-Object { $_.Trim() } | Select-Object -Last 2) -join " "
    return "wsl --import failed: $first"
}
function Test-FolderChoice([string]$path, [string]$what) {
    # "" when the folder can be used; otherwise the reason
    if (-not $path) { return "Please choose the $what." }
    if ($path -notmatch '^[A-Za-z]:\\') { return "The $what must be a folder on a local drive, like D:\CrystalPilot (not a network path)." }
    $letter = $path.Substring(0, 2).ToUpper()
    $disk = $null
    try { $disk = Get-CimInstance Win32_LogicalDisk -Filter ("DeviceID='" + $letter + "'") -ErrorAction Stop } catch {}
    if (-not $disk) { return "Drive $letter does not exist on this computer ($what)." }
    if ([int]$disk.DriveType -eq 4) { return "Drive $letter is a network drive; the $what has to be on a disk of this computer." }
    if ([int]$disk.DriveType -eq 5) { return "Drive $letter is a CD/DVD drive ($what)." }
    try { $full = [IO.Path]::GetFullPath($path).TrimEnd('\') } catch { return "'$path' is not a valid folder name ($what)." }
    # never inside %LOCALAPPDATA%\CrystalPilot: Setup replaces the unpacked
    # installer there on every run and the uninstaller deletes the folder
    $setupRoot = (Join-Path $env:LOCALAPPDATA "CrystalPilot").TrimEnd('\')
    if ($full -eq $setupRoot -or $full.StartsWith($setupRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { return "The $what cannot be inside $setupRoot, the installer's own working folder (replaced every time Setup runs)." }
    if ($full -match '^[A-Za-z]:$') { return "Please choose a folder, not the whole drive $full, for the $what." }
    # the highest folder this check has to create, so it can be removed again afterwards
    $made = -not (Test-Path $full)
    $top = $full; while ((Split-Path $top -Parent) -and -not (Test-Path (Split-Path $top -Parent))) { $top = Split-Path $top -Parent }
    try {
        New-Item -ItemType Directory -Force -Path $full -ErrorAction Stop | Out-Null
        $probe = Join-Path $full ("cp-write-test-" + [guid]::NewGuid().ToString("N"))
        Set-Content -Path $probe -Value "x" -ErrorAction Stop; Remove-Item $probe -Force
    } catch {
        return "Cannot write to $full ($what): " + $_.Exception.Message + " Choose a folder you own (for example not under Program Files)."
    } finally {
        if ($made -and (Test-Path $top) -and -not (Get-ChildItem $top -Recurse -File -Force -ErrorAction SilentlyContinue)) { Remove-Item $top -Recurse -Force -ErrorAction SilentlyContinue }
    }
    return ""
}
function Test-InstallFolderContent([string]$path) {
    # the program folder must be empty, missing, or a CrystalPilot installation:
    # the uninstaller removes what it finds there
    if (-not (Test-Path $path)) { return "" }
    if (Test-Path (Join-Path $path "windows\crystalpilot.cfg")) { return "" }
    if (Test-Path (Join-Path $path "windows\CrystalPilot.bat")) { return "" }
    $items = @(Get-ChildItem $path -Force -ErrorAction SilentlyContinue)
    if ($items.Count -eq 0) { return "" }
    return "The program folder $path already contains other files. Choose an empty folder (Browse adds a CrystalPilot sub-folder by itself)."
}

function Invoke-Install {
    param($state, [scriptblock]$Log, [scriptblock]$Progress)
    # ok = CrystalPilot can be started; warnings = parts that are missing but optional
    $result = @{ ok = $false; reboot = $false; message = ""; warnings = @() }
    try {
        # ── 1. WSL platform ────────────────────────────────────────────────
        & $Log "Checking the Windows Subsystem for Linux ..."
        $vp = Get-VirtualizationProblem
        if ($vp) { throw $vp }
        foreach ($label in @("Install folder", "Runtime folder")) {
            $pth = if ($label -eq "Install folder") { [string]$state.installDir } else { [string]$state.runtimeDir }
            if ($label -eq "Runtime folder" -and $state.runtimeMode -ne "dedicated") { continue }
            $why = Test-FolderChoice $pth $label.ToLower()
            if ($why) { throw $why }
        }
        $why = Test-InstallFolderContent ([string]$state.installDir); if ($why) { throw $why }
        $ws = Get-WslState
        & $Log "    state: $ws"
        if ($ws -in @("missing", "novm")) {
            if ([bool]$state.wslEnableTried -and -not (Test-Admin)) {
                # enabled once already (and restarted): do not ask again in a loop, let the runtime step say what is wrong
                & $Log "WSL still reports '$ws' after it was enabled - trying to continue."
            } elseif (-not (Test-Admin)) {
                $result.message = "elevate"; return $result
            } else {
                $state.wslEnableTried = $true
                $er = Enable-WslPlatform $Log
                if ($er -eq "reboot") { & $Log "Windows must restart to finish enabling WSL."; $result.reboot = $true; $result.message = "reboot"; return $result }
                if ($er -like "error:*") { throw ("Enabling WSL failed - " + $er.Substring(6).Trim()) }
            }
        }
        & $Log "WSL is available."

        # ── 2. Linux runtime ───────────────────────────────────────────────
        $distro = Get-DistroName $state
        $have = @(Get-Distros)
        if ($state.runtimeMode -eq "existing") {
            if (-not ($have -contains $distro)) { throw "The Linux distribution '$distro' was not found." }
            & $Log "Using the existing Linux distribution '$distro'."
        } else {
            if ($have -contains $distro) {
                & $Log "The runtime '$distro' already exists - reusing it."
            } else {
                $rdir = [string]$state.runtimeDir
                if (Test-Path (Join-Path $rdir "ext4.vhdx")) {
                    # a disk left by an earlier attempt: wsl --import would refuse, after a 340 MB download
                    throw (Explain-WslError "ERROR_ALREADY_EXISTS" $rdir)
                }
                New-Item -ItemType Directory -Force -Path $rdir | Out-Null
                $tar = Join-Path $rdir $RootfsName
                # An image shipped with the package (the offline installer) or
                # already downloaded (Downloads, a previous run) is used as it is.
                if (-not (Test-Path $tar) -or (Get-Item $tar).Length -lt 100MB) {
                    $local = Find-Newest @($Here, $Root, (Get-DownloadsDir)) "ubuntu-*wsl*rootfs*.tar.gz"
                    if ($local -and (Get-Item $local).Length -gt 100MB) { & $Log "Using the runtime image found at $local"; $tar = $local }
                }
                if (-not (Test-Path $tar) -or (Get-Item $tar).Length -lt 100MB) {
                    & $Log "Downloading the Ubuntu 24.04 runtime image (about 340 MB) to $rdir - a few minutes on a normal connection ..."
                    Save-Download -Url $RootfsUrl -Dest $tar -Log $Log -Progress $Progress -What "the Ubuntu runtime image"
                    if ((Get-Item $tar).Length -lt 100MB) { Remove-Item $tar -Force -ErrorAction SilentlyContinue; throw "The Ubuntu runtime image did not download completely. Check the internet connection and run the installer again." }
                    & $Progress -1 "Runtime image downloaded"
                }
                & $Log "Creating the Linux runtime '$distro' in $rdir (1 to 3 minutes) ..."
                $imp = Invoke-Live "wsl.exe" @("--import", $distro, $rdir, $tar, "--version", "2") $Log
                if ($imp.rc -ne 0 -and $imp.text -match 'kernel|wsl.exe --update|WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED|update') {
                    & $Log "Updating WSL and trying again ..."
                    $null = Invoke-Live "wsl.exe" @("--update") $Log
                    $imp = Invoke-Live "wsl.exe" @("--import", $distro, $rdir, $tar, "--version", "2") $Log
                }
                if ($imp.rc -ne 0 -or -not (@(Get-Distros) -contains $distro)) { throw (Explain-WslError $imp.text $rdir) }
                # The Ubuntu image enables systemd, which breaks running Windows
                # programs (the CCP4 bridge) in an imported runtime.  CrystalPilot
                # does not need systemd: switch it off, keep interop on, restart once.
                $conf = "[boot]\nsystemd=false\n\n[interop]\nenabled=true\nappendWindowsPath=true\n\n[automount]\nenabled=true\n"
                $null = Invoke-WslLines @("-d", $distro, "-e", "sh", "-c", "printf '$conf' > /etc/wsl.conf")
                $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
                & wsl.exe --terminate $distro 2>&1 | Out-Null
                $ErrorActionPreference = $prev
                Start-Sleep -Seconds 2
                $state.runtimeCreated = $true
                & $Log "Runtime created."
            }
        }
        $probe = @(Invoke-WslLines @("-d", $distro, "-e", "sh", "-c", "echo WSLOK"))
        if (-not ($probe -join "").Contains("WSLOK")) { throw "The runtime '$distro' does not start. Try 'wsl --shutdown' and run the installer again." }

        # ── 3. Files on the Windows side ───────────────────────────────────
        $inst = [string]$state.installDir
        & $Log "Copying CrystalPilot files to $inst ..."
        New-Item -ItemType Directory -Force -Path (Join-Path $inst "windows") | Out-Null
        New-Item -ItemType Directory -Force -Path (Join-Path $inst "files") | Out-Null
        $app = [string]$state.app
        if (-not $app -or -not (Test-Path $app)) { throw "The CrystalPilot application file (xds-gui-vNNN.py) was not found." }
        $appDest = Join-Path (Join-Path $inst "files") (Split-Path $app -Leaf)
        if ((Resolve-Path $app).Path -ne $appDest) { Copy-Item -Force $app $appDest }
        foreach ($f in (Get-ChildItem -Path $Here -File | Where-Object { $_.Extension -in @(".ps1", ".bat", ".sh", ".html", ".md", ".ico") })) {
            $dest = Join-Path (Join-Path $inst "windows") $f.Name
            if ($f.FullName -ne $dest) { Copy-Item -Force $f.FullName $dest }
        }
        # The illustrated manual (docs\manual), served by the app at /manual/ when present
        $manSrc = Join-Path (Split-Path $Here -Parent) "docs\manual"
        if (Test-Path (Join-Path $manSrc "CrystalPilot-Manual.html")) {
            $manDst = Join-Path $inst "docs\manual"
            if ((Resolve-Path $manSrc).Path -ne $manDst) {
                New-Item -ItemType Directory -Force -Path $manDst | Out-Null
                foreach ($f in @("CrystalPilot-Manual.html", "CrystalPilot-Manual.pdf", "CrystalPilot-Manual.index.json", "README.md")) { $p = Join-Path $manSrc $f; if (Test-Path $p) { Copy-Item -Force $p (Join-Path $manDst $f) } }
                & $Log "Illustrated manual copied to $manDst"
            }
        }
        foreach ($src in @([string]$state.xdsTar, [string]$state.neggia)) {
            if ($src -and (Test-Path $src)) { $dest = Join-Path $inst (Split-Path $src -Leaf); if ((Resolve-Path $src).Path -ne $dest) { Copy-Item -Force $src $dest } }
        }
        $wHere = Join-Path $inst "windows"

        # ── 4. Linux side ──────────────────────────────────────────────────
        # A CrystalPilot still running in this runtime would keep serving the old
        # version after the update (the launcher only reopens a running server).
        $stopped = @(Invoke-WslLines @("-d", $distro, "-u", "root", "-e", "sh", "-c", "[ -x /usr/local/bin/crystalpilot ] && /usr/local/bin/crystalpilot stop"))
        if (($stopped -join " ") -match "stopped") { & $Log "Stopped the running CrystalPilot (it restarts with the new version at the end)." }
        & $Log $(if ([bool]$state.update -and $state.runtimeMode -eq "existing") { "Updating CrystalPilot inside '$distro' (Python packages are checked, XDS and CCP4 kept) - about 5 minutes ..." } else { "Installing inside the Linux runtime (Python packages, XDS, neggia, CCP4) - 5 to 15 minutes; the computer is busy while the Linux packages are unpacked ..." })
        $wa = @("-d", $distro, "-e", "bash", (ConvertTo-WslPath (Join-Path $wHere "wsl-install.sh") $distro),
                "--app", (ConvertTo-WslPath $appDest $distro),
                "--wrapper", (ConvertTo-WslPath (Join-Path $wHere "crystalpilot-wsl.sh") $distro),
                "--bridge", (ConvertTo-WslPath (Join-Path $wHere "ccp4win-run.sh") $distro),
                "--port", ([string]$state.port),
                "--projects", ([string]$state.projects))
        if ($state.xdsTar -and (Test-Path ([string]$state.xdsTar))) { $wa += @("--xds-tar", (ConvertTo-WslPath (Join-Path $inst (Split-Path ([string]$state.xdsTar) -Leaf)) $distro)) }
        if ($state.neggia -and (Test-Path ([string]$state.neggia))) { $wa += @("--neggia", (ConvertTo-WslPath (Join-Path $inst (Split-Path ([string]$state.neggia) -Leaf)) $distro)) }
        switch ([string]$state.ccp4Mode) {
            "windows" { if ($state.ccp4Win) { $wa += @("--ccp4-win", (ConvertTo-WslPath ([string]$state.ccp4Win) $distro)) } }
            "linux"   { if ($state.ccp4Tar -and (Test-Path ([string]$state.ccp4Tar))) { $wa += @("--ccp4-tar", (ConvertTo-WslPath ([string]$state.ccp4Tar) $distro)) } }
        }
        for ($i = 4; $i -lt $wa.Count; $i++) {
            # every Windows path must have a Linux name, or bash is started on an empty argument
            if ($wa[$i] -eq "" ) { throw "The runtime '$distro' cannot see the folder $inst (no /mnt path for it). Choose a program folder on a fixed local drive." }
        }
        $lin = Invoke-Live "wsl.exe" $wa $Log
        if ($lin.rc -ne 0) { & $Log "The Linux-side installer reported problems (see above). Continuing with the remaining steps." }
        # What the launcher will find: the same question CrystalPilot.bat asks
        $info = @{}
        foreach ($line in @(Invoke-WslLines @("-d", $distro, "-e", "/usr/local/bin/crystalpilot", "info"))) { $kv = $line.Split("=", 2); if ($kv.Count -eq 2) { $info[$kv[0]] = $kv[1] } }
        $pyOk = ($lin.text -match 'Python packages:\s+ok')
        if ($info["INSTALLED"] -ne "yes") {
            $result.message = "CrystalPilot was not installed inside the Linux runtime (the launcher would not find it). The log above shows the step that failed - most often no internet access from inside WSL (apt-get / pip)."
        } elseif (-not $pyOk) {
            $result.message = "The Python packages could not be installed inside the Linux runtime - most often no internet access from inside WSL (a proxy or VPN). Run the installer again once the connection works."
        }
        if ($info["XDS"] -ne "yes") { $result.warnings += "XDS is not installed: save XDS-gfortran_Linux_x86_64.tar.gz (xds.mr.mpg.de) to Downloads and run Setup again." }

        # ── 5. Configuration + shortcut ────────────────────────────────────
        $projWin = Get-ProjectsWinPath $state
        $driveLine = ""
        # Projects folder reachable from Explorer: desktop shortcut, Quick Access, optional drive letter
        if ($TestMode) { & $Log "(test installation: no shortcuts, no Quick Access pin, no drive letter, no Apps & features entry)" }
        if (-not $TestMode) { try {
            $desktop = [Environment]::GetFolderPath("Desktop")
            $shell = New-Object -ComObject WScript.Shell
            $ico = Join-Path $wHere "CrystalPilot.ico"
            $appIcon = if (Test-Path $ico) { $ico + ",0" } else { "%SystemRoot%\System32\imageres.dll,144" }
            # removed first: Explorer keeps showing the old icon of a shortcut that is only rewritten
            foreach ($old in @((Join-Path $desktop "CrystalPilot.lnk"), (Join-Path ([Environment]::GetFolderPath("Programs")) "CrystalPilot.lnk"), (Join-Path $inst "CrystalPilot.lnk"))) {
                Remove-Item -LiteralPath $old -Force -ErrorAction SilentlyContinue
            }
            $lnk = $shell.CreateShortcut((Join-Path $desktop "CrystalPilot.lnk"))
            $lnk.TargetPath = Join-Path $wHere "CrystalPilot.bat"
            $lnk.WorkingDirectory = $wHere
            $lnk.Description = "CrystalPilot - XDS processing interface"
            $lnk.IconLocation = $appIcon
            $lnk.Save()
            $lnk2 = $shell.CreateShortcut((Join-Path $desktop "CrystalPilot Projects.lnk"))
            $lnk2.TargetPath = $projWin
            $lnk2.Description = "CrystalPilot projects folder (inputs and results)"
            $lnk2.IconLocation = "%SystemRoot%\System32\imageres.dll,3"
            $lnk2.Save()
            $lnk3 = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Programs")) "CrystalPilot.lnk"))
            $lnk3.TargetPath = $lnk.TargetPath; $lnk3.WorkingDirectory = $wHere; $lnk3.Description = $lnk.Description; $lnk3.IconLocation = $lnk.IconLocation
            $lnk3.Save()
            # and one at the top of the program folder, where people look for "the program"
            $lnk4 = $shell.CreateShortcut((Join-Path $inst "CrystalPilot.lnk"))
            $lnk4.TargetPath = $lnk.TargetPath; $lnk4.WorkingDirectory = $wHere; $lnk4.Description = $lnk.Description; $lnk4.IconLocation = $lnk.IconLocation
            $lnk4.Save()
            # the desktop and Start menu read the new icon now, not after the next sign-in
            try { Start-Process -FilePath (Join-Path $env:SystemRoot "System32\ie4uinit.exe") -ArgumentList "-show" -WindowStyle Hidden -Wait -ErrorAction Stop } catch {}
            & $Log "Shortcuts created (desktop: CrystalPilot, CrystalPilot Projects; Start menu: CrystalPilot; $inst\CrystalPilot)."
        } catch { & $Log ("Could not create the shortcuts: " + $_.Exception.Message) } }
        if (-not $TestMode) { try {
            $sh = New-Object -ComObject Shell.Application
            $ns = $sh.Namespace($projWin)
            if ($ns) { $ns.Self.InvokeVerb("pintohome"); & $Log "Projects folder pinned to Quick Access in Explorer." }
        } catch { & $Log ("Could not pin the projects folder to Quick Access: " + $_.Exception.Message) } }
        if ([bool]$state.mapDrive -and -not $TestMode) {
            $letter = ([string]$state.driveLetter).Trim().TrimEnd(':').ToUpper()
            if (-not $letter) { $letter = "P" }
            # Windows can map a drive letter to the runtime's root share (\\wsl.localhost\<distro>)
            # but not to one of its sub-folders, and Explorer cannot enter Linux symlinks through
            # the share.  A bind mount /Projects = <projects folder> inside the runtime (kept in
            # /etc/fstab, so it comes back at every start) makes the projects appear as P:\Projects\...
            $share = "\\wsl.localhost\$distro"
            $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
            $projLinux = ([string]$state.projects).TrimEnd('/')
            $linkOk = $false; $linkErr = ""
            if ($projLinux -eq "/Projects") { $linkOk = $true }
            else {
                & wsl.exe -d $distro -u root -e test -L /Projects 2>$null
                if ($LASTEXITCODE -eq 0) { & wsl.exe -d $distro -u root -e unlink /Projects 2>$null }   # leftover link
                $src = (& wsl.exe -d $distro -u root -e findmnt -n -o SOURCE /Projects 2>$null | Out-String).Trim()
                $mounted = ($src -ne "")
                if ($mounted -and $src -notmatch [regex]::Escape("[" + $projLinux + "]")) {      # bound to another folder: redo
                    & wsl.exe -d $distro -u root -e umount /Projects 2>$null; $mounted = $false
                }
                if (-not $mounted) {
                    & wsl.exe -d $distro -u root -e mkdir -p /Projects 2>$null
                    $busy = (& wsl.exe -d $distro -u root -e ls -A /Projects 2>$null | Out-String).Trim()
                    if ($busy) { $linkErr = "/Projects already exists in the runtime and is not empty" }
                    else {
                        $lo = (& wsl.exe -d $distro -u root -e mount --bind $projLinux /Projects 2>&1 | Out-String)
                        if ($LASTEXITCODE -eq 0) { $mounted = $true } else { $linkErr = ($lo -replace "\s+", " ").Trim() }
                    }
                }
                if ($mounted) {
                    $linkOk = $true
                    # one fstab line for /Projects, always the current folder
                    & wsl.exe -d $distro -u root -e sed -i '\#[[:space:]]/Projects[[:space:]]#d' /etc/fstab 2>$null
                    # (written from inside the runtime: text piped from PowerShell would carry a BOM)
                    & wsl.exe -d $distro -u root -e sh -c 'echo $1 /Projects none bind 0 0 >> /etc/fstab' sh $projLinux 2>$null
                }
            }
            $ErrorActionPreference = $prev
            $sub = "\Projects"
            if (-not $linkOk) { $sub = ($projLinux -replace '/', '\'); & $Log ("Could not present the projects folder as /Projects in the runtime (" + $linkErr + "); the drive will show the full path.") }
            $used = Get-UsedDriveLetters
            if ($used -contains $letter) {
                # keep an existing mapping to the same runtime, otherwise pick the next free letter
                $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
                $cur = (& net use ($letter + ":") 2>$null | Out-String)
                $ErrorActionPreference = $prev
                if ($cur -notmatch [regex]::Escape($share) -and $cur -notmatch [regex]::Escape('\\wsl$\' + $distro)) {
                    $free = Get-FreeDriveLetters
                    if ($free.Count -gt 0) { & $Log "Drive $letter`: is in use - using $($free[0]): instead."; $letter = [string]$free[0] } else { $letter = "" }
                } else { & $Log "Drive $letter`: already points to the Linux runtime." }
            }
            if ($letter) {
                $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
                $out = (& net use ($letter + ":") $share /persistent:yes 2>&1 | Out-String)
                $rcNet = $LASTEXITCODE
                if ($rcNet -ne 0 -and $out -notmatch "already|error 85") {
                    $out = (& net use ($letter + ":") ('\\wsl$\' + $distro) /persistent:yes 2>&1 | Out-String); $rcNet = $LASTEXITCODE
                }
                $ErrorActionPreference = $prev
                if ($rcNet -eq 0 -or $out -match "already|error 85") { $driveLine = $letter + ":" + $sub; & $Log ("Projects folder available as " + $driveLine + "\") }
                else { & $Log ("Could not map drive $letter`: " + ($out -replace "\s+", " ").Trim() + " - use the desktop shortcut or Quick Access instead.") }
            }
        }
        $created = if ([bool]$state.runtimeCreated) { "1" } else { "0" }
        @("DISTRO=$distro", "PORT=$([string]$state.port)", "INSTALL_DIR=$inst", "PROJECTS=$([string]$state.projects)", "PROJECTS_WIN=$projWin", "DRIVE=$driveLine",
          "RUNTIME_DIR=$([string]$state.runtimeDir)", "RUNTIME_CREATED=$created") | Set-Content -Path (Join-Path $wHere "crystalpilot.cfg") -Encoding ASCII
        $state.driveMapped = $driveLine
        # Apps & features: name, version, and the uninstaller next to the launcher
        if (-not $TestMode) { try {
            $ver = "0"
            $vm = [regex]::Match((Get-Content $appDest -Raw), 'VERSION\s*=\s*"([^"]+)"'); if ($vm.Success) { $ver = $vm.Groups[1].Value }
            $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\CrystalPilot"
            New-Item -Path $key -Force | Out-Null
            # the installed copy keeps whatever download mark this one has, so the same policy rule holds for it
            $un = 'powershell.exe -NoProfile -ExecutionPolicy ' + (Get-ScriptPolicy) + ' -STA -File "' + (Join-Path $wHere "CrystalPilot-Uninstall.ps1") + '"'
            Set-ItemProperty -Path $key -Name DisplayName -Value "CrystalPilot"
            Set-ItemProperty -Path $key -Name DisplayVersion -Value $ver
            Set-ItemProperty -Path $key -Name Publisher -Value "Mikael Elias"
            Set-ItemProperty -Path $key -Name InstallLocation -Value $inst
            Set-ItemProperty -Path $key -Name DisplayIcon -Value "%SystemRoot%\System32\imageres.dll,144"
            Set-ItemProperty -Path $key -Name UninstallString -Value $un
            Set-ItemProperty -Path $key -Name NoModify -Value 1 -Type DWord
            Set-ItemProperty -Path $key -Name NoRepair -Value 1 -Type DWord
            Set-ItemProperty -Path $key -Name EstimatedSize -Value 2500000 -Type DWord
            & $Log "Registered in Apps & features (version $ver) with an uninstaller."
        } catch { & $Log ("Could not register the uninstaller: " + $_.Exception.Message) } }
        if ($result.message) {
            & $Log ("ERROR: " + $result.message)
        } else {
            $result.ok = $true
            $result.message = "done"
        }
        foreach ($w in $result.warnings) { & $Log ("NOTE: " + $w) }
        return $result
    } catch {
        $result.message = $_.Exception.Message
        & $Log ("ERROR: " + $_.Exception.Message)
        return $result
    }
}
function Get-ProjectsWinPath($state) {
    $d = Get-DistroName $state
    return "\\wsl.localhost\$d" + (([string]$state.projects) -replace '/', '\')
}
function Get-UsedDriveLetters {
    # The letters Windows has handed out, plus remembered network mappings that are
    # not connected right now.  Only the letters are read: Get-PSDrive (used before
    # 0.6.6e) asked every network drive about itself and took 24 s on a PC with
    # a slow share - the setup window waited for it.
    $l = @([System.IO.DriveInfo]::GetDrives() | ForEach-Object { $_.Name.Substring(0, 1).ToUpper() })
    try { $l += @(Get-ChildItem "HKCU:\Network" -ErrorAction Stop | ForEach-Object { $_.PSChildName.Substring(0, 1).ToUpper() }) } catch {}
    return @($l | Sort-Object -Unique)
}
function Get-FreeDriveLetters { $used = Get-UsedDriveLetters; return @([char[]]([char]'D'..[char]'Z') | ForEach-Object { [string]$_ } | Where-Object { $used -notcontains $_ }) }
# After the restart WSL may need, setup is continued from a Start-menu entry the
# user opens, not started by itself at log-in: a RunOnce key that relaunches a
# hidden PowerShell is exactly how malware survives a reboot, and antivirus
# heuristics weigh an installer that writes one accordingly.
function Get-ResumeShortcutPath { return (Join-Path ([Environment]::GetFolderPath("Programs")) "Continue CrystalPilot Setup.lnk") }
function Register-Resume($statePath) {
    if ($TestMode) { return }
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Get-ResumeShortcutPath))
    $lnk.TargetPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $lnk.Arguments = "-NoProfile -ExecutionPolicy " + (Get-ScriptPolicy) + " -STA -WindowStyle Hidden -File `"$PSCommandPath`" -Resume `"$statePath`""
    $lnk.WorkingDirectory = $Here
    $ico = Join-Path $Here "CrystalPilot.ico"
    $lnk.IconLocation = if (Test-Path $ico) { $ico + ",0" } else { "%SystemRoot%\System32\imageres.dll,144" }
    $lnk.Description = "Finish installing CrystalPilot after the restart"
    $lnk.Save()
}
function Unregister-Resume {
    if ($TestMode) { return }
    Remove-Item -LiteralPath (Get-ResumeShortcutPath) -Force -ErrorAction SilentlyContinue
    # the entry an earlier version of this installer left behind
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce" -Name "CrystalPilotSetup" -ErrorAction SilentlyContinue
}

# ══════════════════════════════════════════════════════════════════════════════
#  Unattended mode
# ══════════════════════════════════════════════════════════════════════════════
if ($Unattended) {
    $state = New-DefaultState
    if ($Config) {
        $cfg = Load-State $Config
        foreach ($k in $cfg.Keys) { $state[$k] = $cfg[$k] }
    }
    Write-Host "CrystalPilot unattended install"
    Write-Host ("  install folder : " + $state.installDir)
    Write-Host ("  runtime        : " + $state.runtimeMode + " / " + (Get-DistroName $state) + $(if ($state.runtimeMode -eq "dedicated") { " at " + $state.runtimeDir } else { "" }))
    Write-Host ("  projects       : " + $state.projects + "   (" + (Get-ProjectsWinPath $state) + ")")
    Write-Host ("  drive letter   : " + $(if ([bool]$state.mapDrive) { [string]$state.driveLetter + ":" } else { "none" }))
    Write-Host ("  XDS / neggia   : " + $state.xdsTar + " / " + $state.neggia)
    Write-Host ("  CCP4           : " + $state.ccp4Mode + " " + $(if ($state.ccp4Mode -eq "windows") { $state.ccp4Win } elseif ($state.ccp4Mode -eq "linux") { $state.ccp4Tar } else { "" }))
    $r = Invoke-Install -state $state -Log { param($m) Write-Host $m } -Progress { param($p, $m) Write-Host ("  " + $m) }
    if ($r.message -eq "elevate") { Write-Host "WSL is not enabled and this session is not elevated. Run this from an administrator PowerShell."; exit 3 }
    if ($r.reboot) { Write-Host "Restart Windows, then run the installer again."; exit 4 }
    if (-not $r.ok) { Write-Host ("Finished with problems: " + $r.message); exit 1 }
    Write-Host ("Done. Start with: " + (Join-Path (Join-Path $state.installDir "windows") "CrystalPilot.bat"))
    exit 0
}

if ($Probe) {
    # run by the wizard in the background while its first window says what is going on
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $s = New-DefaultState
    $s.probeSeconds = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    Save-State $s $Probe
    exit 0
}

# ══════════════════════════════════════════════════════════════════════════════
#  Wizard (WinForms) - modern dark layout: artwork sidebar with the step list,
#  card-based pages, flat accent buttons.  All installation logic is above.
# ══════════════════════════════════════════════════════════════════════════════
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
# Setup.exe starts this hidden: an error nobody catches must not end it without a word.
trap {
    $err = $_
    $errFile = Join-Path $SetupDataDir "setup-error.txt"
    try { New-Item -ItemType Directory -Force -Path $SetupDataDir | Out-Null; Add-Content -Path $errFile -Encoding UTF8 -Value ((Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "  wizard " + $WizardVersion + ": " + $err.Exception.Message + "`r`n" + $err.InvocationInfo.PositionMessage + "`r`n" + $err.ScriptStackTrace) } catch {}
    try { [System.Windows.Forms.MessageBox]::Show("CrystalPilot Setup stopped because of an unexpected error:`n`n" + $err.Exception.Message + "`n`nThe details are in $errFile", "CrystalPilot Setup", "OK", "Error") | Out-Null } catch {}
    exit 1
}
[System.Windows.Forms.Application]::EnableVisualStyles()

# Preview pictures go into the published manual: they show an example machine,
# never the drives, folders and programs of the computer that renders them.
if ($Preview) {
    function Get-FixedDrives { return @([pscustomobject]@{ Letter = "C:"; FreeGB = 212; SizeGB = 476; Label = "" }, [pscustomobject]@{ Letter = "D:"; FreeGB = 1650; SizeGB = 1863; Label = "" }) }
    function Get-UsedDriveLetters { return @("C", "D") }
    function Get-Distros { return @("Ubuntu") }
    function Get-InstalledConfig { return $null }
    function Get-WslInstall([string]$distro) { return $null }
    function Get-ShortcutFolders { return @() }
    function Find-XdsTar { return "C:\Downloads\XDS-gfortran_Linux_x86_64.tar.gz" }
    function Find-Neggia { return "C:\Downloads\dectris-neggia.so" }
    function Find-WindowsCcp4 { return "C:\CCP4-9\9.0" }
    function Find-Ccp4Tar { return "" }
}
function Test-Present([string]$p) { if ($Preview) { return [bool]$p }; return [bool]($p -and (Test-Path $p)) }

# First window, at once: looking at WSL, the disks and an installed CrystalPilot
# takes from a few seconds to a minute, and 0.6.6d showed nothing at all meanwhile.
# The looking is done by a second copy of this script (-Probe); this window keeps
# moving until it is done.
$splash = $null
function Show-Splash {
    $f = New-Object System.Windows.Forms.Form
    $f.FormBorderStyle = "None"; $f.StartPosition = "CenterScreen"; $f.ClientSize = New-Object System.Drawing.Size(480, 176)
    $f.BackColor = [System.Drawing.Color]::FromArgb(10, 16, 30); $f.ShowInTaskbar = $true; $f.Text = "CrystalPilot Setup"
    $t = New-Object System.Windows.Forms.Label; $t.Text = "CrystalPilot Setup"; $t.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 15)
    $t.ForeColor = [System.Drawing.Color]::FromArgb(110, 168, 255); $t.Location = New-Object System.Drawing.Point(24, 20); $t.Size = New-Object System.Drawing.Size(430, 32); $f.Controls.Add($t)
    $m = New-Object System.Windows.Forms.Label
    $m.Text = "Checking this computer: WSL, the disks and an installed CrystalPilot.`r`nThis can take up to a minute - the setup window opens by itself."
    $m.Font = New-Object System.Drawing.Font("Segoe UI", 9.75); $m.ForeColor = [System.Drawing.Color]::FromArgb(226, 232, 240)
    $m.Location = New-Object System.Drawing.Point(24, 62); $m.Size = New-Object System.Drawing.Size(440, 44); $f.Controls.Add($m)
    $pb = New-Object System.Windows.Forms.ProgressBar; $pb.Style = "Marquee"; $pb.MarqueeAnimationSpeed = 25
    $pb.Location = New-Object System.Drawing.Point(24, 118); $pb.Size = New-Object System.Drawing.Size(432, 14); $f.Controls.Add($pb)
    $c = New-Object System.Windows.Forms.Label; $c.Name = "clock"; $c.Text = ""; $c.Font = New-Object System.Drawing.Font("Segoe UI", 8.75)
    $c.ForeColor = [System.Drawing.Color]::FromArgb(143, 163, 199); $c.Location = New-Object System.Drawing.Point(24, 142); $c.Size = New-Object System.Drawing.Size(432, 20); $f.Controls.Add($c)
    $f.Add_Shown({ if ($StartedHidden) { $this.WindowState = "Minimized"; $this.WindowState = "Normal" }; $this.TopMost = $true; $this.Activate() })
    $f.Show(); [System.Windows.Forms.Application]::DoEvents()
    return $f
}
$state = $null
if ($Resume -and (Test-Path $Resume)) { $state = Load-State $Resume }
elseif ($Preview) { $state = New-DefaultState }
else {
    $splash = Show-Splash
    $probeFile = Join-Path $env:TEMP ("cp-setup-probe-" + [guid]::NewGuid().ToString("N") + ".json")
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $pa = @("-NoProfile", "-ExecutionPolicy", (Get-ScriptPolicy), "-File", $PSCommandPath, "-Probe", $probeFile); if ($NoLaunch) { $pa += "-NoLaunch" }
    $psi.Arguments = ConvertTo-ArgString $pa
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $pp = [System.Diagnostics.Process]::Start($psi)
        $clock = $splash.Controls["clock"]
        while (-not $pp.HasExited -and $sw.Elapsed.TotalSeconds -lt 240) {
            [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 40
            $clock.Text = "Checking ... " + (Format-Elapsed $sw.Elapsed)
        }
        if (-not $pp.HasExited) { try { $pp.Kill() } catch {} }
    } catch {}
    if (Test-Path $probeFile) {
        try { $state = Load-State $probeFile } catch { $state = $null }
        Remove-Item $probeFile -Force -ErrorAction SilentlyContinue
    }
    $script:ProbeSeconds = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    if (-not $state -and $sw.Elapsed.TotalSeconds -ge 240) {
        # WSL (or a disk) did not answer for 4 minutes; asking it again here would
        # hang this window with nothing on the screen but a frozen splash
        $splash.Close()
        [void][System.Windows.Forms.MessageBox]::Show("CrystalPilot Setup could not examine this computer: the Windows Subsystem for Linux did not answer within 4 minutes.`n`nRestart Windows (a pending WSL update often causes this), then run the setup again.", "CrystalPilot Setup", "OK", "Warning")
        exit 1
    }
    if (-not $state) { $splash.Controls["clock"].Text = "Checking ... (second try)"; [System.Windows.Forms.Application]::DoEvents(); $state = New-DefaultState }
    $splash.Controls["clock"].Text = "Opening the setup window ..."; [System.Windows.Forms.Application]::DoEvents()
}
if (-not $state.ContainsKey("update")) { $state.update = $false }
$IsUpdate = [bool]$state.update
if (-not $Resume -and $Config -and (Test-Path $Config)) {
    # wizard.ps1 -Config choices.json: the pages open with these choices filled in
    $pre = Load-State $Config; foreach ($k in $pre.Keys) { $state[$k] = $pre[$k] }
}
$StatePath = Join-Path $SetupDataDir "setup-state.json"
New-Item -ItemType Directory -Force -Path (Split-Path $StatePath) | Out-Null

# ── palette ──────────────────────────────────────────────────────────────────
$C = @{
    bg      = [System.Drawing.Color]::FromArgb(10, 16, 30)
    side    = [System.Drawing.Color]::FromArgb(5, 9, 20)
    card    = [System.Drawing.Color]::FromArgb(17, 26, 46)
    field   = [System.Drawing.Color]::FromArgb(11, 18, 34)
    border  = [System.Drawing.Color]::FromArgb(36, 50, 78)
    text    = [System.Drawing.Color]::FromArgb(226, 232, 240)
    dim     = [System.Drawing.Color]::FromArgb(143, 163, 199)
    accent  = [System.Drawing.Color]::FromArgb(110, 168, 255)
    accent2 = [System.Drawing.Color]::FromArgb(180, 140, 255)
    ok      = [System.Drawing.Color]::FromArgb(104, 211, 145)
    warn    = [System.Drawing.Color]::FromArgb(246, 173, 85)
    err     = [System.Drawing.Color]::FromArgb(252, 129, 129)
    white   = [System.Drawing.Color]::White
}
$FontUI    = New-Object System.Drawing.Font("Segoe UI", 9.75)
$FontSmall = New-Object System.Drawing.Font("Segoe UI", 8.75)
$FontH1    = New-Object System.Drawing.Font("Segoe UI Semibold", 19)
$FontH2    = New-Object System.Drawing.Font("Segoe UI Semibold", 10.5)
$FontMono  = New-Object System.Drawing.Font("Consolas", 9)
$FontBrand = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)

# artwork for the sidebar: a plain image file next to this script.  (It used to
# be decoded out of splash.html's base64 text, and decoding base64 into bytes is
# one more thing an antivirus heuristic scores a script on.)
$Artwork = $null
try {
    $art = Join-Path $Here "wizard-art.jpg"
    if (Test-Path $art) { $Artwork = [System.Drawing.Image]::FromFile($art) }
} catch { $Artwork = $null }

# ── form ─────────────────────────────────────────────────────────────────────
$W = 940; $H = 620; $SideW = 270
$form = New-Object System.Windows.Forms.Form
$form.Text = "CrystalPilot Setup"
$form.ClientSize = New-Object System.Drawing.Size($W, $H)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedSingle"; $form.MaximizeBox = $false
$form.BackColor = $C.bg; $form.ForeColor = $C.text; $form.Font = $FontUI

$order  = @("welcome", "choices", "components", "install", "finish")
$titles = @{ welcome = $(if ($IsUpdate) { @("Update CrystalPilot", "The installed CrystalPilot is updated in place; your projects and settings are kept") } else { @("Install CrystalPilot", "Sensible settings are chosen for you; Customize if you want to change them") }); choices = @("Options", "Folders, Linux runtime, port and drive letter"); components = @("Components", "XDS, the Eiger reader and CCP4 - found by themselves when possible"); install = @("Installing", "This can take several minutes"); finish = @("All set", "CrystalPilot is ready") }
$stepNames = @("Welcome", "Options", "Components", "Install", "Finish")
$script:express = $true      # the Options page is skipped until Customize... is clicked
$script:page = 0

# sidebar (owner-drawn: artwork, gradient, brand, step list)
$side = New-Object System.Windows.Forms.Panel
$side.Location = New-Object System.Drawing.Point(0, 0); $side.Size = New-Object System.Drawing.Size($SideW, $H); $side.BackColor = $C.side
$form.Controls.Add($side)
$side.Add_Paint({
    $g = $_.Graphics
    $g.SmoothingMode = "AntiAlias"; $g.TextRenderingHint = "ClearTypeGridFit"
    if ($Artwork) {
        # left third of the artwork (beam cone and rings), scaled to the sidebar height
        $srcW = [int]($Artwork.Width * 0.42); $scale = $H / $Artwork.Height
        $dstW = [int]($srcW * $scale)
        $g.DrawImage($Artwork, (New-Object System.Drawing.Rectangle(0, 0, $dstW, $H)), (New-Object System.Drawing.Rectangle(0, 0, $srcW, $Artwork.Height)), [System.Drawing.GraphicsUnit]::Pixel)
    }
    $br = New-Object System.Drawing.Drawing2D.LinearGradientBrush((New-Object System.Drawing.Rectangle(0, 0, $SideW, $H)), [System.Drawing.Color]::FromArgb(150, 5, 9, 20), [System.Drawing.Color]::FromArgb(235, 5, 9, 20), 90)
    $g.FillRectangle($br, 0, 0, $SideW, $H)
    $g.DrawString("CRYSTALPILOT", $FontBrand, (New-Object System.Drawing.SolidBrush($C.accent)), 22, 26)
    $g.DrawString("Setup", $FontSmall, (New-Object System.Drawing.SolidBrush($C.dim)), 24, 52)
    $y = 120
    for ($i = 0; $i -lt $stepNames.Count; $i++) {
        $isCur = ($i -eq $script:page); $done = ($i -lt $script:page)
        $col = if ($isCur) { $C.accent } elseif ($done) { $C.ok } else { $C.border }
        $pen = New-Object System.Drawing.Pen($col, 1.5)
        $g.DrawEllipse($pen, 24, $y, 22, 22)
        if ($isCur -or $done) { $g.FillEllipse((New-Object System.Drawing.SolidBrush($col)), 24, $y, 22, 22) }
        $numBrush = if ($isCur -or $done) { New-Object System.Drawing.SolidBrush($C.side) } else { New-Object System.Drawing.SolidBrush($C.dim) }
        $lbl = if ($done) { [string][char]0x2713 } else { [string]($i + 1) }
        $g.DrawString($lbl, $FontSmall, $numBrush, 29, ($y + 3))
        $tb = if ($isCur) { New-Object System.Drawing.SolidBrush($C.text) } else { New-Object System.Drawing.SolidBrush($C.dim) }
        $g.DrawString($stepNames[$i], $(if ($isCur) { $FontH2 } else { $FontUI }), $tb, 58, ($y + 1))
        if ($i -lt $stepNames.Count - 1) { $g.DrawLine((New-Object System.Drawing.Pen($C.border, 1)), 35, ($y + 24), 35, ($y + 44)) }
        $y += 46
    }
    $g.DrawString("Mikael Elias", $FontSmall, (New-Object System.Drawing.SolidBrush($C.dim)), 24, ($H - 34))
})

# content header
$header = New-Object System.Windows.Forms.Label
$header.Location = New-Object System.Drawing.Point(($SideW + 34), 26); $header.Size = New-Object System.Drawing.Size(($W - $SideW - 60), 36); $header.Font = $FontH1; $header.ForeColor = $C.text
$form.Controls.Add($header)
$sub = New-Object System.Windows.Forms.Label
$sub.Location = New-Object System.Drawing.Point(($SideW + 36), 64); $sub.Size = New-Object System.Drawing.Size(($W - $SideW - 60), 20); $sub.ForeColor = $C.dim
$form.Controls.Add($sub)

$pages = @{}
$PX = $SideW + 34; $PY = 98; $PW = $W - $SideW - 62; $PH = $H - 98 - 78
foreach ($n in $order) {
    $p = New-Object System.Windows.Forms.Panel
    $p.Location = New-Object System.Drawing.Point($PX, $PY); $p.Size = New-Object System.Drawing.Size($PW, $PH); $p.Visible = $false; $p.BackColor = $C.bg
    $form.Controls.Add($p); $pages[$n] = $p
}

# footer line + buttons
$footLine = New-Object System.Windows.Forms.Panel
$footLine.Location = New-Object System.Drawing.Point($SideW, ($H - 66)); $footLine.Size = New-Object System.Drawing.Size(($W - $SideW), 1); $footLine.BackColor = $C.border
$form.Controls.Add($footLine)
function New-Btn([string]$text, [int]$x, [int]$y, [int]$w, [int]$h, [bool]$primary) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text; $b.Location = New-Object System.Drawing.Point($x, $y); $b.Size = New-Object System.Drawing.Size($w, $h)
    $b.FlatStyle = "Flat"; $b.FlatAppearance.BorderSize = 1; $b.Font = $FontUI; $b.Cursor = "Hand"
    if ($primary) { $b.BackColor = $C.accent; $b.ForeColor = $C.side; $b.FlatAppearance.BorderColor = $C.accent; $b.FlatAppearance.MouseOverBackColor = [System.Drawing.Color]::FromArgb(140, 188, 255) }
    else { $b.BackColor = $C.bg; $b.ForeColor = $C.text; $b.FlatAppearance.BorderColor = $C.border; $b.FlatAppearance.MouseOverBackColor = $C.card }
    return $b
}
$btnBack   = New-Btn "Back"   ($W - 340) ($H - 50) 92 34 $false
$btnNext   = New-Btn "Next"   ($W - 238) ($H - 50) 118 34 $true
$btnCancel = New-Btn "Cancel" ($W - 110) ($H - 50) 84 34 $false
foreach ($b in @($btnBack, $btnNext, $btnCancel)) { $form.Controls.Add($b) }
$btnCancel.Add_Click({ $form.Close() })

# ── widgets ──────────────────────────────────────────────────────────────────
function New-Card($parent, [int]$x, [int]$y, [int]$w, [int]$h, [string]$title) {
    $card = New-Object System.Windows.Forms.Panel
    $card.Location = New-Object System.Drawing.Point($x, $y); $card.Size = New-Object System.Drawing.Size($w, $h); $card.BackColor = $C.card
    $card.Add_Paint({ $g = $_.Graphics; $g.DrawRectangle((New-Object System.Drawing.Pen($C.border)), 0, 0, ($this.Width - 1), ($this.Height - 1)) })
    if ($title) {
        $t = New-Object System.Windows.Forms.Label; $t.Text = $title; $t.Location = New-Object System.Drawing.Point(14, 10); $t.Size = New-Object System.Drawing.Size(($w - 28), 20); $t.Font = $FontH2; $t.ForeColor = $C.text
        $card.Controls.Add($t)
    }
    $parent.Controls.Add($card); return $card
}
function New-Lbl([string]$text, [int]$x, [int]$y, [int]$w, [int]$h, $color, $font) {
    $l = New-Object System.Windows.Forms.Label; $l.Text = $text; $l.Location = New-Object System.Drawing.Point($x, $y); $l.Size = New-Object System.Drawing.Size($w, $h)
    $l.ForeColor = $(if ($color) { $color } else { $C.dim }); if ($font) { $l.Font = $font } else { $l.Font = $FontSmall }; return $l
}
function New-Field([string]$text, [int]$x, [int]$y, [int]$w) {
    # a bordered panel around a borderless TextBox = themable input
    $wrap = New-Object System.Windows.Forms.Panel; $wrap.Location = New-Object System.Drawing.Point($x, $y); $wrap.Size = New-Object System.Drawing.Size($w, 28); $wrap.BackColor = $C.field
    $wrap.Add_Paint({ $_.Graphics.DrawRectangle((New-Object System.Drawing.Pen($C.border)), 0, 0, ($this.Width - 1), ($this.Height - 1)) })
    $t = New-Object System.Windows.Forms.TextBox; $t.Text = $text; $t.BorderStyle = "None"; $t.BackColor = $C.field; $t.ForeColor = $C.text; $t.Font = $FontUI
    $t.Location = New-Object System.Drawing.Point(8, 5); $t.Size = New-Object System.Drawing.Size(($w - 16), 20)
    $wrap.Controls.Add($t)
    $t | Add-Member -NotePropertyName Wrap -NotePropertyValue $wrap -Force
    return $t
}
function New-Small([string]$text, [int]$x, [int]$y, [int]$w) { return (New-Btn $text $x $y $w 28 $false) }
function New-Radio([string]$text, [int]$x, [int]$y, [int]$w) {
    $r = New-Object System.Windows.Forms.RadioButton; $r.Text = $text; $r.Location = New-Object System.Drawing.Point($x, $y); $r.Size = New-Object System.Drawing.Size($w, 24); $r.ForeColor = $C.text; $r.FlatStyle = "Flat"; $r.Cursor = "Hand"; return $r
}
function New-Dot([int]$x, [int]$y, $color) {
    $d = New-Object System.Windows.Forms.Panel; $d.Location = New-Object System.Drawing.Point($x, $y); $d.Size = New-Object System.Drawing.Size(10, 10); $d.BackColor = $C.card
    $d | Add-Member -NotePropertyName DotColor -NotePropertyValue $color -Force
    $d.Add_Paint({ $g = $_.Graphics; $g.SmoothingMode = "AntiAlias"; $g.FillEllipse((New-Object System.Drawing.SolidBrush($this.DotColor)), 0, 0, 9, 9) })
    return $d
}
function Set-Dot($dot, $color) { $dot.DotColor = $color; $dot.Invalidate() }
function Pick-Folder([string]$start) {
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog; $dlg.Description = "Choose a folder"; if ($start -and (Test-Path $start)) { $dlg.SelectedPath = $start }
    if ($dlg.ShowDialog($form) -eq "OK") { return $dlg.SelectedPath } else { return "" }
}
function Pick-File([string]$filter) {
    $dlg = New-Object System.Windows.Forms.OpenFileDialog; $dlg.Filter = $filter; $dlg.InitialDirectory = Get-DownloadsDir
    if ($dlg.ShowDialog($form) -eq "OK") { return $dlg.FileName } else { return "" }
}

# ── Page 1: welcome (express) ────────────────────────────────────────────────
$p1 = $pages["welcome"]
$card = New-Card $p1 0 0 $PW 186 $(if ($IsUpdate) { "What this update does" } else { "What this installer does" })
$tb = New-Object System.Windows.Forms.TextBox
$tb.Multiline = $true; $tb.ReadOnly = $true; $tb.ScrollBars = "Vertical"; $tb.BorderStyle = "None"; $tb.Text = $(if ($IsUpdate) { $UpdateText } else { $DisclosureText }).Replace("`n", "`r`n")
$tb.Location = New-Object System.Drawing.Point(14, 34); $tb.Size = New-Object System.Drawing.Size(($PW - 28), 142); $tb.BackColor = $C.card; $tb.ForeColor = $C.text; $tb.Font = $FontSmall
$tb.TabStop = $false          # otherwise it takes the focus and opens with all its text selected
$card.Controls.Add($tb)
$ecard = New-Card $p1 0 196 $PW 176 $(if ($IsUpdate) { "Ready to update with these settings" } else { "Ready to install with these settings" })
$lblExpress = New-Lbl "" 14 36 ($PW - 156) 132 $C.text $FontMono; $ecard.Controls.Add($lblExpress)
$bCustomize = New-Small "Customize..." ($PW - 130) 32 116; $ecard.Controls.Add($bCustomize)
$lblDisks = New-Lbl "" 2 382 $PW 18 $C.dim $FontSmall; $p1.Controls.Add($lblDisks)
$wslNote = switch ($state.wslState) {
    "missing"  { "WSL is not enabled on this computer yet. It will be enabled (administrator approval, then one restart of Windows)." }
    "novm"     { "WSL is present but the Virtual Machine Platform is not enabled yet. It will be enabled (administrator approval, then one restart of Windows)." }
    "nodistro" { "WSL is enabled but no Linux runtime exists yet. A dedicated CrystalPilot runtime will be created." }
    default    { "WSL is enabled. A dedicated CrystalPilot runtime is created so nothing is changed in your other Linux distributions (Customize to reuse one)." }
}
if ($IsUpdate) {
    $from = if ([string]$state.installedVersion) { "CrystalPilot " + $state.installedVersion } else { "CrystalPilot" }
    $wslNote = $from + " is installed in '" + $state.distro + "'. It is updated to " + $(if ($state.newVersion) { $state.newVersion } else { "this version" }) + " in place - no new Linux runtime, no large download. About 5 minutes."
}
$vpNote = if ($state.ContainsKey("vpNote")) { [string]$state.vpNote } else { Get-VirtualizationProblem }
if ($vpNote) { $wslNote = $vpNote }
$p1.Controls.Add((New-Lbl $wslNote 2 404 $PW 36 $(if ($vpNote) { $C.err } else { $C.accent }) $FontSmall))

# ── Page 2: location ─────────────────────────────────────────────────────────
$p2 = $pages["choices"]
$c1 = New-Card $p2 0 0 $PW 76 "Install folder (Windows side: program, launcher, shortcut target)"
$txtInstall = New-Field $state.installDir 14 36 ($PW - 130); $c1.Controls.Add($txtInstall.Wrap)
$bInstall = New-Small "Browse" ($PW - 106) 36 92; $c1.Controls.Add($bInstall)
$bInstall.Add_Click({ $f = Pick-Folder $txtInstall.Text; if ($f) { $txtInstall.Text = (Join-Path $f "CrystalPilot") } })

$c2 = New-Card $p2 0 86 $PW 158 "Linux runtime (where Ubuntu, XDS and your projects live)"
$rbExisting = New-Radio "Use an existing Linux distribution:" 14 36 250; $c2.Controls.Add($rbExisting)
$cmbDistro = New-Object System.Windows.Forms.ComboBox; $cmbDistro.Location = New-Object System.Drawing.Point(270, 36); $cmbDistro.Size = New-Object System.Drawing.Size(220, 26); $cmbDistro.DropDownStyle = "DropDownList"; $cmbDistro.FlatStyle = "Flat"; $cmbDistro.BackColor = $C.field; $cmbDistro.ForeColor = $C.text
$c2.Controls.Add($cmbDistro)
$distros = @(); if ($state.wslState -eq "ok") { $distros = @($state.distros | Where-Object { $_ }); if ($distros.Count -eq 0) { $distros = @(Get-Distros) } }
foreach ($d in $distros) { [void]$cmbDistro.Items.Add($d) }
if ($distros.Count -gt 0) { $cmbDistro.SelectedIndex = 0 } else { $rbExisting.Enabled = $false; $cmbDistro.Enabled = $false }
if ($state.distro -and ($distros -contains $state.distro)) { $cmbDistro.SelectedItem = $state.distro }
$rbDedicated = New-Radio "Create a dedicated CrystalPilot runtime (Ubuntu 24.04, 340 MB download) in:" 14 66 560; $c2.Controls.Add($rbDedicated)
$txtRuntime = New-Field $state.runtimeDir 34 94 ($PW - 150); $c2.Controls.Add($txtRuntime.Wrap)
$bRuntime = New-Small "Browse" ($PW - 106) 94 92; $c2.Controls.Add($bRuntime)
$bRuntime.Add_Click({ $f = Pick-Folder $txtRuntime.Text; if ($f) { $txtRuntime.Text = (Join-Path $f "CrystalPilot-wsl") } })
$lblRuntimeFree = New-Lbl "" 34 126 ($PW - 60) 18 $C.dim $FontSmall; $c2.Controls.Add($lblRuntimeFree)
if ($state.runtimeMode -eq "existing" -and $rbExisting.Enabled) { $rbExisting.Checked = $true } else { $rbDedicated.Checked = $true }

$c3 = New-Card $p2 0 254 $PW 122 "Projects folder inside the Linux runtime"
$c3.Controls.Add((New-Lbl "All input frames and all results of a project live here. Copy your data into a project folder before processing." 14 32 ($PW - 28) 18 $C.dim $FontSmall))
$txtProjects = New-Field $state.projects 14 56 ($PW - 28); $c3.Controls.Add($txtProjects.Wrap)
$lblProjWin = New-Lbl "" 14 90 ($PW - 28) 20 $C.accent $FontSmall; $c3.Controls.Add($lblProjWin)

$c4 = New-Card $p2 0 386 220 62 "Port of the web interface"
$txtPort = New-Field ([string]$state.port) 14 30 90; $c4.Controls.Add($txtPort.Wrap)
$c5 = New-Card $p2 232 386 ($PW - 232) 62 "Explorer access"
$chkDrive = New-Object System.Windows.Forms.CheckBox; $chkDrive.Text = "Also show the projects folder as drive"; $chkDrive.Location = New-Object System.Drawing.Point(14, 30); $chkDrive.Size = New-Object System.Drawing.Size(250, 24); $chkDrive.ForeColor = $C.text; $chkDrive.FlatStyle = "Flat"; $chkDrive.Cursor = "Hand"
$chkDrive.Checked = [bool]$state.mapDrive; $c5.Controls.Add($chkDrive)
$cmbDrive = New-Object System.Windows.Forms.ComboBox; $cmbDrive.Location = New-Object System.Drawing.Point(268, 29); $cmbDrive.Size = New-Object System.Drawing.Size(56, 26); $cmbDrive.DropDownStyle = "DropDownList"; $cmbDrive.FlatStyle = "Flat"; $cmbDrive.BackColor = $C.field; $cmbDrive.ForeColor = $C.text
foreach ($L in (Get-FreeDriveLetters)) { [void]$cmbDrive.Items.Add($L + ":") }
$pref = ([string]$state.driveLetter).TrimEnd(':').ToUpper() + ":"
# an update keeps its letter: it is "in use" by the installation itself (the
# install step keeps the mapping when it points at the same runtime)
if ($IsUpdate -and [bool]$state.mapDrive -and $pref -match '^[D-Z]:$' -and -not $cmbDrive.Items.Contains($pref)) { $cmbDrive.Items.Insert(0, $pref) }
if ($cmbDrive.Items.Contains($pref)) { $cmbDrive.SelectedItem = $pref } elseif ($cmbDrive.Items.Count -gt 0) { $cmbDrive.SelectedIndex = 0 }
$c5.Controls.Add($cmbDrive)
$chkDrive.Add_CheckedChanged({ $cmbDrive.Enabled = $chkDrive.Checked })
$cmbDrive.Enabled = $chkDrive.Checked

$updateRuntimeLabels = {
    $name = if ($rbDedicated.Checked) { $state.newDistro } else { [string]$cmbDistro.SelectedItem }
    if ($rbDedicated.Checked) {
        $free = Get-FreeGB $txtRuntime.Text
        $need = 3; if ($state.ccp4Mode -eq "linux") { $need = 13 }
        if ($free -ne $null) { $lblRuntimeFree.Text = "Free space on that drive: $free GB  (about $need GB needed)"; $lblRuntimeFree.ForeColor = $(if ($free -lt $need) { $C.err } else { $C.dim }) } else { $lblRuntimeFree.Text = "" }
        $txtRuntime.Enabled = $true; $bRuntime.Enabled = $true
        if ($txtProjects.Text -match '^/home/[^/]+/') { $txtProjects.Text = "/root/crystalpilot_projects" }
    } else { $lblRuntimeFree.Text = ""; $txtRuntime.Enabled = $false; $bRuntime.Enabled = $false }
    $winPath = "\\wsl.localhost\$name" + ($txtProjects.Text -replace '/', '\')
    $lblProjWin.Text = if ($chkDrive.Checked -and $cmbDrive.SelectedItem) { "Seen from Windows as   " + ([string]$cmbDrive.SelectedItem) + "\Projects\   (also " + $winPath + ")" } else { "Seen from Windows as   " + $winPath }
}
$rbDedicated.Add_CheckedChanged($updateRuntimeLabels); $rbExisting.Add_CheckedChanged($updateRuntimeLabels)
$cmbDistro.Add_SelectedIndexChanged({ if ($rbExisting.Checked -and $cmbDistro.SelectedItem) { $h = Get-WslHome ([string]$cmbDistro.SelectedItem); $txtProjects.Text = $h.TrimEnd('/') + "/crystalpilot_projects" }; & $updateRuntimeLabels })
$txtRuntime.Add_TextChanged($updateRuntimeLabels); $txtProjects.Add_TextChanged($updateRuntimeLabels)
$chkDrive.Add_CheckedChanged($updateRuntimeLabels); $cmbDrive.Add_SelectedIndexChanged($updateRuntimeLabels)
& $updateRuntimeLabels

# ── Page 3: components - a checklist that fills itself ───────────────────────
$p3 = $pages["components"]
$p3.Controls.Add((New-Lbl "Files you save to your Downloads folder are picked up by themselves - nothing to type. XDS and the Eiger reader are free for academic use but come from their authors, so this installer cannot include them." 0 0 $PW 34 $C.dim $FontSmall))
function New-CompRow($parent, [int]$y, [int]$h, [string]$title, [string]$why, [int]$whyW, [int]$whyH) {
    # whyW/whyH: the description's box; rows with buttons top-right keep it narrow
    if (-not $whyW) { $whyW = $PW - 300 }; if (-not $whyH) { $whyH = 18 }
    $card = New-Card $parent 0 $y $PW $h ""
    $dot = New-Dot 14 15 $C.warn; $card.Controls.Add($dot)
    $card.Controls.Add((New-Lbl $title 30 10 ($PW - 320) 20 $C.text $FontH2))
    $card.Controls.Add((New-Lbl $why 30 30 $whyW $whyH $C.dim $FontSmall))
    $st = New-Lbl "" 30 (32 + $whyH) ($PW - 60) 40 $C.dim $FontSmall; $card.Controls.Add($st)
    return @{ card = $card; dot = $dot; status = $st }
}
$rowXds = New-CompRow $p3 40 96 "XDS" "The processing programs (required)."
$txtXds = New-Object System.Windows.Forms.TextBox; $txtXds.Text = [string]$state.xdsTar; $txtXds.Visible = $false; $rowXds.card.Controls.Add($txtXds)
$bXdsWeb = New-Small "Get it (download page)" ($PW - 280) 12 172; $rowXds.card.Controls.Add($bXdsWeb); $bXdsWeb.Add_Click({ Start-Process $XdsUrl })
$bXds = New-Small "Choose file" ($PW - 104) 12 90; $rowXds.card.Controls.Add($bXds); $bXds.Add_Click({ $f = Pick-File "XDS package (*.tar.gz)|*.tar.gz"; if ($f) { $txtXds.Text = $f } })

$rowNeg = New-CompRow $p3 146 96 "Eiger reader (neggia)" "Only for Eiger .h5 data; placed next to XDS."
$txtNeggia = New-Object System.Windows.Forms.TextBox; $txtNeggia.Text = [string]$state.neggia; $txtNeggia.Visible = $false; $rowNeg.card.Controls.Add($txtNeggia)
$bNegWeb = New-Small "Get it (download page)" ($PW - 280) 12 172; $rowNeg.card.Controls.Add($bNegWeb); $bNegWeb.Add_Click({ Start-Process $NeggiaUrl })
$bNeg = New-Small "Choose file" ($PW - 104) 12 90; $rowNeg.card.Controls.Add($bNeg); $bNeg.Add_Click({ $f = Pick-File "neggia library|dectris-neggia.so|All files|*.*"; if ($f) { $txtNeggia.Text = $f } })

$rowCcp4 = New-CompRow $p3 252 178 "CCP4" "Optional: POINTLESS, AIMLESS, CTRUNCATE and the MTZ export through f2mtz. XDS, XSCALE and XDSCONV work without it." ($PW - 60) 34
$k3 = $rowCcp4.card
$rowCcp4.status.Size = New-Object System.Drawing.Size(($PW - 60), 18)
$rbCcp4Win = New-Radio "CCP4 for Windows installed at:" 30 88 250; $k3.Controls.Add($rbCcp4Win)
$txtCcp4Win = New-Field $state.ccp4Win 286 86 ($PW - 400); $k3.Controls.Add($txtCcp4Win.Wrap)
$bCcp4Win = New-Small "Browse" ($PW - 106) 86 92; $k3.Controls.Add($bCcp4Win); $bCcp4Win.Add_Click({ $f = Pick-Folder $txtCcp4Win.Text; if ($f) { $txtCcp4Win.Text = $f } })
$rbCcp4Lin = New-Radio "Linux CCP4 package (about 10 GB):" 30 116 250; $k3.Controls.Add($rbCcp4Lin)
$txtCcp4Tar = New-Field $state.ccp4Tar 286 114 ($PW - 400); $k3.Controls.Add($txtCcp4Tar.Wrap)
$bCcp4Tar = New-Small "Browse" ($PW - 106) 114 92; $k3.Controls.Add($bCcp4Tar); $bCcp4Tar.Add_Click({ $f = Pick-File "CCP4 Linux package (*.tar.gz)|*.tar.gz"; if ($f) { $txtCcp4Tar.Text = $f } })
$rbCcp4Skip = New-Radio $(if ($IsUpdate) { "Keep the installed CCP4 (or none)" } else { "Not now (can be added later)" }) 30 144 250; $k3.Controls.Add($rbCcp4Skip)
$bCcp4Web = New-Small "Get it (download page)" ($PW - 186) 142 172; $k3.Controls.Add($bCcp4Web); $bCcp4Web.Add_Click({ Start-Process $Ccp4Url })
switch ($state.ccp4Mode) { "windows" { $rbCcp4Win.Checked = $true } "linux" { $rbCcp4Lin.Checked = $true } default { $rbCcp4Skip.Checked = $true } }
if (-not $state.ccp4Win) { $rbCcp4Win.Enabled = $false }

$updateCompLabels = {
    if (Test-Present $txtXds.Text) { $rowXds.status.Text = "Found: " + $txtXds.Text; $rowXds.status.ForeColor = $C.ok; Set-Dot $rowXds.dot $C.ok; $bXdsWeb.Visible = $false }
    elseif ($IsUpdate -and $state.runtimeMode -eq "existing") { $rowXds.status.Text = "The installed XDS is kept. Choose a file only to replace it with a newer XDS."; $rowXds.status.ForeColor = $C.ok; Set-Dot $rowXds.dot $C.ok; $bXdsWeb.Visible = $true }
    else { $rowXds.status.Text = "Not found yet. Click Get it and save XDS-gfortran_Linux_x86_64.tar.gz to Downloads - this line turns green by itself. CrystalPilot also installs without it (add XDS later)."; $rowXds.status.ForeColor = $C.warn; Set-Dot $rowXds.dot $C.warn; $bXdsWeb.Visible = $true }
    if (Test-Present $txtNeggia.Text) { $rowNeg.status.Text = "Found: " + $txtNeggia.Text; $rowNeg.status.ForeColor = $C.ok; Set-Dot $rowNeg.dot $C.ok; $bNegWeb.Visible = $false }
    elseif ($IsUpdate -and $state.runtimeMode -eq "existing") { $rowNeg.status.Text = "The installed Eiger reader (if any) is kept. Choose a file only to replace it."; $rowNeg.status.ForeColor = $C.dim; Set-Dot $rowNeg.dot $C.dim; $bNegWeb.Visible = $true }
    else { $rowNeg.status.Text = "Not found - skip it unless your detector is an Eiger. Save dectris-neggia.so to Downloads and this line turns green."; $rowNeg.status.ForeColor = $C.dim; Set-Dot $rowNeg.dot $C.dim; $bNegWeb.Visible = $true }
    if ($rbCcp4Win.Checked) { $rowCcp4.status.Text = "Your CCP4 for Windows will be used through the runtime."; $rowCcp4.status.ForeColor = $C.ok; Set-Dot $rowCcp4.dot $C.ok }
    elseif ($rbCcp4Lin.Checked) { $rowCcp4.status.Text = "The Linux package will be installed inside the runtime (about 10 GB of disk)."; $rowCcp4.status.ForeColor = $C.ok; Set-Dot $rowCcp4.dot $C.ok }
    elseif ($IsUpdate -and $state.runtimeMode -eq "existing") { $rowCcp4.status.Text = "The CCP4 CrystalPilot uses now (if any) is kept."; $rowCcp4.status.ForeColor = $C.dim; Set-Dot $rowCcp4.dot $C.dim }
    else { $rowCcp4.status.Text = "Not installed now. Save the Linux package (ccp4-*-linux64.tar.gz) to Downloads and it is picked up; or run this installer again later."; $rowCcp4.status.ForeColor = $C.dim; Set-Dot $rowCcp4.dot $C.dim }
}
& $updateCompLabels
$txtXds.Add_TextChanged($updateCompLabels); $txtNeggia.Add_TextChanged($updateCompLabels)
foreach ($rb in @($rbCcp4Win, $rbCcp4Lin, $rbCcp4Skip)) { $rb.Add_CheckedChanged($updateCompLabels) }
$watch = New-Object System.Windows.Forms.Timer; $watch.Interval = 2000
$watch.Add_Tick({
    if (-not $pages["components"].Visible) { return }
    if (-not ($txtXds.Text -and (Test-Path $txtXds.Text))) { $f = Find-XdsTar; if ($f) { $txtXds.Text = $f } }
    if (-not ($txtNeggia.Text -and (Test-Path $txtNeggia.Text))) { $f = Find-Neggia; if ($f) { $txtNeggia.Text = $f } }
    if (-not ($txtCcp4Tar.Text -and (Test-Path $txtCcp4Tar.Text))) { $f = Find-Ccp4Tar; if ($f) { $txtCcp4Tar.Text = $f; if ($rbCcp4Skip.Checked) { $rbCcp4Lin.Checked = $true } } }
})
$watch.Start()

# ── Page 4: install ──────────────────────────────────────────────────────────
$p4 = $pages["install"]
$lblStep = New-Lbl "Ready to install." 0 0 ($PW - 120) 22 $C.text $FontH2; $p4.Controls.Add($lblStep)
$lblClock = New-Lbl "" ($PW - 120) 2 120 20 $C.dim $FontSmall; $lblClock.TextAlign = "TopRight"; $p4.Controls.Add($lblClock)
$script:installWatch = $null
$progWrap = New-Object System.Windows.Forms.Panel; $progWrap.Location = New-Object System.Drawing.Point(0, 30); $progWrap.Size = New-Object System.Drawing.Size($PW, 6); $progWrap.BackColor = $C.border; $p4.Controls.Add($progWrap)
$progBar = New-Object System.Windows.Forms.Panel; $progBar.Location = New-Object System.Drawing.Point(0, 0); $progBar.Size = New-Object System.Drawing.Size(0, 6); $progBar.BackColor = $C.accent; $progWrap.Controls.Add($progBar)
$script:progPct = -1; $script:marqueeX = 0
$marquee = New-Object System.Windows.Forms.Timer; $marquee.Interval = 40
$marquee.Add_Tick({
    if ($script:progPct -lt 0) { $script:marqueeX = ($script:marqueeX + 8) % ($PW + 160); $progBar.Location = New-Object System.Drawing.Point(($script:marqueeX - 160), 0); $progBar.Width = 160 }
    if ($script:installWatch) { $lblClock.Text = "working  " + (Format-Elapsed $script:installWatch.Elapsed) }
})
$logCard = New-Card $p4 0 46 $PW ($PH - 46) ""
$logBox = New-Object System.Windows.Forms.TextBox; $logBox.Multiline = $true; $logBox.ReadOnly = $true; $logBox.ScrollBars = "Vertical"; $logBox.WordWrap = $false; $logBox.BorderStyle = "None"
$logBox.Location = New-Object System.Drawing.Point(10, 10); $logBox.Size = New-Object System.Drawing.Size(($PW - 20), ($PH - 66)); $logBox.BackColor = $C.card; $logBox.ForeColor = $C.text; $logBox.Font = $FontMono
$logCard.Controls.Add($logBox)

# ── Page 5: finish ───────────────────────────────────────────────────────────
$p5 = $pages["finish"]
$fcard = New-Card $p5 0 0 $PW 262 "Summary"
$lblDone = New-Lbl "" 14 36 ($PW - 28) 216 $C.text $FontUI; $lblDone.Font = $FontMono; $fcard.Controls.Add($lblDone)
$bStart = New-Btn "Start CrystalPilot now" 0 274 220 36 $true; $p5.Controls.Add($bStart)
$bOpenProjects = New-Btn "Open the projects folder" 232 274 200 36 $false; $p5.Controls.Add($bOpenProjects)
$bShowLog = New-Btn "Show the install log" 444 274 ($PW - 444) 36 $false; $p5.Controls.Add($bShowLog)
$lblFinishHint = New-Lbl "" 0 322 $PW 52 $C.dim $FontSmall; $p5.Controls.Add($lblFinishHint)
$script:outcome = "ok"          # ok | warn | fail - decides the finish page's title and buttons
$script:installing = $false
$LogPath = Join-Path $SetupDataDir "install-log.txt"

# ── Navigation ───────────────────────────────────────────────────────────────
# The express summary on the welcome page is what the Options page currently says.
$updateExpress = {
    Read-Choices
    $rt = if ($state.runtimeMode -eq "dedicated") { "'" + $state.newDistro + "' (new Ubuntu 24.04 runtime) in " + $state.runtimeDir } else { "existing distribution '" + $state.distro + "'" }
    if ($state.runtimeMode -eq "dedicated" -and (@(Get-Distros) -contains [string]$state.newDistro)) { $rt = "'" + $state.newDistro + "' (already present - will be updated)" }
    $pv = if ([bool]$state.mapDrive) { [string]$state.driveLetter + ":\Projects\   (" + (Get-ProjectsWinPath $state) + ")" } else { Get-ProjectsWinPath $state }
    $cc = switch ([string]$state.ccp4Mode) { "windows" { "CCP4 for Windows at " + $state.ccp4Win } "linux" { "Linux package, about 10 GB" } default { if ($IsUpdate -and $state.runtimeMode -eq "existing") { "kept as installed" } else { "not now (can be added later)" } } }
    $lblExpress.Text = ("Program folder   {0}`r`nLinux runtime    {1}`r`nProjects         {2}`r`nInterface        http://localhost:{3}`r`nCCP4             {4}" -f $state.installDir, $rt, $pv, $state.port, $cc)
    if ($IsUpdate -and $state.runtimeMode -eq "existing" -and [string]$cmbDistro.SelectedItem -eq [string]$state.distro) {
        $lblExpress.Text += ("`r`nVersion          {0}  ->  {1}" -f $(if ($state.installedVersion) { $state.installedVersion } else { "installed" }), $state.newVersion)
    }
    $free = Get-FreeGB ([string]$state.runtimeDir); $need = 3; if ($state.ccp4Mode -eq "linux") { $need = 13 }
    $parts = @(); foreach ($d in (Get-FixedDrives)) { $parts += ("{0} {1} GB free" -f $d.Letter, $d.FreeGB) }
    $short = ($free -ne $null -and $free -lt $need)
    $lblDisks.Text = "Disk space:  " + ($parts -join "    ") + $(if ($short) { "    - not enough where the runtime goes (about $need GB needed): click Customize" } else { "" })
    $lblDisks.ForeColor = $(if ($short) { $C.warn } else { $C.dim })
}
function Show-Page([int]$i) {
    $script:page = $i
    if ($i -eq 0) { & $updateExpress }
    foreach ($k in $pages.Keys) { $pages[$k].Visible = ($k -eq $order[$i]) }
    $header.Text = $titles[$order[$i]][0]; $sub.Text = $titles[$order[$i]][1]
    # While installing there is nothing to click: no Finish/Next that looks
    # ready, no Cancel that would leave a half-made runtime (closing is refused too).
    # (computed, never read back from .Visible: that reads False until the window is on screen)
    $showBack = ($i -gt 0 -and $i -lt 3); $showNext = ($i -ne 3); $showCancel = ($i -lt 3)
    $btnBack.Visible = $showBack; $btnBack.Enabled = $showBack
    $btnNext.Visible = $showNext; $btnNext.Enabled = $showNext
    $btnCancel.Visible = $showCancel; $btnCancel.Enabled = $showCancel
    $btnNext.Text = if ($i -eq 0) { "Continue" } elseif ($i -eq 2) { if ($IsUpdate -and $state.runtimeMode -eq "existing") { "Update" } else { "Install" } } elseif ($i -ge 3) { "Close" } else { "Next" }
    $side.Invalidate()
}
function Read-Choices {
    $state.installDir = $txtInstall.Text.Trim()
    $state.runtimeMode = if ($rbDedicated.Checked) { "dedicated" } else { "existing" }
    $state.distro = [string]$cmbDistro.SelectedItem
    $state.runtimeDir = $txtRuntime.Text.Trim()
    $state.projects = $txtProjects.Text.Trim()
    $p = 0; if ([int]::TryParse($txtPort.Text.Trim(), [ref]$p) -and $p -gt 0) { $state.port = $p } else { $state.port = 8000 }
    $state.xdsTar = $txtXds.Text.Trim(); $state.neggia = $txtNeggia.Text.Trim()
    $state.ccp4Mode = if ($rbCcp4Win.Checked) { "windows" } elseif ($rbCcp4Lin.Checked) { "linux" } else { "skip" }
    $state.ccp4Win = $txtCcp4Win.Text.Trim(); $state.ccp4Tar = $txtCcp4Tar.Text.Trim()
    $state.acknowledged = $true          # Continue on the welcome page, under the notice
    $state.mapDrive = $chkDrive.Checked
    $state.driveLetter = if ($cmbDrive.SelectedItem) { ([string]$cmbDrive.SelectedItem).TrimEnd(':') } else { "P" }
}
function Test-Choices {
    # the folders are checked before anything is downloaded or created
    $why = Test-FolderChoice $txtInstall.Text.Trim() "program folder"
    if (-not $why) { $why = Test-InstallFolderContent $txtInstall.Text.Trim() }
    if (-not $why -and $rbDedicated.Checked) { $why = Test-FolderChoice $txtRuntime.Text.Trim() "runtime folder" }
    if (-not $why -and $rbDedicated.Checked -and (Test-Path (Join-Path $txtRuntime.Text.Trim() "ext4.vhdx")) -and -not (@(Get-Distros) -contains [string]$state.newDistro)) {
        $why = Explain-WslError "ERROR_ALREADY_EXISTS" $txtRuntime.Text.Trim()
    }
    if ($why) { [System.Windows.Forms.MessageBox]::Show($why, "CrystalPilot Setup", "OK", "Warning") | Out-Null; return $false }
    return $true
}
function Show-Finish($r) {
    $inst = [string]$state.installDir
    $bat = Join-Path (Join-Path $inst "windows") "CrystalPilot.bat"
    $script:outcome = if (-not $r.ok) { "fail" } elseif (@($r.warnings).Count -gt 0) { "warn" } else { "ok" }
    $summary = @()
    switch ($script:outcome) {
        "fail" {
            $titles["finish"] = @("Installation did not complete", "Nothing is ready to start yet - the reason is below")
            $summary += "What went wrong:"
            $summary += ""
            $summary += [string]$r.message
            $summary += ""
            $summary += "Fix that, then click 'Try again' (your choices are kept)."
            $summary += "Install log: $LogPath"
        }
        default {
            $titles["finish"] = if ($script:outcome -eq "ok") { if ($IsUpdate -and $state.runtimeMode -eq "existing") { @("Updated", ("CrystalPilot " + $state.newVersion + " is installed and ready; projects and settings are as they were")) } else { @("All set", "CrystalPilot is installed and ready") } } else { @("Installed, with notes", "CrystalPilot starts; some optional parts are missing") }
            $summary += "Program folder    " + $inst
            $summary += "Start with        'CrystalPilot' on the desktop, Start menu or program folder"
            $summary += "Linux runtime     " + (Get-DistroName $state) + $(if ($state.runtimeMode -eq "dedicated") { "  (" + $state.runtimeDir + ")" } else { "" })
            $summary += "Projects folder   " + $(if ($state.driveMapped) { $state.driveMapped + "\   (" + (Get-ProjectsWinPath $state) + ")" } else { Get-ProjectsWinPath $state })
            $summary += "Interface         http://localhost:" + $state.port
            foreach ($w in @($r.warnings)) { $summary += ""; $summary += "Note: " + $w }
        }
    }
    $lblDone.Text = ($summary -join "`r`n")
    $lblDone.ForeColor = if ($script:outcome -eq "fail") { $C.err } else { $C.text }
    $lblDone.Font = if ($script:outcome -eq "fail") { $FontUI } else { $FontMono }
    if ($script:outcome -eq "fail") {
        $bStart.Text = "Try again"; $bStart.Enabled = $true
        $bOpenProjects.Text = "Change settings"; $bOpenProjects.Enabled = $true
        $lblFinishHint.Text = "Try again repeats the installation with the same choices; Change settings goes back to the options. Nothing half-made is started."
    } else {
        $bStart.Text = "Start CrystalPilot now"; $bStart.Enabled = (Test-Path $bat)
        $bOpenProjects.Text = "Open the projects folder"; $bOpenProjects.Enabled = $true
        $lblFinishHint.Text = "Copy your diffraction frames into a project folder, then start CrystalPilot from the desktop or Start menu. Close this installer - it is not needed while CrystalPilot runs. The Environment screen inside the app shows what was found."
    }
    Show-Page 4
}
function Start-Installation {
    Read-Choices
    if (-not $Resume -and -not (Test-Choices)) { Show-Page 2; return }
    Save-State $state $StatePath
    $watch.Stop()
    $est = if ($state.runtimeMode -eq "existing" -and $IsUpdate) { "about 5 minutes" }
           elseif ($state.runtimeMode -eq "existing" -or (@(Get-Distros) -contains [string]$state.newDistro)) { "about 10 minutes" }
           else { "15 to 30 minutes (a 340 MB download, then the Linux runtime is set up)" }
    $titles["install"] = @($(if ($IsUpdate -and $state.runtimeMode -eq "existing") { "Updating" } else { "Installing" }), ("This takes " + $est + " - the bar and the clock keep moving while it works"))
    $script:installWatch = [Diagnostics.Stopwatch]::StartNew()
    Show-Page 3
    $script:installing = $true
    $script:progPct = -1; $marquee.Start(); $progBar.BackColor = $C.accent
    $logBox.Clear()
    try { Set-Content -Path $LogPath -Value ("CrystalPilot setup log  " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "  (wizard " + $WizardVersion + ", " + [Environment]::OSVersion.VersionString + ")") -Encoding UTF8 } catch {}
    $script:Pump = { [System.Windows.Forms.Application]::DoEvents() }
    $log = { param($m) $line = ($m -replace "`r", ""); $logBox.AppendText($line + "`r`n"); try { Add-Content -Path $LogPath -Value $line -Encoding UTF8 } catch {}; $t = ($line -replace '^\s+', ''); if ($t) { $lblStep.Text = $t.Substring(0, [Math]::Min(100, $t.Length)) }; [System.Windows.Forms.Application]::DoEvents() }
    # a percentage fills the bar; -1 (a step of unknown length) makes it run back and forth again
    $progress = { param($pct, $m) if ($pct -ge 0 -and $pct -le 100) { $script:progPct = $pct; $progBar.Location = New-Object System.Drawing.Point(0, 0); $progBar.Width = [Math]::Max(6, [int]($PW * $pct / 100)) } else { $script:progPct = -1 }; if ($m) { $lblStep.Text = $m }; [System.Windows.Forms.Application]::DoEvents() }
    $r = Invoke-Install -state $state -Log $log -Progress $progress
    if ($r.message -eq "elevate") {
        # Only enabling WSL runs as administrator, in a separate small window;
        # this wizard stays the user's own process, so the runtime, shortcuts and
        # drive letter belong to the person installing, not to the admin account.
        & $log "Administrator approval is needed to enable WSL. Please confirm the Windows prompt ..."
        $statusFile = Join-Path (Split-Path $StatePath) "enable-wsl.txt"
        Remove-Item $statusFile -Force -ErrorAction SilentlyContinue
        $proc = $null
        try { $proc = Start-Process powershell.exe -Verb RunAs -PassThru -ArgumentList (ConvertTo-ArgString @("-NoProfile", "-ExecutionPolicy", (Get-ScriptPolicy), "-File", $PSCommandPath, "-EnableWsl", $statusFile)) } catch { $proc = $null }
        if (-not $proc) {
            $r = @{ ok = $false; reboot = $false; warnings = @(); message = "Administrator approval was refused, so WSL could not be enabled. Click Try again and accept the Windows prompt (an administrator of this computer has to confirm it)." }
        } else {
            while (-not $proc.HasExited) { [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 200 }
            $lines = @(); if (Test-Path $statusFile) { $lines = @(Get-Content $statusFile -Encoding UTF8) }
            $res = "error: the administrator step ended without a result"
            foreach ($l in $lines) { if ($l -like "RESULT=*") { $res = $l.Substring(7) } else { & $log $l } }
            $state.wslEnableTried = $true
            Save-State $state $StatePath
            if ($res -eq "reboot") { $r = @{ ok = $false; reboot = $true; warnings = @(); message = "reboot" } }
            elseif ($res -eq "ok") { $script:installing = $false; Start-Installation; return }
            else { $r = @{ ok = $false; reboot = $false; warnings = @(); message = ("Enabling WSL failed: " + $res.Substring([Math]::Min(6, $res.Length)).Trim()) } }
        }
    }
    $script:installing = $false
    $marquee.Stop(); if ($script:installWatch) { $script:installWatch.Stop(); $lblClock.Text = "took " + (Format-Elapsed $script:installWatch.Elapsed) }; $progBar.Location = New-Object System.Drawing.Point(0, 0); $progBar.Width = $PW; $progBar.BackColor = $(if ($r.ok) { $C.ok } else { $C.warn })
    if ($r.reboot) {
        Register-Resume $StatePath
        & $log "Windows needs to restart. Afterwards, open 'Continue CrystalPilot Setup' from the Start menu."
        $titles["finish"] = @("Restart needed", "Windows has to restart once to finish enabling WSL")
        $lblDone.ForeColor = $C.text; $lblDone.Font = $FontUI
        $lblDone.Text = "WSL has been enabled. Windows must restart before the Linux runtime can be created.`r`n`r`nAfter the restart, open the Start menu and click 'Continue CrystalPilot Setup'. The installer picks up where it stopped; your choices are kept."
        $bStart.Text = "Restart now"; $bStart.Enabled = $true
        $bOpenProjects.Text = "Restart later"; $bOpenProjects.Enabled = $true
        $lblFinishHint.Text = "Save your work in other programs before restarting."
        $script:outcome = "reboot"
        Show-Page 4
        return
    }
    try { if (Test-Path (Join-Path $state.installDir "windows")) { Copy-Item $LogPath (Join-Path $state.installDir "windows\install-log.txt") -Force } } catch {}
    # finished: the Start-menu entry that continues setup has done its job.  On a
    # failure it stays, so closing the wizard does not lose the way back in.
    if ($r.ok) { Unregister-Resume }
    Show-Finish $r
}
$bStart.Add_Click({
    switch ($script:outcome) {
        "fail"   { Start-Installation }
        "reboot" { Start-Process shutdown.exe -ArgumentList @("/r", "/t", "5"); $form.Close() }
        default  {
            $bat = Join-Path (Join-Path $state.installDir "windows") "CrystalPilot.bat"
            if (Test-Path $bat) { Start-Process $bat -WorkingDirectory (Split-Path $bat) }
            else { [System.Windows.Forms.MessageBox]::Show("The launcher was not found at $bat.`n`nThe installation is incomplete - see the install log.", "CrystalPilot Setup", "OK", "Error") | Out-Null }
        }
    }
})
$bOpenProjects.Add_Click({
    switch ($script:outcome) {
        "fail"   { $script:express = $false; Show-Page 1 }
        "reboot" { $form.Close() }
        default  { try { $target = if ($state.driveMapped) { $state.driveMapped + "\" } else { Get-ProjectsWinPath $state }; Start-Process explorer.exe $target } catch {} }
    }
})
$bShowLog.Add_Click({ if (Test-Path $LogPath) { Start-Process notepad.exe -ArgumentList (ConvertTo-ArgString @($LogPath)) } })
$form.Add_FormClosing({
    if ($script:installing) {
        $_.Cancel = $true
        [System.Windows.Forms.MessageBox]::Show("The installation is still running. Please wait until it has finished - closing now would leave a half-made installation.", "CrystalPilot Setup", "OK", "Information") | Out-Null
    }
})
$bCustomize.Add_Click({ $script:express = $false; Show-Page 1 })
$btnBack.Add_Click({
    if ($script:page -eq 2 -and $script:express) { Show-Page 0 }        # the Options page was never shown
    elseif ($script:page -gt 0) { Show-Page ($script:page - 1) }
})
$btnNext.Add_Click({
    switch ($script:page) {
        0 { if ($script:express) { Show-Page 2 } else { Show-Page 1 } }
        1 {
            if (-not $txtInstall.Text.Trim()) { [System.Windows.Forms.MessageBox]::Show("Please choose an install folder.", "CrystalPilot Setup") | Out-Null; return }
            if ($rbDedicated.Checked -and -not $txtRuntime.Text.Trim()) { [System.Windows.Forms.MessageBox]::Show("Please choose where the Linux runtime should be stored.", "CrystalPilot Setup") | Out-Null; return }
            if (-not ($txtProjects.Text.Trim() -match '^/')) { [System.Windows.Forms.MessageBox]::Show("The projects folder must be a Linux path starting with / (for example /root/crystalpilot_projects).", "CrystalPilot Setup") | Out-Null; return }
            if (-not (Test-Choices)) { return }
            Show-Page 2
        }
        2 {
            # an update in place keeps the XDS it has (wsl-install.sh replaces it only when given a package)
            if (-not ($txtXds.Text -and (Test-Path $txtXds.Text)) -and -not ($IsUpdate -and $state.runtimeMode -eq "existing")) {
                $a = [System.Windows.Forms.MessageBox]::Show("No XDS package selected. CrystalPilot will install without XDS; you can add it later on the Environment screen.`n`nContinue anyway?", "CrystalPilot Setup", "YesNo", "Warning")
                if ($a -ne "Yes") { return }
            }
            Start-Installation
        }
        4 { $form.Close() }
    }
})

# Preview mode: render each page to PNG and exit (used to review the layout)
if ($Preview) {
    New-Item -ItemType Directory -Force -Path $Preview | Out-Null
    $form.Opacity = 0; $form.ShowInTaskbar = $false
    $form.Show(); [System.Windows.Forms.Application]::DoEvents()
    $i = 0
    foreach ($n in $order) {
        Show-Page $i; [System.Windows.Forms.Application]::DoEvents()
        if ($n -eq "install") {
            $titles["install"] = @("Installing", "This takes 15 to 30 minutes (a 340 MB download, then the Linux runtime is set up) - the bar and the clock keep moving while it works")
            $header.Text = $titles["install"][0]; $sub.Text = $titles["install"][1]
            $logBox.Text = "Checking the Windows Subsystem for Linux ...`r`n    state: ok`r`nWSL is available.`r`nDownloading the Ubuntu 24.04 runtime image (about 340 MB) to D:\CrystalPilot\runtime - a few minutes on a normal connection ..."
            $lblStep.Text = "Downloading the Ubuntu runtime image: 212 of 340 MB (6.1 MB/s, about 1 min left)"; $progBar.Width = [int]($PW * 0.62); $lblClock.Text = "working  1:04"
        }
        if ($n -eq "finish") { Show-Finish @{ ok = $true; warnings = @(); message = "done" } }
        $bmp = New-Object System.Drawing.Bitmap($form.Width, $form.Height)
        $form.DrawToBitmap($bmp, (New-Object System.Drawing.Rectangle(0, 0, $form.Width, $form.Height)))
        $bmp.Save((Join-Path $Preview ("wizard_{0}_{1}.png" -f ($i + 1), $n)), [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
        $i++
    }
    # the page a failed installation ends on
    Show-Finish @{ ok = $false; warnings = @(); message = (Explain-WslError "HCS_E_HYPERV_NOT_INSTALLED" "D:\CrystalPilot\runtime") }
    [System.Windows.Forms.Application]::DoEvents()
    $bmp = New-Object System.Drawing.Bitmap($form.Width, $form.Height)
    $form.DrawToBitmap($bmp, (New-Object System.Drawing.Rectangle(0, 0, $form.Width, $form.Height)))
    $bmp.Save((Join-Path $Preview "wizard_6_finish_failed.png"), [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
    $form.Close(); exit 0
}

# Setup.exe starts PowerShell with a hidden console; Windows hands that start-up
# mode to this form as well.  From the old IExpress setup it arrived as
# "minimized" (only a taskbar button); from the Inno Setup one, which hides the
# console itself (runhidden), it arrives as "hidden" and the form would open
# invisible.  Minimizing and restoring makes Windows show it - measured: without
# this the form stays invisible, and a throwaway first window does not help.
$form.Add_Shown({
    if ($splash) { try { $splash.Close(); $splash.Dispose() } catch {}; $script:splash = $null }
    try {
        Set-Content -Path (Join-Path $SetupDataDir "setup-start.txt") -Encoding UTF8 -Value ("{0}  wizard {1}: setup window shown after {2:0.0} s (looking at this computer {3} s, of which the check itself {4} s); update: {5}" -f
            (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $WizardVersion, $ScriptClock.Elapsed.TotalSeconds, $script:ProbeSeconds, $state.probeSeconds, $IsUpdate)
    } catch {}
    if ($StartedHidden) { $form.WindowState = "Minimized"; $form.WindowState = "Normal" }
    elseif ($form.WindowState -ne "Normal") { $form.WindowState = "Normal" }
    $form.TopMost = $true; $form.Activate(); $form.TopMost = $false
})
if ($Resume -and $state.stage -eq "start") {
    Show-Page 3
    $form.Add_Shown({ Start-Installation })
} else {
    Show-Page 0
}
# ShowDialog() makes the active window its owner - the splash - and closing the
# splash in Add_Shown then closed this form too, 0.2 s after it appeared (0.6.6e).
# An owner without a handle means no owner at all.
[void]$form.ShowDialog((New-Object System.Windows.Forms.NativeWindow))
exit 0
