#!/usr/bin/env bash
if grep -q $'\r' "$0"; then tr -d '\r' < "$0" > "/tmp/crystalpilot-install.$$.sh"; exec bash "/tmp/crystalpilot-install.$$.sh" "$@"; fi # CRLF guard - keep on one line
#
# CrystalPilot - Linux side of the Windows installer.
# Runs inside WSL (Ubuntu/Debian).  Called by setup.ps1, but can also be run
# by hand:  bash wsl-install.sh --app crystalpilot.py --xds-tar XDS-*.tar.gz
#
# What it sets up (all under $HOME/.crystalpilot unless noted):
#   crystalpilot.py   the single-file application
#   venv/             Python with numpy, h5py, hdf5plugin, fabio, matplotlib, gemmi
#   xds/              XDS binaries (xds_par, xscale_par, xdsconv ...) + dectris-neggia.so
#   config.env        PORT, PROJECTS_DIR, CCP4_SETUP
#   /usr/local/bin/crystalpilot   start/stop/status wrapper used by the launcher
#
set -u

APP=""; XDS_TAR=""; NEGGIA=""; CCP4_SETUP=""; CCP4_TAR=""; CCP4_WIN=""; PORT=8000; WRAPPER_SRC=""; BRIDGE_SRC=""; PROJECTS_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --app)        APP="$2";         shift 2 ;;
        --xds-tar)    XDS_TAR="$2";     shift 2 ;;
        --neggia)     NEGGIA="$2";      shift 2 ;;
        --ccp4-setup) CCP4_SETUP="$2";  shift 2 ;;   # existing Linux CCP4: path of ccp4.setup-sh
        --ccp4-tar)   CCP4_TAR="$2";    shift 2 ;;   # Linux CCP4 tarball to install into $HOME
        --ccp4-win)   CCP4_WIN="$2";    shift 2 ;;   # Windows CCP4 root as seen from WSL (/mnt/c/CCP4-8/8.0)
        --bridge)     BRIDGE_SRC="$2";  shift 2 ;;   # ccp4win-run.sh (Windows CCP4 bridge script)
        --port)       PORT="$2";        shift 2 ;;
        --projects)   PROJECTS_ARG="$2"; shift 2 ;;  # projects folder inside Linux (default $HOME/crystalpilot_projects)
        --wrapper)    WRAPPER_SRC="$2"; shift 2 ;;
        -h|--help)    sed -n '4,15p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

CPDIR="$HOME/.crystalpilot"
XDSDIR="$CPDIR/xds"
VENV="$CPDIR/venv"
PROJECTS_DIR_DEFAULT="$HOME/crystalpilot_projects"
# the XDS site offers only the gfortran Linux build now (the INTEL64 file and the XDS-INP/ paths are gone: 404)
XDS_URLS="https://xds.mr.mpg.de/XDS-gfortran_Linux_x86_64.tar.gz https://xds.mr.mpg.de/XDS-INTEL64_Linux_x86_64.tar.gz"

SUDO=""
if [ "$(id -u)" != "0" ]; then SUDO="sudo"; fi

# Colours only on a real terminal (the Windows launcher pipes this output)
if [ -t 1 ]; then
    C1=$(printf '\033[1;36m'); CG=$(printf '\033[32m'); CY=$(printf '\033[33m'); CB=$(printf '\033[1m'); C0=$(printf '\033[0m')
else
    C1=""; CG=""; CY=""; CB=""; C0=""
fi
step()  { printf '\n%s==> %s%s\n' "$C1" "$*" "$C0"; }
ok()    { printf '    %s[ok]%s %s\n' "$CG" "$C0" "$*"; }
warn()  { printf '    %s[!!]%s %s\n' "$CY" "$C0" "$*"; }
# Windows programs (CCP4 bridge) need the WSLInterop binfmt registration; a
# freshly imported runtime, or one where systemd cleared it, does not have it.
ensure_interop() {
    [ -e /proc/sys/fs/binfmt_misc/WSLInterop ] && return 0
    [ -e /proc/sys/fs/binfmt_misc/WSLInterop-late ] && return 0
    local S=""; [ "$(id -u)" != "0" ] && S="sudo -n"
    printf ':WSLInterop:M::MZ::/init:PF' | $S tee /proc/sys/fs/binfmt_misc/register >/dev/null 2>&1 || true
}

