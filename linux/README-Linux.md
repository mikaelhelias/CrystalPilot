# CrystalPilot on Linux

## Install

1. Copy the built application file (`files/xds-gui-vNNN.py`) and
   `install-linux.sh` into the same folder, ideally next to your XDS binaries
   (`xds_par`, `xscale_par`, `xdsconv`).
2. Run:

```bash
bash install-linux.sh
```

The script creates a private Python environment, finds XDS, the neggia HDF5
reader and CCP4, installs a `crystalpilot` command and a desktop entry, and
starts CrystalPilot once. On the first launch the app opens its Environment
screen, which shows what was found (XDS, xds_par for multi-core runs, neggia,
CCP4, Python packages) with download links and path fields for anything
missing. The same screen is available later from the About panel. Paths you
set there, the parallel on/off choice and the image path of each project are
remembered.

Everything a project needs, input frames and all results, lives in its folder
under the projects folder. **Open folder** in the app header opens it in your
file manager.

Requirements: Python 3.7 or newer with the `venv` module (Debian/Ubuntu:
`sudo apt install python3 python3-venv`) and network access for the Python
packages. Nothing else is downloaded: XDS and neggia must be obtained from
their authors, CCP4 is optional.

**Manual.** Inside CrystalPilot, the **📖 Manual** button in the header opens it and the search box at the top of the **Docs** tab searches it together with the Docs sections. The illustrated, step-by-step manual is `docs/manual/CrystalPilot-Manual.pdf`
(also opened from the program: **Docs** tab, first card; the installer copies it
to `~/crystalpilot/docs/manual`). The **Docs** tab itself is the reference for
every control and file. This file only covers installation on Linux.

## Where things go

| What | Default |
|------|---------|
| Install folder | `~/crystalpilot` (`--prefix DIR` to change) |
| Projects | `~/crystalpilot/projects` (`--projects DIR`) |
| Python environment | `~/crystalpilot/venv` |
| Launcher | `~/crystalpilot/bin/crystalpilot`, linked as `~/.local/bin/crystalpilot` |
| Settings the app remembers | `~/.crystalpilot/settings.json` |
| Server log | `~/crystalpilot/server.log` |

## Using it

| Command | Effect |
|---------|--------|
| `crystalpilot` | start in the background and open the browser |
| `crystalpilot fg` | start in the terminal, Ctrl+C stops it |
| `crystalpilot stop` | stop the background server |
| `crystalpilot status` / `crystalpilot log` | check it / follow the log |

## Network and access

CrystalPilot listens on this computer only (`127.0.0.1`). To use it from
another machine start it with `--host 0.0.0.0` (or `XDS_GUI_HOST=0.0.0.0`);
anyone who can reach the port can then open the interface, so do that on a
trusted network only.

The API answers the browser tab that opened the page and nothing else: the
page receives a per-launch token as a cookie, and other web sites open in the
same browser cannot obtain it. Scripts pass the token printed in the console
banner as the header `X-CrystalPilot-Token` or as `?token=`; set
`XDS_GUI_TOKEN` to make it fixed.

## Options

```bash
bash install-linux.sh --xds /opt/XDS-gfortran_Linux_x86_64   # XDS elsewhere
bash install-linux.sh --neggia /path/dectris-neggia.so       # Eiger HDF5 reader
bash install-linux.sh --ccp4-setup /opt/xtal/ccp4-9/bin/ccp4.setup-sh
bash install-linux.sh --port 8100 --no-launch
bash install-linux.sh --system-python                        # no private environment
```

Running the installer again is safe: it updates the application file and keeps
your projects and settings.

## Updating

Rebuild `xds-gui-vNNN.py`, copy it next to the installer, run the installer
again (or copy it to `~/crystalpilot/app/crystalpilot.py` by hand) and restart
CrystalPilot.

## Uninstall

```bash
crystalpilot stop
rm -rf ~/crystalpilot ~/.local/bin/crystalpilot ~/.local/share/applications/crystalpilot.desktop
```

Projects live in the projects folder; move them elsewhere first if you want to keep them.

## License

CrystalPilot is free software under the GNU General Public License v3 (see `LICENSE`), without any warranty.
