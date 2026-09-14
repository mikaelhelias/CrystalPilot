#!/usr/bin/env bash
if grep -q $'\r' "$0"; then tr -d '\r' < "$0" > "/tmp/crystalpilot-install.$$.sh"; exec bash "/tmp/crystalpilot-install.$$.sh" "$@"; fi # CRLF guard - keep on one line
#
# CrystalPilot - Linux (and macOS) installer.
#
#   bash install-linux.sh                 # install with defaults, then start CrystalPilot
#   bash install-linux.sh --xds /opt/xds  # tell it where the XDS binaries are
#   bash install-linux.sh --help
#
# Drop this script next to the XDS binaries (or anywhere) and run it.  It
#   - finds the CrystalPilot application file (xds-gui-vNNN.py) next to it or in ../files
#   - creates a private Python environment with numpy, h5py, hdf5plugin, fabio, matplotlib, gemmi
#   - finds XDS, the neggia HDF5 reader and CCP4 (or tells you what is missing and where to get it)
#   - installs a launcher:  crystalpilot            start (background) and open the browser
#                           crystalpilot fg         start in this terminal
#                           crystalpilot stop | status | log
#   - adds a desktop entry, and starts CrystalPilot once so the environment check shows what it found
#
# Nothing is downloaded except Python packages: XDS and neggia are free for
# academic use but must be obtained from their authors (https://xds.mr.mpg.de,
# https://github.com/dectris/neggia).  CCP4 is optional (https://www.ccp4.ac.uk).
#
set -u

PREFIX="$HOME/crystalpilot"
PROJECTS=""
XDS_DIR=""
NEGGIA=""
CCP4_SETUP=""
APP=""
PORT=8000
LAUNCH=1
SYSTEM_PYTHON=0
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix)     PREFIX="$2"; shift 2 ;;
        --projects)   PROJECTS="$2"; shift 2 ;;
        --xds)        XDS_DIR="$2"; shift 2 ;;
        --neggia)     NEGGIA="$2"; shift 2 ;;
        --ccp4-setup) CCP4_SETUP="$2"; shift 2 ;;
        --app)        APP="$2"; shift 2 ;;
        --port)       PORT="$2"; shift 2 ;;
        --no-launch)  LAUNCH=0; shift ;;
        --system-python) SYSTEM_PYTHON=1; shift ;;
        -h|--help)
            sed -n '4,22p' "$0" | sed 's/^# \{0,1\}//'
            echo "Options:"
            echo "  --prefix DIR      install folder (default: $PREFIX)"
            echo "  --projects DIR    projects folder (default: <prefix>/projects)"
            echo "  --xds DIR         folder with xds_par / xscale_par / xdsconv"
            echo "  --neggia FILE     dectris-neggia.so (Eiger HDF5 reader for XDS)"
            echo "  --ccp4-setup FILE ccp4.setup-sh of an installed CCP4"
            echo "  --app FILE        CrystalPilot application file (xds-gui-vNNN.py)"
            echo "  --port N          web interface port (default 8000)"
            echo "  --no-launch       do not start CrystalPilot at the end"
            echo "  --system-python   use the system Python packages instead of a private environment"
            exit 0 ;;
        *) echo "unknown option: $1  (try --help)" >&2; exit 2 ;;
    esac
done
[ -n "$PROJECTS" ] || PROJECTS="$PREFIX/projects"

HERE=$(cd "$(dirname "$0")" && pwd)
OS=$(uname -s)
if [ -t 1 ]; then C1=$(printf '\033[1;36m'); CG=$(printf '\033[32m'); CY=$(printf '\033[33m'); CR=$(printf '\033[31m'); CB=$(printf '\033[1m'); C0=$(printf '\033[0m'); else C1=""; CG=""; CY=""; CR=""; CB=""; C0=""; fi
step() { printf '\n%s==> %s%s\n' "$C1" "$*" "$C0"; }
ok()   { printf '    %s[ok]%s %s\n' "$CG" "$C0" "$*"; }
warn() { printf '    %s[!!]%s %s\n' "$CY" "$C0" "$*"; }
fail() { printf '    %s[XX]%s %s\n' "$CR" "$C0" "$*"; }
NOTES=()
S_APP=missing; S_PY=missing; S_XDS=missing; S_NEGGIA=missing; S_CCP4=none

