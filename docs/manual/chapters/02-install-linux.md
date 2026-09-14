# Installing on Linux

**Goal:** CrystalPilot started with one command on a Linux workstation or a lab server, with XDS, neggia and CCP4 found automatically.

## What you need

- Python 3.7 or newer with the `venv` module (`sudo apt install python3 python3-venv` on Debian or Ubuntu).
- XDS unpacked somewhere: `xds_par`, `xscale_par`, `xdsconv` and the helpers `forkxds`, `mcolspot`, `mintegrate` (all in the package from [xds.mr.mpg.de](https://xds.mr.mpg.de)).
- For Eiger data: `dectris-neggia.so`, ideally in the same folder as `xds_par`.
- Optional: CCP4 (`ccp4.setup-sh` sourced, or its path given to the installer), XDSCC12.

## Step by step

1. Put `xds-gui-vNNN.py` and `install-linux.sh` in one folder, ideally next to the XDS binaries.
2. Run the installer:

```
bash install-linux.sh
```

   It creates a private Python environment under `~/crystalpilot/venv` with numpy, h5py, hdf5plugin, fabio, matplotlib and gemmi, looks for XDS, neggia and CCP4, installs a `crystalpilot` command (`~/.local/bin`) and a desktop entry, copies this manual, and starts CrystalPilot once in your browser.

3. Read the summary at the end. Anything marked `[!!]` is missing; the notes tell you how to add it. The **Environment** screen in the browser shows the same information and lets you type paths.

Useful options:

```
bash install-linux.sh --xds /opt/XDS-gfortran_Linux_x86_64        # XDS elsewhere
bash install-linux.sh --neggia /path/to/dectris-neggia.so
bash install-linux.sh --ccp4-setup /opt/xtal/ccp4-9/bin/ccp4.setup-sh
bash install-linux.sh --prefix /data/crystalpilot --projects /data/projects
bash install-linux.sh --port 8100 --no-launch
```

## Everyday commands

| Command | Effect |
|---|---|
| `crystalpilot` | start in the background and open the browser |
| `crystalpilot fg` | start in the terminal; Ctrl+C stops it |
| `crystalpilot stop` | stop the background server |
| `crystalpilot status` / `crystalpilot log` | is it running / follow the log |

The interface is at `http://127.0.0.1:8000`. It answers this computer only; to use it from other machines start the program with `--host 0.0.0.0` (see the Docs tab, *Security and access*).

## Where things go

| What | Default |
|---|---|
| Program | `~/crystalpilot/app/crystalpilot.py` |
| Projects | `~/crystalpilot/projects` (`--projects` to change) |
| Settings you make in the interface | `~/.crystalpilot/settings.json` |
| Server log | `~/crystalpilot/server.log` |
| This manual | `~/crystalpilot/docs/manual` |

## Updating and removing

Copy the new `xds-gui-vNNN.py` next to the installer and run it again (projects and settings are kept), or copy it to `~/crystalpilot/app/crystalpilot.py` and restart. To remove: `crystalpilot stop`, then delete `~/crystalpilot`, `~/.local/bin/crystalpilot` and `~/.local/share/applications/crystalpilot.desktop`. Projects stay where they are.