STATUS_APP=missing; STATUS_PY=missing; STATUS_XDS=missing; STATUS_NEGGIA=missing; STATUS_CCP4=none; STATUS_WRAPPER=missing
NOTES=()

mkdir -p "$CPDIR" "$XDSDIR"

# ── 1. System packages ───────────────────────────────────────────────────────
step "System packages (apt)"
export DEBIAN_FRONTEND=noninteractive
if command -v apt-get >/dev/null 2>&1; then
    if $SUDO apt-get update -qq >/dev/null 2>&1 && \
       $SUDO apt-get install -y -qq python3 python3-venv python3-pip libgfortran5 libgomp1 libquadmath0 curl ca-certificates tar >/dev/null 2>&1; then
        ok "python3, python3-venv, libgfortran5, libgomp1, curl installed"
    else
        warn "apt-get failed - continuing; Python may already be present"
        NOTES+=("apt-get install failed; if the Python step below also failed, run: sudo apt-get install python3 python3-venv libgfortran5 libgomp1")
    fi
else
    warn "apt-get not found (not Debian/Ubuntu) - install python3, python3-venv, libgfortran5, libgomp1 yourself"
fi

# ── 2. The application ───────────────────────────────────────────────────────
step "CrystalPilot application"
if [ -n "$APP" ] && [ -f "$APP" ]; then
    cp -f "$APP" "$CPDIR/crystalpilot.py" && STATUS_APP=ok && ok "installed $(basename "$APP") -> $CPDIR/crystalpilot.py"
elif [ -f "$CPDIR/crystalpilot.py" ]; then
    STATUS_APP=ok; ok "keeping existing $CPDIR/crystalpilot.py"
else
    warn "no application file given (--app) and none installed yet"
    NOTES+=("The application file (files/xds-gui-vNNN.py) was not found. Re-run setup from the CrystalPilot folder.")
fi

# ── 3. Python environment ────────────────────────────────────────────────────
step "Python environment ($VENV)"
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV" >/dev/null 2>&1 || warn "could not create venv (is python3-venv installed?)"
fi
if [ -x "$VENV/bin/python" ]; then
    "$VENV/bin/python" -m pip install -q --upgrade pip wheel >/dev/null 2>&1 || true
    if "$VENV/bin/python" -m pip install -q numpy h5py hdf5plugin fabio matplotlib gemmi >/dev/null 2>&1; then
        ok "numpy, h5py, hdf5plugin, fabio, matplotlib, gemmi installed"
    elif "$VENV/bin/python" -m pip install -q numpy h5py hdf5plugin fabio matplotlib >/dev/null 2>&1; then
        ok "numpy, h5py, hdf5plugin, fabio, matplotlib installed (gemmi skipped)"
        NOTES+=("gemmi could not be installed; MTZ conversion via gemmi will be unavailable (XDSCONV still works).")
    else
        warn "pip install failed - check the network connection inside WSL"
        NOTES+=("Python packages failed to install. Try: $VENV/bin/pip install numpy h5py hdf5plugin fabio matplotlib")
    fi
    if "$VENV/bin/python" -c "import numpy, h5py, hdf5plugin, fabio, matplotlib" >/dev/null 2>&1; then
        STATUS_PY=ok
    fi
fi