printf '%s\n' "${CB}CrystalPilot installer for Linux${C0}"
printf 'Install folder: %s\nProjects folder: %s\n' "$PREFIX" "$PROJECTS"

# ── 1. Application file ──────────────────────────────────────────────────────
step "CrystalPilot application"
if [ -z "$APP" ]; then
    for d in "$HERE" "$HERE/../files" "$HERE/files" "$PWD"; do
        cand=$(ls -1 "$d"/xds-gui-v*.py 2>/dev/null | sed 's/.*xds-gui-v\([0-9]*\)\.py/\1 &/' | sort -n | tail -1 | cut -d' ' -f2-)
        if [ -n "$cand" ]; then APP="$cand"; break; fi
        if [ -f "$d/crystalpilot.py" ]; then APP="$d/crystalpilot.py"; break; fi
    done
fi
if [ -n "$APP" ] && [ -f "$APP" ]; then
    mkdir -p "$PREFIX/app" && cp -f "$APP" "$PREFIX/app/crystalpilot.py" && S_APP=ok && ok "$(basename "$APP") -> $PREFIX/app/crystalpilot.py"
    # Illustrated manual: docs/manual next to the installer, the app file, or one level up
    for md in "$HERE/docs/manual" "$HERE/../docs/manual" "$(dirname "$APP")/docs/manual" "$(dirname "$APP")/../docs/manual"; do
        if [ -f "$md/CrystalPilot-Manual.html" ]; then
            mkdir -p "$PREFIX/docs/manual" && cp -f "$md"/CrystalPilot-Manual.* "$PREFIX/docs/manual/" 2>/dev/null && ok "illustrated manual -> $PREFIX/docs/manual (Docs tab > Illustrated manual)"
            break
        fi
    done
else
    fail "application file not found (xds-gui-vNNN.py next to this script or in ../files). Use --app FILE."
    NOTES+=("Copy the built xds-gui-vNNN.py next to this script, or pass --app /path/to/it, and run again.")
fi

# ── 2. Python ────────────────────────────────────────────────────────────────
step "Python environment"
PY=$(command -v python3 || true)
if [ -z "$PY" ]; then
    fail "python3 not found. Install it (Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip)."
    NOTES+=("Python 3.7 or newer is required.")
else
    ok "python3: $("$PY" --version 2>&1) at $PY"
    if [ "$SYSTEM_PYTHON" = 1 ]; then
        VENV_PY="$PY"
        warn "using system Python packages (--system-python); make sure numpy, h5py, hdf5plugin, fabio, matplotlib are installed"
    else
        VENV="$PREFIX/venv"
        if [ ! -x "$VENV/bin/python" ]; then
            if ! "$PY" -m venv "$VENV" >/dev/null 2>&1; then
                fail "could not create a virtual environment"
                NOTES+=("Install the venv module (Debian/Ubuntu: sudo apt install python3-venv) and run again, or use --system-python.")
            fi
        fi
        VENV_PY="$VENV/bin/python"
        if [ -x "$VENV_PY" ]; then
            "$VENV_PY" -m pip install -q --upgrade pip wheel >/dev/null 2>&1 || true
            printf '    installing numpy, h5py, hdf5plugin, fabio, matplotlib, gemmi ...\n'
            if "$VENV_PY" -m pip install -q numpy h5py hdf5plugin fabio matplotlib gemmi >/dev/null 2>&1; then
                ok "packages installed"
            elif "$VENV_PY" -m pip install -q numpy h5py hdf5plugin fabio matplotlib >/dev/null 2>&1; then
                ok "packages installed (gemmi skipped)"
                NOTES+=("gemmi could not be installed; MTZ conversion through gemmi is unavailable (XDSCONV/f2mtz still work).")
            else
                warn "pip install failed - is there network access? Try: $VENV_PY -m pip install numpy h5py hdf5plugin fabio matplotlib"
            fi
        fi
    fi
    if [ -n "${VENV_PY:-}" ] && "$VENV_PY" -c "import numpy, h5py, hdf5plugin, fabio, matplotlib" >/dev/null 2>&1; then
        S_PY=ok
    else
        S_PY=partial
        NOTES+=("Some Python packages are missing; the frame viewer and HDF5 headers need numpy, h5py, hdf5plugin, fabio, matplotlib. The app can also install them from its Environment screen.")
    fi
fi

