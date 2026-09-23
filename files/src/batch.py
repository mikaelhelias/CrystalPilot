
# ═════════════════════════════════════════════════════════════════════════════
#  AUTOPILOT WIZARD - the engine behind the AutoPilot tab
#
#  One data set or many, one set of choices, no babysitting.
#
#  1. DISCOVER   the folders the user drops are searched for data sets: Eiger
#                master files and numbered frame series.  Each becomes a
#                project of its own.
#  1b. XDS.INP   the beamline's XDS.INP is searched for near the images and
#                imported when it matches them; otherwise XDS.INP is written
#                from the image header.
#  2. STRATEGY   the decisions a user makes by hand for one data set are made
#                once, for all of them: what to do when indexing fails, whether
#                to re-integrate with refined geometry and whether to keep that
#                result only when it is better, a known space group and cell,
#                ice rings, ΔCC½, resolution limits.  The strategy drives
#                AutoPilot (stream_autopilot), so a batch processes a data set
#                exactly as the AutoPilot tab would with the same choices.
#  3. QUEUE      one data set at a time in a background thread - XDS already
#                uses every core - with each data set's log on disk, so the
#                page can be closed, reopened, and pick the batch up again.
#  4. COMPARE    one table: space group, cell, cut-off, completeness, R-meas,
#                I/σ, CC½, ISa - read from each project's own CORRECT.LP, so it
#                is what the LP viewer would show.
#  5. MERGE      the data sets ticked in the table get an XSCALE.INP of their
#                own: common space group, a reference data set for the
#                indexing, each data set at its own cut-off, the inconsistent
#                ones left out with the reason; then XSCALE runs on it.
#
#  Batches live in <projects>/batches/<id>/ (state, logs, merges).  Nothing
#  here decides crystallography that AutoPilot does not already decide: it
#  only fixes, up front, the choices AutoPilot would otherwise take by itself.
# ═════════════════════════════════════════════════════════════════════════════

BATCH_IMAGE_EXTS = (".cbf", ".img", ".mccd", ".osc", ".tif", ".tiff", ".mar3450", ".mar2300", ".sfrm")
BATCH_MIN_FRAMES = 5            # fewer numbered files is a few test shots, not a data set
BATCH_SCAN_LIMIT = 200000       # directory entries: a whole network share must not hang the page
BATCH_CELL_TOLERANCE = 0.03     # relative, per axis, for merging
BATCH_ANGLE_TOLERANCE = 1.5     # degrees

# Every choice a strategy makes: key, the wizard step it belongs to, what the
# user reads, the choices, the default (what AutoPilot does today), and a
# sentence on consequences.
STRATEGY_OPTIONS = [
    {"key": "criterion", "step": "cutoffs", "label": "Resolution cut-off", "default": "isig2",
     "choices": [["isig2", "I/σ ≈ 2"], ["cc_half_50", "CC½ ≈ 50%"],
                 ["cc_half_sig", "CC½ significant"], ["r_obs_55", "R-obs ≈ 55%"]],
     "help": "Where each data set is cut, by the same rule as the cut-off buttons."},
    {"key": "friedel", "step": "cutoffs", "label": "Friedel's law", "default": "TRUE", "input": "checkbox", "on": "TRUE", "off": "FALSE",
     "choices": [["TRUE", "true - merge anomalous pairs"], ["FALSE", "false - keep anomalous pairs apart"]],
     "help": "Ticked: FRIEDEL'S_LAW= TRUE, anomalous pairs merged (native data). Untick for SAD/MAD: FALSE keeps the anomalous signal. Used by XSCALE and XDSCONV."},
    {"key": "res_low", "step": "cutoffs", "label": "Low-resolution limit (Å)", "default": "", "input": "number",
     "help": "Optional: INCLUDE_RESOLUTION_RANGE for every data set. Empty = XDS decides."},
    {"key": "res_high", "step": "cutoffs", "label": "High-resolution limit (Å)", "default": "", "input": "number",
     "help": "Optional; the cut-off above still applies inside it."},
    {"key": "optimize", "step": "reprocessing", "label": "Re-integrate with refined geometry (GXPARM → XPARM)", "default": "always",
     "choices": [["never", "never"], ["always", "always, and keep it"], ["if_better", "try it, keep it only if better"]],
     "help": "A second DEFPIX-INTEGRATE-CORRECT with the geometry CORRECT refined. ‘Only if better’ restores the first integration when the re-integration loses."},
    {"key": "optimize_metric", "step": "reprocessing", "label": "‘Better’ means", "default": "isa", "depends": {"optimize": "if_better"},
     "choices": [["isa", "higher ISa"], ["resolution", "a better resolution cut-off"], ["cc_half", "higher overall CC½"]],
     "help": "What the re-integration is judged on."},
    {"key": "dcc_half", "step": "reprocessing", "label": "ΔCC½ frame rejection (XDSCC12)", "default": "on", "input": "checkbox",
     "choices": [["on", "on"], ["off", "off"]],
     "help": "Excludes frames that lower CC½. It runs as part of the re-integration, so it does nothing when re-integration is ‘never’."},
    {"key": "exclude_ice", "step": "reprocessing", "label": "Ice rings", "default": "yes",
     "choices": [["yes", "exclude them when CORRECT shows them"], ["no", "leave them in"]],
     "help": "Detected rings are written as EXCLUDE_RESOLUTION_RANGE and CORRECT runs again."},
    {"key": "sg_mode", "step": "indexing", "label": "Space group and cell", "default": "auto",
     "choices": [["auto", "determine for each data set"], ["fixed", "use one space group and cell for all"]],
     "help": "One crystal form in a campaign: fixing it keeps every data set in the same setting, which merging needs."},
    {"key": "space_group", "step": "indexing", "label": "Space group number", "default": "", "input": "text", "depends": {"sg_mode": "fixed"},
     "help": "SPACE_GROUP_NUMBER, e.g. 19 for P2₁2₁2₁."},
    {"key": "unit_cell", "step": "indexing", "label": "Unit cell", "default": "", "input": "text", "depends": {"sg_mode": "fixed"},
     "help": "a b c α β γ, e.g. 78.1 78.1 37.2 90 90 90. Required: XDS takes a space group only together with its cell."},
    {"key": "sg_route", "step": "indexing", "label": "Space group in an imported XDS.INP", "default": "without_first",
     "depends": {"sg_mode": "auto"},
     "choices": [["without_first", "process without it; if that fails, with it; if that fails too, auto-index"],
                 ["use", "use it"], ["ignore", "ignore it"]],
     "help": "Only for data sets whose imported XDS.INP has a space group. Data sets with a generated XDS.INP have none."},
    {"key": "autoindex_tier", "step": "indexing", "label": "If indexing fails", "default": "medium",
     "choices": [["off", "give up on that data set"], ["quick", "auto-index, quick"],
                 ["medium", "auto-index, medium"], ["full", "auto-index, full search"]],
     "help": "After AutoPilot's own IDXREF fixes. Deeper tiers try more spot ranges and thresholds and take longer."},
]

STRATEGY_PRESETS = {
    "AutoPilot defaults": {},
    "Quick screening": {"autoindex_tier": "quick", "optimize": "never", "dcc_half": "off"},
    "Best data": {"autoindex_tier": "full", "optimize": "if_better", "optimize_metric": "isa", "dcc_half": "on"},
}


