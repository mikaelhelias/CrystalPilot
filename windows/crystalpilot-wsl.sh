#!/usr/bin/env bash
# CrystalPilot control script inside WSL.  Installed by wsl-install.sh as
# /usr/local/bin/crystalpilot and driven by the Windows launcher.
#
#   crystalpilot start [--app FILE] [--port N]   run the server in the foreground
#   crystalpilot stop                            stop a running server
#   crystalpilot status
#   crystalpilot info                            machine-readable settings
#
CPDIR="$HOME/.crystalpilot"
cmd="${1:-start}"; [ $# -gt 0 ] && shift
[ -f "$CPDIR/config.env" ] && . "$CPDIR/config.env"
PORT="${PORT:-8000}"
PROJECTS_DIR="${PROJECTS_DIR:-$HOME/crystalpilot_projects}"
CCP4_SETUP="${CCP4_SETUP:-}"
CCP4_WIN="${CCP4_WIN:-}"
CCP4_MODE="${CCP4_MODE:-none}"
PYTHON="$CPDIR/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

# Match only the python server process ("python -u .../crystalpilot.py"), not
# transient helpers whose command line merely mentions the file (cp, cmp).
SERVER_RE="python[0-9.]* -u $CPDIR/crystalpilot.py"
is_running() {
    pgrep -f "$SERVER_RE" >/dev/null 2>&1 && return 0
    # A CrystalPilot started another way (e.g. by hand) also counts; a foreign
    # program on the port does not - the start command then reports it.
    if command -v curl >/dev/null 2>&1; then
        curl -fs -m 2 "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q '"version"' && return 0
    fi
    return 1
}
port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; }

# Windows programs (CCP4 bridge) need the WSLInterop binfmt registration; a
# freshly imported runtime, or one where systemd cleared it, does not have it.
ensure_interop() {
    [ -e /proc/sys/fs/binfmt_misc/WSLInterop ] && return 0
    [ -e /proc/sys/fs/binfmt_misc/WSLInterop-late ] && return 0
    local S=""; [ "$(id -u)" != "0" ] && S="sudo -n"
    printf ':WSLInterop:M::MZ::/init:PF' | $S tee /proc/sys/fs/binfmt_misc/register >/dev/null 2>&1 || true
}