# ── 4. XDS binaries ──────────────────────────────────────────────────────────
step "XDS"
install_xds_tar() {
    local tmp; tmp=$(mktemp -d) || return 1
    tar xzf "$1" -C "$tmp" 2>/dev/null || { rm -rf "$tmp"; return 1; }
    local found; found=$(find "$tmp" -type f -name xds_par | head -1)
    [ -n "$found" ] || { rm -rf "$tmp"; return 1; }
    cp -f "$(dirname "$found")"/* "$XDSDIR"/ && chmod +x "$XDSDIR"/*
    rm -rf "$tmp"
}
if [ -n "$XDS_TAR" ] && [ -f "$XDS_TAR" ]; then
    if install_xds_tar "$XDS_TAR"; then ok "unpacked $(basename "$XDS_TAR")"; else warn "could not unpack $XDS_TAR"; fi
fi
if [ ! -x "$XDSDIR/xds_par" ]; then
    for u in $XDS_URLS; do
        printf '    downloading %s ...\n' "$u"
        if curl -fsSL --connect-timeout 20 -o /tmp/crystalpilot-xds.tgz "$u" && install_xds_tar /tmp/crystalpilot-xds.tgz; then
            ok "downloaded and unpacked XDS"; break
        fi
    done
    rm -f /tmp/crystalpilot-xds.tgz
fi
if [ -x "$XDSDIR/xds_par" ]; then
    # Smoke test: without an XDS.INP the binary must complain about XDS.INP,
    # which proves it loads (right architecture, libraries present).
    tdir=$(mktemp -d); out=$( cd "$tdir" && timeout 30 "$XDSDIR/xds_par" 2>&1 | head -c 400 ); rm -rf "$tdir"
    if printf '%s' "$out" | grep -qi "XDS.INP"; then
        STATUS_XDS=ok; ok "xds_par runs ($XDSDIR)"
    else
        warn "xds_par did not start correctly: $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
        NOTES+=("xds_par is present but failed to start. Output: $(printf '%s' "$out" | head -1)")
    fi
else
    warn "XDS not installed"
    NOTES+=("XDS was not found. Download XDS-gfortran_Linux_x86_64.tar.gz from https://xds.mr.mpg.de (free for academic use), put it in the CrystalPilot folder and run setup again.")
fi

# ── 5. Neggia (HDF5/Eiger reader plugin for XDS) ─────────────────────────────
step "dectris-neggia (Eiger HDF5 support for XDS)"
if [ -n "$NEGGIA" ] && [ -f "$NEGGIA" ]; then
    cp -f "$NEGGIA" "$XDSDIR/dectris-neggia.so" && ok "installed $(basename "$NEGGIA")"
fi
if [ ! -f "$XDSDIR/dectris-neggia.so" ]; then
    # Best effort: latest GitHub release of dectris/neggia
    api=$(curl -fsSL --connect-timeout 20 https://api.github.com/repos/dectris/neggia/releases/latest 2>/dev/null || true)
    url=$(printf '%s' "$api" | grep -o '"browser_download_url": *"[^"]*"' | grep -o 'https://[^"]*' | grep -i 'linux\|neggia' | head -1)
    if [ -n "$url" ]; then
        printf '    downloading %s ...\n' "$url"
        if curl -fsSL -o /tmp/crystalpilot-neggia "$url"; then
            case "$url" in
                *.so) cp -f /tmp/crystalpilot-neggia "$XDSDIR/dectris-neggia.so" ;;
                *.tar.gz|*.tgz)
                    tmp=$(mktemp -d); tar xzf /tmp/crystalpilot-neggia -C "$tmp" 2>/dev/null
                    so=$(find "$tmp" -name 'dectris-neggia.so' | head -1); [ -n "$so" ] && cp -f "$so" "$XDSDIR/dectris-neggia.so"; rm -rf "$tmp" ;;
                *.zip)
                    tmp=$(mktemp -d); (cd "$tmp" && "$VENV/bin/python" -m zipfile -e /tmp/crystalpilot-neggia . 2>/dev/null)
                    so=$(find "$tmp" -name 'dectris-neggia.so' | head -1); [ -n "$so" ] && cp -f "$so" "$XDSDIR/dectris-neggia.so"; rm -rf "$tmp" ;;
            esac
        fi
        rm -f /tmp/crystalpilot-neggia
    fi
fi
if [ -f "$XDSDIR/dectris-neggia.so" ]; then
    chmod +x "$XDSDIR/dectris-neggia.so"; STATUS_NEGGIA=ok; ok "$XDSDIR/dectris-neggia.so"
else
    warn "neggia not installed - only needed for Eiger .h5 data"
    NOTES+=("dectris-neggia.so was not found. For Eiger HDF5 data get it from https://github.com/dectris/neggia/releases, put it in the CrystalPilot folder and run setup again.")
fi

# ── 6. CCP4 (optional) ───────────────────────────────────────────────────────
# Three ways to get POINTLESS/AIMLESS/CTRUNCATE/F2MTZ/CAD, in order of preference:
#   a) a Linux CCP4 tarball (ccp4-X.Y.Z-*linux64*.tar.gz) unpacked into $HOME
#   b) a Linux CCP4 already installed inside WSL (ccp4.setup-sh)
#   c) a CCP4 for Windows installation, run through WSL interop (bridge)
step "CCP4 (optional: POINTLESS, AIMLESS, CTRUNCATE, F2MTZ, CAD)"
prev_setup=""; prev_win=""
if [ -f "$CPDIR/config.env" ]; then
    prev_setup=$( . "$CPDIR/config.env"; printf '%s' "${CCP4_SETUP:-}" )
    prev_win=$( . "$CPDIR/config.env"; printf '%s' "${CCP4_WIN:-}" )
fi
CCP4_MODE=none
CCP4_PROGS="pointless aimless ctruncate f2mtz cad"

# a) Linux tarball
if [ -n "$CCP4_TAR" ] && [ -f "$CCP4_TAR" ]; then
    avail_kb=$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2{print $4}')
    if [ -n "$avail_kb" ] && [ "$avail_kb" -lt 12000000 ]; then
        warn "less than 12 GB free in $HOME - CCP4 needs about 10 GB; skipping $(basename "$CCP4_TAR")"
        NOTES+=("Not enough disk space to unpack CCP4 (about 10 GB needed in $HOME).")
    else
        printf '    unpacking %s into %s - this takes several minutes ...\n' "$(basename "$CCP4_TAR")" "$HOME"
        before=$(ls -d "$HOME"/ccp4-*/ 2>/dev/null | tr '\n' ' ')
        if tar xzf "$CCP4_TAR" -C "$HOME" 2>/dev/null; then
            newdir=""
            for d in "$HOME"/ccp4-*/; do
                case " $before " in *" $d "*) ;; *) newdir="${d%/}" ;; esac
            done
            if [ -z "$newdir" ]; then newdir=$(ls -dt "$HOME"/ccp4-*/ 2>/dev/null | head -1); newdir="${newdir%/}"; fi
            if [ -n "$newdir" ] && [ -f "$newdir/BINARY.setup" ]; then
                printf '    running BINARY.setup ...\n'
                ( cd "$newdir" && yes '' 2>/dev/null | timeout 1800 ./BINARY.setup > /tmp/crystalpilot-ccp4-setup.log 2>&1 ) \
                    || warn "BINARY.setup reported a problem (see /tmp/crystalpilot-ccp4-setup.log)"
            fi
            if [ -n "$newdir" ] && [ -f "$newdir/bin/ccp4.setup-sh" ]; then
                CCP4_SETUP="$newdir/bin/ccp4.setup-sh"; ok "unpacked Linux CCP4 into $newdir"
            else
                warn "tarball unpacked but bin/ccp4.setup-sh was not found"
                NOTES+=("The CCP4 tarball did not contain bin/ccp4.setup-sh - is it the Linux package?")
            fi
        else
            warn "could not unpack $CCP4_TAR"
            NOTES+=("Could not unpack $(basename "$CCP4_TAR") - is the download complete?")
        fi
    fi