def normalize_strategy(strategy):
    """A complete, valid strategy: unknown values fall back to the default."""
    strategy = dict(strategy or {})
    out = {}
    for opt in STRATEGY_OPTIONS:
        value = strategy.get(opt["key"], opt["default"])
        value = "" if value is None else str(value).strip()
        if opt.get("choices") and value not in [c[0] for c in opt["choices"]]:
            value = opt["default"]
        out[opt["key"]] = value
    if out["sg_mode"] == "fixed":
        if not out["space_group"].isdigit() or not (1 <= int(out["space_group"]) <= 230):
            raise ValueError("A fixed space group needs a SPACE_GROUP_NUMBER between 1 and 230.")
        cell = out["unit_cell"].replace(",", " ").split()
        if not cell:
            raise ValueError("A fixed space group needs its unit cell too: XDS takes SPACE_GROUP_NUMBER only together "
                             "with UNIT_CELL_CONSTANTS (a b c alpha beta gamma).")
        if cell:
            try:
                values = [float(v) for v in cell]
            except ValueError:
                raise ValueError("The unit cell must be six numbers: a b c alpha beta gamma.")
            if len(values) != 6 or min(values) <= 0:
                raise ValueError("The unit cell must be six positive numbers: a b c alpha beta gamma.")
            out["unit_cell"] = " ".join("%g" % v for v in values)
    for key in ("res_low", "res_high"):
        if out[key]:
            try:
                if float(out[key]) <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError("Resolution limits must be positive numbers in Å.")
    return out


def strategy_autopilot_kwargs(strategy):
    """The stream_autopilot arguments a strategy stands for."""
    s = normalize_strategy(strategy)
    kwargs = {
        "criterion": s["criterion"],
        "friedel": s["friedel"],
        "autoindex_tier": s["autoindex_tier"],
        "optimize": {"never": False, "always": True, "if_better": "if_better"}[s["optimize"]],
        "optimize_metric": s["optimize_metric"],
        "dcc_half": s["dcc_half"] == "on",
        "exclude_ice": s["exclude_ice"] == "yes",
    }
    if s["sg_mode"] == "fixed":
        kwargs["space_group"] = s["space_group"]
        kwargs["unit_cell"] = s["unit_cell"] or None
    if s["res_low"] or s["res_high"]:
        # 999 A: no low-resolution cut unless one is given (50 A drops the lowest shells of cells over 50 A)
        kwargs["resolution_range"] = (float(s["res_low"] or 999), float(s["res_high"] or 0.8))
    return kwargs


# ── 1. discovering data sets ─────────────────────────────────────────────────
def discover_datasets(folder, max_depth=3):
    """Data sets under `folder`: Eiger masters and numbered frame series.

    Name-based only - no headers are read - so a folder on a network share is
    listed in seconds.  XDS.INP is generated from the headers when the data
    set is processed.
    """
    import re as _re
    root = Path(str(folder)).expanduser()
    if not root.is_dir():
        raise FileNotFoundError("Not a folder: " + str(folder))
    numbered = _re.compile(r"^(.*?)(\d{3,})(\.[A-Za-z0-9]+)$")
    found, seen_entries = [], 0
    base_depth = len(root.resolve().parts)
    for dirpath, dirnames, filenames in os.walk(str(root)):
        here = Path(dirpath)
        depth = len(here.resolve().parts) - base_depth
        # never descend into CrystalPilot's own output or hidden folders
        dirnames[:] = [d for d in sorted(dirnames)
                       if not d.startswith(".") and d not in ("batches", "reports", "logs", "__pycache__")
                       and depth < max_depth]
        seen_entries += len(filenames) + len(dirnames)
        if seen_entries > BATCH_SCAN_LIMIT:
            break
        for name in sorted(filenames):
            low = name.lower()
            if low.endswith("_master.h5") or low.endswith("_master.hdf5"):
                label = name[: name.lower().rindex("_master")]
                found.append({"kind": "eiger", "template": str(here / name), "label": label,
                              "folder": str(here), "frames": None})
        series = {}
        for name in filenames:
            m = numbered.match(name)
            if not m or m.group(3).lower() not in BATCH_IMAGE_EXTS:
                continue
            key = (m.group(1), len(m.group(2)), m.group(3))
            entry = series.setdefault(key, [0, None, None])
            number = int(m.group(2))
            entry[0] += 1
            entry[1] = number if entry[1] is None else min(entry[1], number)
            entry[2] = number if entry[2] is None else max(entry[2], number)
        for (prefix, width, ext), (count, first, last) in sorted(series.items()):
            if count < BATCH_MIN_FRAMES:
                continue
            found.append({"kind": "series", "template": str(here / (prefix + "?" * width + ext)),
                          "label": prefix.rstrip("_-. ") or here.name, "folder": str(here),
                          "frames": count, "first": first, "last": last})
    return found


def _batch_project_name(label, taken):
    """A project name from a data set label: safe characters, unique."""
    base = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in str(label)).strip("._") or "dataset"
    name, n = base, 2
    while name in taken or (PROJECTS_DIR / name).exists():
        name = "%s_%d" % (base, n)
        n += 1
    taken.add(name)
    return name


def batch_local_path(path):
    """A path typed or dropped in the browser, as this server sees it.

    Inside WSL a Windows path (P:\\data\\x, file:///P:/data/x) becomes
    /mnt/p/data/x - or the projects folder, when P: is the drive the launcher
    mapped it to.
    """
    import urllib.parse as _up
    p = str(path or "").strip().strip('"').strip("'")
    if p.lower().startswith("file://"):
        p = _up.unquote(p[7:])
        if len(p) > 2 and p[0] == "/" and p[2] == ":":
            p = p[1:]                      # file:///P:/data -> P:/data
    if IS_WSL and len(p) >= 2 and p[1] == ":" and p[0].isalpha():
        rest = p[2:].replace("\\", "/").lstrip("/")
        drive = os.environ.get("CRYSTALPILOT_DRIVE", "").strip().rstrip("\\").rstrip(":").upper()
        if drive and p[0].upper() == drive:
            return str(PROJECTS_DIR / rest) if rest else str(PROJECTS_DIR)
        return "/mnt/" + p[0].lower() + ("/" + rest if rest else "")
    return p


LOCATE_DEPTH = 5                 # folder levels searched below each place
LOCATE_SECONDS = 20.0            # a whole network drive must not hang the page
LOCATE_MAX_ENTRIES = 400000


def locate_dropped_folder(name, files, hints=None, restrict_to=None):
    """Where a folder dropped on the page is on this computer.

    A browser gives a web page the dropped folder's name and the names and
    sizes of the files in it, never its path.  The folder is looked for by
    that name in the places the user is likely to have it - the hint folders
    first (recently used, already added), then the projects folder, the home
    folder and the Windows drives - and a candidate counts only when the
    listed files are in it with the same sizes.  Returns (matches, searched_all).
    """
    import time as _time
    name = str(name or "").strip()
    wanted = [(str(f.get("name", "")), f.get("size")) for f in (files or []) if isinstance(f, dict) and f.get("name")][:12]
    if not name or not wanted:
        return [], True
    roots, seen = [], set()
    def add(p):
        try:
            p = Path(batch_local_path(p)).expanduser().resolve()
        except (OSError, ValueError):
            return
        if restrict_to is not None and p != restrict_to and restrict_to not in p.parents:
            return
        if p.is_dir() and str(p) not in seen:
            seen.add(str(p))
            roots.append(p)
    for h in hints or []:
        add(h)
        add(Path(batch_local_path(h)).parent)
    add(PROJECTS_DIR)
    add(Path.home())
    drives = _wsl_drives() if IS_WSL else []
    for d in [d for d in drives if not d.endswith("/c")] + [d for d in drives if d.endswith("/c")]:
        add(d)

    def matches(folder):
        for fname, size in wanted:
            p = folder / fname
            try:
                if not p.is_file() or (size is not None and p.stat().st_size != int(size)):
                    return False
            except (OSError, ValueError):
                return False
        return True

    found, walked, entries = [], set(), 0
    deadline = _time.time() + LOCATE_SECONDS
    for root in roots:
        base = len(root.parts)
        for dirpath, dirnames, _files in os.walk(str(root)):
            here = Path(dirpath)
            if str(here) in walked:
                dirnames[:] = []
                continue
            walked.add(str(here))
            if here.name == name and matches(here) and str(here) not in found:
                found.append(str(here))
            depth = len(here.parts) - base
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and not d.startswith("$")
                           and d not in ("Windows", "Program Files", "Program Files (x86)", "ProgramData", "AppData", "proc", "sys")
                           and depth < LOCATE_DEPTH]
            # a folder of that name one level down is checked at once, before the walk reaches it
            if name in dirnames:
                cand = here / name
                if matches(cand) and str(cand) not in found:
                    found.append(str(cand))
            entries += len(dirnames) + len(_files)
            if entries > LOCATE_MAX_ENTRIES or _time.time() > deadline:
                return found, False
        if found:
            return found, True          # the likeliest places come first; stop at the first that has it
    return found, True


