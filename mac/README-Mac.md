# CrystalPilot on macOS

CrystalPilot runs natively on macOS, on Apple silicon (M1 and later) and on
Intel Macs, with the macOS build of XDS.

## Before you start

Download from their authors (free for academic use):

- **XDS for macOS** from https://xds.mr.mpg.de/html_doc/downloading.html:
  the Apple silicon package (`XDS-Apple_M1`) on an M-series Mac, the Intel
  package (`XDS-OSX_64`) on an Intel Mac. Unpack it, for example into
  `/Applications`. Each XDS release runs for about a year; when it stops with
  *license expired*, download the current package again.
- **DECTRIS neggia** for Eiger `.h5` data, from
  https://github.com/dectris/neggia/releases: the macOS library for the same
  processor as your XDS (arm64 or x86_64). Put it next to `xds_par`. Any of
  the usual names works (`dectris-neggia.so`, `dectris-neggia-arm64.so`,
  `dectris-neggia_osx.so`, `.dylib`).
- **CCP4** (optional; POINTLESS, AIMLESS, MTZ export) from
  https://www.ccp4.ac.uk. Its installer puts it in `/Applications/ccp4-9`.

Python 3.7 or newer is needed. If `python3` is not installed yet, install the
Apple Command Line Tools (`xcode-select --install`) or Python from
https://www.python.org/downloads/macos/ .

## Install

Get the `mac` folder: the repository (**Code → Download ZIP** on GitHub, or
`git clone`) or the release archive, and unzip it. Then either:

- **In Finder:** double-click **Install CrystalPilot.command** in the `mac`
  folder. The first time, macOS may say it cannot verify the developer:
  right-click the file, choose **Open**, then **Open** again.
- **In Terminal:**

  ```bash
  bash mac/install-mac.sh
  ```

The installer:

- uses the application file `crystalpilot-<version>.py` (or
  `xds-gui-vNNN.py`) if it finds one next to it, in `files/` or in Downloads,
  and otherwise builds it from `files/src`;
- creates a private Python environment with numpy, h5py, hdf5plugin, fabio,
  matplotlib and gemmi;
- finds XDS (`/Applications/XDS*`, `~/XDS*`, `~/Downloads/XDS*`, `/usr/local/xds`,
  `/opt/xds` or your `PATH`), checks that it runs on this Mac, and clears the
  download quarantine that otherwise makes macOS refuse to run it;
- picks the neggia library built for the same processor as XDS (an arm64 XDS
  cannot load an x86_64 neggia, and the reverse);
- finds CCP4 (the newest `ccp4.setup-sh` under `/Applications`, `/opt`,
  `/usr/local` or your home folder);
- installs **CrystalPilot** and **CrystalPilot Stop** in `~/Applications`
  (so they appear in Launchpad and Spotlight; drag CrystalPilot to the Dock to
  keep it there) and a `crystalpilot` command;
- starts CrystalPilot once in your browser.

Read the summary at the end: anything marked `[!!]` or `[XX]` is missing, and
the notes say how to add it. The **Environment** screen in the browser shows
the same and lets you type paths.

## Using it

Open **CrystalPilot** from Launchpad, Spotlight or the Dock: the server starts
in the background and the interface opens in your browser. Opening it again
while it runs just opens the browser. **CrystalPilot Stop** stops the server.

In Terminal (after adding `~/.local/bin` to your `PATH`, as the installer
suggests):

| Command | Effect |
|---------|--------|
| `crystalpilot` | start in the background and open the browser |
| `crystalpilot fg` | start in the terminal, Ctrl+C stops it |
| `crystalpilot stop` | stop the background server |
| `crystalpilot status` / `crystalpilot log` | check it / follow the log |

**Open folder** in the app header shows a project's folder in Finder.

## Where things go

| What | Default |
|------|---------|
| Install folder | `~/CrystalPilot` (`--prefix DIR` to change) |
| Projects | `~/CrystalPilot/projects` (`--projects DIR`) |
| Python environment | `~/CrystalPilot/venv` |
| Apps | `~/Applications/CrystalPilot.app`, `~/Applications/CrystalPilot Stop.app` (`--apps-dir DIR`) |
| Command | `~/CrystalPilot/bin/crystalpilot`, linked as `~/.local/bin/crystalpilot` |
| Settings the app remembers | `~/.crystalpilot/settings.json` |
| Server log | `~/CrystalPilot/server.log` |

## Options

```bash
bash mac/install-mac.sh --xds /Applications/XDS-Apple_M1          # XDS elsewhere
bash mac/install-mac.sh --neggia ~/Downloads/dectris-neggia-arm64.so
bash mac/install-mac.sh --ccp4-setup /Applications/ccp4-9/bin/ccp4.setup-sh
bash mac/install-mac.sh --app ~/Downloads/crystalpilot-0.6.9.py
bash mac/install-mac.sh --port 8100 --no-launch
bash mac/install-mac.sh --system-python                           # no private environment
```

Running the installer again is safe: it updates the application file and the
apps and keeps your projects and settings.

## Differences from Linux

- **RAM limit.** The CPU-core limit works as on Linux (it is written into
  XDS.INP and XSCALE.INP), but macOS has no way to cap the memory of a
  program, so the RAM field of the XDS Config panel is disabled.
- **Network and access** are the same as on Linux: CrystalPilot answers this
  Mac only (`127.0.0.1`), see [../linux/README-Linux.md](../linux/README-Linux.md).

## Updating

Download the new `crystalpilot-<version>.py` into Downloads (or pull the
repository) and run the installer again, then quit and reopen CrystalPilot
(**CrystalPilot Stop**, then **CrystalPilot**).

## Uninstall

```bash
~/CrystalPilot/bin/crystalpilot stop
rm -rf ~/CrystalPilot/app ~/CrystalPilot/venv ~/CrystalPilot/bin ~/CrystalPilot/docs \
       ~/Applications/CrystalPilot.app "$HOME/Applications/CrystalPilot Stop.app" ~/.local/bin/crystalpilot
```

Projects stay in `~/CrystalPilot/projects`; delete `~/CrystalPilot` as well
once you have moved them elsewhere. `~/.crystalpilot` holds the settings.

## License

CrystalPilot is free software under the GNU General Public License v3 (see `LICENSE`), without any warranty.