fi

# b) existing Linux CCP4
if [ -n "$CCP4_SETUP" ] && [ ! -f "$CCP4_SETUP" ]; then warn "given --ccp4-setup does not exist: $CCP4_SETUP"; CCP4_SETUP=""; fi
if [ -z "$CCP4_SETUP" ] && [ -n "$prev_setup" ] && [ -f "$prev_setup" ]; then CCP4_SETUP="$prev_setup"; fi
if [ -z "$CCP4_SETUP" ]; then
    for c in "$HOME"/ccp4-*/bin/ccp4.setup-sh "$HOME"/CCP4-*/bin/ccp4.setup-sh /opt/xtal/ccp4-*/bin/ccp4.setup-sh /opt/ccp4-*/bin/ccp4.setup-sh /usr/local/ccp4-*/bin/ccp4.setup-sh; do
        if [ -f "$c" ]; then CCP4_SETUP="$c"; break; fi
    done
fi
if [ -n "$CCP4_SETUP" ]; then
    missing=$( . "$CCP4_SETUP" >/dev/null 2>&1; for p in $CCP4_PROGS; do command -v "$p" >/dev/null 2>&1 || printf '%s ' "$p"; done )
    if [ -z "$missing" ]; then
        CCP4_MODE=linux
        ccp4_root=$(dirname "$(dirname "$CCP4_SETUP")")
        STATUS_CCP4="ok (Linux: $ccp4_root)"
        ok "Linux CCP4: $CCP4_SETUP"
    else
        warn "Linux CCP4 at $CCP4_SETUP is missing: $missing"
        NOTES+=("The Linux CCP4 at $CCP4_SETUP lacks $missing - the installation seems incomplete.")
        CCP4_SETUP=""
    fi
