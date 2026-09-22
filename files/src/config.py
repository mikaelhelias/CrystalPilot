#!/usr/bin/env python3
"""
XDS GUI - Minimal Version
Zero external dependencies - Python stdlib only
"""

import sys as _sys_early
if _sys_early.version_info < (3, 7):
    _sys_early.exit(
        "CrystalPilot requires Python 3.7 or later.\n"
        "You are running Python %d.%d.%d.\n"
        "Please install a newer Python version."
        % _sys_early.version_info[:3]
    )
del _sys_early

VERSION = "0.6.6c"

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def server_bind(self):
        """Enable SO_REUSEPORT on macOS/Linux to allow fast restarts."""
        import socket
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (OSError, socket.error):
                pass  # Not supported on this kernel/platform
        super().server_bind()

import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import urllib.parse
import os
import sys
import io
import base64
import re
import threading
import signal
import argparse

# ── Optional scientific deps (for frame viewer) ──────────────────────────────
import os as _os, sys as _sys, site as _site

# Add user site-packages to sys.path at startup so packages installed with
# pip --user are found on every run, not just the session they were installed in.
def _ensure_user_site():
    try:
        _u = _site.getusersitepackages()
        if _u not in _sys.path:
            _sys.path.insert(0, _u)
    except Exception:
        pass
_ensure_user_site()

# Console encoding: the banner and the HDF5 header diagnostics contain
# non-ASCII characters (box drawing, Å).  On Windows consoles and under the C
# locale the default codec is not UTF-8, and a failed print aborts whatever
# request triggered it — so switch stdout/stderr to UTF-8 with replacement.
for _stream in (_sys.stdout, _sys.stderr):
    try:
        if _stream is not None and hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# HDF5 file locking: Eiger data usually lives on NFS/Lustre/SMB shares where
# the HDF5 library's advisory locks fail with "unable to lock file" (errno 11)
# or "file locking disabled on this file system".  The GUI only ever reads
# frames, so disable locking unless the user has chosen a setting explicitly.
_os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")

# Fix HDF5 plugin path BEFORE h5py/fabio are imported.
# Must be set to an existing directory or HDF5 raises "can't open directory"
# on every compressed read (LZ4/bitshuffle used by Eiger detectors).
def _setup_hdf5_plugin_path():
    if _os.environ.get("HDF5_PLUGIN_PATH"):
        return
    try:
        import hdf5plugin as _h
        # hdf5plugin registers its filters on import; the env var is only a
        # courtesy for other HDF5 users in this process.  Point it at the real
        # plugin directory, not the package root.
        _os.environ["HDF5_PLUGIN_PATH"] = getattr(_h, "PLUGIN_PATH", None) or \
            _os.path.join(_os.path.dirname(_h.__file__), "plugins")
        return
    except ImportError:
        pass
    import tempfile as _tf
    for _c in ["/usr/lib/x86_64-linux-gnu/hdf5/plugins",
               "/usr/lib64/hdf5/plugins",
               "/usr/local/hdf5/lib/plugin",
               "/usr/lib/hdf5/plugins",
               "/opt/homebrew/lib/hdf5/plugin",          # macOS Homebrew ARM
               "/usr/local/lib/hdf5/plugin",              # macOS Homebrew Intel
               _os.path.join(_os.environ.get("CONDA_PREFIX", ""), "lib", "hdf5", "plugin"),  # Conda
               "/usr/lib/aarch64-linux-gnu/hdf5/plugins", # Linux ARM64 (Debian/Ubuntu)
               ]:
        if _os.path.isdir(_c):
            _os.environ["HDF5_PLUGIN_PATH"] = _c
            return
    _os.environ["HDF5_PLUGIN_PATH"] = _tf.gettempdir()
_setup_hdf5_plugin_path()

