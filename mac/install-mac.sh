#!/usr/bin/env bash
if grep -q $'\r' "$0"; then tr -d '\r' < "$0" > "/tmp/crystalpilot-install.$$.sh"; exec bash "/tmp/crystalpilot-install.$$.sh" "$@"; fi # CRLF guard - keep on one line
#
# CrystalPilot - macOS installer (Apple silicon and Intel).
#
#   bash install-mac.sh                          # install with defaults, then start CrystalPilot
#   bash install-mac.sh --xds /Applications/XDS  # tell it where the XDS binaries are
#   bash install-mac.sh --help
#
# Or double-click "Install CrystalPilot.command" in Finder.  It
#   - finds the CrystalPilot application file (crystalpilot-<version>.py or xds-gui-vNNN.py),
#     or builds it from ../files when run from a copy of the repository
#   - creates a private Python environment with numpy, h5py, hdf5plugin, fabio, matplotlib, gemmi
#   - finds XDS for macOS, the neggia HDF5 reader matching it (arm64 or x86_64) and CCP4,
#     and clears the download quarantine that stops macOS from running XDS
#   - installs CrystalPilot.app and "CrystalPilot Stop.app" in ~/Applications, and a command:
#                           crystalpilot            start (background) and open the browser
#                           crystalpilot fg         start in this terminal
#                           crystalpilot stop | status | log
#   - starts CrystalPilot once so the environment check shows what it found
#
# Nothing is downloaded except Python packages: XDS and neggia are free for
# academic use but must be obtained from their authors (https://xds.mr.mpg.de,
# https://github.com/dectris/neggia).  CCP4 is optional (https://www.ccp4.ac.uk).
#
set -u

PREFIX="$HOME/CrystalPilot"
PROJECTS=""
XDS_DIR=""
NEGGIA=""
CCP4_SETUP=""
APP=""
PORT=8000
LAUNCH=1
SYSTEM_PYTHON=0
APPS_DIR="$HOME/Applications"
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix)     PREFIX="$2"; shift 2 ;;
        --projects)   PROJECTS="$2"; shift 2 ;;
        --xds)        XDS_DIR="$2"; shift 2 ;;
        --neggia)     NEGGIA="$2"; shift 2 ;;
        --ccp4-setup) CCP4_SETUP="$2"; shift 2 ;;
        --app)        APP="$2"; shift 2 ;;
        --port)       PORT="$2"; shift 2 ;;
        --apps-dir)   APPS_DIR="$2"; shift 2 ;;
        --no-launch)  LAUNCH=0; shift ;;
        --system-python) SYSTEM_PYTHON=1; shift ;;
        -h|--help)
            sed -n '4,24p' "$0" | sed 's/^# \{0,1\}//'
            echo "Options:"
            echo "  --prefix DIR      install folder (default: $PREFIX)"
            echo "  --projects DIR    projects folder (default: <prefix>/projects)"
            echo "  --xds DIR         folder with xds_par / xscale_par / xdsconv"
            echo "  --neggia FILE     dectris-neggia library (Eiger HDF5 reader for XDS)"
            echo "  --ccp4-setup FILE ccp4.setup-sh of an installed CCP4"
            echo "  --app FILE        CrystalPilot application file (crystalpilot-<version>.py or xds-gui-vNNN.py)"
            echo "  --port N          web interface port (default 8000)"
            echo "  --apps-dir DIR    where CrystalPilot.app goes (default: $APPS_DIR)"
            echo "  --no-launch       do not start CrystalPilot at the end"
            echo "  --system-python   use the Python packages already installed instead of a private environment"
            exit 0 ;;
        *) echo "unknown option: $1  (try --help)" >&2; exit 2 ;;
    esac
done
[ -n "$PROJECTS" ] || PROJECTS="$PREFIX/projects"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This installer is for macOS. On Linux use linux/install-linux.sh." >&2
    exit 2
fi

HERE=$(cd "$(dirname "$0")" && pwd)
MACHINE=$(uname -m)
if [ -t 1 ]; then C1=$(printf '\033[1;36m'); CG=$(printf '\033[32m'); CY=$(printf '\033[33m'); CR=$(printf '\033[31m'); CB=$(printf '\033[1m'); C0=$(printf '\033[0m'); else C1=""; CG=""; CY=""; CR=""; CB=""; C0=""; fi
step() { printf '\n%s==> %s%s\n' "$C1" "$*" "$C0"; }
ok()   { printf '    %s[ok]%s %s\n' "$CG" "$C0" "$*"; }
warn() { printf '    %s[!!]%s %s\n' "$CY" "$C0" "$*"; }
fail() { printf '    %s[XX]%s %s\n' "$CR" "$C0" "$*"; }
NOTES=()
S_APP=missing; S_PY=missing; S_XDS=missing; S_NEGGIA=missing; S_CCP4=none