# ── 1b. finding the beamline's XDS.INP ───────────────────────────────────────
# Beamline pipelines leave an XDS.INP next to their results, with the
# geometry the beamline knows (rotation axis direction, beam centre, detector
# orientation) - better than anything read from an image header.  Their
# folder names differ from beamline to beamline, so the search looks
# everywhere near the data and uses the names only to rank: a folder whose
# name CONTAINS a keyword (fast_dp_2, autoPROC.run1, processing-old) comes
# first, earlier keywords before later ones.
XDSINP_KEYWORDS_DEFAULT = ["fast_dp", "processing", "autoproc"]
XDSINP_SEARCH_DEPTH = 6          # folder levels below each search root
XDSINP_UP_LEVELS = 2             # the data folder, its parent and grandparent are searched
XDSINP_SCAN_LIMIT = 300000       # directory entries in one search
XDSINP_MAX_SIZE = 512 * 1024     # an XDS.INP is a few kB; anything big is not one
XDSINP_SEARCH_SECONDS = 60.0     # a slow network drive must not hang the page

# beamline settings that belong to the beamline's computers, not this one
XDSINP_LOCAL_KEYS = ("CLUSTER_NODES", "CLUSTER_RUN", "MAXIMUM_NUMBER_OF_JOBS",
                     "MAXIMUM_NUMBER_OF_PROCESSORS", "SECONDS")
# keywords whose value is a file name
XDSINP_FILE_KEYS = ("X-GEO_CORR", "Y-GEO_CORR", "REFERENCE_DATA_SET", "LIB")


def xdsinp_values(text):
    """The effective KEY -> value pairs of an XDS.INP (last one wins, comments skipped)."""
    values = {}
    for line in str(text).splitlines():
        if line.lstrip().startswith("!"):
            continue
        pairs, _ = XDSINPEditor._split_pairs(line)
        for key, value in pairs:
            values[key.upper()] = value
    return values


def _template_key(template):
    """What identifies a data set in a NAME_TEMPLATE_OF_DATA_FRAMES, independent of its folder.

    x_????.cbf and x_0001.cbf -> 'x_#.cbf';  x_master.h5, x_??????.h5 and
    x_data_000001.h5 -> 'x.h5'.
    """
    import re as _re
    name = str(template).replace("\\", "/").rsplit("/", 1)[-1].strip().lower()
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    if ext in ("h5", "hdf5"):
        stem = _re.sub(r"_(master|data_[?\d]+|[?\d]+)$", "", stem)
        return stem + ".h5"
    # only the frame number goes: the ? run of a template, else the last digit run -
    # never a run number or temperature in the prefix (lyso_001_????, prot_100K_????)
    if "?" in stem:
        stem = _re.sub(r"\?+(?=[^?]*$)", "#", stem, count=1)
    else:
        stem = _re.sub(r"\d{3,}(?=\D*$)", "#", stem, count=1)
    return stem + "." + ext


def _dataset_xds_template(dataset, question_marks=6):
    """The dataset's own NAME_TEMPLATE_OF_DATA_FRAMES."""
    template = str(dataset["template"])
    if dataset.get("kind") == "eiger":
        cut = max(template.rfind("/"), template.rfind("\\")) + 1
        folder, name = template[:cut], template[cut:]
        prefix = name[: name.lower().rindex("_master")]
        return folder + prefix + "_" + "?" * question_marks + os.path.splitext(name)[1]
    return template


def _dataset_header(dataset):
    """The image header of a data set's first frame, or {} when it cannot be read."""
    import glob as _glob
    template = str(dataset["template"])
    if dataset.get("kind") == "eiger":
        first = template
    else:
        matches = sorted(_glob.glob(template.replace("?", "[0-9]")))
        first = matches[0] if matches else None
    if not first:
        return {}
    try:
        header = ImageHeaderReader.read(first)
    except Exception:
        return {}
    return {} if ("_error" in header and "wavelength" not in header) else header


def _xdsinp_header_check(values, header):
    """Does an XDS.INP describe the images whose header this is?  (ok, reasons)"""
    def num(v):
        try:
            return float(str(v).split()[0])
        except (TypeError, ValueError, IndexError):
            return None
    reasons = []
    checks = (("X-RAY_WAVELENGTH", "wavelength", "wavelength", lambda a, b: abs(a - b) <= 0.002, "%.4f Å"),
              ("DETECTOR_DISTANCE", "detector_distance", "distance", lambda a, b: abs(abs(a) - abs(b)) <= max(1.0, 0.01 * abs(b)), "%.1f mm"),
              ("OSCILLATION_RANGE", "osc_range", "oscillation", lambda a, b: abs(a - b) <= 0.002, "%.3f°"))
    compared = 0
    for key, hkey, label, same, fmt in checks:
        a, b = num(values.get(key)), num(header.get(hkey))
        if a is None or b is None:
            continue
        compared += 1
        if not same(a, b):
            reasons.append("%s %s in the XDS.INP, %s in the images" % (label, fmt % a, fmt % b))
    return (not reasons), reasons, compared


def _path_parts(path):
    return [p for p in str(path).replace("\\", "/").split("/") if p and p != "."]


def _keyword_rank(path, keywords):
    """Index of the first keyword contained in a folder name of `path`; len(keywords) when none."""
    parts = [p.lower() for p in _path_parts(path)]
    for i, word in enumerate(keywords):
        if word and any(word in part for part in parts):
            return i, word
    return len(keywords), ""


def _xdsinp_search_roots(datasets, roots):
    out, seen = [], set()
    candidates = [batch_local_path(r) for r in (roots or []) if str(r or "").strip()]
    for d in datasets:
        folder = Path(str(d.get("folder") or Path(str(d["template"])).parent))
        for _ in range(XDSINP_UP_LEVELS + 1):
            candidates.append(str(folder))
            if folder.parent == folder:
                break
            folder = folder.parent
    for c in candidates:
        try:
            p = Path(c).expanduser().resolve()
        except OSError:
            continue
        if RESTRICT_BROWSE:
            # climbing to the parent and grandparent must not leave the projects folder
            root = PROJECTS_DIR.resolve()
            if p != root and root not in p.parents:
                continue
        if p.is_dir() and str(p) not in seen:
            seen.add(str(p))
            out.append(p)
    return out


