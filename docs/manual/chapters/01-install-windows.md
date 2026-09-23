# Installing on Windows

**Goal:** a working CrystalPilot on a Windows 10 (2004 or later) or Windows 11 computer, started from a desktop shortcut, with XDS, the Eiger reader and CCP4 in place.

XDS exists only for Linux, so on Windows CrystalPilot runs inside the *Windows Subsystem for Linux* (WSL). The installer takes care of that; you never open a Linux terminal. The interface runs in your normal browser.

## What you need before you start

| Item | Where from | Why |
|---|---|---|
| `CrystalPilot-Setup-<version>.exe` (or the package folder with `windows\`, `files\`, `docs\`) | your download or the lab share | the program itself |
| `XDS-gfortran_Linux_x86_64.tar.gz` | [xds.mr.mpg.de](https://xds.mr.mpg.de), free for academic use | XDS cannot be redistributed; save the file to your Downloads folder |
| `dectris-neggia.so` | [github.com/dectris/neggia/releases](https://github.com/dectris/neggia/releases) | only for Eiger `.h5` data; Downloads folder as well |
| CCP4, optional | an installed *CCP4 for Windows*, or the Linux `ccp4-*-linux64.tar.gz` in Downloads | POINTLESS, AIMLESS, CTRUNCATE, f2mtz/cad |
| About 2.5 GB of free disk (12 GB more with the Linux CCP4) | | the Linux runtime and the Python packages |

> Administrator approval is asked once if WSL has to be enabled, and Windows may need one restart. After the restart, open **Continue CrystalPilot Setup** from the Start menu; the installer picks up where it stopped, with your choices kept.

## Step by step

1. Double-click **CrystalPilot-Setup-\<version\>.exe**. Windows shows its *unknown publisher* notice the first time (More info → Run anyway): the installer is not signed. The package unpacks itself; a small **CrystalPilot Setup** window then says that the computer is being checked (WSL, the disks, an installed CrystalPilot), and the wizard opens by itself — a few seconds, up to a minute on a busy computer. (From the package folder, double-click `windows\CrystalPilot-Setup.bat` instead.)
2. **Welcome** page: read what will be done, look at the settings the installer has chosen — program folder, a dedicated Linux runtime on the disk with the most free space, the projects folder shown as `P:\Projects\`, the port, what happens with CCP4 — and click **Continue**. Only if you want something else, click **Customize…**: that opens the *Options* page, which is otherwise skipped. When CrystalPilot is already installed, the page is called **Update CrystalPilot** instead (see *Updating* below).

![The Welcome page: the notice, the settings the express install will use, and the Customize button.](images/wizard/wizard_1_welcome.png)

3. **Options** page (only after Customize):
   - *Install folder* (Windows side): where the launcher, scripts and this manual go.
   - *Linux runtime*: **Create a dedicated CrystalPilot runtime** on the disk of your choice (a 340 MB download, or the copy inside the offline installer), or **Use an existing Linux distribution** if you would rather install into your own Ubuntu.
   - *Projects folder inside the Linux runtime*: where every input frame you copy in and every result will live. The page shows how it will look from Windows.
   - *Port* of the web interface (8000 unless something else uses it).
   - *Explorer access*: leave **Also show the projects folder as drive** ticked and keep **P:** so that projects appear as `P:\Projects\...` in Explorer.

![The Options page: install folder, runtime choice, projects folder with its Windows path, port and the drive letter.](images/wizard/wizard_2_choices.png)

4. **Components** page: a checklist. Each line turns green by itself when the file is found — in the package folder or in your Downloads. For a missing one, click **Get it**, save the file from the page that opens to Downloads, and watch the line turn green; **Choose file** if you keep it elsewhere. CCP4 is chosen for you: *CCP4 for Windows* when one is installed, the *Linux package* when its tarball is in Downloads, otherwise *Not now*. Click **Install**.

![The Components page: XDS, the Eiger reader and CCP4 as a checklist, each with what was found.](images/wizard/wizard_3_components.png)

5. **Install** page: wait. The heading says how long it takes (15 to 30 minutes on a new computer, about 5 for an update). The log shows every step (WSL check, runtime download and creation, Python packages, XDS unpacking, neggia, CCP4, shortcuts, drive letter); the progress bar keeps moving and a clock counts the time, so a slow step is never mistaken for a frozen window. During the download the line above the bar shows the megabytes, the speed and the time left.

![The Install page with the live log.](images/wizard/wizard_4_install.png)

6. **Finish** page: the summary shows the program folder, the runtime, the projects folder with its Windows path and drive letter, and the interface address. Click **Start CrystalPilot now** or close the installer with **Finish**; it is not needed while CrystalPilot runs.

![The Finish page with the summary and the start button.](images/wizard/wizard_5_finish.png)

## Updating an installed CrystalPilot

Run the new **CrystalPilot-Setup-\<version\>.exe**. The installer finds the installed copy by itself — through the CrystalPilot shortcuts, *Apps & features*, or the CrystalPilot inside a Linux distribution — and the first page becomes **Update CrystalPilot**: it names the installed version and the new one, and keeps the Linux distribution, program folder, port, projects folder and drive letter as they are. No new Linux runtime is created and nothing large is downloaded; the update takes about five minutes. **Customize…** is still there if you want to install somewhere else instead.

## Starting and stopping

- Double-click the **CrystalPilot** shortcut on the desktop or in the Start menu (or `windows\CrystalPilot.bat`). A console window appears; it is the server, keep it open. Your browser opens a loading screen and switches to the interface as soon as the server answers (a few seconds; longer the first time and when disconnected network drives have to time out).
- Close the console window, or press Ctrl+C in it, to stop. Programs still running (XDS, XSCALE, CCP4) are stopped with it. `CrystalPilot-Stop.bat` stops a server that was left running.
- The launcher always uses the newest `files\xds-gui-v*.py`, so updating means running the new installer (it keeps your projects and settings) or replacing that file and restarting.

## Where your files are

- **Projects**: the projects folder inside the Linux runtime. From Explorer: the **CrystalPilot Projects** desktop shortcut, the Quick Access entry, the drive letter `P:\Projects\`, or the **Open folder** buttons in the interface. The raw path is `\\wsl.localhost\<runtime>\...`.
- **Your Windows drives** are visible inside the program as `/mnt/c`, `/mnt/d`, …; connected network drives are mounted at start (`/mnt/z`). Frames can be read from there directly, but large Eiger data sets are much faster when copied into the projects folder first.

## Removing CrystalPilot

*Settings → Apps → Installed apps → CrystalPilot → Uninstall* (or `windows\CrystalPilot-Uninstall.bat`). The program, shortcuts, drive letter and the entry itself are removed. If the Linux runtime was created by the installer you are asked whether to remove it too — **it holds your projects**, so answer *No* to keep them; a Linux distribution you already had is never touched.

## If it goes wrong

| Symptom | What to do |
|---|---|
| "WSL is installed but could not run a command" | run `wsl --shutdown` in PowerShell and start the installer again; `wsl --update` if WSL itself is old |
| The wizard asks for a restart | restart; it resumes after login |
| XDS or neggia not found on the Components page | click **Get it**, save the file to your Downloads folder; the line turns green by itself |
| The loading screen never switches | look at the console window for the error; run the installer again to repair the runtime |
| Network drive missing inside the program | it was disconnected when CrystalPilot started: reconnect it in Explorer and restart CrystalPilot |
| No network at the computer | use `CrystalPilot-Setup-<version>-offline.exe`, which carries the Linux runtime image (about 370 MB) |

Running the installer again is always safe: it updates the program and keeps projects and settings.