case "$cmd" in
  start)
    APP=""; MANUAL=""; NET_DRIVES=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --app)    APP="$2";  shift 2 ;;
            --manual) MANUAL="$2"; shift 2 ;;        # docs/manual folder on the Windows side
            --port)   PORT="$2"; shift 2 ;;
            --net)    NET_DRIVES+=("$2"); shift 2 ;;   # "Z:=\\server\share" (from the launcher)
            *) shift ;;
        esac
    done
    # The illustrated manual is served by the app from $CPDIR/docs/manual; keep a
    # copy in sync with the Windows folder (only when the HTML changed).
    if [ -n "$MANUAL" ] && [ -f "$MANUAL/CrystalPilot-Manual.html" ]; then
        if ! cmp -s "$MANUAL/CrystalPilot-Manual.html" "$CPDIR/docs/manual/CrystalPilot-Manual.html" 2>/dev/null; then
            mkdir -p "$CPDIR/docs/manual" && cp -f "$MANUAL"/CrystalPilot-Manual.* "$CPDIR/docs/manual/" 2>/dev/null && echo "[crystalpilot] updated the illustrated manual"
        fi
    fi
    # WSL mounts fixed drives under /mnt automatically but not mapped network
    # drives.  Mount the ones the launcher reports so they show up as Z:, Y:, ...
    # buttons in the app's folder browser.
    mount_net_drive() {
        local spec="$1" letter unc lower mp S opts
        letter="${spec%%=*}"; unc="${spec#*=}"
        lower=$(printf '%s' "${letter%:}" | tr 'A-Z' 'a-z')
        [ ${#lower} -eq 1 ] || return 0
        mp="/mnt/$lower"
        if mountpoint -q "$mp" 2>/dev/null; then return 0; fi
        mkdir -p "$mp" 2>/dev/null || return 0
        S=""; opts="noatime"
        if [ "$(id -u)" != "0" ]; then S="sudo -n"; opts="$opts,uid=$(id -u),gid=$(id -g)"; fi
        # A disconnected share can block a mount attempt for a minute or more,
        # so every attempt gets a short timeout and the drives are done in parallel.
        timeout 8 $S mount -t drvfs "$letter" "$mp" -o "$opts" 2>/dev/null; rc=$?
        # rc 124 = timed out: the share itself is unreachable, the UNC path would only time out again
        if [ $rc -ne 0 ] && [ $rc -ne 124 ] && [ -n "$unc" ] && [ "$unc" != "$spec" ]; then
            timeout 8 $S mount -t drvfs "$unc" "$mp" -o "$opts" 2>/dev/null; rc=$?
        fi
        if [ $rc -eq 0 ]; then
            echo "[crystalpilot] network drive $letter ($unc) -> $mp"
        else
            echo "[crystalpilot] network drive $letter ($unc) is not reachable right now - skipped"
            rmdir "$mp" 2>/dev/null
        fi
    }
    if [ ${#NET_DRIVES[@]} -gt 0 ]; then
        echo "[crystalpilot] mounting network drives ..."
        for spec in "${NET_DRIVES[@]}"; do mount_net_drive "$spec" & done
        wait
    fi
    # Pick up a newer build handed over by the launcher (developer workflow:
    # rebuild on Windows, relaunch, done).
    if [ -n "$APP" ] && [ -f "$APP" ] && ! cmp -s "$APP" "$CPDIR/crystalpilot.py"; then
        cp -f "$APP" "$CPDIR/crystalpilot.py" && echo "[crystalpilot] updated application from $(basename "$APP")"
    fi
    if [ ! -f "$CPDIR/crystalpilot.py" ]; then
        echo "CrystalPilot is not installed in WSL yet - run CrystalPilot-Setup.bat first." >&2
        exit 1
    fi
    if is_running; then
        echo "[crystalpilot] already running - open http://localhost:$PORT"
        exit 0
    fi
    if port_busy; then
        echo "[crystalpilot] port $PORT is used by another program - change PORT in $CPDIR/config.env" >&2
        exit 4
    fi
    if [ -n "$CCP4_SETUP" ] && [ -f "$CCP4_SETUP" ]; then
        # Linux CCP4 inside WSL
        # shellcheck disable=SC1090
        . "$CCP4_SETUP" >/dev/null 2>&1 || true
    elif [ -n "$CCP4_WIN" ] && [ -x "$CPDIR/ccp4win/pointless" ]; then
        # CCP4 for Windows, driven through WSL interop (see ccp4win-run)
        ensure_interop
        export CCP4_WIN
        export PATH="$CPDIR/ccp4win:$PATH"
    fi
    export PATH="$CPDIR/xds:$PATH"
    # The app creates ./projects in its working directory at import time
    # unless XDS_GUI_PROJECTS is set; point it at the real folder.
    export XDS_GUI_PROJECTS="$PROJECTS_DIR"
    mkdir -p "$PROJECTS_DIR"
    cd "$CPDIR" || exit 1
    echo "[crystalpilot] projects: $PROJECTS_DIR  (Windows: $(wslpath -w "$PROJECTS_DIR" 2>/dev/null))"
    exec "$PYTHON" -u "$CPDIR/crystalpilot.py" --port "$PORT" --host 127.0.0.1 \
         --xds-path "$CPDIR/xds" --projects-dir "$PROJECTS_DIR"
    ;;
  stop)
    if pgrep -f "$SERVER_RE" >/dev/null 2>&1; then
        pkill -f "$SERVER_RE"; sleep 1
        pgrep -f "$SERVER_RE" >/dev/null 2>&1 && pkill -9 -f "$SERVER_RE"
        echo "[crystalpilot] stopped"
    else
        echo "[crystalpilot] not running"
    fi
    ;;
  status)
    if is_running; then echo "running on http://localhost:$PORT"; else echo "not running"; exit 3; fi
    ;;
  info)
    echo "INSTALLED=$([ -f "$CPDIR/crystalpilot.py" ] && echo yes || echo no)"
    echo "PORT=$PORT"
    echo "PROJECTS_DIR=$PROJECTS_DIR"
    echo "PROJECTS_WIN=$(wslpath -w "$PROJECTS_DIR" 2>/dev/null)"
    echo "XDS=$([ -x "$CPDIR/xds/xds_par" ] && echo yes || echo no)"
    echo "NEGGIA=$([ -f "$CPDIR/xds/dectris-neggia.so" ] && echo yes || echo no)"
    case "$CCP4_MODE" in
        linux)   echo "CCP4=Linux ($(dirname "$(dirname "$CCP4_SETUP")"))" ;;
        windows) echo "CCP4=Windows via WSL ($(wslpath -w "$CCP4_WIN" 2>/dev/null || echo "$CCP4_WIN"))" ;;
        *)       echo "CCP4=none" ;;
    esac
    echo "RUNNING=$(pgrep -f "$SERVER_RE" >/dev/null 2>&1 && echo yes || echo no)"
    ;;
  *)
    echo "usage: crystalpilot start|stop|status|info" >&2; exit 2 ;;
esac
