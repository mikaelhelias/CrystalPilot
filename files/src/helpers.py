_H5_EXTS = ('.h5', '.hdf5', '.nxs')


def _h5_find_master(file_path):
    """Locate the Eiger/NeXus *_master.h5 file for any HDF5-related path.

    Accepts a master file, a data chunk file (PREFIX_data_000001.h5), an XDS
    template (PREFIX_??????.h5 or the common but wrong PREFIX_data_??????.h5)
    or a glob pattern.  Returns the master path as a string, or None when no
    master can be found (e.g. a single self-contained data file).
    """
    try:
        p = Path(file_path)
    except Exception:
        return None
    name_lo = p.name.lower()
    if 'master' in name_lo and '?' not in name_lo and '*' not in name_lo:
        return str(p) if p.is_file() else None
    parent = p.parent
    if not parent.is_dir():
        return None
    stem = p.stem
    suffix = p.suffix if p.suffix.lower() in _H5_EXTS else '.h5'
    if re.search(r'[?*]', stem):
        base = re.split(r'[?*]', stem, maxsplit=1)[0]   # lyso_1_??????      -> lyso_1_
    elif re.search(r'_\d+$', stem):
        base = re.sub(r'_\d+$', '', stem)         # lyso_1_data_000001 -> lyso_1_data
    else:
        base = stem
    base = base.rstrip('_')
    candidates = []
    for b in (re.sub(r'_data$', '', base, flags=re.IGNORECASE), base):
        if b and b not in candidates:
            candidates.append(b)
    for b in candidates:
        for ext in (suffix, '.h5', '.hdf5'):
            c = parent / (b + '_master' + ext)
            if c.is_file():
                return str(c)
    # Last resort: the directory holds exactly one master whose name matches
    try:
        masters = [m for m in parent.iterdir()
                   if m.is_file() and m.suffix.lower() in _H5_EXTS
                   and 'master' in m.name.lower()]
    except Exception:
        masters = []
    if len(masters) == 1 and (not base or masters[0].name.lower().startswith(base.lower())):
        return str(masters[0])
    return None


def _resolve_h5_template(file_path):
    """Resolve an HDF5 path or XDS template to a real file to open with h5py.

    Preference order:
    1. The Eiger *_master.h5 (holds the geometry and links to every frame,
       so frame counts are for the whole dataset, not a single chunk file)
    2. The path itself, if it is an existing file
    3. The first file matching the wildcard pattern
    """
    p = Path(file_path)
    if p.is_file() and 'master' in p.name.lower():
        return file_path
    master = _h5_find_master(file_path)
    if master:
        return master
    if p.exists():
        return file_path
    name = p.name
    if ('?' not in name and '*' not in name) or not p.parent.is_dir():
        return file_path
    glob_pat = re.sub(r'[?]+', '*', name)
    matches = sorted(p.parent.glob(glob_pat))
    if matches:
        return str(matches[0])
    return file_path


# ═════════════════════════════════════════════════════════════════════════════
#  WHERE PROJECT FILES LIVE  -  the single place that decides it
#
#  project folder   PROJECTS_DIR/<name>      metadata.json and the inputs the
#                                            user edits: XDS.INP, XSCALE.INP,
#                                            XDSCONV.INP
#  XDS output       folder of the last XDS   *.LP *.HKL *.XDS *.cbf and all
#    kind="xds"     run (may be anywhere,    files derived from them: pointless/
#                   e.g. next to the frames)  aimless/ctruncate logs and MTZs,
#                                            XDSCC12.LP, AUTOPILOT_RESULTS.json
#  XSCALE output    folder of the last       XSCALE.LP, XSCALE.HKL
#    kind="xscale"  XSCALE run (project or XSCALE_NNN)
#  XDSCONV output   folder of the last       XDSCONV.LP, F2MTZ.INP, *.mtz
#    kind="xdsconv" XDSCONV run
#
#  The streams that run the programs record their working folder in
#  metadata.json: last_run_folder (XDS), last_xscale_folder, last_xdsconv_folder.
#  An empty value means "the project folder".  Nothing else may guess.
#
#  Rules for every endpoint / post-processing step:
#     read  ->  _pfile(project_dir, "CORRECT.LP")            (kind defaults to xds)
#     write ->  _pout(project_dir, "pointless.log")
#     run   ->  cwd = _project_out_dir(project_dir)
#  Never write  project_dir / "SOMETHING.LP"  by hand.
#  GET /api/projects/<name>/locations shows what these resolve to right now.
# ═════════════════════════════════════════════════════════════════════════════

_RUN_FOLDER_KEY = {"xds": "last_run_folder", "xscale": "last_xscale_folder", "xdsconv": "last_xdsconv_folder"}


