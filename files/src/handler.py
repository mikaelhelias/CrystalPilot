
def _find_latest_lp(project_dir, step):
    """Find the most recently modified {step}.LP for a project.

    Looks in the folder of the last run (metadata last_run_folder, which may
    be outside the project), in the project folder, and in their immediate
    subdirectories.  Returns a Path or None."""
    lp_name = f"{step}.LP"
    out_dir = _project_out_dir(project_dir)
    # Fast path: the folder of the last run is the answer in almost every
    # case - one stat, no directory walk (a walk over a network share costs
    # seconds).  Only when it has no such file do we look around.
    direct = out_dir / lp_name
    if direct.exists():
        return direct
    candidates = []
    roots = [Path(project_dir)]
    if out_dir != Path(project_dir):
        roots.insert(0, out_dir)
    for root in roots:
        root_lp = root / lp_name
        if root_lp.exists():
            candidates.append(root_lp)
        try:
            for child in root.iterdir():
                if child.is_dir():
                    sub_lp = child / lp_name
                    if sub_lp.exists():
                        candidates.append(sub_lp)
        except OSError:
            pass
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _figure_source(project_dir, source="CORRECT"):
    """(log to read, folder to write figures into) for a figure request.

    The figures belong next to the log they were made from, so a re-run does
    not leave last week's curves behind in another folder.  XSCALE may have run
    in an XSCALE_NNN sub-folder: the newest XSCALE.LP wins, the same rule the
    XSCALE LP viewer uses.
    """
    project_dir = Path(project_dir)
    if str(source).upper() == "XSCALE":
        candidates = []
        root_lp = _pfile(project_dir, "XSCALE.LP", "xscale")
        if root_lp.exists():
            candidates.append(root_lp)
        try:
            for child in project_dir.iterdir():
                if child.is_dir() and child.name.startswith("XSCALE_"):
                    sub_lp = child / "XSCALE.LP"
                    if sub_lp.exists():
                        candidates.append(sub_lp)
        except OSError:
            pass
        if not candidates:
            return _pfile(project_dir, "XSCALE.LP", "xscale"), _project_out_dir(project_dir, "xscale")
        lp = max(candidates, key=lambda p: p.stat().st_mtime)
        return lp, lp.parent
    lp = _find_latest_lp(project_dir, "CORRECT")
    if lp is None:
        return _pfile(project_dir, "CORRECT.LP"), _project_out_dir(project_dir)
    return lp, lp.parent


def _environment_report():
    """What CrystalPilot can find on this computer (for the first-launch screen)."""
    import platform as _plat
    import shutil as _sh
    checks = []

    # Python packages for the frame viewer (matplotlib also draws the figures)
    missing = _check_deps()
    # Named one by one so the page can gate a single feature on a single module:
    # the Figures button is disabled when matplotlib is absent instead of
    # letting the click come back as a 503.
    absent = {e[3] for e in missing}
    modules = {e[3]: (e[3] not in absent) for e in _DEPS}
    if missing:
        checks.append({"id": "python", "status": "warn", "title": "Python packages for the frame viewer",
                       "detail": "Missing: " + ", ".join(e[3] for e in missing) + ". Needed to display frames and to read HDF5 headers.",
                       "action": "install_deps", "pip": " ".join(e[2] for e in missing)})
    else:
        checks.append({"id": "python", "status": "ok", "title": "Python packages for the frame viewer",
                       "detail": "numpy, matplotlib, h5py, hdf5plugin, fabio are installed"})

    # XDS
    xds_path = Path(xds_runner.xds_path)
    def _find(names):
        for n in names:
            p = xds_path / n
            if p.exists():
                return str(p)
        for n in names:
            f = _sh.which(n)
            if f:
                return f
        return None
    xds_exe = _find(("xds_par", "xds"))
    xscale_exe = _find(("xscale_par", "xscale"))
    xdsconv_exe = _find(("xdsconv",))
    if xds_exe and xscale_exe and xdsconv_exe:
        checks.append({"id": "xds", "status": "ok", "title": "XDS",
                       "detail": "Found in " + str(Path(xds_exe).parent), "path": str(Path(xds_exe).parent),
                       "action": "set_xds_path"})
    else:
        found = ", ".join(n for n, e in (("xds", xds_exe), ("xscale", xscale_exe), ("xdsconv", xdsconv_exe)) if e) or "nothing"
        checks.append({"id": "xds", "status": "missing", "title": "XDS",
                       "detail": "Not found in " + str(xds_path) + " (found: " + found + "). XDS is free for academic use; download the Linux package from its authors, unpack it, and enter the folder here.",
                       "path": str(xds_path), "action": "set_xds_path",
                       "link": "https://xds.mr.mpg.de/html_doc/downloading.html", "link_label": "XDS download page"})
    if xds_exe:
        par = _find(("xds_par",)) and _find(("xscale_par",))
        if par and not XDS_PARALLEL:
            checks.append({"id": "parallel", "status": "info", "title": "Parallel processing",
                           "detail": "Switched off in the XDS Config panel: the serial xds / xscale binaries will be used"})
        elif par:
            checks.append({"id": "parallel", "status": "ok", "title": "Parallel processing",
                           "detail": "xds_par and xscale_par are present (multi-core)"})
        else:
            checks.append({"id": "parallel", "status": "warn", "title": "Parallel processing",
                           "detail": "Only the serial xds / xscale binaries were found; processing will use one core"})
        helpers = [n for n in ("forkxds", "mcolspot", "mintegrate") if not (xds_path / n).exists() and not _sh.which(n)]
        if helpers:
            checks.append({"id": "helpers", "status": "warn", "title": "XDS helper programs",
                           "detail": "Missing: " + ", ".join(helpers) + " (xds_par needs them for COLSPOT and INTEGRATE)"})

    # neggia
    # neggia: configured path, else next to the XDS binaries (the folder the
    # user may just have set), else the usual system locations
    neg = NEGGIA_LIB if (NEGGIA_LIB and Path(NEGGIA_LIB).exists()) else ''
    gone = NEGGIA_LIB if (NEGGIA_LIB and not neg) else ''
    if not neg:
        for _n in ('dectris-neggia.so', 'dectris-neggia.dylib'):
            if (xds_path / _n).exists():
                neg = str(xds_path / _n); break
    if not neg:
        neg = _find_neggia()
    if neg and Path(neg).exists():
        checks.append({"id": "neggia", "status": "ok", "title": "Eiger HDF5 reader (dectris-neggia)",
                       "detail": neg, "path": neg, "action": "set_neggia_path"})
    else:
        checks.append({"id": "neggia", "status": "warn", "title": "Eiger HDF5 reader (dectris-neggia)",
                       "detail": ("The library set here is no longer at " + gone + " - enter its path again.") if gone else
                                 "Not found. Only needed for Eiger .h5 data: download dectris-neggia.so from DECTRIS and place it next to xds_par, or enter its path here.",
                       "path": gone, "action": "set_neggia_path",
                       "link": "https://github.com/dectris/neggia/releases", "link_label": "neggia releases"})

    # CCP4 (optional)
    ccp4 = CCP4_BIN or _find_ccp4_bin()
    if ccp4:
        found = {p: _ccp4_program(p, ccp4) for p in CCP4_PROGRAMS}
        miss = [p for p in CCP4_PROGRAMS if not found[p][0]]
        windows = any(found[p][1] == "windows" for p in CCP4_PROGRAMS)
        checks.append({"id": "ccp4", "status": "ok" if not miss else "warn", "title": "CCP4 (optional)",
                       "detail": ("Found in " + ccp4) + (" (CCP4 for Windows, run through WSL)" if windows else "")
                                 + ("; not usable: " + "; ".join(found[p][2] for p in miss) if miss else ""),
                       "path": ccp4, "action": "set_ccp4_path"})
    else:
        checks.append({"id": "ccp4", "status": "warn", "title": "CCP4 (optional)",
                       "detail": ("The saved CCP4 folder " + CCP4_BIN_SAVED + " holds no CCP4 programs any more. "
                                  if CCP4_BIN_SAVED and not _is_ccp4_bin(CCP4_BIN_SAVED) else "") +
                                 "Not found. XDS processing works without it. CCP4 adds POINTLESS, AIMLESS, CTRUNCATE and MTZ export. "
                                 "It is searched for on PATH, in $CCP4/$CBIN and in the usual folders - if it lives somewhere else "
                                 "(CCP4 9 is unpacked wherever you like), enter its folder here.",
                       "path": "", "action": "set_ccp4_path",
                       "link": "https://www.ccp4.ac.uk/download/", "link_label": "CCP4 download page"})

    _pw = _windows_view(str(PROJECTS_DIR))
    checks.append({"id": "projects", "status": "info", "title": "Projects folder",
                   "detail": str(PROJECTS_DIR.resolve()) + ((" - from Windows: " + _pw) if _pw else ""),
                   "path": str(PROJECTS_DIR.resolve()), "action": "open_folder"})
    if IS_WSL:
        checks.append({"id": "wsl", "status": "info", "title": "Windows Subsystem for Linux",
                       "detail": "CrystalPilot runs inside Ubuntu on WSL. Windows drives are under /mnt/c, /mnt/d, ... - every drive connected at start is mounted, and a Windows path pasted into the file browser (D:\\data\\...) is opened directly."})

    fingerprint = "|".join(c["id"] + ":" + c["status"] for c in checks)
    return {"version": VERSION,
            "platform": {"system": _plat.system(), "release": _plat.release(), "is_wsl": IS_WSL,
                         "python": _plat.python_version()},
            "xds_path": str(xds_path), "projects_dir": str(PROJECTS_DIR.resolve()),
            "checks": checks, "fingerprint": fingerprint, "modules": modules,
            "log_file": (str(LOG_PATH) if LOG_PATH else ""),
            "report_email": REPORT_EMAIL,
            "all_ok": not any(c["status"] == "missing" for c in checks)}


def _table1_rpim_for(result):
    """Exact R-pim for the log Table 1 is built from, or the reason it is withheld."""
    primary = result.get("xscale") if (result.get("xscale") or {}).get("statistics_table") else result.get("correct")
    primary = primary or {}
    table, source = primary.get("statistics_table"), primary.get("source")
    if not table or not source:
        return {"overall": None, "outer": None, "reason": "no statistics table"}
    ok, info = _check_gemmi()
    if not ok:
        return {"overall": None, "outer": None, "reason": "gemmi is not installed"}
    lp = Path(source)
    candidates = []
    if lp.name == "CORRECT.LP":
        candidates = [lp.parent / "XDS_ASCII.HKL"]
    elif lp.name == "XSCALE.LP":
        try:
            inp = (lp.parent / "XSCALE.INP").read_text(encoding="utf-8", errors="replace")
        except OSError:
            inp = ""
        for line in inp.splitlines():
            line = line.split("!")[0].strip()
            if line.upper().startswith("OUTPUT_FILE=") and line.split("=", 1)[1].split():
                candidates.insert(0, lp.parent / line.split("=", 1)[1].split()[0])
    else:
        return {"overall": None, "outer": None,
                "reason": "an earlier log: its reflection file has been overwritten"}
    reason = "reflection file not found next to %s" % lp.name
    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            got = table1_rpim(cand, table)
        except Exception as exc:
            reason = "%s could not be read: %s" % (cand.name, exc)
            continue
        if got.get("overall") or got.get("outer") or got.get("d_low"):
            return got
        reason = got.get("reason") or reason
    return {"overall": None, "outer": None, "reason": reason}