# Architectures of a Mach-O file: "arm64", "x86_64" or "arm64 x86_64" (universal)
archs() { file -b "$1" 2>/dev/null | grep -oE 'arm64|x86_64' | sort -u | tr '\n' ' ' | sed 's/ $//'; }
what() { local a; a=$(archs "$1"); echo "${a:-not a Mac library}"; }
# Files unpacked from a browser download carry a quarantine flag; macOS then
# refuses to run them ("cannot be opened because the developer cannot be verified").
unquarantine() {
    xattr -r -d com.apple.quarantine "$1" 2>/dev/null
    ! xattr -p com.apple.quarantine "$1" >/dev/null 2>&1
}
quarantined() { xattr -p com.apple.quarantine "$1" >/dev/null 2>&1; }
# Run "$@" for at most $1 seconds (macOS has no timeout command)
run_limited() {
    local ticks=$(( $1 * 5 )); shift
    "$@" & local pid=$!
    while [ $ticks -gt 0 ] && kill -0 "$pid" 2>/dev/null; do sleep 0.2; ticks=$((ticks - 1)); done
    kill -9 "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
}

printf '%s\n' "${CB}CrystalPilot installer for macOS${C0}"
printf 'macOS %s on %s\n' "$(sw_vers -productVersion 2>/dev/null)" "$MACHINE"
printf 'Install folder: %s\nProjects folder: %s\n' "$PREFIX" "$PROJECTS"

# ── 1. Python ────────────────────────────────────────────────────────────────
# First, because building the application file from the repository needs it.
step "Python environment"
PY=""
for c in "$(command -v python3 2>/dev/null)" /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/bin/python3; do
    [ -n "$c" ] && [ -x "$c" ] || continue
    # /usr/bin/python3 is only a stub until the Command Line Tools are installed
    if [ "$c" = /usr/bin/python3 ] && ! xcode-select -p >/dev/null 2>&1; then continue; fi
    if "$c" -c 'import sys; sys.exit(sys.version_info < (3, 7))' >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
    fail "Python 3.7 or newer not found."
    NOTES+=("Install Python: either the Apple Command Line Tools (run: xcode-select --install) or the installer from https://www.python.org/downloads/macos/ , then run this installer again.")
else
    ok "python3: $("$PY" --version 2>&1) at $PY"
    if [ "$SYSTEM_PYTHON" = 1 ]; then
        VENV_PY="$PY"
        warn "using the packages of this Python (--system-python); make sure numpy, h5py, hdf5plugin, fabio, matplotlib are installed"
    else
        VENV="$PREFIX/venv"
        if [ ! -x "$VENV/bin/python" ]; then
            mkdir -p "$PREFIX"
            if ! "$PY" -m venv "$VENV" >/dev/null 2>&1; then
                fail "could not create a virtual environment"
                NOTES+=("Python at $PY cannot create a virtual environment. Install Python from https://www.python.org/downloads/macos/ and run again, or use --system-python.")
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
        else
            unset VENV_PY
        fi
    fi
    if [ -n "${VENV_PY:-}" ] && "$VENV_PY" -c "import numpy, h5py, hdf5plugin, fabio, matplotlib" >/dev/null 2>&1; then
        S_PY=ok
    else
        S_PY=partial
        NOTES+=("Some Python packages are missing; the frame viewer and HDF5 headers need numpy, h5py, hdf5plugin, fabio, matplotlib. The app can also install them from its Environment screen.")
    fi
fi

# ── 2. Application file ──────────────────────────────────────────────────────
step "CrystalPilot application"
if [ -z "$APP" ]; then
    for d in "$HERE" "$HERE/../files" "$HERE/files" "$PWD" "$HOME/Downloads"; do
        cand=$(ls -1 "$d"/xds-gui-v*.py 2>/dev/null | sed 's/.*xds-gui-v\([0-9]*\)\.py/\1 &/' | sort -n | tail -1 | cut -d' ' -f2-)
        [ -n "$cand" ] || cand=$(ls -1 "$d"/crystalpilot-*.py 2>/dev/null | sort -V 2>/dev/null | tail -1)
        [ -n "$cand" ] || { [ -f "$d/crystalpilot.py" ] && cand="$d/crystalpilot.py"; }
        if [ -n "$cand" ]; then APP="$cand"; break; fi
    done