def _record_run_folder(project_name, work_dir, kind="xds"):
    """Called by the streams: remember where a program ran ('' = project folder)."""
    project_dir = _pdir(project_name)
    wd = Path(work_dir).resolve()
    val = "" if wd == project_dir else str(wd)
    ProjectManager.update(project_name, {_RUN_FOLDER_KEY.get(kind, "last_run_folder"): val})


def _project_out_dir(project_dir, kind="xds"):
    """Folder holding the project's latest output of the given kind (see above)."""
    project_dir = Path(project_dir)
    try:
        meta = json.loads((project_dir / "metadata.json").read_text(encoding="utf-8"))
        lrf = str(meta.get(_RUN_FOLDER_KEY.get(kind, "last_run_folder")) or "").strip()
        if lrf:
            p = Path(lrf)
            if p.is_dir():
                return p
    except Exception:
        pass
    return project_dir


def _pfile(project_dir, filename, kind="xds"):
    """Path of an output file for READING: the output folder's copy when it
    exists, otherwise the project folder's copy (which may not exist either).
    One stat at most on the output folder - never a directory walk."""
    project_dir = Path(project_dir)
    out = _project_out_dir(project_dir, kind)
    if out != project_dir:
        cand = out / filename
        try:
            if cand.exists():
                return cand
        except OSError:
            pass
    return project_dir / filename


def _pout(project_dir, filename, kind="xds"):
    """Path of a derived file for WRITING: always next to the output it was made from."""
    return _project_out_dir(project_dir, kind) / filename


def _project_locations(project_dir):
    """Diagnostic summary used by GET /api/projects/<name>/locations."""
    project_dir = Path(project_dir)
    info = {
        "project_dir": str(project_dir),
        "xds_output": str(_project_out_dir(project_dir, "xds")),
        "xscale_output": str(_project_out_dir(project_dir, "xscale")),
        "xdsconv_output": str(_project_out_dir(project_dir, "xdsconv")),
        "files": {},
    }
    for fn, kind in (("XDS.INP", None), ("IDXREF.LP", "xds"), ("INTEGRATE.LP", "xds"), ("CORRECT.LP", "xds"),
                     ("CORRECT.LP.prev1", "xds"), ("XDS_ASCII.HKL", "xds"), ("SPOT.XDS", "xds"),
                     ("pointless.log", "xds"), ("aimless.log", "xds"), ("XDSCC12.LP", "xds"),
                     ("XSCALE.INP", None), ("XSCALE.LP", "xscale"), ("XSCALE.HKL", "xscale"),
                     ("XDSCONV.INP", None), ("XDSCONV.LP", "xdsconv")):
        p = project_dir / fn if kind is None else _pfile(project_dir, fn, kind)
        try:
            info["files"][fn] = str(p) if p.exists() else None
        except OSError:
            info["files"][fn] = None
    return info


def _xscale_inputs_from_subfolder(text, relback):
    """XSCALE.INP copied into a run subfolder: relative INPUT_FILE names get the way back.

    Only the file name moves: a leading '*' (the reference data set) stays in
    front, the words after the name (format, resolution) and the line's
    indentation are kept.
    """
    out = []
    for ln in str(text).split('\n'):
        stripped = ln.lstrip()
        if stripped.upper().startswith('INPUT_FILE') and '=' in stripped and not stripped.startswith('!'):
            eq = stripped.index('=')
            indent = ln[:len(ln) - len(stripped)]
            words = stripped[eq + 1:].split()
            if words:
                star = '*' if words[0].startswith('*') else ''
                name = words[0][1:] if star else words[0]
                if name and not (name.startswith('/') or os.path.isabs(name)):
                    words[0] = star + relback + '/' + name
                out.append(indent + stripped[:eq + 1] + ' ' + ' '.join(words))
                continue
        out.append(ln)
    return '\n'.join(out)


# --- Windows paths the user pastes into the interface -------------------------
# Under WSL "D:\data\xtal1" or "\\server\share\xtal1" (Explorer's "Copy as
# path") means nothing to Python, and the folder is only readable when the drive
# is mounted.  WSL mounts the fixed drives by itself - unless [automount] is off
# - but never a network share and never a disk plugged in after the runtime
# started.  Translating the path and mounting the drive on the spot turns a
# pasted Windows path into a working way to reach the frames.
_MOUNT_TRIED = {}          # mount point -> when it was last tried (a dead share costs one timeout)


def _drvfs_mount(source, mount_point):
    r"""Mount a Windows drive letter ("D:") or share ("\\server\share") inside
    WSL.  True when the folder can be read afterwards."""
    if not IS_WSL:
        return False
    if os.path.ismount(mount_point):
        return True
    last = _MOUNT_TRIED.get(mount_point, 0)
    import time as _time
    if last and (_time.time() - last) < 60:
        return False                    # just failed: do not pay the timeout again
    _MOUNT_TRIED[mount_point] = _time.time()
    cmd, opts = [], "noatime"
    if os.geteuid() != 0:
        cmd = ["sudo", "-n"]
        opts += ",uid=%d,gid=%d" % (os.getuid(), os.getgid())
    try:
        os.makedirs(mount_point, exist_ok=True)
    except Exception:
        return False
    ok = False
    try:
        r = subprocess.run(cmd + ["mount", "-t", "drvfs", source, mount_point, "-o", opts],
                           capture_output=True, text=True, timeout=12)
        ok = (r.returncode == 0)
    except Exception:
        ok = False
    if not ok:
        try:
            os.rmdir(mount_point)       # leave no empty folder pretending to be a drive
        except Exception:
            pass
    return ok