class XDSGUIHandler(BaseHTTPRequestHandler):
    """HTTP request handler"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def send_response(self, code, message=None):
        # Remember that headers went out: after that an error can only be logged,
        # not turned into a JSON reply (see _guarded).
        self._headers_sent = True
        super().send_response(code, message)

    def _token_cookie_name(self):
        try:
            return "cp_token_%d" % int(self.server.server_address[1])
        except Exception:
            return "cp_token"

    @staticmethod
    def _public_path(path):
        return path in ("/", "/index.html", "/favicon.ico", "/health", "/manual") or path.startswith(("/assets/", "/manual/"))

    @staticmethod
    def _project_route(path):
        parts = path.split("/")
        if len(parts) >= 4 and parts[:3] == ["", "api", "projects"] and all(parts[3:]):
            return "/" + "/".join(parts[4:]) if len(parts) > 4 else ""
        return None

    def _authorized(self):
        """Every /api request must carry the per-launch token: header
        X-CrystalPilot-Token, query ?token=, or the SameSite cookie set when
        the page was served.  Other web sites cannot obtain any of the three,
        so they cannot drive the API from the user's browser."""
        parsed = urllib.parse.urlparse(self.path)
        if self.command == "GET" and self._public_path(parsed.path):
            return True
        tok = (self.headers.get("X-CrystalPilot-Token") or "").strip()
        if not tok:
            tok = (urllib.parse.parse_qs(parsed.query).get("token", [""])[0] or "").strip()
        if not tok:
            raw = self.headers.get("Cookie", "") or ""
            want = self._token_cookie_name() + "="
            for part in raw.split(";"):
                part = part.strip()
                if part.startswith(want):
                    tok = urllib.parse.unquote(part[len(want):]).strip()
                    break
        return bool(tok) and hmac.compare_digest(tok, API_TOKEN)

    def _host_allowed(self):
        """DNS rebinding: another web site can point its own name at 127.0.0.1 and
        load this page under that name - the browser then hands it the page and
        its token cookie.  A server bound to a loopback address therefore answers
        only requests addressed to a loopback name (localhost, 127.x.x.x, [::1],
        *.localhost) or to a name listed in XDS_GUI_ALLOWED_HOSTS.  A server
        opened to the network (--host 0.0.0.0 or an address) is reached by
        whatever name the network gives it and keeps relying on the token."""
        bound = str(HOST or "").strip().lower()
        if bound not in ("127.0.0.1", "localhost", "::1") and not bound.startswith("127."):
            return True
        raw = (self.headers.get("Host") or "").strip().lower()
        if not raw:
            return True                      # HTTP/1.0 clients send none; a browser always does
        if raw.startswith("["):
            name = raw[1:raw.find("]")] if "]" in raw else raw[1:]
        else:
            name = raw.rsplit(":", 1)[0] if raw.count(":") == 1 else raw
        extra = [h.strip().lower() for h in os.environ.get("XDS_GUI_ALLOWED_HOSTS", "").split(",") if h.strip()]
        return (name in ("localhost", "::1", bound) or name.startswith("127.") or name.endswith(".localhost")
                or name in extra)

    def _refuse_outside(self, *paths, base=None):
        """--restrict-browse: every path a request names must lie inside the projects
        folder (after resolving links and '..').  Sends 403 and returns True when
        one does not.  Relative paths are taken relative to `base` (a project
        folder), else to the projects folder; XDS '?' templates count as files."""
        if not RESTRICT_BROWSE:
            return False
        root = PROJECTS_DIR.resolve()
        for raw in paths:
            s = str(raw or "").strip()
            if not s:
                continue
            candidate = Path(s.replace("?", "0"))
            if not candidate.is_absolute():
                candidate = Path(base or root) / candidate
            try:
                candidate = candidate.resolve()
            except (OSError, RuntimeError):
                candidate = Path(os.path.abspath(str(candidate)))
            if candidate != root and root not in candidate.parents:
                self.send_json({"error": "This installation only works inside the projects folder (--restrict-browse)"}, 403)
                return True
        return False

    def _guarded(self, fn):
        """Run a request handler; an unexpected exception becomes a JSON 400/500
        instead of a traceback on the console and a dropped connection."""
        self._headers_sent = False
        self._stream_terminal = None
        try:
            if not self._host_allowed():
                self.send_json({"error": "Refused: this CrystalPilot answers only requests addressed to localhost "
                                         "(set XDS_GUI_ALLOWED_HOSTS to add a name)"}, 403)
                return
            request_path = urllib.parse.urlparse(self.path).path
            if not request_path.startswith("/api/") and not (self.command == "GET" and self._public_path(request_path)):
                self.send_json({"error": "Not found"}, 404)
                return
            if not self._authorized():
                self.send_json({"error": "Not authorised: this CrystalPilot instance only answers the browser tab that opened it (or requests carrying its token, see the console banner)"}, 403)
                return
            fn()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            if getattr(self, "_headers_sent", False):
                if self._stream_terminal:
                    event = "ap_error" if self._stream_terminal == "ap_done" else "error_msg"
                    message = str(e) or type(e).__name__
                    try:
                        payload = "event: " + event + "\ndata: " + json.dumps({"message": message}) + "\n\n"
                        payload += "event: " + self._stream_terminal + "\ndata: " + json.dumps({"status": "error", "message": message}) + "\n\n"
                        self.wfile.write(payload.encode()); self.wfile.flush()
                    except (OSError, ValueError):
                        pass
                try:
                    print(f"[request] {self.command} {self.path}: {type(e).__name__}: {e}")
                except Exception:
                    pass
                return
            status = 409 if isinstance(e, DirectoryBusyError) else (404 if isinstance(e, FileNotFoundError) else (400 if isinstance(e, (ValueError, KeyError)) else 500))
            msg = str(e) if not isinstance(e, KeyError) else f"Missing field: {e}"
            self.send_json({"error": msg or type(e).__name__}, status)

    def _begin_processing_stream(self, project_name, terminal="done"):
        """Validate before headers; later failures use the stream's terminal event.

        A browser's EventSource can show neither the status code nor the body, so
        a plain 404 for a missing project reached the reader as "connection
        closed" and nothing else.  It says what it is (the standard requires
        ``Accept: text/event-stream``), so for that client the stream is opened
        and the failure travels as its own error event - which is what the log
        shows.  A script, which can read a status, still gets the 404.  Either
        way nothing has started, so no work is left behind.
        """
        def open_stream():
            self._stream_terminal = terminal
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
        try:
            ProjectManager.get(project_name)
        except FileNotFoundError:
            if "text/event-stream" in (self.headers.get("Accept") or ""):
                open_stream()
            raise
        open_stream()

    @staticmethod
    def _batch_path_allowed(target):
        """--restrict-browse keeps the AutoPilot wizard inside the projects folder too."""
        if not RESTRICT_BROWSE:
            return True
        root = PROJECTS_DIR.resolve()
        try:
            target = Path(target).resolve()
        except (OSError, RuntimeError):
            return False
        return target == root or root in target.parents

    def send_json(self, data, status=200, extra_headers=None):
        """Send JSON response"""
        try:
            payload = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            for k, v in (extra_headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
    
    def send_html(self, html):
        """Send HTML response"""
        try:
            payload = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            # The tab that loads the page gets the API token as a SameSite
            # cookie (name includes the port so two instances do not clash).
            self.send_header("Set-Cookie", "%s=%s; Path=/; SameSite=Strict" % (self._token_cookie_name(), API_TOKEN))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
    
    def _serve_asset(self, filename):
        """Serve a static asset from the embedded STATIC_ASSETS dict"""
        try:
            asset = STATIC_ASSETS.get(filename)
            if asset is None:
                self.send_response(404)
                self.end_headers()
                return
            content_type, data = asset
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        try:
            self.send_response(200)
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
    
    def do_GET(self):
        self._guarded(self._do_GET)

    def _do_GET(self):
        """Handle GET requests"""
        global MISSING_DEPS, VIEWER_READY, CCP4_BIN, NEGGIA_LIB
        path = urllib.parse.urlparse(self.path).path
        project_route = self._project_route(path)
        
        # Root - serve frontend
        if path == "/" or path == "/index.html":
            self.send_html(get_frontend_html())
        
        # Favicon - return empty 204 to suppress browser 404
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        
        # Serve static assets (images shipped alongside the script)
        elif path.startswith("/assets/"):
            self._serve_asset(path[len("/assets/"):])
        
        # The illustrated manual (docs/manual next to the application, or in the
        # source tree), served like the assets: no token, files of that folder only.
        elif path.startswith("/manual/") or path == "/manual":
            rel = urllib.parse.unquote(path[len("/manual/"):]) if path.startswith("/manual/") else ""
            here = Path(__file__).resolve().parent
            roots = [here / "docs" / "manual", here.parent / "docs" / "manual", here.parent.parent / "docs" / "manual"]
            base = next((r for r in roots if r.is_dir()), None)
            if not rel:   # /manual or /manual/ : what is available (the Docs tab asks this)
                self.send_json({"available": bool(base and (base / "CrystalPilot-Manual.html").is_file()),
                                "html": bool(base and (base / "CrystalPilot-Manual.html").is_file()),
                                "pdf": bool(base and (base / "CrystalPilot-Manual.pdf").is_file()),
                                "index": bool(base and (base / "CrystalPilot-Manual.index.json").is_file()),
                                "folder": str(base) if base else ""})
                return
            target = (base / rel).resolve() if base else None
            if base is None or target is None or base.resolve() not in target.parents or not target.is_file():
                self.send_json({"error": "The illustrated manual is not installed next to the application (docs/manual)"}, 404)
                return
            ctype = {".html": "text/html; charset=utf-8", ".pdf": "application/pdf", ".png": "image/png", ".md": "text/plain; charset=utf-8",
                     ".jpg": "image/jpeg", ".css": "text/css", ".js": "application/javascript", ".json": "application/json; charset=utf-8"}.get(target.suffix.lower(), "application/octet-stream")
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        # Health check
        elif path == "/health":
            # Readable from any origin: the Windows loading screen (a local
            # file) polls it to know when to switch to the interface.  It
            # carries no data worth protecting.
            self.send_json({"status": "ok", "version": VERSION, "app": "CrystalPilot"},
                           extra_headers={"Access-Control-Allow-Origin": "*"})
        
        # List projects
        elif path == "/api/projects":
            self.send_json(ProjectManager.list_all())
        
        # Get project
        elif project_route == "":
            name = _url_project_name(path.split("/")[-1])
            try:
                meta = ProjectManager.get(name)
                # Where this project's XDS output currently lives (single source of truth)
                meta["output_dir"] = str(_project_out_dir(_pdir(name)))
                self.send_json(meta)
            except FileNotFoundError:
                self.send_json({"error": "Project not found"}, 404)
        
        # Get LP file
        elif re.fullmatch('/lp/[^/]+', project_route or ""):
            parts = path.split("/")
            name, step = _url_project_name(parts[3]), parts[5]
            lp_file = _find_latest_lp(_pdir(name), step)
            try:
                if lp_file:
                    self.send_json({"step": step, "content": _read_text_lenient(lp_file), "source": str(lp_file)})
                else:
                    self.send_json({"error": "LP file not found"}, 404)
            except Exception as e:
                self.send_json({"error": f"Failed to read LP file: {e}"}, 500)
        
        # Where does this project read/write its files right now?
        elif project_route == '/locations':
            name = _url_project_name(path.split("/")[3])
            try:
                self.send_json(_project_locations(_pdir(name)))
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Get parsed metrics from LP file
        elif re.fullmatch('/metrics/[^/]+', project_route or ""):
            parts = path.split("/")
            name, step = _url_project_name(parts[3]), parts[5]
            lp_file = _find_latest_lp(_pdir(name), step)
            try:
                if lp_file:
                    content = _read_text_lenient(lp_file)
                    if step == "IDXREF":
                        metrics = LPParser.parse_idxref(content)
                        self.send_json({"step": step, "metrics": metrics})
                    elif step == "CORRECT":
                        metrics = LPParser.parse_correct(content)
                        self.send_json({"step": step, "metrics": metrics})
                    elif step == "INTEGRATE":
                        metrics = LPParser.parse_integrate(content)
                        self.send_json({"step": step, "metrics": metrics})
                    elif step == "COLSPOT":
                        metrics = LPParser.parse_colspot(content)
                        self.send_json({"step": step, "metrics": metrics})
                    elif step == "INIT":
                        metrics = LPParser.parse_init(content)
                        self.send_json({"step": step, "metrics": metrics})
                    else:
                        self.send_json({"step": step, "metrics": {}})
                else:
                    self.send_json({"error": "LP file not found"}, 404)
            except Exception as e:
                self.send_json({"error": f"Failed to read metrics: {e}"}, 500)
        
        # Matthews coefficient calculator
        elif project_route == '/matthews':
            try:
                name = _url_project_name(path.split("/")[3])
                from urllib.parse import parse_qs, urlparse
                qs = parse_qs(urlparse(self.path).query)
                mw = float(qs.get("mw", [0])[0])
                if mw <= 0:
                    self.send_json({"error": "Molecular weight must be positive"}, 400)
                    return
                lp_file = _pfile(_pdir(name), "CORRECT.LP")
                if not lp_file.exists():
                    self.send_json({"error": "CORRECT.LP not found. Run CORRECT first."}, 404)
                    return
                content = _read_text_lenient(lp_file)
                metrics = LPParser.parse_correct(content)
                uc = metrics.get("unit_cell")
                sg = metrics.get("space_group")
                if not uc or not sg:
                    self.send_json({"error": "Unit cell or space group not found in CORRECT.LP"}, 400)
                    return
                results = LPParser.matthews_coefficient(uc, sg, mw)
                if not results:
                    self.send_json({"error": "Could not calculate Matthews coefficient"}, 400)
                    return
                self.send_json({"results": results, "unit_cell": uc, "space_group": sg})
            except ValueError:
                self.send_json({"error": "Invalid molecular weight"}, 400)
            except Exception as e:
                self.send_json({"error": f"Matthews calculation failed: {e}"}, 500)

        # Get BEAM_DIVERGENCE and REFLECTING_RANGE from INTEGRATE.LP
        elif project_route == '/integrate-params':
            try:
                name = _url_project_name(path.split("/")[3])
                lp_file = _pfile(_pdir(name), "INTEGRATE.LP")
                if not lp_file.exists():
                    self.send_json({"error": "INTEGRATE.LP not found"}, 404)
                    return
                content = _read_text_lenient(lp_file)
                metrics = LPParser.parse_integrate(content)
                params = {}
                if 'beam_divergence' in metrics:
                    params['beam_divergence'] = metrics['beam_divergence']
                if 'beam_divergence_esd' in metrics:
                    params['beam_divergence_esd'] = metrics['beam_divergence_esd']
                if 'reflecting_range' in metrics:
                    params['reflecting_range'] = metrics['reflecting_range']
                if 'reflecting_range_esd' in metrics:
                    params['reflecting_range_esd'] = metrics['reflecting_range_esd']
                self.send_json({"params": params})
            except Exception as e:
                self.send_json({"error": f"Failed to read INTEGRATE.LP: {e}"}, 500)

        # Compare current CORRECT.LP with previous run (CORRECT.LP.prev)
        elif project_route == '/compare-correct':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                current_lp = _pfile(project_dir, "CORRECT.LP")
                prev_lp = _pfile(project_dir, "CORRECT.LP.prev1")
                if not prev_lp.exists():
                    prev_lp = _pfile(project_dir, "CORRECT.LP.prev")   # legacy name
                if not current_lp.exists():
                    self.send_json({"error": "CORRECT.LP not found"}, 404)
                    return
                if not prev_lp.exists():
                    self.send_json({"error": "No previous CORRECT.LP.prev found. Run CORRECT at least twice to compare."}, 404)
                    return
                cur_content = current_lp.read_text(encoding="utf-8", errors="replace")
                prev_content = prev_lp.read_text(encoding="utf-8", errors="replace")
                cur_metrics = LPParser.parse_correct(cur_content)
                prev_metrics = LPParser.parse_correct(prev_content)
                # Extract compact summary for comparison
                def _summarize(m):
                    s = {}
                    s['space_group'] = m.get('space_group', '')
                    uc = m.get('unit_cell')
                    if uc:
                        s['unit_cell'] = [uc.get('a',0), uc.get('b',0), uc.get('c',0),
                                          uc.get('alpha',0), uc.get('beta',0), uc.get('gamma',0)]
                    isa = m.get('isa')
                    if isa:
                        s['isa'] = isa.get('isa', '')
                    wl = m.get('wilson_line')
                    if wl:
                        s['wilson_b'] = wl.get('b', '')
                    s['chi2_values'] = m.get('chi2_values', [])
                    s['mosaicity'] = m.get('mosaicity', '')
                    fl = m.get('friedels_law', '')
                    if fl:
                        s['friedels_law'] = fl
                    tbl = m.get('statistics_table', [])
                    if tbl:
                        def _shell_keys(row):
                            return {
                                'resolution': row.get('resolution', ''),
                                'completeness': row.get('completeness', ''),
                                'r_meas': row.get('r_meas', ''),
                                'i_sigma': row.get('i_sigma', ''),
                                'cc_half': row.get('cc_half', ''),
                                'r_obs': row.get('r_obs', ''),
                                'siganom': row.get('siganom', ''),
                            }
                        # Separate total row from resolution shells
                        shells = [r for r in tbl if r.get('resolution','').lower() != 'total']
                        total = [r for r in tbl if r.get('resolution','').lower() == 'total']
                        if total:
                            s['overall'] = _shell_keys(total[0])
                        elif shells:
                            s['overall'] = _shell_keys(shells[0])
                        if len(shells) >= 1:
                            s['inner'] = _shell_keys(shells[0])
                        if len(shells) >= 2:
                            s['outer'] = _shell_keys(shells[-1])
                    return s
                prev_time = os.path.getmtime(str(prev_lp))
                cur_time = os.path.getmtime(str(current_lp))
                self.send_json({
                    "current": _summarize(cur_metrics),
                    "current_time": datetime.fromtimestamp(cur_time).strftime("%Y-%m-%d %H:%M"),
                    "previous": _summarize(prev_metrics),
                    "previous_time": datetime.fromtimestamp(prev_time).strftime("%Y-%m-%d %H:%M"),
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Compare current IDXREF.LP with previous run (IDXREF.LP.prev)
        elif project_route == '/compare-idxref':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                current_lp = _pfile(project_dir, "IDXREF.LP")
                prev_lp = _pfile(project_dir, "IDXREF.LP.prev1")
                if not prev_lp.exists():
                    prev_lp = _pfile(project_dir, "IDXREF.LP.prev")    # legacy name
                if not current_lp.exists():
                    self.send_json({"error": "IDXREF.LP not found"}, 404)
                    return
                if not prev_lp.exists():
                    self.send_json({"error": "No previous IDXREF.LP.prev found. Run IDXREF at least twice to compare."}, 404)
                    return
                cur_content = current_lp.read_text(encoding="utf-8", errors="replace")
                prev_content = prev_lp.read_text(encoding="utf-8", errors="replace")
                cur_metrics = LPParser.parse_idxref(cur_content)
                prev_metrics = LPParser.parse_idxref(prev_content)
                def _summarize_idx(m):
                    s = {}
                    if m.get('indexed_count') is not None and m.get('total_spots') is not None:
                        s['indexed_count'] = m['indexed_count']
                        s['total_spots'] = m['total_spots']
                        s['indexed_pct'] = round(m['indexed_count'] / m['total_spots'] * 100, 1) if m['total_spots'] > 0 else 0
                    for k in ('sigma_spot', 'sigma_spindle', 'orgx', 'orgy', 'detector_distance',
                              'orgx_initial', 'orgy_initial', 'detector_distance_initial'):
                        if m.get(k) is not None:
                            s[k] = m[k]
                    lats = m.get('lattices', [])
                    if lats:
                        sel = lats[0]
                        s['lattice'] = sel.get('bravais', '')
                        s['quality'] = sel.get('quality', '')
                        s['unit_cell'] = [sel.get('a',''), sel.get('b',''), sel.get('c',''),
                                          sel.get('alpha',''), sel.get('beta',''), sel.get('gamma','')]
                    return s
                prev_time = os.path.getmtime(str(prev_lp))
                cur_time = os.path.getmtime(str(current_lp))
                self.send_json({
                    "current": _summarize_idx(cur_metrics),
                    "current_time": datetime.fromtimestamp(cur_time).strftime("%Y-%m-%d %H:%M"),
                    "previous": _summarize_idx(prev_metrics),
                    "previous_time": datetime.fromtimestamp(prev_time).strftime("%Y-%m-%d %H:%M"),
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Compare current XSCALE.LP with previous run (XSCALE.LP.prev)
        elif project_route == '/compare-xscale':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                # Find most recent XSCALE.LP (same logic as xscalelp endpoint)
                candidates = []
                root_lp = _pfile(project_dir, "XSCALE.LP", "xscale")
                if root_lp.exists():
                    candidates.append(root_lp)
                try:
                    for child in project_dir.iterdir():
                        if child.is_dir() and child.name.startswith("XSCALE_"):
                            sub_lp = child / "XSCALE.LP"
                            if sub_lp.exists():
                                candidates.append(sub_lp)
                except OSError:
                    pass
                if not candidates:
                    self.send_json({"error": "XSCALE.LP not found"}, 404)
                    return
                current_lp = max(candidates, key=lambda p: p.stat().st_mtime)
                prev_lp = current_lp.parent / "XSCALE.LP.prev1"
                if not prev_lp.exists():
                    prev_lp = current_lp.parent / "XSCALE.LP.prev"     # legacy name
                if not prev_lp.exists():
                    self.send_json({"error": "No previous XSCALE.LP.prev found. Run XSCALE at least twice to compare."}, 404)
                    return
                cur_content = current_lp.read_text(encoding="utf-8", errors="replace")
                prev_content = prev_lp.read_text(encoding="utf-8", errors="replace")
                cur_metrics = LPParser.parse_xscale(cur_content)
                prev_metrics = LPParser.parse_xscale(prev_content)
                def _summarize_xs(m):
                    s = {}
                    s['space_group'] = m.get('space_group', '')
                    uc = m.get('unit_cell')
                    if uc:
                        s['unit_cell'] = [uc.get('a',0), uc.get('b',0), uc.get('c',0),
                                          uc.get('alpha',0), uc.get('beta',0), uc.get('gamma',0)]
                    fl = m.get('friedels_law', '')
                    if fl:
                        s['friedels_law'] = fl
                    # ISa from first dataset
                    isa_tbl = m.get('isa_table', [])
                    if isa_tbl:
                        s['isa'] = isa_tbl[0].get('isa', '')
                        s['isa0'] = isa_tbl[0].get('isa0', '')
                    tbl = m.get('statistics_table', [])
                    if tbl:
                        def _shell_keys(row):
                            return {
                                'resolution': row.get('resolution', ''),
                                'completeness': row.get('completeness', ''),
                                'r_meas': row.get('r_meas', ''),
                                'i_sigma': row.get('i_sigma', ''),
                                'cc_half': row.get('cc_half', ''),
                                'r_obs': row.get('r_obs', ''),
                                'siganom': row.get('siganom', ''),
                            }
                        shells = [r for r in tbl if r.get('resolution','').lower() != 'total']
                        total = [r for r in tbl if r.get('resolution','').lower() == 'total']
                        if total:
                            s['overall'] = _shell_keys(total[0])
                        elif shells:
                            s['overall'] = _shell_keys(shells[0])
                        if len(shells) >= 1:
                            s['inner'] = _shell_keys(shells[0])
                        if len(shells) >= 2:
                            s['outer'] = _shell_keys(shells[-1])
                    return s
                prev_time = os.path.getmtime(str(prev_lp))
                cur_time = os.path.getmtime(str(current_lp))
                self.send_json({
                    "current": _summarize_xs(cur_metrics),
                    "current_time": datetime.fromtimestamp(cur_time).strftime("%Y-%m-%d %H:%M"),
                    "previous": _summarize_xs(prev_metrics),
                    "previous_time": datetime.fromtimestamp(prev_time).strftime("%Y-%m-%d %H:%M"),
                    "source": str(current_lp),
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # History comparison: up to 5 runs for CORRECT
        elif project_route == '/history-correct':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                def _sk_c(row):
                    return {k: row.get(k, '') for k in ('resolution','completeness','r_meas','i_sigma','cc_half','r_obs','siganom')}
                def _sum_correct(content):
                    m = LPParser.parse_correct(content)
                    s = {}
                    s['space_group'] = m.get('space_group', '')
                    uc = m.get('unit_cell')
                    if uc:
                        s['unit_cell'] = [uc.get(k,0) for k in ('a','b','c','alpha','beta','gamma')]
                    isa = m.get('isa')
                    if isa: s['isa'] = isa.get('isa', '')
                    wl = m.get('wilson_line')
                    if wl: s['wilson_b'] = wl.get('b', '')
                    s['chi2_values'] = m.get('chi2_values', [])
                    s['mosaicity'] = m.get('mosaicity', '')
                    fl = m.get('friedels_law', '')
                    if fl: s['friedels_law'] = fl
                    tbl = m.get('statistics_table', [])
                    if tbl:
                        shells = [r for r in tbl if r.get('resolution','').lower() != 'total']
                        total = [r for r in tbl if r.get('resolution','').lower() == 'total']
                        if total: s['overall'] = _sk_c(total[0])
                        elif shells: s['overall'] = _sk_c(shells[0])
                        if len(shells) >= 1: s['inner'] = _sk_c(shells[0])
                        if len(shells) >= 2: s['outer'] = _sk_c(shells[-1])
                    return s
                runs = []
                current_lp = _pfile(project_dir, "CORRECT.LP")
                if current_lp.exists():
                    t = os.path.getmtime(str(current_lp))
                    runs.append({"label": "Current", "time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                                 "data": _sum_correct(current_lp.read_text(encoding="utf-8", errors="replace")),
                                 "source": str(current_lp)})
                # Collect prev1..prev4, also legacy .prev
                for suffix in [".prev1", ".prev2", ".prev3", ".prev4", ".prev"]:
                    pf = _pfile(project_dir, "CORRECT.LP" + suffix)
                    if pf.exists():
                        t = os.path.getmtime(str(pf))
                        lbl = suffix.replace(".", "").replace("prev", "Run -")
                        if suffix == ".prev": lbl = "Run -1 (legacy)"
                        runs.append({"label": lbl, "time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                                     "data": _sum_correct(pf.read_text(encoding="utf-8", errors="replace")),
                                     "source": str(pf)})
                if not runs:
                    self.send_json({"error": "No CORRECT.LP files found"}, 404)
                    return
                self.send_json({"runs": runs[:5]})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # History comparison: up to 5 runs for IDXREF
        elif project_route == '/history-idxref':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                def _sum_idxref(content):
                    m = LPParser.parse_idxref(content)
                    s = {}
                    if m.get('indexed_count') is not None and m.get('total_spots') is not None:
                        s['indexed_count'] = m['indexed_count']
                        s['total_spots'] = m['total_spots']
                        s['indexed_pct'] = round(m['indexed_count'] / m['total_spots'] * 100, 1) if m['total_spots'] > 0 else 0
                    for k in ('sigma_spot', 'sigma_spindle', 'orgx', 'orgy', 'detector_distance'):
                        if m.get(k) is not None: s[k] = m[k]
                    lats = m.get('lattices', [])
                    if lats:
                        sel = lats[0]
                        s['lattice'] = sel.get('bravais', '')
                        s['quality'] = sel.get('quality', '')
                        s['unit_cell'] = [sel.get('a',''), sel.get('b',''), sel.get('c',''),
                                          sel.get('alpha',''), sel.get('beta',''), sel.get('gamma','')]
                    return s
                runs = []
                current_lp = _pfile(project_dir, "IDXREF.LP")
                if current_lp.exists():
                    t = os.path.getmtime(str(current_lp))
                    runs.append({"label": "Current", "time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                                 "data": _sum_idxref(current_lp.read_text(encoding="utf-8", errors="replace")),
                                 "source": str(current_lp)})
                for suffix in [".prev1", ".prev2", ".prev3", ".prev4", ".prev"]:
                    pf = _pfile(project_dir, "IDXREF.LP" + suffix)
                    if pf.exists():
                        t = os.path.getmtime(str(pf))
                        lbl = suffix.replace(".", "").replace("prev", "Run -")
                        if suffix == ".prev": lbl = "Run -1 (legacy)"
                        runs.append({"label": lbl, "time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                                     "data": _sum_idxref(pf.read_text(encoding="utf-8", errors="replace")),
                                     "source": str(pf)})
                if not runs:
                    self.send_json({"error": "No IDXREF.LP files found"}, 404)
                    return
                self.send_json({"runs": runs[:5]})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # History comparison: up to 5 runs for XSCALE
        elif project_route == '/history-xscale':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                def _sk_x(row):
                    return {k: row.get(k, '') for k in ('resolution','completeness','r_meas','i_sigma','cc_half','r_obs','siganom')}
                def _sum_xscale(content):
                    m = LPParser.parse_xscale(content)
                    s = {}
                    s['space_group'] = m.get('space_group', '')
                    uc = m.get('unit_cell')
                    if uc:
                        s['unit_cell'] = [uc.get(k,0) for k in ('a','b','c','alpha','beta','gamma')]
                    fl = m.get('friedels_law', '')
                    if fl: s['friedels_law'] = fl
                    isa_tbl = m.get('isa_table', [])
                    if isa_tbl:
                        s['isa'] = isa_tbl[0].get('isa', '')
                        s['isa0'] = isa_tbl[0].get('isa0', '')
                    tbl = m.get('statistics_table', [])
                    if tbl:
                        shells = [r for r in tbl if r.get('resolution','').lower() != 'total']
                        total = [r for r in tbl if r.get('resolution','').lower() == 'total']
                        if total: s['overall'] = _sk_x(total[0])
                        elif shells: s['overall'] = _sk_x(shells[0])
                        if len(shells) >= 1: s['inner'] = _sk_x(shells[0])
                        if len(shells) >= 2: s['outer'] = _sk_x(shells[-1])
                    return s
                runs = []
                # Find current XSCALE.LP (most recent across subfolders)
                candidates = []
                root_lp = _pfile(project_dir, "XSCALE.LP", "xscale")
                if root_lp.exists(): candidates.append(root_lp)
                try:
                    for child in project_dir.iterdir():
                        if child.is_dir() and child.name.startswith("XSCALE_"):
                            sub_lp = child / "XSCALE.LP"
                            if sub_lp.exists(): candidates.append(sub_lp)
                except OSError: pass
                if candidates:
                    current_lp = max(candidates, key=lambda p: p.stat().st_mtime)
                    work_dir = current_lp.parent
                    t = os.path.getmtime(str(current_lp))
                    runs.append({"label": "Current", "time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                                 "data": _sum_xscale(current_lp.read_text(encoding="utf-8", errors="replace")),
                                 "source": str(current_lp)})
                    for suffix in [".prev1", ".prev2", ".prev3", ".prev4", ".prev"]:
                        pf = work_dir / ("XSCALE.LP" + suffix)
                        if pf.exists():
                            t = os.path.getmtime(str(pf))
                            lbl = suffix.replace(".", "").replace("prev", "Run -")
                            if suffix == ".prev": lbl = "Run -1 (legacy)"
                            runs.append({"label": lbl, "time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                                         "data": _sum_xscale(pf.read_text(encoding="utf-8", errors="replace")),
                                         "source": str(pf)})
                if not runs:
                    self.send_json({"error": "No XSCALE.LP files found"}, 404)
                    return
                self.send_json({"runs": runs[:5]})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Parse SPOT.XDS for indexed/unindexed spot visualization
        elif project_route == '/spot-data':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                spot_file = _pfile(project_dir, "SPOT.XDS")
                if not spot_file.exists():
                    self.send_json({"error": "SPOT.XDS not found"}, 404)
                    return
                indexed = []
                unindexed = []
                with open(spot_file, 'r', errors='replace') as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) < 4:
                            continue
                        try:
                            x = float(parts[0])
                            y = float(parts[1])
                            intensity = float(parts[3])
                        except (ValueError, IndexError):
                            continue
                        # After IDXREF: columns 7,8,9 are H,K,L; 0,0,0 = unindexed
                        if len(parts) >= 7:
                            try:
                                h, k, l = int(parts[-3]), int(parts[-2]), int(parts[-1])
                                if h == 0 and k == 0 and l == 0:
                                    unindexed.append([x, y, intensity])
                                else:
                                    indexed.append([x, y, intensity])
                            except (ValueError, IndexError):
                                unindexed.append([x, y, intensity])
                        else:
                            # Pre-IDXREF: no HKL columns, treat all as unclassified
                            unindexed.append([x, y, intensity])
                # Subsample if too many spots (keep all unindexed, subsample indexed)
                n_indexed_true = len(indexed)
                n_unindexed_true = len(unindexed)
                max_spots = 8000
                total = n_indexed_true + n_unindexed_true
                if total > max_spots:
                    # Always keep all unindexed (diagnostically important)
                    budget = max_spots - len(unindexed)
                    if budget > 0 and len(indexed) > budget:
                        import random
                        random.seed(42)
                        indexed = random.sample(indexed, budget)
                    elif budget <= 0:
                        # Even unindexed exceeds budget; subsample both
                        import random
                        random.seed(42)
                        half = max_spots // 2
                        if len(unindexed) > half:
                            unindexed = random.sample(unindexed, half)
                        budget2 = max_spots - len(unindexed)
                        if len(indexed) > budget2:
                            indexed = random.sample(indexed, budget2)
                # Get NX, NY from XDS.INP if available
                nx, ny = 0, 0
                qx, qy, wavelength_spot = 0.0, 0.0, 0.0
                xds_inp = project_dir / "XDS.INP"
                if xds_inp.exists():
                    try:
                        inp_text = xds_inp.read_text(encoding='utf-8', errors='replace')
                        for inp_line in inp_text.split('\n'):
                            ls = inp_line.split('!')[0].strip()
                            if not ls:
                                continue
                            ls_up = ls.upper()
                            for tok in ls.split():
                                tok_up = tok.upper()
                                if tok_up.startswith('NX='):
                                    try: nx = int(tok.split('=')[1])
                                    except Exception: pass
                                elif tok_up.startswith('NY='):
                                    try: ny = int(tok.split('=')[1])
                                    except Exception: pass
                                elif tok_up.startswith('QX='):
                                    try: qx = float(tok.split('=')[1])
                                    except Exception: pass
                                elif tok_up.startswith('QY='):
                                    try: qy = float(tok.split('=')[1])
                                    except Exception: pass
                            if ls_up.startswith('X-RAY_WAVELENGTH='):
                                try: wavelength_spot = float(ls.split('=', 1)[1].strip().split()[0])
                                except Exception: pass
                    except Exception:
                        pass
                self.send_json({
                    "indexed": indexed,
                    "unindexed": unindexed,
                    "n_indexed": n_indexed_true,
                    "n_unindexed": n_unindexed_true,
                    "nx": nx, "ny": ny,
                    "qx": qx, "qy": qy,
                    "wavelength": wavelength_spot,
                    "total": n_indexed_true + n_unindexed_true
                })
            except Exception as e:
                self.send_json({"error": f"Failed to parse SPOT.XDS: {e}"}, 500)

        # Export chart data as CSV (no external dependencies)
        elif re.fullmatch('/export-data/[^/]+', project_route or ""):
            try:
                parts_list = path.split("/")
                name = parts_list[3]
                export_type = parts_list[-1]  # correct, integrate
                project_dir = _pdir(name)
                import csv

                def make_csv(headers, rows):
                    buf = io.StringIO()
                    w = csv.writer(buf)
                    w.writerow(headers)
                    for r in rows:
                        w.writerow(r)
                    return buf.getvalue()

                sections = []  # list of (filename, csv_string)

                if export_type == 'correct':
                    lp_path = _pfile(project_dir, "CORRECT.LP")
                    if not lp_path.exists():
                        self.send_json({"error": "CORRECT.LP not found"}, 404)
                        return
                    with open(lp_path, 'r', errors='replace') as f:
                        content = f.read()
                    m = LPParser.parse_correct(content)

                    if m.get('statistics_table'):
                        sections.append(('statistics', make_csv(
                            ['Resolution', 'Observed', 'Unique', 'Possible', 'Completeness%', 'R_obs%', 'R_exp%', 'Compared', 'I/sigma', 'R_meas%', 'CC1/2', 'AnoCorr', 'SigAno', 'Nano'],
                            [[r.get('resolution',''), r.get('observed',''), r.get('unique',''), r.get('possible',''),
                              r.get('completeness',''), r.get('r_obs',''), r.get('r_exp',''), r.get('compared',''),
                              r.get('i_sigma',''), r.get('r_meas',''), r.get('cc_half',''),
                              r.get('anomal_corr',''), r.get('siganom',''), r.get('nano','')]
                             for r in m['statistics_table']])))
                    if m.get('wilson_table_raw'):
                        wrows = list(m['wilson_table_raw'])
                        if m.get('wilson_line'):
                            wrows.append([])
                            wrows.append(['# Wilson fit', 'A=', m['wilson_line']['a'], 'B=', m['wilson_line']['b'], 'Corr=', m['wilson_line']['correlation']])
                        sections.append(('wilson_plot', make_csv(
                            ['#Reflections', 'Resolution_d(A)', 'sin2theta_lambda2', 'MeanI', 'ln_MeanI', 'Local_B'],
                            wrows)))
                    if m.get('wilson_moments'):
                        sections.append(('wilson_moments', make_csv(
                            ['#Reflections', 'Resolution_d(A)', 'I2_moment', 'I3_moment', 'I4_moment'],
                            m['wilson_moments'])))
                    if m.get('aliens'):
                        sections.append(('aliens', make_csv(
                            ['h', 'k', 'l', 'Resolution_d(A)', 'Z_score'],
                            [[a['h'], a['k'], a['l'], a['res'], a['z']] for a in m['aliens']])))

                elif export_type == 'integrate':
                    lp_path = _pfile(project_dir, "INTEGRATE.LP")
                    if not lp_path.exists():
                        self.send_json({"error": "INTEGRATE.LP not found"}, 404)
                        return
                    with open(lp_path, 'r', errors='replace') as f:
                        content = f.read()
                    m = LPParser.parse_integrate(content)
                    if m.get('image_stats'):
                        irows = [[s['image'], s['ier'], s['scale'], s['novl'], s['nstrong'], s['nrej'], s['sigmab'], s['sigmar']] for s in m['image_stats']]
                        if m.get('mosaicity') is not None:
                            irows.append([])
                            irows.append(['# Final mosaicity (SIGMAR)', m['mosaicity']])
                        if m.get('beam_divergence') is not None:
                            irows.append(['# Beam divergence', m['beam_divergence']])
                        sections.append(('frame_statistics', make_csv(
                            ['Frame', 'IER', 'Scale', 'Overloads', 'Strong', 'Rejected', 'SIGMAB(deg)', 'SIGMAR(deg)'],
                            irows)))
                else:
                    self.send_json({"error": f"Unknown export type: {export_type}"}, 400)
                    return

                if not sections:
                    self.send_json({"error": "No data found to export"}, 404)
                    return

                # If single section, serve as plain CSV; if multiple, combine with section headers
                if len(sections) == 1:
                    csv_data = sections[0][1].encode('utf-8')
                    fname = f"{name}_{export_type}_{sections[0][0]}.csv"
                else:
                    combined = io.StringIO()
                    for i, (sec_name, csv_str) in enumerate(sections):
                        if i > 0:
                            combined.write('\n')
                        combined.write(f'### {sec_name.upper().replace("_", " ")} ###\n')
                        combined.write(csv_str)
                    csv_data = combined.getvalue().encode('utf-8')
                    fname = f"{name}_{export_type}_data.csv"

                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.send_header('Content-Length', str(len(csv_data)))
                self.end_headers()
                self.wfile.write(csv_data)
            except Exception as e:
                self.send_json({"error": f"Export failed: {e}"}, 500)
        
        # ── Ice Ring Detection ──────────────────────────────────────────
        elif project_route == '/ice-rings':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            try:
                lp_path = _find_latest_lp(project_dir, "CORRECT")
                if not lp_path:
                    self.send_json({"error": "CORRECT.LP not found — run CORRECT first"}, 404)
                    return
                content = lp_path.read_text(encoding="utf-8", errors="replace")
                m = LPParser.parse_correct(content)
                tbl = m.get('statistics_table', [])
                if not tbl:
                    self.send_json({"error": "No statistics table found in CORRECT.LP"}, 404)
                    return
                ice = LPParser.detect_ice_rings(tbl)
                # Also read current XDS.INP to report existing exclusions
                existing_excl = []
                xds_inp = project_dir / "XDS.INP"
                if xds_inp.exists():
                    for line in xds_inp.read_text(encoding="utf-8", errors="replace").split('\n'):
                        stripped = line.lstrip()
                        if stripped.startswith('!'):
                            continue
                        upper = stripped.upper()
                        if upper.startswith('EXCLUDE_RESOLUTION_RANGE') and '=' in stripped:
                            parts = stripped.split('=', 1)[1].strip().split()
                            if len(parts) >= 2:
                                try:
                                    existing_excl.append([float(parts[0]), float(parts[1])])
                                except ValueError:
                                    pass
                self.send_json({
                    "rings": ice,
                    "existing_exclusions": existing_excl,
                    "standard_positions": [
                        {"d": r[0], "hw": r[1], "label": r[2], "form": r[3]}
                        for r in LPParser.ICE_RING_POSITIONS
                    ]
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Generate XDS.INP from image headers
        elif project_route == '/generate-xdsinp':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            try:
                # Use template from query param if provided, else from XDS.INP, else scan
                template = qs.get('template', [None])[0]
                if not template:
                    xds_inp = project_dir / "XDS.INP"
                    if xds_inp.exists():
                        for line in xds_inp.read_text(encoding="utf-8", errors="replace").split('\n'):
                            ls = line.lstrip('! \t')
                            if ls.upper().startswith('NAME_TEMPLATE_OF_DATA_FRAMES'):
                                template = ls.split('=', 1)[1].strip()
                                break

                # If no template from XDS.INP, scan directory for images
                if not template:
                    exts = ('.cbf', '.img', '.h5', '.hdf5', '.tif', '.tiff', '.osc', '.mar3450')
                    for f in sorted(project_dir.iterdir()):
                        if f.suffix.lower() in exts:
                            # For HDF5, prefer master file
                            if f.suffix.lower() in ('.h5', '.hdf5'):
                                if '_master' in f.name:
                                    template = str(f)
                                    break
                            else:
                                # Convert filename to XDS template with ??????
                                import re as _re_gen
                                # the frame number is the LAST digit run (lyso_100K_00001.cbf)
                                m = _re_gen.search(r'(\d{3,})(?=\D*$)', f.stem)
                                if m:
                                    digits = m.group(1)
                                    qmarks = '?' * len(digits)
                                    tname = f.stem[:m.start(1)] + qmarks + f.stem[m.end(1):] + f.suffix
                                    template = str(project_dir / tname)
                                else:
                                    template = str(f)
                                break

                if not template:
                    self.send_json({"error": "No diffraction images found in project directory. "
                                             "Add images or set NAME_TEMPLATE_OF_DATA_FRAMES in XDS.INP."}, 404)
                    return

                # Sanitize HDF5 templates: XDS NAME_TEMPLATE must never contain
                # _data_ — the neggia plugin resolves ?????? → master internally.
                # A previous (buggy) generation may have written _data_ into XDS.INP.
                import re as _re_sanitize
                if template.lower().endswith(('.h5', '.hdf5')):
                    template = _re_sanitize.sub(r'_data_(\?+)', r'_\1', template)

                # If the user passed a concrete file path (no wildcards),
                # auto-convert it to an XDS template and count files via glob
                import glob as _glob_gen
                if '?' not in template and '*' not in template:
                    p_tmpl = Path(template)
                    ext_lo = p_tmpl.suffix.lower()
                    if ext_lo in ('.h5', '.hdf5'):
                        # For HDF5: XDS needs a wildcard template like data_??????.h5
                        # We also need to read headers from the master file
                        par = p_tmpl.parent
                        stem = p_tmpl.stem
                        if '_master' in p_tmpl.name.lower():
                            # User selected master file: convert to XDS wildcard template
                            # XDS NAME_TEMPLATE for Eiger HDF5 is always PREFIX_??????.h5
                            # The neggia/bitshuffle plugin resolves ?????? → master internally.
                            # Never use _data_ in the template — that refers to chunk files.
                            prefix = stem.replace('_master', '').replace('_Master', '').replace('_MASTER', '')
                            # Find actual data files to determine digit count
                            import glob as _g2
                            _found_tmpl = False
                            for ndigits in (6, 5, 4, 8, 3):
                                qmarks = '?' * ndigits
                                cand = str(par / (prefix + '_' + qmarks + p_tmpl.suffix))
                                pattern = cand.replace('?', '[0-9]')
                                if _g2.glob(pattern):
                                    template = cand
                                    _found_tmpl = True
                                    break
                            if not _found_tmpl:
                                # Default: 6-digit wildcard (standard Eiger convention)
                                template = str(par / f'{prefix}_??????{p_tmpl.suffix}')
                        elif '_master' not in p_tmpl.name.lower():
                            # Data chunk file: try to find master for header reading
                            # e.g. PREFIX_data_000001.h5 → template PREFIX_??????.h5
                            # (XDS template never contains _data_)
                            m = re.search(r'_\d+$', stem)
                            if m:
                                prefix = stem[:m.start()]
                                # Strip trailing _data from prefix — XDS template
                                # must be PREFIX_??????.h5, not PREFIX_data_??????.h5
                                xds_prefix = re.sub(r'_data$', '', prefix, flags=re.IGNORECASE)
                                # Build wildcard template
                                ndigits = len(stem) - m.start() - 1  # digits after _
                                qmarks = '?' * ndigits
                                template = str(par / f'{xds_prefix}_{qmarks}{p_tmpl.suffix}')
                                # Try to locate master for header reading
                                master_prefix = re.sub(r'_data$', '', prefix, flags=re.IGNORECASE)
                                for cand in (par / f'{master_prefix}_master.h5',
                                             par / f'{master_prefix}_master.hdf5',
                                             par / f'{prefix}_master.h5',
                                             par / f'{prefix}_master.hdf5'):
                                    if cand.exists():
                                        break
                    else:
                        # For frame-per-file formats: replace trailing digits with ?
                        stem = p_tmpl.stem
                        ext = p_tmpl.suffix
                        par = p_tmpl.parent
                        # Prefer trailing digits (most common: name_001.cbf)
                        m = re.search(r'(\d+)\s*$', stem)
                        if m:
                            qmarks = '?' * len(m.group(1))
                            tname = stem[:m.start(1)] + qmarks + stem[m.end(1):] + ext
                            template = str(par / tname)

                # Resolve to first actual file for header reading
                first_file = None
                if '?' in template:
                    pattern = template.replace('?', '[0-9]')
                    matches = sorted(_glob_gen.glob(pattern))
                    ext_lo = Path(template).suffix.lower()
                    if ext_lo in ('.h5', '.hdf5'):
                        # The master file holds the geometry; chunk files do not.
                        first_file = _h5_find_master(template)
                        if not first_file and matches:
                            first_file = matches[0]
                    else:
                        if matches:
                            first_file = matches[0]
                else:
                    first_file = template

                if not first_file or not Path(first_file).exists():
                    self.send_json({"error": f"Could not find image file from template: {template}"}, 404)
                    return

                # Read header
                header = ImageHeaderReader.read(first_file)
                if '_error' in header and not any(k in header for k in ('wavelength', 'detector_distance')):
                    self.send_json({"error": f"Failed to read image header: {header['_error']}. "
                                             "Ensure fabio, h5py, and hdf5plugin are installed."}, 500)
                    return

                # Count frames from file system for frame-per-file formats
                if '?' in template:
                    pattern = template.replace('?', '[0-9]')
                    nfiles = len(_glob_gen.glob(pattern))
                    if nfiles > 0:
                        # For frame-per-file formats, glob count is authoritative
                        ext_lo = Path(template).suffix.lower()
                        if ext_lo not in ('.h5', '.hdf5') or 'nframes' not in header:
                            header['nframes'] = str(nfiles)
                            numbers = XDSINPGenerator.frame_numbers(template)
                            if numbers:
                                header['first_frame'], header['last_frame'] = numbers[0], numbers[1]

                content, warnings = XDSINPGenerator.generate(template, header, lib_path=NEGGIA_LIB)
                # Add debug info about which file was read and what was found
                hdr_keys = sorted(k for k in header if not k.startswith('_'))
                hdr_summary = ', '.join(f'{k}={header[k]}' for k in hdr_keys[:15])
                h5dbg = header.get('_h5_debug', '')
                self.send_json({
                    "content": content,
                    "warnings": warnings,
                    "header": {k: v for k, v in header.items() if not k.startswith('_')},
                    "template": template,
                    "first_file": str(first_file),
                    "debug": f"Read from: {first_file} | Keys: {hdr_summary}",
                    "h5_debug": h5dbg
                })
            except ImportError as e:
                self.send_json({"error": f"Missing Python dependency: {e}. "
                                         "Install with: pip install fabio h5py hdf5plugin"}, 500)
            except Exception as e:
                import traceback
                self.send_json({"error": f"Generation failed: {e}",
                                "traceback": traceback.format_exc()}, 500)

        # Get XDS.INP file
        elif project_route == '/xdsinp':
            name = _url_project_name(path.split("/")[3])
            xds_inp = _pdir(name) / "XDS.INP"
            try:
                if xds_inp.exists():
                    _sync_cpu_keywords(xds_inp)
                    self.send_json({"content": _read_text_lenient(xds_inp)})
                else:
                    self.send_json({"content": ""})
            except Exception as e:
                self.send_json({"error": f"Failed to read XDS.INP: {e}"}, 500)
        
        
        # Config
        elif path == "/api/environment":
            try:
                _env = _environment_report()
                # what was dismissed on this machine (settings file, so it
                # survives a different browser or a cleared browser store)
                _env["seen"] = str(_load_settings().get("env_seen") or "")
                self.send_json(_env)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif path == "/api/config":
            if not NEGGIA_LIB:
                NEGGIA_LIB = _find_neggia()
            self.send_json({"xds_path": str(xds_runner.xds_path), "ccp4_bin": CCP4_BIN, "neggia_lib": NEGGIA_LIB, "script_dir": str(Path(__file__).parent.resolve()), "projects_dir": str(PROJECTS_DIR.resolve()), "is_wsl": IS_WSL, "wsl_drives": _wsl_drives(), "parallel": XDS_PARALLEL, "settings_file": str(SETTINGS_FILE),
                            "wsl_distro": os.environ.get("WSL_DISTRO_NAME", ""), "projects_drive": os.environ.get("CRYSTALPILOT_DRIVE", "").strip(),
                            "projects_win": _windows_view(str(PROJECTS_DIR)), "resources": _resource_info()})

        # List XSCALE subfolders (for XDSCONV workdir selection)
        elif project_route == '/xscale-subfolders':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            folders = []
            try:
                for child in project_dir.iterdir():
                    if child.is_dir() and child.name.startswith("XSCALE_"):
                        folders.append({"name": child.name, "path": str(child), "mtime": child.stat().st_mtime})
            except OSError:
                pass
            folders.sort(key=lambda x: x["mtime"], reverse=True)
            latest = folders[0] if folders else None
            self.send_json({"folders": [f["name"] for f in folders], "latest": latest["path"] if latest else "", "latest_name": latest["name"] if latest else ""})

        # CCP4 check
        elif path == "/api/ccp4check":
            if not CCP4_BIN:
                CCP4_BIN = _find_ccp4_bin()
            found = bool(CCP4_BIN)
            progs = {p: _ccp4_program(p) for p in CCP4_PROGRAMS}
            # why a program cannot run, for the interface to show as it is
            problems = [progs[p][2] for p in ("f2mtz", "cad") if found and not progs[p][0]]
            if CCP4_BIN_SAVED and CCP4_BIN_SAVED != CCP4_BIN and not _is_ccp4_bin(CCP4_BIN_SAVED):
                problems.append("the saved CCP4 folder " + CCP4_BIN_SAVED + " holds no CCP4 programs any more")
            gemmi_ok, gemmi_ver = _check_gemmi()
            self.send_json({"found": found, "ccp4_bin": CCP4_BIN,
                            "windows": any(v[1] == "windows" for v in progs.values()),
                            "problems": problems,
                            "f2mtz": bool(progs["f2mtz"][0]), "cad": bool(progs["cad"][0]),
                            "pointless": bool(progs["pointless"][0]), "aimless": bool(progs["aimless"][0]),
                            "ctruncate": bool(progs["ctruncate"][0]),
                            "gemmi": gemmi_ok, "gemmi_version": gemmi_ver if gemmi_ok else None})

        # LP stats for gemmi comparison: return statistics_table from CORRECT.LP or XSCALE.LP
        elif path == '/api/gemmi/lp-stats':
            qs_lp = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project = qs_lp.get("project", [""])[0]
            source = qs_lp.get("source", ["correct"])[0]  # "correct" or "xscale"
            if not project:
                self.send_json({"success": False, "message": "No project specified"}, 400)
                return
            project_dir = _pdir(project)
            try:
                if source == "xscale":
                    # Find most recent XSCALE.LP
                    candidates = []
                    root_lp = _pfile(project_dir, "XSCALE.LP", "xscale")
                    if root_lp.exists():
                        candidates.append(root_lp)
                    try:
                        for child in project_dir.iterdir():
                            if child.is_dir() and child.name.startswith("XSCALE_"):
                                sub_lp = child / "XSCALE.LP"
                                if sub_lp.exists():
                                    candidates.append(sub_lp)
                    except OSError:
                        pass
                    if not candidates:
                        self.send_json({"success": False, "message": "No XSCALE.LP found"})
                        return
                    lp_file = max(candidates, key=lambda pp: pp.stat().st_mtime)
                    content = lp_file.read_text(encoding="utf-8", errors="replace")
                    m = LPParser.parse_xscale(content)
                    tbl = m.get("statistics_table", [])
                    sg = m.get("space_group", "")
                else:
                    lp_file = _pfile(project_dir, "CORRECT.LP")
                    if not lp_file.exists():
                        self.send_json({"success": False, "message": "No CORRECT.LP found"})
                        return
                    content = lp_file.read_text(encoding="utf-8", errors="replace")
                    m = LPParser.parse_correct(content)
                    tbl = m.get("statistics_table", [])
                    sg = m.get("space_group", "")
                # Separate shells from total
                shells = [r for r in tbl if str(r.get("resolution", "")).lower() != "total"]
                total = [r for r in tbl if str(r.get("resolution", "")).lower() == "total"]
                self.send_json({
                    "success": True,
                    "source": source,
                    "source_file": str(lp_file),
                    "spacegroup": sg,
                    "shells": shells,
                    "overall": total[0] if total else {},
                    "n_shells": len(shells)
                })
            except Exception as e:
                self.send_json({"success": False, "message": str(e)}, 500)

        # Download deposition CIF file
        elif path == '/api/gemmi/download-cif':
            qs_dl = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            filepath = qs_dl.get("path", [""])[0]
            if self._refuse_outside(filepath):
                return
            if not filepath or not Path(filepath).exists():
                self.send_json({"error": "File not found"}, 404)
                return
            try:
                cif_data = Path(filepath).read_bytes()
                fname = Path(filepath).name
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.send_header('Content-Length', str(len(cif_data)))
                self.end_headers()
                self.wfile.write(cif_data)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # ── Batch processing ─────────────────────────────────────────────
        elif path == '/api/batch/strategy':
            self.send_json({"options": STRATEGY_OPTIONS, "presets": STRATEGY_PRESETS})

        elif path == '/api/batch/list':
            self.send_json({"batches": batch_list(), "active": _BATCH_ACTIVE["id"]})

        elif path == '/api/batch':
            batch_id = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("id", [""])[0]
            self.send_json(batch_state(batch_id))

        elif path == '/api/batch/log':
            qs_bl = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            batch_id = qs_bl.get("id", [""])[0]
            project = qs_bl.get("project", [""])[0]
            state = batch_load(batch_id)
            if project not in [i["project"] for i in state.get("items", [])]:
                self.send_json({"error": "That project is not part of this batch"}, 400)
                return
            log = _batch_dir(batch_id) / "logs" / (project + ".log")
            text = ""
            if log.is_file():
                # the SSE framing is for the browser stream; the reader wants the lines
                lines = []
                for block in _read_text_lenient(log).split("\n\n"):
                    head, _, data = block.partition("\ndata: ")
                    if head.strip() in ("event: ap_log", "event: ap_error", "event: ap_phase"):
                        try:
                            payload = json.loads(data)
                        except ValueError:
                            continue
                        lines.append(payload.get("text") or payload.get("message") or
                                     ("== " + str(payload.get("phase", "")) + " ==" if payload.get("phase") else ""))
                text = "\n".join(lines[-2000:])
            self.send_json({"project": project, "log": text})

        # Download a problem report written by POST /api/bug-report
        elif path == '/api/bug-report':
            name = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("name", [""])[0]
            if not _report_matches(name):
                self.send_json({"error": "Unknown report: " + name}, 400)
                return
            target = PROJECTS_DIR / "reports" / name
            if not target.is_file():
                self.send_json({"error": name + " does not exist"}, 404)
                return
            payload = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        # Download a project export written by POST /api/export
        elif path == '/api/export':
            qs_ex = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project = qs_ex.get("project", [""])[0]
            name = qs_ex.get("name", [""])[0]
            project_dir = _pdir(project)
            # only a name this project's own exporter could have produced
            if not _export_matches(project, name):
                self.send_json({"error": "Unknown export: " + name}, 400)
                return
            target = project_dir / name
            if not target.is_file():
                self.send_json({"error": name + " has not been written yet"}, 404)
                return
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
                self.send_header("Content-Length", str(target.stat().st_size))
                self.end_headers()
                with open(str(target), "rb") as fh:
                    while True:
                        chunk = fh.read(1024 * 256)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        # One publication figure, by name, from the folder the figures were written to
        elif path == '/api/figure':
            qs_fig = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project = qs_fig.get("project", [""])[0]
            name = qs_fig.get("name", [""])[0]
            # The name says which log it came from; a path is never built from
            # anything but one of our own names.
            source = figure_source_of(name)
            if source is None:
                self.send_json({"error": "Unknown figure: " + name}, 400)
                return
            project_dir = _pdir(project)
            lp_path, out_dir = _figure_source(project_dir, source)
            target = out_dir / name
            if not target.is_file():
                self.send_json({"error": name + " has not been written yet for this run"}, 404)
                return
            try:
                payload = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except OSError as e:
                self.send_json({"error": str(e)}, 500)

        # XDS check – verify xds_par/xds, xscale_par/xscale and helpers
        elif path == "/api/xdscheck":
            import shutil as _sh_xds
            xds_path = xds_runner.xds_path
            # Find XDS
            xds_exe = None
            for name in ("xds_par", "xds"):
                p = xds_path / name
                if p.exists():
                    xds_exe = str(p); break
            if not xds_exe:
                for name in ("xds_par", "xds"):
                    f = _sh_xds.which(name)
                    if f:
                        xds_exe = f; break
            # Find XSCALE
            xscale_exe = None
            for name in ("xscale_par", "xscale"):
                p = xds_path / name
                if p.exists():
                    xscale_exe = str(p); break
            if not xscale_exe:
                for name in ("xscale_par", "xscale"):
                    f = _sh_xds.which(name)
                    if f:
                        xscale_exe = f; break
            # Find XDSCONV
            xdsconv_exe = None
            for name in ("xdsconv",):
                p = xds_path / name
                if p.exists():
                    xdsconv_exe = str(p); break
            if not xdsconv_exe:
                f = _sh_xds.which("xdsconv")
                if f:
                    xdsconv_exe = f
            # Check helpers
            helpers = ("forkxds", "mcolspot", "mintegrate")
            missing_helpers = []
            for name in helpers:
                if not (xds_path / name).exists() and not _sh_xds.which(name):
                    missing_helpers.append(name)
            self.send_json({
                "xds": xds_exe, "xscale": xscale_exe, "xdsconv": xdsconv_exe,
                "xds_path": str(xds_path),
                "missing_helpers": missing_helpers
            })

        # Directory listing for folder picker
        elif path == "/api/ls":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            req_path = qs.get("path", [""])[0] or str(Path.home())
            try:
                # A Windows path pasted from Explorer ("D:\data\xtal1",
                # "\\server\share\xtal1") is translated, and the drive or share
                # mounted when WSL has not done it - see _to_local_path.
                typed, path_problem = req_path, ""
                if not RESTRICT_BROWSE:
                    req_path, path_problem = _to_local_path(req_path)
                p = Path(req_path).resolve()
                missing = None
                if not p.exists() or not p.is_dir():
                    missing = typed         # tell the UI we fell back to home
                    p = Path.home()
                # When --restrict-browse is active, clamp to PROJECTS_DIR tree
                # (a real parent check: /home/u/xds2 is not inside /home/u/xds)
                if RESTRICT_BROWSE:
                    proj_root = PROJECTS_DIR.resolve()
                    if p != proj_root and proj_root not in p.parents:
                        p = proj_root
                entries = []
                if p.parent != p:
                    parent = p.parent
                    if RESTRICT_BROWSE:
                        proj_root = PROJECTS_DIR.resolve()
                        if parent == proj_root or proj_root in parent.parents:
                            entries.append({"name": "..", "path": str(parent), "is_dir": True})
                    else:
                        entries.append({"name": "..", "path": str(parent), "is_dir": True})
                for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    if not child.name.startswith("."):
                        entries.append({"name": child.name, "path": str(child), "is_dir": child.is_dir()})
                self.send_json({"cwd": str(p), "entries": entries, "missing": missing, "problem": path_problem})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Detect XDS_ASCII.HKL files in project folder and immediate subdirectories
        elif path == "/api/xscale-detect-hkl":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            if not project_name:
                self.send_json({"error": "project parameter required"}, 400)
                return
            project_dir = _pdir(project_name)
            if not project_dir.is_dir():
                self.send_json({"error": "Project directory not found"}, 404)
                return
            try:
                found = []
                # Scan top-level for .HKL files (excluding INTEGRATE.HKL)
                for child in sorted(project_dir.iterdir(), key=lambda x: x.name.lower()):
                    if child.is_file() and child.name.upper().endswith(('.HKL', '.AHKL')) and child.name.upper() != 'INTEGRATE.HKL':
                        found.append({"name": child.name, "path": str(child), "subfolder": ""})
                # Scan immediate subdirectories
                for child in sorted(project_dir.iterdir(), key=lambda x: x.name.lower()):
                    if child.is_dir() and not child.name.startswith('.') and not child.name.startswith('XSCALE_'):
                        for f in sorted(child.iterdir(), key=lambda x: x.name.lower()):
                            if f.is_file() and f.name.upper().endswith(('.HKL', '.AHKL')) and f.name.upper() != 'INTEGRATE.HKL':
                                found.append({"name": f.name, "path": str(f), "subfolder": child.name})
                # HKL files in the XDS output folder (when it is not the project folder)
                out_dir = _project_out_dir(project_dir)
                if out_dir != project_dir:
                    try:
                        for f in sorted(out_dir.iterdir(), key=lambda x: x.name.lower()):
                            if f.is_file() and f.name.upper().endswith(('.HKL', '.AHKL')) and f.name.upper() != 'INTEGRATE.HKL':
                                found.insert(0, {"name": f.name, "path": str(f), "subfolder": "XDS output folder"})
                    except OSError:
                        pass
                self.send_json({"files": found})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # SSE live log stream
        # Dependency status
        elif path == "/api/deps":
            self.send_json({"ready": VIEWER_READY,
                            "missing": [{"apt": e[0], "pip": e[2], "import": e[3]} for e in MISSING_DEPS]})

        # Frame render endpoint
        elif path == "/api/frame":
            if not VIEWER_READY:
                self.send_json({"error": "deps_missing"}, 503)
                return
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            file_path = qs.get("path", [""])[0]
            if self._refuse_outside(file_path):
                return
            cmap_name = qs.get("cmap", ["gray_r"])[0]
            try:
                frame_idx = int(float(qs.get("frame", ["0"])[0] or 0))
                vmin_pct  = float(qs.get("vmin", ["0"])[0] or 0)
                vmax_pct  = float(qs.get("vmax", ["99.5"])[0] or 99.5)
            except (TypeError, ValueError):
                self.send_json({"error": "frame, vmin and vmax must be numbers"}, 400)
                return
            if not file_path:
                self.send_json({"error": "path required"}, 400)
                return
            try:
                import fabio, numpy as np, matplotlib
                from matplotlib.figure import Figure
                from matplotlib.backends.backend_agg import FigureCanvasAgg

                bad_mask = None   # pixels excluded from contrast scaling (gaps, dead)
                # ── HDF5/Eiger: use h5py directly to get true frame count ──────
                # Eiger master.h5 stores links in /entry/data/data_000001 ...
                # data_NNNNNN — each pointing to a separate chunk file of ~100
                # frames. visititems() does NOT follow external links, so we must
                # enumerate those keys explicitly and build a frame LUT.
                # Eiger data.h5 (single chunk) stores frames at /entry/data/data.
                ext = Path(file_path).suffix.lower()
                if ext in ('.h5', '.hdf5'):
                    import h5py, hdf5plugin  # noqa: F401 (registers decompressors)
                    nframes = 1
                    data    = None
                    header  = {}
                    # Image data: an existing file is read as given (a chunk
                    # file is addressed with chunk-local frame indices); a
                    # template resolves to the master, which links every frame.
                    # Geometry always comes from the master when one exists.
                    img_file  = file_path if Path(file_path).is_file() else _resolve_h5_template(file_path)
                    meta_file = _h5_find_master(img_file) or img_file
                    file_path = img_file
                    with h5py.File(img_file, 'r') as f:

                        # ── Strategy 1: Eiger master.h5 ──────────────────────
                        # /entry/data contains keys data_000001, data_000002 …
                        # each is an external link to a chunk file.
                        # h5py follows external links transparently when accessed.
                        img_data = None
                        if 'entry/data' in f:
                            edata = f['entry/data']
                            # Collect chunk keys in sorted order
                            chunk_keys = sorted(
                                k for k in edata.keys()
                                if k.startswith('data_')
                            )
                            if chunk_keys:
                                # Build cumulative frame offsets
                                offsets = []  # (start_frame, dataset)
                                total = 0
                                for ck in chunk_keys:
                                    try:
                                        ds = edata[ck]
                                        if ds.ndim == 3:
                                            offsets.append((total, ds))
                                            total += ds.shape[0]
                                    except Exception:
                                        pass
                                if offsets:
                                    nframes = total
                                    fi = min(frame_idx, nframes - 1)
                                    # Find which chunk holds frame fi
                                    for (start, ds) in reversed(offsets):
                                        if fi >= start:
                                            img_data = ds[fi - start]
                                            break

                        # ── Strategy 2: single data.h5 with /entry/data/data ─
                        if img_data is None and 'entry/data/data' in f:
                            ds = f['entry/data/data']
                            if ds.ndim == 3:
                                nframes  = ds.shape[0]
                                fi       = min(frame_idx, nframes - 1)
                                img_data = ds[fi]

                        # ── Strategy 3: walk all datasets (fallback) ──────────
                        if img_data is None:
                            best_ds   = None
                            best_size = 0
                            def _collect(name, obj):
                                nonlocal best_ds, best_size
                                try:
                                    if isinstance(obj, h5py.Dataset) and obj.ndim == 3:
                                        if obj.shape[0] > best_size:
                                            best_size = obj.shape[0]
                                            best_ds   = obj
                                except Exception:
                                    pass
                            f.visititems(_collect)
                            if best_ds is not None:
                                nframes  = best_ds.shape[0]
                                fi       = min(frame_idx, nframes - 1)
                                img_data = best_ds[fi]

                        if img_data is None:
                            raise RuntimeError(
                                "No image data found in HDF5 file. "
                                "Expected Eiger master.h5 (/entry/data/data_000001…) "
                                "or data.h5 (/entry/data/data)."
                            )
                        # Eiger flags gap and dead pixels with the dtype maximum
                        # (65535 for 16-bit, 4294967295 for 32-bit data).
                        raw = np.asarray(img_data)
                        if raw.dtype.kind == 'u':
                            bad_mask = raw == np.iinfo(raw.dtype).max
                        elif raw.dtype.kind in 'if':
                            bad_mask = raw < 0
                        data = raw.astype(np.float32)

                    with h5py.File(meta_file, 'r') as f:
                        header['ny'] = str(data.shape[0])
                        header['nx'] = str(data.shape[1])
                        # Detector pixel mask (bit 0 = gap, others = dead/hot …)
                        try:
                            _pm = f['/entry/instrument/detector/detectorSpecific/pixel_mask']
                            if tuple(_pm.shape) == tuple(data.shape):
                                _pmv = _pm[()] != 0
                                bad_mask = _pmv if bad_mask is None else (bad_mask | _pmv)
                        except Exception:
                            pass
                        try:
                            _desc = f['/entry/instrument/detector/description'][()]
                            if hasattr(_desc, 'flat') and not isinstance(_desc, (bytes, str)):
                                _desc = _desc.flat[0]
                            if isinstance(_desc, (bytes, np.bytes_)):
                                _desc = _desc.decode('utf-8', 'replace')
                            _desc = str(_desc).strip()
                            if _desc:
                                header['detector_name'] = _desc
                        except Exception:
                            pass

                        # ── Metadata ──────────────────────────────────────────
                        # Phase 1: try explicit known NeXus/Eiger paths.
                        # This is robust against visititems aborting early when
                        # external data links are unreachable.
                        # Phase 2: visititems walk as catch-all for non-standard files.
                        # All values converted to canonical units:
                        #   wavelength        → Å
                        #   detector_distance → mm
                        #   x/y_pixel_size    → mm
                        #   beam_center_x/y   → pixels (no conversion)

                        def _h5scalar(ds):
                            try:
                                v = ds[()]
                                if hasattr(v, '__len__'): v = v.flat[0]
                                return float(v)
                            except Exception:
                                return None

                        def _h5units(ds):
                            try:
                                u = ds.attrs.get('units', b'')
                                if isinstance(u, (bytes, np.bytes_)):
                                    u = u.decode()
                                return str(u).lower().strip()
                            except Exception:
                                return ''

                        def _to_canonical(v, units, canon):
                            u = units
                            if canon == 'wavelength':
                                if u in ('m', 'meter', 'meters', 'metre', 'metres'):
                                    return v * 1e10
                                elif u in ('nm', 'nanometer', 'nanometre',
                                           'nanometers', 'nanometres'):
                                    return v * 10.0
                                else:
                                    return v  # assume Å
                            elif canon in ('detector_distance',
                                           'x_pixel_size', 'y_pixel_size'):
                                av = abs(v)
                                if u in ('mm', 'millimeter', 'millimetre',
                                         'millimeters', 'millimetres'):
                                    return av
                                elif u in ('cm', 'centimeter', 'centimetre'):
                                    return av * 10.0
                                elif u in ('m', 'meter', 'meters',
                                           'metre', 'metres'):
                                    return av * 1000.0
                                else:
                                    # NeXus default is metres; values >= 1 are mm
                                    return av * 1000.0 if av < 1.0 else av
                            else:
                                return v  # beam_center: pixels, no conversion

                        def _h5get(grp, path, canon):
                            """Try to read one explicit path; store in header if found."""
                            if canon in header:
                                return
                            try:
                                ds = grp[path]
                                if not isinstance(ds, h5py.Dataset):
                                    return
                                v = _h5scalar(ds)
                                if v is None:
                                    return
                                converted = _to_canonical(v, _h5units(ds), canon)
                                header[canon] = str(round(converted, 6))
                            except Exception:
                                pass

                        # Phase 1 — explicit paths (ordered: most common first)
                        _explicit = [
                            # detector distance
                            ('detector_distance', '/entry/instrument/detector/distance'),
                            ('detector_distance', '/entry/instrument/detector/detector_distance'),
                            ('detector_distance', '/entry/instrument/detector/sample_detector_distance'),
                            ('detector_distance', '/entry/instrument/detector/detector_distance/value'),
                            ('detector_distance', '/entry/instrument/detector_z/value'),
                            ('detector_distance', '/entry/instrument/detector_z/data'),
                            # wavelength
                            ('wavelength', '/entry/instrument/beam/incident_wavelength'),
                            ('wavelength', '/entry/instrument/monochromator/wavelength'),
                            ('wavelength', '/entry/sample/beam/incident_wavelength'),
                            ('wavelength', '/entry/instrument/beam/wavelength'),
                            ('wavelength', '/entry/instrument/beam/photon_wavelength'),
                            # pixel size
                            ('x_pixel_size', '/entry/instrument/detector/x_pixel_size'),
                            ('y_pixel_size', '/entry/instrument/detector/y_pixel_size'),
                            # beam center
                            ('beam_center_x', '/entry/instrument/detector/beam_center_x'),
                            ('beam_center_y', '/entry/instrument/detector/beam_center_y'),
                        ]
                        for canon, epath in _explicit:
                            _h5get(f, epath, canon)

                        # Phase 1b — photon_energy → wavelength conversion
                        if 'wavelength' not in header:
                            _energy_paths = [
                                '/entry/instrument/beam/photon_energy',
                                '/entry/instrument/monochromator/energy',
                                '/entry/instrument/beam/energy',
                            ]
                            for epath in _energy_paths:
                                try:
                                    ds = f[epath]
                                    if not isinstance(ds, h5py.Dataset):
                                        continue
                                    eV = _h5scalar(ds)
                                    if eV is None or eV <= 0:
                                        continue
                                    u = _h5units(ds)
                                    if u in ('kev', 'kiloelectronvolt'):
                                        eV = eV * 1000.0
                                    elif u in ('ev', 'electronvolt', ''):
                                        pass  # already eV (or guess eV)
                                    # Heuristic: if value < 100, likely keV
                                    if eV < 100:
                                        eV = eV * 1000.0
                                    wl_angstrom = 12398.419 / eV
                                    header['wavelength'] = str(round(wl_angstrom, 6))
                                    break
                                except Exception:
                                    pass

                        # Phase 1c — targeted subgroup walk
                        # visititems on the full file can abort if /entry/data
                        # contains broken external links. Walk safe subgroups only.
                        _geo_keys = {
                            'detector_distance', 'distance',
                            'sample_detector_distance',
                            'beam_center_x', 'beam_center_y',
                            'x_pixel_size', 'y_pixel_size',
                            'incident_wavelength', 'wavelength',
                            'photon_wavelength',
                            'beam_x', 'beam_y', 'x_beam', 'y_beam',
                            'photon_energy', 'energy',
                        }
                        _key_canon = {
                            'incident_wavelength': 'wavelength',
                            'photon_wavelength': 'wavelength',
                            'distance': 'detector_distance',
                            'sample_detector_distance': 'detector_distance',
                            'beam_x': 'beam_center_x', 'beam_y': 'beam_center_y',
                            'x_beam': 'beam_center_x', 'y_beam': 'beam_center_y',
                        }
                        _energy_canon = {'photon_energy', 'energy'}

                        def _collect_geo(name, obj):
                            try:
                                if not isinstance(obj, h5py.Dataset): return
                                key = name.split('/')[-1].lower()
                                if key not in _geo_keys: return
                                v = _h5scalar(obj)
                                if v is None or v == 0: return
                                canon = _key_canon.get(key, key)
                                if key in _energy_canon:
                                    # Convert energy → wavelength
                                    if 'wavelength' in header: return
                                    eV = v
                                    u = _h5units(obj)
                                    if u in ('kev', 'kiloelectronvolt'):
                                        eV *= 1000.0
                                    elif eV < 100:
                                        eV *= 1000.0
                                    header['wavelength'] = str(round(12398.419 / eV, 6))
                                    return
                                if canon in header: return  # phase 1 wins
                                units = _h5units(obj)
                                converted = _to_canonical(v, units, canon)
                                header[canon] = str(round(converted, 6))
                            except Exception:
                                pass

                        # Walk safe subgroups first (avoids broken external links in /entry/data)
                        for _subgrp in ('entry/instrument', 'entry/sample'):
                            if _subgrp in f:
                                try:
                                    f[_subgrp].visititems(_collect_geo)
                                except Exception:
                                    pass
                        # Fallback: try full root walk (may fail on master files
                        # with broken external links, but catches oddly structured files)
                        try:
                            f.visititems(_collect_geo)
                        except Exception:
                            pass

                        # Diagnostic: if key values still missing, log H5 tree to stderr
                        if 'detector_distance' not in header or 'wavelength' not in header:
                            import sys as _sys2
                            _sys2.stderr.write(
                                f"[H5 DEBUG] {file_path}\n"
                                f"  header so far: {header}\n"
                            )
                            for _subgrp in ('entry/instrument', 'entry/sample'):
                                if _subgrp in f:
                                    try:
                                        def _dump(name, obj):
                                            if isinstance(obj, h5py.Dataset):
                                                try:
                                                    v = obj[()]
                                                    if hasattr(v, '__len__') and len(v) > 5:
                                                        v = f"array({v.shape})"
                                                    u = obj.attrs.get('units', b'')
                                                    _sys2.stderr.write(
                                                        f"    {_subgrp}/{name}: {v} (units={u})\n"
                                                    )
                                                except Exception:
                                                    _sys2.stderr.write(
                                                        f"    {_subgrp}/{name}: <unreadable>\n"
                                                    )
                                        f[_subgrp].visititems(_dump)
                                    except Exception:
                                        pass
                            _sys2.stderr.flush()
                else:
                    # ── Non-HDF5: use fabio ────────────────────────────────────
                    # .osc is Rigaku R-AXIS; fabio doesn't register the extension.
                    img_obj = None
                    if ext == '.osc':
                        from fabio.raxisimage import RaxisImage as _RaxisImage
                        img_obj = _RaxisImage()
                        img_obj.read(file_path)
                    else:
                        try:
                            img_obj = fabio.open(file_path)
                        except Exception:
                            img_obj = None

                    # ── Fallback: raw CBF byte-offset reader ───────────────────
                    # XDS diagnostic CBFs (SHOW_SPOT/HKL/BKG.cbf) have non-
                    # standard CIF headers that crash fabio's parser.  Read the
                    # binary section directly with byte-offset decompression.
                    if img_obj is None and ext == '.cbf':
                        raw_bytes = Path(file_path).read_bytes()
                        # Locate binary data marker
                        _CBF_MAGIC = b'\x0c\x1a\x04\xd5'
                        bpos = raw_bytes.find(_CBF_MAGIC)
                        if bpos < 0:
                            raise ValueError("Not a valid CBF file (no binary marker)")
                        # Parse dimensions from text header
                        text_hdr = raw_bytes[:bpos].decode('latin-1')
                        import re as _re_cbf
                        m_fast = _re_cbf.search(
                            r'X-Binary-Size-Fastest-Dimension:\s*(\d+)', text_hdr)
                        m_sec = _re_cbf.search(
                            r'X-Binary-Size-Second-Dimension:\s*(\d+)', text_hdr)
                        if not m_fast or not m_sec:
                            raise ValueError("CBF missing dimension headers")
                        nx = int(m_fast.group(1))
                        ny = int(m_sec.group(1))
                        npixels = nx * ny
                        # Decode byte-offset compression
                        import struct as _struct
                        buf = raw_bytes[bpos + len(_CBF_MAGIC):]
                        vals = np.empty(npixels, dtype=np.int32)
                        val = 0
                        j = 0   # output index
                        i = 0   # input index
                        blen = len(buf)
                        while j < npixels and i < blen:
                            delta = _struct.unpack_from('b', buf, i)[0]
                            i += 1
                            if delta == -128:
                                if i + 2 > blen: break
                                delta = _struct.unpack_from('<h', buf, i)[0]
                                i += 2
                                if delta == -32768:
                                    if i + 4 > blen: break
                                    delta = _struct.unpack_from('<i', buf, i)[0]
                                    i += 4
                            val += delta
                            vals[j] = val
                            j += 1
                        data = vals[:npixels].reshape(ny, nx).astype(np.float32)
                        nframes = 1
                        # Minimal header — no geometry for diagnostic images
                        header = {}
                    elif img_obj is None:
                        raise ValueError(
                            f"Cannot open {file_path} — fabio failed and not a CBF")
                    else:
                        nframes = getattr(img_obj, "nframes", 1)
                        if frame_idx > 0 and nframes > 1:
                            img_obj = img_obj.getframe(frame_idx)
                        data = img_obj.data.astype(np.float32)

                    # ── Extract geometry from image header ─────────────────────
                    # Output (all canonical units):
                    #   wavelength        Å
                    #   detector_distance mm
                    #   x_pixel_size      mm/pixel
                    #   y_pixel_size      mm/pixel
                    #   beam_center_x     pixels  (from detector corner)
                    #   beam_center_y     pixels
                    #
                    # Format unit conventions (verified against fabio source):
                    #   CBF (Pilatus/Eiger):
                    #       Pixel_size        metres   → *1000
                    #       Detector_distance metres   → *1000
                    #       Beam_xy           pixels   (no conversion)
                    #       Wavelength        Å        (no conversion)
                    #   ADSC/SMV .img:
                    #       PIXEL_SIZE        mm       (no conversion)
                    #       DISTANCE          mm       (no conversion)
                    #       BEAM_CENTER_X/Y   mm(!)    → /PIXEL_SIZE → pixels
                    #       WAVELENGTH        Å        (no conversion)
                    #   OSC/RAXIS binary:
                    #       X/Y Pixel Length  mm       (no conversion)
                    #       Crystal-to-detector Distance  mm  (no conversion)
                    #       Direct beam X/Y position  mm(!) → /pixel_size → pixels
                    #       Wavelength        Å        (no conversion)

                    def _unwrap(v):
                        # struct.unpack always returns a tuple, e.g. (0.172,).
                        # Unwrap single-element numeric tuples so _flt can parse them.
                        if isinstance(v, tuple) and len(v) == 1:
                            return v[0]
                        return v
                    if img_obj is not None:
                        raw = {k.strip(): str(_unwrap(v)).strip()
                               for k, v in img_obj.header.items()}
                        header = {}
                    else:
                        raw = {}

                    def _flt(s):
                        try: return float(str(s).split()[0])
                        except Exception: return None

                    # ── CBF: geometry from pilatus_headers (PILATUS_1.2) ────────
                    ph = getattr(img_obj, 'pilatus_headers', None)
                    if ph is not None:
                        try:
                            if 'Pixel_size' in ph:
                                px = ph['Pixel_size']          # (x_m, y_m) metres
                                header['x_pixel_size'] = str(round(float(px[0]) * 1000.0, 6))
                                header['y_pixel_size'] = str(round(float(px[1]) * 1000.0, 6))
                            if 'Detector_distance' in ph:
                                header['detector_distance'] = str(
                                    round(abs(float(ph['Detector_distance'])) * 1000.0, 4))
                            if 'Wavelength' in ph:
                                header['wavelength'] = str(round(float(ph['Wavelength']), 6))
                            if 'Beam_xy' in ph:
                                bxy = ph['Beam_xy']             # (x_px, y_px) pixels
                                header['beam_center_x'] = str(round(float(bxy[0]), 4))
                                header['beam_center_y'] = str(round(float(bxy[1]), 4))
                        except (TypeError, IndexError, ValueError, KeyError):
                            pass  # Non-standard CBF (e.g. XDS diagnostic) — fall through

                    # ── CBF fallback: parse _array_data.header_contents text ────
                    # Handles CBF files where pilatus_headers is None (non-PILATUS_1.2)
                    import re as _re
                    _mini = raw.get('_array_data.header_contents', '') or ''
                    if _mini:
                        def _mini_flt(pat, txt, scale=1.0):
                            m = _re.search(pat, txt, _re.IGNORECASE)
                            if m:
                                try: return float(m.group(1)) * scale
                                except Exception: pass
                            return None
                        if 'detector_distance' not in header:
                            v = _mini_flt(r'Detector_distance\s+([\d.eE+\-]+)', _mini, 1000.0)
                            if v: header['detector_distance'] = str(round(abs(v), 4))
                        if 'wavelength' not in header:
                            v = _mini_flt(r'Wavelength\s+([\d.eE+\-]+)', _mini, 1.0)
                            if v and v > 0.01: header['wavelength'] = str(round(v, 6))
                        if 'x_pixel_size' not in header:
                            v = _mini_flt(r'Pixel_size\s+([\d.eE+\-]+)', _mini, 1000.0)
                            if v:
                                header['x_pixel_size'] = str(round(v, 6))
                                m2 = _re.search(
                                    r'Pixel_size\s+[\d.eE+\-]+\s+\S+\s+x\s+([\d.eE+\-]+)',
                                    _mini, _re.IGNORECASE)
                                vy = float(m2.group(1)) * 1000.0 if m2 else v
                                header['y_pixel_size'] = str(round(vy, 6))
                        if 'beam_center_x' not in header:
                            m2 = _re.search(
                                r'Beam_xy\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)',
                                _mini, _re.IGNORECASE)
                            if m2:
                                header['beam_center_x'] = str(round(float(m2.group(1)), 4))
                                header['beam_center_y'] = str(round(float(m2.group(2)), 4))

                    # ── ADSC/SMV .img ──────────────────────────────────────────
                    if 'x_pixel_size' not in header:
                        v = _flt(raw.get('PIXEL_SIZE'))     # mm — no conversion
                        if v:
                            header['x_pixel_size'] = str(round(v, 6))
                            header['y_pixel_size'] = str(round(v, 6))

                    if 'detector_distance' not in header:
                        v = _flt(raw.get('DISTANCE'))       # mm — no conversion
                        if v:
                            header['detector_distance'] = str(round(abs(v), 4))

                    if 'wavelength' not in header:
                        v = _flt(raw.get('WAVELENGTH'))     # Å — no conversion
                        if v and v > 0.01:                  # guard against metres
                            header['wavelength'] = str(round(v, 6))

                    if 'beam_center_x' not in header:
                        cx = _flt(raw.get('BEAM_CENTER_X')) # mm → pixels
                        cy = _flt(raw.get('BEAM_CENTER_Y'))
                        qx = _flt(header.get('x_pixel_size'))
                        if cx and cy and qx:
                            header['beam_center_x'] = str(round(cx / qx, 4))
                            header['beam_center_y'] = str(round(cy / qx, 4))

                    # ── OSC/RAXIS binary ───────────────────────────────────────
                    if 'x_pixel_size' not in header:
                        v = _flt(raw.get('X Pixel Length')) # mm — no conversion
                        if v:
                            header['x_pixel_size'] = str(round(v, 6))
                            vy = _flt(raw.get('Y Pixel Length')) or v
                            header['y_pixel_size'] = str(round(vy, 6))

                    if 'detector_distance' not in header:
                        v = _flt(raw.get('Crystal-to-detector Distance'))  # mm
                        if v:
                            header['detector_distance'] = str(round(abs(v), 4))

                    if 'wavelength' not in header:
                        v = _flt(raw.get('Wavelength'))     # Å — no conversion
                        if v and v > 0.01:
                            header['wavelength'] = str(round(v, 6))

                    if 'beam_center_x' not in header:
                        cx = _flt(raw.get('Direct beam X position'))
                        cy = _flt(raw.get('Direct beam Y position'))
                        qx = _flt(header.get('x_pixel_size'))
                        # R-AXIS stores beam position in 0.1mm units (raw float).
                        # Convert: val * 0.1mm / qx(mm/px) = pixels.
                        if cx and cy and qx:
                            header['beam_center_x'] = str(round(cx * 0.1 / qx, 4))
                            header['beam_center_y'] = str(round(cy * 0.1 / qx, 4))

                # ── Detector pixel-size lookup table (fallback) ───────────────
                # Used only when pixel size is absent from the image header.
                # Source: XDS supported detectors (xds.mr.mpg.de/html_doc/detectors.html)
                #
                # IMPORTANT: several detectors share the same pixel dimensions
                # (e.g. ADSC Q315 and MarCCD 225mm are both 3072×3072).  The
                # image format (file extension / fabio class) is used to
                # disambiguate.  Each entry: (NX, NY, fmt_hint, qx, qy, name)
                # fmt_hint is a substring matched against ext or fabio classname;
                # None means "match any format".
                _DET_LIST = [
                    # ── DECTRIS PILATUS (172 µm) — unique shapes, CBF ──────────
                    (2463, 2527, 'cbf',  0.172,  0.172,  'PILATUS 6M'),
                    (2463, 5071, 'cbf',  0.172,  0.172,  'PILATUS 12M'),
                    (1475, 1679, 'cbf',  0.172,  0.172,  'PILATUS 3M'),
                    ( 981, 1043, 'cbf',  0.172,  0.172,  'PILATUS 1M'),
                    ( 487,  619, 'cbf',  0.172,  0.172,  'PILATUS 300K'),
                    ( 487,  407, 'cbf',  0.172,  0.172,  'PILATUS 200K'),
                    ( 487,  195, 'cbf',  0.172,  0.172,  'PILATUS 100K'),
                    # ── DECTRIS EIGER / EIGER2 (75 µm) — HDF5 or CBF ──────────
                    (1030, 1065, None,   0.075,  0.075,  'EIGER 1M'),
                    (2070, 2167, None,   0.075,  0.075,  'EIGER 4M'),
                    (3110, 3269, None,   0.075,  0.075,  'EIGER 9M'),
                    (4150, 4371, None,   0.075,  0.075,  'EIGER 16M'),
                    (1028, 1062, None,   0.075,  0.075,  'EIGER2 1M'),
                    (1030,  514, None,   0.075,  0.075,  'EIGER 500K'),
                    (1028,  512, None,   0.075,  0.075,  'EIGER2 500K'),
                    (2068, 2162, None,   0.075,  0.075,  'EIGER2 4M'),
                    (3108, 3262, None,   0.075,  0.075,  'EIGER2 9M'),
                    (4148, 4362, None,   0.075,  0.075,  'EIGER2 16M'),
                    # ── ADSC CCD — SMV/img format ─────────────────────────────
                    (2048, 2048, 'img',  0.1024, 0.1024, 'ADSC Q210'),
                    (4096, 4096, 'img',  0.051,  0.051,  'ADSC Q210r'),
                    (3072, 3072, 'img',  0.10259,0.10259,'ADSC Q315'),
                    (6144, 6144, 'img',  0.0513, 0.0513, 'ADSC Q315r'),
                    (2304, 2304, 'img',  0.0816, 0.0816, 'ADSC Q4r'),
                    (2048, 2048, 'img',  0.05,   0.05,   'ADSC Q105'),
                    # ── MarCCD / Rayonix — TIFF format ────────────────────────
                    (4096, 4096, 'tif',  0.07342,0.07342,'Rayonix MX300'),
                    (3072, 3072, 'tif',  0.07345,0.07345,'Rayonix MX225'),
                    (2048, 2048, 'tif',  0.079,  0.079,  'Rayonix MX165'),
                    (2048, 2048, 'tif',  0.064,  0.064,  'MarCCD 133mm'),
                    (1024, 1024, 'tif',  0.0508, 0.0508, 'MarCCD old CHESS'),
                    # ── MAR345 imaging plate — mar345 format ──────────────────
                    (2300, 2300, 'mar',  0.150,  0.150,  'MAR345 2300'),
                    (2000, 2000, 'mar',  0.150,  0.150,  'MAR345 2000'),
                    (1600, 1600, 'mar',  0.150,  0.150,  'MAR345 1600'),
                    (1200, 1200, 'mar',  0.150,  0.150,  'MAR345 1200'),
                    (3450, 3450, 'mar',  0.100,  0.100,  'MAR345 3450'),
                    (3000, 3000, 'mar',  0.100,  0.100,  'MAR345 3000'),
                    (2400, 2400, 'mar',  0.100,  0.100,  'MAR345 2400'),
                    (1800, 1800, 'mar',  0.100,  0.100,  'MAR345 1800'),
                    # ── MAR555 flat panel ──────────────────────────────────────
                    (2560, 3072, 'mar',  0.139,  0.139,  'MAR555'),
                    # ── Rigaku R-AXIS — osc/raxis format ──────────────────────
                    ( 950,  950, 'osc',  0.2034, 0.210,  'R-AXIS II'),
                    (1900, 1900, 'osc',  0.1017, 0.105,  'R-AXIS II 2x'),
                    (3000, 3000, 'osc',  0.100,  0.100,  'R-AXIS IV/V'),
                    (1500, 1500, 'osc',  0.200,  0.200,  'R-AXIS IV 1x'),
                    (6000, 6000, 'osc',  0.050,  0.050,  'R-AXIS IV 2x'),
                    # ── Rigaku Saturn CCD — home source ───────────────────────
                    ( 512,  512, None,   0.140,  0.140,  'Saturn 70'),
                    ( 512,  512, None,   0.180,  0.180,  'Saturn 92'),
                    # ── Bruker / APEX ──────────────────────────────────────────
                    ( 512,  512, None,   0.120,  0.120,  'Bruker APEX'),
                    (1024, 1024, None,   0.060,  0.060,  'Bruker APEX2'),
                    # ── NOIR (lens CCD at ALS 4.2.2) ──────────────────────────
                    (2048, 2048, 'img',  0.07767,0.07767,'NOIR-1'),
                ]
                if 'x_pixel_size' not in header:
                    h_px, w_px = data.shape
                    fmt_lower = ext.lstrip('.').lower()  # 'cbf', 'img', 'tif', etc.
                    det = None
                    # First pass: match shape + format hint
                    for nx, ny, fmt, qx, qy, name in _DET_LIST:
                        if nx == w_px and ny == h_px:
                            if fmt is None or fmt in fmt_lower:
                                det = (qx, qy, name)
                                break
                    # Second pass: shape only (no format hint, last resort)
                    if det is None:
                        for nx, ny, fmt, qx, qy, name in _DET_LIST:
                            if nx == w_px and ny == h_px and fmt is None:
                                det = (qx, qy, name)
                                break
                    if det:
                        header['x_pixel_size'] = str(det[0])
                        header['y_pixel_size'] = str(det[1])
                        header['detector_name'] = det[2]

                # Masked pixels (negative in CBF/fabio data: Pilatus gaps are -1,
                # dead pixels -2; dtype-max or pixel_mask in Eiger HDF5) must not
                # feed the contrast percentiles.  On an Eiger the module gaps are
                # several percent of all pixels, so the 99.5 % cutoff would land
                # on the gap value and wash out the entire frame.
                _neg = data < 0
                bad_mask = _neg if bad_mask is None else (bad_mask | _neg)
                data = np.log1p(np.clip(data, 0, None))
                valid = data[~bad_mask]
                if valid.size == 0:
                    valid = data.ravel()
                lo = float(np.percentile(valid, vmin_pct))
                hi = float(np.percentile(valid, vmax_pct))
                if hi <= lo:
                    hi = lo + 1e-3
                data[bad_mask] = np.nan
                try:
                    try:
                        _cmap = matplotlib.colormaps[cmap_name]
                    except Exception:
                        _cmap = matplotlib.cm.get_cmap(cmap_name)
                    import copy as _copy
                    _cmap = _copy.copy(_cmap)
                    _cmap.set_bad('#7d8fa8')   # gaps drawn in a neutral blue-grey
                except Exception:
                    _cmap = cmap_name
                dpi = 100
                h, w = data.shape
                fig = Figure(figsize=(w/dpi, h/dpi), dpi=dpi)
                ax = fig.add_axes([0,0,1,1])
                ax.imshow(data, cmap=_cmap, vmin=lo, vmax=hi,
                          origin="upper", interpolation="nearest", aspect="equal")
                ax.axis("off")
                buf = io.BytesIO()
                FigureCanvasAgg(fig).print_png(buf)
                b64 = base64.b64encode(buf.getvalue()).decode()
                self.send_json({"image": b64, "nframes": nframes,
                                "shape": list(data.shape), "header": header})
            except Exception as e:
                try:
                    self.send_json({"error": str(e)}, 500)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

        # Return total frame count for an HDF5 file (without rendering)
        elif path == "/api/h5/nframes":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            file_path = qs.get("path", [""])[0]
            if self._refuse_outside(file_path):
                return
            try:
                file_path = _resolve_h5_template(file_path)
                import h5py, hdf5plugin  # noqa
                total = 0
                with h5py.File(file_path, 'r') as f:
                    if 'entry/data' in f:
                        edata = f['entry/data']
                        chunk_keys = sorted(k for k in edata.keys()
                                            if k.startswith('data_'))
                        for ck in chunk_keys:
                            try:
                                ds = edata[ck]
                                if ds.ndim == 3:
                                    total += ds.shape[0]
                            except Exception:
                                pass
                    if total == 0 and 'entry/data/data' in f:
                        ds = f['entry/data/data']
                        if ds.ndim == 3:
                            total = ds.shape[0]
                    if total == 0:
                        # fallback: walk
                        def _coll(name, obj):
                            nonlocal total
                            try:
                                if isinstance(obj, h5py.Dataset) and obj.ndim == 3:
                                    if obj.shape[0] > total:
                                        total = obj.shape[0]
                            except Exception:
                                pass
                        f.visititems(_coll)
                    if total == 0:
                        # Data links unreachable: fall back to the declared count
                        try:
                            _spec = f['/entry/instrument/detector/detectorSpecific']
                            total = int(_spec['nimages'][()]) * int(_spec['ntrigger'][()])
                        except Exception:
                            pass
                self.send_json({"nframes": max(1, total)})
            except Exception as e:
                self.send_json({"nframes": 1, "error": str(e)})

        # Read an arbitrary XDS.INP file for the frame viewer auto-extract
        elif path == "/api/fv-xdsinp":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            file_path = qs.get("path", [""])[0]
            if self._refuse_outside(file_path):
                return
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="replace")
                # Also return pre-parsed geometry params for robust client use
                params = _parse_xdsinp_params(content)
                geo = {}
                for xds_key, geo_key in [
                    ('QX', 'qx'), ('QY', 'qy'),
                    ('DETECTOR_DISTANCE', 'dist'),
                    ('ORGX', 'orgx'), ('ORGY', 'orgy'),
                    ('X-RAY_WAVELENGTH', 'wavelength'),
                    ('NAME_TEMPLATE_OF_DATA_FRAMES', 'template'),
                    ('DETECTOR', 'detector'),
                    ('NX', 'nx'), ('NY', 'ny'),
                    ('OSCILLATION_RANGE', 'osc'),
                ]:
                    if xds_key in params and params[xds_key]:
                        geo[geo_key] = params[xds_key]
                self.send_json({"content": content, "params": geo})
            except Exception as e:
                self.send_json({"error": str(e)}, 404)

        # Read SPOT.XDS and return spots for a specific frame number
        elif path == "/api/fv-spots":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            dirpath = qs.get("dir", [""])[0]
            if self._refuse_outside(dirpath):
                return
            try:
                spot_file = Path(dirpath) / "SPOT.XDS"
                if not spot_file.exists():
                    self.send_json({"spots": [], "info": "SPOT.XDS not found"})
                    return
                spots = []
                with open(spot_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('!'):
                            continue
                        parts = line.split()
                        if len(parts) < 4:
                            continue
                        try:
                            x   = float(parts[0])
                            y   = float(parts[1])
                            z   = float(parts[2])
                            intensity = float(parts[3])
                            h = int(parts[4]) if len(parts) > 6 else 0
                            k = int(parts[5]) if len(parts) > 6 else 0
                            l = int(parts[6]) if len(parts) > 6 else 0
                            indexed = (h != 0 or k != 0 or l != 0)
                            # Frame assignment: XDS Z is 0-based fractional;
                            # frame 1 spans Z in [0,1), frame 2 in [1,2), etc.
                            frame = int(z) + 1
                            if z > 0 and z == int(z):
                                frame = int(z)
                            spots.append([x, y, z, frame, 1 if indexed else 0, intensity])
                        except (ValueError, IndexError):
                            continue
                self.send_json({"spots": spots, "count": len(spots),
                                "file": str(spot_file)})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Glob frames matching a NAME_TEMPLATE pattern
        elif path == "/api/frames/list":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            template = qs.get("template", [""])[0]
            if self._refuse_outside(template):
                return
            try:
                p = Path(template)
                parent = p.parent
                name = p.name
                # XDS ?-wildcards: one digit each for frame series, so xtal_?????.cbf does not
                # also list xtal_2_00001.cbf of another sweep; Eiger templates keep * (it must
                # reach the _master file)
                if name.lower().endswith(('.h5', '.hdf5')):
                    glob_pat = re.sub(r"[?]+", "*", name)
                else:
                    glob_pat = name.replace("?", "[0-9]")
                IMAGE_EXTS = {'.cbf', '.osc', '.img', '.smv', '.mccd', '.mar',
                              '.h5', '.hdf5', '.tiff', '.tif'}
                SERIES_EXTS = {'.cbf', '.osc', '.img', '.smv', '.mccd', '.mar'}
                # If the input is a bare directory, scan it for image files
                if p.is_dir():
                    files = []
                    for ext in IMAGE_EXTS:
                        files.extend(p.glob('*' + ext))
                        files.extend(p.glob('*' + ext.upper()))
                    files = sorted(set(str(f) for f in files if f.is_file()))
                    _h5files = [f for f in files if f.lower().endswith(('.h5', '.hdf5'))]
                    _masters = [f for f in _h5files if 'master' in Path(f).name.lower()]
                    if _masters:
                        # Each Eiger master links every frame of its dataset;
                        # listing the chunk files as well would count frames twice.
                        files = [f for f in files if f not in _h5files] + _masters
                    self.send_json({"files": files, "count": len(files)})
                    return
                # Special handling for HDF5 templates: resolve to master file
                # XDS template like prefix_??????.h5 → look for prefix_master.h5
                if ('?' in name or '*' in name) and p.suffix.lower() in ('.h5', '.hdf5'):
                    master_path = _resolve_h5_template(template)
                    mp = Path(master_path)
                    if mp.exists() and 'master' in mp.name.lower():
                        # Return just the master file; the frame viewer will
                        # use h5/nframes to count frames via external links.
                        self.send_json({"files": [master_path], "count": 1})
                        return
                    # No master found — glob for data chunk files
                    if parent.is_dir():
                        files = sorted(str(f) for f in parent.glob(glob_pat)
                                       if f.is_file() and 'master' not in f.name.lower())
                        if files:
                            self.send_json({"files": files, "count": len(files)})
                            return
                # A concrete HDF5 file (master or data chunk): view the whole
                # dataset through its master file when one exists.
                if p.is_file() and p.suffix.lower() in ('.h5', '.hdf5') and '?' not in name and '*' not in name:
                    _m = _h5_find_master(str(p))
                    if _m:
                        self.send_json({"files": [_m], "count": 1})
                        return
                # If the input is a concrete single-frame file with no wildcards,
                # auto-discover the full series by replacing trailing digits with *
                if p.is_file() and p.suffix.lower() in SERIES_EXTS and '?' not in name and '*' not in name:
                    stem = p.stem
                    ext  = p.suffix
                    base = re.sub(r'\d+$', '*', stem)
                    if base != stem:
                        glob_pat = base + ext
                if not parent.is_dir():
                    self.send_json({"files": [], "error": "Directory not found"})
                    return
                files = sorted(str(f) for f in parent.glob(glob_pat)
                               if f.is_file())
                self.send_json({"files": files, "count": len(files)})
            except Exception as e:
                self.send_json({"files": [], "error": str(e)})

        # Install missing deps (GET for EventSource compatibility)
        elif path == "/api/deps/install":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            def wfn(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            def ev(event, data_obj):
                wfn("event: " + event + "\ndata: " + json.dumps(data_obj) + "\n\n")
            if not MISSING_DEPS:
                ev("done", {"success": True, "message": "Already installed"})
                return
            try:
                def _run_stream(cmd):
                    rc, outcome = _run_streaming(cmd, os.getcwd(), lambda t: ev("log", {"text": t}),
                                                 timeout=1800, key="install", register=False)
                    if outcome != "ok":
                        ev("log", {"text": ">>> " + _outcome_message(outcome, " ".join(str(c) for c in cmd[:2]))})
                    return rc

                def _run_quiet(cmd):
                    try:
                        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        return r.returncode, r.stdout + r.stderr
                    except Exception:
                        return 1, ""

                def _cmd_exists(cmd):
                    return shutil.which(cmd) is not None

                # ── Detect environment (once, shared by all _install_one calls) ──
                in_conda   = bool(os.environ.get("CONDA_PREFIX") or
                                  os.environ.get("CONDA_DEFAULT_ENV"))
                has_apt    = _cmd_exists("apt-get")
                has_dnf    = _cmd_exists("dnf")
                has_yum    = _cmd_exists("yum")
                has_pacman = _cmd_exists("pacman")
                has_zypper = _cmd_exists("zypper")
                has_brew   = _cmd_exists("brew")
                # Just check if sudo exists. If it needs a password and there's
                # no TTY the command will simply fail (rc!=0) and we fall through
                # to the next method. This avoids skipping apt/dnf entirely on
                # lab machines where users have sudo but must type a password.
                has_sudo   = _cmd_exists("sudo")

                # Track whether apt-get update / zypper refresh has been run
                _pkg_cache_refreshed = False

                import platform as _platform
                _uname_sys = _platform.system()  # "Linux" or "Darwin"

                # Log detected environment for debugging
                _env_parts = []
                if in_conda: _env_parts.append("conda")
                if has_apt: _env_parts.append("apt")
                if has_dnf: _env_parts.append("dnf")
                if has_yum: _env_parts.append("yum")
                if has_pacman: _env_parts.append("pacman")
                if has_zypper: _env_parts.append("zypper")
                if has_brew: _env_parts.append("brew")
                if has_sudo: _env_parts.append("sudo")
                ev("log", {"text": f"[setup] platform={_uname_sys}, tools={','.join(_env_parts) or 'none'}"})

                # Detect pip and its version once
                # _pip_cmd will be set to the working pip invocation prefix
                _pip_cmd = None

                def _get_pip_info():
                    nonlocal _pip_cmd
                    # Try python3 -m pip first (most reliable)
                    rc, out = _run_quiet([sys.executable, "-m", "pip", "--version"])
                    if rc == 0:
                        _pip_cmd = [sys.executable, "-m", "pip"]
                        try:
                            import re as _re
                            grp = _re.search(r"pip (\d+)\.(\d+)", out).groups()
                            ver = tuple(int(x) for x in grp)
                            return True, ver >= (22, 3)
                        except Exception:
                            return True, False
                    # Fallback: try pip3 binary on PATH
                    if _cmd_exists("pip3"):
                        rc2, out2 = _run_quiet(["pip3", "--version"])
                        if rc2 == 0:
                            _pip_cmd = ["pip3"]
                            try:
                                import re as _re
                                grp = _re.search(r"pip (\d+)\.(\d+)", out2).groups()
                                ver = tuple(int(x) for x in grp)
                                return True, ver >= (22, 3)
                            except Exception:
                                return True, False
                    return False, False

                has_pip, pip_new_enough = _get_pip_info()

                # If no pip at all, try to get it first
                if not has_pip:
                    ev("log", {"text": "[setup] pip not found — attempting to install..."})
                    # Try ensurepip first (works without sudo, ships with Python)
                    ev("log", {"text": "[setup] trying python3 -m ensurepip..."})
                    _run_stream([sys.executable, "-m", "ensurepip", "--default-pip"])
                    has_pip, pip_new_enough = _get_pip_info()
                    if not has_pip:
                        if has_apt and has_sudo:
                            ev("log", {"text": "[setup] sudo apt-get install -y python3-pip"})
                            _run_stream(["sudo", "apt-get", "install", "-y", "python3-pip"])
                        elif has_dnf and has_sudo:
                            _run_stream(["sudo", "dnf", "install", "-y", "python3-pip"])
                        elif has_yum and has_sudo:
                            _run_stream(["sudo", "yum", "install", "-y", "python3-pip"])
                        elif has_pacman and has_sudo:
                            _run_stream(["sudo", "pacman", "-S", "--noconfirm", "python-pip"])
                        elif has_zypper and has_sudo:
                            _run_stream(["sudo", "zypper", "--non-interactive", "install", "python3-pip"])
                        elif has_brew:
                            ev("log", {"text": "[brew] brew install python3 (includes pip)"})
                            _run_stream(["brew", "install", "python3"])
                        has_pip, pip_new_enough = _get_pip_info()

                def _try_import(pkg):
                    """Import pkg after clearing caches so freshly-installed packages are found."""
                    # Only clear cached import *failures* (None in sys.modules).
                    # Never pop a successfully-loaded module — reimporting causes recursion.
                    if sys.modules.get(pkg) is None and pkg in sys.modules:
                        del sys.modules[pkg]
                    try: import importlib; importlib.invalidate_caches()
                    except Exception: pass
                    import site as _s
                    try:
                        u = _s.getusersitepackages()
                        if u and u not in sys.path:
                            sys.path.insert(0, u)
                    except Exception: pass
                    try:
                        for sp in _s.getsitepackages():
                            if sp not in sys.path:
                                sys.path.append(sp)
                    except Exception: pass
                    try: __import__(pkg); return True
                    except ImportError: pass
                    # Last resort: verify with subprocess (avoids stale in-process state)
                    try:
                        rc = subprocess.run(
                            [sys.executable, "-c", f"import {pkg}"],
                            capture_output=True, timeout=30).returncode
                        if rc == 0:
                            # Package exists on disk; force-load it
                            try:
                                import importlib as _il
                                _il.import_module(pkg)
                                return True
                            except Exception:
                                pass
                            # Even importlib failed but subprocess proved it's installed.
                            # Mark success — _check_deps() at the end will do the
                            # authoritative re-check anyway.
                            return True
                    except Exception: pass
                    return False

                def _pip_run(pkg, flags):
                    """Run pip install, silently dropping unknown flags on old pip."""
                    clean = [f for f in flags
                             if f != "--break-system-packages" or pip_new_enough]
                    cmd = (_pip_cmd or [sys.executable, "-m", "pip"]) + ["install", pkg] + clean
                    return _run_stream(cmd)

                def _install_one(entry):
                    """Try every available install method. Returns True on success."""
                    nonlocal _pkg_cache_refreshed
                    apt_pkg    = entry[0]
                    dnf_pkg    = entry[1]
                    pip_pkg    = entry[2]
                    imp        = entry[3]
                    pacman_pkg = entry[4] if len(entry) > 4 else None
                    zypper_pkg = entry[5] if len(entry) > 5 else None

                    # 1. Conda (use conda's own pip — no sudo, no PEP 668 issues)
                    if in_conda:
                        ev("log", {"text": f"[conda] conda install -y -c conda-forge {pip_pkg}"})
                        rc = _run_stream(["conda", "install", "-y", "-c", "conda-forge", pip_pkg])
                        if rc == 0 and _try_import(imp): return True
                        ev("log", {"text": "[conda] trying conda pip..."})
                        rc = _run_stream([sys.executable, "-m", "pip", "install", pip_pkg])
                        if rc == 0 and _try_import(imp): return True

                    # 2. apt-get (Debian/Ubuntu/Mint)
                    if has_apt and has_sudo:
                        if not _pkg_cache_refreshed:
                            ev("log", {"text": "[apt] sudo apt-get update"})
                            _run_stream(["sudo", "apt-get", "update", "-qq"])
                            _pkg_cache_refreshed = True
                        ev("log", {"text": f"[apt] sudo apt-get install -y {apt_pkg}"})
                        rc = _run_stream(["sudo", "apt-get", "install", "-y", apt_pkg])
                        if rc == 0 and _try_import(imp): return True
                        ev("log", {"text": "[apt] not in repos, trying pip..."})

                    # 3. dnf (Fedora / RHEL 8+ / Rocky / AlmaLinux)
                    if has_dnf and has_sudo and dnf_pkg:
                        ev("log", {"text": f"[dnf] sudo dnf install -y {dnf_pkg}"})
                        rc = _run_stream(["sudo", "dnf", "install", "-y", dnf_pkg])
                        if rc == 0 and _try_import(imp): return True

                    # 4. yum (CentOS 7 / RHEL 7)
                    if has_yum and has_sudo and dnf_pkg:
                        ev("log", {"text": f"[yum] sudo yum install -y {dnf_pkg}"})
                        rc = _run_stream(["sudo", "yum", "install", "-y", dnf_pkg])
                        if rc == 0 and _try_import(imp): return True

                    # 4b. pacman (Arch / Manjaro)
                    if has_pacman and has_sudo and pacman_pkg:
                        ev("log", {"text": f"[pacman] sudo pacman -S --noconfirm {pacman_pkg}"})
                        rc = _run_stream(["sudo", "pacman", "-S", "--noconfirm", pacman_pkg])
                        if rc == 0 and _try_import(imp): return True

                    # 4c. zypper (openSUSE / SLES)
                    if has_zypper and has_sudo and zypper_pkg:
                        ev("log", {"text": f"[zypper] sudo zypper --non-interactive install {zypper_pkg}"})
                        rc = _run_stream(["sudo", "zypper", "--non-interactive", "install", zypper_pkg])
                        if rc == 0 and _try_import(imp): return True

                    # 4d. Homebrew (macOS)
                    # Only some Python packages have Homebrew formulae; others must use pip.
                    # Verify sys.executable is the Homebrew Python so brew packages are
                    # actually importable from our process.
                    _brew_names = {
                        "numpy": "numpy",
                        "matplotlib": "matplotlib",
                        "h5py": "hdf5",        # brew installs C lib; pip installs bindings
                    }
                    if has_brew and pip_pkg in _brew_names:
                        _brew_python = False
                        try:
                            _bp, _ = _run_quiet(["brew", "--prefix"])
                            _brew_python = sys.executable.startswith(_bp.strip())
                        except Exception: pass
                        if _brew_python:
                            brew_pkg = _brew_names[pip_pkg]
                            ev("log", {"text": f"[brew] brew install {brew_pkg}"})
                            rc = _run_stream(["brew", "install", brew_pkg])
                            if rc == 0 and _try_import(imp): return True
                            # h5py needs pip after brew installs the C lib
                            if brew_pkg != pip_pkg:
                                ev("log", {"text": f"[brew+pip] pip install {pip_pkg}"})
                                rc = _pip_run(pip_pkg, [])
                                if rc == 0 and _try_import(imp): return True

                    if not has_pip:
                        ev("log", {"text": f"[pip] pip unavailable, cannot install {pip_pkg}"})
                        return False

                    # 5. pip with sudo (installs system-wide)
                    if has_sudo:
                        sudo_pip = ["sudo"] + (_pip_cmd or [sys.executable, "-m", "pip"])
                        ev("log", {"text": f"[pip] sudo {' '.join((_pip_cmd or [sys.executable, '-m', 'pip']))} install {pip_pkg}"})
                        rc = _run_stream(sudo_pip + ["install", pip_pkg] +
                                         (["--break-system-packages"] if pip_new_enough else []))
                        if rc == 0 and _try_import(imp): return True

                    # 6. pip --user (no root needed, works on all pip versions and distros)
                    ev("log", {"text": f"[pip] python3 -m pip install {pip_pkg} --user"})
                    rc = _pip_run(pip_pkg, ["--user"])
                    if rc == 0 and _try_import(imp): return True

                    # 7. pip without --user as last resort (some venvs don't support --user)
                    ev("log", {"text": f"[pip] python3 -m pip install {pip_pkg}"})
                    rc = _pip_run(pip_pkg, ["--break-system-packages"])
                    if rc == 0 and _try_import(imp): return True

                    return False

                # Install each missing dep
                for entry in list(MISSING_DEPS):
                    ev("log", {"text": f"--- Installing {entry[3]} ---"})
                    ok = _install_one(entry)
                    if not ok:
                        ev("log", {"text": f"WARNING: could not install {entry[3]} by any method"})

                # Refresh dep state after all installs
                MISSING_DEPS = _check_deps()
                VIEWER_READY = len(MISSING_DEPS) == 0

                # Re-run HDF5 plugin path setup regardless of full success
                # (h5py + hdf5plugin may now be installed even if others are missing)
                _setup_hdf5_plugin_path.__globals__["_os"].environ.pop("HDF5_PLUGIN_PATH", None)
                _setup_hdf5_plugin_path()

                if VIEWER_READY:
                    ev("done", {"success": True, "message": "All dependencies installed!"})
                else:
                    still = [e[3] for e in MISSING_DEPS]
                    # Build platform-specific manual install command
                    if has_apt:
                        sys_pkgs = " ".join(e[0] for e in MISSING_DEPS)
                        manual = f"sudo apt-get update && sudo apt-get install -y python3-pip {sys_pkgs}"
                    elif has_dnf:
                        sys_pkgs = " ".join((e[1] or e[2]) for e in MISSING_DEPS)
                        manual = f"sudo dnf install -y python3-pip {sys_pkgs}"
                    elif has_pacman:
                        sys_pkgs = " ".join(e[4] for e in MISSING_DEPS if e[4])
                        pip_pkgs = " ".join(e[2] for e in MISSING_DEPS if not e[4])
                        parts = ["sudo pacman -S --noconfirm python-pip"]
                        if sys_pkgs:
                            parts[0] += " " + sys_pkgs
                        if pip_pkgs:
                            parts.append(f"pip install --user {pip_pkgs}")
                        manual = " && ".join(parts)
                    elif has_zypper:
                        sys_pkgs = " ".join(e[5] for e in MISSING_DEPS if e[5])
                        pip_pkgs = " ".join(e[2] for e in MISSING_DEPS if not e[5])
                        parts = ["sudo zypper --non-interactive install python3-pip"]
                        if sys_pkgs:
                            parts[0] += " " + sys_pkgs
                        if pip_pkgs:
                            parts.append(f"pip3 install --user {pip_pkgs}")
                        manual = " && ".join(parts)
                    elif has_brew:
                        pip_pkgs = " ".join(e[2] for e in MISSING_DEPS)
                        manual = f"pip3 install {pip_pkgs}"
                    else:
                        pip_pkgs = " ".join(e[2] for e in MISSING_DEPS)
                        manual = f"pip3 install {pip_pkgs}"
                    ev("done", {"success": False,
                                "message": "Still missing: " + ", ".join(still) +
                                           " — run in a terminal: " + manual})
            except Exception as e:
                ev("done", {"success": False, "message": str(e)})

        elif path == "/api/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            step_param   = qs.get("step",    [""])[0]
            stop_at      = qs.get("stop_at", [""])[0]
            steps_param  = qs.get("steps",   [""])[0]
            run_folder   = qs.get("run_folder", [""])[0]
            copy_gxparm  = qs.get("copy_gxparm", [""])[0] == "1"
            if self._refuse_outside(run_folder, base=_pdir(project_name) if project_name else None):
                return
            if step_param:
                steps = [step_param]
            elif steps_param:
                steps = [s.strip() for s in steps_param.split(",")]
            elif stop_at:
                if stop_at not in XDS_PIPELINE:
                    self.send_json({"error": "Unknown step: " + stop_at}, 400); return
                steps = XDS_PIPELINE[:XDS_PIPELINE.index(stop_at) + 1]
            else:
                steps = list(XDS_PIPELINE)
            bad = [s for s in steps if s not in XDS_PIPELINE]
            if bad or not steps:
                self.send_json({"error": "Unknown step: " + ", ".join(bad or ["(none)"])}, 400); return
            self._begin_processing_stream(project_name, "done")
            def write_fn(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_xds(project_name, steps, write_fn, run_folder=run_folder if run_folder else None, copy_gxparm=copy_gxparm)

        # SSE stream for Auto-Indexing
        elif path == "/api/autoindex/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            tier = qs.get("tier", ["quick"])[0]
            if tier not in ("quick", "medium", "full"):
                tier = "quick"
            force_cell = qs.get("force_cell", ["0"])[0] == "1"
            self._begin_processing_stream(project_name, "ai_done")
            def write_fn_ai(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_autoindex(project_name, tier, write_fn_ai, force_cell=force_cell)

        # Cached auto-indexing results
        elif project_route == '/autoindex-cached':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            try:
                result = load_autoindex_cached_results(str(project_dir))
                self.send_json(result)
            except Exception as e:
                self.send_json({"has_results": False, "error": str(e)})

        # Get XSCALE.INP file
        elif project_route == '/xscaleinp':
            name = _url_project_name(path.split("/")[3])
            xscale_inp = _pdir(name) / "XSCALE.INP"
            if xscale_inp.exists():
                try:
                    _sync_cpu_keywords(xscale_inp)
                    self.send_json({"content": xscale_inp.read_text(encoding="utf-8", errors='replace')})
                except Exception as e:
                    self.send_json({"error": f"Failed to read XSCALE.INP: {e}"}, 500)
            else:
                self.send_json({"content": "", "note": "XSCALE.INP not found in " + str(_pdir(name))})

        # Get XSCALE.LP file
        elif project_route == '/xscalelp':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            # Collect all XSCALE.LP candidates: project root + XSCALE_NNN subfolders
            candidates = []
            root_lp = _pfile(project_dir, "XSCALE.LP", "xscale")
            if root_lp.exists():
                candidates.append(root_lp)
            try:
                for child in project_dir.iterdir():
                    if child.is_dir() and child.name.startswith("XSCALE_"):
                        sub_lp = child / "XSCALE.LP"
                        if sub_lp.exists():
                            candidates.append(sub_lp)
            except OSError:
                pass
            if candidates:
                # Pick the most recently modified XSCALE.LP
                lp_file = max(candidates, key=lambda p: p.stat().st_mtime)
                try:
                    content = lp_file.read_text(encoding="utf-8", errors='replace')
                    metrics = LPParser.parse_xscale(content)
                    self.send_json({"content": content, "source": str(lp_file), "metrics": metrics})
                except Exception as e:
                    self.send_json({"error": f"Failed to read XSCALE.LP: {e}"}, 500)
            else:
                self.send_json({"error": "XSCALE.LP not found in " + str(project_dir) + " or its XSCALE_* subfolders"}, 404)

        # SSE stream for XSCALE
        elif path == "/api/xscale/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            run_folder   = qs.get("run_folder", [""])[0]
            if self._refuse_outside(run_folder, base=_pdir(project_name) if project_name else None):
                return
            self._begin_processing_stream(project_name, "done")
            def write_fn_xs(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_xscale(project_name, write_fn_xs, run_folder=run_folder if run_folder else None)

        # Get XDSCONV.INP file
        elif project_route == '/xdsconvinp':
            name = _url_project_name(path.split("/")[3])
            xdsconv_inp = _pdir(name) / "XDSCONV.INP"
            if xdsconv_inp.exists():
                try:
                    self.send_json({"content": xdsconv_inp.read_text(encoding="utf-8", errors='replace')})
                except Exception as e:
                    self.send_json({"error": f"Failed to read XDSCONV.INP: {e}"}, 500)
            else:
                self.send_json({"content": "", "note": "XDSCONV.INP not found"})

        # Get XDSCONV.LP file
        elif project_route == '/xdsconvlp':
            name = _url_project_name(path.split("/")[3])
            lp_file = _pfile(_pdir(name), "XDSCONV.LP", "xdsconv")
            if lp_file.exists():
                try:
                    self.send_json({"content": lp_file.read_text(encoding="utf-8", errors='replace')})
                except Exception as e:
                    self.send_json({"error": f"Failed to read XDSCONV.LP: {e}"}, 500)
            else:
                self.send_json({"error": "XDSCONV.LP not found"}, 404)

        # SSE stream for XDSCONV
        elif path == "/api/xdsconv/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            work_dir_param = qs.get("work_dir", [""])[0]
            mtz_name_param = qs.get("mtz_name", [""])[0]
            if self._refuse_outside(work_dir_param, base=_pdir(project_name) if project_name else None):
                return
            self._begin_processing_stream(project_name, "done")
            def write_fn_xc(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_xdsconv(project_name, write_fn_xc, work_dir=work_dir_param or None, mtz_name=mtz_name_param or None)

        # SSE stream for gemmi MTZ conversion (intensity-only, no CCP4 needed)
        elif path == "/api/gemmi-mtz/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            work_dir_param = qs.get("work_dir", [""])[0]
            mtz_name_param = qs.get("mtz_name", [""])[0]
            input_file_param = qs.get("input_file", [""])[0]
            freer_param = qs.get("freer", ["1"])[0]
            if self._refuse_outside(work_dir_param, input_file_param, base=_pdir(project_name) if project_name else None):
                return
            self._begin_processing_stream(project_name, "done")
            def write_fn_gm(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_gemmi_mtz(
                project_name, write_fn_gm,
                work_dir=work_dir_param or None,
                mtz_name=mtz_name_param or None,
                input_file=input_file_param or None,
                generate_freer=(freer_param != "0")
            )

        # SSE stream for auto-installing gemmi
        elif path == "/api/gemmi/install":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            def wfn_gi(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            def ev_gi(event, data_obj):
                wfn_gi("event: " + event + "\ndata: " + json.dumps(data_obj) + "\n\n")

            # Already installed?
            gi_ok, gi_info = _check_gemmi()
            if gi_ok:
                ev_gi("done", {"success": True, "message": "gemmi already installed (v" + gi_info + ")"})
            else:
                try:
                    import shutil as _sh_gi

                    def _gi_run_stream(cmd):
                        rc, outcome = _run_streaming(cmd, os.getcwd(), lambda t: ev_gi("log", {"text": t}),
                                                     timeout=1800, key="install", register=False)
                        if outcome != "ok":
                            ev_gi("log", {"text": ">>> " + _outcome_message(outcome, " ".join(str(c) for c in cmd[:2]))})
                        return rc

                    def _gi_run_quiet(cmd):
                        try:
                            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                            return r.returncode, r.stdout + r.stderr
                        except Exception:
                            return 1, ""

                    def _gi_try_import():
                        if sys.modules.get("gemmi") is None and "gemmi" in sys.modules:
                            del sys.modules["gemmi"]
                        try: import importlib; importlib.invalidate_caches()
                        except Exception: pass
                        import site as _s
                        try:
                            u = _s.getusersitepackages()
                            if u and u not in sys.path:
                                sys.path.insert(0, u)
                        except Exception: pass
                        try:
                            for sp in _s.getsitepackages():
                                if sp not in sys.path:
                                    sys.path.append(sp)
                        except Exception: pass
                        try: __import__("gemmi"); return True
                        except ImportError: pass
                        # Last resort: subprocess check
                        try:
                            rc = subprocess.run(
                                [sys.executable, "-c", "import gemmi"],
                                capture_output=True, timeout=30).returncode
                            if rc == 0: return True
                        except Exception: pass
                        return False

                    def _gi_cmd_exists(cmd):
                        return _sh_gi.which(cmd) is not None

                    in_conda = bool(os.environ.get("CONDA_PREFIX") or
                                    os.environ.get("CONDA_DEFAULT_ENV"))
                    # Try python3 -m pip first, then pip3 binary
                    has_pip_gi = _gi_run_quiet([sys.executable, "-m", "pip", "--version"])[0] == 0
                    if not has_pip_gi and _gi_cmd_exists("pip3"):
                        has_pip_gi = _gi_run_quiet(["pip3", "--version"])[0] == 0
                    has_sudo_gi = _gi_cmd_exists("sudo")
                    # Detect pip version for --break-system-packages
                    pip_new_gi = False
                    if has_pip_gi:
                        try:
                            import re as _re_gi
                            rc_gi, out_gi = _gi_run_quiet([sys.executable, "-m", "pip", "--version"])
                            grp_gi = _re_gi.search(r"pip (\d+)\.(\d+)", out_gi)
                            if grp_gi:
                                pip_new_gi = tuple(int(x) for x in grp_gi.groups()) >= (22, 3)
                        except Exception:
                            pass

                    installed = False

                    # Detect Python version — gemmi source builds need >=3.9 (nanobind)
                    # but pre-built wheels exist for 3.8+ on most platforms.
                    py_ver = sys.version_info[:2]
                    ev_gi("log", {"text": "[info] Python " + ".".join(str(x) for x in py_ver)
                                  + " on " + sys.platform})

                    # Helper: pip install with given flags, streaming output
                    def _gi_pip(pkg_spec, extra_flags, label="pip"):
                        cmd = [sys.executable, "-m", "pip", "install", pkg_spec] + extra_flags
                        ev_gi("log", {"text": "[" + label + "] " + " ".join(cmd)})
                        return _gi_run_stream(cmd)

                    def _gi_sudo_pip(pkg_spec, extra_flags, label="pip"):
                        cmd = ["sudo", sys.executable, "-m", "pip", "install", pkg_spec] + extra_flags
                        ev_gi("log", {"text": "[" + label + "] " + " ".join(cmd)})
                        return _gi_run_stream(cmd)

                    # Common flags
                    bsp = ["--break-system-packages"] if pip_new_gi else []

                    # 1. Conda
                    if not installed and in_conda:
                        ev_gi("log", {"text": "[conda] conda install -y -c conda-forge gemmi"})
                        rc = _gi_run_stream(["conda", "install", "-y", "-c", "conda-forge", "gemmi"])
                        if rc == 0 and _gi_try_import(): installed = True
                        if not installed:
                            rc = _gi_pip("gemmi", [], "conda-pip")
                            if rc == 0 and _gi_try_import(): installed = True

                    # 2. pip: prefer binary wheel (avoids source build on Python <3.9)
                    #    Try --only-binary=:all: first to grab the pre-built wheel.
                    if not installed and has_pip_gi:
                        # 2a. sudo + binary-only
                        if has_sudo_gi:
                            rc = _gi_sudo_pip("gemmi", ["--only-binary=:all:"] + bsp, "pip-wheel")
                            if rc == 0 and _gi_try_import(): installed = True

                        # 2b. --user + binary-only
                        if not installed:
                            rc = _gi_pip("gemmi", ["--only-binary=:all:", "--user"] + bsp, "pip-wheel")
                            if rc == 0 and _gi_try_import(): installed = True

                    # 3. If wheel install failed, pip may be too old to handle
                    #    manylinux_2_27/2_28 tags.  Upgrade pip and retry.
                    if not installed and has_pip_gi:
                        ev_gi("log", {"text": "[pip] Binary wheel not found — upgrading pip and retrying..."})
                        up_flags = bsp[:]
                        if has_sudo_gi:
                            _gi_run_stream(["sudo", sys.executable, "-m", "pip", "install", "--upgrade", "pip"] + up_flags)
                        else:
                            _gi_run_stream([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--user"] + up_flags)
                        # Re-detect pip version after upgrade
                        try:
                            import re as _re_gi2
                            rc_gi2, out_gi2 = _gi_run_quiet([sys.executable, "-m", "pip", "--version"])
                            grp_gi2 = _re_gi2.search(r"pip (\d+)\.(\d+)", out_gi2)
                            if grp_gi2:
                                pip_new_gi = tuple(int(x) for x in grp_gi2.groups()) >= (22, 3)
                                bsp = ["--break-system-packages"] if pip_new_gi else []
                        except Exception:
                            pass
                        # Retry binary-only with upgraded pip
                        if has_sudo_gi:
                            rc = _gi_sudo_pip("gemmi", ["--only-binary=:all:"] + bsp, "pip-wheel-retry")
                            if rc == 0 and _gi_try_import(): installed = True
                        if not installed:
                            rc = _gi_pip("gemmi", ["--only-binary=:all:", "--user"] + bsp, "pip-wheel-retry")
                            if rc == 0 and _gi_try_import(): installed = True

                    # 4. Source build — only attempt on Python >=3.9 (nanobind requirement)
                    if not installed and has_pip_gi and py_ver >= (3, 9):
                        ev_gi("log", {"text": "[pip] Trying source build (Python >= 3.9)..."})
                        if has_sudo_gi:
                            rc = _gi_sudo_pip("gemmi", bsp, "pip-source")
                            if rc == 0 and _gi_try_import(): installed = True
                        if not installed:
                            rc = _gi_pip("gemmi", ["--user"] + bsp, "pip-source")
                            if rc == 0 and _gi_try_import(): installed = True

                    if installed:
                        gi_ok2, gi_ver2 = _check_gemmi()
                        ev_gi("done", {"success": True, "message": "gemmi installed successfully" + (" (v" + gi_ver2 + ")" if gi_ok2 else "")})
                    else:
                        hint = "pip install gemmi"
                        if py_ver < (3, 9):
                            hint = ("No pre-built gemmi wheel found for Python "
                                    + ".".join(str(x) for x in py_ver)
                                    + " on this platform, and source builds require"
                                    + " Python >= 3.9. Upgrade Python or install"
                                    + " gemmi in a Python >= 3.9 environment.")
                        ev_gi("done", {"success": False, "message": "Could not install gemmi. " + hint})
                except Exception as e:
                    ev_gi("done", {"success": False, "message": "Install error: " + str(e)})

        # SSE stream for POINTLESS (CCP4 space group determination)
        elif path == "/api/pointless/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            input_file = qs.get("input_file", [""])[0]
            if self._refuse_outside(input_file, base=_pdir(project_name) if project_name else None):
                return
            chirality = qs.get("chirality", ["CHIRAL"])[0]
            setting = qs.get("setting", ["SYMMETRY-BASED"])[0]
            lauegroup = qs.get("lauegroup", [""])[0]
            spacegroup = qs.get("spacegroup", [""])[0]
            res_low = qs.get("resolution_low", [""])[0]
            res_high = qs.get("resolution_high", [""])[0]
            self._begin_processing_stream(project_name, "done")
            def write_fn_ptl(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_pointless(
                project_name, write_fn_ptl,
                input_file=input_file or None,
                chirality=chirality,
                setting=setting,
                lauegroup=lauegroup or None,
                spacegroup=spacegroup or None,
                resolution_low=res_low or None,
                resolution_high=res_high or None,
            )

        # Get POINTLESS log file (raw text for new-tab viewer)
        elif project_route == '/pointless-log-raw':
            name = _url_project_name(path.split("/")[3])
            log_file = _pfile(_pdir(name), "pointless.log")
            if log_file.exists():
                try:
                    content = log_file.read_text(encoding="utf-8", errors='replace')
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
            else:
                self.send_json({"error": "pointless.log not found — run POINTLESS first"}, 404)

        # Get POINTLESS log file (JSON for client-side parsing)
        elif project_route == '/pointless-log':
            name = _url_project_name(path.split("/")[3])
            log_file = _pfile(_pdir(name), "pointless.log")
            if log_file.exists():
                try:
                    self.send_json({"content": log_file.read_text(encoding="utf-8", errors='replace')})
                except Exception as e:
                    self.send_json({"error": f"Failed to read pointless.log: {e}"}, 500)
            else:
                self.send_json({"error": "pointless.log not found"}, 404)

        # Cached POINTLESS parsed results (load from saved pointless.log)
        elif project_route == '/pointless-cached':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            try:
                result = load_pointless_cached_results(str(project_dir))
                self.send_json(result)
            except Exception as e:
                self.send_json({"has_results": False, "error": str(e)})

        # ── Anisotropy Analysis endpoint ──────────────────────────────────

        elif project_route == '/anisotropy-analyze':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            n_shells = 15
            try:
                n_shells = int(qs.get("n_shells", ["15"])[0])
            except (ValueError, TypeError):
                pass
            # Find XDS_ASCII.HKL
            hkl_path = _pfile(project_dir, "XDS_ASCII.HKL")
            if not hkl_path.exists():
                self.send_json({"success": False, "error": "XDS_ASCII.HKL not found — run CORRECT first"}, 404)
                return
            try:
                result = analyze_anisotropy(str(hkl_path), n_shells=n_shells)
                self.send_json(result)
            except NameError:
                # Function not available — gemmi not installed or ahkl2mtz not loaded
                self.send_json({"success": False, "error": "gemmi not installed — required for anisotropy analysis"}, 500)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, 500)

        # ── AIMLESS / Scale & Merge endpoints ──────────────────────────────

        # SSE stream for AIMLESS pipeline (POINTLESS → AIMLESS → CTRUNCATE)
        elif path == "/api/aimless/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            res_low = qs.get("resolution_low", [""])[0]
            res_high = qs.get("resolution_high", [""])[0]
            anomalous = qs.get("anomalous", ["on"])[0].lower() in ("on", "true", "1", "yes")
            bins_val = 20
            try: bins_val = int(qs.get("bins", ["20"])[0])
            except ValueError: pass
            run_ptl = qs.get("run_pointless", ["true"])[0].lower() in ("true", "1", "yes")
            run_ctr = qs.get("run_ctruncate", ["true"])[0].lower() in ("true", "1", "yes")
            input_file = qs.get("input_file", [""])[0]
            if self._refuse_outside(input_file, base=_pdir(project_name) if project_name else None):
                return
            self._begin_processing_stream(project_name, "done")
            def write_fn_aml(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_aimless(
                project_name, write_fn_aml,
                resolution_low=res_low or None,
                resolution_high=res_high or None,
                anomalous=anomalous,
                bins=bins_val,
                run_pointless=run_ptl,
                run_ctruncate=run_ctr,
                input_file=input_file or None,
            )

        # Get AIMLESS log file (raw text for new-tab viewer)
        elif project_route == '/aimless-log-raw':
            name = _url_project_name(path.split("/")[3])
            log_file = _pfile(_pdir(name), "aimless.log")
            if log_file.exists():
                try:
                    content = log_file.read_text(encoding="utf-8", errors='replace')
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
            else:
                self.send_json({"error": "aimless.log not found — run AIMLESS first"}, 404)

        # Get AIMLESS log file (JSON for client-side access)
        elif project_route == '/aimless-log':
            name = _url_project_name(path.split("/")[3])
            log_file = _pfile(_pdir(name), "aimless.log")
            if log_file.exists():
                try:
                    self.send_json({"content": log_file.read_text(encoding="utf-8", errors='replace')})
                except Exception as e:
                    self.send_json({"error": f"Failed to read aimless.log: {e}"}, 500)
            else:
                self.send_json({"error": "aimless.log not found"}, 404)

        # Get CTRUNCATE log file
        elif project_route == '/ctruncate-log':
            name = _url_project_name(path.split("/")[3])
            log_file = _pfile(_pdir(name), "ctruncate.log")
            if log_file.exists():
                try:
                    self.send_json({"content": log_file.read_text(encoding="utf-8", errors='replace')})
                except Exception as e:
                    self.send_json({"error": f"Failed to read ctruncate.log: {e}"}, 500)
            else:
                self.send_json({"error": "ctruncate.log not found"}, 404)

        # Cached AIMLESS + CTRUNCATE parsed results (load from saved logs)
        elif project_route == '/aimless-cached':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            try:
                result = load_aimless_cached_results(str(project_dir))
                self.send_json(result)
            except Exception as e:
                self.send_json({"has_results": False, "error": str(e)})

        # ── XDSCC12 / ΔCC½ endpoints ─────────────────────────────────────

        # Check if XDSCC12 binary is available
        elif path == "/api/xdscc12/check":
            import platform as _plat_chk
            global XDSCC12_BIN
            if not XDSCC12_BIN:
                XDSCC12_BIN = _find_xdscc12()
            self.send_json({
                "found": bool(XDSCC12_BIN),
                "path": XDSCC12_BIN or "",
                "can_download": _plat_chk.system() in XDSCC12_URLS,
                "platform": _plat_chk.system(),
            })

        # Run XDSCC12 analysis (SSE stream)
        elif path == "/api/xdscc12/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            batch_width = qs.get("batch_width", ["1"])[0]
            nbin = qs.get("nbin", ["5"])[0]
            self._begin_processing_stream(project_name, "done")
            def write_fn_dcc(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_xdscc12(project_name, write_fn_dcc,
                           batch_width=batch_width, nbin=nbin)

        # Download XDSCC12 binary (SSE stream)
        elif path == "/api/xdscc12/download":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            def write_fn_dcc_dl(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            download_xdscc12(write_fn_dcc_dl)

        # Get cached XDSCC12 results (from previous run)
        elif project_route == '/xdscc12-results':
            name = _url_project_name(path.split("/")[3])
            lp_file = _pfile(_pdir(name), "XDSCC12.LP")
            if lp_file.exists():
                try:
                    content = lp_file.read_text(encoding="utf-8", errors='replace')
                    parsed = LPParser.parse_xdscc12(content)
                    self.send_json(parsed)
                except Exception as e:
                    self.send_json({"error": f"Failed to parse XDSCC12.LP: {e}"}, 500)
            else:
                self.send_json({"error": "XDSCC12.LP not found"}, 404)

        # Get raw XDSCC12.LP text for viewing
        elif project_route == '/xdscc12-lp':
            name = _url_project_name(path.split("/")[3])
            lp_file = _pfile(_pdir(name), "XDSCC12.LP")
            if lp_file.exists():
                try:
                    content = lp_file.read_text(encoding="utf-8", errors='replace')
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
            else:
                self.send_json({"error": "XDSCC12.LP not found — run ΔCC½ analysis first"}, 404)

        # Statistics Table 1 data (combine XDS.INP + XSCALE.LP or CORRECT.LP)
        elif project_route == '/table1data':
            name = _url_project_name(path.split("/")[3])
            qs_t1 = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            lp_source_path = qs_t1.get("lp_source", [""])[0]  # optional override
            project_dir = _pdir(name)
            if self._refuse_outside(lp_source_path, base=project_dir):
                return
            result = {"xdsinp": {}, "xscale": {}, "correct": {}}

            # ── Parse XDS.INP ──────────────────────────────────────
            xds_inp = project_dir / "XDS.INP"
            if xds_inp.exists():
                try:
                    inp_text = xds_inp.read_text(encoding="utf-8", errors='replace')
                    p = _parse_xdsinp_params(inp_text)
                    result["xdsinp"]["detector"] = p.get("DETECTOR", "")
                    result["xdsinp"]["wavelength"] = p.get("X-RAY_WAVELENGTH", "")
                    result["xdsinp"]["oscillation_range"] = p.get("OSCILLATION_RANGE", "")
                    result["xdsinp"]["detector_distance"] = p.get("DETECTOR_DISTANCE", "")
                    result["xdsinp"]["space_group"] = p.get("SPACE_GROUP_NUMBER", "")
                    result["xdsinp"]["unit_cell"] = p.get("UNIT_CELL_CONSTANTS", "")
                    result["xdsinp"]["sensor_thickness"] = p.get("SENSOR_THICKNESS", "")
                    result["xdsinp"]["friedels_law"] = p.get("FRIEDEL'S_LAW", p.get("FRIEDELS_LAW", ""))
                    dr = p.get("DATA_RANGE", "")
                    result["xdsinp"]["data_range"] = dr
                    if dr:
                        parts = dr.split()
                        if len(parts) >= 2:
                            try:
                                n_images = int(parts[1]) - int(parts[0]) + 1
                                result["xdsinp"]["n_images"] = n_images
                                osc = p.get("OSCILLATION_RANGE", "")
                                if osc:
                                    result["xdsinp"]["total_rotation"] = round(n_images * float(osc), 2)
                            except (ValueError, IndexError):
                                pass
                    tmpl = p.get("NAME_TEMPLATE_OF_DATA_FRAMES", "")
                    result["xdsinp"]["name_template"] = tmpl
                except Exception:
                    pass

            # ── Parse CORRECT.LP for ISa and stats if XSCALE not available ──
            correct_lp = _pfile(project_dir, "CORRECT.LP")
            if correct_lp.exists():
                try:
                    content = correct_lp.read_text(encoding="utf-8", errors='replace')
                    cm = LPParser.parse_correct(content)
                    if cm.get("space_group"):
                        result["correct"]["space_group"] = cm["space_group"]
                    if cm.get("unit_cell"):
                        result["correct"]["unit_cell"] = cm["unit_cell"]
                    if cm.get("isa"):
                        result["correct"]["isa"] = cm["isa"]
                    if cm.get("statistics_table"):
                        result["correct"]["statistics_table"] = cm["statistics_table"]
                    if cm.get("wilson_line"):
                        result["correct"]["wilson_line"] = cm["wilson_line"]
                    if cm.get("resolution_range_low"):
                        result["correct"]["resolution_range_low"] = cm["resolution_range_low"]
                    if cm.get("mosaicity") is not None:
                        result["correct"]["mosaicity"] = cm["mosaicity"]
                    result["correct"]["source"] = str(correct_lp)
                    if cm.get("wilson_moments"):
                        result["correct"]["wilson_moments"] = cm["wilson_moments"]
                    if cm.get("aliens"):
                        result["correct"]["aliens"] = cm["aliens"]
                except Exception:
                    pass

            # ── Parse XSCALE.LP (prefer over CORRECT.LP) ──────────
            # If lp_source_path is given, use that specific file instead
            if lp_source_path:
                override_path = Path(lp_source_path)
                if override_path.exists():
                    try:
                        content = override_path.read_text(encoding="utf-8", errors='replace')
                        fname = override_path.name.upper()
                        if "XSCALE" in fname:
                            xm = LPParser.parse_xscale(content)
                            result["xscale"]["source"] = str(override_path)
                            if xm.get("space_group"): result["xscale"]["space_group"] = xm["space_group"]
                            if xm.get("unit_cell"): result["xscale"]["unit_cell"] = xm["unit_cell"]
                            if xm.get("statistics_table"): result["xscale"]["statistics_table"] = xm["statistics_table"]
                            if xm.get("isa_table"): result["xscale"]["isa_table"] = xm["isa_table"]
                            if xm.get("resolution_range_low"): result["xscale"]["resolution_range_low"] = xm["resolution_range_low"]
                        elif "CORRECT" in fname:
                            cm2 = LPParser.parse_correct(content)
                            result["correct"]["source"] = str(override_path)
                            if cm2.get("space_group"): result["correct"]["space_group"] = cm2["space_group"]
                            if cm2.get("unit_cell"): result["correct"]["unit_cell"] = cm2["unit_cell"]
                            if cm2.get("isa"): result["correct"]["isa"] = cm2["isa"]
                            if cm2.get("statistics_table"): result["correct"]["statistics_table"] = cm2["statistics_table"]
                            if cm2.get("wilson_line"): result["correct"]["wilson_line"] = cm2["wilson_line"]
                            result["correct"]["resolution_range_low"] = cm2.get("resolution_range_low")
                            result["correct"]["mosaicity"] = cm2.get("mosaicity")
                            # Clear xscale so CORRECT is used as primary
                            result["xscale"] = {}
                    except Exception:
                        pass
            else:
                xscale_candidates = []
                root_lp = _pfile(project_dir, "XSCALE.LP", "xscale")
                if root_lp.exists():
                    xscale_candidates.append(root_lp)
                try:
                    for child in project_dir.iterdir():
                        if child.is_dir() and child.name.startswith("XSCALE_"):
                            sub_lp = child / "XSCALE.LP"
                            if sub_lp.exists():
                                xscale_candidates.append(sub_lp)
                except OSError:
                    pass
                if xscale_candidates:
                    lp_file = max(xscale_candidates, key=lambda pp: pp.stat().st_mtime)
                    try:
                        content = lp_file.read_text(encoding="utf-8", errors='replace')
                        xm = LPParser.parse_xscale(content)
                        result["xscale"]["source"] = str(lp_file)
                        if xm.get("space_group"):
                            result["xscale"]["space_group"] = xm["space_group"]
                        if xm.get("unit_cell"):
                            result["xscale"]["unit_cell"] = xm["unit_cell"]
                        if xm.get("statistics_table"):
                            result["xscale"]["statistics_table"] = xm["statistics_table"]
                        if xm.get("isa_table"):
                            result["xscale"]["isa_table"] = xm["isa_table"]
                        if xm.get("resolution_range_low"):
                            result["xscale"]["resolution_range_low"] = xm["resolution_range_low"]
                    except Exception:
                        pass

            # Exact R-pim from the unmerged reflections (asked for separately:
            # a 200 MB file on a network share takes a while to read).
            if qs_t1.get("rpim", [""])[0] == "1":
                result["rpim"] = _table1_rpim_for(result)

            self.send_json(result)

        # ── AutoPilot endpoints ────────────────────────────────────────────
        # SSE stream: run full autopilot pipeline
        elif path == "/api/autopilot/stream":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            criterion = qs.get("criterion", ["isig2"])[0]
            if criterion not in ("isig2", "cc_half_50", "r_obs_55", "cc_half_sig"):
                criterion = "isig2"
            friedel = qs.get("friedel", ["FALSE"])[0].upper()
            if friedel not in ("TRUE", "FALSE"):
                friedel = "FALSE"
            template = qs.get("template", [None])[0]
            optimize = qs.get("optimize", ["1"])[0] == "1"
            dcc_half = qs.get("dcc_half", ["1"])[0] == "1"
            neggia_lib = qs.get("neggia_lib", [""])[0] or NEGGIA_LIB
            if self._refuse_outside(template, base=_pdir(project_name) if project_name else None):
                return
            self._begin_processing_stream(project_name, "ap_done")
            def write_fn_ap(s):
                try: self.wfile.write(s.encode()); self.wfile.flush()
                except Exception: pass
            stream_autopilot(project_name, write_fn_ap, criterion=criterion, friedel=friedel, template=template, optimize=optimize, dcc_half=dcc_half, neggia_lib=neggia_lib)

        # Cached autopilot results
        elif project_route == '/autopilot-cached':
            name = _url_project_name(path.split("/")[3])
            project_dir = _pdir(name)
            try:
                result = load_autopilot_cached_results(str(project_dir))
                self.send_json(result)
            except Exception as e:
                self.send_json({"has_results": False, "error": str(e)})

        # Autopilot status (lightweight check without streaming)
        elif path == "/api/autopilot/status":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            project_name = qs.get("project", [""])[0]
            if not project_name:
                # asked without a project (e.g. right after start-up): nothing to report
                self.send_json({"running": False, "has_results": False})
                return
            project_dir = _pdir(project_name)
            result_file = _pfile(project_dir, "AUTOPILOT_RESULTS.json")
            running = _jobs_running(project_name, kind="autopilot")
            if result_file.exists():
                try:
                    data = json.loads(_read_text_lenient(result_file))
                    self.send_json({"running": running, "has_results": True, "status": data.get("status", "unknown")})
                except Exception:
                    self.send_json({"running": running, "has_results": False})
            else:
                self.send_json({"running": running, "has_results": False})

        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        self._guarded(self._do_POST)

    def _do_POST(self):
        """Handle POST requests"""
        global xds_runner, CCP4_BIN, CCP4_BIN_SAVED, NEGGIA_LIB, XDS_PARALLEL
        
        path = urllib.parse.urlparse(self.path).path
        project_route = self._project_route(path)
        
        # Read body
        length = int(self.headers.get("Content-Length", 0))
        if length < 0:
            raise ValueError("Content-Length must be nonnegative")
        body = self.rfile.read(length).decode() if length > 0 else "{}"
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError) as e:
            self.send_json({"error": f"Invalid JSON: {e}"}, 400)
            return
        if not isinstance(data, dict):
            self.send_json({"error": "Request body must be a JSON object"}, 400)
            return
        
        with _directory_reservation(self._write_paths(path, data)):
            self._dispatch_POST(path, data)

    def _write_paths(self, path, data):
        if self._project_route(path) is not None:
            return [_pdir(_url_project_name(path.split("/")[3]))]
        if path in ("/api/run-folder", "/api/xscale-run-folder"):
            paths = [_pdir(data.get("project_name"))]
            if data.get("folder"):
                paths.append(Path(data["folder"]))
            return paths
        if path in ("/api/gemmi/deposition", "/api/gemmi/polarization") and data.get("project"):
            p = _pdir(data["project"])
            return [p, _project_out_dir(p)]
        if path == "/api/export" and data.get("project"):
            return [_pdir(data["project"])]
        if path == "/api/figures" and data.get("project"):
            p = _pdir(data["project"])
            return [p, _figure_source(p, data.get("source", "CORRECT"))[1]]
        return []

    def _dispatch_POST(self, path, data):
        global xds_runner, CCP4_BIN, CCP4_BIN_SAVED, NEGGIA_LIB, XDS_PARALLEL, CPU_CORES, RAM_LIMIT_GB
        project_route = self._project_route(path)
        # Create project
        if path == "/api/projects":
            try:
                # the data folder may be typed as a Windows path (D:\data\...)
                data_path = data.get("data_path", "")
                if data_path:
                    data_path = _to_local_path(data_path)[0]
                result = ProjectManager.create(
                    data["name"],
                    data.get("description", ""),
                    data_path
                )
                self.send_json(result)
            except ValueError as e:
                self.send_json({"error": str(e)}, 400)
        
        # Run XDS
        elif path == "/api/run":
            project_name = data.get("project_name", "")
            step = data.get("step")
            stop_at = data.get("stop_at")
            if not project_name:
                self.send_json({"error": "project_name required"}, 400); return
            if (step and step not in XDS_PIPELINE) or (stop_at and stop_at not in XDS_PIPELINE):
                self.send_json({"error": "Unknown step"}, 400); return

            if step:
                result = xds_runner.run_step(project_name, step)
                self.send_json({"results": [result]})
            else:
                results = xds_runner.run_pipeline(project_name, stop_at=stop_at)
                self.send_json({"results": results})
        
        # Stop running XDS process
        elif path == "/api/stop":
            # Stop the program of one project (project_name given) or all of them.
            # The whole process group is killed, so xds_par's forkxds children go too.
            key = data.get("project_name")
            # kind: stop only that program (xds, xscale, xdsconv, ...) - the XSCALE tab's Stop
            # must not end an XDS or AutoPilot run of the same project
            kind = data.get("kind") or None
            if kind not in (None, "xds", "xscale", "xdsconv", "gemmi", "pointless", "aimless", "xdscc12", "autoindex", "autopilot"):
                self.send_json({"error": "Unknown program kind: " + str(kind)}, 400)
                return
            try:
                n = _stop_procs(key if key else None, kind=kind)
                self.send_json({"message": ("Process terminated" if n else "No process running"), "stopped": n})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Stop auto-indexing
        elif path == "/api/autoindex/stop":
            _stop_procs(data.get("project_name") or None, kind="autoindex")
            self.send_json({"message": "Auto-indexing stop requested"})

        # Stop autopilot
        elif path == "/api/autopilot/stop":
            _stop_procs(data.get("project_name") or None, kind="autopilot")
            self.send_json({"message": "AutoPilot stop requested"})

        # Set up a run folder: create it, copy XDS.INP into it
        elif path == "/api/run-folder":
            project_name = data.get("project_name", "")
            folder_path  = data.get("folder", "")
            if not project_name or not folder_path:
                self.send_json({"error": "project_name and folder required"}, 400)
                return
            if self._refuse_outside(folder_path, base=_pdir(project_name)):
                return
            try:
                project_dir = _pdir(project_name)
                run_dir = Path(folder_path)
                run_dir.mkdir(parents=True, exist_ok=True)
                # Copy XDS.INP from project into run folder
                src_inp = project_dir / "XDS.INP"
                if src_inp.exists():
                    shutil.copy2(str(src_inp), str(run_dir / "XDS.INP"))
                self.send_json({"message": "Run folder ready", "path": str(run_dir)})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Create XSCALE run subfolder and copy XSCALE.INP into it
        elif path == "/api/xscale-run-folder":
            project_name = data.get("project_name", "")
            if not project_name:
                self.send_json({"error": "project_name required"}, 400)
                return
            try:
                project_dir = _pdir(project_name)
                # Find next XSCALE_NNN number
                next_num = 1
                if project_dir.is_dir():
                    for child in project_dir.iterdir():
                        if child.is_dir() and child.name.startswith("XSCALE_"):
                            try:
                                n = int(child.name.split("_", 1)[1])
                                if n >= next_num:
                                    next_num = n + 1
                            except (ValueError, IndexError):
                                pass
                folder_name = f"XSCALE_{next_num:03d}"
                run_dir = project_dir / folder_name
                run_dir.mkdir(parents=True, exist_ok=True)
                # Copy XSCALE.INP and fix INPUT_FILE paths for subfolder context
                src_inp = project_dir / "XSCALE.INP"
                if src_inp.exists():
                    shutil.copy2(str(src_inp), str(run_dir / "XSCALE.INP"))
                    # Rewrite relative INPUT_FILE= paths to resolve from subfolder
                    try:
                        relback = os.path.relpath(str(project_dir), str(run_dir))
                        dest_inp = run_dir / "XSCALE.INP"
                        inp_text = dest_inp.read_text(encoding="utf-8", errors='replace')
                        _write_inp(dest_inp, _xscale_inputs_from_subfolder(inp_text, relback))
                    except Exception:
                        pass  # If rewrite fails, keep the copied file as-is
                self.send_json({"message": f"Created {folder_name}", "path": str(run_dir), "folder_name": folder_name})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # List existing sub-run folders and find next auto-number
        elif path == "/api/run-folder/list":
            project_name = data.get("project_name", "")
            base_folder  = data.get("base_folder", "")
            if not base_folder:
                self.send_json({"error": "base_folder required"}, 400)
                return
            if self._refuse_outside(base_folder, base=_pdir(project_name) if project_name else None):
                return
            try:
                base = Path(base_folder)
                existing = []
                next_num = 1
                if base.is_dir():
                    for child in sorted(base.iterdir()):
                        if child.is_dir():
                            existing.append(child.name)
                            # Track highest numeric folder
                            try:
                                n = int(child.name)
                                if n >= next_num:
                                    next_num = n + 1
                            except ValueError:
                                pass
                self.send_json({"existing": existing, "next_num": next_num})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Update config
        elif path == "/api/config":
            # What the user typed is cleaned up first (blanks, quotes, ~, a
            # folder instead of the file) and has to exist.  Storing a path
            # that is then dropped without a word at the next start is what
            # made the reader path look like it was never saved.
            neggia = data.get("neggia_lib")
            if neggia is not None:
                neggia = _clean_path_setting(neggia, NEGGIA_NAMES)
                if neggia and not Path(neggia).is_file():
                    self.send_json({"error": "No file at " + neggia +
                                             ". Give the full path of dectris-neggia.so (or the folder it is in)."}, 400)
                    return
            new_path = data.get("xds_path")
            if new_path:
                new_path = _clean_path_setting(new_path) or new_path
                if not Path(new_path).is_dir():
                    self.send_json({"error": "No folder at " + new_path +
                                             ". Give the folder that contains xds_par (or xds)."}, 400)
                    return
                xds_runner = XDSRunner(new_path)
            ccp4 = data.get("ccp4_bin")
            if ccp4 is not None:
                # the user may give the CCP4 root or its bin folder
                ccp4 = _clean_path_setting(ccp4)
                if ccp4 and not _is_ccp4_bin(ccp4):
                    import glob as _glob_ccp4
                    _alt = [str(Path(ccp4) / "bin")]
                    _alt += sorted(_glob_ccp4.glob(str(Path(ccp4) / "[Cc][Cc][Pp]4*" / "bin")), reverse=True)
                    _alt += sorted(_glob_ccp4.glob(str(Path(ccp4) / "[Cc][Cc][Pp]4*" / "*" / "bin")), reverse=True)
                    _alt += sorted(_glob_ccp4.glob(str(Path(ccp4) / "*" / "bin")), reverse=True)   # CCP4 for Windows: CCP4-9/9.0/bin
                    _hit = next((a for a in _alt if _is_ccp4_bin(a)), "")
                    if not _hit:
                        _win = any(Path(d, p + ".exe").is_file() for d in [ccp4] + _alt for p in CCP4_PROGRAMS)
                        self.send_json({"error": ("The folder " + ccp4 + " holds CCP4 for Windows (.exe programs), which cannot run on Linux. Install the Linux CCP4."
                                                  if _win else "No CCP4 programs in " + ccp4 +
                                                 ". Give the CCP4 folder or its bin folder (the one with pointless, aimless, ctruncate).")}, 400)
                        return
                    ccp4 = _hit
                CCP4_BIN = CCP4_BIN_SAVED = ccp4
            if neggia is not None:
                NEGGIA_LIB = neggia
            par = data.get("parallel")
            if par is not None:
                XDS_PARALLEL = bool(par)
            # CPU cores and RAM for the programs; the next run uses them
            cores, ram = data.get("cpu_cores"), data.get("ram_gb")
            try:
                if cores is not None:
                    CPU_CORES = _clamp_cpu_cores(cores)
                if ram is not None:
                    RAM_LIMIT_GB = _clamp_ram_gb(ram)
            except (TypeError, ValueError):
                self.send_json({"error": "CPU cores and RAM must be numbers"}, 400)
                return
            if (cores is not None or ram is not None) and _ram_limit_mode()[0] == 'cgroup':
                _apply_cgroup_limits()          # running programs follow at once
            if cores is not None:
                _sync_cpu_keywords_all_projects()   # XDS.INP / XSCALE.INP of every project
            # The Environment screen's "Don't show this again": kept per
            # machine, so it also holds when the page is opened in another
            # browser (on Linux the launcher may not reuse the same one).
            env_seen = data.get("env_seen")
            # Remember these choices for the next start (per machine)
            _save_settings(xds_path=str(xds_runner.xds_path) if new_path else None,
                           ccp4_bin=ccp4, neggia_lib=neggia, env_seen=env_seen,
                           parallel=(bool(par) if par is not None else None),
                           cpu_cores=(CPU_CORES if cores is not None else None),
                           ram_gb=(RAM_LIMIT_GB if ram is not None else None))
            self.send_json({"message": "Config updated", "xds_path": str(xds_runner.xds_path), "ccp4_bin": CCP4_BIN,
                            "neggia_lib": NEGGIA_LIB, "parallel": XDS_PARALLEL, "settings_file": str(SETTINGS_FILE),
                            "resources": _resource_info()})

        # Gemmi analysis: merging stats, completeness, lattice symmetry
        elif path == "/api/batch/discover":
            folder = batch_local_path(data.get("folder"))
            if not folder:
                self.send_json({"error": "Choose a folder to search"}, 400); return
            target = Path(folder).expanduser().resolve()
            if not self._batch_path_allowed(target):
                self.send_json({"error": "This installation only lists folders inside the projects folder"}, 403); return
            if not target.is_dir():
                self.send_json({"error": "Not a folder on this computer: " + folder}, 400); return
            try:
                depth = max(0, min(int(data.get("depth", 3)), 6))
            except (TypeError, ValueError):
                depth = 3
            datasets = discover_datasets(target, max_depth=depth)
            self.send_json({"folder": str(target), "datasets": datasets})

        elif path == "/api/batch/locate-folder":
            hints = [h for h in (data.get("hints") or []) if isinstance(h, str)][:20]
            found, complete = locate_dropped_folder(data.get("name"), data.get("files") or [], hints,
                                                    PROJECTS_DIR.resolve() if RESTRICT_BROWSE else None)
            self.send_json({"folders": found, "complete": complete})

        elif path == "/api/batch/xdsinp-search":
            datasets = [d for d in (data.get("datasets") or []) if isinstance(d, dict) and d.get("template")]
            roots = [r for r in (batch_local_path(x) for x in (data.get("roots") or [])) if r]
            if not all(self._batch_path_allowed(Path(r).expanduser()) for r in roots) or \
               not all(self._batch_path_allowed(Path(str(d["template"])).parent) for d in datasets) or \
               not all(self._batch_path_allowed(Path(str(d["folder"]))) for d in datasets if d.get("folder")):
                self.send_json({"error": "This installation only searches inside the projects folder"}, 403); return
            keywords = data.get("keywords")
            self.send_json(find_xdsinp_candidates(datasets, roots, keywords if isinstance(keywords, list) else None))

        elif path == "/api/batch/xdsinp-preview":
            dataset = data.get("dataset") or {}
            source = Path(str(data.get("path") or ""))
            if not dataset.get("template") or not source.is_file() or source.name.upper() != "XDS.INP" \
               or not self._batch_path_allowed(source.resolve()):
                self.send_json({"error": "Choose an XDS.INP of this data set"}, 400); return
            neggia = NEGGIA_LIB if str(dataset["template"]).lower().endswith((".h5", ".hdf5")) else ""
            text, notes = import_xdsinp(source, dataset, neggia)
            # the preview is the file as it will be written, CPU cores included
            self.send_json({"content": _with_cpu_keywords(text, "xds"), "notes": notes, "original": _read_text_lenient(source)})

        elif path == "/api/batch/create":
            for d in (data.get("datasets") or []):
                if isinstance(d, dict) and self._refuse_outside(d.get("template"), d.get("xdsinp"), d.get("folder")):
                    return
            state = batch_create(data.get("name", ""), data.get("datasets") or [], data.get("strategy") or {},
                                 data.get("search") or {})
            self.send_json(state)

        elif path == "/api/batch/start":
            self.send_json(batch_start(str(data.get("id", ""))))

        elif path == "/api/batch/stop":
            self.send_json(batch_stop(str(data.get("id", ""))))

        elif path == "/api/batch/skip":
            self.send_json(batch_stop(str(data.get("id", "")), skip_only=True))

        elif path == "/api/batch/merge-plan":
            state = batch_load(str(data.get("id", "")))
            strategy = normalize_strategy(state.get("strategy"))
            plan = merge_plan(data.get("projects") or [], strategy["criterion"], data.get("reference") or None)
            # the preview names the inputs exactly as the merge will, so it can be read as the real file
            preview = (_with_cpu_keywords(merge_xscale_inp(plan, data.get("friedel") or strategy["friedel"], merge_input_names(plan)), "xscale")
                       if len(plan["inputs"]) >= 1 else "")
            self.send_json({"plan": plan, "xscale_inp": preview})

        elif path == "/api/batch/merge":
            self.send_json(batch_merge(str(data.get("id", "")), data.get("projects") or [],
                                       data.get("reference") or None, data.get("friedel") or None))

        elif path == "/api/bug-report":
            project = str(data.get("project") or "")
            if project:
                ProjectManager.get(project)          # 404 for an unknown project
            errors = data.get("page_errors") or []
            if not isinstance(errors, list):
                errors = []
            self.send_json(build_problem_report(data.get("description", ""), project=project,
                                                include_project=bool(data.get("include_project")),
                                                page_errors=errors))

        elif path == "/api/export":
            project = data.get("project", "")
            reflections = bool(data.get("reflections", True))
            ProjectManager.get(project)             # 404 for an unknown project
            result = export_project(project, reflections=reflections)
            result["reflections"] = reflections
            self.send_json(result)

        elif path == "/api/figures":
            project = data.get("project", "")
            source = str(data.get("source", "CORRECT") or "CORRECT").upper()
            wanted = data.get("metrics") or None
            if source not in ("CORRECT", "XSCALE"):
                self.send_json({"error": "source must be CORRECT or XSCALE"}, 400); return
            ProjectManager.get(project)            # 404 for an unknown project
            project_dir = _pdir(project)
            lp_path, out_dir = _figure_source(project_dir, source)
            if not lp_path or not Path(lp_path).is_file():
                self.send_json({"error": source + ".LP not found for this project - run it first"}, 404); return
            try:
                result = publication_figures(lp_path, out_dir, source=source, metrics=wanted)
            except RuntimeError as e:
                self.send_json({"error": str(e)}, 503 if "matplotlib" in str(e) else 400); return
            result["source"] = source
            result["source_lp"] = str(lp_path)
            result["out_dir"] = str(out_dir)
            self.send_json(result)

        elif path == "/api/gemmi/analyze":
            analysis = data.get("analysis")  # "merging_stats", "completeness", "lattice_symmetry"
            project = data.get("project", "")
            work_dir = data.get("work_dir", "")
            input_file = data.get("input_file", "")
            if self._refuse_outside(work_dir, input_file, base=_pdir(project) if project else None):
                return
            n_shells = int(data.get("n_shells", 20))
            weighting = data.get("weighting", "X")
            max_obliq = float(data.get("max_obliquity", 3.0))
            # Resolution range: res_low = low-res limit (large d), res_high = high-res limit (small d)
            res_low = data.get("res_low")
            res_high = data.get("res_high")
            if res_low is not None:
                try: res_low = float(res_low)
                except (TypeError, ValueError): res_low = None
            if res_high is not None:
                try: res_high = float(res_high)
                except (TypeError, ValueError): res_high = None

            # Resolve input file
            hkl_path = None
            if input_file:
                p = Path(input_file)
                if p.is_absolute() and p.exists():
                    hkl_path = str(p)
            if not hkl_path and work_dir:
                wd = Path(work_dir)
                for name in ["XDS_ASCII.HKL", "INTEGRATE.HKL"]:
                    candidate = wd / name
                    if candidate.exists():
                        hkl_path = str(candidate)
                        break
            if not hkl_path and project:
                proj_dir = _pdir(project)
                for name in ["XDS_ASCII.HKL", "INTEGRATE.HKL"]:
                    candidate = _pfile(proj_dir, name)
                    if candidate.exists():
                        hkl_path = str(candidate)
                        break

            if not hkl_path:
                self.send_json({"success": False, "message": "No XDS_ASCII.HKL found"}, 400)
                return

            ok, info = _check_gemmi()
            if not ok:
                self.send_json({"success": False, "message": "gemmi not available: " + info}, 400)
                return

            try:
                if analysis == "merging_stats":
                    result = analyze_merging_stats(hkl_path, n_shells=n_shells, weighting=weighting, res_low=res_low, res_high=res_high)
                elif analysis == "completeness":
                    result = analyze_completeness(hkl_path, n_shells=n_shells, res_low=res_low, res_high=res_high)
                elif analysis == "data_quality":
                    result = analyze_data_quality(hkl_path, n_shells=n_shells, weighting=weighting, res_low=res_low, res_high=res_high)
                elif analysis == "lattice_symmetry":
                    result = analyze_lattice_symmetry(hkl_path, max_obliq=max_obliq)
                else:
                    self.send_json({"success": False, "message": "Unknown analysis: " + str(analysis)}, 400)
                    return
                result["input_file"] = hkl_path
                self.send_json(result)
            except Exception as e:
                import traceback
                self.send_json({"success": False, "message": str(e), "traceback": traceback.format_exc()}, 500)

        # Gemmi: anomalous scattering factors
        elif path == "/api/gemmi/anomalous":
            element = data.get("element", "")
            wavelength = data.get("wavelength")
            energy = data.get("energy")
            scan_range = float(data.get("scan_range", 200))
            try:
                wl = float(wavelength) if wavelength else None
            except (TypeError, ValueError):
                wl = None
            try:
                ev = float(energy) if energy else None
            except (TypeError, ValueError):
                ev = None

            ok, info = _check_gemmi()
            if not ok:
                self.send_json({"success": False, "message": "gemmi not available: " + info}, 400)
                return

            try:
                result = compute_anomalous_scattering(element, wl, energy_ev=ev, scan_range_ev=scan_range)
                self.send_json(result)
            except Exception as e:
                self.send_json({"success": False, "message": str(e)}, 500)

        # Gemmi: prepare PDB deposition mmCIF
        elif path == "/api/gemmi/deposition":
            project = data.get("project", "")
            input_file = data.get("input_file", "")
            merged_mtz = data.get("merged_mtz", "")
            if self._refuse_outside(input_file, merged_mtz, base=_pdir(project) if project else None):
                return

            # Resolve input HKL file
            hkl_path = None
            if input_file:
                p = Path(input_file)
                if p.is_absolute() and p.exists():
                    hkl_path = str(p)
            if not hkl_path and project:
                proj_dir = _pdir(project)
                for nm in ["XDS_ASCII.HKL"]:
                    cand = _pfile(proj_dir, nm)      # the run folder's copy when XDS ran in one
                    if cand.exists():
                        hkl_path = str(cand)
                        break
            if not hkl_path:
                self.send_json({"success": False, "message": "No XDS_ASCII.HKL found"}, 400)
                return

            # Resolve merged MTZ path (optional)
            mtz_path = None
            if merged_mtz:
                mp = Path(merged_mtz)
                if mp.is_absolute() and mp.exists():
                    mtz_path = str(mp)
            if not mtz_path and project:
                # Auto-detect common merged MTZ names in project dir
                proj_dir = _pdir(project)
                for nm in ["XDS_ASCII.mtz", "merged.mtz", "F_SIGF.mtz"]:
                    cand = proj_dir / nm
                    if cand.exists():
                        mtz_path = str(cand)
                        break
                # Also check XSCALE subdirs
                if not mtz_path:
                    try:
                        for child in proj_dir.iterdir():
                            if child.is_dir() and child.name.startswith("XSCALE_"):
                                for nm in ["XDS_ASCII.mtz", "merged.mtz", "F_SIGF.mtz"]:
                                    cand = child / nm
                                    if cand.exists():
                                        mtz_path = str(cand)
                                        break
                            if mtz_path:
                                break
                    except OSError:
                        pass

            ok, info = _check_gemmi()
            if not ok:
                self.send_json({"success": False, "message": "gemmi not available: " + info}, 400)
                return

            try:
                result = prepare_deposition_cif(hkl_path, merged_mtz_path=mtz_path)
                self.send_json(result)
            except Exception as e:
                import traceback
                self.send_json({"success": False, "message": str(e), "traceback": traceback.format_exc()}, 500)
        
        # Gemmi: polarization correction
        elif path == "/api/gemmi/polarization":
            project = data.get("project", "")
            input_file = data.get("input_file", "")
            if self._refuse_outside(input_file, base=_pdir(project) if project else None):
                return
            polarization = float(data.get("polarization", 0.99))
            normal = data.get("normal", [0, 1, 0])
            if isinstance(normal, list) and len(normal) == 3:
                normal = tuple(float(x) for x in normal)
            else:
                normal = (0, 1, 0)

            # Resolve input HKL
            hkl_path = None
            if input_file:
                p = Path(input_file)
                if p.is_absolute() and p.exists():
                    hkl_path = str(p)
            if not hkl_path and project:
                proj_dir = _pdir(project)
                for nm in ["XDS_ASCII.HKL"]:
                    cand = _pfile(proj_dir, nm)      # the run folder's copy when XDS ran in one
                    if cand.exists():
                        hkl_path = str(cand)
                        break
            if not hkl_path:
                self.send_json({"success": False, "message": "No XDS_ASCII.HKL found"}, 400)
                return

            ok, info = _check_gemmi()
            if not ok:
                self.send_json({"success": False, "message": "gemmi not available: " + info}, 400)
                return

            try:
                result = apply_polarization_and_compare(hkl_path, polarization=polarization, normal=normal)
                self.send_json(result)
            except Exception as e:
                import traceback
                self.send_json({"success": False, "message": str(e), "traceback": traceback.format_exc()}, 500)
        
        # Open a folder in the desktop file manager (Explorer via WSL interop, xdg-open, ...)
        elif path == "/api/open-folder":
            target = str((data or {}).get("path") or "")
            dry = bool((data or {}).get("dry"))
            if not target:
                self.send_json({"error": "path required"}, 400); return
            if self._refuse_outside(target):
                return
            ok, info = _open_in_file_manager(target, dry_run=dry)
            self.send_json({"ok": ok, "info": info, "windows_view": _windows_view(target)}, 200 if ok else 500)

        # Per-project interface settings remembered in metadata.json
        elif project_route == '/settings':
            name = _url_project_name(path.split("/")[3])
            allowed = {"viewer_template"}
            updates = {k: str(v) for k, v in (data or {}).items() if k in allowed}
            try:
                if updates:
                    ProjectManager.update(name, updates)
                self.send_json({"message": "Settings saved", "updated": sorted(updates)})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Save individual parameters (must come before /xdsinp catch-all)
        elif project_route == '/xdsinp/params':
            name = _url_project_name(path.split("/")[3])
            xds_inp = _pdir(name) / "XDS.INP"
            params = data.get("params", {})
            try:
                content2 = _read_text_lenient(xds_inp) if xds_inp.exists() else ""
                content2 = XDSINPEditor.apply_params(content2, params)
                _write_inp(xds_inp, content2)
                self.send_json({"message": "Parameters saved"})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Save full XDS.INP
        elif project_route == '/xdsinp':
            name = _url_project_name(path.split("/")[3])
            xds_inp = _pdir(name) / "XDS.INP"
            try:
                _write_inp(xds_inp, data["content"])
                self.send_json({"message": "XDS.INP saved", "content": _read_text_lenient(xds_inp)})
            except Exception as e:
                self.send_json({"error": f"Failed to save XDS.INP: {e}"}, 500)

        # Save XSCALE.INP params (merge into existing file)
        elif project_route == '/xscaleinp/params':
            name = _url_project_name(path.split("/")[3])
            xscale_inp = _pdir(name) / "XSCALE.INP"
            params = data.get("params", {})
            try:
                # fresh=true ("Save new XSCALE.INP"): start from an empty file so
                # the writer lays every keyword out in its XSCALE section.
                content2 = "" if data.get("fresh") else (xscale_inp.read_text(encoding="utf-8", errors='replace') if xscale_inp.exists() else "")
                # No input files chosen: default to this project's XDS_ASCII.HKL
                # (wherever the last XDS run wrote it) when the file has none yet.
                if isinstance(params.get("INPUT_FILE"), list) and not [f for f in params["INPUT_FILE"] if str(f).strip()]:
                    has_input = any(_xscale_key(l) == "INPUT_FILE" and not l.strip().startswith("!") for l in content2.split("\n"))
                    hkl = _pfile(_pdir(name), "XDS_ASCII.HKL")
                    if not has_input and hkl.exists():
                        params["INPUT_FILE"] = [str(hkl)]
                    else:
                        params.pop("INPUT_FILE")
                content2 = _xscale_apply_params(content2, params)
                _write_inp(xscale_inp, content2)
                self.send_json({"message": "Parameters updated in XSCALE.INP"})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Save full XSCALE.INP
        elif project_route == '/xscaleinp':
            name = _url_project_name(path.split("/")[3])
            xscale_inp = _pdir(name) / "XSCALE.INP"
            try:
                _write_inp(xscale_inp, data["content"])
                self.send_json({"message": "XSCALE.INP saved", "content": _read_text_lenient(xscale_inp)})
            except Exception as e:
                self.send_json({"error": f"Failed to save XSCALE.INP: {e}"}, 500)

        # Save XDSCONV.INP
        elif project_route == '/xdsconvinp':
            name = _url_project_name(path.split("/")[3])
            xdsconv_inp = _pdir(name) / "XDSCONV.INP"
            try:
                xdsconv_inp.write_text(data["content"], encoding="utf-8")
                self.send_json({"message": "XDSCONV.INP saved"})
            except Exception as e:
                self.send_json({"error": f"Failed to save XDSCONV.INP: {e}"}, 500)

        elif project_route == '/export-table1':
            try:
                name = _url_project_name(path.split("/")[3])
                rows = data.get("rows", [])
                if not rows:
                    self.send_json({"error": "No data to export"}, 400)
                    return
                import csv
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(['Parameter', 'Value'])
                for row in rows:
                    if len(row) >= 2:
                        param = row[0].lstrip('# ') if row[0].startswith('#') else row[0]
                        w.writerow([param, row[1]])
                csv_data = buf.getvalue().encode('utf-8')
                fname = f"{name}_Table1.csv"
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.send_header('Content-Length', str(len(csv_data)))
                self.end_headers()
                self.wfile.write(csv_data)
            except Exception as e:
                self.send_json({"error": f"Export failed: {e}"}, 500)

        # Compare current IDXREF.LP with user-uploaded LP file
        elif project_route == '/compare-idxref-file':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                current_lp = _pfile(project_dir, "IDXREF.LP")
                if not current_lp.exists():
                    self.send_json({"error": "IDXREF.LP not found"}, 404)
                    return
                uploaded_content = data.get("lp_content", "")
                if not uploaded_content:
                    self.send_json({"error": "No file content provided"}, 400)
                    return
                cur_content = current_lp.read_text(encoding="utf-8", errors="replace")
                cur_metrics = LPParser.parse_idxref(cur_content)
                ref_metrics = LPParser.parse_idxref(uploaded_content)
                def _sum_i(m):
                    s = {}
                    if m.get('indexed_count') is not None and m.get('total_spots') is not None:
                        s['indexed_count'] = m['indexed_count']
                        s['total_spots'] = m['total_spots']
                        s['indexed_pct'] = round(m['indexed_count'] / m['total_spots'] * 100, 1) if m['total_spots'] > 0 else 0
                    for k in ('sigma_spot', 'sigma_spindle', 'orgx', 'orgy', 'detector_distance',
                              'orgx_initial', 'orgy_initial', 'detector_distance_initial'):
                        if m.get(k) is not None:
                            s[k] = m[k]
                    lats = m.get('lattices', [])
                    if lats:
                        sel = lats[0]
                        s['lattice'] = sel.get('bravais', '')
                        s['quality'] = sel.get('quality', '')
                        s['unit_cell'] = [sel.get('a',''), sel.get('b',''), sel.get('c',''),
                                          sel.get('alpha',''), sel.get('beta',''), sel.get('gamma','')]
                    return s
                cur_time = os.path.getmtime(str(current_lp))
                self.send_json({
                    "current": _sum_i(cur_metrics),
                    "current_time": datetime.fromtimestamp(cur_time).strftime("%Y-%m-%d %H:%M"),
                    "previous": _sum_i(ref_metrics),
                    "previous_time": data.get("filename", "uploaded file"),
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Compare current CORRECT.LP with user-uploaded LP file
        elif project_route == '/compare-correct-file':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                current_lp = _pfile(project_dir, "CORRECT.LP")
                if not current_lp.exists():
                    self.send_json({"error": "CORRECT.LP not found"}, 404)
                    return
                uploaded_content = data.get("lp_content", "")
                if not uploaded_content:
                    self.send_json({"error": "No file content provided"}, 400)
                    return
                cur_content = current_lp.read_text(encoding="utf-8", errors="replace")
                cur_metrics = LPParser.parse_correct(cur_content)
                ref_metrics = LPParser.parse_correct(uploaded_content)
                def _sk(row):
                    return {k: row.get(k, '') for k in ('resolution','completeness','r_meas','i_sigma','cc_half','r_obs','siganom')}
                def _sum_c(m):
                    s = {}
                    s['space_group'] = m.get('space_group', '')
                    uc = m.get('unit_cell')
                    if uc:
                        s['unit_cell'] = [uc.get(k,0) for k in ('a','b','c','alpha','beta','gamma')]
                    isa = m.get('isa')
                    if isa: s['isa'] = isa.get('isa', '')
                    wl = m.get('wilson_line')
                    if wl: s['wilson_b'] = wl.get('b', '')
                    s['chi2_values'] = m.get('chi2_values', [])
                    s['mosaicity'] = m.get('mosaicity', '')
                    fl = m.get('friedels_law', '')
                    if fl: s['friedels_law'] = fl
                    tbl = m.get('statistics_table', [])
                    if tbl:
                        shells = [r for r in tbl if r.get('resolution','').lower() != 'total']
                        total = [r for r in tbl if r.get('resolution','').lower() == 'total']
                        if total: s['overall'] = _sk(total[0])
                        elif shells: s['overall'] = _sk(shells[0])
                        if len(shells) >= 1: s['inner'] = _sk(shells[0])
                        if len(shells) >= 2: s['outer'] = _sk(shells[-1])
                    return s
                cur_time = os.path.getmtime(str(current_lp))
                self.send_json({
                    "current": _sum_c(cur_metrics),
                    "current_time": datetime.fromtimestamp(cur_time).strftime("%Y-%m-%d %H:%M"),
                    "previous": _sum_c(ref_metrics),
                    "previous_time": data.get("filename", "uploaded file"),
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        # Compare current XSCALE.LP with user-uploaded LP file
        elif project_route == '/compare-xscale-file':
            try:
                name = _url_project_name(path.split("/")[3])
                project_dir = _pdir(name)
                candidates = []
                root_lp = _pfile(project_dir, "XSCALE.LP", "xscale")
                if root_lp.exists(): candidates.append(root_lp)
                try:
                    for child in project_dir.iterdir():
                        if child.is_dir() and child.name.startswith("XSCALE_"):
                            sub_lp = child / "XSCALE.LP"
                            if sub_lp.exists(): candidates.append(sub_lp)
                except OSError: pass
                if not candidates:
                    self.send_json({"error": "XSCALE.LP not found"}, 404)
                    return
                current_lp = max(candidates, key=lambda p: p.stat().st_mtime)
                uploaded_content = data.get("lp_content", "")
                if not uploaded_content:
                    self.send_json({"error": "No file content provided"}, 400)
                    return
                cur_content = current_lp.read_text(encoding="utf-8", errors="replace")
                cur_metrics = LPParser.parse_xscale(cur_content)
                ref_metrics = LPParser.parse_xscale(uploaded_content)
                def _sk2(row):
                    return {k: row.get(k, '') for k in ('resolution','completeness','r_meas','i_sigma','cc_half','r_obs','siganom')}
                def _sum_x(m):
                    s = {}
                    s['space_group'] = m.get('space_group', '')
                    uc = m.get('unit_cell')
                    if uc:
                        s['unit_cell'] = [uc.get(k,0) for k in ('a','b','c','alpha','beta','gamma')]
                    fl = m.get('friedels_law', '')
                    if fl: s['friedels_law'] = fl
                    isa_tbl = m.get('isa_table', [])
                    if isa_tbl:
                        s['isa'] = isa_tbl[0].get('isa', '')
                        s['isa0'] = isa_tbl[0].get('isa0', '')
                    tbl = m.get('statistics_table', [])
                    if tbl:
                        shells = [r for r in tbl if r.get('resolution','').lower() != 'total']
                        total = [r for r in tbl if r.get('resolution','').lower() == 'total']
                        if total: s['overall'] = _sk2(total[0])
                        elif shells: s['overall'] = _sk2(shells[0])
                        if len(shells) >= 1: s['inner'] = _sk2(shells[0])
                        if len(shells) >= 2: s['outer'] = _sk2(shells[-1])
                    return s
                cur_time = os.path.getmtime(str(current_lp))
                self.send_json({
                    "current": _sum_x(cur_metrics),
                    "current_time": datetime.fromtimestamp(cur_time).strftime("%Y-%m-%d %H:%M"),
                    "previous": _sum_x(ref_metrics),
                    "previous_time": data.get("filename", "uploaded file"),
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_DELETE(self):
        self._guarded(self._do_DELETE)

    def _do_DELETE(self):
        """Handle DELETE requests"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        project_route = self._project_route(path)
        qs = urllib.parse.parse_qs(parsed.query)
        
        if project_route == "":
            name = _url_project_name(path.split("/")[-1])
            delete_files = qs.get("files", ["false"])[0].lower() == "true"
            try:
                ProjectManager.delete(name, delete_files=delete_files)
                msg = f"Project {name} deleted" + (" (including files)" if delete_files else " (from list only)")
                self.send_json({"message": msg})
            except DirectoryBusyError as e:
                self.send_json({"error": str(e)}, 409)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        else:
            self.send_json({"error": "Not found"}, 404)