# Each entry: (apt_pkg, dnf_pkg, pip_pkg, import_name, pacman_pkg, zypper_pkg)
# None means the package is not available in that repo and pip is the only option.
_DEPS = [
    ("python3-numpy",      "python3-numpy",      "numpy",      "numpy",      "python-numpy",      "python3-numpy"),
    ("python3-matplotlib", "python3-matplotlib", "matplotlib", "matplotlib", "python-matplotlib", "python3-matplotlib"),
    ("python3-h5py",       "python3-h5py",       "h5py",       "h5py",       "python-h5py",       "python3-h5py"),
    ("python3-hdf5plugin", None,                 "hdf5plugin", "hdf5plugin", None,                None),
    ("python3-fabio",      None,                 "fabio",      "fabio",      None,                None),
]

def _check_deps():
    missing = []
    # Invalidate finder caches so freshly-installed packages are discovered
    try: import importlib; importlib.invalidate_caches()
    except Exception: pass
    # Ensure user and system site-packages are on sys.path
    try:
        import site as _sd
        _u = _sd.getusersitepackages()
        if _u and _u not in _sys.path:
            _sys.path.insert(0, _u)
        for _sp in _sd.getsitepackages():
            if _sp not in _sys.path:
                _sys.path.append(_sp)
    except Exception: pass
    for entry in _DEPS:
        imp = entry[3]  # import_name is always at index 3
        # Only clear cached import *failures* (None entries in sys.modules).
        # Never pop an already-loaded module — reimporting numpy/fabio/etc.
        # mid-session causes infinite recursion or subtle corruption.
        if _sys.modules.get(imp) is None and imp in _sys.modules:
            del _sys.modules[imp]
        try: __import__(imp)
        except ImportError: missing.append(entry)
    return missing

# ═════════════════════════════════════════════════════════════════════════════
#  THE LOG FILE
#
#  Everything the program prints also goes to a file, because "look at the
#  console window" is no help to someone who closed it - and on Windows the
#  console belongs to a launcher the user never sees.  The file lives in the
#  projects folder, which is the one place every install can reach from
#  Explorer (desktop shortcut, Quick Access, P:\Projects).
#
#  XDS_GUI_LOG=<path>  put it somewhere else
#  XDS_GUI_LOG=off     write no file
#
#  The stream is only ever a tee: if the file cannot be written the program
#  carries on printing to the console, because a broken log must not stop a
#  data-processing run.
# ═════════════════════════════════════════════════════════════════════════════
LOG_MAX_BYTES = 2 * 1024 * 1024      # rotate at 2 MB
LOG_KEEP = 3                         # crystalpilot.log.1 .. .3
LOG_PATH = None                      # set by _start_logging()