# ── 3. XDS ───────────────────────────────────────────────────────────────────
step "XDS"
if [ -z "$XDS_DIR" ]; then
    for d in "$HERE" "${XDS:-}" "$(dirname "$(command -v xds_par 2>/dev/null || true)" 2>/dev/null)" "$(dirname "$(command -v xds 2>/dev/null || true)" 2>/dev/null)" \
             /opt/xds /opt/xds/* /usr/local/xds /usr/local/xds/* "$HOME"/xds "$HOME"/xds/* "$HOME"/XDS* /usr/local/bin; do
        [ -n "$d" ] && [ -d "$d" ] || continue
        if [ -x "$d/xds_par" ] || [ -x "$d/xds" ]; then XDS_DIR=$(cd "$d" && pwd); break; fi
    done
fi
if [ -n "$XDS_DIR" ] && { [ -x "$XDS_DIR/xds_par" ] || [ -x "$XDS_DIR/xds" ]; }; then
    tdir=$(mktemp -d); exe="$XDS_DIR/xds_par"; [ -x "$exe" ] || exe="$XDS_DIR/xds"
    out=$( cd "$tdir" && timeout 30 "$exe" 2>&1 | head -c 400 ); rm -rf "$tdir"
    if printf '%s' "$out" | grep -qi "XDS.INP"; then
        S_XDS=ok; ok "$XDS_DIR ($(basename "$exe") runs)"
        [ -x "$XDS_DIR/xds_par" ] && [ -x "$XDS_DIR/xscale_par" ] || warn "only serial binaries found (no xds_par/xscale_par) - processing will use one core"
    else
        S_XDS=broken; fail "$exe is present but does not start: $(printf '%s' "$out" | head -1)"
        NOTES+=("XDS binaries were found in $XDS_DIR but do not run on this machine (wrong architecture or missing libraries).")
    fi
else
    fail "XDS not found"
    NOTES+=("Download the Linux XDS package (free for academic use) from https://xds.mr.mpg.de/html_doc/downloading.html, unpack it, and run:  bash $(basename "$0") --xds /path/to/XDS-gfortran_Linux_x86_64   (or set it later on the app's Environment screen).")
fi

# ── 4. neggia (Eiger HDF5 reader) ────────────────────────────────────────────
step "Eiger HDF5 reader (dectris-neggia)"
if [ -z "$NEGGIA" ]; then
    for c in "$XDS_DIR/dectris-neggia.so" "$HERE/dectris-neggia.so" "$XDS_DIR/dectris-neggia.dylib" /usr/local/lib/dectris-neggia.so "$HOME"/lib/dectris-neggia.so; do
        [ -n "$c" ] && [ -f "$c" ] && { NEGGIA="$c"; break; }
    done
fi
if [ -n "$NEGGIA" ] && [ -f "$NEGGIA" ]; then
    if [ -n "$XDS_DIR" ] && [ -d "$XDS_DIR" ] && [ ! -f "$XDS_DIR/$(basename "$NEGGIA")" ] && [ -w "$XDS_DIR" ]; then
        cp -f "$NEGGIA" "$XDS_DIR/" && NEGGIA="$XDS_DIR/$(basename "$NEGGIA")"
    fi
    S_NEGGIA=ok; ok "$NEGGIA"
else
    warn "not found - only needed for Eiger .h5 data"
    NOTES+=("For Eiger HDF5 data, get dectris-neggia.so from https://github.com/dectris/neggia/releases and put it next to xds_par (or run again with --neggia FILE).")
fi

# ── 5. CCP4 (optional) ───────────────────────────────────────────────────────
step "CCP4 (optional)"
if [ -n "$CCP4_SETUP" ] && [ ! -f "$CCP4_SETUP" ]; then warn "--ccp4-setup file does not exist: $CCP4_SETUP"; CCP4_SETUP=""; fi
if [ -z "$CCP4_SETUP" ]; then
    for c in "${CCP4:-}"/bin/ccp4.setup-sh /opt/xtal/ccp4-*/bin/ccp4.setup-sh /opt/ccp4-*/bin/ccp4.setup-sh /usr/local/ccp4-*/bin/ccp4.setup-sh "$HOME"/ccp4-*/bin/ccp4.setup-sh /Applications/ccp4-*/bin/ccp4.setup-sh; do
        [ -f "$c" ] && { CCP4_SETUP="$c"; break; }
    done