fi

# c) Windows CCP4 through WSL interop
if [ "$CCP4_MODE" = none ]; then
    if [ -z "$CCP4_WIN" ] && [ -n "$prev_win" ] && [ -f "$prev_win/bin/pointless.exe" ]; then CCP4_WIN="$prev_win"; fi
    if [ -n "$CCP4_WIN" ] && [ ! -f "$CCP4_WIN/bin/pointless.exe" ]; then
        warn "no bin/pointless.exe under $CCP4_WIN"; CCP4_WIN=""
    fi
    BR="$CPDIR/ccp4win"
    if [ -n "$CCP4_WIN" ]; then
        if [ -n "$BRIDGE_SRC" ] && [ -f "$BRIDGE_SRC" ]; then
            mkdir -p "$BR"
            tr -d '\r' < "$BRIDGE_SRC" > "$BR/ccp4win-run" && chmod +x "$BR/ccp4win-run"
        fi
        if [ -x "$BR/ccp4win-run" ]; then
            for p in $CCP4_PROGS mtzdump truncate freerflag uniqueify sftools mtz2various; do
                if [ -f "$CCP4_WIN/bin/$p.exe" ]; then ln -sf ccp4win-run "$BR/$p"; else rm -f "$BR/$p"; fi
            done
            ensure_interop
            out=$( CCP4_WIN="$CCP4_WIN" timeout 90 "$BR/pointless" </dev/null 2>&1 | head -c 3000 )
            if printf '%s' "$out" | grep -q "POINTLESS"; then
                CCP4_MODE=windows
                win_root=$(wslpath -w "$CCP4_WIN" 2>/dev/null || echo "$CCP4_WIN")
                STATUS_CCP4="ok (Windows CCP4 via WSL: $win_root)"
                ok "Windows CCP4 bridge: $BR -> $win_root"
                NOTES+=("CCP4 programs run from your Windows installation ($win_root). Files pass through the WSL network share, which is slower than a Linux CCP4 but works. For a native setup put ccp4-*-linux64.tar.gz in the CrystalPilot folder and run setup again.")
            else
                warn "Windows CCP4 found at $CCP4_WIN but pointless.exe could not be started from WSL"
                NOTES+=("Windows CCP4 at $CCP4_WIN could not be run from WSL (is Windows interop enabled in /etc/wsl.conf?). First output line: $(printf '%s' "$out" | head -1)")
                CCP4_WIN=""
            fi
        else
            warn "bridge script (--bridge ccp4win-run.sh) missing - cannot use the Windows CCP4"
            CCP4_WIN=""
        fi
    fi