class _LogTee:
    """Writes to the original stream and appends to the log file."""

    def __init__(self, stream, path):
        self._stream = stream
        self._path = path
        self._lock = threading.Lock()

    def write(self, text):
        try:
            self._stream.write(text)
        except Exception:
            pass
        if not text.strip():
            self._append(text)
            return text and len(text) or 0
        self._append(text)
        return len(text)

    def _append(self, text):
        with self._lock:
            try:
                self._rotate()
                self._write(text)
            except Exception:
                try:
                    # The folder can be missing at the first line (nothing has
                    # created it yet) or later on (a projects folder on a mount
                    # that went away and came back). Make it and write again;
                    # only then give up, silently, because a log that cannot be
                    # written must never interrupt a data-processing run.
                    self._path.parent.mkdir(parents=True, exist_ok=True)
                    self._write(text)
                except Exception:
                    pass

    def _write(self, text):
        with open(self._path, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(self._redact(text))

    @staticmethod
    def _redact(text):
        """Never write the API token to a file.

        The console shows it on purpose - whoever sees the console already runs
        the program.  The log lives in the projects folder, which other people
        may be able to read, and the token drives every API route.  It appears
        in the banner and in any URL a request error echoes, so it is removed
        on the way to the file rather than at each call site.
        """
        try:
            if API_TOKEN and API_TOKEN in text:
                return text.replace(API_TOKEN, "<token hidden: see the console>")
        except Exception:
            pass
        return text

    def _rotate(self):
        try:
            if self._path.exists() and self._path.stat().st_size < LOG_MAX_BYTES:
                return
            if not self._path.exists():
                return
            for n in range(LOG_KEEP, 0, -1):
                older = self._path.with_name(self._path.name + "." + str(n))
                newer = self._path.with_name(self._path.name + "." + str(n - 1)) if n > 1 else self._path
                if newer.exists():
                    if older.exists():
                        older.unlink()
                    newer.rename(older)
        except Exception:
            pass

    def flush(self):
        try:
            self._stream.flush()
        except Exception:
            pass

    def isatty(self):
        try:
            return self._stream.isatty()
        except Exception:
            return False

    def fileno(self):
        return self._stream.fileno()


def _start_logging():
    """Tee stdout and stderr into the log file. Returns its path, or None."""
    global LOG_PATH
    setting = (os.environ.get("XDS_GUI_LOG") or "").strip()
    if setting.lower() in ("off", "none", "0", "false"):
        return None
    try:
        path = Path(setting) if setting else (PROJECTS_DIR / "logs" / "crystalpilot.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        tee = _LogTee(sys.stdout, path)
        sys.stdout = tee
        sys.stderr = _LogTee(sys.stderr, path)
        LOG_PATH = path
        return path
    except Exception:
        return None


MISSING_DEPS = _check_deps()
VIEWER_READY = len(MISSING_DEPS) == 0

# Set Agg backend once at startup if matplotlib is available (must be before any pyplot import)
if VIEWER_READY or not any(e[3] == "matplotlib" for e in MISSING_DEPS):
    try:
        import matplotlib
        matplotlib.use("Agg")
    except Exception:
        pass

# Configuration — defaults; overridden by CLI args / env vars in main()
PROJECTS_DIR = Path(os.environ.get("XDS_GUI_PROJECTS", str(Path.cwd() / "projects")))
# main() replaces this when --projects-dir is given; do not litter the current
# folder with an unused ./projects in that case.
if "--projects-dir" not in sys.argv:
    try:
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as _e:
        print(f"Warning: cannot create projects folder {PROJECTS_DIR}: {_e}")
# ── Persistent per-machine settings ──────────────────────────────────────────
# ~/.crystalpilot/settings.json holds what the user set in the interface:
# xds_path, neggia_lib, ccp4_bin, parallel.  Precedence at start-up:
# command line > settings file > environment variable > built-in default.
SETTINGS_FILE = Path(os.environ.get("XDS_GUI_SETTINGS", str(Path.home() / ".crystalpilot" / "settings.json")))

def _load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_settings(**kv):
    """Merge the given keys into the settings file (None values are skipped)."""
    try:
        s = _load_settings()
        s.update({k: v for k, v in kv.items() if v is not None})
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # write a temporary file and rename it: a crash or a second save half-way
        # through must never leave a broken file that silently resets every setting
        tmp = SETTINGS_FILE.with_name(SETTINGS_FILE.name + ".%d.tmp" % os.getpid())
        tmp.write_text(json.dumps(s, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(SETTINGS_FILE))
        return True
    except Exception:
        return False

SETTINGS = _load_settings()

XDS_PATH = Path(os.environ.get("XDS_GUI_XDS_PATH", str(Path(__file__).parent.resolve())))
if SETTINGS.get("xds_path") and Path(str(SETTINGS["xds_path"])).is_dir():
    XDS_PATH = Path(str(SETTINGS["xds_path"]))

# Use the parallel binaries (xds_par / xscale_par)?  Can be switched off in the
# interface when they misbehave on a machine.
XDS_PARALLEL = bool(SETTINGS.get("parallel", os.environ.get("XDS_GUI_PARALLEL", "1").lower() not in ("0", "false", "no")))
# Time limit (seconds) for one program run (an XDS step, XSCALE, POINTLESS ...);
# the process and its children are killed when it is exceeded.  0 = no limit.
try:
    XDS_STEP_TIMEOUT = int(float(SETTINGS.get("step_timeout", os.environ.get("XDS_GUI_STEP_TIMEOUT", "14400"))))
except (TypeError, ValueError):
    XDS_STEP_TIMEOUT = 14400
PORT = int(os.environ.get("XDS_GUI_PORT", "8000"))
# Listen on this computer only unless asked otherwise (--host 0.0.0.0 for the LAN).
HOST = os.environ.get("XDS_GUI_HOST", "127.0.0.1")
# Per-launch API token.  The page sets it as a SameSite cookie when served, so
# the browser tab that opened CrystalPilot is authorised and another web site
# open in the same browser is not.  Scripts pass it as X-CrystalPilot-Token
# or ?token=; XDS_GUI_TOKEN fixes it for automation.
import secrets as _secrets
import hmac
API_TOKEN = os.environ.get("XDS_GUI_TOKEN", "").strip() or _secrets.token_urlsafe(24)
RESTRICT_BROWSE = os.environ.get("XDS_GUI_RESTRICT_BROWSE", "").lower() in ("1", "true", "yes")

# Where "Report a problem" sends users: the author's address for bug reports.
# Empty = no address; the report can still be saved as a zip.  A lab that
# supports its own installation can point it elsewhere with XDS_GUI_REPORT_EMAIL.
# (stored encoded so address harvesters scanning the source do not pick it up)
import base64 as _b64
REPORT_EMAIL_DEFAULT = _b64.b64decode("bWlrYWVsLmVsaWFzLmdpdEBnbWFpbC5jb20=").decode("ascii")
REPORT_EMAIL = (os.environ.get("XDS_GUI_REPORT_EMAIL") or REPORT_EMAIL_DEFAULT).strip()

# Running inside Windows Subsystem for Linux?  Windows drives then appear
# under /mnt/<letter>; the file browser offers them as shortcuts.
def _detect_wsl():
    try:
        with open("/proc/version", "r", encoding="utf-8", errors="replace") as _f:
            return "microsoft" in _f.read().lower()
    except Exception:
        return False
IS_WSL = _detect_wsl()

def _wsl_automount_root():
    """Where WSL puts the Windows drives.  /mnt/ unless /etc/wsl.conf says
    otherwise ([automount] root=/): with root=/ the drives are /c, /d ... and
    looking only under /mnt would find nothing at all."""
    root = "/mnt/"
    if not IS_WSL:
        return root
    try:
        section = ""
        with open("/etc/wsl.conf", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.split("#", 1)[0].split(";", 1)[0].strip()
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip().lower()
                elif section == "automount" and "=" in line:
                    key, val = line.split("=", 1)
                    if key.strip().lower() == "root":
                        val = val.strip().strip('"').strip("'")
                        if val:
                            root = val if val.endswith("/") else val + "/"
    except Exception:
        pass
    return root

WSL_MOUNT_ROOT = _wsl_automount_root()

def _wsl_drives():
    """Windows drives currently mounted inside WSL, e.g. ['/mnt/c', '/mnt/z'].

    Only real mount points are listed: a leftover empty /mnt/z directory from a
    network drive that is not reachable right now must not show up as a button.
    """
    drives = []
    if IS_WSL:
        try:
            for d in sorted(Path(WSL_MOUNT_ROOT).iterdir()):
                if len(d.name) == 1 and d.name.isalpha() and d.is_dir() and os.path.ismount(str(d)):
                    drives.append(str(d))
        except Exception:
            pass
    return drives

# CCP4 detection
CCP4_PROGRAMS = ("pointless", "aimless", "ctruncate", "f2mtz", "cad")

# A CCP4 for Windows bin folder (pointless.exe ...) can be run from WSL through
# interop; anywhere else only real Linux programs count.
_CCP4_EXE_OK = IS_WSL or os.name == "nt"


def _is_ccp4_bin(folder):
    """True when this folder holds at least one of the programs we run."""
    try:
        d = Path(folder)
    except Exception:
        return False
    for n in CCP4_PROGRAMS:
        if (d / n).is_file() or (_CCP4_EXE_OK and (d / (n + ".exe")).is_file()):
            return True
    return False


# The folder saved in the settings is checked, not trusted: a CCP4 that was
# moved, removed or reinstalled elsewhere must not leave a dead path behind
# that makes every program look missing.  CCP4_BIN_SAVED keeps what was saved
# so the interface can say why it is not used.
CCP4_BIN_SAVED = str(SETTINGS.get("ccp4_bin") or "")
CCP4_BIN = CCP4_BIN_SAVED if CCP4_BIN_SAVED and _is_ccp4_bin(CCP4_BIN_SAVED) else ""


def _ccp4_program(name, folder=None):
    """Find CCP4 program `name` in the CCP4 bin folder.

    Returns (path, kind, problem).  kind is "unix" for a program that runs as
    it is, "windows" for name.exe of a CCP4 for Windows run through WSL
    interop, "" when it cannot be run - problem then says why, in words the
    user can act on.
    """
    folder = folder if folder is not None else CCP4_BIN
    if not folder:
        return None, "", "CCP4 not found"
    d = Path(folder)
    if not d.is_dir():
        return None, "", "the CCP4 folder " + str(d) + " does not exist"
    p = d / name
    if p.is_file():
        return p, "unix", ""
    if p.is_symlink():
        try:
            target = os.readlink(str(p))
        except OSError:
            target = "?"
        return None, "", (name + " in " + str(d) + " is a broken link (to " + target + "): the CCP4 installation "
                          "is incomplete - run BINARY.setup in the CCP4 folder, or install CCP4 again")
    pe = d / (name + ".exe")
    if pe.is_file():
        if os.name == "nt":
            return pe, "unix", ""
        if IS_WSL:
            return pe, "windows", ""
        return None, "", (str(d) + " holds " + name + ".exe, a CCP4 for Windows, which cannot run on Linux - "
                          "install the Linux CCP4")
    return None, "", name + " not found in " + str(d)


def _wsl_win_path(p):
    """Windows form of a Linux path for a Windows program (wslpath needs the
    file to exist, so an output file is translated through its folder)."""
    try:
        if os.path.exists(p):
            return subprocess.run(["wslpath", "-w", p], capture_output=True, text=True,
                                  timeout=10).stdout.strip() or p
        d, base = os.path.split(p)
        if d and os.path.isdir(d):
            wd = subprocess.run(["wslpath", "-w", d], capture_output=True, text=True, timeout=10).stdout.strip()
            if wd:
                return wd.rstrip("\\") + "\\" + base
    except Exception:
        pass
    return p


def _ensure_wsl_interop():
    """Windows programs need the WSLInterop binfmt entry; a runtime where
    systemd cleared it gets it back (same as the ccp4win-run bridge)."""
    if os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop") or \
       os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop-late"):
        return
    try:
        with open("/proc/sys/fs/binfmt_misc/register", "w") as f:
            f.write(":WSLInterop:M::MZ::/init:PF")
    except OSError:
        pass


def _ccp4_command(name, args, scratch, env=None):
    """Command line and environment to run CCP4 program `name` with `args`.

    A Linux CCP4 runs directly with the CCP4 variables filled in where the
    shell did not set them.  A CCP4 for Windows under WSL runs its .exe
    through interop: path arguments and the CCP4 variables are handed over in
    Windows form, as windows/ccp4win-run.sh does for the installer's bridge.
    Raises RuntimeError with the reason when the program cannot be run.
    """
    path, kind, problem = _ccp4_program(name)
    if path is None:
        raise RuntimeError(problem)
    env = dict(os.environ if env is None else env)
    root = path.parent.parent
    if kind == "windows":
        _ensure_wsl_interop()
        for var, val in (("CCP4", root), ("CBIN", root / "bin"), ("CLIB", root / "lib"),
                         ("CLIBD", root / "lib" / "data"), ("CINCL", root / "include"),
                         ("CLIBD_MON", str(root / "lib" / "data" / "monomers") + "/"),
                         ("MMCIFDIC", root / "lib" / "ccp4" / "cif_mmdic.lib"), ("CCP4_SCR", scratch)):
            env[var] = str(val)
        env.setdefault("CCP4_OPEN", "UNKNOWN")
        env["GFORTRAN_UNBUFFERED_PRECONNECTED"] = "Y"
        wslenv = "CCP4/p:CBIN/p:CLIB/p:CLIBD/p:CINCL/p:CLIBD_MON/p:MMCIFDIC/p:CCP4_SCR/p:CCP4_OPEN:GFORTRAN_UNBUFFERED_PRECONNECTED"
        env["WSLENV"] = wslenv + (":" + env["WSLENV"] if env.get("WSLENV") else "")
        return [str(path)] + [_wsl_win_path(a) if a.startswith("/") else a for a in map(str, args)], env
    env.setdefault("CCP4", str(root))
    env.setdefault("CLIBD", str(root / "lib" / "data"))
    env.setdefault("CCP4_SCR", str(scratch))
    env.setdefault("CINCL", str(root / "include"))
    env["PATH"] = str(path.parent) + os.pathsep + env.get("PATH", "")
    return [str(path)] + [str(a) for a in args], env


def _find_ccp4_bin():
    """Locate the CCP4 bin folder.  Returns the path or an empty string.

    CCP4 9 is installed by unpacking an archive wherever the user likes, so
    there is no fixed place to look: try the environment first (a sourced
    ccp4.setup-sh), then a broad set of roots two levels deep.  Any of the
    programs CrystalPilot actually runs counts - keying the whole detection
    on f2mtz alone missed installations that have everything else.
    """
    import glob as _glob

    # 1. on PATH - the user sourced ccp4.setup-sh in the shell that started us
    for n in CCP4_PROGRAMS:
        hit = shutil.which(n)
        if hit:
            return str(Path(hit).parent)

    # 2. what ccp4.setup-sh leaves in the environment
    for var in ("CBIN", "CCP4_BIN"):
        val = os.environ.get(var, "")
        if val and _is_ccp4_bin(val):
            return str(Path(val))
    for var in ("CCP4", "CCP4_MASTER"):
        val = os.environ.get(var, "")
        if not val:
            continue
        for cand in (Path(val) / "bin", Path(val)):
            if _is_ccp4_bin(cand):
                return str(cand)
        for hit in sorted(_glob.glob(str(Path(val) / "[Cc][Cc][Pp]4*" / "bin")), reverse=True):
            if _is_ccp4_bin(hit):
                return hit

    # 3. the usual places, plus where a downloaded archive is unpacked
    home = Path.home()
    roots = [Path("/opt"), Path("/opt/xtal"), Path("/usr/local"), Path("/usr/local/xtal"),
             Path("/software"), Path("/Applications"), home, home / "Downloads",
             home / "Documents", home / "Desktop", home / "Applications", home / "software"]
    seen = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        if not root.is_dir():
            continue
        for pat in ("[Cc][Cc][Pp]4*/bin", "[Cc][Cc][Pp]4*/*/bin"):
            for hit in sorted(_glob.glob(str(root / pat)), reverse=True):   # newest first
                if _is_ccp4_bin(hit):
                    return hit
    return ""


# ── XDSCC12 detection ─────────────────────────────────────────────────────────
# XDSCC12: standalone binary by Kay Diederichs (Uni Konstanz).
# Computes per-frame ΔCC½ for identifying bad/damaged frames.
# Reference: Assmann, Brehm & Diederichs (2016) J. Appl. Cryst. 49, 1021-1028.

XDSCC12_URLS = {
    "Linux":  "https://wiki.uni-konstanz.de/pub/linux_bin/xdscc12",
    "Darwin": "https://wiki.uni-konstanz.de/pub/mac_bin/xdscc12",
}

XDSCC12_BIN = ""  # Auto-detected at startup; set alongside CCP4_BIN in runner.py

def _find_xdscc12():
    """Try to locate the xdscc12 binary. Returns full path string or empty string."""
    import platform as _plat
    # 1. Check PATH
    found = shutil.which("xdscc12")
    if found:
        return found
    # 2. Check alongside XDS binaries
    candidate = XDS_PATH / "xdscc12"
    if candidate.exists():
        return str(candidate)
    # 3. Check common locations
    search_dirs = [
        Path.home() / ".local" / "bin",
        Path.home() / "bin",
        Path("/usr/local/bin"),
    ]
    if _plat.system() == "Darwin":
        search_dirs.append(Path("/opt/homebrew/bin"))
    for d in search_dirs:
        c = d / "xdscc12"
        if c.exists():
            return str(c)
    return ""

# ── Neggia / HDF5 reader library for XDS ──────────────────────────────────────
# XDS requires LIB= pointing to dectris-neggia.so (or equivalent) to read HDF5
# data frames (Eiger detectors).  Without it, XDS cannot open .h5 files.
# The library is distributed by DECTRIS and often installed alongside XDS.

NEGGIA_LIB = ""  # Auto-detected at startup; can be set via Settings or CLI

def _clean_path_setting(value, filenames=()):
    """Make what a user typed or pasted into a usable path.

    Strips blanks and surrounding quotes (a path pasted from a terminal often
    carries a trailing space, one from Explorer a pair of quotes), expands ~
    and $HOME, and accepts a folder when the file is inside it.  Returns ""
    for an empty value.  The path is not required to exist - the caller
    decides what to do when it does not.
    """
    v = str(value or "").strip().strip('"').strip("'").strip()
    if not v:
        return ""
    v = os.path.expandvars(os.path.expanduser(v))
    p = Path(v)
    if filenames and p.is_dir():
        for n in filenames:
            if (p / n).is_file():
                return str(p / n)
    return str(p)


NEGGIA_NAMES = ('dectris-neggia.so', 'dectris-neggia.dylib')


def _find_neggia():
    """Try to locate the dectris-neggia shared library.

    Search order:
      1. XDS_PATH (alongside xds_par / xds binary)
      2. Common system/user locations on Linux and macOS
      3. NEGGIA environment variable (if set by the user)

    Returns the full path string or empty string.
    """
    import platform as _plat
    import glob as _glob_neg

    names = ['dectris-neggia.so', 'dectris-neggia.dylib']
    if _plat.system() == 'Darwin':
        names = ['dectris-neggia.dylib', 'dectris-neggia.so']

    # 0. Environment variable override
    env_val = os.environ.get('NEGGIA', '')
    if env_val and os.path.isfile(env_val):
        return env_val

    # 1. Alongside XDS binaries
    for n in names:
        candidate = XDS_PATH / n
        if candidate.exists():
            return str(candidate)

    # 2. Common installation locations
    search_dirs = [
        Path.home() / '.local' / 'lib',
        Path.home() / 'lib',
        Path('/usr/local/lib'),
        Path('/usr/lib'),
    ]
    if _plat.system() == 'Darwin':
        search_dirs.extend([
            Path('/opt/homebrew/lib'),
            Path('/usr/local/lib/xds'),
        ])
    else:
        search_dirs.extend([
            Path('/usr/local/lib/xds'),
            Path('/usr/lib/x86_64-linux-gnu'),
            Path('/usr/lib/aarch64-linux-gnu'),
        ])
    for d in search_dirs:
        for n in names:
            c = d / n
            if c.exists():
                return str(c)
    # 3. Glob alongside XDS common install locations
    for pat in ['/opt/xds/*/dectris-neggia.*',
                str(Path.home() / 'xds' / '*' / 'dectris-neggia.*'),
                '/usr/local/xds/*/dectris-neggia.*']:
        hits = _glob_neg.glob(pat)
        if hits:
            return hits[0]

    return ''

# XDS Pipeline
XDS_PIPELINE = ["XYCORR", "INIT", "COLSPOT", "IDXREF", "DEFPIX","XPLAN", "INTEGRATE", "CORRECT"]

# Run neggia auto-detection at startup
try:
    NEGGIA_LIB = _find_neggia()
except Exception:
    NEGGIA_LIB = ""
# A path the user set in the interface wins over auto-detection.  It used to
# be dropped without a word when it did not point at a file any more (a pasted
# trailing space was enough), which looked exactly like "the program does not
# save the path": keep it and let the Environment screen report it instead.
NEGGIA_LIB_SET = _clean_path_setting(SETTINGS.get("neggia_lib"), NEGGIA_NAMES)
if NEGGIA_LIB_SET:
    NEGGIA_LIB = NEGGIA_LIB_SET

# ── AutoPilot configuration ───────────────────────────────────────────────────
AUTOPILOT_MAX_RETRIES   = 3   # max retries per XDS step before fallback
AUTOPILOT_MAX_DELPHI    = 90  # upper limit for DELPHI escalation (degrees)