fi
mkdir -p "$PREFIX/app"
if [ -n "$APP" ] && [ -f "$APP" ]; then
    cp -f "$APP" "$PREFIX/app/crystalpilot.py" && S_APP=ok && ok "$(basename "$APP") -> $PREFIX/app/crystalpilot.py"
elif [ -f "$HERE/../files/build.py" ] && [ -n "$PY" ]; then
    # A copy of the repository: build the single-file application from files/src
    if "$PY" "$HERE/../files/build.py" --output "$PREFIX/app/crystalpilot.py" >/dev/null 2>&1; then
        APP="$PREFIX/app/crystalpilot.py"; S_APP=ok; ok "built from $(cd "$HERE/../files" && pwd)/src -> $APP"
    else
        fail "building the application from files/src failed (run: $PY files/build.py to see why)"
    fi
fi
if [ "$S_APP" = ok ]; then
    # Illustrated manual: docs/manual next to the installer, the app file, or one level up
    for md in "$HERE/docs/manual" "$HERE/../docs/manual" "$(dirname "$APP")/docs/manual" "$(dirname "$APP")/../docs/manual"; do
        if [ -f "$md/CrystalPilot-Manual.html" ]; then
            mkdir -p "$PREFIX/docs/manual" && cp -f "$md"/CrystalPilot-Manual.* "$PREFIX/docs/manual/" 2>/dev/null && ok "illustrated manual -> $PREFIX/docs/manual (Docs tab > Illustrated manual)"
            break
        fi
    done
else
    fail "application file not found (crystalpilot-<version>.py or xds-gui-vNNN.py next to this script, in ../files or in Downloads). Use --app FILE."
    NOTES+=("Download crystalpilot-<version>.py from the Releases page into Downloads (or next to this script), or pass --app /path/to/it, and run again.")
fi

# ── 3. XDS ───────────────────────────────────────────────────────────────────
step "XDS"
if [ -z "$XDS_DIR" ]; then
    for d in "$HERE" "$HERE/.." "$HERE/../.." "${XDS:-}" \
             "$(dirname "$(command -v xds_par 2>/dev/null || true)" 2>/dev/null)" "$(dirname "$(command -v xds 2>/dev/null || true)" 2>/dev/null)" \
             /Applications/XDS* /Applications/XDS*/* /Applications/xds* "$HOME"/Applications/XDS* \
             /usr/local/xds /usr/local/xds/* /opt/xds /opt/xds/* "$HOME"/xds "$HOME"/xds/* "$HOME"/XDS* "$HOME"/XDS*/* \
             "$HOME"/Downloads/XDS* "$HOME"/Downloads/XDS*/* /usr/local/bin /opt/homebrew/bin; do
        [ -n "$d" ] && [ -d "$d" ] || continue
        if [ -f "$d/xds_par" ] || [ -f "$d/xds" ]; then XDS_DIR=$(cd "$d" && pwd); break; fi
    done
fi
if [ -n "$XDS_DIR" ] && { [ -f "$XDS_DIR/xds_par" ] || [ -f "$XDS_DIR/xds" ]; }; then
    exe="$XDS_DIR/xds_par"; [ -f "$exe" ] || exe="$XDS_DIR/xds"
    XDS_ARCH=$(archs "$exe")
    if quarantined "$exe"; then
        if unquarantine "$XDS_DIR"; then
            ok "cleared the download quarantine on $XDS_DIR"
        else
            warn "$XDS_DIR is quarantined and not writable for you"
            NOTES+=("macOS blocks the downloaded XDS binaries. Run once:  sudo xattr -r -d com.apple.quarantine \"$XDS_DIR\"")
        fi
    fi
    for n in xds xds_par xscale xscale_par xdsconv forkxds mcolspot mcolspot_par mintegrate mintegrate_par; do
        [ -f "$XDS_DIR/$n" ] && [ ! -x "$XDS_DIR/$n" ] && chmod +x "$XDS_DIR/$n" 2>/dev/null
    done
    case " $XDS_ARCH " in
        *" $MACHINE "*) ;;
        *" x86_64 "*)
            if ! arch -x86_64 /usr/bin/true >/dev/null 2>&1; then
                NOTES+=("These XDS binaries are for Intel Macs and need Rosetta:  softwareupdate --install-rosetta --agree-to-license  (or get the Apple silicon XDS package, which is faster).")
            else
                warn "Intel XDS binaries - they run through Rosetta; the Apple silicon package from xds.mr.mpg.de is faster"
            fi ;;
        "  ")
            NOTES+=("$exe is not a macOS program. Download the macOS XDS package (Apple silicon or Intel) from https://xds.mr.mpg.de/html_doc/downloading.html .") ;;
    esac
    tdir=$(mktemp -d)
    ( cd "$tdir" && run_limited 30 "$exe" > "$tdir/out.txt" 2>&1 < /dev/null )
    out=$(head -c 400 "$tdir/out.txt" 2>/dev/null); rm -rf "$tdir"
    if printf '%s' "$out" | grep -qi "XDS.INP"; then
        S_XDS=ok; ok "$XDS_DIR ($(basename "$exe"), ${XDS_ARCH:-?}, runs)"
        [ -f "$XDS_DIR/xds_par" ] && [ -f "$XDS_DIR/xscale_par" ] || warn "only serial binaries found (no xds_par/xscale_par) - processing will use one core"
    else
        first=$(printf '%s\n' "$out" | grep -m1 -v '^[[:space:]]*$' | sed 's/^[[:space:]]*//')
        S_XDS=broken; fail "$exe is present but does not start${first:+: $first}"
        if printf '%s' "$out" | grep -qi 'licen[cs]e expired'; then
            NOTES+=("The licence of this XDS build has expired (each XDS release runs for about a year). Download the current macOS package from https://xds.mr.mpg.de/html_doc/downloading.html , unpack it over $XDS_DIR (or elsewhere and use --xds DIR), and run again.")
        else
            NOTES+=("XDS was found in $XDS_DIR but does not run on this Mac (${XDS_ARCH:-not a Mac program}; this Mac is $MACHINE). Get the matching macOS package from https://xds.mr.mpg.de .")
        fi
    fi