fi
[ "$CCP4_MODE" = windows ] || CCP4_WIN=""
[ "$CCP4_MODE" = linux ]   || CCP4_SETUP=""
if [ "$CCP4_MODE" = none ]; then
    warn "no CCP4 available (XDS, XSCALE and XDSCONV work without it)"
    NOTES+=("CCP4 is optional. Either download the Linux package (ccp4-*-linux64.tar.gz from https://www.ccp4.ac.uk/download) into the CrystalPilot folder, or install CCP4 for Windows - then run setup again and it is picked up automatically.")
fi

# ── 7. Config + wrapper ──────────────────────────────────────────────────────
step "Configuration"
PROJECTS_DIR="$PROJECTS_DIR_DEFAULT"
[ -f "$CPDIR/config.env" ] && prev_pd=$( . "$CPDIR/config.env"; printf '%s' "${PROJECTS_DIR:-}" ) && [ -n "${prev_pd:-}" ] && PROJECTS_DIR="$prev_pd"
[ -n "$PROJECTS_ARG" ] && PROJECTS_DIR="$PROJECTS_ARG"     # chosen in the installer
mkdir -p "$PROJECTS_DIR" || warn "could not create the projects folder $PROJECTS_DIR"
{
    echo "# CrystalPilot WSL configuration (edit and restart)"
    printf '%s=%q\n' PORT "$PORT"
    printf '%s=%q\n' PROJECTS_DIR "$PROJECTS_DIR"
    printf '%s=%q\n' CCP4_MODE "$CCP4_MODE"
    printf '%s=%q\n' CCP4_SETUP "$CCP4_SETUP"
    printf '%s=%q\n' CCP4_WIN "$CCP4_WIN"
} > "$CPDIR/config.env"
ok "wrote $CPDIR/config.env"

if [ -n "$WRAPPER_SRC" ] && [ -f "$WRAPPER_SRC" ]; then
    tr -d '\r' < "$WRAPPER_SRC" > /tmp/crystalpilot-wrapper.$$
    if $SUDO install -m 755 /tmp/crystalpilot-wrapper.$$ /usr/local/bin/crystalpilot 2>/dev/null; then
        STATUS_WRAPPER=ok; ok "installed /usr/local/bin/crystalpilot"
    else
        mkdir -p "$HOME/.local/bin" && install -m 755 /tmp/crystalpilot-wrapper.$$ "$HOME/.local/bin/crystalpilot" && STATUS_WRAPPER=ok && ok "installed $HOME/.local/bin/crystalpilot"
    fi
    rm -f /tmp/crystalpilot-wrapper.$$
elif [ -x /usr/local/bin/crystalpilot ] || [ -x "$HOME/.local/bin/crystalpilot" ]; then
    STATUS_WRAPPER=ok; ok "wrapper already installed"
else
    warn "wrapper script not given (--wrapper)"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
WIN_PROJECTS=$(wslpath -w "$PROJECTS_DIR" 2>/dev/null || echo "$PROJECTS_DIR")
printf '\n%s%s%s\n' "$CB" "CrystalPilot WSL setup summary" "$C0"
printf '  %-22s %s\n' "Application:" "$STATUS_APP" "Python packages:" "$STATUS_PY" "XDS:" "$STATUS_XDS" "Neggia (Eiger h5):" "$STATUS_NEGGIA" "CCP4:" "$STATUS_CCP4" "Launcher wrapper:" "$STATUS_WRAPPER"
printf '  %-22s %s\n' "Projects folder:" "$PROJECTS_DIR"
printf '  %-22s %s\n' "  from Windows:" "$WIN_PROJECTS"
printf '  %-22s %s\n' "Windows drives:" "/mnt/c, /mnt/d, ... (inside the app's file browser)"
if [ ${#NOTES[@]} -gt 0 ]; then
    printf '\n%sNotes%s\n' "$CB" "$C0"
    for n in "${NOTES[@]}"; do printf '  * %s\n' "$n"; done
fi
echo
if [ "$STATUS_APP" = ok ] && [ "$STATUS_PY" = ok ] && [ "$STATUS_WRAPPER" = ok ]; then
    exit 0
else
    exit 1
fi
