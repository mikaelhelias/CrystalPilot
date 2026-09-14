#!/usr/bin/env bash
# CrystalPilot - run a *Windows* CCP4 program from inside WSL.
#
# Installed by wsl-install.sh as ~/.crystalpilot/ccp4win/ccp4win-run, with
# symlinks named pointless, aimless, ctruncate, f2mtz, cad ... pointing at it.
# CrystalPilot calls e.g. "pointless XDSIN /root/.../XDS_ASCII.HKL HKLOUT ..."
# exactly as it would on Linux; this script
#   1. translates every path argument to a Windows path (\\wsl.localhost\...
#      for WSL files, F:\... for /mnt/f files),
#   2. exports the CCP4 environment with Windows-style values via WSLENV,
#   3. runs <CCP4_WIN>\bin\<program>.exe through WSL interop, stdin/stdout
#      pass straight through.
#
# CCP4_WIN is the Linux view of the Windows CCP4 root, e.g. /mnt/f/CCP4-8/8.0,
# taken from ~/.crystalpilot/config.env (or the environment).
#
CPDIR="$HOME/.crystalpilot"
if [ -z "${CCP4_WIN:-}" ] && [ -f "$CPDIR/config.env" ]; then
    CCP4_WIN=$( . "$CPDIR/config.env"; printf '%s' "${CCP4_WIN:-}" )
fi
prog=$(basename "$0")
exe="$CCP4_WIN/bin/$prog.exe"
if [ -z "${CCP4_WIN:-}" ] || [ ! -f "$exe" ]; then
    echo "ccp4win: $prog.exe not found under '${CCP4_WIN:-<unset>}/bin' - re-run CrystalPilot-Setup" >&2
    exit 127
fi

# Translate a Linux path to a Windows path.  wslpath needs the file to exist,
# so for output files translate the parent directory and append the name.
to_win() {
    local p="$1"
    if [ -e "$p" ]; then
        wslpath -w "$p" 2>/dev/null && return 0
    else
        local d; d=$(dirname "$p")
        if [ -d "$d" ]; then
            printf '%s\\%s\n' "$(wslpath -w "$d" 2>/dev/null)" "$(basename "$p")"
            return 0
        fi
    fi
    printf '%s\n' "$p"
}

args=()
for a in "$@"; do
    case "$a" in
        /*) args+=("$(to_win "$a")") ;;
        *)  args+=("$a") ;;
    esac
done

export CCP4="$CCP4_WIN"
export CBIN="$CCP4_WIN/bin"
export CLIB="$CCP4_WIN/lib"
export CLIBD="$CCP4_WIN/lib/data"
export CINCL="$CCP4_WIN/include"
export CLIBD_MON="$CCP4_WIN/lib/data/monomers/"
export MMCIFDIC="$CCP4_WIN/lib/ccp4/cif_mmdic.lib"
export CCP4_SCR="${CCP4_SCR:-$PWD}"
export CCP4_OPEN="${CCP4_OPEN:-UNKNOWN}"
export GFORTRAN_UNBUFFERED_PRECONNECTED=Y
# /p = translate the path when handing the variable to the Windows process
export WSLENV="CCP4/p:CBIN/p:CLIB/p:CLIBD/p:CINCL/p:CLIBD_MON/p:MMCIFDIC/p:CCP4_SCR/p:CCP4_OPEN:GFORTRAN_UNBUFFERED_PRECONNECTED${WSLENV:+:$WSLENV}"

# Windows programs (CCP4 bridge) need the WSLInterop binfmt registration; a
# freshly imported runtime, or one where systemd cleared it, does not have it.
ensure_interop() {
    [ -e /proc/sys/fs/binfmt_misc/WSLInterop ] && return 0
    [ -e /proc/sys/fs/binfmt_misc/WSLInterop-late ] && return 0
    local S=""; [ "$(id -u)" != "0" ] && S="sudo -n"
    printf ':WSLInterop:M::MZ::/init:PF' | $S tee /proc/sys/fs/binfmt_misc/register >/dev/null 2>&1 || true
}

ensure_interop
exec "$exe" "${args[@]}"
