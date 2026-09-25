class XDSRunner:
    """Run XDS executables"""
    
    def __init__(self, xds_path):
        self.xds_path = Path(xds_path)
    
    @_processing_job("xds")
    def run_step(self, project_name, step):
        project_dir = _pdir(project_name)
        
        # Check XDS.INP exists
        xds_inp = project_dir / "XDS.INP"
        if not xds_inp.exists():
            return {
                "step": step,
                "status": "error",
                "error_message": "XDS.INP not found"
            }
        
        # Modify XDS.INP for this step
        ProjectManager.invalidate_steps(project_name, step)
        with open(xds_inp, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        # Update or add JOB= line
        new_lines = []
        job_found = False
        for line in lines:
            if line.strip().startswith("JOB="):
                new_lines.append(f"JOB= {step}\n")
                job_found = True
            else:
                new_lines.append(line)
        
        if not job_found:
            new_lines.insert(0, f"JOB= {step}\n")
        
        with open(xds_inp, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        # Check XDS executable
        xds_exe = _find_xds_exe(self.xds_path)
        if not xds_exe.exists():
            return {
                "step": step,
                "status": "error",
                "error_message": f"XDS executable not found at {xds_exe}"
            }
        
        # Run XDS where this project's output lives (the folder of the last
        # run, or the project folder).  The edited XDS.INP above is the
        # project's copy; hand it to the run folder first, as /api/run-folder does.
        work_dir = _project_out_dir(project_dir)
        if work_dir != project_dir:
            try:
                shutil.copy2(str(xds_inp), str(work_dir / "XDS.INP"))
            except Exception as e:
                return {"step": step, "status": "error", "error_message": f"Cannot copy XDS.INP to {work_dir}: {e}"}
        try:
            rc, outcome = _run_streaming([str(xds_exe)], work_dir, lambda t: None, key=project_name, expected_outputs=[step + ".LP"])
            if outcome == "timeout":
                return {"step": step, "status": "timeout", "error_message": _outcome_message(outcome, step)}
            if outcome != "ok":
                return {"step": step, "status": "stopped" if outcome == "stopped" else "error", "error_message": _outcome_message(outcome, step)}

            # Check for errors in .LP file
            lp_file = _pfile(project_dir, f"{step}.LP")
            status = "completed"
            error_msg = None
            
            if lp_file.exists():
                content = _read_text_lenient(lp_file)
                if ("!!! ERROR !!!" in content or "!!! ERROR IN" in content):
                    status = "failed"
                    for line in content.split("\n"):
                        if ("!!! ERROR !!!" in line or "!!! ERROR IN" in line):
                            error_msg = line.strip()
                            break
            else:
                status = "failed"
                error_msg = "No .LP file generated"
            
            # Update metadata
            if status == "completed":
                metadata = ProjectManager.get(project_name)
                if step not in metadata.get("completed_steps", []):
                    metadata.setdefault("completed_steps", []).append(step)
                    ProjectManager.update(project_name, metadata)
            
            return {
                "step": step,
                "status": status,
                "error_message": error_msg,
                "returncode": rc
            }
            
        except subprocess.TimeoutExpired:
            return {
                "step": step,
                "status": "timeout",
                "error_message": "Timeout after 1 hour"
            }
        except Exception as e:
            return {
                "step": step,
                "status": "error",
                "error_message": str(e)
            }
    
    @_processing_job("xds")
    def run_pipeline(self, project_name, start_from=None, stop_at=None):
        start_idx = XDS_PIPELINE.index(start_from) if start_from else 0
        end_idx = XDS_PIPELINE.index(stop_at) if stop_at else len(XDS_PIPELINE) - 1
        
        results = []
        for i in range(start_idx, end_idx + 1):
            step = XDS_PIPELINE[i]
            result = self.run_step(project_name, step)
            results.append(result)
            
            if result["status"] != "completed":
                break
        
        return results


# Global runner
xds_runner = XDSRunner(XDS_PATH)
def _outcome_message(outcome, label, timeout=None):
    if outcome == "timeout":
        limit = XDS_STEP_TIMEOUT if timeout is None else timeout
        duration = format(limit / 60, 'g') + " min" if limit >= 60 else format(limit, 'g') + " s"
        return label + " exceeded the time limit of " + duration + " and was stopped"
    if outcome == "stopped":
        return label + " was stopped"
    return label + " could not be run: " + outcome.replace("error: ", "", 1)


CCP4_BIN = CCP4_BIN or _find_ccp4_bin()
XDSCC12_BIN = _find_xdscc12()


def _xds_binary_order(parallel_name, serial_name):
    """Preferred binary order according to the Parallel setting."""
    return (parallel_name, serial_name) if XDS_PARALLEL else (serial_name, parallel_name)


def _find_xds_exe(xds_path):
    """Resolve the XDS executable: xds_par first when parallel processing is
    enabled (the default), otherwise the serial xds; falls back to the other."""
    names = _xds_binary_order("xds_par", "xds")
    for name in names:
        exe = xds_path / name
        if exe.exists():
            return exe
    # Also check PATH via shutil.which
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return xds_path / names[0]   # return default so error messages stay informative


def _find_xscale_exe(xds_path):
    """Resolve the XSCALE executable, honouring the Parallel setting."""
    names = _xds_binary_order("xscale_par", "xscale")
    for name in names:
        exe = xds_path / name
        if exe.exists():
            return exe
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return xds_path / names[0]


def _find_xdsconv_exe(xds_path):
    """Resolve xdsconv: the XDS folder first, then PATH (same as xds/xscale)."""
    exe = xds_path / "xdsconv"
    if exe.exists():
        return exe
    found = shutil.which("xdsconv")
    if found:
        return Path(found)
    return exe


def _check_xds_helpers(xds_path):
    """Check that XDS helper executables (forkxds, mcolspot, etc.) are reachable.

    These are required by xds_par for parallel steps (COLSPOT, INTEGRATE, CORRECT).
    Returns a list of missing executable names (empty list if all found).
    """
    helpers = ("forkxds", "mcolspot", "mintegrate")
    missing = []
    for name in helpers:
        # Check explicit XDS directory first, then PATH
        if (xds_path / name).exists():
            continue
        if shutil.which(name):
            continue
        missing.append(name)
    return missing


@_processing_job("xds")
def stream_xds(project_name, steps, write_fn, run_folder=None, copy_gxparm=False):
    """Run XDS steps, streaming stdout line-by-line via SSE write_fn.
    
    If run_folder is given, XDS runs in that directory (which must already
    contain XDS.INP — the /api/run-folder endpoint copies it there).
    Otherwise XDS runs in the project directory (overwrite mode).
    If copy_gxparm is True, copies GXPARM.XDS -> XPARM.XDS before running.
    """
    project_dir = _pdir(project_name)
    xds_exe = _find_xds_exe(xds_runner.xds_path)

    # Determine working directory for XDS
    if run_folder:
        work_dir = Path(run_folder).resolve()
        if not work_dir.is_dir():
            try:
                work_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                write_fn("event: error_msg\ndata: " + json.dumps({"message": f"Cannot create run folder: {e}"}) + "\n\n")
                write_fn("event: done\ndata: " + json.dumps({"status": "error"}) + "\n\n")
                return
        # Copy XDS.INP if not already present
        work_inp = work_dir / "XDS.INP"
        src_inp = project_dir / "XDS.INP"
        if not work_inp.exists() and src_inp.exists():
            shutil.copy2(str(src_inp), str(work_inp))
    else:
        work_dir = project_dir

    # Remember where this run happens so the LP viewer, metrics, spot overlay,
    # POINTLESS etc. find the output even when the run folder is outside the
    # project (an empty value means: the project folder itself).
    _record_run_folder(project_name, work_dir, "xds")

    xds_inp = work_dir / "XDS.INP"

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    if not xds_inp.exists():
        send("error_msg", {"message": "XDS.INP not found"}); send("done", {}); return
    if not xds_exe.exists():
        send("error_msg", {"message": "XDS executable not found (tried xds_par, xds) at " + str(xds_runner.xds_path)}); send("done", {}); return

    # Warn if XDS helper executables are missing (needed by xds_par for parallel steps)
    if str(xds_exe).endswith("xds_par"):
        missing = _check_xds_helpers(xds_runner.xds_path)
        if missing:
            send("log", {"text": ">>> WARNING: XDS helper executable(s) not found in PATH: " + ", ".join(missing)})
            send("log", {"text": ">>>   Parallel steps (COLSPOT, INTEGRATE) will fail."})
            send("log", {"text": ">>>   Ensure the full XDS installation directory is in your $PATH."})

    # Preflight: for HDF5 data, check that the frames XDS is about to ask for
    # can actually be reached (see _check_h5_frames — a missing chunk file is
    # reported by XDS as a problem with dectris-neggia.so).
    try:
        _h5_fatal, _h5_lines = _check_h5_frames(xds_inp)
    except Exception:
        _h5_fatal, _h5_lines = False, []
    if _h5_lines:
        if _h5_fatal:
            send("error_msg", {"message": "XDS cannot read the images:\n" + "\n".join(_h5_lines)})
            send("done", {})
            return
        send("log", {"text": ">>> WARNING: " + _h5_lines[0]})
        for _ln in _h5_lines[1:]:
            send("log", {"text": ">>>   " + _ln})

    # Copy GXPARM.XDS -> XPARM.XDS if requested (re-integrate with refined geometry)
    if copy_gxparm:
        gxparm = work_dir / "GXPARM.XDS"
        xparm = work_dir / "XPARM.XDS"
        # If GXPARM.XDS not in work_dir (subfolder mode), try project dir
        if not gxparm.exists() and work_dir != project_dir:
            gxparm_src = project_dir / "GXPARM.XDS"
            if gxparm_src.exists():
                gxparm = gxparm_src
        if gxparm.exists():
            shutil.copy2(str(gxparm), str(xparm))
            send("log", {"text": ">>> Copied " + str(gxparm) + " -> " + str(xparm)})
        else:
            send("error_msg", {"message": "GXPARM.XDS not found in " + str(work_dir) + " or " + str(project_dir) + " -- run CORRECT first"})
            send("done", {})
            return

    for step in steps:
        if _job_stopped():
            send("done", {"status": "stopped"})
            return
        ProjectManager.invalidate_steps(project_name, step)
        # Auto-backup LP files before re-running a step (rotate up to 4 previous)
        if step in ("CORRECT", "IDXREF"):
            lp_name = step + ".LP"
            prev_lp = work_dir / lp_name
            if prev_lp.exists():
                try:
                    # Rotate: prev3→prev4, prev2→prev3, prev1→prev2, current→prev1
                    for ri in range(4, 1, -1):
                        src = work_dir / (lp_name + ".prev" + str(ri - 1))
                        dst = work_dir / (lp_name + ".prev" + str(ri))
                        if src.exists():
                            shutil.copy2(str(src), str(dst))
                    shutil.copy2(str(prev_lp), str(work_dir / (lp_name + ".prev1")))
                    send("log", {"text": ">>> Saved previous " + lp_name + " as " + lp_name + ".prev1"})
                except Exception:
                    pass

        lines = _read_text_lenient(xds_inp).splitlines(keepends=True)
        new_lines, found = [], False
        for line in lines:
            if line.strip().startswith("JOB="):
                new_lines.append("JOB= " + step + "\n"); found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.insert(0, "JOB= " + step + "\n")
        xds_inp.write_text("".join(new_lines), encoding="utf-8")

        send("step_start", {"step": step})

        rc, outcome = _run_streaming([str(xds_exe)], work_dir, lambda t: send("log", {"text": t}), key=project_name, expected_outputs=[step + ".LP"])
        if outcome != "ok":
            msg = _outcome_message(outcome, step)
            send("error_msg", {"message": msg})
            send("step_done", {"step": step, "status": outcome if outcome in ("timeout", "stopped") else "error", "error": msg})
            send("done", {})
            return

        lp_file = work_dir / (step + ".LP")
        status, error_msg = "completed", None
        if lp_file.exists():
            lp_text = _read_text_lenient(lp_file)
            if ("!!! ERROR !!!" in lp_text or "!!! ERROR IN" in lp_text):
                status = "failed"
                for ln in lp_text.split("\n"):
                    if ("!!! ERROR !!!" in ln or "!!! ERROR IN" in ln):
                        error_msg = ln.strip(); break
                # Detect missing helper executables (forkxds, mcolspot, etc.)
                if error_msg and "LP_01.tmp" in lp_text:
                    missing = _check_xds_helpers(xds_runner.xds_path)
                    if missing:
                        error_msg += (" - XDS helper(s) not in PATH: "
                                      + ", ".join(missing)
                                      + ". Add the XDS directory to $PATH.")
        else:
            status, error_msg = "failed", "No .LP file generated"

        if status == "completed":
            meta = ProjectManager.get(project_name)
            if step not in meta.get("completed_steps", []):
                meta.setdefault("completed_steps", []).append(step)
                ProjectManager.update(project_name, meta)

        send("step_done", {"step": step, "status": status, "error": error_msg})
        if status != "completed":
            send("done", {})
            return

    send("done", {})


@_processing_job("autoindex")
def stream_autoindex(project_name, tier, write_fn, force_cell=False):
    """Auto-indexing engine: systematically search SIGNAL_PIXEL + SPOT_RANGE
    combinations to find parameters that yield successful IDXREF.

    tier: 'quick', 'medium', or 'full'
    force_cell: if True, preserve SPACE_GROUP_NUMBER and UNIT_CELL_CONSTANTS
                from the user's XDS.INP.  If False (default), strip them so
                IDXREF performs ab-initio lattice determination.

    Streams progress via SSE write_fn.  Final event contains the full results
    table and the top-5 trials ranked by indexed fraction.
    """
    import time as _time
    project_dir = _pdir(project_name)
    xds_exe = _find_xds_exe(xds_runner.xds_path)

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    # ── Validate prerequisites ──────────────────────────────────────
    xds_inp_path = project_dir / "XDS.INP"
    if not xds_inp_path.exists():
        send("error_msg", {"message": "XDS.INP not found"}); send("ai_done", {}); return
    if not xds_exe.exists():
        send("error_msg", {"message": "XDS executable not found"}); send("ai_done", {}); return

    xds_inp_orig = _read_text_lenient(xds_inp_path)
    orig_params = _parse_xdsinp_params(xds_inp_orig)

    # ── Determine dataset frame range from XDS.INP ──────────────────
    data_range_str = orig_params.get("DATA_RANGE", "")
    try:
        dr_parts = data_range_str.split()
        frame_start, frame_end = int(dr_parts[0]), int(dr_parts[1])
    except (ValueError, IndexError):
        send("error_msg", {"message": "Cannot parse DATA_RANGE from XDS.INP"})
        send("ai_done", {}); return

    total_frames = frame_end - frame_start + 1
    osc_range = 1.0
    try:
        osc_range = float(orig_params.get("OSCILLATION_RANGE", "1.0"))
    except (ValueError, TypeError):
        osc_range = 1.0
    if osc_range <= 0:
        osc_range = 1.0

    send("ai_log", {"text": "═══ CrystalPilot Auto-Indexing ═══"})
    send("ai_log", {"text": "Tier: " + tier.upper() + " | Frames: " + str(frame_start) + "-" + str(frame_end)
                     + " (" + str(total_frames) + " frames, " + str(round(total_frames * osc_range, 1)) + "°)"})
    if force_cell:
        send("ai_log", {"text": "🔒 Space group / unit cell constraints preserved from XDS.INP"})
    else:
        send("ai_log", {"text": "🔓 Ab-initio indexing (space group / unit cell not constrained)"})

    # ── Build trial plan ────────────────────────────────────────────
    # Each trial: {'spot_range': [start, end], 'signal_pixel': value, 'label': str}
    trials = []

    # Wedge generation helper
    def _wedges_deg(deg_width):
        """Generate non-overlapping single wedges of given angular width
        from start, middle, end of dataset."""
        n_frames = max(1, int(round(deg_width / osc_range)))
        wedges = []
        # Start wedge
        ws = frame_start
        we = min(frame_start + n_frames - 1, frame_end)
        wedges.append((ws, we, "start"))
        # Middle wedge
        mid = frame_start + total_frames // 2 - n_frames // 2
        mid = max(frame_start, min(mid, frame_end - n_frames + 1))
        ms, me = mid, min(mid + n_frames - 1, frame_end)
        if ms > we + 1:  # avoid overlap with start
            wedges.append((ms, me, "middle"))
        # End wedge
        es = max(frame_start, frame_end - n_frames + 1)
        ee = frame_end
        if es > max(w[1] for w in wedges) + 1:  # avoid overlap
            wedges.append((es, ee, "end"))
        return wedges

    # SIGNAL_PIXEL grids
    sp_coarse = [3, 6, 12, 25, 50]
    sp_wide   = [2, 4, 8, 15, 25, 40, 60, 80]
    sp_medium = [3, 8, 20, 40, 70]

    # Get current SPOT_RANGE from XDS.INP (for quick mode)
    current_spot_ranges = []
    for line in xds_inp_orig.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("SPOT_RANGE") and "=" in stripped:
            parts = stripped.split("=", 1)[1].strip().split()
            if len(parts) >= 2:
                try:
                    current_spot_ranges.append((int(parts[0]), int(parts[1])))
                except ValueError:
                    pass
    if not current_spot_ranges:
        # Fall back to first 30° of dataset (not entire dataset which
        # can be thousands of frames with fine-sliced oscillation)
        n_frames_30deg = max(1, int(round(30.0 / osc_range)))
        fallback_end = min(frame_start + n_frames_30deg - 1, frame_end)
        current_spot_ranges = [(frame_start, fallback_end)]

    if tier == "quick":
        # Phase 1 only: test SIGNAL_PIXEL on current SPOT_RANGE
        for sp in sp_coarse:
            sr_label = "+".join(str(s) + "-" + str(e) for s, e in current_spot_ranges)
            trials.append({
                'spot_ranges': list(current_spot_ranges),
                'signal_pixel': sp,
                'label': "current(" + sr_label + ") SP=" + str(sp),
                'phase': 'signal_sweep'
            })
    elif tier == "medium":
        # Phase 1: test 3 wedges × 2 SIGNAL_PIXEL values
        wedge_deg = 10 if total_frames * osc_range < 60 else 20
        wedges_20 = _wedges_deg(wedge_deg)
        for ws, we, pos in wedges_20:
            for sp in [6, 25]:
                trials.append({
                    'spot_ranges': [(ws, we)],
                    'signal_pixel': sp,
                    'label': pos + "(" + str(ws) + "-" + str(we) + ") SP=" + str(sp),
                    'phase': 'region_triage'
                })
        # Phase 2 & 3 added dynamically after phase 1
    elif tier == "full":
        # Phase 1: comprehensive region sampling
        wedge_deg = 10 if total_frames * osc_range < 60 else 20
        wedges_20 = _wedges_deg(wedge_deg)
        for ws, we, pos in wedges_20:
            for sp in [3, 10, 30, 60]:
                trials.append({
                    'spot_ranges': [(ws, we)],
                    'signal_pixel': sp,
                    'label': pos + "(" + str(ws) + "-" + str(we) + ") SP=" + str(sp),
                    'phase': 'region_triage'
                })
        # Phase 2+ added dynamically

    # ── Trial execution engine ──────────────────────────────────────
    all_results = []
    trial_num = 0
    base_dir = project_dir / "_autoindex"

    def _cleanup_base():
        """Remove _autoindex working directory."""
        try:
            if base_dir.exists():
                shutil.rmtree(str(base_dir))
        except Exception:
            pass

    def _run_trial(trial):
        """Execute a single COLSPOT+IDXREF trial in a temp subdirectory.
        Returns dict with trial info + parsed results."""
        nonlocal trial_num
        trial_num += 1
        trial_id = str(trial_num).zfill(3)
        trial_dir = base_dir / ("trial_" + trial_id)

        result = {
            'trial_id': trial_id,
            'spot_ranges': trial['spot_ranges'],
            'signal_pixel': trial['signal_pixel'],
            'label': trial['label'],
            'phase': trial.get('phase', ''),
            'success': False,
            'indexed_count': 0,
            'total_spots': 0,
            'indexed_fraction': 0.0,
            'spots_per_image': 0.0,
            'sigma_spot': None,
            'sigma_spindle': None,
            'mosaicity': None,
            'error_type': None,
            'colspot_total': 0,
            'skipped': False,
            'index_error': trial.get('index_error', None),
            'min_pixels': trial.get('min_pixels', None),
            'index_origin': trial.get('index_origin', None),
            'index_origins_table': [],  # parsed from IDXREF.LP
            'selected_origin': None,
            'score': 0.0,  # composite: fraction × min(1, count/200)
        }

        try:
            trial_dir.mkdir(parents=True, exist_ok=True)

            # Symlink the project's XYCORR/INIT output into the trial dir so
            # COLSPOT finds it (X-/Y-CORRECTIONS, BKGINIT, BLANK, GAIN), from
            # the folder the last run wrote to.  What a COLSPOT+IDXREF trial
            # WRITES is never linked: XDS would write through the link and the
            # last trial - not the best - would replace the project's
            # SPOT.XDS, XPARM.XDS and IDXREF.LP.  Large outputs are skipped.
            _skip_symlink = {'XDS.INP', 'INTEGRATE.LP', 'INTEGRATE.HKL',
                             'XDS_ASCII.HKL', 'CORRECT.LP', 'XSCALE.LP',
                             'XSCALE.INP', 'XSCALE.HKL',
                             'SPOT.XDS', 'XPARM.XDS', 'GXPARM.XDS', 'COLSPOT.LP', 'IDXREF.LP', 'FRAME.cbf'}
            try:
                for item in _project_out_dir(project_dir).iterdir():
                    if item.name in _skip_symlink:
                        continue
                    if item.name.startswith('_autoindex'):
                        continue
                    dest = trial_dir / item.name
                    if not dest.exists():
                        try:
                            dest.symlink_to(item)
                        except OSError:
                            pass  # skip if symlinking not supported
            except OSError:
                pass

            # Build modified XDS.INP
            inp_lines = []
            skip_params = {'JOB', 'SPOT_RANGE', 'SIGNAL_PIXEL'}
            if 'index_error' in trial and trial['index_error'] is not None:
                skip_params.add('INDEX_ERROR')
            if 'min_pixels' in trial and trial['min_pixels'] is not None:
                skip_params.add('MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT')
            if 'index_origin' in trial and trial['index_origin'] is not None:
                skip_params.add('INDEX_ORIGIN')
            # Strip space group and unit cell by default so IDXREF
            # performs ab-initio lattice determination.  The force_cell
            # flag (from enclosing scope) preserves them when user
            # explicitly requests it.
            if not force_cell:
                skip_params.update({
                    'SPACE_GROUP_NUMBER', 'UNIT_CELL_CONSTANTS',
                    'UNIT_CELL_A-AXIS', 'UNIT_CELL_B-AXIS', 'UNIT_CELL_C-AXIS',
                })
            for line in xds_inp_orig.splitlines():
                stripped = line.strip().upper()
                param_name = stripped.split("=")[0].strip() if "=" in stripped else ""
                if param_name in skip_params:
                    continue

                # Make file-path parameters absolute so they resolve
                # correctly from the trial subdirectory
                if param_name in ('NAME_TEMPLATE_OF_DATA_FRAMES', 'LIB'):
                    eq_idx = line.index('=')
                    raw_val = line[eq_idx + 1:].strip()
                    # Strip any trailing comments
                    if raw_val and not os.path.isabs(raw_val):
                        abs_val = str((project_dir / raw_val).resolve())
                        line = line[:eq_idx + 1] + ' ' + abs_val
                inp_lines.append(line)

            # Insert our parameters
            inp_lines.insert(0, "JOB= COLSPOT IDXREF")
            inp_lines.insert(1, "SIGNAL_PIXEL= " + str(trial['signal_pixel']))
            for sr_start, sr_end in trial['spot_ranges']:
                inp_lines.insert(2, "SPOT_RANGE= " + str(sr_start) + " " + str(sr_end))
            if 'index_error' in trial and trial['index_error'] is not None:
                inp_lines.insert(2, "INDEX_ERROR= " + str(trial['index_error']))
            if 'min_pixels' in trial and trial['min_pixels'] is not None:
                inp_lines.insert(2, "MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT= " + str(trial['min_pixels']))
            if 'index_origin' in trial and trial['index_origin'] is not None:
                io = trial['index_origin']
                inp_lines.insert(2, "INDEX_ORIGIN= " + str(io[0]) + " " + str(io[1]) + " " + str(io[2]))

            trial_inp = trial_dir / "XDS.INP"
            _write_inp(trial_inp, "\n".join(inp_lines) + "\n")

            # Run XDS (COLSPOT+IDXREF)
            t0 = _time.time()
            # Auto-index trials are not registered for the main Stop button (they
            # manage their own lifecycle) but still run in their own process group
            # so a timeout kills the forkxds children too.  5 min max per trial.
            _trial_out = []
            _trial_rc, _trial_outcome = _run_streaming([str(xds_exe)], trial_dir, _trial_out.append,
                                                       timeout=300, should_stop=lambda: _job_stopped(), key=project_name, expected_outputs=_xds_expected_outputs(trial_dir))
            stdout_text = "\n".join(_trial_out)
            if _trial_outcome == "timeout":
                result['error_type'] = 'timeout'
                return result
            elapsed = round(_time.time() - t0, 1)
            result['elapsed_sec'] = elapsed
            result['xds_retcode'] = _trial_rc

            # Parse COLSPOT.LP
            colspot_lp = trial_dir / "COLSPOT.LP"
            if colspot_lp.exists():
                col_text = colspot_lp.read_text(encoding="utf-8", errors="replace")
                col = LPParser.parse_colspot_quick(col_text)
                result['colspot_total'] = col['total_spots']
                result['spots_per_image'] = round(col['spots_per_image'], 1)

                # Skip IDXREF check if too few spots per image
                if col['spots_per_image'] < 25:
                    result['error_type'] = 'too_few_spots'
                    result['skipped'] = True
            else:
                # COLSPOT.LP was not created — XDS likely failed to start
                result['error_type'] = 'no_colspot_lp'
                result['skipped'] = True
                # Capture last 5 lines of XDS stdout for diagnostics
                if stdout_text:
                    tail = stdout_text.strip().split('\n')[-5:]
                    result['xds_stdout_tail'] = tail

            # Parse IDXREF.LP
            idxref_lp = trial_dir / "IDXREF.LP"
            if idxref_lp.exists() and not result['skipped']:
                idx_text = idxref_lp.read_text(encoding="utf-8", errors="replace")
                idx = LPParser.parse_idxref_quick(idx_text)
                result['success'] = idx['success']
                result['indexed_count'] = idx['indexed_count']
                result['total_spots'] = idx['total_spots']
                result['indexed_fraction'] = round(idx['indexed_fraction'], 4)
                result['sigma_spot'] = idx['sigma_spot']
                result['sigma_spindle'] = idx['sigma_spindle']
                result['mosaicity'] = idx['mosaicity']
                result['error_type'] = idx['error_type']
                result['subtrees'] = idx.get('subtrees', [])
                result['index_origins_table'] = idx.get('index_origins', [])
                result['selected_origin'] = idx.get('selected_origin', None)
                # Composite score: fraction × min(1, indexed_count / 200)
                # Rewards both high fraction AND sufficient absolute count.
                # Below 200 indexed reflections, the lattice determination
                # is considered less reliable and the score is penalized.
                n_ref = 200.0
                frac = result['indexed_fraction']
                cnt = result['indexed_count']
                result['score'] = round(frac * min(1.0, cnt / n_ref), 4)
                # Fallback: if COLSPOT.LP didn't yield total_spots,
                # use IDXREF's total (same value = spots fed to IDXREF)
                if result['colspot_total'] == 0 and idx['total_spots'] > 0:
                    result['colspot_total'] = idx['total_spots']
            elif not result['skipped']:
                result['error_type'] = 'no_idxref_lp'

        except Exception as e:
            result['error_type'] = 'exception'
            result['error_detail'] = str(e)

        return result

    def _bisect_signal_pixel(spot_ranges, sp_low, sp_high, label_prefix, phase_name, max_iters=5):
        """Bisection refinement of SIGNAL_PIXEL between sp_low and sp_high.

        Searches for the SIGNAL_PIXEL value that maximizes indexed_fraction.
        Uses a robust approach: evaluates midpoint, keeps the better half.
        Stops after max_iters or when interval < 2.
        """
        results = []
        # Evaluate endpoints if not already tested
        lo_result = None
        hi_result = None

        for existing in all_results:
            if (existing['spot_ranges'] == spot_ranges
                    and abs(existing['signal_pixel'] - sp_low) < 0.5):
                lo_result = existing
            if (existing['spot_ranges'] == spot_ranges
                    and abs(existing['signal_pixel'] - sp_high) < 0.5):
                hi_result = existing

        if lo_result is None:
            t = {'spot_ranges': spot_ranges, 'signal_pixel': sp_low,
                 'label': label_prefix + " SP=" + str(sp_low), 'phase': phase_name}
            lo_result = _run_trial(t)
            all_results.append(lo_result)
            results.append(lo_result)
            _report_trial(lo_result)

        if hi_result is None:
            t = {'spot_ranges': spot_ranges, 'signal_pixel': sp_high,
                 'label': label_prefix + " SP=" + str(sp_high), 'phase': phase_name}
            hi_result = _run_trial(t)
            all_results.append(hi_result)
            results.append(hi_result)
            _report_trial(hi_result)

        lo_frac = lo_result.get('indexed_fraction', 0)
        hi_frac = hi_result.get('indexed_fraction', 0)
        current_lo, current_hi = sp_low, sp_high

        # Skip bisection if both endpoints are near-zero — flat response
        if lo_frac < 0.05 and hi_frac < 0.05:
            return results

        for iteration in range(max_iters):
            if _job_stopped():
                break
            if current_hi - current_lo < 2:
                break

            mid = round((current_lo + current_hi) / 2.0)
            # Avoid re-testing values too close to existing ones
            if abs(mid - current_lo) < 1 or abs(mid - current_hi) < 1:
                break

            t = {'spot_ranges': spot_ranges, 'signal_pixel': mid,
                 'label': label_prefix + " SP=" + str(mid) + " (bisect " + str(iteration + 1) + ")",
                 'phase': phase_name}
            send("ai_log", {"text": "  ├ Bisection " + str(iteration + 1) + ": testing SIGNAL_PIXEL=" + str(mid)})
            mid_result = _run_trial(t)
            all_results.append(mid_result)
            results.append(mid_result)
            _report_trial(mid_result)

            mid_frac = mid_result.get('indexed_fraction', 0)

            # Keep the half that contains the better result
            if lo_frac >= hi_frac:
                # Low side is better — narrow from high
                if mid_frac >= lo_frac:
                    # Mid is even better — narrow from low
                    current_lo = mid
                    lo_frac = mid_frac
                else:
                    current_hi = mid
                    hi_frac = mid_frac
            else:
                # High side is better — narrow from low
                if mid_frac >= hi_frac:
                    current_hi = mid
                    hi_frac = mid_frac
                else:
                    current_lo = mid
                    lo_frac = mid_frac

        return results

    def _report_trial(result):
        """Send SSE event for a completed trial."""
        frac_pct = round(result['indexed_fraction'] * 100, 1)
        status_icon = "✓" if result['success'] else "✗"
        sp_text = " | SP/img=" + str(result['spots_per_image']) if result['spots_per_image'] else ""
        sigma_text = ""
        if result['sigma_spot'] is not None:
            sigma_text = " | σ_px=" + str(round(result['sigma_spot'], 2))
        if result['sigma_spindle'] is not None:
            sigma_text += " σ_φ=" + str(round(result['sigma_spindle'], 2))
        elapsed_text = ""
        if result.get('elapsed_sec'):
            elapsed_text = " (" + str(result['elapsed_sec']) + "s)"

        msg = ("  " + status_icon + " #" + result['trial_id'] + " " + result['label']
               + " → " + str(frac_pct) + "% indexed"
               + " (" + str(result['indexed_count']) + "/" + str(result['total_spots']) + ")"
               + sp_text + sigma_text + elapsed_text)

        if result.get('error_type') == 'too_few_spots':
            msg = "  ⊘ #" + result['trial_id'] + " " + result['label'] + " → too few spots/image (" + str(result['spots_per_image']) + ")"
        elif result.get('error_type') == 'no_colspot_lp':
            msg = "  ⚠ #" + result['trial_id'] + " " + result['label'] + " → COLSPOT.LP not created (XDS failed to run)"
            tail = result.get('xds_stdout_tail', [])
            if tail:
                for tl in tail:
                    send("ai_log", {"text": "      " + tl})
        elif result.get('error_type') == 'timeout':
            msg = "  ⏱ #" + result['trial_id'] + " " + result['label'] + " → timeout"

        send("ai_log", {"text": msg})
        send("ai_trial", result)

    # ── Execute trials ──────────────────────────────────────────────
    _cleanup_base()
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        send("error_msg", {"message": "Cannot create _autoindex directory: " + str(e)})
        send("ai_done", {}); return

    send("ai_log", {"text": "─── Phase 1: " + ("SIGNAL_PIXEL sweep" if tier == "quick" else "Region triage") + " ───"})
    send("ai_phase", {"phase": 1, "description": "SIGNAL_PIXEL sweep" if tier == "quick" else "Region triage"})

    for trial in trials:
        if _job_stopped():
            send("ai_log", {"text": "  └ Stopped by user."}); break
        send("ai_log", {"text": "  ├ Testing: " + trial['label']})
        result = _run_trial(trial)
        all_results.append(result)
        _report_trial(result)

        # Early termination for quick mode: if we find >70% indexed, stop
        if tier == "quick" and result['indexed_fraction'] > 0.70:
            send("ai_log", {"text": "  └ Good result found, proceeding to bisection refinement..."})
            break

    # ── Dynamic phases for medium/full ──────────────────────────────
    if tier in ("medium", "full"):
        # Find best region from phase 1
        phase1_results = [r for r in all_results if r['phase'] == 'region_triage']
        if phase1_results:
            best_p1 = max(phase1_results, key=lambda r: r['score'])
            best_region = best_p1['spot_ranges']
            best_region_label = str(best_region[0][0]) + "-" + str(best_region[0][1])

            send("ai_log", {"text": ""})
            send("ai_log", {"text": "  Best region: frames " + best_region_label
                             + " (" + str(round(best_p1['indexed_fraction'] * 100, 1)) + "% indexed)"})

            # Phase 2: SIGNAL_PIXEL optimization on best region
            send("ai_log", {"text": ""})
            send("ai_log", {"text": "─── Phase 2: SIGNAL_PIXEL optimization on best region ───"})
            send("ai_phase", {"phase": 2, "description": "SIGNAL_PIXEL optimization"})

            sp_grid = sp_medium if tier == "medium" else sp_wide
            for sp in sp_grid:
                if _job_stopped():
                    send("ai_log", {"text": "  └ Stopped by user."}); break
                # Skip if already tested in phase 1
                already = any(
                    r['spot_ranges'] == best_region and abs(r['signal_pixel'] - sp) < 0.5
                    for r in all_results
                )
                if already:
                    continue
                t = {'spot_ranges': best_region, 'signal_pixel': sp,
                     'label': "best(" + best_region_label + ") SP=" + str(sp),
                     'phase': 'signal_optimize'}
                send("ai_log", {"text": "  ├ Testing: " + t['label']})
                result = _run_trial(t)
                all_results.append(result)
                _report_trial(result)

            # Bisection refinement around the two best SIGNAL_PIXEL values
            if not _job_stopped():
                opt_results = [r for r in all_results if r['spot_ranges'] == best_region and r['indexed_fraction'] > 0]
                if len(opt_results) >= 2:
                    opt_sorted = sorted(opt_results, key=lambda r: -r['score'])
                    best_sp = opt_sorted[0]['signal_pixel']
                    second_sp = opt_sorted[1]['signal_pixel']
                    lo_sp = min(best_sp, second_sp)
                    hi_sp = max(best_sp, second_sp)

                    if hi_sp - lo_sp >= 3:
                        send("ai_log", {"text": ""})
                        send("ai_log", {"text": "─── Phase 2b: Bisection refinement (SP " + str(lo_sp) + "-" + str(hi_sp) + ") ───"})
                        _bisect_signal_pixel(best_region, lo_sp, hi_sp,
                                             "best(" + best_region_label + ")", 'bisection')

            # Phase 3: Expand to larger wedge with best SIGNAL_PIXEL
            all_with_region = [r for r in all_results if r['spot_ranges'] == best_region]
            if all_with_region and not _job_stopped():
                best_overall = max(all_with_region, key=lambda r: r['score'])
                best_sp_val = best_overall['signal_pixel']

                # Expand to 50°, then 100° if medium, also full dataset if full
                expand_degs = [50, 100] if tier == "full" else [50]

                send("ai_log", {"text": ""})
                send("ai_log", {"text": "─── Phase 3: Verify with expanded wedge ───"})
                send("ai_phase", {"phase": 3, "description": "Expanded wedge verification"})

                for deg in expand_degs:
                    if _job_stopped():
                        send("ai_log", {"text": "  └ Stopped by user."}); break
                    n_frames_exp = max(1, int(round(deg / osc_range)))
                    # Center expansion on the best region
                    center = (best_region[0][0] + best_region[0][1]) // 2
                    exp_start = max(frame_start, center - n_frames_exp // 2)
                    exp_end = min(frame_end, exp_start + n_frames_exp - 1)

                    t = {'spot_ranges': [(exp_start, exp_end)],
                         'signal_pixel': best_sp_val,
                         'label': str(deg) + "deg(" + str(exp_start) + "-" + str(exp_end) + ") SP=" + str(int(best_sp_val)),
                         'phase': 'expand'}
                    send("ai_log", {"text": "  ├ Testing: " + t['label']})
                    result = _run_trial(t)
                    all_results.append(result)
                    _report_trial(result)

                # Full dataset test (full tier only)
                if tier == "full" and not _job_stopped():
                    t = {'spot_ranges': [(frame_start, frame_end)],
                         'signal_pixel': best_sp_val,
                         'label': "full(" + str(frame_start) + "-" + str(frame_end) + ") SP=" + str(int(best_sp_val)),
                         'phase': 'full_dataset'}
                    send("ai_log", {"text": "  ├ Testing: " + t['label']})
                    result = _run_trial(t)
                    all_results.append(result)
                    _report_trial(result)

            # ── Phase 4: Combined wedges (full tier only) ──────────────
            # Test non-contiguous SPOT_RANGE pairs for better reciprocal-
            # space coverage.  Only runs when single wedges haven't solved
            # the indexing problem (best < 70% indexed).
            if tier == "full" and not _job_stopped():
                best_so_far = max(all_results, key=lambda r: r['score'])
                if best_so_far['indexed_fraction'] < 0.70:
                    total_deg = total_frames * osc_range
                    if total_deg >= 40:  # need enough angular range
                        import random as _rng
                        from itertools import combinations as _combs

                        sub_deg = 15
                        n_sub = max(1, int(round(sub_deg / osc_range)))
                        n_positions = 5

                        # Evenly space sub-wedge start positions
                        usable = total_frames - n_sub
                        positions = []
                        if usable > 0:
                            for _pi in range(n_positions):
                                off = int(round(_pi * usable / max(n_positions - 1, 1)))
                                ps = frame_start + off
                                pe = min(ps + n_sub - 1, frame_end)
                                positions.append((ps, pe))

                        # Remove overlapping positions
                        unique_pos = []
                        for p in positions:
                            overlap = False
                            for u in unique_pos:
                                if p[0] <= u[1] and p[1] >= u[0]:
                                    overlap = True
                                    break
                            if not overlap:
                                unique_pos.append(p)

                        # Generate non-overlapping pairs with a gap
                        pairs = []
                        for a, b in _combs(unique_pos, 2):
                            if b[0] > a[1] + 1:
                                pairs.append((a, b))

                        max_pairs = 10
                        if len(pairs) > max_pairs:
                            _rng.shuffle(pairs)
                            pairs = pairs[:max_pairs]

                        if pairs:
                            # Collect best SP values from all prior phases
                            sp_candidates = []
                            for _cr in sorted(all_results, key=lambda r: -r['score']):
                                if _cr['indexed_fraction'] > 0 and _cr['signal_pixel'] not in sp_candidates:
                                    sp_candidates.append(_cr['signal_pixel'])
                                if len(sp_candidates) >= 3:
                                    break
                            if not sp_candidates:
                                sp_candidates = [best_sp_val]

                            n_combo_trials = len(pairs) * len(sp_candidates)
                            send("ai_log", {"text": ""})
                            send("ai_log", {"text": "─── Phase 4: Combined wedges ("
                                             + str(len(pairs)) + " pairs × "
                                             + str(len(sp_candidates)) + " SP = "
                                             + str(n_combo_trials) + " trials) ───"})
                            send("ai_phase", {"phase": 4, "description": "Combined wedge trials"})

                            combo_found = False
                            for wedge_a, wedge_b in pairs:
                                if _job_stopped() or combo_found:
                                    break
                                for sp in sp_candidates:
                                    if _job_stopped():
                                        break
                                    t = {
                                        'spot_ranges': [wedge_a, wedge_b],
                                        'signal_pixel': sp,
                                        'label': ("combo(" + str(wedge_a[0]) + "-" + str(wedge_a[1])
                                                  + "+" + str(wedge_b[0]) + "-" + str(wedge_b[1])
                                                  + ") SP=" + str(sp)),
                                        'phase': 'combined_wedge'
                                    }
                                    send("ai_log", {"text": "  ├ Testing: " + t['label']})
                                    result = _run_trial(t)
                                    all_results.append(result)
                                    _report_trial(result)
                                    # Early exit if we found a good result
                                    if result['indexed_fraction'] > 0.70:
                                        send("ai_log", {"text": "  └ Good combined-wedge result, stopping Phase 4."})
                                        combo_found = True
                                        break

                            if _job_stopped():
                                send("ai_log", {"text": "  └ Stopped by user."})
                    else:
                        send("ai_log", {"text": ""})
                        send("ai_log", {"text": "─── Phase 4: Skipped (dataset < 40°, too short for combined wedges) ───"})

            # ── Phase 4b: INDEX_ORIGIN alternatives ────────────────────
            # If the best trial's IDXREF.LP shows alternative origins
            # with significantly better DH/DK/DL than the selected 0,0,0
            # then test those — wrong origin is the most common cause of
            # misindexing from inaccurate ORGX/ORGY.
            if not _job_stopped():
                best_so_far_io = max(all_results, key=lambda r: r['score'])
                if best_so_far_io['indexed_fraction'] < 0.70:
                    io_table = best_so_far_io.get('index_origins_table', [])
                    io_selected = best_so_far_io.get('selected_origin', None)
                    if io_table and io_selected is not None:
                        # Compute average DH/DK/DL for the selected origin
                        sel_avg = None
                        for entry in io_table:
                            if entry['origin'] == io_selected:
                                sel_avg = (entry['dh'] + entry['dk'] + entry['dl']) / 3.0
                                break
                        if sel_avg is not None and sel_avg > 0.01:
                            # Find alternatives with meaningfully better DH/DK/DL
                            # (30% better average AND each component < 0.10)
                            candidates = []
                            for entry in io_table:
                                if entry['origin'] == io_selected:
                                    continue
                                avg = (entry['dh'] + entry['dk'] + entry['dl']) / 3.0
                                if avg < sel_avg * 0.7 and entry['dh'] < 0.10 and entry['dk'] < 0.10 and entry['dl'] < 0.10:
                                    candidates.append(entry)
                            # Sort by average DH/DK/DL (best first)
                            candidates.sort(key=lambda e: (e['dh'] + e['dk'] + e['dl']) / 3.0)
                            # Limit by tier
                            max_io = 1 if tier == "quick" else (2 if tier == "medium" else 3)
                            candidates = candidates[:max_io]

                            if candidates:
                                io_wedge = best_so_far_io['spot_ranges']
                                io_sp = best_so_far_io['signal_pixel']
                                io_wedge_label = "+".join(str(s) + "-" + str(e) for s, e in io_wedge)

                                send("ai_log", {"text": ""})
                                origins_str = ", ".join(
                                    str(c['origin'][0]) + " " + str(c['origin'][1]) + " " + str(c['origin'][2])
                                    for c in candidates
                                )
                                send("ai_log", {"text": "─── Phase 4b: INDEX_ORIGIN alternatives (" + origins_str + ") ───"})
                                send("ai_phase", {"phase": "4b", "description": "INDEX_ORIGIN alternatives"})
                                send("ai_log", {"text": "  Selected origin " + str(io_selected)
                                                 + " has avg(DH,DK,DL)=" + str(round(sel_avg, 3))
                                                 + "; testing alternatives with better fit"})

                                for cand in candidates:
                                    if _job_stopped():
                                        break
                                    io_val = cand['origin']
                                    io_str = str(io_val[0]) + " " + str(io_val[1]) + " " + str(io_val[2])
                                    t = {
                                        'spot_ranges': io_wedge,
                                        'signal_pixel': io_sp,
                                        'index_origin': io_val,
                                        'label': "origin(" + io_wedge_label + ") SP=" + str(io_sp) + " IO=" + io_str,
                                        'phase': 'index_origin_alt'
                                    }
                                    send("ai_log", {"text": "  ├ Testing: " + t['label']})
                                    result = _run_trial(t)
                                    all_results.append(result)
                                    _report_trial(result)
                                    # Early exit if we improved significantly
                                    if result['indexed_fraction'] >= 0.70:
                                        send("ai_log", {"text": "  └ INDEX_ORIGIN alternative successful."})
                                        break

                                if _job_stopped():
                                    send("ai_log", {"text": "  └ Stopped by user."})

            # ── Phase 5: INDEX_ERROR relaxation (rescue) ───────────────
            # Relax the INDEX_ERROR tolerance when best result is 10-50%
            # indexed — the lattice was found but too many spots rejected
            # by the strict default tolerance.
            if not _job_stopped():
                best_so_far_ie = max(all_results, key=lambda r: r['score'])
                if 0.10 <= best_so_far_ie['indexed_fraction'] < 0.50:
                    ie_wedge = best_so_far_ie['spot_ranges']
                    ie_sp = best_so_far_ie['signal_pixel']
                    ie_wedge_label = "+".join(str(s) + "-" + str(e) for s, e in ie_wedge)

                    ie_values = [0.10] if tier == "medium" else [0.08, 0.10, 0.14]

                    send("ai_log", {"text": ""})
                    send("ai_log", {"text": "─── Phase 5: INDEX_ERROR relaxation ("
                                     + ", ".join(str(v) for v in ie_values) + ") ───"})
                    send("ai_phase", {"phase": 5, "description": "INDEX_ERROR relaxation"})

                    for ie_val in ie_values:
                        if _job_stopped():
                            break
                        t = {
                            'spot_ranges': ie_wedge,
                            'signal_pixel': ie_sp,
                            'index_error': ie_val,
                            'label': "idxerr(" + ie_wedge_label + ") SP=" + str(ie_sp) + " IE=" + str(ie_val),
                            'phase': 'index_error_relax'
                        }
                        send("ai_log", {"text": "  ├ Testing: " + t['label']})
                        result = _run_trial(t)
                        all_results.append(result)
                        _report_trial(result)
                        # Early exit if relaxation pushed us above 50%
                        if result['indexed_fraction'] >= 0.50:
                            send("ai_log", {"text": "  └ INDEX_ERROR relaxation successful."})
                            break

                    if _job_stopped():
                        send("ai_log", {"text": "  └ Stopped by user."})

            # ── Phase 6: MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT ────────────
            # Vary the minimum cluster size for COLSPOT when indexing is
            # still below 50%.  Different values change which pixel
            # clusters are accepted as spots — a fundamentally different
            # spot list than prior phases.
            if not _job_stopped():
                best_so_far_mp = max(all_results, key=lambda r: r['score'])
                if best_so_far_mp['indexed_fraction'] < 0.50:
                    mp_wedge = best_so_far_mp['spot_ranges']
                    mp_sp = best_so_far_mp['signal_pixel']
                    mp_wedge_label = "+".join(str(s) + "-" + str(e) for s, e in mp_wedge)

                    # Detect the user's current value so we skip it
                    user_mp_str = orig_params.get("MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT", "6")
                    try:
                        user_mp = int(user_mp_str)
                    except (ValueError, TypeError):
                        user_mp = 6
                    all_mp_values = [2, 3, 4, 8] if tier == "full" else [3]
                    mp_values = [v for v in all_mp_values if v != user_mp]

                    if mp_values:
                        send("ai_log", {"text": ""})
                        send("ai_log", {"text": "─── Phase 6: MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT ("
                                         + ", ".join(str(v) for v in mp_values) + ") ───"})
                        send("ai_phase", {"phase": 6, "description": "Min pixels in spot"})

                        for mp_val in mp_values:
                            if _job_stopped():
                                break
                            t = {
                                'spot_ranges': mp_wedge,
                                'signal_pixel': mp_sp,
                                'min_pixels': mp_val,
                                'label': "minpx(" + mp_wedge_label + ") SP=" + str(mp_sp) + " MP=" + str(mp_val),
                                'phase': 'min_pixels_sweep'
                            }
                            send("ai_log", {"text": "  ├ Testing: " + t['label']})
                            result = _run_trial(t)
                            all_results.append(result)
                            _report_trial(result)
                            # Early exit if we crossed 50%
                            if result['indexed_fraction'] >= 0.50:
                                send("ai_log", {"text": "  └ Min-pixels variation successful."})
                                break

                        if _job_stopped():
                            send("ai_log", {"text": "  └ Stopped by user."})

    # ── Bisection for quick mode ────────────────────────────────────
    if tier == "quick" and all_results and not _job_stopped():
        # Find the two best SIGNAL_PIXEL values and bisect between them
        sorted_results = sorted(all_results, key=lambda r: -r['score'])
        if len(sorted_results) >= 2 and sorted_results[0]['indexed_fraction'] > 0:
            best_sp = sorted_results[0]['signal_pixel']
            second_sp = sorted_results[1]['signal_pixel']
            lo_sp = min(best_sp, second_sp)
            hi_sp = max(best_sp, second_sp)
            if hi_sp - lo_sp >= 3:
                sr = sorted_results[0]['spot_ranges']
                sr_label = "+".join(str(s) + "-" + str(e) for s, e in sr)
                send("ai_log", {"text": ""})
                send("ai_log", {"text": "─── Bisection refinement (SP " + str(lo_sp) + "-" + str(hi_sp) + ") ───"})
                _bisect_signal_pixel(sr, lo_sp, hi_sp, "refine(" + sr_label + ")", 'bisection')

    # ── Compile final report ────────────────────────────────────────
    stopped = _job_stopped()
    send("ai_log", {"text": ""})
    send("ai_log", {"text": "═══ Auto-Indexing " + ("Stopped" if stopped else "Complete") + " ═══"})

    # Top 10 by composite score (fraction × count reliability)
    top10 = sorted(all_results, key=lambda r: (-r['score'],
                                               r.get('sigma_spot') or 999,
                                               r.get('sigma_spindle') or 999))[:10]

    any_success = any(r['success'] for r in all_results)
    best = top10[0] if top10 else None

    if any_success and best:
        send("ai_log", {"text": "✅ Best: " + best['label'] + " — "
                         + str(round(best['indexed_fraction'] * 100, 1)) + "% indexed"
                         + " (" + str(best['indexed_count']) + "/" + str(best['total_spots']) + ")"})
    elif best and best['indexed_fraction'] > 0:
        send("ai_log", {"text": "⚠ Best result (below 50% threshold): " + best['label'] + " — "
                         + str(round(best['indexed_fraction'] * 100, 1)) + "% indexed"})
    else:
        send("ai_log", {"text": "❌ No successful indexing found across all trials."})

    send("ai_log", {"text": "Total trials: " + str(len(all_results))})

    # Build report log
    report_lines = []
    report_lines.append("CrystalPilot Auto-Indexing Report")
    report_lines.append("Tier: " + tier.upper())
    report_lines.append("Project: " + project_name)
    report_lines.append("Frames: " + str(frame_start) + "-" + str(frame_end))
    report_lines.append("")
    report_lines.append("Trial  Wedge              SIGNAL_PIXEL  IdxErr  MinPx  Origin     Spots  /frame  Indexed  Frac     Score   RMSD(px)  RMSD(phi)  Status")
    report_lines.append("-" * 145)
    for r in sorted(all_results, key=lambda x: -x['score']):
        sr_str = "+".join(str(s) + "-" + str(e) for s, e in r['spot_ranges'])
        sr_str = sr_str[:20].ljust(20)
        sp_str = str(r['signal_pixel']).ljust(14)
        ie_val = r.get('index_error')
        ie_str = (str(ie_val) if ie_val is not None else "-").ljust(8)
        mp_val = r.get('min_pixels')
        mp_str = (str(mp_val) if mp_val is not None else "-").ljust(7)
        io_val = r.get('index_origin')
        io_str = (" ".join(str(v) for v in io_val) if io_val is not None else "-").ljust(11)
        spots_str = str(r['colspot_total']).ljust(7)
        spimg_str = str(r['spots_per_image']).ljust(8)
        idx_str = str(r['indexed_count']).ljust(9)
        frac_str = (str(round(r['indexed_fraction'] * 100, 1)) + "%").ljust(9)
        score_str = str(round(r['score'], 3)).ljust(8)
        rmsd_px = str(round(r['sigma_spot'], 2)) if r['sigma_spot'] is not None else "-"
        rmsd_phi = str(round(r['sigma_spindle'], 2)) if r['sigma_spindle'] is not None else "-"
        status = "OK" if r['success'] else (r.get('error_type') or 'low_frac')
        report_lines.append(
            r['trial_id'] + "    " + sr_str + "  " + sp_str + ie_str + mp_str + io_str + spots_str + spimg_str
            + idx_str + frac_str + score_str + rmsd_px.ljust(10) + rmsd_phi.ljust(11) + status
        )
    report_text = "\n".join(report_lines)

    # Write report to project directory
    report_path = project_dir / "AUTOINDEX_REPORT.txt"
    try:
        report_path.write_text(report_text, encoding="utf-8")
    except Exception:
        pass

    # Save structured results as JSON for reload on tab switch
    # Strip large per-trial fields not needed by the frontend
    for r in all_results:
        r.pop('index_origins_table', None)
        r.pop('selected_origin', None)
        r.pop('subtrees', None)

    results_payload = {
        "top5": top10,  # top 10 results despite key name (backward compat)
        "total_trials": len(all_results),
        "any_success": any_success,
        "all_results": all_results,
        "report": report_text,
        "tier": tier,
    }
    json_path = project_dir / "AUTOINDEX_RESULTS.json"
    try:
        json_path.write_text(json.dumps(results_payload), encoding="utf-8")
    except Exception:
        pass

    # Clean up trial directories (keep report + JSON)
    _cleanup_base()

    # Send final results
    send("ai_report", {"report": report_text})
    send("ai_results", {
        "top5": top10,  # top 10 results despite key name (backward compat)
        "total_trials": len(all_results),
        "any_success": any_success,
        "all_results": all_results,
    })
    send("ai_done", {})


def load_autoindex_cached_results(project_dir):
    """Read previously saved AUTOINDEX_RESULTS.json from disk.

    Returns dict with keys:
        'has_results': bool
        'top5', 'all_results', 'total_trials', 'any_success', 'report', 'tier'
    Used by the handler to serve cached results when IDXREF metrics are viewed.
    """
    from pathlib import Path
    project_dir = Path(project_dir)
    result = {'has_results': False}

    json_path = project_dir / "AUTOINDEX_RESULTS.json"
    if json_path.exists():
        try:
            data = json.loads(_read_text_lenient(json_path))
            if data.get('top5') and len(data['top5']) > 0:
                result.update(data)
                result['has_results'] = True
        except Exception:
            pass

    return result


@_processing_job("xscale")
def stream_xscale(project_name, write_fn, run_folder=None):
    """Run XSCALE, streaming stdout line-by-line via SSE write_fn.

    If run_folder is given, XSCALE runs in that directory (which must already
    contain XSCALE.INP).  Otherwise XSCALE runs in the project directory.
    """
    project_dir = _pdir(project_name)
    xscale_exe = _find_xscale_exe(xds_runner.xds_path)

    # No XSCALE.INP yet: write the default one for this project's XDS_ASCII.HKL (the
    # values an empty XSCALE form saves with "Save as new XSCALE.INP") and run it
    made_default = ""
    if not (project_dir / "XSCALE.INP").exists() and not (run_folder and (Path(run_folder) / "XSCALE.INP").exists()):
        _hkl = _pfile(project_dir, "XDS_ASCII.HKL")
        if _hkl.exists():
            _write_inp(project_dir / "XSCALE.INP", _xscale_apply_params("", {
                "OUTPUT_FILE": "merged.ahkl", "INPUT_FILE": [str(_hkl)],
                "STRICT_ABSORPTION_CORRECTION": "FALSE", "FRIEDEL'S_LAW": "TRUE", "MERGE": "FALSE"}))
            made_default = str(_hkl)

    # Determine working directory
    if run_folder:
        work_dir = Path(run_folder).resolve()
        if not work_dir.is_dir():
            try:
                work_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                write_fn("event: error_msg\ndata: " + json.dumps({"message": f"Cannot create run folder: {e}"}) + "\n\n")
                write_fn("event: done\ndata: " + json.dumps({"status": "error"}) + "\n\n")
                return
        # Copy XSCALE.INP when the folder has none or the project's copy is
        # newer (edited in the app since the last run), fixing INPUT_FILE paths
        work_inp = work_dir / "XSCALE.INP"
        src_inp = project_dir / "XSCALE.INP"
        if src_inp.exists() and (not work_inp.exists() or src_inp.stat().st_mtime > work_inp.stat().st_mtime):
            shutil.copy2(str(src_inp), str(work_inp))
            # Rewrite INPUT_FILE= paths so they resolve from the subfolder.
            # Relative paths (e.g. "XDS_ASCII.HKL" or "1/XDS_ASCII.HKL") are
            # relative to the project dir, so prefix with the relative path back.
            try:
                relback = os.path.relpath(str(project_dir), str(work_dir))
                inp_text = work_inp.read_text(encoding="utf-8", errors='replace')
                _write_inp(work_inp, _xscale_inputs_from_subfolder(inp_text, relback))
            except Exception:
                pass  # If rewrite fails, keep the copied file as-is
    else:
        work_dir = project_dir
    _record_run_folder(project_name, work_dir, "xscale")

    xscale_inp = work_dir / "XSCALE.INP"

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    if made_default:
        send("log", {"text": ">>> No XSCALE.INP yet: wrote the default one (OUTPUT_FILE= merged.ahkl, INPUT_FILE= " + made_default + ")"})
    if not xscale_inp.exists():
        send("error_msg", {"message": "No XSCALE.INP in " + str(work_dir) + " and no XDS_ASCII.HKL of this project to write one for. Run CORRECT first, or set the input files in the XSCALE tab and save."}); send("done", {}); return
    try:
        _inp_text = xscale_inp.read_text(encoding="utf-8", errors="replace")
        if not any(_xscale_key(l) == "INPUT_FILE" and not l.strip().startswith("!") for l in _inp_text.split("\n")):
            # No input given: use this project's XDS_ASCII.HKL (folder of the
            # last XDS run) rather than failing.
            _hkl = _pfile(project_dir, "XDS_ASCII.HKL")
            if _hkl.exists():
                _write_inp(xscale_inp, _xscale_apply_params(_inp_text, {"INPUT_FILE": [str(_hkl)]}))
                send("log", {"text": ">>> XSCALE.INP had no INPUT_FILE= line - using " + str(_hkl)})
            else:
                send("error_msg", {"message": "XSCALE.INP has no INPUT_FILE= line and no XDS_ASCII.HKL was found for this project (" + str(_hkl) + "). Run CORRECT first, or add the file(s) in the XSCALE tab and save."})
                send("done", {}); return
    except Exception as _e:
        send("log", {"text": ">>> Could not check INPUT_FILE lines: " + str(_e)})
    if not xscale_exe.exists():
        send("error_msg", {"message": "XSCALE executable not found (tried xscale_par, xscale) at " + str(xds_runner.xds_path)}); send("done", {}); return

    # Auto-backup XSCALE.LP before re-running (rotate up to 4 previous)
    prev_lp = work_dir / "XSCALE.LP"
    if prev_lp.exists():
        try:
            for ri in range(4, 1, -1):
                src = work_dir / ("XSCALE.LP.prev" + str(ri - 1))
                dst = work_dir / ("XSCALE.LP.prev" + str(ri))
                if src.exists():
                    shutil.copy2(str(src), str(dst))
            shutil.copy2(str(prev_lp), str(work_dir / "XSCALE.LP.prev1"))
            send("log", {"text": ">>> Saved previous XSCALE.LP as XSCALE.LP.prev1"})
        except Exception:
            pass

    send("step_start", {"step": "XSCALE"})

    rc, outcome = _run_streaming([str(xscale_exe)], work_dir, lambda t: send("log", {"text": t}), key=project_name, expected_outputs=["XSCALE.LP"])
    if outcome != "ok":
        msg = _outcome_message(outcome, "XSCALE")
        send("error_msg", {"message": msg})
        send("step_done", {"step": "XSCALE", "status": outcome if outcome in ("timeout", "stopped") else "error", "error": msg})
        send("done", {})
        return

    lp_file = work_dir / "XSCALE.LP"
    status, error_msg = "completed", None
    if lp_file.exists():
        lp_text = _read_text_lenient(lp_file)
        if ("!!! ERROR !!!" in lp_text or "!!! ERROR IN" in lp_text):
            status = "failed"
            for ln in lp_text.split("\n"):
                if ("!!! ERROR !!!" in ln or "!!! ERROR IN" in ln):
                    error_msg = ln.strip(); break
    else:
        status, error_msg = "failed", "No XSCALE.LP file generated"

    send("step_done", {"step": "XSCALE", "status": status, "error": error_msg})
    send("done", {})


@_processing_job("xdsconv")
def stream_xdsconv(project_name, write_fn, work_dir=None, mtz_name=None):
    """Run XDSCONV, streaming stdout line-by-line via SSE write_fn."""
    project_dir = _pdir(project_name)
    xdsconv_exe = _find_xdsconv_exe(xds_runner.xds_path)

    if work_dir:
        work_dir = Path(work_dir).resolve()
    else:
        work_dir = project_dir
    _record_run_folder(project_name, work_dir, "xdsconv")

    # Copy XDSCONV.INP into work_dir when it is missing there or the project's
    # copy is newer (edited in the app since the last run)
    xdsconv_inp = work_dir / "XDSCONV.INP"
    if work_dir != project_dir:
        src = project_dir / "XDSCONV.INP"
        if src.exists() and (not xdsconv_inp.exists() or src.stat().st_mtime > xdsconv_inp.stat().st_mtime):
            shutil.copy2(str(src), str(xdsconv_inp))

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    if not xdsconv_inp.exists():
        send("error_msg", {"message": "XDSCONV.INP not found in " + str(work_dir)}); send("done", {}); return
    if not xdsconv_exe.exists():
        send("error_msg", {"message": "xdsconv not found at " + str(xdsconv_exe)}); send("done", {}); return

    send("step_start", {"step": "XDSCONV"})

    f2mtz_before = _output_stamp(work_dir / "F2MTZ.INP")
    printed_errors = []

    def _xdsconv_log(t):
        # a wrong input file: XDSCONV prints "!!! ERROR !!! WRONG TYPE OF INPUT FILE"
        # on the screen only and its XDSCONV.LP ends before any error line
        if "!!! ERROR" in t:
            printed_errors.append(t.strip())
        send("log", {"text": t})
    rc, outcome = _run_streaming([str(xdsconv_exe)], work_dir, _xdsconv_log, key=project_name, expected_outputs=["XDSCONV.LP"])
    if outcome != "ok":
        msg = _outcome_message(outcome, "XDSCONV")
        send("error_msg", {"message": msg})
        send("step_done", {"step": "XDSCONV", "status": outcome if outcome in ("timeout", "stopped") else "error", "error": msg})
        send("done", {})
        return

    lp_file = work_dir / "XDSCONV.LP"
    status, error_msg = "completed", None
    if lp_file.exists():
        lp_text = _read_text_lenient(lp_file)
        if ("!!! ERROR !!!" in lp_text or "!!! ERROR IN" in lp_text):
            status = "failed"
            for ln in lp_text.split("\n"):
                if ("!!! ERROR !!!" in ln or "!!! ERROR IN" in ln):
                    error_msg = ln.strip(); break
    else:
        status, error_msg = "failed", "No XDSCONV.LP file generated"
    if status == "completed" and printed_errors:
        status, error_msg = "failed", printed_errors[0]

    send("step_done", {"step": "XDSCONV", "status": status, "error": error_msg})

    # If XDSCONV succeeded and CCP4 is available, run f2mtz + cad to produce .mtz
    if status == "completed" and CCP4_BIN:
        f2mtz_inp = work_dir / "F2MTZ.INP"
        if f2mtz_inp.exists() and _output_stamp(f2mtz_inp) != f2mtz_before:
            f2mtz_exe, _, f2mtz_problem = _ccp4_program("f2mtz")
            cad_exe, _, cad_problem = _ccp4_program("cad")
            if f2mtz_exe and cad_exe:
                # Determine final mtz name: use explicit parameter, or derive from OUTPUT_FILE
                if not mtz_name:
                    mtz_name = "XDSCONV.mtz"
                    try:
                        inp_text = xdsconv_inp.read_text(encoding="utf-8", errors='replace')
                        for ln in inp_text.split('\n'):
                            s = ln.strip()
                            if s.startswith('!'):
                                continue
                            c = s.split('!')[0].strip()
                            if c.upper().startswith('OUTPUT_FILE') and '=' in c:
                                parts = c.split('=', 1)[1].strip().split()
                                if parts:
                                    base = Path(parts[0]).stem
                                    mtz_name = base + ".mtz"
                                break
                    except Exception:
                        pass

                temp_mtz = work_dir / "temp_f2mtz.mtz"

                # Step: f2mtz
                send("step_start", {"step": "f2mtz"})
                try:
                    with open(str(f2mtz_inp), 'r', encoding='utf-8') as fin:
                        cmd, env = _ccp4_command("f2mtz", ["HKLOUT", str(temp_mtz)], work_dir)
                        _run_checked(cmd, work_dir,
                                       lambda t: send("log", {"text": t}), timeout=600, env=env,
                                       stdin_file=fin, key=project_name, expected_outputs=[temp_mtz])

                    if temp_mtz.exists():
                        send("step_done", {"step": "f2mtz", "status": "completed", "error": None})
                    else:
                        send("step_done", {"step": "f2mtz", "status": "failed", "error": "f2mtz did not produce output"})
                        send("done", {}); return
                except Exception as e:
                    send("step_done", {"step": "f2mtz", "status": "error", "error": str(e)})
                    send("done", {}); return

                # Step: cad
                final_mtz = work_dir / mtz_name
                send("step_start", {"step": "cad"})
                try:
                    cmd, env = _ccp4_command("cad", ["HKLIN1", str(temp_mtz), "HKLOUT", str(final_mtz)], work_dir)
                    _run_checked(cmd, work_dir,
                                   lambda t: send("log", {"text": t}), timeout=600, env=env,
                                   stdin_text="LABIN FILE 1 ALL\nEND\n", key=project_name, expected_outputs=[final_mtz])

                    if final_mtz.exists():
                        send("step_done", {"step": "cad", "status": "completed", "error": None})
                        send("log", {"text": ">>> MTZ file created: " + str(final_mtz)})
                    else:
                        send("step_done", {"step": "cad", "status": "failed", "error": "cad did not produce output"})
                except Exception as e:
                    send("step_done", {"step": "cad", "status": "error", "error": str(e)})
            else:
                send("log", {"text": ">>> MTZ conversion skipped - " + (f2mtz_problem or cad_problem)})
        else:
            send("log", {"text": ">>> No fresh F2MTZ.INP generated by XDSCONV - skipping MTZ conversion"})
    elif status == "completed" and not CCP4_BIN:
        send("log", {"text": ">>> CCP4 not found - MTZ conversion skipped. Install CCP4 for automatic .mtz creation."})

    send("done", {})


@_processing_job("gemmi")
def stream_gemmi_mtz(project_name, write_fn, work_dir=None, mtz_name=None,
                     input_file=None, generate_freer=True):
    """Convert XDS_ASCII.HKL to MTZ using gemmi (intensities only).

    This is an alternative to the CCP4 f2mtz+cad pipeline that does NOT
    require CCP4.  The output MTZ contains intensities (IMEAN/SIGIMEAN)
    but no amplitudes (no French-Wilson conversion).
    Suitable for Phenix refinement; not for standard REFMAC5.
    """
    project_dir = _pdir(project_name)

    if work_dir:
        work_dir = Path(work_dir).resolve()
    else:
        work_dir = project_dir

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    send("step_start", {"step": "gemmi_mtz"})

    # Check gemmi availability
    ok, info = _check_gemmi()
    if not ok:
        send("error_msg", {"message": "gemmi not available: " + info
             + ". Install with: pip install gemmi"})
        send("step_done", {"step": "gemmi_mtz", "status": "error", "error": info})
        send("done", {})
        return

    send("log", {"text": ">>> gemmi version: " + info})

    # Locate input file
    if input_file:
        hkl_path = Path(input_file)
        if not hkl_path.is_absolute():
            hkl_path = work_dir / input_file
    else:
        hkl_path = work_dir / "XDS_ASCII.HKL"

    if not hkl_path.exists():
        send("error_msg", {"message": "Input file not found: " + str(hkl_path)})
        send("step_done", {"step": "gemmi_mtz", "status": "error",
                           "error": "Input file not found"})
        send("done", {})
        return

    send("log", {"text": ">>> Input: " + str(hkl_path)})

    # Determine output name
    if not mtz_name:
        mtz_name = hkl_path.stem + "_gemmi.mtz"
    out_path = work_dir / mtz_name

    send("log", {"text": ">>> Output: " + str(out_path)})
    send("log", {"text": ">>> FreeR flag: " + ("yes" if generate_freer else "no")})

    # Run conversion
    try:
        result = convert_xds_to_mtz(
            str(hkl_path), str(out_path),
            generate_freer=generate_freer
        )
    except Exception as e:
        send("error_msg", {"message": "Conversion failed: " + str(e)})
        send("step_done", {"step": "gemmi_mtz", "status": "error", "error": str(e)})
        send("done", {})
        return

    if result["success"]:
        send("log", {"text": ">>> " + result["message"]})
        send("log", {"text": ">>> Columns: " + ", ".join(result["columns"])})
        send("log", {"text": ">>> Reflections: " + str(result["nreflections"])})
        if result["spacegroup"]:
            send("log", {"text": ">>> Space group: " + result["spacegroup"]})
        send("log", {"text": ">>> Cell: " + "  ".join("%.2f" % v for v in result["cell"])})
        send("log", {"text": ">>> Merged: " + str(result["merged"])})
        send("log", {"text": ">>> FreeR added: " + str(result["has_freer"])})
        for w in result["warnings"]:
            send("log", {"text": ">>> NOTE: " + w})
        send("step_done", {"step": "gemmi_mtz", "status": "completed", "error": None})
        send("gemmi_mtz_result", {
            "mtz_path": str(out_path),
            "columns": result["columns"],
            "nreflections": result["nreflections"],
            "spacegroup": result["spacegroup"],
            "cell": result["cell"],
            "has_freer": result["has_freer"],
            "merged": result["merged"]
        })
    else:
        send("error_msg", {"message": result["message"]})
        for w in result["warnings"]:
            send("log", {"text": ">>> " + w})
        send("step_done", {"step": "gemmi_mtz", "status": "failed",
                           "error": result["message"]})

    send("done", {})


@_processing_job("pointless")
def stream_pointless(project_name, write_fn, input_file=None, chirality="CHIRAL",
                     setting="SYMMETRY-BASED", lauegroup=None, spacegroup=None,
                     resolution_low=None, resolution_high=None):
    """Run CCP4 POINTLESS, streaming stdout line-by-line via SSE write_fn.

    POINTLESS writes its log to stdout (no .LP file). We capture the full
    output for post-run parsing while simultaneously streaming it to the client.
    The captured log is saved to pointless.log in the project directory.
    """
    project_dir = _pdir(project_name)

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    # Locate pointless binary
    if not CCP4_BIN:
        send("error_msg", {"message": "CCP4 not found. Install CCP4 and source ccp4.setup-sh, or set the CCP4 bin path in the XDSCONV tab."})
        send("done", {})
        return

    ptl_exe, _, ptl_problem = _ccp4_program("pointless")
    if not ptl_exe:
        send("error_msg", {"message": "POINTLESS cannot run: " + ptl_problem + "."})
        send("done", {})
        return

    # Resolve input file
    if input_file:
        inp = Path(input_file)
        if not inp.is_absolute():
            inp = _pfile(project_dir, inp)
    else:
        # Auto-detect: prefer XDS_ASCII.HKL in project dir
        inp = _pfile(project_dir, "XDS_ASCII.HKL")
        if not inp.exists():
            for candidate in ["XSCALE.HKL", "merged.hkl"]:
                c = _pfile(project_dir, candidate, kind="xscale")
                if c.exists():
                    inp = c
                    break

    if not inp.exists():
        send("error_msg", {"message": "Input file not found: " + str(inp)})
        send("done", {})
        return

    # Determine input type (XDSIN for XDS/HKL files, HKLIN for MTZ)
    inp_str = str(inp)
    is_xds = _is_xds_reflection_file(inp_str)

    # Build command line
    cmd = [str(ptl_exe)]
    if is_xds:
        cmd += ["XDSIN", inp_str]
    else:
        cmd += ["HKLIN", inp_str]

    hklout = _pout(project_dir, "pointless_out.mtz")
    xmlout = _pout(project_dir, "pointless.xml")
    cmd += ["HKLOUT", str(hklout)]
    cmd += ["XMLOUT", str(xmlout)]

    # Build stdin keywords
    keywords = []
    keywords.append("SETTING " + (setting or "SYMMETRY-BASED"))
    keywords.append("CHIRALITY " + (chirality or "CHIRAL"))
    if lauegroup:
        keywords.append("LAUEGROUP " + lauegroup)
    if spacegroup:
        keywords.append("SPACEGROUP " + spacegroup)
    if resolution_low or resolution_high:
        lo = resolution_low or "999"
        hi = resolution_high or "0"
        keywords.append("RESOLUTION " + str(lo) + " " + str(hi))
    keywords.append("END")
    stdin_text = "\n".join(keywords) + "\n"

    send("step_start", {"step": "POINTLESS"})
    send("log", {"text": ">>> Command: " + " ".join(cmd)})
    send("log", {"text": ">>> Input: " + inp_str})
    send("log", {"text": ">>> Keywords: " + " | ".join(keywords[:-1])})

    # CCP4 environment (and, for a CCP4 for Windows, Windows paths)
    cmd, env = _ccp4_command("pointless", cmd[1:], _project_out_dir(project_dir))

    captured_log = []  # Capture full output for post-run parsing

    try:
        def _ptl_line(t):
            captured_log.append(t)
            send("log", {"text": t})
        rc, outcome = _run_streaming(cmd, _project_out_dir(project_dir), _ptl_line, timeout=1800, env=env,
                                     stdin_text=stdin_text, key=project_name)
        if outcome != "ok":
            raise RuntimeError(_outcome_message(outcome, "POINTLESS"))
    except Exception as e:
        send("error_msg", {"message": str(e)})
        send("step_done", {"step": "POINTLESS", "status": "error", "error": str(e)})
        send("done", {})
        return

    # Save captured log to file for future reference
    log_path = _pout(project_dir, "pointless.log")
    try:
        log_path.write_text("\n".join(captured_log), encoding="utf-8")
    except Exception:
        pass

    # Check result
    status, error_msg = "completed", None
    if rc != 0:
        status = "failed"
        error_msg = "POINTLESS exited with code " + str(rc)

    send("step_done", {"step": "POINTLESS", "status": status, "error": error_msg})

    # Parse log and send structured results
    if status == "completed":
        try:
            full_log = "\n".join(captured_log)
            parsed = LPParser.parse_pointless(full_log)
            # Send result if we extracted anything useful (best_solution is always a dict,
            # so check it has actual content, not just truthiness of empty {})
            if parsed.get('best_solution') and len(parsed['best_solution']) > 0:
                send("pointless_result", parsed)
            elif parsed.get('space_groups'):
                # Got SG table but no best solution block - still useful
                send("pointless_result", parsed)
        except Exception as e:
            send("log", {"text": ">>> Warning: could not parse POINTLESS output: " + str(e)})

        if hklout.exists():
            send("log", {"text": ">>> Output MTZ: " + str(hklout)})
        send("log", {"text": ">>> Log saved to: " + str(log_path)})

    send("done", {})


@_processing_job("aimless")
def stream_aimless(project_name, write_fn, resolution_low=None, resolution_high=None,
                   anomalous=True, bins=20, run_pointless=True, run_ctruncate=True,
                   input_file=None):
    """Run POINTLESS → AIMLESS → CTRUNCATE pipeline, streaming via SSE write_fn.

    AIMLESS scales and merges unmerged reflections, producing publication-ready
    merged MTZ and detailed statistics. CTRUNCATE converts I→F with French-Wilson
    and performs twinning tests.

    Reference: Evans, P.R. & Murshudov, G.N. (2013) Acta Cryst. D69, 1204-1214.
    """
    project_dir = _pdir(project_name)

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    # ── Check CCP4 ──
    if not CCP4_BIN:
        send("error_msg", {"message": "CCP4 not found. Install CCP4 and source ccp4.setup-sh, or set the CCP4 bin path in the XDSCONV tab."})
        send("done", {})
        return

    aimless_exe, _, aml_problem = _ccp4_program("aimless")
    if not aimless_exe:
        send("error_msg", {"message": "AIMLESS cannot run: " + aml_problem + "."})
        send("done", {})
        return

    ptl_exe, _, ptl_problem = _ccp4_program("pointless")
    if not ptl_exe:
        send("error_msg", {"message": "POINTLESS, needed to prepare the input for AIMLESS, cannot run: " + ptl_problem + "."})
        send("done", {})
        return
    ccp4_scr = _project_out_dir(project_dir)   # each step gets its command line and CCP4 environment from _ccp4_command

    # ── Resolve input file ──
    if input_file:
        inp = Path(input_file)
        if not inp.is_absolute():
            inp = _pfile(project_dir, inp)
    else:
        inp = _pfile(project_dir, "XDS_ASCII.HKL")
        if not inp.exists():
            for candidate in ["XSCALE.HKL", "merged.hkl"]:
                c = _pfile(project_dir, candidate, kind="xscale")
                if c.exists():
                    inp = c
                    break

    if not inp.exists():
        send("error_msg", {"message": "Input file not found: " + str(inp)})
        send("done", {})
        return

    ptl_mtz = _pout(project_dir, "aimless_pointless.mtz")
    aimless_mtz = _pout(project_dir, "aimless_scaled.mtz")
    aimless_unmerged = _pout(project_dir, "aimless_unmerged.mtz")
    aimless_xml = _pout(project_dir, "aimless.xml")
    ctruncate_mtz = _pout(project_dir, "aimless_truncate.mtz")

    # ══════════════════════════════════════════════════════════════════════
    # Step 1: POINTLESS — reindex and sort for AIMLESS
    # ══════════════════════════════════════════════════════════════════════
    if run_pointless or not ptl_mtz.exists():
        send("step_start", {"step": "POINTLESS"})

        inp_str = str(inp)
        is_xds = _is_xds_reflection_file(inp_str)
        cmd_ptl = [str(ptl_exe)]
        if is_xds:
            cmd_ptl += ["XDSIN", inp_str]
        else:
            cmd_ptl += ["HKLIN", inp_str]
        cmd_ptl += ["HKLOUT", str(ptl_mtz)]

        ptl_keywords = "SETTING SYMMETRY-BASED\nCHIRALITY CHIRAL\nEND\n"

        send("log", {"text": ">>> POINTLESS: " + " ".join(cmd_ptl)})
        cmd_ptl, env = _ccp4_command("pointless", cmd_ptl[1:], ccp4_scr)

        ptl_log = []
        try:
            def _ptl_line(t):
                ptl_log.append(t)
                send("log", {"text": t})
            rc, outcome = _run_streaming(cmd_ptl, _project_out_dir(project_dir), _ptl_line, timeout=1800, env=env,
                                         stdin_text=ptl_keywords, key=project_name)
            if outcome != "ok":
                raise RuntimeError(_outcome_message(outcome, "POINTLESS"))
        except Exception as e:
            send("error_msg", {"message": "POINTLESS failed: " + str(e)})
            send("step_done", {"step": "POINTLESS", "status": "error", "error": str(e)})
            send("done", {})
            return

        if rc != 0 or not ptl_mtz.exists():
            send("step_done", {"step": "POINTLESS", "status": "failed", "error": "POINTLESS exited with code " + str(rc)})
            send("done", {})
            return

        send("step_done", {"step": "POINTLESS", "status": "completed", "error": None})
        send("log", {"text": ">>> POINTLESS output: " + str(ptl_mtz)})
    else:
        send("log", {"text": ">>> Reusing existing " + str(ptl_mtz)})

    # ══════════════════════════════════════════════════════════════════════
    # Step 2: AIMLESS — scale and merge
    # ══════════════════════════════════════════════════════════════════════
    send("step_start", {"step": "AIMLESS"})

    cmd_aml = [
        str(aimless_exe),
        "HKLIN", str(ptl_mtz),
        "HKLOUT", str(aimless_mtz),
        "XMLOUT", str(aimless_xml),
    ]

    # Build keywords
    aml_kw = []
    aml_kw.append("BINS " + str(int(bins)))
    if resolution_low or resolution_high:
        lo = str(resolution_low) if resolution_low else "999"
        hi = str(resolution_high) if resolution_high else "0"
        aml_kw.append("RESOLUTION " + lo + " " + hi)
    if anomalous:
        aml_kw.append("ANOMALOUS ON")
    else:
        aml_kw.append("ANOMALOUS OFF")
    aml_kw.append("OUTPUT UNMERGED")
    aml_kw.append("PLOT NOXMGR")
    aml_kw.append("END")
    aml_stdin = "\n".join(aml_kw) + "\n"

    send("log", {"text": ">>> AIMLESS: " + " ".join(cmd_aml)})
    cmd_aml, env = _ccp4_command("aimless", cmd_aml[1:], ccp4_scr)
    send("log", {"text": ">>> Keywords: " + " | ".join(aml_kw[:-1])})

    aml_log = []
    try:
        def _aml_line(t):
            aml_log.append(t)
            send("log", {"text": t})
        rc, outcome = _run_streaming(cmd_aml, _project_out_dir(project_dir), _aml_line, timeout=7200, env=env,
                                     stdin_text=aml_stdin, key=project_name)
        if outcome != "ok":
            raise RuntimeError(_outcome_message(outcome, "AIMLESS"))
    except Exception as e:
        send("error_msg", {"message": "AIMLESS failed: " + str(e)})
        send("step_done", {"step": "AIMLESS", "status": "error", "error": str(e)})
        send("done", {})
        return

    # Save log
    aml_log_path = _pout(project_dir, "aimless.log")
    try:
        aml_log_path.write_text("\n".join(aml_log), encoding="utf-8")
    except Exception:
        pass

    if rc != 0:
        send("step_done", {"step": "AIMLESS", "status": "failed", "error": "AIMLESS exited with code " + str(rc)})
        send("done", {})
        return

    send("step_done", {"step": "AIMLESS", "status": "completed", "error": None})
    if aimless_mtz.exists():
        send("log", {"text": ">>> AIMLESS output: " + str(aimless_mtz)})

    # ── Parse AIMLESS log for statistics ──
    aml_full = "\n".join(aml_log)
    parsed = _parse_aimless_log(aml_full)
    if parsed:
        send("aimless_result", parsed)

    send("log", {"text": ">>> Log saved to: " + str(aml_log_path)})

    # ══════════════════════════════════════════════════════════════════════
    # Step 3: CTRUNCATE (optional) — I→F + twinning tests
    # ══════════════════════════════════════════════════════════════════════
    if run_ctruncate and aimless_mtz.exists():
        ctr_exe, _, ctr_problem = _ccp4_program("ctruncate")
        if not ctr_exe:
            send("log", {"text": ">>> CTRUNCATE skipped - " + ctr_problem})
        else:
            send("step_start", {"step": "CTRUNCATE"})

            cmd_ctr = [
                str(ctr_exe),
                "-hklin", str(aimless_mtz),
                "-hklout", str(ctruncate_mtz),
                "-colin", "/*/*/[IMEAN,SIGIMEAN]",
            ]
            # Add anomalous columns if anomalous was on
            if anomalous:
                cmd_ctr += ["-colano", "/*/*/[I(+),SIGI(+),I(-),SIGI(-)]"]

            send("log", {"text": ">>> CTRUNCATE: " + " ".join(cmd_ctr)})
            cmd_ctr, env = _ccp4_command("ctruncate", cmd_ctr[1:], ccp4_scr)

            ctr_log = []
            try:
                def _ctr_line(t):
                    ctr_log.append(t)
                    send("log", {"text": t})
                rc, outcome = _run_streaming(cmd_ctr, _project_out_dir(project_dir), _ctr_line, timeout=600, env=env,
                                             stdin_text="END\n", key=project_name)
                if outcome != "ok":
                    raise RuntimeError(_outcome_message(outcome, "CTRUNCATE"))
            except Exception as e:
                send("step_done", {"step": "CTRUNCATE", "status": "error", "error": str(e)})
                send("done", {})
                return

            # Save log
            ctr_log_path = _pout(project_dir, "ctruncate.log")
            try:
                ctr_log_path.write_text("\n".join(ctr_log), encoding="utf-8")
            except Exception:
                pass

            if rc != 0:
                send("step_done", {"step": "CTRUNCATE", "status": "failed", "error": "CTRUNCATE exited with code " + str(rc)})
            else:
                send("step_done", {"step": "CTRUNCATE", "status": "completed", "error": None})
                if ctruncate_mtz.exists():
                    send("log", {"text": ">>> Final MTZ with amplitudes: " + str(ctruncate_mtz)})

                # Parse CTRUNCATE log for twinning results
                ctr_full = "\n".join(ctr_log)
                ctr_parsed = _parse_ctruncate_log(ctr_full)
                if ctr_parsed:
                    send("ctruncate_result", ctr_parsed)

    send("done", {})


def _parse_aimless_log(text):
    """Parse AIMLESS log text for statistics tables and batch data.

    AIMLESS uses CCP4 $TABLE format for structured output. We extract:
    - Overall summary statistics
    - Resolution shell table (from 'Summary data for' table)
    - Scale/B vs batch data (from 'Analysis against Batch' tables)
    """
    result = {}
    lines = text.split('\n')

    # ── Extract overall summary ──
    # AIMLESS summary block has 3 columns: Overall  InnerShell  OuterShell
    # Numbers are at positions parts[-3] (overall), parts[-2] (inner), parts[-1] (outer)
    # We look for the "Summary data for" section which has the definitive stats.
    in_summary = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('Summary data for'):
            in_summary = True
            continue
        if not in_summary:
            continue
        # Stop at end of summary section
        if s.startswith('$$') or s.startswith('===='):
            if result.get('space_group'):
                break  # We have everything
            continue
        # Parse each stat line: "Label    overall    inner    outer"
        # Rmerge lines (multiple variants)
        if s.startswith('Rmerge') and 'all I+' in s:
            parts = s.split()
            if len(parts) >= 3:
                try: result['rmerge_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['rmerge_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Rmeas') and 'all I+' in s:
            parts = s.split()
            if len(parts) >= 3:
                try: result['rmeas_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['rmeas_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Rpim') and 'all I+' in s:
            parts = s.split()
            if len(parts) >= 3:
                try: result['rpim_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['rpim_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        # If no "all I+" variants, take "within I+/I-" as fallback
        elif s.startswith('Rmerge') and 'within' in s and 'rmerge_overall' not in result:
            parts = s.split()
            if len(parts) >= 3:
                try: result['rmerge_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['rmerge_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Rmeas') and 'within' in s and 'rmeas_overall' not in result:
            parts = s.split()
            if len(parts) >= 3:
                try: result['rmeas_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['rmeas_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Rpim') and 'within' in s and 'rpim_overall' not in result:
            parts = s.split()
            if len(parts) >= 3:
                try: result['rpim_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['rpim_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Mean((I)/sd(I))'):
            parts = s.split()
            if len(parts) >= 2:
                try: result['isig_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['isig_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Mn(I) half-set correlation CC(1/2)'):
            parts = s.split()
            if len(parts) >= 2:
                try: result['cc_half_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['cc_half_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Completeness') and 'Anomalous' not in s:
            parts = s.split()
            if len(parts) >= 2:
                try: result['completeness_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['completeness_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif s.startswith('Multiplicity') and 'Anomalous' not in s:
            parts = s.split()
            if len(parts) >= 2:
                try: result['multiplicity_overall'] = float(parts[-3])
                except (ValueError, IndexError): pass
                try: result['multiplicity_outer'] = float(parts[-1])
                except (ValueError, IndexError): pass
        elif 'Total number of observations' in s:
            parts = s.split()
            # Overall is parts[-3], not parts[-1] (which is outer shell)
            try: result['n_obs'] = int(parts[-3])
            except (ValueError, IndexError): pass
        elif 'Total number unique' in s:
            parts = s.split()
            try: result['n_unique'] = int(parts[-3])
            except (ValueError, IndexError): pass
        elif s.startswith('High resolution limit'):
            parts = s.split()
            if len(parts) >= 4:
                try: result['resolution_high'] = float(parts[-3])
                except (ValueError, IndexError): pass
        elif s.startswith('Low resolution limit'):
            parts = s.split()
            if len(parts) >= 4:
                try: result['resolution_low'] = float(parts[-3])
                except (ValueError, IndexError): pass
        # Space group and cell
        elif s.startswith('Space group:'):
            result['space_group'] = s.split(':', 1)[1].strip()
        elif s.startswith('Average unit cell:'):
            cell_str = s.split(':', 1)[1].strip()
            try:
                cell_vals = [float(x) for x in cell_str.split()]
                if len(cell_vals) == 6:
                    result['unit_cell'] = cell_vals
            except ValueError:
                pass

    # Fallback: if we didn't find summary section, try scanning entire log
    if 'space_group' not in result:
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith('Space group:'):
                result['space_group'] = s.split(':', 1)[1].strip()
            elif s.startswith('Average unit cell:'):
                cell_str = s.split(':', 1)[1].strip()
                try:
                    cell_vals = [float(x) for x in cell_str.split()]
                    if len(cell_vals) == 6:
                        result['unit_cell'] = cell_vals
                except ValueError:
                    pass

    # ── Extract resolution shell tables ──
    # AIMLESS outputs multiple $TABLE blocks against resolution.
    # CCP4 $TABLE format (AIMLESS style — headers and $$ on same line):
    #   $TABLE: title:
    #   $GRAPHS: ...
    #   $$
    #   col_header1 col_header2 ...  $$ $$
    #   data_row_1
    #   data_row_2
    #   ...
    #   $$
    # The "headers $$ $$" pattern means: headers, then end-of-headers ($$),
    # then end-of-optional-text ($$) on the SAME line. Data follows until
    # the next standalone $$.
    #
    # We specifically target these tables by title keywords:
    #   "Analysis against resolution" — R-factors (Rmrg, Rmeas, Rpim, etc.)
    #   "Analysis against resolution, with & without anomalous" — anom R-factors
    #   "Completeness & multiplicity" — Nobs, Nuniq, %poss, Mlplct
    # We EXCLUDE tables about "Batch" (e.g. "CC(1/2) in resolution ranges vs. Batch")
    res_tables = []  # list of {title, headers, rows}
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        # Match $TABLE lines about resolution but NOT about batch
        if '$TABLE' in s and 'esolution' in s and 'atch' not in s:
            table_title = s.replace('$TABLE', '').strip().strip(':').strip()
            col_headers = []
            rows = []
            i += 1
            in_data = False
            # Parse through the $TABLE structure
            while i < len(lines):
                s2 = lines[i].strip()
                if in_data:
                    # We are in the data section — collect until standalone $$
                    if s2 == '$$' or (s2.startswith('$$') and len(s2.replace('$','').strip()) == 0):
                        break
                    # Also stop if we hit "Overall:" summary line (outside data)
                    if s2.startswith('Overall:'):
                        break
                    vals = s2.split()
                    if len(vals) >= 4:
                        try:
                            float(vals[0])
                            rows.append(vals)
                        except ValueError:
                            pass
                else:
                    # Looking for the header line
                    # AIMLESS format: "  headers  $$ $$" — headers followed by $$ $$
                    if '$$' in s2 and not s2.startswith('$TABLE') and not s2.startswith('$GRAPHS'):
                        # Check if this line has "headers $$ $$" pattern
                        # or just a bare "$$" line
                        stripped = s2.replace('$$', ' ').strip()
                        if stripped and not stripped.startswith('$'):
                            # This is the combined header line: "N 1/d^2 Dmid Rmrg ... $$ $$"
                            col_headers = stripped.split()
                            # Count $$ occurrences — if >= 2, data starts next line
                            dollar_pairs = s2.count('$$')
                            if dollar_pairs >= 2:
                                in_data = True
                            # If only 1 $$, next $$ starts data
                            elif dollar_pairs == 1:
                                # Look for next $$ line which ends the "optional text" section
                                i += 1
                                while i < len(lines):
                                    s3 = lines[i].strip()
                                    if '$$' in s3:
                                        in_data = True
                                        break
                                    i += 1
                        # else: bare $$ line, skip
                i += 1
            if rows and col_headers:
                res_tables.append({
                    'title': table_title,
                    'headers': col_headers,
                    'rows': rows
                })
        i += 1

    # Also try to find "Completeness" table which may use "v." instead of "against"
    # e.g. "Completeness & multiplicity v. resolution"
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if '$TABLE' in s and 'ompleteness' in s and 'esolution' in s:
            # Check if already captured
            already = any(t['title'] and 'ompleteness' in t['title'] for t in res_tables)
            if not already:
                table_title = s.replace('$TABLE', '').strip().strip(':').strip()
                col_headers = []
                rows = []
                i += 1
                in_data = False
                while i < len(lines):
                    s2 = lines[i].strip()
                    if in_data:
                        if s2 == '$$' or (s2.startswith('$$') and len(s2.replace('$','').strip()) == 0):
                            break
                        if s2.startswith('Overall:'):
                            break
                        vals = s2.split()
                        if len(vals) >= 4:
                            try:
                                float(vals[0])
                                rows.append(vals)
                            except ValueError:
                                pass
                    else:
                        if '$$' in s2 and not s2.startswith('$TABLE') and not s2.startswith('$GRAPHS'):
                            stripped = s2.replace('$$', ' ').strip()
                            if stripped and not stripped.startswith('$'):
                                col_headers = stripped.split()
                                if s2.count('$$') >= 2:
                                    in_data = True
                                else:
                                    i += 1
                                    while i < len(lines):
                                        if '$$' in lines[i].strip():
                                            in_data = True
                                            break
                                        i += 1
                    i += 1
                if rows and col_headers:
                    res_tables.append({
                        'title': table_title,
                        'headers': col_headers,
                        'rows': rows
                    })
        i += 1

    # Identify R-factor table vs completeness/counts table by column names
    rfac_table = None
    count_table = None
    cc_table = None
    for t in res_tables:
        hdr_lower = ' '.join(t['headers']).lower()
        # R-factor table: has Rmrg/Rmerge AND Rpim columns
        if ('rmrg' in hdr_lower or 'rmerge' in hdr_lower) and 'rpim' in hdr_lower:
            # Prefer the simpler table (without "Ov" anomalous columns)
            if rfac_table is None or ('ov' not in hdr_lower and 'Ov' not in ' '.join(t['headers'])):
                rfac_table = t
        # Completeness table: has %poss or Nref columns
        elif '%poss' in hdr_lower or 'nref' in hdr_lower:
            count_table = t
        # CC table: has CC1/2 or CChalf
        elif 'cc1/2' in hdr_lower or 'cchalf' in hdr_lower:
            cc_table = t

    # Store each table with its headers so frontend can label correctly
    if rfac_table:
        result['rfac_table'] = {
            'headers': rfac_table['headers'],
            'rows': rfac_table['rows']
        }
    if count_table:
        result['count_table'] = {
            'headers': count_table['headers'],
            'rows': count_table['rows']
        }
    if cc_table:
        result['cc_table'] = {
            'headers': cc_table['headers'],
            'rows': cc_table['rows']
        }
    # Also keep a flat list of all resolution tables for any table not matched above
    if res_tables:
        result['all_res_tables'] = [{
            'title': t['title'],
            'headers': t['headers'],
            'rows': t['rows']
        } for t in res_tables]

    # If no $TABLE shells found, try parsing the text-format resolution table
    if not res_tables:
        shells = []
        for i, line in enumerate(lines):
            s = line.strip()
            # Look for lines like " 50.00 -  5.00   ..."
            if ' - ' in s and not s.startswith('#') and not s.startswith('!'):
                parts = s.split()
                if len(parts) >= 8:
                    try:
                        float(parts[0])
                        float(parts[2])
                        shells.append(parts)
                    except (ValueError, IndexError):
                        pass
        if shells:
            result['shells'] = shells

    # ── Extract anisotropy information ──
    # AIMLESS outputs "Estimated B factors" per axis when anisotropy is present
    # Format varies but typically:
    #   "Estimated B factor from Wilson plot:  23.5"
    #   "Estimated B factors along a*, b*, c* :  18.2  25.1  30.4"
    # or within a "Diffraction anisotropy" section
    for i, line in enumerate(lines):
        s = line.strip()
        if 'anisotrop' in s.lower() and 'b factor' in s.lower() or \
           ('B factor' in s and ('a*' in s or 'b*' in s or 'c*' in s)):
            parts = s.split()
            # Try to extract 3 B-factor values from the line
            floats = []
            for p in parts:
                try:
                    v = float(p)
                    if 0 < v < 500:
                        floats.append(v)
                except ValueError:
                    pass
            if len(floats) >= 3:
                result['anisotropy_b_factors'] = {
                    'a_star': floats[0], 'b_star': floats[1], 'c_star': floats[2]
                }
                break
            elif len(floats) == 1:
                # Single B factor — just the isotropic Wilson B
                pass
        # Also look for "Diffraction anisotropy analysis" section
        if 'falloff' in s.lower() and ('direction' in s.lower() or 'axis' in s.lower()):
            if 'anisotropy_falloff' not in result:
                result['anisotropy_falloff'] = s

    # ── Extract batch data (Scale & B vs batch) ──
    # Table title: "Scales v rotation range" with headers including Mn(k), Bfactor
    batch_data = {'batches': [], 'scales': [], 'bfactors': []}
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if '$TABLE' in s and ('cales' in s or 'Scale' in s) and ('otation' in s or 'atch' in s):
            i += 1
            in_data = False
            batch_col_headers = []
            while i < len(lines):
                s2 = lines[i].strip()
                if in_data:
                    if s2 == '$$' or (s2.startswith('$$') and len(s2.replace('$','').strip()) == 0):
                        break
                    vals = s2.split()
                    if len(vals) >= 6:
                        try:
                            # Headers: N Run Phi Batch Mn(k) 0k Number Bfactor Bdecay
                            batch_num = float(vals[3])  # Batch column
                            scale = float(vals[4])      # Mn(k) column
                            bfac = float(vals[7]) if len(vals) > 7 else 0.0  # Bfactor column
                            batch_data['batches'].append(batch_num)
                            batch_data['scales'].append(scale)
                            batch_data['bfactors'].append(bfac)
                        except (ValueError, IndexError):
                            pass
                else:
                    if '$$' in s2 and not s2.startswith('$TABLE') and not s2.startswith('$GRAPHS'):
                        stripped = s2.replace('$$', ' ').strip()
                        if stripped and not stripped.startswith('$'):
                            batch_col_headers = stripped.split()
                            if s2.count('$$') >= 2:
                                in_data = True
                            else:
                                i += 1
                                while i < len(lines):
                                    if '$$' in lines[i].strip():
                                        in_data = True
                                        break
                                    i += 1
                i += 1
            break  # Only need one batch table
        i += 1

    if batch_data['batches']:
        result['batch_data'] = batch_data

    return result if result else None


def _parse_ctruncate_log(text):
    """Parse CTRUNCATE log for twinning test results and Wilson B-factor."""
    result = {}
    lines = text.split('\n')

    for i, line in enumerate(lines):
        s = line.strip()
        # Wilson B
        if 'Wilson B factor' in s:
            parts = s.split()
            for j, p in enumerate(parts):
                if p == 'factor':
                    if j + 1 < len(parts):
                        # Might be "factor : 25.3" or "factor = 25.3"
                        val_str = parts[j+1].strip(':=').strip()
                        if not val_str and j + 2 < len(parts):
                            val_str = parts[j+2]
                        try:
                            result['wilson_b'] = float(val_str)
                        except (ValueError, TypeError):
                            pass
                        break
        # L-test for twinning
        elif '<|L|>' in s or 'Padilla' in s:
            parts = s.split()
            for j, p in enumerate(parts):
                try:
                    v = float(p)
                    if 0 < v < 1 and 'l_statistic' not in result:
                        result['l_statistic'] = v
                except ValueError:
                    pass
        elif '<L^2>' in s or '<L**2>' in s:
            parts = s.split()
            for j, p in enumerate(parts):
                try:
                    v = float(p)
                    if 0 < v < 1:
                        result['l2_statistic'] = v
                except ValueError:
                    pass
        # Twinning warning
        elif 'twinning' in s.lower() and ('warning' in s.lower() or 'possible' in s.lower() or 'apparent' in s.lower() or 'detected' in s.lower()):
            if 'twin_warning' not in result:
                result['twin_warning'] = s
        # Anisotropy
        elif 'anisotropy' in s.lower() and ('correction' in s.lower() or 'ratio' in s.lower()):
            if 'anisotropy_info' not in result:
                result['anisotropy_info'] = s

    return result if result else None


@_processing_job("xdscc12")
def stream_xdscc12(project_name, write_fn, batch_width=1, nbin=5):
    """Run XDSCC12 on XDS_ASCII.HKL, streaming output via SSE write_fn.

    Computes per-frame ΔCC½ for identifying bad/damaged frames.
    Reference: Assmann, Brehm & Diederichs (2016) J. Appl. Cryst. 49, 1021-1028.
    """
    global XDSCC12_BIN
    project_dir = _pdir(project_name)

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    # Re-check binary (may have been installed since startup)
    if not XDSCC12_BIN:
        XDSCC12_BIN = _find_xdscc12()
    if not XDSCC12_BIN:
        send("error_msg", {"message":
            "XDSCC12 not found. Install it from "
            "https://wiki.uni-konstanz.de/xds/index.php/Xdscc12 "
            "or use the Download button to install automatically."})
        send("done", {})
        return

    # Check binary still exists on disk
    if not Path(XDSCC12_BIN).exists():
        XDSCC12_BIN = _find_xdscc12()
        if not XDSCC12_BIN:
            send("error_msg", {"message": "XDSCC12 binary no longer found at previously detected path."})
            send("done", {})
            return

    # Locate XDS_ASCII.HKL - in the folder xdscc12 runs in (it is given the bare name)
    hkl_file = _project_out_dir(project_dir) / "XDS_ASCII.HKL"
    if not hkl_file.exists():
        send("error_msg", {"message":
            "XDS_ASCII.HKL not found in project directory. "
            "Run CORRECT first to produce unmerged reflection data."})
        send("done", {})
        return

    # Build command
    cmd = [XDSCC12_BIN]
    try:
        bw = float(batch_width)
        if bw > 0:
            cmd += ["-t", str(int(bw)) if bw == int(bw) else str(bw)]
    except (ValueError, TypeError):
        cmd += ["-t", "1"]
    try:
        nb = int(nbin)
        if nb > 0:
            cmd += ["-nbin", str(nb)]
    except (ValueError, TypeError):
        cmd += ["-nbin", "5"]
    cmd.append("XDS_ASCII.HKL")

    send("step_start", {"step": "XDSCC12"})
    send("log", {"text": ">>> Command: " + " ".join(cmd)})
    send("log", {"text": ">>> Working dir: " + str(project_dir)})

    captured_log = []

    try:
        def _cc12_line(t):
            captured_log.append(t)
            send("log", {"text": t})
        rc, outcome = _run_streaming(cmd, _project_out_dir(project_dir), _cc12_line, key=project_name)
        if outcome != "ok":
            raise RuntimeError(_outcome_message(outcome, "XDSCC12"))
    except Exception as e:
        send("error_msg", {"message": str(e)})
        send("step_done", {"step": "XDSCC12", "status": "error", "error": str(e)})
        send("done", {})
        return

    # Save log
    log_path = _pout(project_dir, "XDSCC12.LP")
    try:
        log_path.write_text("\n".join(captured_log), encoding="utf-8")
    except Exception:
        pass

    # Check result
    status, error_msg = "completed", None
    if rc != 0:
        status = "failed"
        error_msg = "XDSCC12 exited with code " + str(rc)

    send("step_done", {"step": "XDSCC12", "status": status, "error": error_msg})

    # Parse and send structured results
    if status == "completed" and captured_log:
        try:
            full_log = "\n".join(captured_log)
            parsed = LPParser.parse_xdscc12(full_log)
            if parsed.get('frames'):
                send("xdscc12_result", parsed)
        except Exception as e:
            send("log", {"text": ">>> Warning: could not parse XDSCC12 output: " + str(e)})

    send("done", {})


def download_xdscc12(write_fn):
    """Download the XDSCC12 binary for the current platform.

    Downloads from wiki.uni-konstanz.de to ~/.local/bin/ (no root needed).
    Updates the global XDSCC12_BIN variable on success.
    """
    global XDSCC12_BIN
    import platform as _dl_plat
    import urllib.request
    import stat

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    system = _dl_plat.system()
    if system not in XDSCC12_URLS:
        send("error_msg", {"message":
            "XDSCC12 is only available for Linux and macOS. "
            "Detected platform: " + system})
        send("done", {})
        return

    url = XDSCC12_URLS[system]

    # Determine install directory (no root needed)
    install_dir = Path.home() / ".local" / "bin"
    try:
        install_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to ~/bin
        install_dir = Path.home() / "bin"
        try:
            install_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            send("error_msg", {"message": "Cannot create install directory: " + str(e)})
            send("done", {})
            return

    dest = install_dir / "xdscc12"

    send("log", {"text": ">>> Platform: " + system})
    send("log", {"text": ">>> Downloading XDSCC12 from " + url})
    send("log", {"text": ">>> Install path: " + str(dest)})

    try:
        import hashlib
        tmp = dest.with_name(dest.name + ".download")
        with urllib.request.urlopen(url, timeout=120) as resp, open(tmp, "wb") as out:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read()
            out.write(data)
        # A login page or an error page instead of the program: refuse it
        if len(data) < 100000 or "text/html" in ctype or data[:4] not in (b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
            try:
                tmp.unlink()
            except OSError:
                pass
            send("error_msg", {"message": "The download does not look like the XDSCC12 program (%d bytes, %s). Download it by hand from %s." % (len(data), ctype or "unknown type", url)})
            send("done", {})
            return
        send("log", {"text": ">>> Downloaded %d bytes, SHA-256 %s" % (len(data), hashlib.sha256(data).hexdigest())})
        os.replace(str(tmp), str(dest))
    except Exception as e:
        send("error_msg", {"message": "Download failed: " + str(e)})
        send("done", {})
        return

    # Make executable
    try:
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception as e:
        send("error_msg", {"message": "chmod +x failed: " + str(e)})
        send("done", {})
        return

    # Verify the binary actually runs
    try:
        subprocess.run(
            [str(dest), "-h"],
            capture_output=True, text=True, timeout=10
        )
        send("log", {"text": ">>> Binary verification: OK"})
    except Exception as e:
        send("error_msg", {"message":
            "Downloaded binary failed to execute: " + str(e)
            + ". It may not be compatible with your system."})
        try:
            dest.unlink()
        except Exception:
            pass
        send("done", {})
        return

    # Update global
    XDSCC12_BIN = str(dest)
    send("log", {"text": ">>> XDSCC12 installed successfully at " + str(dest)})
    send("log", {"text": ">>> Tip: add " + str(install_dir) + " to $PATH for future sessions."})
    send("xdscc12_installed", {"path": str(dest)})
    send("done", {})


def load_aimless_cached_results(project_dir):
    """Read previously saved aimless.log and ctruncate.log from disk and return parsed results.

    Returns dict with keys:
        'aimless': parsed AIMLESS stats (or None)
        'ctruncate': parsed CTRUNCATE stats (or None)
        'has_results': bool
    Used by the handler to serve cached results when the Aimless tab is opened.
    """
    from pathlib import Path
    project_dir = Path(project_dir)
    result = {'aimless': None, 'ctruncate': None, 'has_results': False}

    aml_log = _pfile(project_dir, "aimless.log")
    if aml_log.exists():
        try:
            text = aml_log.read_text(encoding="utf-8", errors="replace")
            parsed = _parse_aimless_log(text)
            if parsed and (parsed.get('rmeas_overall') is not None or parsed.get('rmerge_overall') is not None):
                result['aimless'] = parsed
                result['has_results'] = True
        except Exception:
            pass

    ctr_log = _pfile(project_dir, "ctruncate.log")
    if ctr_log.exists():
        try:
            text = ctr_log.read_text(encoding="utf-8", errors="replace")
            parsed = _parse_ctruncate_log(text)
            if parsed:
                result['ctruncate'] = parsed
        except Exception:
            pass

    return result


def load_pointless_cached_results(project_dir):
    """Read previously saved pointless.log from disk and return parsed results.

    Returns dict with keys:
        'result': parsed POINTLESS result (or None)
        'has_results': bool
    Used by the handler to serve cached results when the Pointless tab is opened.
    """
    from pathlib import Path
    project_dir = Path(project_dir)
    result = {'result': None, 'has_results': False}

    ptl_log = _pfile(project_dir, "pointless.log")
    if ptl_log.exists():
        try:
            text = ptl_log.read_text(encoding="utf-8", errors="replace")
            parsed = LPParser.parse_pointless(text)
            if parsed.get('best_solution') and len(parsed['best_solution']) > 0:
                result['result'] = parsed
                result['has_results'] = True
            elif parsed.get('space_groups'):
                result['result'] = parsed
                result['has_results'] = True
        except Exception:
            pass

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  AutoPilot — Fully Automated XDS Processing Pipeline
# ═══════════════════════════════════════════════════════════════════════════════
# State machine: INIT → PROCESS → DIAGNOSE → (AUTOINDEX) → ANALYZE →
#                XSCALE → CONVERT → DONE
# Streams progress via SSE.  Diagnoses errors and applies fixes automatically.
# ═══════════════════════════════════════════════════════════════════════════════

# The files a GXPARM re-integration replaces.  'if_better' copies them aside
# before it starts and puts them back when the re-integration loses.
_AP_INTEGRATION_FILES = ("XDS.INP", "XPARM.XDS", "GXPARM.XDS", "INTEGRATE.LP", "INTEGRATE.HKL",
                         "CORRECT.LP", "XDS_ASCII.HKL", "DEFPIX.LP", "BKGPIX.cbf", "ABS.cbf",
                         "GAIN.cbf", "BLANK.cbf", "DECAY.cbf", "MODPIX.cbf", "ABSORP.cbf")


def _ap_snapshot_integration(project_dir, send):
    """Copy the first integration's files aside. Returns the folder, or None."""
    import shutil as _sh
    out_dir = _project_out_dir(project_dir)
    snap = out_dir / "pre_optimize"
    try:
        if snap.exists():
            _sh.rmtree(str(snap))
        snap.mkdir(parents=True)
        copied = 0
        for name in _AP_INTEGRATION_FILES:
            src = (project_dir / name) if name == "XDS.INP" else (out_dir / name)
            if src.is_file():
                _sh.copy2(str(src), str(snap / name))
                copied += 1
        send("ap_log", {"text": ">>> First integration put aside (" + str(copied) + " files) in case the re-integration fails or is worse"})
        return snap
    except Exception as exc:
        send("ap_log", {"text": ">>> Could not put the first integration aside (" + str(exc) + ") - re-integration will be kept"})
        return None


def _ap_restore_integration(project_dir, snap, send):
    """Put the first integration's files back."""
    import shutil as _sh
    out_dir = _project_out_dir(project_dir)
    restored = 0
    for item in sorted(Path(snap).iterdir()):
        target = (project_dir / item.name) if item.name == "XDS.INP" else (out_dir / item.name)
        try:
            _sh.copy2(str(item), str(target))
            restored += 1
        except OSError as exc:
            send("ap_log", {"text": ">>>   could not restore " + item.name + ": " + str(exc)})
    send("ap_log", {"text": ">>> First integration restored (" + str(restored) + " files)"})


def _ap_optimize_is_better(pre, post, metric='isa'):
    """Did the re-integration improve the chosen metric? Returns (bool, reason).

    isa and cc_half must not go down; resolution (the cut-off, in A) must not go
    up.  When either value is missing there is nothing to judge, and the
    re-integration is kept as AutoPilot always did.
    """
    def num(v):
        try:
            return float(str(v).replace('%', '').replace('*', ''))
        except (TypeError, ValueError):
            return None
    label = {'isa': 'ISa', 'resolution': 'resolution cut-off', 'cc_half': 'overall CC1/2'}.get(metric, metric)
    before, after = num(pre.get(metric)), num(post.get(metric))
    if after is None and before is not None:
        return False, label + " could not be determined after the re-integration"
    if before is None or after is None:
        return True, label + " not available on both sides, nothing to compare"
    if metric == 'resolution':
        better = after <= before
        return better, "%s %.2f -> %.2f A" % (label, before, after)
    better = after >= before
    return better, "%s %.2f -> %.2f" % (label, before, after)


def _ap_apply_xdsinp_fix(xds_inp_path, fix_params, send):
    """Apply parameter fixes to XDS.INP for autopilot error recovery.

    fix_params: dict of PARAM_NAME -> value (str).
    Special key '_exclude_resolution_ranges': list of {lo, hi, label} dicts
    to APPEND as EXCLUDE_RESOLUTION_RANGE lines.
    Special key '_exclude_data_ranges': list of {first, last, reason} dicts
    to APPEND as EXCLUDE_DATA_RANGE lines.

    Returns True if any change was made.
    """
    if not fix_params:
        return False

    text = _read_text_lenient(xds_inp_path)
    lines = text.splitlines(keepends=True)
    changed = False

    # Handle EXCLUDE_RESOLUTION_RANGE additions (append, don't replace)
    excl_ranges = fix_params.pop('_exclude_resolution_ranges', None)
    if excl_ranges:
        for rng in excl_ranges:
            entry = "EXCLUDE_RESOLUTION_RANGE= {lo} {hi}  ! ice ring {label}\n".format(**rng)
            # Check it isn't already present
            key_str = "{lo} {hi}".format(**rng)
            if key_str not in text:
                lines.append(entry)
                send("ap_log", {"text": "  + Added " + entry.strip()})
                changed = True

    # Handle EXCLUDE_DATA_RANGE additions (append, don't replace)
    excl_data = fix_params.pop('_exclude_data_ranges', None)
    if excl_data:
        for rng in excl_data:
            first = str(rng['first'])
            last = str(rng['last'])
            reason = rng.get('reason', '')
            entry = "EXCLUDE_DATA_RANGE= " + first + " " + last
            if reason:
                entry += "  ! " + reason
            entry += "\n"
            # Check it isn't already present
            key_str = first + " " + last
            already = False
            for existing in lines:
                if 'EXCLUDE_DATA_RANGE' in existing and key_str in existing and not existing.strip().startswith('!'):
                    already = True
                    break
            if not already:
                lines.append(entry)
                send("ap_log", {"text": "  + Added " + entry.strip()})
                changed = True

    # Handle regular parameter updates
    for param, value in fix_params.items():
        if param.startswith('_'):
            continue  # skip internal keys
        # Try to find and replace existing line
        found = False
        new_lines = []
        param_upper = param.upper()
        for line in lines:
            stripped = line.strip()
            # Match uncommented lines starting with this param
            if not stripped.startswith('!') and stripped.upper().startswith(param_upper) and '=' in stripped:
                eq_idx = stripped.index('=')
                before_eq = stripped[:eq_idx].strip().upper().replace(' ', '')
                if before_eq == param_upper.replace(' ', '').replace('(', '(').replace(')', ')'):
                    new_line = param + "= " + value + "\n"
                    new_lines.append(new_line)
                    found = True
                    changed = True
                    send("ap_log", {"text": "  ~ " + param + " = " + value})
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        lines = new_lines

        if not found:
            # Append the parameter
            lines.append(param + "= " + value + "\n")
            changed = True
            send("ap_log", {"text": "  + " + param + " = " + value})

    if changed:
        xds_inp_path.write_text("".join(lines), encoding="utf-8")

    return changed


def _ap_best_autoindex_trial(project_dir):
    """The best successful trial of the last auto-indexing run (AUTOINDEX_RESULTS.json), or None."""
    try:
        data = json.loads((Path(project_dir) / "AUTOINDEX_RESULTS.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    trials = [r for r in (data.get("all_results") or data.get("top5") or []) if isinstance(r, dict) and r.get("success")]
    if not trials:
        return None
    return max(trials, key=lambda r: (float(r.get("score") or 0), float(r.get("indexed_fraction") or 0)))


def _ap_autoindex_params(trial):
    """XDS.INP keywords a trial stands for - the same ones the Auto-Index card's Apply writes."""
    params = {"SIGNAL_PIXEL": str(trial["signal_pixel"]),
              "SPOT_RANGE": [[str(a), str(b)] for a, b in trial["spot_ranges"]]}
    if trial.get("index_error") is not None:
        params["INDEX_ERROR"] = str(trial["index_error"])
    if trial.get("min_pixels") is not None:
        params["MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT"] = str(trial["min_pixels"])
    if trial.get("index_origin") is not None:
        params["INDEX_ORIGIN"] = " ".join(str(v) for v in trial["index_origin"])
    return params


def _ap_set_job(xds_inp_path, job_str):
    """Set the JOB= line in XDS.INP."""
    lines = _read_text_lenient(xds_inp_path).splitlines(keepends=True)
    new_lines, found = [], False
    for line in lines:
        if line.strip().startswith("JOB="):
            new_lines.append("JOB= " + job_str + "\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.insert(0, "JOB= " + job_str + "\n")
    xds_inp_path.write_text("".join(new_lines), encoding="utf-8")


def _sg_from_absences_choice(correct_data):
    """The space group CrystalPilot's absence analysis of CORRECT.LP points to when it
    differs from XDS's choice.  Returns (suggestion, [enantiomorph names]) or
    (None, why not)."""
    cur = correct_data.get('space_group')
    sugg = correct_data.get('sg_suggestions') or []
    if not cur or not sugg:
        return None, 'no axial reflections to judge them by'
    if cur in [s.get('sg_number') for s in sugg]:
        return None, 'the absences agree with ' + str(correct_data.get('current_sg_name') or cur)
    # enantiomorphs have the same screw periods: absences cannot tell them apart
    if len({tuple(sorted((s.get('screws') or {}).items())) for s in sugg}) != 1:
        return None, 'the absences allow ' + ', '.join(str(s.get('name')) for s in sugg)
    return sugg[0], [str(s.get('name')) for s in sugg[1:]]


def _ap_sg_from_absences(work_dir, xds_inp_path, xds_exe, correct_data, send):
    """XDS's space group never has screw axes (C222 for C222₁).  When the axial
    reflections in CORRECT.LP show them, CORRECT runs again in the matching space
    group with the refined cell - seconds, no re-integration.
    Returns (new CORRECT data or None, note for the summary, stopped)."""
    given = str(_parse_xdsinp_params(_read_text_lenient(xds_inp_path)).get('SPACE_GROUP_NUMBER', '')).strip()
    if given and given != '0':
        send("ap_log", {"text": ">>> Screw axes: space group " + given + " is given in XDS.INP - kept"})
        return None, '', False
    choice, other = _sg_from_absences_choice(correct_data)
    if not choice:
        send("ap_log", {"text": ">>> Screw axes: " + other + " - space group kept"})
        return None, '', False
    uc = correct_data.get('unit_cell') or {}
    keys = ('a', 'b', 'c', 'alpha', 'beta', 'gamma')
    if not all(k in uc for k in keys):
        send("ap_log", {"text": ">>> Screw axes: no refined cell in CORRECT.LP - space group kept"})
        return None, '', False
    axes = {'h00': 'h,0,0', '0k0': '0,k,0', '00l': '0,0,l'}
    seen = ', '.join('%s only every %s%s present' % (axes.get(ax, ax), per, 'nd' if per == 2 else 'th')
                     for ax, per in sorted((choice.get('screws') or {}).items()))
    xds_name = '%s (#%s)' % (correct_data.get('current_sg_name') or '', correct_data.get('space_group'))
    new_name = '%s (#%s)' % (choice.get('name'), choice.get('sg_number'))
    send("ap_log", {"text": ">>> Screw axes from the systematic absences: " + seen})
    send("ap_log", {"text": "    -> " + new_name + ", not " + xds_name + " as XDS chose; CORRECT runs again in " + str(choice.get('name'))})
    before = _read_text_lenient(xds_inp_path)
    _ap_apply_xdsinp_fix(xds_inp_path, {'SPACE_GROUP_NUMBER': str(choice['sg_number']),
                                        'UNIT_CELL_CONSTANTS': ' '.join('%.3f' % float(uc[k]) for k in keys)}, send)
    _ap_set_job(xds_inp_path, "CORRECT")
    rc, stopped = _ap_run_xds(work_dir, xds_exe, send, label="CORRECT (space group from the screw axes)")
    if stopped:
        return None, '', True
    lp, err, errline = _ap_check_lp(work_dir, "CORRECT")
    data = LPParser.parse_correct(lp) if lp and not err else None
    if not data or data.get('space_group') != choice.get('sg_number'):
        # back to what XDS chose, and its CORRECT output
        send("ap_log", {"text": ">>> CORRECT in " + str(choice.get('name')) + " did not work (" + str(errline or 'no result')
                                + ") - back to " + xds_name})
        xds_inp_path.write_text(before, encoding="utf-8")
        _ap_set_job(xds_inp_path, "CORRECT")
        rc, stopped = _ap_run_xds(work_dir, xds_exe, send, label="CORRECT (back to XDS's space group)")
        return None, '', stopped
    note = new_name + ' from the screw axes (XDS chose ' + xds_name + ')'
    if other:
        note += '; or its enantiomorph ' + ', '.join(other) + ' - absences cannot tell them apart'
    send("ap_log", {"text": ">>> Space group: " + note})
    return data, note, False


def _ap_run_xds(work_dir, xds_exe, send, label="XDS", timeout=7200):
    """Run XDS in work_dir, streaming output. Returns (returncode, was_stopped).

    Respects the global _job_stopped() flag.
    """
    rc, outcome = _run_streaming([str(xds_exe)], work_dir, lambda t: send("ap_log", {"text": t}),
                                 timeout=timeout, should_stop=lambda: _job_stopped(), key="autopilot", expected_outputs=_xds_expected_outputs(work_dir))
    if outcome == "stopped":
        return (-1, True)
    if outcome != "ok":
        send("ap_log", {"text": ">>> ERROR running " + label + ": " + _outcome_message(outcome, label, timeout)})
        return (-1, False)
    return (rc, False)


def _ap_run_xscale(work_dir, xscale_exe, send, timeout=3600):
    """Run XSCALE in work_dir, streaming output. Returns (returncode, was_stopped)."""
    rc, outcome = _run_streaming([str(xscale_exe)], work_dir, lambda t: send("ap_log", {"text": t}),
                                 timeout=timeout, should_stop=lambda: _job_stopped(), key="autopilot", expected_outputs=["XSCALE.LP"])
    if outcome == "stopped":
        return (-1, True)
    if outcome != "ok":
        send("ap_log", {"text": ">>> ERROR running XSCALE: " + _outcome_message(outcome, "XSCALE", timeout)})
        return (-1, False)
    return (rc, False)


def _ap_check_lp(work_dir, step):
    """Check if step.LP exists and whether it contains errors.
    Returns (lp_text_or_None, has_error, error_line).
    """
    lp_path = work_dir / (step + ".LP")
    outcome = _current_output_error(lp_path)
    if not lp_path.exists():
        return (None, True, _outcome_message(outcome, step) if outcome else "No " + step + ".LP generated")
    lp_text = lp_path.read_text(encoding="utf-8", errors="replace")
    if "!!! ERROR !!!" in lp_text or "!!! ERROR IN" in lp_text:
        err_line = None
        for ln in lp_text.split("\n"):
            if "!!! ERROR !!!" in ln or "!!! ERROR IN" in ln:
                err_line = ln.strip()
                break
        return (lp_text, True, err_line)
    if outcome:
        return (lp_text, True, _outcome_message(outcome, step))
    return (lp_text, False, None)


def _ap_build_xscale_inp(work_dir, resolution, friedel, shells=None):
    """Generate XSCALE.INP for autopilot with resolution cutoff and shell binning.

    work_dir: directory containing XDS_ASCII.HKL
    resolution: high-resolution cutoff in Angstroms
    friedel: 'TRUE' or 'FALSE'
    shells: optional list of (d_hi, d_lo) tuples for RESOLUTION_SHELLS

    Format follows XSCALE convention (Kabsch, 2010):
      Global params (SG, cell) first, then OUTPUT_FILE block,
      then INPUT_FILE block with per-dataset INCLUDE_RESOLUTION_RANGE.
    """
    # Read unit cell and SG from XDS_ASCII.HKL header
    sg = ""
    cell = ""
    ascii_hkl = work_dir / "XDS_ASCII.HKL"
    if ascii_hkl.exists():
        try:
            with open(str(ascii_hkl), 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('!SPACE_GROUP_NUMBER='):
                        sg = line.split('=')[1].strip()
                    elif line.startswith('!UNIT_CELL_CONSTANTS='):
                        cell = line.split('=')[1].strip()
                    elif not line.startswith('!'):
                        break
        except Exception:
            pass

    lines = []
    lines.append("! XSCALE.INP generated by CrystalPilot AutoPilot")
    # Global parameters first
    if sg:
        lines.append("SPACE_GROUP_NUMBER= " + sg)
    if cell:
        lines.append("UNIT_CELL_CONSTANTS= " + cell)
    lines.append("")
    # Output file block
    lines.append("OUTPUT_FILE= XSCALE.HKL")
    lines.append("FRIEDEL'S_LAW= " + friedel)
    lines.append("MERGE= FALSE")
    lines.append("")
    # Input file block — INCLUDE_RESOLUTION_RANGE is per-dataset
    lines.append("INPUT_FILE= XDS_ASCII.HKL")
    if resolution and resolution > 0:
        # 999: no low-resolution cut - 50 A drops the lowest shells of any cell longer than 50 A
        lines.append("  INCLUDE_RESOLUTION_RANGE= 999 " + str(round(resolution, 2)))
    lines.append("")

    xscale_inp = work_dir / "XSCALE.INP"
    _write_inp(xscale_inp, "\n".join(lines) + "\n")
    return str(xscale_inp)


def _ap_build_xdsconv_inp(work_dir, resolution, friedel, input_file="XSCALE.HKL"):
    """Generate XDSCONV.INP for autopilot MTZ conversion."""
    lines = []
    lines.append("! XDSCONV.INP generated by CrystalPilot AutoPilot")
    lines.append("INPUT_FILE= " + input_file)
    lines.append("OUTPUT_FILE= temp.hkl  CCP4_F")
    if resolution and resolution > 0:
        lines.append("INCLUDE_RESOLUTION_RANGE= 999 " + str(round(resolution, 2)))
    lines.append("FRIEDEL'S_LAW= " + friedel)
    lines.append("GENERATE_FRACTION_OF_TEST_REFLECTIONS= 0.05")
    lines.append("")

    xdsconv_inp = work_dir / "XDSCONV.INP"
    xdsconv_inp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(xdsconv_inp)


def _ap_generate_xdsinp(project_dir, send, template=None, neggia_lib=''):
    """Auto-generate XDS.INP from diffraction images.

    Uses the same logic as the /generate-xdsinp handler endpoint:
    1. If template provided, use it directly.
    2. Otherwise, scan project_dir for image files (.cbf, .h5, etc.).
    3. Read image header via ImageHeaderReader.
    4. Generate XDS.INP via XDSINPGenerator.
    5. Inject standard geometry defaults if missing.
    6. Write XDS.INP to project_dir.

    Args:
        project_dir: Path to project directory
        send: SSE send callback
        template: optional NAME_TEMPLATE path
        neggia_lib: path to dectris-neggia.so for HDF5 data

    Returns True on success, False on failure.
    """
    import glob as _glob_gen
    import re as _re_gen

    # ── Step 1: Determine template ──────────────────────────────────
    if not template:
        # Scan project dir for image files
        exts = ('.cbf', '.img', '.h5', '.hdf5', '.tif', '.tiff', '.osc', '.mar3450')
        try:
            for f in sorted(project_dir.iterdir()):
                try:
                    if f.suffix.lower() in exts:
                        if f.suffix.lower() in ('.h5', '.hdf5'):
                            if '_master' in f.name:
                                template = str(f)
                                break
                        else:
                            # the frame number is the LAST digit run of the name (lyso_100K_00001.cbf)
                            m = _re_gen.search(r'(\d{3,})(?=\D*$)', f.stem)
                            if m:
                                digits = m.group(1)
                                qmarks = '?' * len(digits)
                                tname = f.stem[:m.start(1)] + qmarks + f.stem[m.end(1):] + f.suffix
                                template = str(project_dir / tname)
                            else:
                                template = str(f)
                            break
                except Exception:
                    continue
        except Exception:
            pass

    if not template:
        send("ap_log", {"text": ">>> No diffraction images found in project directory"})
        return False

    # Sanitize HDF5 templates: XDS NAME_TEMPLATE must never contain
    # _data_ — the neggia plugin resolves ?????? → master internally.
    # A previous (buggy) generation may have written _data_ into XDS.INP.
    if template.lower().endswith(('.h5', '.hdf5')):
        template = _re_gen.sub(r'_data_(\?+)', r'_\1', template)

    send("ap_log", {"text": ">>> Image template: " + template})

    # ── Step 2: Convert concrete path to XDS template ───────────────
    if '?' not in template and '*' not in template:
        p_tmpl = Path(template)
        ext_lo = p_tmpl.suffix.lower()
        if ext_lo in ('.h5', '.hdf5'):
            par = p_tmpl.parent
            stem = p_tmpl.stem
            if '_master' in p_tmpl.name.lower():
                prefix = stem.replace('_master', '').replace('_Master', '').replace('_MASTER', '')
                # XDS NAME_TEMPLATE for Eiger HDF5 is always PREFIX_??????.h5
                # The neggia/bitshuffle plugin resolves ?????? → master file internally.
                # Never use _data_ in the template — that refers to chunk files
                # which XDS cannot open directly.
                _found_tmpl = False
                for ndigits in (6, 5, 4, 8, 3):
                    qmarks = '?' * ndigits
                    cand = str(par / (prefix + '_' + qmarks + p_tmpl.suffix))
                    pattern = cand.replace('?', '[0-9]')
                    if _glob_gen.glob(pattern):
                        template = cand
                        _found_tmpl = True
                        break
                if not _found_tmpl:
                    # Default: 6-digit wildcard (standard Eiger convention)
                    template = str(par / (prefix + '_??????' + p_tmpl.suffix))
            else:
                m = _re_gen.search(r'_(\d+)$', stem)
                if m:
                    prefix = stem[:m.start()]
                    # PREFIX_data_000001.h5 → PREFIX_??????.h5: the XDS template
                    # must never contain _data_, neggia maps ?????? → _master.
                    prefix = _re_gen.sub(r'_data$', '', prefix, flags=_re_gen.IGNORECASE)
                    ndigits = len(m.group(1))
                    qmarks = '?' * ndigits
                    template = str(par / (prefix + '_' + qmarks + p_tmpl.suffix))
        else:
            stem = p_tmpl.stem
            ext = p_tmpl.suffix
            par = p_tmpl.parent
            m = _re_gen.search(r'(\d+)\s*$', stem)
            if m:
                qmarks = '?' * len(m.group(1))
                tname = stem[:m.start(1)] + qmarks + stem[m.end(1):] + ext
                template = str(par / tname)

    # ── Step 3: Find first file for header reading ──────────────────
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
        send("ap_log", {"text": ">>> Could not find image file from template: " + template})
        return False

    send("ap_log", {"text": ">>> Reading header from: " + str(first_file)})

    # ── Step 4: Read header ─────────────────────────────────────────
    try:
        header = ImageHeaderReader.read(first_file)
    except Exception as e:
        send("ap_log", {"text": ">>> Failed to read image header: " + str(e)})
        send("ap_log", {"text": ">>> Ensure fabio, h5py, and hdf5plugin are installed"})
        return False

    if '_error' in header and not any(k in header for k in ('wavelength', 'detector_distance')):
        send("ap_log", {"text": ">>> Image header unreadable: " + header.get('_error', 'unknown error')})
        return False

    # Count frames from filesystem for frame-per-file formats
    if '?' in template:
        pattern = template.replace('?', '[0-9]')
        nfiles = len(_glob_gen.glob(pattern))
        if nfiles > 0:
            ext_lo = Path(template).suffix.lower()
            if ext_lo not in ('.h5', '.hdf5') or 'nframes' not in header:
                header['nframes'] = str(nfiles)
                numbers = XDSINPGenerator.frame_numbers(template)
                if numbers:
                    header['first_frame'], header['last_frame'] = numbers[0], numbers[1]

    # ── Step 5: Generate XDS.INP ────────────────────────────────────
    try:
        content, warnings = XDSINPGenerator.generate(template, header, lib_path=neggia_lib)
    except Exception as e:
        send("ap_log", {"text": ">>> XDS.INP generation failed: " + str(e)})
        return False

    # ── Step 6: Inject standard geometry defaults if missing ────────
    geom_defaults = [
        ('DIRECTION_OF_DETECTOR_X-AXIS=', ' 1.0 0.0 0.0'),
        ('DIRECTION_OF_DETECTOR_Y-AXIS=', ' 0.0 1.0 0.0'),
        ('ROTATION_AXIS=', ' 1.0 0.0 0.0'),
        ('INCIDENT_BEAM_DIRECTION=', ' 0.0 0.0 1.0'),
        ('FRACTION_OF_POLARIZATION=', ' 0.99'),
        ('POLARIZATION_PLANE_NORMAL=', ' 0.0 1.0 0.0'),
    ]
    geom_added = []
    for gkey, gval in geom_defaults:
        if gkey not in content:
            content += '\n' + gkey + gval
            geom_added.append(gkey.replace('=', ''))
    if geom_added:
        send("ap_log", {"text": ">>> Added standard geometry defaults: " + ", ".join(geom_added)})

    # ── Step 7: Write XDS.INP ───────────────────────────────────────
    xds_inp_path = project_dir / "XDS.INP"
    _write_inp(xds_inp_path, content)

    for w in warnings:
        send("ap_log", {"text": ">>> Warning: " + w})

    send("ap_log", {"text": ">>> XDS.INP generated and saved (" + str(len(content.splitlines())) + " lines)"})
    return True


@_processing_job("autopilot")
def stream_autopilot(project_name, write_fn, criterion='isig2', friedel='FALSE', template=None, optimize=True, dcc_half=True, neggia_lib='',
                     autoindex_tier='medium', exclude_ice=True, space_group=None, unit_cell=None,
                     resolution_range=None, optimize_metric='isa', sg_from_absences=True):
    """AutoPilot: fully automated XDS processing pipeline with error recovery.

    Streams progress via SSE write_fn.

    Phases:
      1. PROCESS   — Run full XDS pipeline (XYCORR..CORRECT)
      2. DIAGNOSE  — Parse LP files, apply fixes, retry if needed
      3. AUTOINDEX — Fallback if IDXREF fails after retries
      4. ANALYZE   — Parse CORRECT.LP, determine resolution cutoff
      5. OPTIMIZE  — Re-integrate with CORRECT-refined geometry (GXPARM→XPARM)
                     + optional ΔCC½ frame rejection via XDSCC12
      6. XSCALE    — Build XSCALE.INP with cutoff, run XSCALE
      7. CONVERT   — XDSCONV + f2mtz (if CCP4 available) or gemmi
      8. DONE      — Present summary

    Args:
        project_name: name of the project
        write_fn: SSE write function
        criterion: resolution cutoff criterion ('isig2', 'cc_half_50', 'r_obs_55', 'cc_half_sig')
        friedel: 'TRUE' or 'FALSE' for FRIEDEL'S_LAW in XSCALE/XDSCONV
        template: optional NAME_TEMPLATE_OF_DATA_FRAMES path for XDS.INP generation
        optimize: if True, re-integrate with CORRECT-refined geometry (GXPARM→XPARM)
        dcc_half: if True, run XDSCC12 ΔCC½ analysis during OPTIMIZE (requires XDSCC12)
        neggia_lib: path to dectris-neggia.so for HDF5 data (injected as LIB= in XDS.INP)
    """
    global XDSCC12_BIN

    project_dir = _pdir(project_name)
    for output_kind in ("xds", "xscale", "xdsconv"):
        _record_run_folder(project_name, project_dir, output_kind)

    xds_exe = _find_xds_exe(xds_runner.xds_path)
    xscale_exe = _find_xscale_exe(xds_runner.xds_path)

    def send(event, data):
        write_fn("event: " + event + "\ndata: " + json.dumps(data) + "\n\n")

    # ── Validate prerequisites ─────────────────────────────────────────────
    xds_inp_path = project_dir / "XDS.INP"
    if not xds_inp_path.exists():
        send("ap_log", {"text": ">>> XDS.INP not found — attempting auto-generation from images..."})
        generated = _ap_generate_xdsinp(project_dir, send, template=template, neggia_lib=neggia_lib)
        if not generated:
            send("ap_error", {"message": "XDS.INP could not be generated. "
                 "Provide a NAME_TEMPLATE_OF_DATA_FRAMES path or place images in the project directory."})
            send("ap_done", {"status": "error"})
            return
    if not xds_exe.exists():
        send("ap_error", {"message": "XDS executable not found (tried xds_par, xds) at " + str(xds_runner.xds_path)})
        send("ap_done", {"status": "error"})
        return

    # ── Ensure LIB= is present for HDF5 data ──────────────────────────────
    # If neggia_lib is set and XDS.INP references .h5 data but has no LIB=
    # line, inject it now so XDS can read the frames.
    if neggia_lib and xds_inp_path.exists():
        try:
            _inp_text = xds_inp_path.read_text(encoding='utf-8', errors='replace')
            _has_lib = any(
                ln.strip().upper().startswith('LIB=') or ln.strip().upper().startswith('LIB =')
                for ln in _inp_text.splitlines()
                if not ln.strip().startswith('!')
            )
            _has_h5 = False
            for ln in _inp_text.splitlines():
                ls = ln.strip()
                if ls.startswith('!'):
                    continue
                if 'NAME_TEMPLATE_OF_DATA_FRAMES' in ls.upper() and '=' in ls:
                    tval = ls.split('=', 1)[1].strip().lower()
                    if tval.endswith('.h5') or tval.endswith('.hdf5'):
                        _has_h5 = True
                    break
            if _has_h5 and not _has_lib:
                # Insert LIB= right after NAME_TEMPLATE_OF_DATA_FRAMES line
                new_lines = []
                for ln in _inp_text.splitlines():
                    new_lines.append(ln)
                    ls = ln.strip()
                    if not ls.startswith('!') and 'NAME_TEMPLATE_OF_DATA_FRAMES' in ls.upper() and '=' in ls:
                        new_lines.append('LIB= ' + neggia_lib)
                xds_inp_path.write_text('\n'.join(new_lines), encoding='utf-8')
                send("ap_log", {"text": ">>> Injected LIB= " + neggia_lib + " for HDF5 data"})
        except Exception:
            pass  # Non-fatal — user can add LIB= manually

    # ── Strategy: what the user decided once for every data set ─────────
    # A known space group and cell keep a whole campaign in one setting,
    # which merging needs; limits apply before anything is integrated.
    strategy_fix = {}
    if space_group:
        strategy_fix['SPACE_GROUP_NUMBER'] = str(space_group).strip()
        if unit_cell:
            strategy_fix['UNIT_CELL_CONSTANTS'] = ' '.join(str(unit_cell).replace(',', ' ').split())
    if resolution_range:
        try:
            low, high = float(resolution_range[0]), float(resolution_range[1])
            strategy_fix['INCLUDE_RESOLUTION_RANGE'] = '%g %g' % (max(low, high), min(low, high))
        except (TypeError, ValueError, IndexError):
            send("ap_log", {"text": ">>> Resolution limits ignored: " + str(resolution_range)})
    if strategy_fix and _ap_apply_xdsinp_fix(xds_inp_path, dict(strategy_fix), send):
        send("ap_log", {"text": ">>> Strategy applied to XDS.INP: " + ', '.join(k + '= ' + v for k, v in strategy_fix.items())})

    # Preflight: HDF5 frames reachable?  (same check as the manual run)
    try:
        _h5_fatal, _h5_lines = _check_h5_frames(xds_inp_path)
    except Exception:
        _h5_fatal, _h5_lines = False, []
    if _h5_lines:
        send("ap_log", {"text": ""})
        send("ap_log", {"text": ">>> " + ("XDS cannot read the images:" if _h5_fatal else "WARNING:")})
        for _ln in _h5_lines:
            send("ap_log", {"text": ">>>   " + _ln})
        if _h5_fatal:
            send("ap_error", {"message": _h5_lines[0]})
            send("ap_done", {"status": "error"})
            return

    max_retries = AUTOPILOT_MAX_RETRIES

    send("ap_log", {"text": ""})
    send("ap_log", {"text": "============================================"})
    send("ap_log", {"text": "  CrystalPilot AutoPilot v1.0"})
    send("ap_log", {"text": "  Cutoff criterion: " + criterion})
    send("ap_log", {"text": "  FRIEDEL'S_LAW: " + friedel})
    send("ap_log", {"text": "============================================"})
    send("ap_log", {"text": ""})

    summary = {
        'status': 'running',
        'phases_completed': [],
        'retries': 0,
        'errors_fixed': [],
        'resolution': None,
        'space_group': None,
        'unit_cell': None,
        'mtz_file': None,
        'criterion': criterion,
        'friedel': friedel,
        'strategy': {'autoindex_tier': autoindex_tier, 'exclude_ice': bool(exclude_ice),
                     'space_group': space_group, 'unit_cell': unit_cell,
                     'resolution_range': list(resolution_range) if resolution_range else None,
                     'optimize': optimize, 'optimize_metric': optimize_metric, 'dcc_half': bool(dcc_half)},
    }

    # Track DELPHI escalation state across retries
    delphi_step_idx = 0  # index into escalation list [10, 20, 45, 90]
    delphi_escalation = [10, 20, 45, 90]

    # ══════════════════════════════════════════════════════════════════════
    #  PHASE 1: Full XDS pipeline
    # ══════════════════════════════════════════════════════════════════════
    send("ap_phase", {"phase": "PROCESS", "message": "Running XDS pipeline..."})

    # Set JOB to full pipeline
    ProjectManager.invalidate_steps(project_name, XDS_PIPELINE[0])
    previous_results = project_dir / "AUTOPILOT_RESULTS.json"
    if previous_results.is_file():
        os.replace(str(previous_results), str(previous_results) + ".previous_attempt")
    full_pipeline = "XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT"
    _ap_set_job(xds_inp_path, full_pipeline)

    rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="XDS full pipeline")
    if stopped:
        send("ap_log", {"text": ">>> AutoPilot stopped by user"})
        summary['status'] = 'stopped'
        send("ap_done", {"status": "stopped", "summary": summary})
        return

    # ── Early bail-out: if XDS failed before producing any LP file,
    #    it likely cannot read the images at all (missing LIB=, wrong
    #    template, corrupt files, etc.).  No point retrying.
    if rc != 0:
        _earliest_lps = ['XYCORR.LP', 'INIT.LP', 'COLSPOT.LP']
        _any_lp = any((project_dir / lp).exists() for lp in _earliest_lps)
        if not _any_lp:
            # Check XDS output for common error patterns
            _xds_err_msg = "XDS failed before producing any output."
            for _lp_cand in ['LP_01.tmp', 'LogFile.tmp']:
                _lp_tmp = project_dir / _lp_cand
                if _lp_tmp.exists():
                    _tmp_text = _lp_tmp.read_text(encoding='utf-8', errors='replace')[:2000]
                    if 'CANNOT OPEN OR READ' in _tmp_text.upper():
                        _xds_err_msg = ("XDS cannot read the image files. This usually means:\n"
                                        "  • For HDF5: the _data_00000N.h5 files are not next to the master file\n"
                                        "    (the plugin looks there and nowhere else; XDS then blames the library)\n"
                                        "  • NAME_TEMPLATE_OF_DATA_FRAMES does not match actual files\n"
                                        "  • LIB= path is missing or incorrect (required for HDF5/Eiger data)\n"
                                        "Check the AutoPilot log above for the exact XDS error.")
                        break
                    elif 'ERROR' in _tmp_text.upper():
                        # Extract first error line
                        for _eline in _tmp_text.splitlines():
                            if 'ERROR' in _eline.upper() or '!!!' in _eline:
                                _xds_err_msg = "XDS error: " + _eline.strip()
                                break
                        break
            send("ap_log", {"text": ""})
            send("ap_log", {"text": ">>> FATAL: " + _xds_err_msg})
            send("ap_error", {"message": _xds_err_msg})
            summary['status'] = 'failed'
            try:
                _res_path = _pout(project_dir, "AUTOPILOT_RESULTS.json")
                _res_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
            except Exception:
                pass
            send("ap_done", {"status": "error", "summary": summary})
            return

    # ══════════════════════════════════════════════════════════════════════
    #  PHASE 2: Diagnose & Retry
    # ══════════════════════════════════════════════════════════════════════
    send("ap_phase", {"phase": "DIAGNOSE", "message": "Checking results..."})
    summary['phases_completed'].append('PROCESS')

    # Check each step in reverse order of importance: CORRECT > INTEGRATE > IDXREF
    idxref_ok = False
    integrate_ok = False
    correct_ok = False

    # ── Check IDXREF ──────────────────────────────────────────────────────
    idxref_lp, idxref_err, idxref_errline = _ap_check_lp(project_dir, "IDXREF")
    if idxref_lp and not idxref_err:
        send("ap_log", {"text": ">>> IDXREF: no fatal errors"})
        # Still run diagnosis to check quality even without errors
        diags = LPParser.diagnose_idxref(idxref_lp)
        has_quality_issues = False
        for diag in diags:
            if diag['severity'] != 'info':
                has_quality_issues = True
                send("ap_log", {"text": "  Quality check: " + diag['message']})
        if not has_quality_issues:
            idxref_ok = True
            send("ap_log", {"text": ">>> IDXREF: OK"})
        else:
            # Non-fatal quality issues found — still continue but log
            idxref_ok = True
            send("ap_log", {"text": ">>> IDXREF: proceeding with warnings"})
    elif idxref_lp and idxref_err:
        send("ap_log", {"text": ">>> IDXREF: ERROR - " + str(idxref_errline)})

        # Diagnose and retry IDXREF
        diags = LPParser.diagnose_idxref(idxref_lp)
        retry_count = 0

        for diag in diags:
            send("ap_log", {"text": "  Diagnosis: " + diag['message']})
            summary['errors_fixed'].append(diag['error'])

            if diag['strategy'] == 'skip_to_integrate':
                # Moderate indexing — just skip ahead
                send("ap_log", {"text": "  Strategy: continuing with DEFPIX INTEGRATE CORRECT"})
                _ap_set_job(xds_inp_path, "DEFPIX INTEGRATE CORRECT")
                rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="XDS (skip to integrate)")
                if stopped:
                    summary['status'] = 'stopped'
                    send("ap_done", {"status": "stopped", "summary": summary})
                    return
                idxref_ok = True  # we're proceeding despite IDXREF warning
                break

            elif diag['strategy'] == 'retry_idxref' and retry_count < max_retries:
                send("ap_log", {"text": "  Strategy: applying fix and retrying IDXREF"})
                if _ap_apply_xdsinp_fix(xds_inp_path, dict(diag['fix']), send):
                    _ap_set_job(xds_inp_path, "IDXREF")
                    rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="IDXREF retry")
                    if stopped:
                        summary['status'] = 'stopped'
                        send("ap_done", {"status": "stopped", "summary": summary})
                        return
                    summary['retries'] += 1
                    retry_count += 1

                    # Re-check
                    idxref_lp2, idxref_err2, _ = _ap_check_lp(project_dir, "IDXREF")
                    if idxref_lp2 and not idxref_err2:
                        idxref_ok = True
                        send("ap_log", {"text": "  >>> IDXREF retry: SUCCESS"})
                        # Continue with remaining steps
                        _ap_set_job(xds_inp_path, "DEFPIX INTEGRATE CORRECT")
                        rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="XDS (after IDXREF fix)")
                        if stopped:
                            summary['status'] = 'stopped'
                            send("ap_done", {"status": "stopped", "summary": summary})
                            return
                        break

            elif diag['strategy'] == 'autoindex':
                send("ap_log", {"text": "  Strategy: falling back to auto-indexing"})
                # Will handle below
                break

        # If IDXREF still not OK and autoindex is warranted
        if not idxref_ok and autoindex_tier == 'off':
            send("ap_log", {"text": ">>> Indexing failed, and the strategy says not to try auto-indexing."})
            summary['status'] = 'failed'
            summary['failure_reason'] = 'IDXREF failed (auto-indexing switched off by the strategy)'
            send("ap_done", {"status": "failed", "summary": summary})
            return
        if not idxref_ok:
            send("ap_phase", {"phase": "AUTOINDEX", "message": "Running auto-indexing..."})
            send("ap_log", {"text": ">>> Falling back to CrystalPilot auto-indexing (" + str(autoindex_tier) + " tier"
                                  + (", keeping the strategy's space group and cell" if space_group else "") + ")"})

            # Use the existing stream_autoindex with a capture function
            autoindex_results = []

            def _ai_capture(text):
                """Capture autoindex SSE output and forward to autopilot stream."""
                # Forward to autopilot log
                try:
                    # Parse the SSE text to extract event and data
                    for chunk in text.split("\n\n"):
                        if not chunk.strip():
                            continue
                        event_line = ""
                        data_line = ""
                        for ln in chunk.split("\n"):
                            if ln.startswith("event:"):
                                event_line = ln[6:].strip()
                            elif ln.startswith("data:"):
                                data_line = ln[5:].strip()
                        if event_line == "ai_log" and data_line:
                            try:
                                d = json.loads(data_line)
                                send("ap_log", {"text": "[AI] " + d.get('text', '')})
                            except Exception:
                                pass
                        elif event_line == "ai_result" and data_line:
                            try:
                                autoindex_results.append(json.loads(data_line))
                            except Exception:
                                pass
                        elif event_line == "ai_done" and data_line:
                            try:
                                d = json.loads(data_line)
                                if d.get('top5'):
                                    autoindex_results.extend(d['top5'])
                            except Exception:
                                pass
                except Exception:
                    pass

            # an imposed space group and cell must survive the trials
            stream_autoindex(project_name, autoindex_tier, _ai_capture, force_cell=bool(space_group))

            # Auto-indexing only reports its trials; apply the best successful one
            # to XDS.INP and run COLSPOT + IDXREF with it in the project.
            best_trial = _ap_best_autoindex_trial(project_dir)
            if best_trial is None:
                send("ap_log", {"text": ">>> Auto-indexing found no trial that indexed"})
                idxref_lp3, idxref_err3 = None, True
            else:
                send("ap_log", {"text": ">>> Applying the best auto-indexing trial: " + str(best_trial.get('label', ''))
                                      + " (" + str(round(float(best_trial.get('indexed_fraction') or 0) * 100, 1)) + "% indexed)"})
                xds_inp_path.write_text(XDSINPEditor.apply_params(_read_text_lenient(xds_inp_path), _ap_autoindex_params(best_trial)),
                                        encoding="utf-8")
                _ap_set_job(xds_inp_path, "COLSPOT IDXREF")
                rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="COLSPOT IDXREF (best auto-indexing trial)")
                if stopped:
                    summary['status'] = 'stopped'
                    send("ap_done", {"status": "stopped", "summary": summary})
                    return
                idxref_lp3, idxref_err3, _ = _ap_check_lp(project_dir, "IDXREF")
            if idxref_lp3 and not idxref_err3:
                idxref_ok = True
                send("ap_log", {"text": ">>> Auto-indexing: SUCCESS"})
                # Run remaining pipeline
                _ap_set_job(xds_inp_path, "DEFPIX INTEGRATE CORRECT")
                rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="XDS (after autoindex)")
                if stopped:
                    summary['status'] = 'stopped'
                    send("ap_done", {"status": "stopped", "summary": summary})
                    return
            else:
                send("ap_log", {"text": ">>> Auto-indexing: FAILED"})
                send("ap_log", {"text": ">>> AutoPilot cannot proceed without successful indexing."})
                summary['status'] = 'failed'
                summary['failure_reason'] = 'IDXREF failed after auto-indexing'
                send("ap_done", {"status": "failed", "summary": summary})
                return

            summary['phases_completed'].append('AUTOINDEX')
    else:
        # No IDXREF.LP at all — something very wrong
        send("ap_log", {"text": ">>> IDXREF.LP not found — check XDS.INP and data files"})
        summary['status'] = 'failed'
        summary['failure_reason'] = 'IDXREF.LP not generated'
        send("ap_done", {"status": "failed", "summary": summary})
        return

    if _job_stopped():
        summary['status'] = 'stopped'
        send("ap_done", {"status": "stopped", "summary": summary})
        return

    # ── Check INTEGRATE ───────────────────────────────────────────────────
    int_lp, int_err, int_errline = _ap_check_lp(project_dir, "INTEGRATE")
    if int_lp and not int_err:
        send("ap_log", {"text": ">>> INTEGRATE: no fatal errors"})
        # Still run diagnosis to check quality even without errors
        diags = LPParser.diagnose_integrate(int_lp)
        has_int_issues = False
        for diag in diags:
            if diag['severity'] != 'info':
                has_int_issues = True
                send("ap_log", {"text": "  Quality check: " + diag['message']})
        if not has_int_issues:
            integrate_ok = True
            send("ap_log", {"text": ">>> INTEGRATE: OK"})
        else:
            integrate_ok = True
            send("ap_log", {"text": ">>> INTEGRATE: proceeding with warnings"})
    elif int_lp and int_err:
        send("ap_log", {"text": ">>> INTEGRATE: ERROR - " + str(int_errline)})

        diags = LPParser.diagnose_integrate(int_lp)
        retry_count = 0

        for diag in diags:
            send("ap_log", {"text": "  Diagnosis: " + diag['message']})
            summary['errors_fixed'].append(diag['error'])

            if diag['strategy'] == 'retry_integrate' and retry_count < max_retries:
                # Handle DELPHI escalation
                fix = dict(diag['fix'])
                escalation = diag.get('_delphi_escalation')
                if escalation and 'DELPHI' in fix:
                    if delphi_step_idx < len(escalation):
                        fix['DELPHI'] = str(escalation[delphi_step_idx])
                        delphi_step_idx += 1
                    elif delphi_step_idx < len(delphi_escalation):
                        fix['DELPHI'] = str(delphi_escalation[delphi_step_idx])
                        delphi_step_idx += 1

                send("ap_log", {"text": "  Strategy: applying fix and retrying INTEGRATE"})
                if _ap_apply_xdsinp_fix(xds_inp_path, fix, send):
                    _ap_set_job(xds_inp_path, "DEFPIX INTEGRATE CORRECT")
                    rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="INTEGRATE retry")
                    if stopped:
                        summary['status'] = 'stopped'
                        send("ap_done", {"status": "stopped", "summary": summary})
                        return
                    summary['retries'] += 1
                    retry_count += 1

                    # Re-check
                    int_lp2, int_err2, _ = _ap_check_lp(project_dir, "INTEGRATE")
                    if int_lp2 and not int_err2:
                        integrate_ok = True
                        send("ap_log", {"text": "  >>> INTEGRATE retry: SUCCESS"})
                        break

        if not integrate_ok:
            # Last resort: try DELPHI escalation if not yet exhausted
            while delphi_step_idx < len(delphi_escalation) and retry_count < max_retries:
                val = delphi_escalation[delphi_step_idx]
                if val > AUTOPILOT_MAX_DELPHI:
                    break
                delphi_step_idx += 1
                retry_count += 1
                send("ap_log", {"text": "  Escalating DELPHI to " + str(val)})
                _ap_apply_xdsinp_fix(xds_inp_path, {'DELPHI': str(val)}, send)
                _ap_set_job(xds_inp_path, "DEFPIX INTEGRATE CORRECT")
                rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="INTEGRATE retry")
                if stopped:
                    summary['status'] = 'stopped'
                    send("ap_done", {"status": "stopped", "summary": summary})
                    return
                summary['retries'] += 1

                int_lp3, int_err3, _ = _ap_check_lp(project_dir, "INTEGRATE")
                if int_lp3 and not int_err3:
                    integrate_ok = True
                    send("ap_log", {"text": "  >>> INTEGRATE retry: SUCCESS"})
                    break

        if not integrate_ok:
            send("ap_log", {"text": ">>> INTEGRATE failed after all retries"})
            summary['status'] = 'failed'
            summary['failure_reason'] = 'INTEGRATE failed after retries'
            send("ap_done", {"status": "failed", "summary": summary})
            return
    else:
        send("ap_log", {"text": ">>> INTEGRATE.LP not found"})
        summary['status'] = 'failed'
        summary['failure_reason'] = 'INTEGRATE.LP not generated'
        send("ap_done", {"status": "failed", "summary": summary})
        return

    summary['phases_completed'].append('DIAGNOSE')

    if _job_stopped():
        summary['status'] = 'stopped'
        send("ap_done", {"status": "stopped", "summary": summary})
        return

    # ── Check CORRECT ─────────────────────────────────────────────────────
    cor_lp, cor_err, cor_errline = _ap_check_lp(project_dir, "CORRECT")
    if cor_lp and not cor_err:
        send("ap_log", {"text": ">>> CORRECT: no fatal errors"})
        # Run diagnosis to detect quality issues (e.g. low ISa without error string)
        cor_diags_early = LPParser.diagnose_correct(cor_lp)
        for diag in cor_diags_early:
            if diag['severity'] != 'info':
                send("ap_log", {"text": "  Quality check: " + diag['message']})
        correct_ok = True
        send("ap_log", {"text": ">>> CORRECT: OK"})
    elif cor_lp and cor_err:
        send("ap_log", {"text": ">>> CORRECT: ERROR - " + str(cor_errline)})
        # CORRECT errors are rare; usually means something fundamental is wrong
        send("ap_log", {"text": ">>> CORRECT failed — cannot continue"})
        summary['status'] = 'failed'
        summary['failure_reason'] = 'CORRECT failed: ' + str(cor_errline)
        send("ap_done", {"status": "failed", "summary": summary})
        return
    else:
        send("ap_log", {"text": ">>> CORRECT.LP not found"})
        summary['status'] = 'failed'
        summary['failure_reason'] = 'CORRECT.LP not generated'
        send("ap_done", {"status": "failed", "summary": summary})
        return

    # ══════════════════════════════════════════════════════════════════════
    #  PHASE 3: Analyze CORRECT results — ice rings, resolution cutoff
    # ══════════════════════════════════════════════════════════════════════
    send("ap_phase", {"phase": "ANALYZE", "message": "Analyzing data quality..."})

    correct_data = LPParser.parse_correct(cor_lp)
    stats_table = correct_data.get('statistics_table', [])

    # Extract space group and cell
    sg = correct_data.get('space_group')
    uc = correct_data.get('unit_cell')
    if sg:
        summary['space_group'] = sg
    if uc:
        summary['unit_cell'] = uc

    send("ap_log", {"text": ">>> Space group: " + str(sg or 'unknown')})
    if uc:
        send("ap_log", {"text": ">>> Unit cell: " +
             " ".join(str(round(v, 2)) for v in [uc['a'], uc['b'], uc['c'], uc['alpha'], uc['beta'], uc['gamma']])})

    # Check for ice rings and fix
    cor_diags = LPParser.diagnose_correct(cor_lp, stats_table)
    ice_fix_applied = False
    for diag in cor_diags:
        send("ap_log", {"text": "  Diagnosis: " + diag['message']})
        summary['errors_fixed'].append(diag['error'])

        # retry_correct is the ice-ring exclusion; the strategy may leave ice alone
        if diag['strategy'] == 'retry_correct' and diag.get('fix') and exclude_ice:
            send("ap_log", {"text": "  Strategy: applying exclusion ranges and re-running CORRECT"})
            if _ap_apply_xdsinp_fix(xds_inp_path, dict(diag['fix']), send):
                _ap_set_job(xds_inp_path, "CORRECT")
                rc, stopped = _ap_run_xds(project_dir, xds_exe, send, label="CORRECT (ice fix)")
                if stopped:
                    summary['status'] = 'stopped'
                    send("ap_done", {"status": "stopped", "summary": summary})
                    return
                summary['retries'] += 1
                ice_fix_applied = True

                # Re-parse CORRECT results
                cor_lp2, _, _ = _ap_check_lp(project_dir, "CORRECT")
                if cor_lp2:
                    correct_data = LPParser.parse_correct(cor_lp2)
                    stats_table = correct_data.get('statistics_table', [])

    # Screw axes: XDS's space group never has them (C222 for C222₁); the axial
    # reflections in CORRECT.LP decide, and CORRECT runs again in that group.
    if sg_from_absences and not space_group:
        sg_data, sg_note, stopped = _ap_sg_from_absences(project_dir, xds_inp_path, xds_exe, correct_data, send)
        if stopped:
            summary['status'] = 'stopped'
            send("ap_done", {"status": "stopped", "summary": summary})
            return
        if sg_data:
            correct_data = sg_data
            stats_table = correct_data.get('statistics_table', [])
            summary['retries'] += 1
            sg = summary['space_group'] = correct_data.get('space_group') or sg
            uc = correct_data.get('unit_cell') or uc
            if uc:
                summary['unit_cell'] = uc
            summary['sg_note'] = sg_note

    # Determine resolution cutoff
    cutoff_result = LPParser.determine_resolution_cutoff(stats_table, criterion)
    resolution = cutoff_result.get('resolution')
    summary['resolution'] = resolution
    summary['all_cutoffs'] = cutoff_result.get('all_cutoffs', {})

    send("ap_log", {"text": ""})
    send("ap_log", {"text": ">>> Resolution cutoffs:"})
    for crit_name, crit_val in cutoff_result.get('all_cutoffs', {}).items():
        marker = " <-- selected" if crit_name == criterion else ""
        send("ap_log", {"text": "    " + crit_name + ": " + (str(crit_val) + " A" if crit_val else "N/A") + marker})

    if resolution:
        send("ap_log", {"text": ">>> Selected resolution cutoff: " + str(round(resolution, 2)) + " A (" + criterion + ")"})
    else:
        send("ap_log", {"text": ">>> Could not determine resolution cutoff — using all data"})

    # ISa quality indicator
    isa = correct_data.get('isa')
    isa_val = None
    if isa:
        try:
            isa_val = float(isa.get('isa', 0))
        except (ValueError, TypeError):
            isa_val = None
        send("ap_log", {"text": ">>> ISa = " + str(isa.get('isa', '?'))})
        if isa_val is not None and isa_val < 3.0:
            send("ap_log", {"text": ""})
            send("ap_log", {"text": ">>> FAILED: ISa = " + str(round(isa_val, 2)) + " is critically low (< 3.0)"})
            send("ap_log", {"text": ">>>   This indicates the data is not usable:"})
            send("ap_log", {"text": ">>>   - Wrong unit cell or space group"})
            send("ap_log", {"text": ">>>   - Failed indexing (wrong lattice, twinning)"})
            send("ap_log", {"text": ">>>   - Severe radiation damage or ice"})
            send("ap_log", {"text": ">>>   - Detector / geometry problems"})
            send("ap_log", {"text": ">>>   Aborting — the resulting data would be unusable."})
            send("ap_log", {"text": ">>>   Try: check XDS.INP parameters, re-index manually,"})
            send("ap_log", {"text": ">>>   verify ROTATION_AXIS and detector geometry."})
            summary['status'] = 'failed'
            summary['failure_reason'] = 'ISa=' + str(round(isa_val, 2)) + ' critically low — data quality insufficient'
            summary['phases_completed'].append('ANALYZE')
            send("ap_result", {"type": "analysis", "data": {
                "resolution": resolution,
                "all_cutoffs": cutoff_result.get('all_cutoffs', {}),
                "space_group": sg,
                "unit_cell": uc,
                "isa": isa,
                "ice_rings_fixed": ice_fix_applied,
            }})
            send("ap_done", {"status": "failed", "summary": summary})
            return

    # Verify XDS_ASCII.HKL was produced by THIS run (not stale from a previous run)
    ascii_hkl = _pfile(project_dir, "XDS_ASCII.HKL")
    correct_lp_path = _pfile(project_dir, "CORRECT.LP")
    ascii_stale = False
    if ascii_hkl.exists() and correct_lp_path.exists():
        try:
            # XDS_ASCII.HKL must be newer than or same age as CORRECT.LP
            # (CORRECT produces XDS_ASCII.HKL as its output)
            ascii_mtime = ascii_hkl.stat().st_mtime
            correct_mtime = correct_lp_path.stat().st_mtime
            if ascii_mtime < correct_mtime - 2:  # 2s tolerance
                ascii_stale = True
                send("ap_log", {"text": ">>> WARNING: XDS_ASCII.HKL is older than CORRECT.LP — likely from a previous run"})
        except Exception:
            pass
    elif not ascii_hkl.exists():
        send("ap_log", {"text": ">>> WARNING: XDS_ASCII.HKL not found — CORRECT may have failed silently"})

    summary['phases_completed'].append('ANALYZE')
    send("ap_result", {"type": "analysis", "data": {
        "resolution": resolution,
        "all_cutoffs": cutoff_result.get('all_cutoffs', {}),
        "space_group": sg,
        "unit_cell": uc,
        "isa": isa,
        "ice_rings_fixed": ice_fix_applied,
    }})

    if _job_stopped():
        summary['status'] = 'stopped'
        send("ap_done", {"status": "stopped", "summary": summary})
        return

    # ══════════════════════════════════════════════════════════════════════
    #  PHASE 3.5: OPTIMIZE — re-integrate with CORRECT-refined geometry
    # ══════════════════════════════════════════════════════════════════════
    if optimize:
        send("ap_phase", {"phase": "OPTIMIZE", "message": "Optimizing with refined geometry..."})

        # ── Save pre-optimization metrics for comparison ─────────────
        pre_opt = {'isa': isa_val, 'resolution': resolution}
        pre_total = None
        for _row in stats_table:
            if str(_row.get('resolution', '')).lower() == 'total':
                pre_total = _row
                break
        if pre_total:
            pre_opt['r_meas'] = pre_total.get('r_meas', '')
            pre_opt['completeness'] = pre_total.get('completeness', '')
            pre_opt['i_sigma'] = pre_total.get('i_sigma', '')
            pre_opt['cc_half'] = pre_total.get('cc_half', '')

        # ── Keep the first integration within reach ─────────────────────
        # Always, not only for 'if_better': a re-integration that FAILS has
        # already overwritten XPARM.XDS and INTEGRATE.HKL, and without the copy
        # the project would be left with files from two different runs.
        pre_optimize_dir = _ap_snapshot_integration(project_dir, send)

        # ── Step 1: GXPARM.XDS → XPARM.XDS ──────────────────────────
        gxparm = _pfile(project_dir, "GXPARM.XDS")
        xparm = _pout(project_dir, "XPARM.XDS")
        if gxparm.exists():
            import shutil
            shutil.copy2(str(gxparm), str(xparm))
            send("ap_log", {"text": ">>> Copied GXPARM.XDS → XPARM.XDS (refined geometry from CORRECT)"})
        else:
            send("ap_log", {"text": ">>> GXPARM.XDS not found — skipping optimization"})
            summary['phases_completed'].append('OPTIMIZE_SKIPPED')
            # Fall through to XSCALE with existing data
            optimize = False

        if optimize and not _job_stopped():
            # ── Step 2: Re-INTEGRATE + re-CORRECT ────────────────────
            send("ap_log", {"text": ">>> Re-integrating with refined geometry..."})
            _ap_set_job(xds_inp_path, "DEFPIX INTEGRATE CORRECT")
            rc, stopped = _ap_run_xds(project_dir, xds_exe, send,
                                      label="Re-integration (refined geometry)")
            if stopped:
                summary['status'] = 'stopped'
                send("ap_done", {"status": "stopped", "summary": summary})
                return

            # Verify the re-run succeeded
            int_lp_opt, int_err_opt, _ = _ap_check_lp(project_dir, "INTEGRATE")
            cor_lp_opt, cor_err_opt, _ = _ap_check_lp(project_dir, "CORRECT")

            if cor_lp_opt and not cor_err_opt:
                # ── Step 3: Re-parse CORRECT.LP ──────────────────────
                correct_data = LPParser.parse_correct(cor_lp_opt)
                stats_table = correct_data.get('statistics_table', [])

                # Re-check ice rings on updated statistics
                ice_rings_opt = LPParser.detect_ice_rings(stats_table)
                new_ice = [r for r in ice_rings_opt if LPParser.ice_ring_is_actionable(r)]
                if new_ice and exclude_ice:
                    send("ap_log", {"text": ">>> " + str(len(new_ice)) + " ice ring(s) detected — adding exclusions"})
                    fix = {'_exclude_resolution_ranges': [
                        {'lo': r['lo'], 'hi': r['hi'], 'label': r['label']} for r in new_ice
                    ]}
                    if _ap_apply_xdsinp_fix(xds_inp_path, fix, send):
                        _ap_set_job(xds_inp_path, "CORRECT")
                        rc, stopped = _ap_run_xds(project_dir, xds_exe, send,
                                                  label="Re-CORRECT (ice excluded)")
                        if stopped:
                            summary['status'] = 'stopped'
                            send("ap_done", {"status": "stopped", "summary": summary})
                            return
                        # Re-parse after ice exclusion
                        cor_lp_ice, _, _ = _ap_check_lp(project_dir, "CORRECT")
                        if cor_lp_ice:
                            correct_data = LPParser.parse_correct(cor_lp_ice)
                            stats_table = correct_data.get('statistics_table', [])

                # ── Step 4: Update all downstream variables ──────────
                cutoff_result = LPParser.determine_resolution_cutoff(stats_table, criterion)
                resolution = cutoff_result.get('resolution') or resolution

                isa = correct_data.get('isa')
                if isa:
                    try:
                        isa_val = float(isa.get('isa', 0))
                    except (ValueError, TypeError):
                        pass

                sg = correct_data.get('space_group') or sg
                uc = correct_data.get('unit_cell') or uc
                summary['space_group'] = sg
                summary['unit_cell'] = uc
                summary['resolution'] = resolution
                summary['all_cutoffs'] = cutoff_result.get('all_cutoffs', {})

                # ── Step 4b: ΔCC½ frame rejection (XDSCC12) ─────────
                # Optional: if XDSCC12 is available and user enabled it.
                # Uses adaptive threshold: 3×MAD default, relaxes to 2×MAD
                # if exclusion impact is ≤ 20° of oscillation.
                dcc_half_result = None
                if dcc_half and not _job_stopped():
                    if not XDSCC12_BIN:
                        XDSCC12_BIN = _find_xdscc12()
                    if XDSCC12_BIN and Path(XDSCC12_BIN).exists():
                        ascii_hkl_cc = _pfile(project_dir, "XDS_ASCII.HKL")
                        if ascii_hkl_cc.exists():
                            send("ap_log", {"text": ">>> Running XDSCC12 for ΔCC½ frame analysis..."})
                            try:
                                cc12_log_lines = []
                                cc12_rc, cc12_outcome = _run_streaming([XDSCC12_BIN, "XDS_ASCII.HKL"], _project_out_dir(project_dir),
                                                                       cc12_log_lines.append, timeout=1800,
                                                                       should_stop=lambda: _job_stopped(), key="autopilot")

                                # Save log
                                cc12_lp_path = _pout(project_dir, "XDSCC12.LP")
                                cc12_lp_path.write_text("\n".join(cc12_log_lines), encoding="utf-8")

                                if cc12_rc == 0 and cc12_outcome == "ok":
                                    cc12_data = LPParser.parse_xdscc12("\n".join(cc12_log_lines))
                                    frames = cc12_data.get('frames', [])
                                    batch_width = cc12_data.get('frames_per_batch') or 1

                                    if len(frames) >= 5:
                                        # Parse OSCILLATION_RANGE from XDS.INP
                                        osc = 1.0
                                        try:
                                            inp_text = _read_text_lenient(xds_inp_path)
                                            import re as _re_osc
                                            m_osc = _re_osc.search(r'OSCILLATION_RANGE\s*=\s*([\d.]+)', inp_text)
                                            if m_osc:
                                                osc = float(m_osc.group(1))
                                                if osc <= 0:
                                                    osc = 1.0
                                        except Exception:
                                            pass

                                        deltas = [f['delta_all'] for f in frames]
                                        n_total = len(deltas)
                                        sorted_d = sorted(deltas)
                                        median_d = sorted_d[n_total // 2]
                                        abs_devs = sorted([abs(d - median_d) for d in deltas])
                                        mad = abs_devs[n_total // 2] * 1.4826  # MAD → sigma

                                        send("ap_log", {"text": ">>>   ΔCC½ median=" + str(round(median_d, 2))
                                                              + "  MAD=" + str(round(mad, 3))
                                                              + "  frames=" + str(n_total)
                                                              + "  batch=" + str(batch_width)
                                                              + "  osc=" + str(osc) + "°"})

                                        if mad > 0.001:  # avoid division issues with perfectly uniform data
                                            # Try 3×MAD first (strict — only severe outliers)
                                            threshold_3 = median_d - 3.0 * mad
                                            bad_3 = [f for f in frames if f['delta_all'] < threshold_3]

                                            # Try 2×MAD (moderate)
                                            threshold_2 = median_d - 2.0 * mad
                                            bad_2 = [f for f in frames if f['delta_all'] < threshold_2]

                                            # Decide: use 2×MAD only if it excludes ≤ 20° of data
                                            excl_degrees_2 = len(bad_2) * batch_width * osc
                                            excl_degrees_3 = len(bad_3) * batch_width * osc

                                            if len(bad_2) > 0 and excl_degrees_2 <= 20.0 and len(bad_2) <= n_total * 0.15:
                                                bad_frames = bad_2
                                                threshold = threshold_2
                                                thr_label = "2×MAD"
                                            elif len(bad_3) > 0 and len(bad_3) <= n_total * 0.15:
                                                bad_frames = bad_3
                                                threshold = threshold_3
                                                thr_label = "3×MAD"
                                            else:
                                                bad_frames = []
                                                threshold = threshold_3
                                                thr_label = "3×MAD"

                                            send("ap_log", {"text": ">>>   3×MAD: " + str(len(bad_3)) + " frames ("
                                                                  + str(round(excl_degrees_3, 1)) + "°)"
                                                                  + "  |  2×MAD: " + str(len(bad_2)) + " frames ("
                                                                  + str(round(excl_degrees_2, 1)) + "°)"})

                                            if bad_frames:
                                                excl_degrees = len(bad_frames) * batch_width * osc
                                                send("ap_log", {"text": ">>>   Using " + thr_label
                                                                      + " threshold=" + str(round(threshold, 2))
                                                                      + " → excluding " + str(len(bad_frames))
                                                                      + " batches (" + str(round(excl_degrees, 1)) + "°)"})

                                                # Build EXCLUDE_DATA_RANGE entries
                                                excl_ranges_data = []
                                                for bf in bad_frames:
                                                    first = bf['batch'] - batch_width + 1
                                                    last = bf['batch']
                                                    excl_ranges_data.append({
                                                        'first': first, 'last': last,
                                                        'reason': 'dcc_half=' + str(round(bf['delta_all'], 2))
                                                    })
                                                    send("ap_log", {"text": ">>>     frames " + str(first) + "-" + str(last)
                                                                          + "  ΔCC½=" + str(round(bf['delta_all'], 2))})

                                                _ap_apply_xdsinp_fix(xds_inp_path,
                                                    {'_exclude_data_ranges': excl_ranges_data}, send)

                                                # Re-INTEGRATE + re-CORRECT with frame exclusions
                                                send("ap_log", {"text": ">>> Re-integrating with bad frames excluded..."})
                                                _ap_set_job(xds_inp_path, "DEFPIX INTEGRATE CORRECT")
                                                rc, stopped = _ap_run_xds(project_dir, xds_exe, send,
                                                    label="Re-integration (ΔCC½ frame rejection)")
                                                if stopped:
                                                    summary['status'] = 'stopped'
                                                    send("ap_done", {"status": "stopped", "summary": summary})
                                                    return

                                                # Re-parse and update all variables
                                                cor_lp_dcc, cor_err_dcc, _ = _ap_check_lp(project_dir, "CORRECT")
                                                if cor_lp_dcc and not cor_err_dcc:
                                                    correct_data = LPParser.parse_correct(cor_lp_dcc)
                                                    stats_table = correct_data.get('statistics_table', [])
                                                    cutoff_result = LPParser.determine_resolution_cutoff(stats_table, criterion)
                                                    resolution = cutoff_result.get('resolution') or resolution
                                                    isa = correct_data.get('isa')
                                                    if isa:
                                                        try:
                                                            isa_val = float(isa.get('isa', 0))
                                                        except (ValueError, TypeError):
                                                            pass
                                                    sg = correct_data.get('space_group') or sg
                                                    uc = correct_data.get('unit_cell') or uc
                                                    summary['space_group'] = sg
                                                    summary['unit_cell'] = uc
                                                    summary['resolution'] = resolution
                                                    summary['all_cutoffs'] = cutoff_result.get('all_cutoffs', {})
                                                else:
                                                    send("ap_log", {"text": ">>> Re-integration after ΔCC½ exclusion failed — using previous results"})

                                                dcc_half_result = {
                                                    'threshold': thr_label,
                                                    'threshold_value': round(threshold, 3),
                                                    'median': round(median_d, 3),
                                                    'mad': round(mad, 4),
                                                    'n_excluded': len(bad_frames),
                                                    'degrees_excluded': round(excl_degrees, 1),
                                                    'n_total': n_total,
                                                }
                                            else:
                                                if len(bad_3) > n_total * 0.15:
                                                    send("ap_log", {"text": ">>>   Too many outliers at 3×MAD ("
                                                                          + str(len(bad_3)) + "/" + str(n_total)
                                                                          + " > 15%) — skipping exclusion"})
                                                else:
                                                    send("ap_log", {"text": ">>>   No severe outliers detected — data is clean"})
                                                dcc_half_result = {
                                                    'threshold': '3×MAD',
                                                    'threshold_value': round(threshold_3, 3),
                                                    'median': round(median_d, 3),
                                                    'mad': round(mad, 4),
                                                    'n_excluded': 0,
                                                    'degrees_excluded': 0,
                                                    'n_total': n_total,
                                                }
                                        else:
                                            send("ap_log", {"text": ">>>   ΔCC½ distribution is uniform (MAD≈0) — no outliers"})
                                    else:
                                        send("ap_log", {"text": ">>>   Too few batches for ΔCC½ analysis (" + str(len(frames)) + ")"})
                                else:
                                    send("ap_log", {"text": ">>>   XDSCC12 " + ("timed out (30 min) - skipping" if cc12_outcome == "timeout" else "exited with code " + str(cc12_rc))})
                            except Exception as e:
                                send("ap_log", {"text": ">>>   XDSCC12 error: " + str(e)})
                        else:
                            send("ap_log", {"text": ">>> XDS_ASCII.HKL not found — skipping ΔCC½"})
                    else:
                        send("ap_log", {"text": ">>> XDSCC12 not available — skipping ΔCC½ analysis"})

                if dcc_half_result:
                    summary['dcc_half'] = dcc_half_result

                # ── Step 5: Before/after comparison ──────────────────
                # read from the CORRECT.LP the re-integration wrote - not from the variables,
                # which still hold the first integration's values when that log lacks them
                post_opt = {'isa': None, 'resolution': None}
                _post_lp, _, _ = _ap_check_lp(project_dir, "CORRECT")
                if _post_lp:
                    _post_cd = LPParser.parse_correct(_post_lp)
                    try:
                        post_opt['isa'] = float((_post_cd.get('isa') or {}).get('isa'))
                    except (TypeError, ValueError):
                        pass
                    post_opt['resolution'] = LPParser.determine_resolution_cutoff(
                        _post_cd.get('statistics_table', []), criterion).get('resolution')
                post_total = None
                for _row in stats_table:
                    if str(_row.get('resolution', '')).lower() == 'total':
                        post_total = _row
                        break
                if post_total:
                    post_opt['r_meas'] = post_total.get('r_meas', '')
                    post_opt['completeness'] = post_total.get('completeness', '')
                    post_opt['i_sigma'] = post_total.get('i_sigma', '')
                    post_opt['cc_half'] = post_total.get('cc_half', '')

                send("ap_log", {"text": ""})
                send("ap_log", {"text": ">>> Optimization comparison (before → after):"})
                labels = {'isa': 'ISa', 'r_meas': 'R-meas', 'i_sigma': '<I/sig>',
                          'cc_half': 'CC1/2', 'completeness': 'Complete%', 'resolution': 'Resolution'}
                for metric in ['isa', 'resolution', 'r_meas', 'i_sigma', 'cc_half', 'completeness']:
                    pre_v = pre_opt.get(metric, '?')
                    post_v = post_opt.get(metric, '?')
                    if pre_v != '?' or post_v != '?':
                        pre_s = str(round(pre_v, 2)) if isinstance(pre_v, float) else str(pre_v)
                        post_s = str(round(post_v, 2)) if isinstance(post_v, float) else str(post_v)
                        send("ap_log", {"text": ">>>   " + labels.get(metric, metric)
                                              + ": " + pre_s + " → " + post_s})

                summary['optimization'] = {'pre': pre_opt, 'post': post_opt, 'kept': True}

                # ── 'if_better': the re-integration has to earn its place ─────
                if optimize == 'if_better' and pre_optimize_dir:
                    better, why = _ap_optimize_is_better(pre_opt, post_opt, optimize_metric)
                    send("ap_log", {"text": ">>> Re-integration " + ("kept: " if better else "rejected: ") + why})
                    if not better:
                        _ap_restore_integration(project_dir, pre_optimize_dir, send)
                        cor_lp_back, _, _ = _ap_check_lp(project_dir, "CORRECT")
                        if cor_lp_back:
                            correct_data = LPParser.parse_correct(cor_lp_back)
                            stats_table = correct_data.get('statistics_table', [])
                            cutoff_result = LPParser.determine_resolution_cutoff(stats_table, criterion)
                            resolution = cutoff_result.get('resolution') or pre_opt.get('resolution')
                            isa_val = pre_opt.get('isa', isa_val)
                            sg = correct_data.get('space_group') or sg
                            uc = correct_data.get('unit_cell') or uc
                            summary['space_group'] = sg
                            summary['unit_cell'] = uc
                            summary['resolution'] = resolution
                            summary['all_cutoffs'] = cutoff_result.get('all_cutoffs', {})
                        summary['optimization']['kept'] = False
                    summary['optimization']['decision'] = why
                send("ap_log", {"text": ""})
            else:
                if cor_err_opt:
                    send("ap_log", {"text": ">>>   CORRECT error after re-integration"})
                elif int_err_opt:
                    send("ap_log", {"text": ">>>   INTEGRATE error after re-integration"})
                if pre_optimize_dir:
                    # the failed pass has already overwritten XPARM.XDS, INTEGRATE.HKL and
                    # moved CORRECT.LP aside: put the first integration back
                    send("ap_log", {"text": ">>> Re-integration failed — restoring the first integration"})
                    _ap_restore_integration(project_dir, pre_optimize_dir, send)
                    summary['optimization'] = {'pre': pre_opt, 'post': {}, 'kept': False,
                                               'decision': 'the re-integration failed'}
                else:
                    send("ap_log", {"text": ">>> Re-integration failed — its files replaced the first integration's; "
                                          "the statistics below may not describe one consistent run"})

            summary['phases_completed'].append('OPTIMIZE')

        if _job_stopped():
            summary['status'] = 'stopped'
            send("ap_done", {"status": "stopped", "summary": summary})
            return

    # Need to refresh stale-file check since OPTIMIZE rewrote XDS_ASCII.HKL
    ascii_hkl = _pfile(project_dir, "XDS_ASCII.HKL")
    ascii_stale = False
    correct_lp_path = _pfile(project_dir, "CORRECT.LP")
    if ascii_hkl.exists() and correct_lp_path.exists():
        try:
            if ascii_hkl.stat().st_mtime < correct_lp_path.stat().st_mtime - 2:
                ascii_stale = True
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════
    #  PHASE 4: XSCALE
    # ══════════════════════════════════════════════════════════════════════
    send("ap_phase", {"phase": "XSCALE", "message": "Running XSCALE..."})
    xscale_stats = []  # will be populated if XSCALE succeeds
    # Verify XDS_ASCII.HKL exists and is current
    if not ascii_hkl.exists() or ascii_stale:
        reason = "stale (from a previous run)" if ascii_stale else "not found"
        send("ap_log", {"text": ">>> XDS_ASCII.HKL " + reason + " — skipping XSCALE and MTZ conversion"})
        send("ap_log", {"text": ">>> The current processing run did not produce usable reflection data."})
        send("ap_log", {"text": ">>> Check the CORRECT step output and data quality."})
        summary['status'] = 'failed'
        summary['failure_reason'] = 'No valid XDS_ASCII.HKL from current run'
        summary['phases_completed'].append('XSCALE_SKIPPED')
        send("ap_done", {"status": "failed", "summary": summary})
        return

    # Build XSCALE.INP
    _ap_build_xscale_inp(project_dir, resolution, friedel)
    send("ap_log", {"text": ">>> Generated XSCALE.INP" + (" (cutoff " + str(round(resolution, 2)) + " A)" if resolution else "")})

    xscale_ok = False
    if not xscale_exe.exists():
        send("ap_log", {"text": ">>> XSCALE executable not found — skipping"})
        summary['phases_completed'].append('XSCALE_SKIPPED')
    else:
        rc, stopped = _ap_run_xscale(project_dir, xscale_exe, send)
        if stopped:
            summary['status'] = 'stopped'
            send("ap_done", {"status": "stopped", "summary": summary})
            return

        xscale_lp, xscale_err, xscale_errline = _ap_check_lp(project_dir, "XSCALE")
        if xscale_err:
            send("ap_log", {"text": ">>> XSCALE failed: " + str(xscale_errline)})
            summary['phases_completed'].append('XSCALE_FAILED')
        else:
            xscale_ok = True
            send("ap_log", {"text": ">>> XSCALE: OK"})
            summary['phases_completed'].append('XSCALE')

            # Parse XSCALE results for summary
            if xscale_lp:
                xscale_data = LPParser.parse_xscale(xscale_lp)
                xscale_stats = xscale_data.get('statistics_table', [])
                if xscale_stats:
                    # Report total line
                    for row in xscale_stats:
                        if row.get('resolution', '').lower() == 'total':
                            send("ap_log", {"text": ">>> XSCALE totals: R-meas=" +
                                 str(row.get('r_meas', '?')) + "% CC1/2=" +
                                 str(row.get('cc_half', '?')) + "% I/sig=" +
                                 str(row.get('i_sigma', '?'))})
                            break

    if _job_stopped():
        summary['status'] = 'stopped'
        send("ap_done", {"status": "stopped", "summary": summary})
        return

    # ══════════════════════════════════════════════════════════════════════
    #  PHASE 5: MTZ Conversion
    # ══════════════════════════════════════════════════════════════════════
    send("ap_phase", {"phase": "CONVERT", "message": "Converting to MTZ..."})

    # Determine input file for conversion:
    # Only use XSCALE.HKL if XSCALE actually succeeded in THIS run
    xscale_hkl = _pfile(project_dir, "XSCALE.HKL")
    if xscale_ok and xscale_hkl.exists():
        conv_input = "XSCALE.HKL"
    else:
        conv_input = "XDS_ASCII.HKL"
        if not xscale_ok:
            send("ap_log", {"text": ">>> XSCALE did not succeed — falling back to XDS_ASCII.HKL for MTZ"})
    send("ap_log", {"text": ">>> Converting " + conv_input + " to MTZ"})

    mtz_name = project_name + ".mtz"

    # Try CCP4 path first (XDSCONV + f2mtz + cad)
    if CCP4_BIN:
        xdsconv_exe = _find_xdsconv_exe(xds_runner.xds_path)
        if xdsconv_exe.exists():
            _ap_build_xdsconv_inp(project_dir, resolution, friedel, input_file=conv_input)
            send("ap_log", {"text": ">>> Running XDSCONV..."})

            conversion_ok = False
            # Run XDSCONV
            try:
                rc, outcome = _run_streaming([str(xdsconv_exe)], _project_out_dir(project_dir),
                                             lambda t: send("ap_log", {"text": t}), timeout=600,
                                             should_stop=lambda: _job_stopped(), key="autopilot", expected_outputs=["XDSCONV.LP", "F2MTZ.INP"])
                if outcome != "ok":
                    raise RuntimeError(_outcome_message(outcome, "XDSCONV"))
                conversion_ok = True
            except Exception as e:
                send("ap_log", {"text": ">>> XDSCONV error: " + str(e)})

            if _job_stopped():
                summary['status'] = 'stopped'
                send("ap_done", {"status": "stopped", "summary": summary})
                return

            # Run f2mtz + cad
            f2mtz_inp = _pout(project_dir, "F2MTZ.INP")
            if conversion_ok and f2mtz_inp.exists():
                f2mtz_exe, _, f2mtz_problem = _ccp4_program("f2mtz")
                cad_exe, _, cad_problem = _ccp4_program("cad")
                if f2mtz_exe and cad_exe:
                    temp_mtz = _pout(project_dir, "temp_f2mtz.mtz")
                    final_mtz = _pout(project_dir, mtz_name)

                    f2mtz_ok = False
                    # f2mtz
                    send("ap_log", {"text": ">>> Running f2mtz..."})
                    try:
                        with open(str(f2mtz_inp), 'r', encoding='utf-8') as fin:
                            cmd, env = _ccp4_command("f2mtz", ["HKLOUT", str(temp_mtz)], _project_out_dir(project_dir))
                            _run_checked(cmd, _project_out_dir(project_dir),
                                           lambda t: None, timeout=600, env=env, stdin_file=fin,
                                           should_stop=lambda: _job_stopped(), key="autopilot", expected_outputs=[temp_mtz])
                        f2mtz_ok = True
                    except Exception as e:
                        send("ap_log", {"text": ">>> f2mtz error: " + str(e)})

                    if _job_stopped():
                        summary['status'] = 'stopped'
                        send("ap_done", {"status": "stopped", "summary": summary})
                        return

                    # cad
                    if f2mtz_ok and temp_mtz.exists():
                        cad_ok = False
                        send("ap_log", {"text": ">>> Running cad..."})
                        try:
                            cmd, env = _ccp4_command("cad", ["HKLIN1", str(temp_mtz), "HKLOUT", str(final_mtz)],
                                                     _project_out_dir(project_dir))
                            _run_checked(cmd, _project_out_dir(project_dir), lambda t: None, timeout=600, env=env,
                                           stdin_text="LABIN FILE 1 ALL\nEND\n",
                                           should_stop=lambda: _job_stopped(), key="autopilot", expected_outputs=[final_mtz])
                            cad_ok = True
                        except Exception as e:
                            send("ap_log", {"text": ">>> cad error: " + str(e)})

                        if cad_ok and final_mtz.exists():
                            send("ap_log", {"text": ">>> MTZ file created: " + str(final_mtz)})
                            summary['mtz_file'] = str(final_mtz)
                        else:
                            send("ap_log", {"text": ">>> MTZ conversion failed (cad)"})
                    else:
                        send("ap_log", {"text": ">>> f2mtz did not produce output"})
                else:
                    send("ap_log", {"text": ">>> MTZ conversion with CCP4 skipped - " + (f2mtz_problem or cad_problem)})
            else:
                send("ap_log", {"text": ">>> F2MTZ.INP not generated by XDSCONV"})
        else:
            send("ap_log", {"text": ">>> xdsconv not found — trying gemmi"})
    else:
        send("ap_log", {"text": ">>> CCP4 not found — trying gemmi fallback"})

    # Gemmi fallback if no MTZ yet
    if not summary.get('mtz_file'):
        try:
            import gemmi
            send("ap_log", {"text": ">>> Converting with gemmi (intensities only, no amplitudes)"})
            hkl_path = str(xscale_hkl if xscale_ok and xscale_hkl.exists() else ascii_hkl)
            out_mtz = str(_pout(project_dir, mtz_name))
            try:
                converted = convert_xds_to_mtz(hkl_path, out_mtz)
                if not converted.get('success'):
                    raise RuntimeError(converted.get('message', 'MTZ conversion failed'))
                send("ap_log", {"text": ">>> MTZ file created (gemmi): " + out_mtz})
                summary['mtz_file'] = out_mtz
            except Exception as e:
                send("ap_log", {"text": ">>> gemmi conversion failed: " + str(e)})
        except ImportError:
            send("ap_log", {"text": ">>> gemmi not available — MTZ conversion skipped"})
            send("ap_log", {"text": ">>> Install CCP4 or gemmi for automatic MTZ generation"})

    summary['phases_completed'].append('CONVERT')

    # ══════════════════════════════════════════════════════════════════════
    #  PHASE 6: Save results and finish
    # ══════════════════════════════════════════════════════════════════════
    send("ap_phase", {"phase": "DONE", "message": "AutoPilot complete"})
    summary['status'] = 'completed'

    # Attach statistics table and key metrics to summary
    # Prefer XSCALE stats if scaling succeeded, else use CORRECT stats
    final_stats = None
    if xscale_ok and xscale_stats:
        final_stats = xscale_stats
        summary['stats_source'] = 'XSCALE'
    elif stats_table:
        final_stats = stats_table
        summary['stats_source'] = 'CORRECT'

    if final_stats:
        summary['stats_table'] = final_stats
        # Extract key metrics from total row for quick display
        total_row = None
        hi_res_row = None
        for row in final_stats:
            if str(row.get('resolution', '')).lower() == 'total':
                total_row = row
        # Highest-res shell = last numeric row before total
        for row in final_stats:
            if str(row.get('resolution', '')).lower() != 'total':
                hi_res_row = row  # last one wins = highest resolution
        if total_row:
            summary['key_metrics'] = {
                'completeness': total_row.get('completeness', ''),
                'r_meas': total_row.get('r_meas', ''),
                'r_merge': total_row.get('r_obs', ''),
                'i_sigma': total_row.get('i_sigma', ''),
                'cc_half': total_row.get('cc_half', ''),
                'observed': total_row.get('observed', ''),
                'unique': total_row.get('unique', ''),
            }
            if hi_res_row:
                summary['key_metrics']['hi_completeness'] = hi_res_row.get('completeness', '')
                summary['key_metrics']['hi_r_meas'] = hi_res_row.get('r_meas', '')
                summary['key_metrics']['hi_i_sigma'] = hi_res_row.get('i_sigma', '')
                summary['key_metrics']['hi_cc_half'] = hi_res_row.get('cc_half', '')

    # ISa
    if isa:
        summary['isa'] = isa

    # Wilson B-factor
    wilson_b = correct_data.get('wilson_line', {}).get('b')
    if wilson_b is not None:
        summary['wilson_b'] = wilson_b

    # Additional diagnostic fields from CORRECT (for warning cards in results)
    if correct_data.get('chi2_values'):
        summary['chi2_values'] = correct_data['chi2_values']
    if correct_data.get('wilson_moments'):
        summary['wilson_moments'] = correct_data['wilson_moments']
    if correct_data.get('mosaicity') is not None:
        summary['mosaicity'] = correct_data['mosaicity']
    summary['friedels_law'] = correct_data.get('friedels_law', friedel == 'FALSE' and 'FALSE' or 'TRUE')

    # Persist completion before telling the browser the workflow is finished.
    meta = ProjectManager.get(project_name)
    for step_name in full_pipeline.split():
        if step_name not in meta.get("completed_steps", []):
            meta.setdefault("completed_steps", []).append(step_name)
    ProjectManager.update(project_name, meta)

    # Save autopilot results
    results_path = _pout(project_dir, "AUTOPILOT_RESULTS.json")
    ProjectManager._write_meta(results_path, summary)

    send("ap_log", {"text": ""})
    send("ap_log", {"text": "============================================"})
    send("ap_log", {"text": "  CrystalPilot AutoPilot — Complete"})
    send("ap_log", {"text": "============================================"})
    if summary.get('space_group'):
        send("ap_log", {"text": "  Space group:   " + str(summary['space_group'])})
        if summary.get('sg_note'):
            send("ap_log", {"text": "                 " + summary['sg_note']})
    if summary.get('resolution'):
        send("ap_log", {"text": "  Resolution:    " + str(round(summary['resolution'], 2)) + " A"})
    km = summary.get('key_metrics', {})
    if km:
        # Values from CORRECT.LP may already contain '%' — strip before formatting
        def _sv(v):
            return str(v).replace('%', '').strip() if v else str(v)
        if km.get('completeness'):
            hi = ' (' + _sv(km['hi_completeness']) + '%)' if km.get('hi_completeness') else ''
            send("ap_log", {"text": "  Completeness:  " + _sv(km['completeness']) + "%" + hi})
        if km.get('r_meas'):
            hi = ' (' + _sv(km['hi_r_meas']) + '%)' if km.get('hi_r_meas') else ''
            send("ap_log", {"text": "  R-meas:        " + _sv(km['r_meas']) + "%" + hi})
        if km.get('i_sigma'):
            hi = ' (' + str(km['hi_i_sigma']) + ')' if km.get('hi_i_sigma') else ''
            send("ap_log", {"text": "  <I/sig(I)>:    " + str(km['i_sigma']) + hi})
        if km.get('cc_half'):
            hi = ' (' + _sv(km['hi_cc_half']) + '%)' if km.get('hi_cc_half') else ''
            send("ap_log", {"text": "  CC1/2:         " + _sv(km['cc_half']) + "%" + hi})
    if summary.get('isa'):
        send("ap_log", {"text": "  ISa:           " + str(summary['isa'].get('isa', '?'))})
    if summary.get('wilson_b') is not None:
        send("ap_log", {"text": "  Wilson B:      " + str(round(summary['wilson_b'], 1)) + " A^2"})
    if summary.get('mtz_file'):
        send("ap_log", {"text": "  MTZ:           " + summary['mtz_file']})
    send("ap_log", {"text": "  Retries:       " + str(summary['retries'])})
    if summary['errors_fixed']:
        send("ap_log", {"text": "  Errors fixed:  " + ", ".join(summary['errors_fixed'])})
    send("ap_log", {"text": "  Stats source:  " + summary.get('stats_source', 'N/A')})
    send("ap_log", {"text": "============================================"})

    send("ap_result", {"type": "final", "data": summary})
    send("ap_done", {"status": "completed", "summary": summary})


def load_autopilot_cached_results(project_dir):
    """Read previously saved AUTOPILOT_RESULTS.json from disk.

    Returns dict with keys:
        'has_results': bool
        plus all summary fields from the autopilot run
    Used by the handler to serve cached results when the AutoPilot tab is opened.
    """
    from pathlib import Path
    project_dir = Path(project_dir)
    result = {'has_results': False}

    json_path = _pout(project_dir, "AUTOPILOT_RESULTS.json")
    if json_path.exists():
        try:
            data = json.loads(_read_text_lenient(json_path))
            if data.get('status'):
                result.update(data)
                result['has_results'] = True
        except Exception:
            pass

    return result