def _to_local_path(path):
    """A path as the user may have typed or pasted it, as this program can open it.

    Returns (path, problem).  Outside WSL, and for an ordinary Linux path, the
    path comes back unchanged and problem is empty; problem says in plain words
    why a Windows drive or share could not be reached.
    """
    p = (path or "").strip().strip('"').strip("'")
    if not p or not IS_WSL:
        return path, ""
    m = re.match(r"^([A-Za-z]):([\\/].*)?$", p)
    if m:
        letter = m.group(1).upper()
        rest = (m.group(2) or "").replace("\\", "/").lstrip("/")
        mp = WSL_MOUNT_ROOT + letter.lower()
        if not os.path.ismount(mp) and not _drvfs_mount(letter + ":", mp):
            return path, ("drive " + letter + ": is not available inside Linux - is it still "
                          "connected?  Starting CrystalPilot again mounts the drives that are.")
        return (mp + "/" + rest if rest else mp), ""
    if p.startswith("\\\\") and len(p) > 2:
        parts = [x for x in p[2:].replace("\\", "/").split("/") if x]
        if len(parts) >= 2 and all(re.match(r"^[A-Za-z0-9._$ ()-]+$", x) for x in parts[:2]):
            server, share, rest = parts[0], parts[1], "/".join(parts[2:])
            mp = WSL_MOUNT_ROOT + "unc/" + server + "/" + share
            if not os.path.ismount(mp) and not _drvfs_mount("\\\\" + server + "\\" + share, mp):
                return path, ("the share \\\\" + server + "\\" + share + " could not be reached - "
                              "open it once in Windows Explorer, then try again")
            return (mp + "/" + rest if rest else mp), ""
    return path, ""


def _windows_view(path):
    r"""How a WSL path looks from Windows: 'P:\\sub' when the launcher mapped the
    projects folder to a drive letter (CRYSTALPILOT_DRIVE), else the
    \\wsl.localhost\<distro>\... form.  Empty string outside WSL."""
    if not IS_WSL:
        return ""
    p = str(Path(path).resolve()) if path else ""
    if not p:
        return ""
    drive = os.environ.get("CRYSTALPILOT_DRIVE", "").strip().rstrip("\\")
    try:
        proj = str(PROJECTS_DIR.resolve())
    except Exception:
        proj = str(PROJECTS_DIR)
    if drive and (p == proj or p.startswith(proj.rstrip("/") + "/")):
        rest = p[len(proj):].lstrip("/")
        return drive + "\\" + rest.replace("/", "\\") if rest else drive + "\\"
    unc = WSL_MOUNT_ROOT + "unc/"
    if p.startswith(unc) and len(p.split("/")) > len(unc.split("/")):
        return "\\\\" + p[len(unc):].replace("/", "\\")
    root = WSL_MOUNT_ROOT                      # /mnt/ unless wsl.conf moved it
    n = len(root)
    if p.startswith(root) and len(p) > n and p[n].isalpha() and (len(p) == n + 1 or p[n + 1] == "/"):
        rest = p[n + 1:]
        return p[n].upper() + ":" + (rest.replace("/", "\\") if rest else "\\")
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    return ("\\\\wsl.localhost\\" + distro + p.replace("/", "\\")) if distro else ""


def _open_in_file_manager(path, dry_run=False):
    """Open a folder in the desktop file manager (Explorer through WSL interop,
    xdg-open on Linux, Finder on macOS, Explorer on Windows).  Returns
    (ok, description)."""
    import platform as _plat
    p = Path(path)
    if p.is_file():
        p = p.parent
    if not p.is_dir():
        return False, "Folder does not exist: " + str(path)
    target = str(p)
    if IS_WSL:
        win = _windows_view(target)
        if not win:
            try:
                win = subprocess.run(["wslpath", "-w", target], capture_output=True, text=True, timeout=10).stdout.strip()
            except Exception:
                win = ""
        cmd = ["explorer.exe", win or target]
        shown = win or target
    elif _plat.system() == "Windows":
        cmd = ["explorer", target]; shown = target
    elif _plat.system() == "Darwin":
        cmd = ["open", target]; shown = target
    else:
        cmd = ["xdg-open", target]; shown = target
    if dry_run:
        return True, " ".join(cmd)
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, shown
    except Exception as e:
        return False, str(e)