fi
if [ -n "$CCP4_SETUP" ]; then
    S_CCP4="ok ($CCP4_SETUP)"; ok "will source $CCP4_SETUP at start"
elif command -v f2mtz >/dev/null 2>&1 && command -v pointless >/dev/null 2>&1; then
    S_CCP4="ok (already in PATH: $(dirname "$(command -v f2mtz)"))"; ok "CCP4 programs already in PATH"
else
    warn "not found. XDS, XSCALE and XDSCONV work without it; CCP4 adds POINTLESS, AIMLESS, CTRUNCATE and MTZ export."
    NOTES+=("CCP4 is optional: https://www.ccp4.ac.uk/download . After installing, run again with --ccp4-setup /path/to/ccp4-9/bin/ccp4.setup-sh (or start CrystalPilot from a terminal where CCP4 is sourced).")
fi

# ── 6. Folders, config, launcher ─────────────────────────────────────────────
step "Launcher"
mkdir -p "$PREFIX/bin" "$PROJECTS" "$HOME/.crystalpilot"
{
    echo "# CrystalPilot configuration (written by install-linux.sh $(date +%Y-%m-%d))"
    printf '%s=%q\n' PORT "$PORT"
    printf '%s=%q\n' PROJECTS_DIR "$PROJECTS"
    printf '%s=%q\n' XDS_DIR "$XDS_DIR"
    printf '%s=%q\n' CCP4_SETUP "$CCP4_SETUP"
    printf '%s=%q\n' PYTHON "${VENV_PY:-python3}"
} > "$PREFIX/config.env"
# Tell the app about neggia / CCP4 through its own settings file (per user)
if [ -n "${VENV_PY:-}" ] && [ -x "$VENV_PY" ]; then
    "$VENV_PY" - "$NEGGIA" "$CCP4_SETUP" <<'PYEOF' 2>/dev/null || true
import json, os, sys
p = os.path.expanduser("~/.crystalpilot/settings.json")
try:
    s = json.load(open(p))
except Exception:
    s = {}
neg, setup = sys.argv[1], sys.argv[2]
if neg:
    s["neggia_lib"] = neg
if setup:
    b = os.path.join(os.path.dirname(setup), "")
    if os.path.exists(os.path.join(b, "f2mtz")):
        s["ccp4_bin"] = b.rstrip("/")
os.makedirs(os.path.dirname(p), exist_ok=True)
json.dump(s, open(p, "w"), indent=2)
PYEOF
fi

cat > "$PREFIX/bin/crystalpilot" <<'LAUNCHER'
#!/usr/bin/env bash
# CrystalPilot launcher (written by install-linux.sh)
#   crystalpilot            start in the background and open the browser
#   crystalpilot fg         start in this terminal (Ctrl+C stops it)
#   crystalpilot stop | status | log
PREFIX="__PREFIX__"
. "$PREFIX/config.env"
PORT="${PORT:-8000}"; APP="$PREFIX/app/crystalpilot.py"; LOG="$PREFIX/server.log"; PIDF="$PREFIX/server.pid"
URL="http://localhost:$PORT"
running() { [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null; }
open_browser() {
    for i in $(seq 1 120); do
        if curl -fs -m 2 "$URL/health" >/dev/null 2>&1 || wget -q -T 2 -O /dev/null "$URL/health" 2>/dev/null; then
            if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
            elif command -v open >/dev/null 2>&1; then open "$URL"; fi
            return 0
        fi
        sleep 0.5
    done
}
setup_env() {
    [ -n "${CCP4_SETUP:-}" ] && [ -f "$CCP4_SETUP" ] && . "$CCP4_SETUP" >/dev/null 2>&1
    [ -n "${XDS_DIR:-}" ] && export PATH="$XDS_DIR:$PATH"
    export XDS_GUI_PROJECTS="$PROJECTS_DIR"
    ARGS=(--port "$PORT" --host 127.0.0.1 --projects-dir "$PROJECTS_DIR")
    [ -n "${XDS_DIR:-}" ] && ARGS+=(--xds-path "$XDS_DIR")
}
case "${1:-start}" in
  start)
    if running; then echo "CrystalPilot is already running: $URL"; open_browser; exit 0; fi
    setup_env; cd "$PREFIX"
    nohup "$PYTHON" -u "$APP" "${ARGS[@]}" > "$LOG" 2>&1 &
    echo $! > "$PIDF"
    echo "CrystalPilot started (pid $(cat "$PIDF")) - $URL   [log: $LOG]"
    open_browser ;;
  fg)
    if running; then echo "CrystalPilot is already running: $URL"; exit 0; fi
    setup_env; cd "$PREFIX"
    ( open_browser ) &
    exec "$PYTHON" -u "$APP" "${ARGS[@]}" ;;
  stop)
    if running; then kill "$(cat "$PIDF")" && rm -f "$PIDF" && echo "CrystalPilot stopped"; else rm -f "$PIDF"; echo "CrystalPilot is not running"; fi ;;
  status)
    if running; then echo "running (pid $(cat "$PIDF")) - $URL"; else echo "not running"; exit 3; fi ;;
  log) tail -n 50 -f "$LOG" ;;
  *) echo "usage: crystalpilot [start|fg|stop|status|log]"; exit 2 ;;