def _is_crystalpilot_project(folder):
    """A folder CrystalPilot made: metadata.json with its own keys (other programs use the name too)."""
    try:
        meta = json.loads((Path(folder) / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(meta, dict) and "completed_steps" in meta and "name" in meta


def _find_xdsinp_files(roots, keywords):
    """Every XDS.INP under the roots, keyword folders first, each file once."""
    import time as _time
    found, walked, entries = [], set(), 0
    deadline = _time.time() + XDSINP_SEARCH_SECONDS
    for root in roots:
        base_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(str(root)):
            here = Path(dirpath)
            if str(here) in walked:
                dirnames[:] = []
                continue
            walked.add(str(here))
            if "metadata.json" in filenames and _is_crystalpilot_project(here):
                # a CrystalPilot project: its XDS.INP carries an earlier run's exclusions and
                # fixes, and names the images by their path on this computer, so it would
                # outrank the beamline's file.  Neither it nor its run folders are candidates.
                dirnames[:] = []
                continue
            depth = len(here.parts) - base_depth
            # keyword folders are walked first, so a scan limit cuts the least likely places
            dirnames[:] = sorted((d for d in dirnames
                                  if not d.startswith(".") and d not in ("batches", "__pycache__")
                                  and depth < XDSINP_SEARCH_DEPTH),
                                 key=lambda d: (_keyword_rank(d, keywords)[0], d.lower()))
            entries += len(filenames) + len(dirnames)
            if entries > XDSINP_SCAN_LIMIT or _time.time() > deadline:
                return found, True
            for name in filenames:
                if name.upper() == "XDS.INP":
                    found.append(here / name)
    return found, False


def find_xdsinp_candidates(datasets, roots=None, keywords=None):
    """For each data set, the XDS.INP files that describe it, best first.

    A candidate must name the data set's images (NAME_TEMPLATE_OF_DATA_FRAMES,
    file name part - beamline paths are not this computer's paths) and, where
    the image header can be read, agree with it on wavelength, distance and
    oscillation.  Ranked by: how much of the image folder path its template
    shares with the data set's folder, then the keyword of its folder, then
    the newest.  State per data set: 'imported' (a clear best), 'pick'
    (equally good candidates that disagree on geometry or space group) or
    'generate' (none - XDS.INP is written from the image header).
    """
    keywords = [str(k).strip().lower() for k in (keywords if keywords is not None else XDSINP_KEYWORDS_DEFAULT)
                if str(k).strip()]
    datasets = [d for d in (datasets or []) if d and d.get("template")]
    search_roots = _xdsinp_search_roots(datasets, roots)
    files, truncated = _find_xdsinp_files(search_roots, keywords)
    parsed = []
    for path in files:
        try:
            if path.stat().st_size > XDSINP_MAX_SIZE:
                continue
            text = _read_text_lenient(path)
            mtime = path.stat().st_mtime
        except OSError:
            continue
        values = xdsinp_values(text)
        template = values.get("NAME_TEMPLATE_OF_DATA_FRAMES", "").split()
        if not template:
            continue
        template = template[0]
        tdir = template.replace("\\", "/").rsplit("/", 1)[0] if "/" in template.replace("\\", "/") else ""
        if tdir and not tdir.startswith("/") and not (len(tdir) > 1 and tdir[1] == ":"):
            tdir = str((path.parent / tdir).resolve())       # relative to the XDS.INP
        elif not tdir:
            tdir = str(path.parent)
        rank, word = _keyword_rank(path.parent, keywords)
        parsed.append({"path": str(path), "key": _template_key(template), "template": template, "template_dir": tdir,
                       "values": values, "mtime": mtime, "keyword_rank": rank, "keyword": word})

    results = []
    for d in datasets:
        key = _template_key(_dataset_xds_template(d))
        folder = str(d.get("folder") or Path(str(d["template"])).parent)
        fparts = _path_parts(folder)
        header = None
        accepted, rejected = [], []
        for c in parsed:
            if c["key"] != key:
                continue
            if header is None:
                header = _dataset_header(d)
            ok, reasons, compared = _xdsinp_header_check(c["values"], header) if header else (True, [], 0)
            tparts = _path_parts(c["template_dir"])
            if os.path.normpath(c["template_dir"]) == os.path.normpath(folder):
                tail = len(fparts) + 1                        # it names this very folder
            else:
                tail = 0
                while tail < min(len(fparts), len(tparts)) and fparts[-1 - tail] == tparts[-1 - tail]:
                    tail += 1
            v = c["values"]
            entry = {"path": c["path"], "keyword": c["keyword"], "keyword_rank": c["keyword_rank"],
                     "folder_match": tail, "mtime": c["mtime"],
                     "modified": datetime.fromtimestamp(c["mtime"]).isoformat(timespec="minutes"),
                     "template": c["template"], "header_checked": bool(header) and compared > 0,
                     "space_group": (v.get("SPACE_GROUP_NUMBER", "").split() or [""])[0],
                     "unit_cell": " ".join(v.get("UNIT_CELL_CONSTANTS", "").split()[:6]),
                     "geometry": [" ".join(v.get(k, "").split()) for k in
                                  ("ORGX", "ORGY", "DETECTOR_DISTANCE", "ROTATION_AXIS", "SPACE_GROUP_NUMBER", "UNIT_CELL_CONSTANTS")]}
            if ok:
                accepted.append(entry)
            else:
                entry["reason"] = "; ".join(reasons)
                rejected.append(entry)
        accepted.sort(key=lambda e: (-e["folder_match"], e["keyword_rank"], -e["mtime"]))
        if not accepted:
            state = "generate"
        elif len(accepted) > 1 and \
                (accepted[0]["folder_match"], accepted[0]["keyword_rank"]) == (accepted[1]["folder_match"], accepted[1]["keyword_rank"]) and \
                any(e["geometry"] != accepted[0]["geometry"] for e in accepted[1:]
                    if (e["folder_match"], e["keyword_rank"]) == (accepted[0]["folder_match"], accepted[0]["keyword_rank"])):
            state = "pick"
        else:
            state = "imported"
        for e in accepted + rejected:
            e.pop("geometry", None)
        results.append({"template": d["template"], "state": state,
                        "choice": accepted[0]["path"] if accepted else "",
                        "candidates": accepted, "rejected": rejected})
    return {"results": results, "roots": [str(r) for r in search_roots], "files": len(parsed),
            "truncated": truncated, "keywords": keywords}


def import_xdsinp(source, dataset, neggia_lib=""):
    """A beamline XDS.INP made to run here on this data set: (text, notes).

    Kept: the beamline's geometry and everything else.  Changed: the image
    template (this computer's copy of the images), the HDF5 library, file
    names that do not exist here, the beamline's own computer settings, and
    the resolution range (the wizard's cut-off decides).
    """
    source = Path(str(source))
    text = _read_text_lenient(source)
    notes = []
    template = _dataset_xds_template(dataset)
    is_h5 = str(dataset.get("template", "")).lower().endswith((".h5", ".hdf5"))
    old_template = xdsinp_values(text).get("NAME_TEMPLATE_OF_DATA_FRAMES", "").split()
    if dataset.get("kind") == "eiger" and old_template and "?" in old_template[0]:
        template = _dataset_xds_template(dataset, old_template[0].count("?"))
    first, last = dataset.get("first"), dataset.get("last")
    out = ["! Imported by CrystalPilot %s from %s" % (VERSION, source),
           "! Changes are listed as comments starting with '! CrystalPilot:'"]
    template_written = False
    for line in text.splitlines():
        if line.lstrip().startswith("!") or "=" not in line:
            out.append(line)
            continue
        pairs, comment = XDSINPEditor._split_pairs(line)
        kept, dropped = [], []
        for key, value in pairs:
            ku = key.upper()
            if ku == "NAME_TEMPLATE_OF_DATA_FRAMES":
                rest = value.split()[1:]                       # e.g. a trailing CBF / DIRECT format word
                new = " ".join([template] + rest)
                if value != new:
                    notes.append("NAME_TEMPLATE_OF_DATA_FRAMES: %s -> %s" % (value, new))
                kept.append([key, new])
                template_written = True
            elif ku in XDSINP_LOCAL_KEYS:
                dropped.append((key, value, "a setting of the beamline's computers"))
            elif ku == "INCLUDE_RESOLUTION_RANGE":
                dropped.append((key, value, "the resolution limits come from the wizard"))
            elif ku == "LIB":
                if is_h5 and neggia_lib:
                    if value != neggia_lib:
                        notes.append("LIB: %s -> %s" % (value, neggia_lib))
                    kept.append([key, neggia_lib])
                elif Path(value).is_file():
                    kept.append([key, value])
                else:
                    dropped.append((key, value, "that library is not on this computer"))
            elif ku in XDSINP_FILE_KEYS and value:
                name = value.split()[0]
                here = Path(name) if Path(name).is_absolute() else source.parent / name
                if here.is_file():
                    if str(here) != name:
                        notes.append("%s: %s -> %s" % (key, name, here))
                    kept.append([key, str(here)])
                else:
                    dropped.append((key, value, "file not found here"))
            elif ku in ("DATA_RANGE", "SPOT_RANGE", "BACKGROUND_RANGE") and first is not None and last is not None:
                try:
                    lo, hi = [int(float(x)) for x in value.split()[:2]]
                except ValueError:
                    kept.append([key, value])
                    continue
                if lo >= first and hi <= last:
                    kept.append([key, value])
                    continue
                new_lo, new_hi = max(lo, first), min(hi, last)
                if new_lo > new_hi:
                    # nothing of the beamline's range is on disk
                    if ku == "SPOT_RANGE":
                        dropped.append((key, value, "none of these frames are on disk (%d-%d)" % (first, last)))
                        continue
                    new_lo, new_hi = first, (last if ku == "DATA_RANGE" else min(first + 9, last))
                new = "%d %d" % (new_lo, new_hi)
                notes.append("%s: %s -> %s (the frames on disk are %d-%d)" % (key, value, new, first, last))
                kept.append([key, new])
            else:
                kept.append([key, value])
        if kept:
            out.append(XDSINPEditor._join_pairs(kept, comment))
        for key, value, why in dropped:
            out.append("!%s= %s  ! CrystalPilot: %s" % (key, value, why))
            notes.append("%s= %s commented out: %s" % (key, value, why))
    if not template_written:
        out.append("NAME_TEMPLATE_OF_DATA_FRAMES= " + template)
        notes.append("NAME_TEMPLATE_OF_DATA_FRAMES added: " + template)
    if is_h5 and neggia_lib and "LIB" not in xdsinp_values("\n".join(out)):
        out.append("LIB= " + neggia_lib)
        notes.append("LIB added: " + neggia_lib)
    return "\n".join(out) + "\n", notes


def _xdsinp_without_space_group(text):
    """The same XDS.INP with SPACE_GROUP_NUMBER and UNIT_CELL_CONSTANTS commented out."""
    return XDSINPEditor.apply_params(text, {"SPACE_GROUP_NUMBER": None, "UNIT_CELL_CONSTANTS": None})


# ── 2. batch state on disk ───────────────────────────────────────────────────
_BATCH_LOCK = threading.RLock()
_BATCH_ACTIVE = {"id": None, "thread": None, "stop": None, "skip": False, "project": None}
_BATCH_ITEM_STATES = ("queued", "running", "done", "failed", "stopped", "skipped", "interrupted")


def _batch_root():
    return PROJECTS_DIR / "batches"


def _batch_dir(batch_id):
    if not batch_id or batch_id != Path(str(batch_id)).name or str(batch_id).startswith("."):
        raise ValueError("Invalid batch id")
    return _batch_root() / str(batch_id)


def batch_load(batch_id):
    path = _batch_dir(batch_id) / "batch.json"
    if not path.is_file():
        raise FileNotFoundError("Batch not found")
    with _BATCH_LOCK:
        state = json.loads(path.read_text(encoding="utf-8"))
    # a batch that was running when the server stopped is not running any more
    if _BATCH_ACTIVE["id"] != batch_id:
        changed = False
        for item in state.get("items", []):
            if item.get("status") == "running":
                item["status"] = "interrupted"
                item["error"] = "the program stopped while this data set was being processed"
                changed = True
        if state.get("status") == "running":
            state["status"] = "stopped"
            changed = True
        if changed:
            batch_save(state)
    state["merges"] = _batch_merges(batch_id)
    return state


def batch_save(state):
    """Write batch.json - the queue's state only.

    Merges are kept in their own merge_<stamp>/merge.json: the queue worker
    holds the batch state in memory while it runs, and a merge recorded in
    batch.json in the meantime would be overwritten by the worker's next save.
    """
    folder = _batch_dir(state["id"])
    folder.mkdir(parents=True, exist_ok=True)
    with _BATCH_LOCK:
        state["updated"] = datetime.now().isoformat(timespec="seconds")
        on_disk = {k: v for k, v in state.items() if k not in ("merges", "active", "current")}
        ProjectManager._write_meta(folder / "batch.json", on_disk)


def _batch_merges(batch_id):
    """Every merge of a batch, oldest first, from its own merge.json."""
    out = []
    for path in sorted(_batch_dir(batch_id).glob("merge_*/merge.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def _merge_save(record):
    with _BATCH_LOCK:
        ProjectManager._write_meta(Path(record["folder"]) / "merge.json", record)


def batch_list():
    root = _batch_root()
    out = []
    if not root.is_dir():
        return out
    for folder in sorted(root.iterdir(), reverse=True):
        if not (folder / "batch.json").is_file():
            continue
        try:
            state = batch_load(folder.name)
        except Exception:
            continue
        counts = {}
        for item in state.get("items", []):
            counts[item.get("status", "queued")] = counts.get(item.get("status", "queued"), 0) + 1
        out.append({"id": state["id"], "name": state.get("name", ""), "created": state.get("created", ""),
                    "status": state.get("status", "draft"), "counts": counts, "size": len(state.get("items", []))})
    return out


def batch_create(name, datasets, strategy, search=None):
    """Make the projects and the batch. Nothing runs until batch_start.

    A data set's 'xdsinp' is the XDS.INP chosen for it in the wizard (empty:
    generate it from the image header).  search: the keywords and folders the
    XDS.INP search used, kept with the batch as a record.
    """
    strategy = normalize_strategy(strategy)
    datasets = [d for d in (datasets or []) if d and d.get("template")]
    if not datasets:
        raise ValueError("Choose at least one data set.")
    for d in datasets:
        if d.get("xdsinp") and not Path(str(d["xdsinp"])).is_file():
            raise ValueError("XDS.INP not found: " + str(d["xdsinp"]))
        if d.get("existing_project"):
            # a project set up by hand: processed in place, with its own XDS.INP
            if not (_pdir(str(d["existing_project"])) / "XDS.INP").is_file():
                raise ValueError("Project %s has no XDS.INP to start from." % d["existing_project"])
    owned = [str(d["existing_project"]) for d in datasets if d.get("existing_project")]
    if len(owned) != len(set(owned)):
        raise ValueError("A project can be in a run only once.")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    batch_id, n = stamp, 2
    while _batch_dir(batch_id).exists():          # a double click must not overwrite the first run
        batch_id, n = "%s_%d" % (stamp, n), n + 1
    taken = set(owned)
    items = []
    for d in datasets:
        if d.get("existing_project"):
            project = str(d["existing_project"])
        else:
            project = _batch_project_name(d.get("project") or d.get("label") or Path(d["template"]).stem, taken)
            ProjectManager.create(project, "AutoPilot " + stamp + ": " + str(d.get("label", "")), str(d.get("folder", "")))
        items.append({"project": project, "template": str(d["template"]), "kind": d.get("kind", "series"),
                      "existing": bool(d.get("existing_project")),
                      "label": d.get("label", ""), "folder": str(d.get("folder", "")),
                      "first": d.get("first"), "last": d.get("last"),
                      "xdsinp": str(d.get("xdsinp") or ""), "attempt": "",
                      "status": "queued", "phase": "", "error": "",
                      "started": "", "finished": "", "metrics": {}})
    search = search or {}
    state = {"id": batch_id, "name": str(name or "").strip() or ("AutoPilot " + stamp),
             "created": datetime.now().isoformat(timespec="seconds"),
             "status": "draft", "strategy": strategy, "items": items, "merges": [],
             "search": {"keywords": [str(k) for k in (search.get("keywords") or [])],
                        "roots": [str(r) for r in (search.get("roots") or [])]}}
    batch_save(state)
    return state


# ── 3. the queue ─────────────────────────────────────────────────────────────
def batch_metrics(project):
    """What the comparison table shows for one project, read from its own logs."""
    project_dir = _pdir(project)
    out = {}
    lp = _pfile(project_dir, "CORRECT.LP")
    if lp.is_file():
        parsed = LPParser.parse_correct(_read_text_lenient(lp))
        out["space_group"] = parsed.get("space_group")
        out["sg_name"] = parsed.get("current_sg_name")
        cell = parsed.get("unit_cell") or {}
        if cell:
            out["unit_cell"] = [cell.get(k) for k in ("a", "b", "c", "alpha", "beta", "gamma")]
        isa = parsed.get("isa")
        if isinstance(isa, dict):
            out["isa"] = isa.get("isa")
        out["mosaicity"] = parsed.get("mosaicity")
        for row in parsed.get("statistics_table") or []:
            if str(row.get("resolution", "")).strip().lower() == "total":
                for key in ("completeness", "r_meas", "i_sigma", "cc_half"):
                    out[key] = row.get(key)
    results = _pfile(project_dir, "AUTOPILOT_RESULTS.json")
    if results.is_file():
        try:
            summary = json.loads(results.read_text(encoding="utf-8"))
            out["resolution"] = summary.get("resolution")
            opt = summary.get("optimization") or {}
            if "kept" in opt:
                out["reintegration"] = "kept" if opt.get("kept") else "rejected"
                out["reintegration_why"] = opt.get("decision", "")
            if summary.get("mtz_file"):
                out["mtz"] = summary.get("mtz_file")
        except (OSError, ValueError):
            pass
    return out


def _batch_event_reader(item, state, log):
    """A write_fn for AutoPilot: keeps the log, follows the phase, catches the end."""
    final = {}
    last_save = [0.0]

    def write_fn(event_text):
        try:
            log.write(event_text)
            log.flush()
        except Exception:
            pass
        head, _, data = event_text.partition("\ndata: ")
        name = head.partition(":")[2].strip()
        if name == "ap_phase":
            try:
                item["phase"] = json.loads(data).get("phase", "")
            except ValueError:
                return
            import time as _t
            if _t.time() - last_save[0] > 1.0:
                last_save[0] = _t.time()
                batch_save(state)
        elif name == "ap_error":
            try:
                item["error"] = json.loads(data).get("message", "")
            except ValueError:
                pass
        elif name == "ap_done":
            try:
                final.update(json.loads(data))
            except ValueError:
                pass
    return write_fn, final


def _batch_log(log, text):
    """A line in a data set's log, in the same framing AutoPilot's own lines have."""
    try:
        log.write("event: ap_log\ndata: " + json.dumps({"text": text}) + "\n\n")
        log.flush()
    except Exception:
        pass


_LINK_FAILURES = {}      # template -> why no link without blanks could be made


def batch_xds_safe_template(project, template):
    """The data set's image template in a form XDS can read.

    XDS cuts NAME_TEMPLATE_OF_DATA_FRAMES at the first blank.  When the image
    FOLDER has blanks (/mnt/c/Users/First Last/...), the project gets a
    link without blanks to that folder (frames, frames_2, ...) and the
    template goes through it (relative to the project folder when that path has
    blanks as well); the images stay where they are.  Blanks in the
    frame file names themselves cannot be worked around this way: ValueError.
    """
    t = str(template)
    if " " not in t:
        return t
    cut = max(t.rfind("/"), t.rfind("\\")) + 1
    folder, name = t[:cut].rstrip("/\\"), t[cut:]
    if " " in name:
        raise ValueError("The frame file names contain blanks (%s): XDS cannot read such names. "
                         "Rename the frames, or link them under names without blanks." % name)
    project_dir = _pdir(project)
    real = os.path.realpath(folder)
    n = 1
    while True:
        link = project_dir / ("frames" if n == 1 else "frames_%d" % n)
        if link.is_symlink() or link.exists():
            if link.is_symlink() and os.path.realpath(str(link)) == real:
                break
            n += 1
            continue
        try:
            os.symlink(folder, str(link))
        except (OSError, NotImplementedError) as exc:
            # no links on this file system: leave the path as it is; the log says why XDS may not read it
            _LINK_FAILURES[str(template)] = str(exc)
            return t
        break
    if " " in str(project_dir):
        # the project's own path has blanks too: name the link relative to the project
        # folder, where AutoPilot runs XDS
        return link.name + "/" + name
    return str(link) + "/" + name


def _batch_prepare_xdsinp(item, neggia, log):
    """Write the imported XDS.INP into the project; its text, or None when AutoPilot generates one."""
    if item.get("existing"):
        _batch_log(log, ">>> XDS.INP: the project's own, as it was set up by hand")
        return None
    if not item.get("xdsinp"):
        _batch_log(log, ">>> XDS.INP: written from the image header (no beamline XDS.INP chosen)")
        return None
    text, notes = import_xdsinp(item["xdsinp"], item, neggia)
    _write_inp(_pdir(item["project"]) / "XDS.INP", text)
    _batch_log(log, ">>> XDS.INP imported from " + item["xdsinp"])
    for note in notes:
        _batch_log(log, "    " + note)
    return text


def batch_attempts(strategy, kwargs, imported_text):
    """The AutoPilot runs one data set gets, in order; the first that succeeds ends it.

    Each: label, the stream_autopilot kwargs, and the XDS.INP text to start
    from (None: leave the project's XDS.INP as it is).  Only an imported
    XDS.INP with a space group gives more than one run: by default without
    that space group, then with it, then auto-indexing - each without
    auto-indexing except the last, so a failed indexing moves on at once.
    """
    s = normalize_strategy(strategy)
    base = dict(kwargs)
    single = [{"label": "", "kwargs": base, "xdsinp": imported_text}]
    if imported_text is None or s["sg_mode"] == "fixed":
        return single
    v = xdsinp_values(imported_text)
    sg = (v.get("SPACE_GROUP_NUMBER", "").split() or [""])[0]
    if not sg.isdigit() or int(sg) < 1:
        return single
    cell_values = v.get("UNIT_CELL_CONSTANTS", "").split()[:6]
    try:
        cell = " ".join(cell_values) if len(cell_values) == 6 and min(float(x) for x in cell_values) > 0 else None
    except ValueError:
        cell = None
    without = _xdsinp_without_space_group(imported_text)
    if cell is None:
        # XDS takes a space group only together with its cell: without one it is of no use
        return [{"label": "without the imported space group %s (the file has no unit cell for it)" % sg,
                 "kwargs": base, "xdsinp": without}]
    with_sg = dict(base, space_group=sg, unit_cell=cell)
    if s["sg_route"] == "use":
        return [{"label": "with the imported space group %s" % sg, "kwargs": with_sg, "xdsinp": imported_text}]
    if s["sg_route"] == "ignore":
        return [{"label": "without the imported space group", "kwargs": base, "xdsinp": without}]
    attempts = [
        {"label": "without the imported space group %s" % sg, "kwargs": dict(base, autoindex_tier="off"), "xdsinp": without},
        {"label": "with the imported space group %s" % sg, "kwargs": dict(with_sg, autoindex_tier="off"), "xdsinp": imported_text},
    ]
    if base.get("autoindex_tier", "medium") != "off":
        attempts.append({"label": "auto-indexing (%s), space group left open" % base["autoindex_tier"],
                         "kwargs": base, "xdsinp": without})
    return attempts


def _batch_worker(batch_id):
    try:
        _batch_worker_run(batch_id)
    except Exception as exc:
        print("[batch %s] stopped by an error: %s: %s" % (batch_id, type(exc).__name__, exc))
    finally:
        with _BATCH_LOCK:
            _BATCH_ACTIVE.update({"id": None, "thread": None, "stop": None, "skip": False, "project": None})


def _batch_worker_run(batch_id):
    state = batch_load(batch_id)
    stop = _BATCH_ACTIVE["stop"]
    kwargs = strategy_autopilot_kwargs(state["strategy"])
    state["status"] = "running"
    batch_save(state)
    logs = _batch_dir(batch_id) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    try:
        for item in state["items"]:
            if stop.is_set():
                break
            if item.get("status") not in ("queued", "interrupted", "stopped"):   # "stopped": runs saved by v351 before the fix
                continue
            project = item["project"]
            _BATCH_ACTIVE["project"] = project
            _BATCH_ACTIVE["skip"] = False
            if item.get("started") and not item.get("existing") and not item.get("xdsinp"):
                # its XDS.INP was generated and then changed by the interrupted run (DELPHI,
                # ice rings, exclusions): put it aside so AutoPilot writes a fresh one
                stale = _pdir(project) / "XDS.INP"
                if stale.is_file():
                    os.replace(str(stale), str(stale) + ".interrupted_run")
            item.update({"status": "running", "phase": "PREPARE", "error": "", "attempt": "",
                         "started": datetime.now().isoformat(timespec="seconds"), "finished": ""})
            batch_save(state)
            neggia = NEGGIA_LIB if str(item.get("template", "")).lower().endswith((".h5", ".hdf5")) else ""
            print("[batch %s] %s: started" % (batch_id, project))
            try:
                with open(str(logs / (project + ".log")), "a", encoding="utf-8", errors="replace") as log:
                    run_item = item
                    if not item.get("existing"):
                        safe = batch_xds_safe_template(project, item["template"])
                        if safe != item["template"]:
                            _batch_log(log, ">>> The image folder has blanks, which XDS cannot read: images reached through " + safe)
                        elif " " in safe:
                            _batch_log(log, ">>> Warning: the image path has blanks, which XDS cannot read, and no link without blanks "
                                            "could be made (" + _LINK_FAILURES.get(safe, "unknown reason") + ")")
                        run_item = dict(item, template=safe)
                    imported = _batch_prepare_xdsinp(run_item, neggia, log)
                    attempts = batch_attempts(state["strategy"], kwargs, imported)
                    status, final = "stopped", {}
                    for n, attempt in enumerate(attempts, 1):
                        if stop.is_set() or _BATCH_ACTIVE["skip"]:
                            break
                        if len(attempts) > 1:
                            item["attempt"] = "%d of %d: %s" % (n, len(attempts), attempt["label"])
                            _batch_log(log, "")
                            _batch_log(log, "=== Attempt %s ===" % item["attempt"])
                        if attempt.get("xdsinp") is not None:
                            _write_inp(_pdir(project) / "XDS.INP", attempt["xdsinp"])
                        item["error"] = ""
                        write_fn, final = _batch_event_reader(item, state, log)
                        stream_autopilot(project, write_fn, template=None if item.get("existing") else run_item["template"],
                                         neggia_lib=neggia, **attempt["kwargs"])
                        status = str(final.get("status") or "failed")
                        if status in ("success", "completed", "done", "stopped") or stop.is_set() or _BATCH_ACTIVE["skip"]:
                            break
                summary = final.get("summary") or {}
                if status in ("success", "completed", "done"):
                    # a run that finished stays finished, even when Stop or Skip came in its last seconds
                    item["status"] = "done"
                elif _BATCH_ACTIVE["skip"]:
                    item["status"] = "skipped"
                elif status == "stopped" or stop.is_set():
                    # Stop halts the run; the data set it interrupted goes back in the queue, so Resume redoes it
                    item["status"] = "queued"
                    item["error"] = "stopped while it was being processed; Resume starts it again"
                else:
                    item["status"] = "failed"
                    item["error"] = item.get("error") or summary.get("failure_reason") or "AutoPilot ended with " + status
            except Exception as exc:
                item["status"] = "failed"
                item["error"] = "%s: %s" % (type(exc).__name__, exc)
            item["phase"] = ""
            item["finished"] = datetime.now().isoformat(timespec="seconds")
            try:
                item["metrics"] = batch_metrics(project)
            except Exception as exc:
                item["metrics"] = {"error": str(exc)}
            print("[batch %s] %s: %s%s" % (batch_id, project, item["status"],
                                           (" - " + item["error"]) if item.get("error") else ""))
            batch_save(state)
        state["status"] = "stopped" if stop.is_set() else "done"
        batch_save(state)
    finally:
        with _BATCH_LOCK:
            _BATCH_ACTIVE.update({"id": None, "thread": None, "stop": None, "skip": False, "project": None})


def batch_start(batch_id):
    state = batch_load(batch_id)
    with _BATCH_LOCK:
        if _BATCH_ACTIVE["id"]:
            raise DirectoryBusyError("Batch %s is already running - one batch at a time, XDS uses every core." % _BATCH_ACTIVE["id"])
        if not any(i.get("status") in ("queued", "interrupted", "stopped") for i in state["items"]):
            raise ValueError("Nothing left to process in this batch.")
        _BATCH_ACTIVE.update({"id": batch_id, "stop": threading.Event(), "skip": False, "project": None})
        thread = threading.Thread(target=_batch_worker, args=(batch_id,), name="batch-" + batch_id, daemon=True)
        _BATCH_ACTIVE["thread"] = thread
        thread.start()
    return {"started": batch_id}


def batch_stop(batch_id, skip_only=False):
    """Stop the batch, or (skip_only) just the data set being processed."""
    with _BATCH_LOCK:
        if _BATCH_ACTIVE["id"] != batch_id:
            return {"running": False}
        project = _BATCH_ACTIVE["project"]
        if skip_only:
            _BATCH_ACTIVE["skip"] = True
        else:
            _BATCH_ACTIVE["stop"].set()
    if project:
        _stop_procs(project, kind="autopilot")
    return {"running": True, "project": project, "skip": skip_only}


def batch_state(batch_id):
    state = batch_load(batch_id)
    active = _BATCH_ACTIVE["id"] == batch_id
    # A finished data set without numbers (a batch written by an older version,
    # or metrics that could not be read at the time) gets them now - once, not
    # on every poll: reading 50 CORRECT.LP files every three seconds is not free.
    if not active:
        filled = False
        for item in state.get("items", []):
            if item.get("status") == "done" and not item.get("metrics") and not item.get("metrics_checked"):
                try:
                    item["metrics"] = batch_metrics(item["project"])
                except Exception:
                    pass
                item["metrics_checked"] = True
                filled = True
        if filled:
            batch_save(state)
    state["active"] = active
    state["current"] = _BATCH_ACTIVE["project"] if active else None
    return state


# ── 5. merging ───────────────────────────────────────────────────────────────
def _hkl_header(path):
    """SPACE_GROUP_NUMBER and UNIT_CELL_CONSTANTS from an XDS reflection file header."""
    sg, cell = None, None
    try:
        with open(str(path), "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.startswith("!"):
                    break
                if line.startswith("!SPACE_GROUP_NUMBER="):
                    sg = line.split("=", 1)[1].strip()
                elif line.startswith("!UNIT_CELL_CONSTANTS="):
                    cell = [float(v) for v in line.split("=", 1)[1].split()[:6]]
    except (OSError, ValueError):
        pass
    return sg, cell


def merge_plan(projects, criterion="isig2", reference=None):
    """Which data sets can be merged, against which reference, at which cut-offs."""
    rows, excluded = [], []
    for project in projects or []:
        try:
            project_dir = _pdir(project)
        except ValueError:
            excluded.append({"project": project, "reason": "invalid project name"})
            continue
        hkl = _pfile(project_dir, "XDS_ASCII.HKL")
        if not hkl.is_file():
            excluded.append({"project": project, "reason": "no XDS_ASCII.HKL - CORRECT has not finished"})
            continue
        sg, cell = _hkl_header(hkl)
        if not sg or not cell or len(cell) != 6:
            excluded.append({"project": project, "reason": "no space group or cell in the XDS_ASCII.HKL header"})
            continue
        metrics = batch_metrics(project)
        resolution = metrics.get("resolution")
        if not resolution:
            lp = _pfile(project_dir, "CORRECT.LP")
            if lp.is_file():
                table = LPParser.parse_correct(_read_text_lenient(lp)).get("statistics_table") or []
                resolution = LPParser.determine_resolution_cutoff(table, criterion).get("resolution")
        try:
            isa = float(metrics.get("isa"))
        except (TypeError, ValueError):
            isa = None
        rows.append({"project": project, "hkl": str(hkl), "space_group": sg, "cell": cell,
                     "resolution": resolution, "isa": isa})
    if not rows:
        return {"inputs": [], "excluded": excluded, "reference": None}
    by_name = {r["project"]: r for r in rows}
    ref = by_name.get(reference) if reference else None
    if ref is None:
        # the strongest data set anchors the scaling and the indexing
        ref = max(rows, key=lambda r: (r["isa"] is not None, r["isa"] or 0))
    inputs = [ref]
    for row in rows:
        if row is ref:
            continue
        if row["space_group"] != ref["space_group"]:
            excluded.append({"project": row["project"],
                             "reason": "space group %s, the reference has %s" % (row["space_group"], ref["space_group"])})
            continue
        worst_axis = max(abs(row["cell"][i] - ref["cell"][i]) / ref["cell"][i] for i in range(3))
        worst_angle = max(abs(row["cell"][i] - ref["cell"][i]) for i in range(3, 6))
        if worst_axis > BATCH_CELL_TOLERANCE or worst_angle > BATCH_ANGLE_TOLERANCE:
            excluded.append({"project": row["project"],
                             "reason": "cell differs from the reference by %.1f%% (axis) / %.1f° (angle)"
                                       % (100 * worst_axis, worst_angle)})
            continue
        inputs.append(row)
    return {"inputs": inputs, "excluded": excluded, "reference": ref["project"],
            "space_group": ref["space_group"], "cell": ref["cell"]}


def merge_input_names(plan):
    """The short name each reflection file is reached by from the merge folder.

    XDS splits keyword values at blanks and limits the length of file names, so
    inputs/NN_<project>.HKL links stand in for the real paths.  The preview uses
    the same names as the merge, so what the user reads is what runs.
    """
    names = []
    for n, row in enumerate(plan.get("inputs") or [], 1):
        safe = "".join(ch if ch.isalnum() else "_" for ch in row["project"])[:24]
        names.append("inputs/%02d_%s.HKL" % (n, safe))
    return names


def merge_xscale_inp(plan, friedel="FALSE", input_names=None, output_file="merged.ahkl"):
    """XSCALE.INP for a merge plan, keyword by keyword in its proper section.

    input_names: the name each INPUT_FILE is written as (short local links, see
    batch_merge); defaults to the reflection files' own paths.
    """
    names = input_names or [row["hkl"] for row in plan["inputs"]]
    lines = [
        "! XSCALE.INP written by CrystalPilot %s for a batch merge" % VERSION,
        "! reference data set: %s (it anchors the scaling and the indexing)" % plan["reference"],
        "SPACE_GROUP_NUMBER= %s" % plan["space_group"],
        "UNIT_CELL_CONSTANTS= %s" % " ".join("%g" % v for v in plan["cell"]),
        "REFERENCE_DATA_SET= %s" % names[0],
        "",
        "OUTPUT_FILE= %s" % output_file,
        "FRIEDEL'S_LAW= %s" % ("TRUE" if str(friedel).upper() == "TRUE" else "FALSE"),
        "",
    ]
    for row, name in zip(plan["inputs"], names):
        lines.append("! %s" % row["project"])
        lines.append("INPUT_FILE= %s" % name)
        if row.get("resolution"):
            # 999: no low-resolution cut.  A 50 A limit silently drops the
            # lowest-resolution reflections of any cell longer than 50 A.
            lines.append(" INCLUDE_RESOLUTION_RANGE= 999 %.2f" % float(row["resolution"]))
        lines.append("")
    return "\n".join(lines)


def batch_merge(batch_id, projects, reference=None, friedel=None):
    """Write the merge folder and run XSCALE in the background. Returns the merge record."""
    state = batch_load(batch_id)
    strategy = normalize_strategy(state.get("strategy"))
    friedel = friedel or strategy["friedel"]
    plan = merge_plan(projects, strategy["criterion"], reference)
    if len(plan["inputs"]) < 2:
        raise ValueError("Merging needs at least two consistent data sets. "
                         + "; ".join("%s: %s" % (e["project"], e["reason"]) for e in plan["excluded"]))
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    folder, n = _batch_dir(batch_id) / ("merge_" + stamp), 2
    while folder.exists():
        folder, n = _batch_dir(batch_id) / ("merge_%s_%d" % (stamp, n)), n + 1
    stamp = folder.name[len("merge_"):]
    (folder / "inputs").mkdir(parents=True)
    # XDS splits keyword values at blanks and has a length limit on names, so
    # each reflection file is reached through a short name without spaces
    names = merge_input_names(plan)
    for row, local in zip(plan["inputs"], names):
        try:
            os.symlink(row["hkl"], str(folder / local))
        except (OSError, NotImplementedError, AttributeError):
            shutil.copy2(row["hkl"], str(folder / local))
    _write_inp(folder / "XSCALE.INP", merge_xscale_inp(plan, friedel, names))
    record = {"id": stamp, "folder": str(folder), "status": "running", "friedel": friedel,
              "reference": plan["reference"], "inputs": [r["project"] for r in plan["inputs"]],
              "excluded": plan["excluded"], "stats": {}, "error": ""}
    _merge_save(record)

    def run():
        log_lines = []
        exe = _find_xscale_exe(xds_runner.xds_path)
        try:
            rc, outcome = _run_streaming([str(exe)], folder, log_lines.append, expected_outputs=["XSCALE.LP"])
            status = "done" if outcome == "ok" else "failed"
            error = "" if outcome == "ok" else _outcome_message(outcome, "XSCALE")
            stats = {}
            lp = folder / "XSCALE.LP"
            if lp.is_file():
                parsed = LPParser.parse_xscale(_read_text_lenient(lp))
                for row in parsed.get("statistics_table") or []:
                    if str(row.get("resolution", "")).strip().lower() == "total":
                        stats = {k: row.get(k) for k in ("completeness", "r_meas", "i_sigma", "cc_half")}
                table = parsed.get("statistics_table") or []
                shells = [r for r in table if str(r.get("resolution", "")).strip().lower() != "total"]
                if shells:
                    stats["high_resolution"] = shells[-1].get("resolution")
        except Exception as exc:
            status, error, stats = "failed", "%s: %s" % (type(exc).__name__, exc), {}
        record.update({"status": status, "error": error, "stats": stats})
        _merge_save(record)

    threading.Thread(target=run, name="merge-" + stamp, daemon=True).start()
    return record
