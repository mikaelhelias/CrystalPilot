# CrystalPilot on Windows

CrystalPilot's interface is plain Python and runs anywhere. XDS, however, only
exists for Linux. On Windows everything therefore runs inside **WSL2**
(Windows Subsystem for Linux, built into Windows 10 2004+ and Windows 11) and
the interface opens in your normal Windows browser. You never need to use a
Linux terminal.

## Install (once)

Double-click **`CrystalPilot-Setup-<version>.exe`** (Windows shows its *unknown
publisher* notice the first time - More info, Run anyway - because the
installer is not code-signed). It unpacks the package to
`%LOCALAPPDATA%\CrystalPilot\setup` and opens the wizard. From a package
folder, double-click `windows\CrystalPilot-Setup.bat` instead.

1. **Welcome.** What will be done (WSL and an Ubuntu runtime), the disk
   footprint, and the settings the installer has chosen: program folder
   `C:\CrystalPilot`, a dedicated `CrystalPilot` runtime on the disk with the
   most free space, the projects folder inside it shown as `P:\Projects\`,
   port 8000, CCP4 for Windows when one is found. **Continue** takes them;
   **Customize...** opens the Options page, which is otherwise skipped.
2. **Options** (only via Customize). The install folder, the Linux runtime
   (dedicated, on a disk of your choice, or an existing distribution), the
   **projects folder** inside the runtime, the port, and whether the projects
   folder should appear as a drive letter in Explorer (P: by default).
3. **Components.** A checklist for the XDS package, the neggia reader and
   CCP4. XDS and neggia must be downloaded from their authors (free for
   academic use): **Get it** opens the page, and a file saved to Downloads is
   picked up by itself - the line turns green. CCP4 is preselected (a CCP4 for
   Windows already installed, the Linux tarball in Downloads, or not now).
4. **Installation** with a live log. If WSL itself has to be enabled, Windows
   asks for administrator approval and may need one restart; afterwards, open
   **Continue CrystalPilot Setup** from the Start menu and it picks up where it
   stopped.
5. **Finish**: summary, a **CrystalPilot** shortcut on the desktop and in the
   Start menu, an entry in *Apps & features*.

Then double-click the shortcut (or `CrystalPilot.bat`). A loading screen opens
in your browser and switches to the interface when the server is ready. Close
the CrystalPilot window (or press Ctrl+C) to stop it. `CrystalPilot-Stop.bat`
stops a server that was left running.

Running the installer again is safe: it updates the application and keeps your
projects and settings (a copy installed next to a `crystalpilot.cfg` starts
from those settings). For scripted installs use
`powershell -ExecutionPolicy Bypass -File wizard.ps1 -Unattended -Config choices.json`
(the JSON holds the same choices as the wizard pages: installDir, runtimeMode,
newDistro, runtimeDir, projects, port, xdsTar, neggia, ccp4Mode, ccp4Win,
mapDrive, driveLetter, launch, acknowledged).

**Offline computers.** `CrystalPilot-Setup-<version>-offline.exe` carries the
Ubuntu runtime image (about 340 MB more), so nothing is downloaded during the
install except what you fetch yourself (XDS, neggia). A runtime image already
in your Downloads folder is used the same way.

**Removing CrystalPilot.** *Settings > Apps > Installed apps > CrystalPilot >
Uninstall*, or `windows\CrystalPilot-Uninstall.bat`. It removes the program,
the shortcuts, the drive letter and the entry. When the Linux runtime was
created by the installer you are asked whether to remove it as well - it holds
your projects, so say No to keep them; a distribution you already had is never
touched.

**Building the installer** (developers): `py -3 windows\make_installer.py`
writes `dist\CrystalPilot-<version>.zip` (the portable package) and
`dist\CrystalPilot-Setup-<version>.exe` (a self-extracting archive made with
IExpress, which is part of Windows); `--offline` adds the installer with the
runtime image inside. The version comes from `files\src\config.py`, the
application from the newest `files\xds-gui-v*.py`, the manual from
`docs\manual`.

**Projects folder.** Everything belonging to a project, input frames and all
results, lives in the projects folder inside the Linux runtime. Copy your data
into a project folder before processing. Reaching it from Explorer:

* a **CrystalPilot Projects** shortcut on the desktop opens it directly,
* it is pinned to **Quick Access** in Explorer's left pane,
* optionally it is shown under a **drive letter** (P: by default, chosen in the
  wizard), so a project looks like `P:\Projects\my_project\`. Windows can only
  map a letter to the whole Linux runtime, so `P:\` is the runtime and
  `P:\Projects` is your projects folder (the same folder, made visible there
  by the installer). The drive reconnects by itself; if Explorer shows it as
  disconnected, just open it,
* inside CrystalPilot, **Open folder** next to the project name and next to the
  run folder opens the right folder in Explorer.

The raw path, if you ever need it, is `\\wsl.localhost\<runtime>\<projects folder>`.

**Manual.** Inside CrystalPilot, the **📖 Manual** button in the header opens it and the search box at the top of the **Docs** tab searches it together with the Docs sections. The illustrated, step-by-step manual is `docs\manual\CrystalPilot-Manual.pdf`
(also opened from the program: **Docs** tab, first card). The **Docs** tab itself
is the reference for every control and file. This file only covers the
Windows-specific parts.

## Where your files are

| What | Linux path (inside the app) | Windows path (Explorer) |
|------|-----------------------------|-------------------------|
| Projects (results) | `~/crystalpilot_projects` (chosen in the wizard) | `P:\Projects\` when the drive letter is enabled, otherwise `\\wsl.localhost\Ubuntu\root\crystalpilot_projects` (shown when you start) |
| Your Windows drives | `/mnt/c`, `/mnt/d`, ... | `C:\`, `D:\`, ... |
| Settings the app remembers | `~/.crystalpilot/settings.json` | `P:\root\.crystalpilot\settings.json` |

The app's folder browser shows **C:, D:, ... buttons** when it runs in WSL.
**Network drives** (Z: and friends) are not mounted by WSL itself; the
launcher detects your mapped drives every time it starts and mounts the ones
that are currently connected, so they appear as buttons too (`/mnt/z`). A drive
that is disconnected in Explorer is skipped; reconnect it and restart
CrystalPilot. To have a share mounted permanently instead, add a line like
`Z: /mnt/z drvfs defaults,noatime 0 0` to `/etc/fstab` inside Ubuntu.
Frames can be read directly from a Windows drive. Reading large Eiger `.h5`
datasets across the `/mnt` bridge is noticeably slower than from the Linux
side, so for big datasets copy the data into the projects folder first (open
the Windows path above in Explorer and drag the folder in).

## CCP4 (POINTLESS, AIMLESS, CTRUNCATE, F2MTZ, CAD)

XDS, XSCALE and XDSCONV work without CCP4. For the CCP4 steps, setup looks for
CCP4 in this order and uses the first it finds:

1. **A Linux CCP4 tarball** (`ccp4-*-linux64.tar.gz`, downloaded from
   https://www.ccp4.ac.uk/download, Linux, "tar.gz" package) in the
   CrystalPilot folder or your Downloads. Setup unpacks it into the Linux home
   folder (about 10 GB, several minutes), runs its `BINARY.setup`, and uses it.
   This is the fastest and most robust option.
2. **A Linux CCP4 already installed inside WSL** (found in `~/ccp4-*`,
   `/opt/xtal`, `/opt`, `/usr/local`). For another location set
   `CCP4_SETUP=/path/to/ccp4-9/bin/ccp4.setup-sh` in `~/.crystalpilot/config.env`
   inside the runtime and restart.
3. **CCP4 for Windows**, if it is installed (for example `F:\CCP4-8\8.0`).
   Setup finds it on all local drives and installs a small bridge in WSL: the
   app calls `pointless`, `aimless`, ... exactly as on Linux, and the bridge
   runs the Windows `.exe` with translated paths and environment. Nothing to
   download. Files pass through the WSL network share, which is a bit slower
   than option 1 but works for all the CCP4 steps CrystalPilot uses.
   Use `-WindowsCcp4 D:\CCP4-9\9.0` to point at a specific installation, or
   `-NoWindowsCcp4` to disable this route.

The launcher window shows which route is active (`CCP4: Linux (...)`,
`CCP4: Windows via WSL (...)` or `CCP4: none`).

## Options

| Setting | How |
|---------|-----|
| Port | chosen in the wizard; later edit `PORT=` in `~/.crystalpilot/config.env` (inside the runtime) and `PORT=` in `windows\crystalpilot.cfg` |
| Projects folder | edit `PROJECTS_DIR=` in `~/.crystalpilot/config.env` and restart |
| WSL distribution | set the environment variable `CRYSTALPILOT_DISTRO=<name>` or pass `-Distro <name>` |
| Drive letter for the projects | run the wizard again and change the "Explorer access" choice (it keeps everything else) |
| Parallel XDS (xds_par / xscale_par) | toggle in the app header; remembered in `~/.crystalpilot/settings.json` |
| No browser auto-open | `launch.ps1 -NoBrowser` |
| CCP4 tarball / Windows CCP4 | Components page of the wizard (run it again to change) |

## Developers

The launcher always copies the newest `files\xds-gui-v*.py` into WSL before
starting, so the workflow is: edit `files\src`, run `build.py`, double-click
the shortcut.

Files in this folder:

| File | Purpose |
|------|---------|
| `CrystalPilot-Setup.bat` / `wizard.ps1` | the graphical installer: WSL check, runtime, projects folder, components, Explorer access (shortcuts, Quick Access, drive letter), live log; `-Unattended -Config file.json` for scripted installs |
| `crystalpilot.cfg` | written by the installer: runtime name, port, install folder, projects folder, drive letter |
| `splash.html` | loading screen shown in the browser until the server answers |
| `wsl-install.sh` | Linux side: apt packages, Python venv, XDS, neggia, CCP4 (tarball / existing / Windows bridge), config |
| `crystalpilot-wsl.sh` | installed as `/usr/local/bin/crystalpilot` (`start`, `stop`, `status`, `info`) |
| `ccp4win-run.sh` | installed as `~/.crystalpilot/ccp4win/ccp4win-run`; runs a Windows CCP4 program from WSL with path and environment translation |
| `CrystalPilot.bat` / `launch.ps1` | starts the server in WSL, waits for it, opens the browser |
| `CrystalPilot-Stop.bat` | stops a running server |

## Troubleshooting

* **"WSL is installed but could not run a command"**: run `wsl --shutdown` in
  PowerShell and try again; if WSL itself is outdated run `wsl --update`.
* **Port already in use**: another CrystalPilot window is probably open. The
  launcher simply opens the browser in that case. Otherwise change the port.
* **XDS not found**: put `XDS-gfortran_Linux_x86_64.tar.gz` (from
  https://xds.mr.mpg.de, free for academic use) in the CrystalPilot folder and
  run setup again.
* **Eiger `.h5` data cannot be read by XDS**: `dectris-neggia.so` is missing.
  Get it from https://github.com/dectris/neggia/releases, put it in the
  CrystalPilot folder and run setup again.
* **CCP4 for Windows found but "could not be started from WSL"**: Windows
  interop is disabled in WSL. Remove `enabled=false` under `[interop]` in
  `/etc/wsl.conf` (inside Ubuntu), run `wsl --shutdown`, and run setup again.
* **Slow file browsing on `/mnt/...`**: expected for large directories on the
  Windows side; use the projects folder for heavy data.

## License

CrystalPilot is free software under the GNU General Public License v3 (see `LICENSE`), without any warranty.