else
    fail "XDS not found"
    NOTES+=("Download the macOS XDS package (Apple silicon: XDS-Apple_M1, Intel: XDS-OSX_64; free for academic use) from https://xds.mr.mpg.de/html_doc/downloading.html, unpack it (for example into /Applications), and run:  bash $(basename "$0") --xds /path/to/the/XDS/folder   (or set it later on the app's Environment screen).")
fi

# ── 4. neggia (Eiger HDF5 reader) ────────────────────────────────────────────
step "Eiger HDF5 reader (dectris-neggia)"
# Mac builds come under several names (dectris-neggia.so, dectris-neggia-arm64.so,
# dectris-neggia_osx.so ...) and XDS can only load one built for its own
# processor: take the first that matches the XDS binaries.
WANT_ARCH=${XDS_ARCH:-$MACHINE}
neggia_ok() { local a; a=" $(archs "$1") "; for w in $WANT_ARCH; do case "$a" in *" $w "*) return 0 ;; esac; done; return 1; }
if [ -n "$NEGGIA" ]; then
    if [ ! -f "$NEGGIA" ]; then warn "--neggia file does not exist: $NEGGIA"; NEGGIA=""
    elif ! neggia_ok "$NEGGIA"; then warn "$NEGGIA is built for $(what "$NEGGIA"), XDS here is $WANT_ARCH - XDS will not be able to load it"; fi
fi
if [ -z "$NEGGIA" ]; then
    WRONG=""
    for d in "$XDS_DIR" "$HERE" "$HERE/.." "$HOME/Downloads" /usr/local/lib /opt/homebrew/lib "$HOME/lib"; do
        [ -n "$d" ] && [ -d "$d" ] || continue
        for c in "$d"/dectris-neggia.so "$d"/dectris-neggia.dylib "$d"/dectris-neggia*.so "$d"/dectris-neggia*.dylib; do
            [ -f "$c" ] || continue
            if neggia_ok "$c"; then NEGGIA="$c"; break 2; fi
            [ -n "$WRONG" ] || WRONG="$c"
        done
    done