def _is_xds_reflection_file(path):
    """True for XDS-format reflection files (XDS_ASCII.HKL, XSCALE output such
    as merged.ahkl, INTEGRATE.HKL): by extension, else by the !FORMAT= header.
    Everything else (typically .mtz) is not."""
    p = Path(str(path))
    ext = p.suffix.upper()
    if ext in ('.HKL', '.AHKL'):
        return True
    if ext in ('.MTZ', '.CIF', '.SCA'):
        return False
    try:
        with open(p, 'rb') as fh:
            head = fh.read(512).decode('ascii', 'replace').upper()
        return '!FORMAT=XDS_ASCII' in head or '!OUTPUT_FILE=' in head
    except OSError:
        return False


def _read_text_lenient(path):
    """Read a program output or input file as text.  XDS, XSCALE and CCP4
    logs are not guaranteed UTF-8 (Fortran writes whatever bytes it gets), so
    undecodable bytes become U+FFFD instead of failing the whole request."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _url_project_name(segment):
    """Decode a URL path segment exactly once, then validate it as a name."""
    return ProjectManager._safe_name(urllib.parse.unquote(segment, errors="strict"))


def _pdir(name):
    """Project folder for a decoded name (JSON/query values are already decoded)."""
    return (PROJECTS_DIR / ProjectManager._safe_name(str(name or ""))).resolve()


def _parse_xdsinp_params(content):
    """Parse XDS.INP text content and return a dict of {PARAM: value} for active lines.

    Handles XDS.INP's very loose formatting:
    - Multiple key=value pairs per line
    - KEY= VALUE or KEY=VALUE or KEY =VALUE
    - Inline ! comments
    - Continuation values (e.g. UNIT_CELL_CONSTANTS= 100 100 100 90 90 90)
    - Tabs and mixed whitespace
    """
    result = {}
    for line in content.split('\n'):
        stripped = line.strip()
        # Skip comment lines
        if stripped.startswith('!'):
            continue
        # Strip inline comments
        stripped = stripped.split('!')[0].strip()
        if not stripped:
            continue
        # Split into whitespace-delimited tokens
        parts = stripped.split()
        i = 0
        while i < len(parts):
            eq = parts[i].find('=')
            if eq > 0:
                # Standard case: KEY=VALUE or KEY=
                key = parts[i][:eq].upper()
                val = parts[i][eq+1:]
                # Collect continuation tokens (not KEY=VAL themselves)
                j = i + 1
                while j < len(parts):
                    if '=' in parts[j] and parts[j].index('=') > 0:
                        break
                    if parts[j].startswith('='):
                        break
                    # Look ahead: if next token starts with '=' then current
                    # token is a KEY beginning a new 'KEY = VALUE' pair — stop.
                    if j + 1 < len(parts) and parts[j + 1].startswith('='):
                        break
                    val += ' ' + parts[j]
                    j += 1
                result[key] = val.strip()
                i = j
            elif eq == 0:
                # Bare "=VALUE" — skip (consumed by lookahead below)
                i += 1
            else:
                # No '=' in this token — look ahead for 'KEY = VALUE' pattern
                # where '=' is a separate token or '=VALUE'
                if i + 1 < len(parts) and parts[i + 1].startswith('='):
                    key = parts[i].upper()
                    # The '=' may be alone or attached to the value: '=' or '=VALUE'
                    val = parts[i + 1][1:]  # everything after '='
                    j = i + 2
                    while j < len(parts):
                        if '=' in parts[j] and parts[j].index('=') > 0:
                            break
                        if parts[j].startswith('='):
                            break
                        if j + 1 < len(parts) and parts[j + 1].startswith('='):
                            break
                        val += ' ' + parts[j]
                        j += 1
                    result[key] = val.strip()
                    i = j
                else:
                    i += 1
    return result



# ═════════════════════════════════════════════════════════════════════════════
#  EXPORTING A PROJECT
#
#  One zip a colleague can open: what was asked of XDS, what XDS answered, the
#  reflection files, the figures and the reports - and a README naming the
#  program, the project and the day.
#
#  Left out on purpose: frames (*.h5, *.cbf images), the correction images XDS
#  writes for every run (*-CORRECTIONS.cbf, tens of MB and regenerated by the
#  next run), SPOT.XDS and the rotated .prev/.previous_attempt logs.  A reader
#  needs the result, not the scratch space.
# ═════════════════════════════════════════════════════════════════════════════
EXPORT_ALWAYS = (
    "metadata.json", "*.INP", "*.LP", "*.log", "*.json", "*.cif",
    "GXPARM.XDS", "XPARM.XDS", "*_vs_Resolution.png", "*_vs_Resolution.pdf",
    "*_Resolution_Statistics.png", "*_Resolution_Statistics.pdf", "*.csv", "*.txt",
)
EXPORT_REFLECTIONS = ("*.HKL", "*.ahkl", "*.mtz", "*.hkl", "*.sca", "*.sf")
EXPORT_NEVER = (
    "*-CORRECTIONS.cbf", "*.h5", "*.cbf", "*.img", "*.tif", "*.tiff", "*.osc",
    "SPOT.XDS", "*.prev", "*.prev1", "*.prev2", "*.prev3", "*.prev4",
    "*.previous_attempt", "*.zip", "*.part", "__pycache__",
)
EXPORT_MAX_FILE = 600 * 1024 * 1024      # one file this big is a mistake, not a result


def _export_wanted(name, reflections):
    """Does this file belong in the export?"""
    import fnmatch
    for pattern in EXPORT_NEVER:
        if fnmatch.fnmatch(name, pattern):
            return False
    patterns = list(EXPORT_ALWAYS) + (list(EXPORT_REFLECTIONS) if reflections else [])
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def _export_stem(project_name):
    """The project name made safe for a file name."""
    return "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(project_name)).strip("_") or "project"


def _export_name(project_name):
    """<project>_<date>.zip - what an export is called."""
    return "%s_%s.zip" % (_export_stem(project_name), datetime.now().strftime("%Y-%m-%d"))


def _export_matches(project_name, name):
    """Is `name` an export of this project (any date)? Guards the download route.

    A path is never built from a name that does not match: no separators, no
    other project's export, nothing but <project>_YYYY-MM-DD.zip.
    """
    # Path(name).name strips any directory part, so a name that survives this
    # comparison carries none - no separator of either platform, no "..".
    if not name or name != Path(name).name or name.startswith("."):
        return False
    prefix = _export_stem(project_name) + "_"
    if not name.startswith(prefix) or not name.endswith(".zip"):
        return False
    date = name[len(prefix):-4]          # YYYY-MM-DD and nothing else
    return (len(date) == 10 and date[4] == "-" and date[7] == "-"
            and date.replace("-", "").isdigit())


def export_project(project_name, reflections=True):
    """Write one zip holding the project's inputs, logs, data and figures.

    Returns {"name", "path", "size", "entries", "skipped", "folders"}.
    """
    import zipfile
    project_dir = _pdir(project_name)
    if not project_dir.is_dir():
        raise FileNotFoundError("Project not found")
    # every folder this project has written to: the project itself and the
    # output folders of the three programs (they may be elsewhere entirely)
    folders, seen = [], set()
    for kind in ("xds", "xscale", "xdsconv"):
        for folder in (project_dir, _project_out_dir(project_dir, kind)):
            key = os.path.normcase(str(Path(folder).resolve()))
            if key not in seen and Path(folder).is_dir():
                seen.add(key)
                folders.append(Path(folder))

    target = project_dir / _export_name(project_name)
    entries, skipped = [], []
    tmp = target.with_suffix(".zip.part")
    with zipfile.ZipFile(str(tmp), "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        for folder in folders:
            # one level down as well: XSCALE_001, run sub-folders, docs
            paths = list(folder.glob("*")) + [p for sub in folder.glob("*") if sub.is_dir() for p in sub.glob("*")]
            for path in paths:
                if not path.is_file():
                    continue
                if not _export_wanted(path.name, reflections):
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size > EXPORT_MAX_FILE:
                    skipped.append({"name": path.name, "size": size, "reason": "larger than the export limit"})
                    continue
                # inside the zip: <project>/<folder>/<file>, so two runs of the
                # same step from different folders cannot collide
                rel = path.relative_to(folder)
                label = folder.name if folder != project_dir else ""
                arc = Path(str(project_name).strip() or "project") / label / rel
                name = str(arc).replace("\\", "/")
                if name in {e["name"] for e in entries}:
                    continue
                try:
                    zf.write(str(path), name)
                except OSError as exc:
                    skipped.append({"name": path.name, "size": size, "reason": str(exc)})
                    continue
                entries.append({"name": name, "size": size})
        readme = [
            "CrystalPilot " + VERSION + " - export of project '" + str(project_name) + "'",
            "Written " + datetime.now().strftime("%Y-%m-%d %H:%M"),
            "",
            "Folders this project wrote to:",
        ]
        readme += ["   " + str(f) for f in folders]
        readme += [
            "",
            "In this archive: the XDS/XSCALE/XDSCONV input files, every program log,",
            "the parsed reports and figures, the refined geometry"
            + (", and the reflection files." if reflections else " (reflection files were left out)."),
            "",
            "Not in this archive: the diffraction frames, the correction images XDS",
            "regenerates for each run (*-CORRECTIONS.cbf), SPOT.XDS, and the rotated",
            "copies of older logs (.prev1 ... .prev4).",
            "",
            "%d files, %s" % (len(entries), _human_size(sum(e["size"] for e in entries))),
        ]
        if skipped:
            readme += ["", "Left out:"] + ["   %s (%s) - %s" % (s["name"], _human_size(s["size"]), s["reason"]) for s in skipped]
        zf.writestr(str(Path(str(project_name).strip() or "project") / "README.txt").replace("\\", "/"),
                    "\n".join(readme) + "\n")
    os.replace(str(tmp), str(target))
    return {"name": target.name, "path": str(target), "size": target.stat().st_size,
            "entries": entries, "skipped": skipped, "folders": [str(f) for f in folders]}


def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%.0f %s" if unit in ("B", "KB") else "%.1f %s") % (n, unit)
        n /= 1024.0
    return str(n)

# ═════════════════════════════════════════════════════════════════════════════
#  PROBLEM REPORTS
#
#  What the author needs to understand someone else's problem without a
#  back-and-forth: what they did and expected, which version on which system,
#  what the Environment screen found, what the program printed last, what went
#  wrong in the page - and, only if the user ticks it, the project's XDS.INP
#  and logs, because that is their data.
#
#  Written to <projects>/reports/ so the user can open it before sending it.
#  User names are taken out of every path and the API token out of every line:
#  the report is meant to be mailed to someone else.
# ═════════════════════════════════════════════════════════════════════════════
REPORT_LOG_LINES = 400           # the end of the log is where the problem is
REPORT_MAIL_LINK = 1900          # characters of the ENCODED mailto link; Windows cuts them near 2000


# The path segment after /home/, /Users/ or \Users\ IS a user name - the full
# one, a Windows 8.3 short form (JOHNDO~1), or somebody else's - so it is
# replaced by its position in the path, not by looking for a known name.
# [\\]+ also covers JSON text, where each backslash is written twice; matching
# only the names this account goes by missed exactly that case.
_REPORT_USER_SEGMENT = re.compile(r"(/home/|/Users/|[\\]+Users[\\]+)([^\\/\r\n\"'<>|]+)")


def _report_redact(text):
    """Take user names out of paths and the API token out of text."""
    text = str(text)
    try:
        if API_TOKEN:
            text = text.replace(API_TOKEN, "<token>")
    except Exception:
        pass
    return _REPORT_USER_SEGMENT.sub(lambda mt: mt.group(1) + "<user>", text)


def _report_redact_data(value):
    """The same, for every string inside a structure - before it becomes JSON."""
    if isinstance(value, dict):
        return {k: _report_redact_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_report_redact_data(v) for v in value]
    if isinstance(value, str):
        return _report_redact(value)
    return value


def _report_log_tail():
    """The last lines of the log file, or a note saying why there are none."""
    try:
        path = LOG_PATH
    except NameError:
        path = None
    if not path or not Path(path).is_file():
        return "(no log file: logging is off or nothing has been written yet)"
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return "(the log file could not be read: %s)" % exc
    return "\n".join(lines[-REPORT_LOG_LINES:])


def _report_environment_summary(env):
    """One line per check: what the Environment screen shows, for a mail body."""
    rows = []
    platform = env.get("platform") or {}
    rows.append("CrystalPilot %s on %s %s%s, Python %s" % (
        env.get("version", "?"), platform.get("system", "?"), platform.get("release", ""),
        " (WSL)" if platform.get("is_wsl") else "", platform.get("python", "?")))
    for check in env.get("checks") or []:
        rows.append("%-8s %s" % (str(check.get("status", "?")).upper(), check.get("title", "")))
    return "\n".join(rows)


def build_problem_report(description, project="", include_project=False, page_errors=None, page_url=""):
    """Write the report zip and the short text for an e-mail.

    Returns {"name", "path", "size", "files", "mail_body", "mail_subject", "report_email"}.
    """
    import json as _json
    import zipfile
    description = str(description or "").strip()
    if not description:
        raise ValueError("Describe what happened first - that is the part nobody else can write.")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    env = _environment_report()
    page_errors = [str(e)[:2000] for e in (page_errors or [])][-50:]

    folder = PROJECTS_DIR / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("crystalpilot-report_%s.zip" % stamp)

    summary = [
        "CrystalPilot problem report",
        "Written " + datetime.now().strftime("%Y-%m-%d %H:%M"),
        "",
        "WHAT HAPPENED",
        description,
        "",
        "SYSTEM",
        _report_environment_summary(env),
        "",
        "PROJECT",
        (str(project) + ("  (its XDS.INP and logs are attached)" if include_project else "  (project files not attached)"))
        if project else "(none open)",
        "",
        "ERRORS IN THE PAGE (most recent last)",
        "\n".join(page_errors[-15:]) if page_errors else "(none recorded)",
    ]
    files = []
    with zipfile.ZipFile(str(target), "w", zipfile.ZIP_DEFLATED) as zf:
        def put(name, text):
            data = _report_redact(text)
            zf.writestr(name, data)
            files.append({"name": name, "size": len(data.encode("utf-8"))})
        put("REPORT.txt", "\n".join(summary) + "\n")
        # redacted as data, before JSON doubles every backslash in a Windows path
        put("environment.json", _json.dumps(_report_redact_data(env), indent=2, default=str))
        put("crystalpilot.log (last %d lines).txt" % REPORT_LOG_LINES, _report_log_tail())
        if page_errors:
            put("page-errors.txt", "\n\n".join(page_errors))
        if include_project and project:
            project_dir = _pdir(project)
            out_dir = _project_out_dir(project_dir)
            for folder_ in [project_dir] + ([out_dir] if out_dir != project_dir else []):
                for pattern in ("XDS.INP", "XSCALE.INP", "XDSCONV.INP", "*.LP"):
                    for path in sorted(Path(folder_).glob(pattern)):
                        if path.is_file() and path.stat().st_size < 20 * 1024 * 1024:
                            try:
                                put("project/" + path.name, path.read_text(encoding="utf-8", errors="replace"))
                            except OSError:
                                pass

    # the mail itself stays short: a mail program opens it from a URL, and the
    # zip carries everything else
    body_lines = [
        description,
        "",
        "-- ",
        _report_environment_summary(env),
    ]
    if page_errors:
        body_lines += ["", "Last error in the page:", page_errors[-1][:400]]
    body_lines += ["", "The full report is attached: " + target.name]
    body = _report_redact("\n".join(body_lines))
    first_line = description.splitlines()[0] if description else "problem"
    subject = _report_redact("CrystalPilot %s: %s" % (VERSION, first_line[:70]))
    # The limit that matters is the ENCODED mail link: every space and line
    # break becomes three characters, so 1500 characters of text made a
    # 2086-character link, past what Windows hands to a mail program.
    note = "\n[... shortened - the attached zip has all of it]"

    def link_length(text):
        return len("mailto:%s?subject=%s&body=%s" % (REPORT_EMAIL, urllib.parse.quote(subject, safe=""),
                                                     urllib.parse.quote(text, safe="")))
    if link_length(body) > REPORT_MAIL_LINK:
        low, high = 0, len(body)
        while low < high:                    # the longest start of the body that still fits
            mid = (low + high + 1) // 2
            if link_length(body[:mid].rstrip() + note) <= REPORT_MAIL_LINK:
                low = mid
            else:
                high = mid - 1
        body = body[:low].rstrip() + note
    return {"name": target.name, "path": str(target), "size": target.stat().st_size, "files": files,
            "mail_subject": subject, "mail_body": body, "report_email": REPORT_EMAIL}


def _report_matches(name):
    """A download may only name a report this program wrote."""
    if not name or name != Path(name).name or not name.startswith("crystalpilot-report_") or not name.endswith(".zip"):
        return False
    stamp = name[len("crystalpilot-report_"):-4]            # YYYY-MM-DD_HHMMSS
    return (len(stamp) == 17 and stamp[4] == "-" and stamp[7] == "-" and stamp[10] == "_"
            and stamp.replace("-", "").replace("_", "").isdigit())



def _check_h5_frames(xds_inp_path):
    """Check that XDS can really reach the HDF5 frames named in XDS.INP.

    XDS replaces the ?????? in NAME_TEMPLATE_OF_DATA_FRAMES with 'master' and
    hands that name to the LIB= plugin (dectris-neggia).  The plugin follows
    the external links in /entry/data; a relative link is looked up next to
    the master file and nowhere else (no working directory, no search path).
    A data file that is missing there fails with
        NEGGIA ERROR: OPENING FILE RETURNED ERROR CODE: 2
    inside the plugin, and XDS then reports "could not open ...
    dectris-neggia.so" — which blames the library instead of the data.
    Say what is really wrong before XDS starts.

    Returns (fatal, lines).  lines is empty when nothing could be checked or
    everything is in place; fatal means XDS cannot read the images at all.
    """
    lines = []
    try:
        content = Path(xds_inp_path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False, []

    template, lib_paths = '', []
    for raw in content.splitlines():
        ls = raw.strip()
        if not ls or ls.startswith('!'):
            continue
        m = re.match(r'NAME_TEMPLATE_OF_DATA_FRAMES\s*=\s*(\S+)', ls, re.I)
        if m:
            template = m.group(1)
        m = re.match(r'LIB\s*=\s*(\S+)', ls, re.I)
        if m:
            lib_paths.append(m.group(1))

    if not template or not template.lower().endswith(('.h5', '.hdf5')):
        return False, []                      # not HDF5 data — nothing to check

    # XDS does not accept a single file name here.  It replaces the frame-number
    # wildcards with 'master' itself and refuses anything else outright:
    #     !!! ERROR !!! INVALID "NAME_TEMPLATE_OF_DATA_FRAMES="
    if '?' not in template:
        suggest = re.sub(r'(_master|_data_\d+|_\d+)(\.[^.]+)$', r'_??????\2', template, flags=re.I)
        lines.append("NAME_TEMPLATE_OF_DATA_FRAMES names one file. XDS needs the frame-number "
                     "wildcards there and puts 'master' in their place itself"
                     + (" — use " + suggest if suggest != template else "") + ".")
        return True, lines

    work_dir = Path(xds_inp_path).parent
    # XDS builds the master file name from the template itself
    master = Path(re.sub(r'\?+', 'master', template))
    if not master.is_absolute():
        master = work_dir / master

    if not lib_paths:
        lines.append("XDS.INP has no LIB= line. HDF5/Eiger data can only be read "
                     "through dectris-neggia.so — set the HDF5 library path in "
                     "Settings, or add LIB= to XDS.INP.")
        return True, lines
    if len(lib_paths) > 1:
        lines.append("XDS.INP has %d LIB= lines. XDS opens the plugin once per "
                     "line and the second one fails ('handle' not null) — keep one."
                     % len(lib_paths))
    if not Path(lib_paths[0]).exists():
        lines.append("The HDF5 reader library is not there: " + lib_paths[0])
        return True, lines

    if not master.exists():
        lines.append("XDS will open " + str(master) + ", which does not exist.")
        if '_data_' in master.name.lower():
            lines.append("The template contains _data_ — XDS builds the master file name from it, "
                         "so it has to be PREFIX_??????.h5 without _data.")
        parent = master.parent
        if not parent.is_dir():
            lines.append("The folder " + str(parent) + " is not there either "
                         "(a network drive that is not mounted looks like this).")
        else:
            near = sorted(p.name for p in parent.glob('*master*.h5'))
            if near:
                lines.append("The folder does contain: " + ", ".join(near[:4]))
        return True, lines

    try:
        import h5py
    except Exception:
        return False, []                      # cannot check without h5py
    # hdf5plugin only matters for reading compressed frames, not for the links

    missing, present, per_file = [], 0, 0
    try:
        with h5py.File(str(master), 'r') as f:
            if 'entry/data' not in f:
                return False, []              # not an Eiger master — leave it to XDS
            group = f['entry/data']
            names = {p.name.lower(): p.name for p in master.parent.iterdir()}
            for key in sorted(group):
                link = group.get(key, getlink=True)
                target = getattr(link, 'filename', None)
                if target is None:
                    present += 1              # frames live inside the master
                    continue
                path = Path(target) if target.startswith('/') else master.parent / target
                if path.exists():
                    present += 1
                    if not per_file:
                        try:
                            per_file = int(group[key].shape[0])
                        except Exception:
                            per_file = 0
                else:
                    missing.append((key, target))
    except Exception:
        return False, []                      # unreadable master — XDS will say so

    if not missing:
        return False, []

    # Which chunk files does this run actually need?  neggia picks the file by
    # (frame - 1) // frames-per-file + 1, so a dataset processed only in part
    # can be complete for the frames in DATA_RANGE.
    needed = None
    if per_file:
        m = re.search(r'^\s*DATA_RANGE\s*=\s*(\d+)\s+(\d+)', content, re.I | re.M)
        if m:
            first, last = int(m.group(1)), int(m.group(2))
            needed = set(range((first - 1) // per_file + 1,
                               (last - 1) // per_file + 2))

    def _index(key):
        digits = re.search(r'(\d+)$', key)
        return int(digits.group(1)) if digits else None

    blocking = [(k, t) for k, t in missing
                if needed is None or _index(k) is None or _index(k) in needed]
    # Only neggia is known to look next to the master and nowhere else; with
    # another plugin (durin, the HDF5 library itself) say it but let it run.
    neggia = 'neggia' in Path(lib_paths[0]).name.lower()
    fatal = neggia and ((present == 0) or bool(blocking and needed is not None))

    lines.append("%d of the %d data files listed in %s %s missing from %s:"
                 % (len(missing), len(missing) + present, master.name,
                    "is" if len(missing) == 1 else "are", master.parent))
    for key, target in missing[:6]:
        hint = ""
        base = target.rsplit('/', 1)[-1]
        if base.lower() in names and names[base.lower()] != base:
            hint = "   (the folder has '%s' — same name, different capitals; "\
                   "Linux keeps them apart)" % names[base.lower()]
        elif target.startswith('/'):
            hint = "   (the master stores this as an absolute path from the "\
                   "beamline; the plugin does not look next to the master then)"
        elif '/' in target:
            hint = "   (the master points into a sub-folder)"
        lines.append("    " + target + hint)
    if len(missing) > 6:
        lines.append("    ... and %d more" % (len(missing) - 6))
    if present:
        lines.append("%d data file(s) are in place." % present)
    if present and needed is not None and not blocking:
        lines.append("The frames in DATA_RANGE are covered, so XDS can run — "
                     "but a wider range will fail.")
    else:
        lines.append("Copy the missing files next to the master file, or point "
                     "NAME_TEMPLATE_OF_DATA_FRAMES at the folder that has the "
                     "whole dataset.")
    return fatal, lines