esac
LAUNCHER
PREFIX_QUOTED=$(printf '%q' "$PREFIX")
"${VENV_PY:-python3}" - "$PREFIX/bin/crystalpilot" "$PREFIX_QUOTED" <<'PYEOF'
from pathlib import Path
import sys
p = Path(sys.argv[1])
p.write_text(p.read_text().replace('"__PREFIX__"', sys.argv[2]))
PYEOF
chmod +x "$PREFIX/bin/crystalpilot"
ok "$PREFIX/bin/crystalpilot"
mkdir -p "$HOME/.local/bin" && ln -sf "$PREFIX/bin/crystalpilot" "$HOME/.local/bin/crystalpilot"
case ":$PATH:" in *":$HOME/.local/bin:"*) ok "'crystalpilot' is on your PATH" ;; *) warn "$HOME/.local/bin is not on your PATH - use $PREFIX/bin/crystalpilot, or log out and in again" ;; esac

# Icon (from the artwork embedded in the app) and desktop entry
if [ "$OS" = "Linux" ] && [ "$S_APP" = ok ] && [ -n "${VENV_PY:-}" ]; then
    "$VENV_PY" - "$PREFIX/app/crystalpilot.py" "$PREFIX/icon.png" <<'PYEOF' 2>/dev/null || true
import re, base64, io, sys
src = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
m = re.search(r'_LOGO_B64 = "([A-Za-z0-9+/=]+)"', src)
if m:
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGB")
    w, h = im.size; s = min(w, h)
    im = im.crop(((w - s)//2, (h - s)//2, (w - s)//2 + s, (h - s)//2 + s)).resize((256, 256))
    im.save(sys.argv[2])
PYEOF
    mkdir -p "$HOME/.local/share/applications"
    cat > "$HOME/.local/share/applications/crystalpilot.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=CrystalPilot
Comment=XDS / XSCALE / CCP4 data processing interface
Exec="$PREFIX/bin/crystalpilot"
Icon=$PREFIX/icon.png
Terminal=false
Categories=Science;Education;
DESKTOP
    ok "desktop entry: ~/.local/share/applications/crystalpilot.desktop"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
printf '\n%sSummary%s\n' "$CB" "$C0"
printf '  %-18s %s\n' "Application:" "$S_APP" "Python packages:" "$S_PY" "XDS:" "$S_XDS ${XDS_DIR:+($XDS_DIR)}" "Neggia:" "$S_NEGGIA" "CCP4:" "$S_CCP4"
printf '  %-18s %s\n' "Install folder:" "$PREFIX" "Projects folder:" "$PROJECTS" "Interface:" "http://localhost:$PORT"
printf '  %-18s %s\n' "Start:" "crystalpilot   (or $PREFIX/bin/crystalpilot; 'crystalpilot fg' keeps it in the terminal)"
if [ ${#NOTES[@]} -gt 0 ]; then
    printf '\n%sNotes%s\n' "$CB" "$C0"
    for n in "${NOTES[@]}"; do printf '  * %s\n' "$n"; done
fi
echo
if [ "$S_APP" != ok ] || [ "${VENV_PY:-}" = "" ]; then exit 1; fi
if [ "$LAUNCH" = 1 ]; then
    step "Starting CrystalPilot"
    "$PREFIX/bin/crystalpilot" start
    echo "The Environment screen in the browser shows what was found; XDS and neggia paths can be set there."
fi
exit 0