fi
if [ -n "$NEGGIA" ] && [ -f "$NEGGIA" ]; then
    quarantined "$NEGGIA" && { unquarantine "$NEGGIA" || NOTES+=("Run once:  sudo xattr -d com.apple.quarantine \"$NEGGIA\""); }
    if [ -n "$XDS_DIR" ] && [ "$(cd "$(dirname "$NEGGIA")" && pwd)" != "$XDS_DIR" ] && [ -w "$XDS_DIR" ] && [ ! -e "$XDS_DIR/$(basename "$NEGGIA")" ]; then
        cp -f "$NEGGIA" "$XDS_DIR/" && NEGGIA="$XDS_DIR/$(basename "$NEGGIA")"
    fi
    S_NEGGIA=ok; ok "$NEGGIA ($(archs "$NEGGIA"))"
else
    if [ -n "${WRONG:-}" ]; then
        warn "only $WRONG found, built for $(what "$WRONG"); XDS here needs $WANT_ARCH"
    else
        warn "not found - only needed for Eiger .h5 data"
    fi
    NOTES+=("For Eiger HDF5 data, get the macOS dectris-neggia library for $WANT_ARCH from https://github.com/dectris/neggia/releases , put it next to xds_par and run again (or use --neggia FILE).")
fi

# ── 5. CCP4 (optional) ───────────────────────────────────────────────────────
step "CCP4 (optional)"
if [ -n "$CCP4_SETUP" ] && [ ! -f "$CCP4_SETUP" ]; then warn "--ccp4-setup file does not exist: $CCP4_SETUP"; CCP4_SETUP=""; fi
if [ -z "$CCP4_SETUP" ]; then
    # The CCP4 installer puts it in /Applications/ccp4-9 (or ccp4-8.0 ...); take the newest.
    for base in "${CCP4:-}" "${CCP4_MASTER:-}" /Applications "$HOME/Applications" /opt /opt/xtal /usr/local /usr/local/xtal \
                "$HOME" "$HOME/Downloads" "$HOME/software"; do
        [ -n "$base" ] || continue
        c=$(ls -1d "$base"/bin/ccp4.setup-sh "$base"/[Cc][Cc][Pp]4*/bin/ccp4.setup-sh "$base"/[Cc][Cc][Pp]4*/*/bin/ccp4.setup-sh 2>/dev/null | sort -V | tail -1)
        [ -n "$c" ] && [ -f "$c" ] && { CCP4_SETUP="$c"; break; }
    done
fi
if [ -n "$CCP4_SETUP" ]; then
    S_CCP4="ok ($CCP4_SETUP)"; ok "will source $CCP4_SETUP at start"
elif command -v f2mtz >/dev/null 2>&1 && command -v pointless >/dev/null 2>&1; then
    S_CCP4="ok (already in PATH: $(dirname "$(command -v f2mtz)"))"; ok "CCP4 programs already in PATH"
else
    warn "not found. XDS, XSCALE and XDSCONV work without it; CCP4 adds POINTLESS, AIMLESS, CTRUNCATE and MTZ export."
    NOTES+=("CCP4 is optional: https://www.ccp4.ac.uk/download (macOS package). After installing, run again, or with --ccp4-setup /Applications/ccp4-9/bin/ccp4.setup-sh .")
fi

# ── 6. Folders, config, launcher ─────────────────────────────────────────────
step "Launcher"
mkdir -p "$PREFIX/bin" "$PROJECTS" "$HOME/.crystalpilot"
{
    echo "# CrystalPilot configuration (written by install-mac.sh $(date +%Y-%m-%d))"
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
# CrystalPilot launcher (written by install-mac.sh)
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
        if curl -fs -m 2 "$URL/health" >/dev/null 2>&1; then open "$URL"; return 0; fi
        sleep 0.5
    done
    return 1
}
setup_env() {
    # Started from Finder, PATH is only /usr/bin:/bin:/usr/sbin:/sbin
    export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
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
    open_browser || { echo "CrystalPilot did not answer; see $LOG" >&2; exit 1; } ;;
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
PREFIX_QUOTED="$PREFIX_QUOTED" perl -0pi -e 's/"__PREFIX__"/$ENV{PREFIX_QUOTED}/' "$PREFIX/bin/crystalpilot" 2>/dev/null \
  || "${VENV_PY:-python3}" - "$PREFIX/bin/crystalpilot" "$PREFIX_QUOTED" <<'PYEOF'
from pathlib import Path
import sys
p = Path(sys.argv[1])
p.write_text(p.read_text().replace('"__PREFIX__"', sys.argv[2]))
PYEOF
chmod +x "$PREFIX/bin/crystalpilot"
ok "$PREFIX/bin/crystalpilot"
mkdir -p "$HOME/.local/bin" && ln -sf "$PREFIX/bin/crystalpilot" "$HOME/.local/bin/crystalpilot"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ok "'crystalpilot' is on your PATH" ;;
    *) warn "for the 'crystalpilot' command in Terminal, add ~/.local/bin to your PATH:  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zprofile" ;;
esac

# ── 7. CrystalPilot.app and CrystalPilot Stop.app ────────────────────────────
# Small application bundles that run the launcher, so CrystalPilot starts from
# Launchpad, Spotlight or the Dock.  LSUIElement: they only start or stop the
# server and quit, so no Dock icon bounces.
make_app() {  # make_app NAME ID COMMAND
    local app="$APPS_DIR/$1.app"
    rm -rf "$app"
    mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
    cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>$1</string>
    <key>CFBundleDisplayName</key><string>$1</string>
    <key>CFBundleIdentifier</key><string>$2</string>
    <key>CFBundleExecutable</key><string>launcher</string>
    <key>CFBundleIconFile</key><string>CrystalPilot</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>LSUIElement</key><true/>
</dict>
</plist>
PLIST
    printf '#!/bin/bash\n%s\n' "$3" > "$app/Contents/MacOS/launcher"
    chmod +x "$app/Contents/MacOS/launcher"
    [ -f "$PREFIX/CrystalPilot.icns" ] && cp -f "$PREFIX/CrystalPilot.icns" "$app/Contents/Resources/"
    touch "$app"
}
# Icon from the artwork embedded in the app
if [ "$S_APP" = ok ] && [ -n "${VENV_PY:-}" ]; then
    ICONSET="$PREFIX/CrystalPilot.iconset"
    rm -rf "$ICONSET"; mkdir -p "$ICONSET"
    "$VENV_PY" - "$PREFIX/app/crystalpilot.py" "$ICONSET" <<'PYEOF' 2>/dev/null || true
import re, base64, io, os, sys
src = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
m = re.search(r'_LOGO_B64 = "([A-Za-z0-9+/=]+)"', src)
if m:
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGBA")
    w, h = im.size; s = min(w, h)
    im = im.crop(((w - s)//2, (h - s)//2, (w - s)//2 + s, (h - s)//2 + s))
    for n in (16, 32, 128, 256, 512):
        im.resize((n, n), Image.LANCZOS).save(os.path.join(sys.argv[2], "icon_%dx%d.png" % (n, n)))
        im.resize((2 * n, 2 * n), Image.LANCZOS).save(os.path.join(sys.argv[2], "icon_%dx%d@2x.png" % (n, n)))
PYEOF
    ls "$ICONSET"/*.png >/dev/null 2>&1 && iconutil -c icns "$ICONSET" -o "$PREFIX/CrystalPilot.icns" 2>/dev/null
    rm -rf "$ICONSET"
fi
if mkdir -p "$APPS_DIR" 2>/dev/null; then
    CP_Q=$(printf '%q' "$PREFIX/bin/crystalpilot")
    make_app "CrystalPilot" "org.crystalpilot.launcher" \
        "$CP_Q start >/dev/null 2>&1 || osascript -e 'display alert \"CrystalPilot did not start\" message \"See the log: $PREFIX/server.log\"'"
    make_app "CrystalPilot Stop" "org.crystalpilot.stop" \
        "msg=\$($CP_Q stop 2>&1); osascript -e \"display notification \\\"\$msg\\\" with title \\\"CrystalPilot\\\"\""
    ok "$APPS_DIR/CrystalPilot.app and CrystalPilot Stop.app (Launchpad, Spotlight; drag to the Dock to keep)"
else
    warn "could not create $APPS_DIR - start CrystalPilot with $PREFIX/bin/crystalpilot"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
printf '\n%sSummary%s\n' "$CB" "$C0"
printf '  %-18s %s\n' "Application:" "$S_APP" "Python packages:" "$S_PY" "XDS:" "$S_XDS ${XDS_DIR:+($XDS_DIR)}" "Neggia:" "$S_NEGGIA" "CCP4:" "$S_CCP4"
printf '  %-18s %s\n' "Install folder:" "$PREFIX" "Projects folder:" "$PROJECTS" "Interface:" "http://localhost:$PORT"
printf '  %-18s %s\n' "Start:" "CrystalPilot in Launchpad / Spotlight, or 'crystalpilot' in Terminal"
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
