def _check_gemmi():
    """Check if gemmi is available. Returns (True, version_str) or (False, error_str)."""
    import sys as _cg_sys
    if _cg_sys.modules.get("gemmi") is None and "gemmi" in _cg_sys.modules:
        del _cg_sys.modules["gemmi"]
    try: import importlib; importlib.invalidate_caches()
    except Exception: pass
    try:
        import site as _cg_s
        _u = _cg_s.getusersitepackages()
        if _u and _u not in _cg_sys.path:
            _cg_sys.path.insert(0, _u)
        for _sp in _cg_s.getsitepackages():
            if _sp not in _cg_sys.path:
                _cg_sys.path.append(_sp)
    except Exception: pass
    try:
        import gemmi
        return True, gemmi.__version__
    except ImportError:
        return False, "gemmi not installed (pip install gemmi)"


def convert_xds_to_mtz(input_hkl, output_mtz, generate_freer=True, freer_fraction=0.05,
                       freer_reference=None):
    """Convert XDS_ASCII.HKL to MTZ using gemmi.

    Reads XDS_ASCII.HKL (merged or unmerged, with or without anomalous signal)
    and writes an MTZ file containing intensity data (IMEAN/SIGIMEAN for merged,
    I/SIGI + batch columns for unmerged).

    Optionally adds a FreeR_flag column (requires numpy). The FreeR flag uses
    CCP4 convention: integers 0..N-1 where N = int(1/freer_fraction),
    and flag == 0 designates the test set (~freer_fraction of reflections).
    Assignments are stable per symmetry/Friedel equivalence class. Existing
    flags are preserved from freer_reference or an existing output MTZ.

    IMPORTANT LIMITATION: This produces INTENSITY-ONLY MTZ files.
    No French-Wilson (I→F) conversion is performed.
    - Suitable for: Phenix (auto-converts I→F internally), REFMAC5 twin refinement.
    - NOT suitable for: Standard REFMAC5 refinement (needs FP/SIGFP amplitudes).
    For amplitude-based MTZ files, use the CCP4 pipeline: XDSCONV → f2mtz → cad.

    Args:
        input_hkl: Path to XDS_ASCII.HKL (str or Path)
        output_mtz: Path for output .mtz file (str or Path)
        generate_freer: If True, add FreeR_flag column (requires numpy)
        freer_fraction: Fraction of reflections for test set (default 0.05 = 5%)
        freer_reference: Optional MTZ with the master FreeR assignments

    Returns:
        dict with keys:
            success (bool), message (str),
            columns (list of str), nreflections (int),
            spacegroup (str), cell (list of float),
            has_freer (bool), merged (bool),
            warnings (list of str)

    Raises:
        ImportError: if gemmi is not installed
        FileNotFoundError: if input_hkl does not exist
        RuntimeError: if gemmi cannot parse the input file
    """
    import gemmi
    from pathlib import Path

    input_hkl = str(input_hkl)
    output_mtz = str(output_mtz)

    if not Path(input_hkl).exists():
        raise FileNotFoundError("Input file not found: " + input_hkl)

    warnings = []

    # Read XDS_ASCII.HKL
    xds = gemmi.read_xds_ascii(input_hkl)
    nref_input = xds.data_size

    if nref_input == 0:
        return {
            "success": False,
            "message": "No reflections found in " + input_hkl,
            "columns": [], "nreflections": 0,
            "spacegroup": "", "cell": [],
            "has_freer": False, "merged": False,
            "warnings": ["Input file contains no reflection data"]
        }

    # Convert to MTZ
    mtz = xds.to_mtz()
    sg = gemmi.find_spacegroup_by_number(xds.spacegroup_number)
    if sg is None:
        raise ValueError('Cannot assign crystallographic symmetry to the MTZ')
    mtz.spacegroup = sg
    columns = list(mtz.column_labels())
    nref = mtz.nreflections

    # Determine if merged or unmerged based on presence of BATCH column
    is_merged = "BATCH" not in columns

    # Extract cell and spacegroup
    cell = [mtz.cell.a, mtz.cell.b, mtz.cell.c,
            mtz.cell.alpha, mtz.cell.beta, mtz.cell.gamma]
    sg_name = mtz.spacegroup_name or ""
    sg_num = mtz.spacegroup_number

    # If spacegroup name is empty but number is set, try to get name
    if not sg_name and sg_num > 0:
        try:
            sg_obj = gemmi.SpaceGroup(sg_num)
            sg_name = sg_obj.short_name()
        except Exception:
            sg_name = "SG#" + str(sg_num)

    # Determine column content description for user
    if is_merged:
        if "IMEAN" in columns and "SIGIMEAN" in columns:
            col_desc = "IMEAN/SIGIMEAN (merged intensities)"
        else:
            col_desc = ", ".join(columns[3:])  # skip H,K,L
    else:
        col_desc = "I/SIGI + batch info (unmerged intensities)"

    # Add FreeR_flag if requested
    has_freer = False
    if generate_freer and nref > 0:
        try:
            import numpy as np
            import hashlib
            import math
            if not math.isfinite(float(freer_fraction)) or not 0 < freer_fraction <= 0.5:
                raise ValueError('FreeR fraction must be greater than zero and at most 0.5')
            nbins = max(2, int(round(1.0 / freer_fraction)))
            asu, ops = gemmi.ReciprocalAsu(sg), sg.operations()
            def reflection_key(hkl):
                return tuple(asu.to_asu([int(v) for v in hkl], ops)[0])
            # Preserve assignments on re-export, or use an explicitly supplied
            # reference MTZ. Reject conflicts instead of silently corrupting it.
            reference = freer_reference or (output_mtz if Path(output_mtz).exists() else None)
            assignments = {}
            if reference:
                previous = gemmi.read_mtz_file(str(reference))
                labels = list(previous.column_labels())
                if 'FreeR_flag' in labels:
                    if previous.spacegroup is None or previous.spacegroup.operations() != ops:
                        raise ValueError('FreeR reference uses a different space group')
                    flag_index = labels.index('FreeR_flag')
                    for row in np.array(previous, copy=True):
                        flag = float(row[flag_index])
                        if not math.isfinite(flag):
                            continue
                        if flag != int(flag) or flag < 0:
                            raise ValueError('FreeR reference contains invalid flags')
                        hkl = reflection_key(row[:3])
                        if hkl in assignments and assignments[hkl] != int(flag):
                            raise ValueError('FreeR reference has conflicting flags for equivalent reflections; choose a consistent reference or a new output filename')
                        assignments[hkl] = int(flag)
                    if assignments:
                        nbins = max(nbins, max(assignments.values()) + 1)
            mtz.add_column("FreeR_flag", "I")
            data = np.array(mtz, copy=False)
            for i, row in enumerate(data):
                hkl = reflection_key(row[:3])
                if hkl not in assignments:
                    # Stable per-ASU assignment also survives reordering and
                    # expansion of a dataset, without changing global RNG state.
                    digest = hashlib.sha256(('CrystalPilot-FreeR-v1:' + str(sg.number) + ':' + ','.join(map(str, hkl))).encode()).digest()
                    assignments[hkl] = int.from_bytes(digest[:8], 'big') % nbins
                data[i, -1] = assignments[hkl]
            mtz.set_data(data)
            has_freer = True
            n_test = int(np.sum(data[:, -1] == 0.0))
            pct = 100.0 * n_test / nref if nref > 0 else 0.0
            columns = list(mtz.column_labels())
        except ImportError:
            warnings.append(
                "numpy not available — FreeR_flag not added. "
                "Install numpy (pip install numpy) to enable FreeR flag generation, "
                "or add FreeR flags in your refinement program."
            )

    # Write MTZ
    mtz.write_to_file(output_mtz)

    # Verify output was written
    if not Path(output_mtz).exists():
        return {
            "success": False,
            "message": "MTZ file was not created at " + output_mtz,
            "columns": columns, "nreflections": nref,
            "spacegroup": sg_name, "cell": cell,
            "has_freer": has_freer, "merged": is_merged,
            "warnings": warnings
        }

    out_size = Path(output_mtz).stat().st_size

    msg = ("MTZ file written: " + output_mtz
           + " (" + str(nref) + " reflections, "
           + str(out_size) + " bytes, "
           + col_desc + ")")

    # Add limitation warning
    warnings.append(
        "This MTZ contains intensities only (no amplitudes). "
        "Suitable for Phenix refinement (auto-converts I→F). "
        "For REFMAC5 standard refinement, use the CCP4 pipeline "
        "(XDSCONV → f2mtz → cad) to obtain FP/SIGFP amplitudes."
    )

    return {
        "success": True,
        "message": msg,
        "columns": columns,
        "nreflections": nref,
        "spacegroup": sg_name,
        "cell": cell,
        "has_freer": has_freer,
        "merged": is_merged,
        "warnings": warnings
    }


# ---------------------------------------------------------------------------
# Gemmi analysis functions: merging stats, completeness, lattice symmetry
#
# All functions probe gemmi capabilities at runtime and use fallback paths
# so they work across gemmi versions (tested 0.5.x through 0.7.x).
# ---------------------------------------------------------------------------

def _xds_sg_cell(xds):
    """Extract SpaceGroup and UnitCell from an XdsAscii object (all versions)."""
    import gemmi
    sg = gemmi.find_spacegroup_by_number(xds.spacegroup_number)
    cc = xds.cell_constants
    cell = gemmi.UnitCell(cc[0], cc[1], cc[2], cc[3], cc[4], cc[5])
    return sg, cell, list(cc)


def _get_merged_mtz(xds):
    """Return an Mtz with one row per unique (merged, mean) reflection.

    Tries three strategies in order of preference:
      1. Intensities.clone + merge_in_place + prepare_merged_mtz  (gemmi ≥0.6.5)
      2. Intensities.merged + prepare_merged_mtz                  (gemmi ≥0.7.3)
      3. XdsAscii.to_mtz  (all versions — may contain unmerged rows)
    """
    import gemmi

    # Strategy 1: clone + merge_in_place (avoids mutating original)
    if hasattr(gemmi, 'Intensities') and hasattr(gemmi, 'DataType'):
        try:
            i = gemmi.Intensities()
            i.import_xds(xds)
            copy = i.clone()
            copy.merge_in_place(gemmi.DataType.Mean)
            return copy.prepare_merged_mtz(True), "merge_in_place"
        except Exception:
            pass

        # Strategy 2: .merged() (returns new object)
        try:
            i2 = gemmi.Intensities()
            i2.import_xds(xds)
            m = i2.merged(gemmi.DataType.Mean)
            return m.prepare_merged_mtz(True), "merged"
        except Exception:
            pass

    # Strategy 3: to_mtz (always available, may be unmerged)
    return xds.to_mtz(), "to_mtz"


def _filter_intensities_by_resolution(intensities, res_low=None, res_high=None):
    """Filter an Intensities object to a resolution range.

    Args:
        intensities: gemmi.Intensities (already import_xds'd)
        res_low:  low-resolution limit in Angstrom (e.g. 80.0) — large d
        res_high: high-resolution limit in Angstrom (e.g. 2.0) — small d

    Returns new Intensities with only reflections in [res_high, res_low].
    If both are None, returns the original unchanged.
    """
    if res_low is None and res_high is None:
        return intensities

    import gemmi
    import numpy as np

    cell = intensities.unit_cell
    sg = intensities.spacegroup
    hkl = np.array(intensities.miller_array, dtype=np.int32)
    val = np.array(intensities.value_array, dtype=np.float64)
    sig = np.array(intensities.sigma_array, dtype=np.float64)

    if len(hkl) == 0:
        return intensities

    # Compute d-spacing for each reflection
    d_arr = np.array([cell.calculate_d(h) for h in hkl])

    mask = np.ones(len(d_arr), dtype=bool)
    if res_low is not None and res_low > 0:
        mask &= (d_arr <= res_low)
    if res_high is not None and res_high > 0:
        mask &= (d_arr >= res_high)

    if mask.all():
        return intensities  # no filtering needed

    filtered = gemmi.Intensities()
    filtered.set_data(cell, sg, hkl[mask], val[mask], sig[mask])
    return filtered


def _filter_mtz_by_resolution(mtz, res_low=None, res_high=None):
    """Filter an Mtz object by resolution. Returns (filtered_mtz, n_removed).

    For completeness calculation on merged MTZ.
    If both are None, returns original unchanged.
    """
    if res_low is None and res_high is None:
        return mtz, 0

    import numpy as np

    d_arr = mtz.make_d_array()
    if len(d_arr) == 0:
        return mtz, 0

    mask = np.ones(len(d_arr), dtype=bool)
    if res_low is not None and res_low > 0:
        mask &= (d_arr <= res_low)
    if res_high is not None and res_high > 0:
        mask &= (d_arr >= res_high)

    n_removed = int(np.sum(~mask))
    if n_removed == 0:
        return mtz, 0

    # Extract data as 2D array, filter rows, write back
    data = np.array(mtz, copy=True)  # shape (nrows, ncols), float32
    mtz.set_data(data[mask].astype(np.float32))
    return mtz, n_removed


def analyze_merging_stats(input_hkl, n_shells=20, weighting='X', res_low=None, res_high=None):
    """Compute merging statistics from XDS_ASCII.HKL using gemmi.

    Requires gemmi.Intensities with calculate_merging_stats (gemmi ≥0.6).
    """
    import gemmi

    xds = gemmi.read_xds_ascii(input_hkl)
    sg, cell, cell_params = _xds_sg_cell(xds)
    sg_name = sg.xhm() if sg else "unknown"

    if not hasattr(gemmi, 'Intensities'):
        return {"success": False, "message": "gemmi too old: Intensities class not available. Upgrade with: pip install -U gemmi"}

    intensities = gemmi.Intensities()
    intensities.import_xds(xds)

    # Apply resolution filter if specified
    intensities = _filter_intensities_by_resolution(intensities, res_low, res_high)

    # Determine data type from friedels_law flag
    dt = gemmi.DataType.Mean if xds.friedels_law else gemmi.DataType.Anomalous

    intensities.prepare_for_merging(dt)

    # Setup binner
    binner = gemmi.Binner()
    try:
        binner.setup(n_shells, gemmi.Binner.Method.Dstar3, intensities)
    except Exception:
        try:
            binner.setup(n_shells, gemmi.Binner.Method.EqualCount, intensities)
        except Exception:
            return {"success": False, "message": "Failed to set up resolution bins"}

    # Calculate stats
    try:
        stats_list = intensities.calculate_merging_stats(binner, use_weights=weighting)
    except TypeError:
        # Older gemmi may not support use_weights keyword
        stats_list = intensities.calculate_merging_stats(binner)

    # Build per-shell results
    shells = []
    for i, st in enumerate(stats_list):
        d_max = binner.dmax_of_bin(i)
        d_min = binner.dmin_of_bin(i)
        n_all = st.all_refl if hasattr(st, 'all_refl') else None
        n_uniq = st.unique_refl if hasattr(st, 'unique_refl') else None
        mult = round(n_all / n_uniq, 1) if n_all and n_uniq and n_uniq > 0 else None
        shell_data = {
            "d_max": round(d_max, 3),
            "d_min": round(d_min, 3),
            "r_merge": _safe_float(st.r_merge()),
            "r_meas": _safe_float(st.r_meas()),
            "r_pim": _safe_float(st.r_pim()),
            "cc_half": _safe_float(st.cc_half()),
            "n_obs": n_all,
            "n_unique": n_uniq,
            "multiplicity": mult,
        }
        try:
            shell_data["cc_star"] = _safe_float(st.cc_star())
        except Exception:
            shell_data["cc_star"] = None
        shells.append(shell_data)

    # Overall stats (no binner)
    try:
        overall_list = intensities.calculate_merging_stats(None, use_weights=weighting)
    except TypeError:
        overall_list = intensities.calculate_merging_stats(None)
    overall = {}
    if overall_list:
        ov = overall_list[0]
        n_all_ov = ov.all_refl if hasattr(ov, 'all_refl') else None
        n_uniq_ov = ov.unique_refl if hasattr(ov, 'unique_refl') else None
        mult_ov = round(n_all_ov / n_uniq_ov, 1) if n_all_ov and n_uniq_ov and n_uniq_ov > 0 else None
        overall = {
            "r_merge": _safe_float(ov.r_merge()),
            "r_meas": _safe_float(ov.r_meas()),
            "r_pim": _safe_float(ov.r_pim()),
            "cc_half": _safe_float(ov.cc_half()),
            "n_obs": n_all_ov,
            "n_unique": n_uniq_ov,
            "multiplicity": mult_ov,
        }
        try:
            overall["cc_star"] = _safe_float(ov.cc_star())
        except Exception:
            overall["cc_star"] = None

    # Resolution range
    try:
        res_range = intensities.resolution_range()
        d_max_overall = round(res_range[0], 2) if res_range else None
        d_min_overall = round(res_range[1], 2) if len(res_range) > 1 else None
    except Exception:
        d_max_overall = shells[0]["d_max"] if shells else None
        d_min_overall = shells[-1]["d_min"] if shells else None

    return {
        "success": True,
        "shells": shells,
        "overall": overall,
        "data_type": "anomalous" if dt == gemmi.DataType.Anomalous else "mean",
        "n_observations": xds.data_size if hasattr(xds, 'data_size') else None,
        "spacegroup": sg_name,
        "cell": cell_params,
        "resolution_range": [d_max_overall, d_min_overall],
        "weighting": weighting,
        "n_shells": len(shells)
    }


def analyze_completeness(input_hkl, n_shells=20, res_low=None, res_high=None):
    """Compute completeness per resolution shell from XDS_ASCII.HKL.

    Merges reflections (combining Friedel mates) then counts unique
    reflections vs the theoretical count for the space group.
    Works across all gemmi versions via _get_merged_mtz fallback chain.
    """
    import gemmi
    import numpy as np

    xds = gemmi.read_xds_ascii(input_hkl)
    sg, cell, cc = _xds_sg_cell(xds)
    if not sg:
        return {"success": False, "message": "Could not read spacegroup from file"}

    is_anomalous = not xds.friedels_law

    # Get merged MTZ (tries multiple strategies)
    merged_mtz, method = _get_merged_mtz(xds)

    # Apply resolution filter to merged MTZ
    merged_mtz, _nrem = _filter_mtz_by_resolution(merged_mtz, res_low, res_high)

    d_array = merged_mtz.make_d_array()
    if len(d_array) == 0:
        return {"success": False, "message": "No reflections in file"}

    d_min_overall = float(np.min(d_array))
    d_max_overall = float(np.max(d_array))

    # Setup binner on the merged MTZ
    binner = gemmi.Binner()
    binner.setup(n_shells, gemmi.Binner.Method.Dstar3, merged_mtz)

    bins = binner.get_bins(merged_mtz)

    shells = []
    for i in range(binner.size):
        d_max_sh = binner.dmax_of_bin(i)
        d_min_sh = binner.dmin_of_bin(i)
        mask = (bins == i)
        n_observed = int(np.sum(mask))
        n_theoretical = gemmi.count_reflections(cell, sg, d_min_sh, dmax=d_max_sh)
        # completeness: observed/theoretical, capped at 1.0
        completeness = round(min(n_observed, n_theoretical) / n_theoretical, 4) if n_theoretical > 0 else 0.0
        shells.append({
            "d_max": round(d_max_sh, 3),
            "d_min": round(d_min_sh, 3),
            "n_observed": n_observed,
            "n_theoretical": n_theoretical,
            "completeness": completeness
        })

    n_total_obs = len(d_array)
    n_total_theory = gemmi.count_reflections(cell, sg, d_min_overall, dmax=d_max_overall)
    overall_completeness = round(min(n_total_obs, n_total_theory) / n_total_theory, 4) if n_total_theory > 0 else 0.0

    return {
        "success": True,
        "shells": shells,
        "overall": {
            "n_observed": n_total_obs,
            "n_theoretical": n_total_theory,
            "completeness": overall_completeness
        },
        "spacegroup": sg.xhm(),
        "cell": cc,
        "resolution_range": [round(d_max_overall, 2), round(d_min_overall, 2)],
        "anomalous_input": is_anomalous,
        "merge_method": method
    }


def analyze_lattice_symmetry(input_hkl, max_obliq=3.0):
    """Find lattice symmetry consistent with unit cell from XDS_ASCII.HKL.

    Uses gemmi.find_lattice_symmetry() (gemmi ≥0.5). Falls back gracefully
    if GruberVector or find_lattice_2fold_ops are unavailable.
    """
    import gemmi

    xds = gemmi.read_xds_ascii(input_hkl)
    sg, cell, cell_params = _xds_sg_cell(xds)

    if not sg:
        return {"success": False, "message": "Could not determine spacegroup from file"}

    if not hasattr(gemmi, 'find_lattice_symmetry'):
        return {"success": False, "message": "gemmi too old: find_lattice_symmetry not available. Upgrade with: pip install -U gemmi"}

    sg_name = sg.xhm()

    # Determine centring
    centring = sg.centring_type() if hasattr(sg, 'centring_type') else sg_name[0]

    # Find lattice symmetry at increasing obliquity levels
    results = []
    seen_numbers = set()
    for obliq_try in sorted(set([1.0, 2.0, max_obliq, 5.0, 8.0])):
        try:
            ops = gemmi.find_lattice_symmetry(cell, centring, obliq_try)
            if hasattr(gemmi, 'find_spacegroup_by_ops'):
                found_sg = gemmi.find_spacegroup_by_ops(ops)
            else:
                continue
            if found_sg and found_sg.number not in seen_numbers:
                seen_numbers.add(found_sg.number)
                csys = found_sg.crystal_system_str() if hasattr(found_sg, 'crystal_system_str') else str(found_sg.crystal_system())
                ctr = found_sg.centring_type() if hasattr(found_sg, 'centring_type') else found_sg.xhm()[0]
                results.append({
                    "spacegroup": found_sg.xhm(),
                    "number": found_sg.number,
                    "crystal_system": csys,
                    "centring": ctr,
                    "max_obliquity": obliq_try
                })
        except Exception:
            pass

    # Find 2-fold ops (requires reduced cell via GruberVector)
    twofolds = []
    if hasattr(gemmi, 'GruberVector') and hasattr(gemmi, 'find_lattice_2fold_ops'):
        try:
            gv = gemmi.GruberVector(cell, centring)
            gv.niggli_reduce()
            reduced_cell = gemmi.UnitCell(*gv.cell_parameters())
            ops_2fold = gemmi.find_lattice_2fold_ops(reduced_cell, max(max_obliq, 5.0))
            for op, obliq_val in ops_2fold:
                twofolds.append({
                    "operation": op.triplet(),
                    "obliquity": round(obliq_val, 2)
                })
        except Exception:
            pass

    return {
        "success": True,
        "current_spacegroup": sg_name,
        "current_number": sg.number,
        "cell": cell_params,
        "centring": centring,
        "possible_symmetries": results,
        "twofold_ops": twofolds,
        "max_obliquity_searched": max(max_obliq, 8.0)
    }


def _safe_float(val):
    """Convert to float, return None if NaN/inf."""
    import math
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 6)
    except (TypeError, ValueError):
        return None


def analyze_data_quality(input_hkl, n_shells=20, weighting='X', res_low=None, res_high=None):
    """Combined merging statistics + completeness in one pass.

    Returns a unified result with per-shell rows containing both
    merging R-factors/CC and completeness data.
    """
    # Run both analyses
    merging = analyze_merging_stats(input_hkl, n_shells=n_shells, weighting=weighting, res_low=res_low, res_high=res_high)
    completeness = analyze_completeness(input_hkl, n_shells=n_shells, res_low=res_low, res_high=res_high)

    if not merging.get("success"):
        return merging
    if not completeness.get("success"):
        return completeness

    # Merge shell data by index (both use same n_shells)
    m_shells = merging.get("shells", [])
    c_shells = completeness.get("shells", [])

    combined_shells = []
    for i in range(max(len(m_shells), len(c_shells))):
        ms = m_shells[i] if i < len(m_shells) else {}
        cs = c_shells[i] if i < len(c_shells) else {}
        row = {
            "d_max": ms.get("d_max") or cs.get("d_max"),
            "d_min": ms.get("d_min") or cs.get("d_min"),
            "n_obs": ms.get("n_obs"),
            "n_unique": ms.get("n_unique"),
            "multiplicity": ms.get("multiplicity"),
            "r_merge": ms.get("r_merge"),
            "r_meas": ms.get("r_meas"),
            "r_pim": ms.get("r_pim"),
            "cc_half": ms.get("cc_half"),
            "cc_star": ms.get("cc_star"),
            "n_observed": cs.get("n_observed"),
            "n_theoretical": cs.get("n_theoretical"),
            "completeness": cs.get("completeness"),
        }
        combined_shells.append(row)

    # Merge overall
    m_ov = merging.get("overall", {})
    c_ov = completeness.get("overall", {})
    combined_overall = {}
    combined_overall.update(m_ov)
    if c_ov:
        combined_overall["n_observed_unique"] = c_ov.get("n_observed")
        combined_overall["n_theoretical"] = c_ov.get("n_theoretical")
        combined_overall["completeness"] = c_ov.get("completeness")

    return {
        "success": True,
        "shells": combined_shells,
        "overall": combined_overall,
        "data_type": merging.get("data_type", "mean"),
        "n_observations": merging.get("n_observations"),
        "spacegroup": merging.get("spacegroup", ""),
        "cell": merging.get("cell", []),
        "resolution_range": merging.get("resolution_range", []),
        "weighting": merging.get("weighting", weighting),
        "n_shells": len(combined_shells),
        "anomalous_input": completeness.get("anomalous_input", False),
        "merge_method": completeness.get("merge_method", ""),
    }


# ---------------------------------------------------------------------------
# Anomalous scattering factors via Cromer-Liberman
# ---------------------------------------------------------------------------

# Common elements for SAD/MAD with their Z numbers
ANOMALOUS_ELEMENTS = {
    "P":  15, "S":  16, "Cl": 17, "K":  19, "Ca": 20, "Mn": 25, "Fe": 26,
    "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "As": 33, "Se": 34, "Br": 35,
    "Mo": 42, "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "I":  53,
    "Xe": 54, "Ba": 56, "La": 57, "Sm": 62, "Eu": 63, "Gd": 64, "Yb": 70,
    "Lu": 71, "Ta": 73, "W":  74, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79,
    "Hg": 80, "Pb": 82, "Bi": 83, "U":  92,
}

def compute_anomalous_scattering(element, wavelength_a, energy_ev=None, scan_range_ev=200, scan_steps=50):
    """Compute anomalous scattering factors f' and f'' for an element.

    Args:
        element: element symbol (e.g. 'Se') or atomic number (int)
        wavelength_a: X-ray wavelength in Angstrom
        energy_ev: beam energy in eV (if given, overrides wavelength)
        scan_range_ev: range for the energy scan around the main energy
        scan_steps: number of points in the energy scan

    Returns dict with f', f'' at the specified energy plus an energy scan
    showing how f'/f'' vary near the working energy.
    """
    import gemmi

    if not hasattr(gemmi, 'cromer_liberman'):
        return {"success": False, "message": "gemmi too old: cromer_liberman not available. Upgrade with: pip install -U gemmi"}

    # Resolve element to Z
    if isinstance(element, int):
        z = element
        el_symbol = gemmi.Element(z).name if hasattr(gemmi, 'Element') else str(z)
    else:
        element = element.strip().capitalize()
        if len(element) > 1:
            element = element[0] + element[1:].lower()
        z = ANOMALOUS_ELEMENTS.get(element)
        if z is None:
            # Try gemmi.Element
            try:
                el = gemmi.Element(element)
                z = el.atomic_number
                if z == 0:
                    return {"success": False, "message": "Unknown element: " + str(element)}
            except Exception:
                return {"success": False, "message": "Unknown element: " + str(element)}
        el_symbol = element

    # Compute energy
    if energy_ev is not None and energy_ev > 0:
        energy = float(energy_ev)
        wavelength_a = 12398.419 / energy
    elif wavelength_a is not None and wavelength_a > 0:
        energy = 12398.419 / float(wavelength_a)
    else:
        return {"success": False, "message": "Specify wavelength or energy"}

    # Main calculation
    try:
        fp, fpp = gemmi.cromer_liberman(z, energy)
    except Exception as e:
        return {"success": False, "message": "cromer_liberman failed: " + str(e)}

    result = {
        "success": True,
        "element": el_symbol,
        "atomic_number": z,
        "wavelength_a": round(wavelength_a, 5),
        "energy_ev": round(energy, 1),
        "fp": round(fp, 3),
        "fpp": round(fpp, 3),
    }

    # Energy scan: compute f'/f'' over a range around the working energy
    scan = []
    e_start = max(100, energy - scan_range_ev)
    e_end = energy + scan_range_ev
    step = (e_end - e_start) / scan_steps
    for i in range(scan_steps + 1):
        e = e_start + i * step
        try:
            sp, spp = gemmi.cromer_liberman(z, e)
            scan.append({
                "energy_ev": round(e, 1),
                "wavelength_a": round(12398.419 / e, 5),
                "fp": round(sp, 3),
                "fpp": round(spp, 3),
            })
        except Exception:
            pass

    result["scan"] = scan

    # Find f'' maximum (absorption edge) in scan range
    if scan:
        max_fpp = max(scan, key=lambda s: s["fpp"])
        min_fp = min(scan, key=lambda s: s["fp"])
        result["edge_peak"] = {
            "energy_ev": max_fpp["energy_ev"],
            "wavelength_a": max_fpp["wavelength_a"],
            "fpp": max_fpp["fpp"],
        }
        result["edge_inflection"] = {
            "energy_ev": min_fp["energy_ev"],
            "wavelength_a": min_fp["wavelength_a"],
            "fp": min_fp["fp"],
        }

    return result

# ---------------------------------------------------------------------------
# PDB deposition mmCIF generation
# ---------------------------------------------------------------------------

def prepare_deposition_cif(input_hkl, merged_mtz_path=None, output_path=None):
    """Generate a PDB deposition-ready SF-mmCIF file.

    Combines merged and unmerged reflection data into a single mmCIF file
    following PDB deposition requirements (merged in _refln, unmerged in
    _diffrn_refln).

    Args:
        input_hkl: path to unmerged XDS_ASCII.HKL
        merged_mtz_path: optional path to a pre-existing merged MTZ.
                         If None, merged data is computed from the HKL file.
        output_path: where to write the .cif file. If None, auto-generated
                     next to input_hkl.

    Returns dict with success/message and output_path.
    """
    import gemmi
    import os

    if not hasattr(gemmi, 'MtzToCif'):
        return {"success": False,
                "message": "gemmi too old: MtzToCif not available. Upgrade: pip install -U gemmi"}

    # ── Read unmerged data ──────────────────────────────────────
    try:
        xds = gemmi.read_xds_ascii(input_hkl)
    except Exception as e:
        return {"success": False, "message": "Cannot read XDS_ASCII: " + str(e)}

    sg, cell, cell_params = _xds_sg_cell(xds)
    sg_name = sg.xhm() if sg else "unknown"
    n_unmerged = xds.data_size

    # to_mtz() produces unmerged MTZ with batch headers
    try:
        unmerged_mtz = xds.to_mtz()
    except Exception as e:
        return {"success": False, "message": "xds.to_mtz() failed: " + str(e)}

    n_unmerged_mtz = unmerged_mtz.nreflections
    n_batches = len(unmerged_mtz.batches)

    # ── Get or make merged data ─────────────────────────────────
    merged_mtz = None
    merged_source = None

    # Strategy 1: user-provided merged MTZ
    if merged_mtz_path:
        try:
            merged_mtz = gemmi.read_mtz_file(str(merged_mtz_path))
            merged_source = os.path.basename(str(merged_mtz_path))
            # Verify it's actually merged (no batches)
            if len(merged_mtz.batches) > 0:
                # It's unmerged — cannot use as merged input
                merged_mtz = None
                merged_source = None
        except Exception:
            merged_mtz = None

    # Strategy 2: compute merged from XDS_ASCII via Intensities
    if merged_mtz is None:
        try:
            merged_mtz, merge_method = _get_merged_mtz(xds)
            merged_source = "gemmi (" + merge_method + ")"
        except Exception as e:
            return {"success": False,
                    "message": "Could not create merged data: " + str(e)}

    if merged_mtz is None:
        return {"success": False, "message": "Failed to obtain merged MTZ"}

    n_merged = merged_mtz.nreflections

    # ── Determine output path ───────────────────────────────────
    if output_path is None:
        base_dir = os.path.dirname(os.path.abspath(input_hkl))
        output_path = os.path.join(base_dir, "deposit_sf.cif")

    # ── Convert to mmCIF ────────────────────────────────────────
    try:
        conv = gemmi.MtzToCif()
        conv.with_comments = True
        conv.with_history = True

        # Set wavelength from XDS header if available
        if hasattr(xds, 'wavelength') and xds.wavelength > 0:
            conv.wavelength = xds.wavelength

        cif_string = conv.write_cif_to_string(merged_mtz, unmerged_mtz)
    except Exception as e:
        return {"success": False,
                "message": "MtzToCif conversion failed: " + str(e)}

    # ── Write output ────────────────────────────────────────────
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cif_string)
    except Exception as e:
        return {"success": False, "message": "Cannot write file: " + str(e)}

    return {
        "success": True,
        "output_path": output_path,
        "output_size": os.path.getsize(output_path),
        "spacegroup": sg_name,
        "cell": cell_params,
        "n_merged": n_merged,
        "n_unmerged": n_unmerged_mtz,
        "n_batches": n_batches,
        "wavelength": round(xds.wavelength, 5) if hasattr(xds, 'wavelength') else None,
        "merged_source": merged_source,
        "merged_columns": [c.label for c in merged_mtz.columns],
        "unmerged_columns": [c.label for c in unmerged_mtz.columns],
    }

# ---------------------------------------------------------------------------
# Polarization correction
# ---------------------------------------------------------------------------

def _quick_rmerge(xds):
    """Compute overall R-merge from an XdsAscii object.

    Fast single-pass calculation for before/after comparison.
    Returns dict with r_merge, r_meas, n_obs, n_unique or None on failure.
    """
    import gemmi

    if not hasattr(gemmi, 'Intensities'):
        return None

    try:
        intensities = gemmi.Intensities()
        intensities.import_xds(xds)
        dt = gemmi.DataType.Mean if xds.friedels_law else gemmi.DataType.Anomalous
        intensities.prepare_for_merging(dt)

        # Overall stats (no binner = overall)
        try:
            stats_list = intensities.calculate_merging_stats(None)
        except Exception:
            return None

        if not stats_list:
            return None

        ov = stats_list[0]
        n_all = ov.all_refl if hasattr(ov, 'all_refl') else None
        n_uniq = ov.unique_refl if hasattr(ov, 'unique_refl') else None
        return {
            "r_merge": _safe_float(ov.r_merge()),
            "r_meas": _safe_float(ov.r_meas()),
            "r_pim": _safe_float(ov.r_pim()),
            "cc_half": _safe_float(ov.cc_half()),
            "n_obs": n_all,
            "n_unique": n_uniq,
        }
    except Exception:
        return None


def apply_polarization_and_compare(input_hkl, polarization=0.99, normal=(0, 1, 0),
                                   output_hkl=None):
    """Apply polarization correction to XDS_ASCII.HKL and show before/after.

    Args:
        input_hkl: path to XDS_ASCII.HKL
        polarization: polarization fraction (0 to 1).
                      0.99 = typical synchrotron, 0.5 = unpolarized / lab source
        normal: 3-tuple for the polarization normal direction.
                (0,1,0) = horizontal polarization (standard synchrotron)
                (1,0,0) = vertical polarization
        output_hkl: path for corrected file. If None, writes to
                    <input_dir>/XDS_ASCII_polcorr.HKL

    Returns dict with success, before/after stats, output path.
    """
    import gemmi
    import os
    import numpy as np

    if not hasattr(gemmi.XdsAscii, 'apply_polarization_correction'):
        return {"success": False,
                "message": "gemmi too old: apply_polarization_correction not available"}

    # Read input
    try:
        xds = gemmi.read_xds_ascii(input_hkl)
    except Exception as e:
        return {"success": False, "message": "Cannot read file: " + str(e)}

    n_refl = xds.data_size
    sg, cell, cell_params = _xds_sg_cell(xds)

    # Capture before intensities
    iobs_before = np.array(xds.iobs_array, copy=True)

    # Compute before merging stats
    before_stats = _quick_rmerge(xds)

    # Apply correction
    p = float(polarization)
    nv = gemmi.Vec3(float(normal[0]), float(normal[1]), float(normal[2]))
    try:
        xds.apply_polarization_correction(p, nv)
    except RuntimeError as e:
        msg = str(e)
        if "unknown unit cell axes" in msg:
            return {"success": False,
                    "message": "XDS_ASCII.HKL is missing UNIT_CELL_A/B/C_AXIS headers. "
                               "These are required for the polarization geometry calculation. "
                               "Re-run CORRECT in XDS to generate a file with axis information."}
        return {"success": False, "message": "Correction failed: " + msg}

    # Capture after intensities
    iobs_after = np.array(xds.iobs_array, copy=True)

    # Compute intensity change statistics
    valid = (iobs_before != 0)
    if np.any(valid):
        ratios = iobs_after[valid] / iobs_before[valid]
        mean_ratio = float(np.mean(ratios))
        std_ratio = float(np.std(ratios))
        min_ratio = float(np.min(ratios))
        max_ratio = float(np.max(ratios))
    else:
        mean_ratio = std_ratio = min_ratio = max_ratio = 1.0

    # Compute after merging stats
    after_stats = _quick_rmerge(xds)

    # Write corrected file
    if output_hkl is None:
        base_dir = os.path.dirname(os.path.abspath(input_hkl))
        output_hkl = os.path.join(base_dir, "XDS_ASCII_polcorr.HKL")

    try:
        mtz_out = xds.to_mtz()
        # We need to write as XDS_ASCII, not MTZ — use the original file as template
        # gemmi doesn't have write_xds_ascii, so we write a corrected MTZ instead
        mtz_path = output_hkl
        if not mtz_path.endswith('.mtz'):
            mtz_path = mtz_path.rsplit('.', 1)[0] + '.mtz' if '.' in os.path.basename(mtz_path) else mtz_path + '.mtz'
        mtz_out.write_to_file(mtz_path)
        output_size = os.path.getsize(mtz_path)
    except Exception as e:
        return {"success": False, "message": "Cannot write output: " + str(e)}

    return {
        "success": True,
        "input_file": input_hkl,
        "output_file": mtz_path,
        "output_size": output_size,
        "n_reflections": n_refl,
        "spacegroup": sg.xhm() if sg else "unknown",
        "cell": cell_params,
        "polarization": p,
        "normal": list(normal),
        "intensity_change": {
            "mean_ratio": round(mean_ratio, 6),
            "std_ratio": round(std_ratio, 6),
            "min_ratio": round(min_ratio, 6),
            "max_ratio": round(max_ratio, 6),
        },
        "before": before_stats,
        "after": after_stats,
    }


# ---------------------------------------------------------------------------
# Anisotropy analysis — per-axis resolution statistics from XDS_ASCII.HKL
#
# Computes I/σ, CC½, and Wilson B-factor along principal reciprocal-space
# axes (a*, b*, c*) to diagnose diffraction anisotropy.
#
# References:
#   - Strong et al. (2006) PNAS 103, 8060–8065  (anisotropy correction)
#   - Tickle et al. (2018) Acta Cryst. D74, 1095–1107 (STARANISO method)
#   - Popov & Bourenkov (2003) Acta Cryst. D59, 1145–1153
# ---------------------------------------------------------------------------

def analyze_anisotropy(input_hkl, n_shells=15):
    """Analyse diffraction anisotropy from XDS_ASCII.HKL.

    Projects each reflection onto the principal reciprocal-space axes
    (a*, b*, c*) and computes per-axis resolution statistics.

    Requires: gemmi, numpy.

    Args:
        input_hkl: path to XDS_ASCII.HKL
        n_shells:  number of resolution bins per axis (default 15)

    Returns:
        dict with keys:
          success (bool), message (str),
          cell (list), spacegroup (str),
          per_axis (dict of 'a_star','b_star','c_star' each containing
                    list of shell dicts with d_min, d_max, mean_i_sigma, cc_half),
          b_factors (dict with a_star, b_star, c_star Wilson B per axis),
          b_iso (float — isotropic Wilson B for comparison),
          fractional_anisotropy (float — 0=isotropic, 1=fully anisotropic),
          delta_b (dict with pairwise B differences),
          recommendation (str)
    """
    import gemmi
    import numpy as np
    from pathlib import Path
    import math

    input_hkl = str(input_hkl)
    if not Path(input_hkl).exists():
        return {"success": False, "message": "XDS_ASCII.HKL not found: " + input_hkl}

    try:
        xds = gemmi.read_xds_ascii(input_hkl)
    except Exception as e:
        return {"success": False, "message": "Cannot read HKL file: " + str(e)}

    if xds.data_size < 100:
        return {"success": False, "message": "Too few reflections for anisotropy analysis"}

    sg, cell, cell_params = _xds_sg_cell(xds)
    sg_name = sg.xhm() if sg else "unknown"

    # ── Extract reflection data as numpy arrays ──
    # gemmi XdsAscii stores h,k,l,iobs,sigma per reflection
    try:
        # Try modern gemmi API first
        if hasattr(xds, 'miller_array'):
            hkl = np.array(xds.miller_array, dtype=np.int32)
        elif hasattr(gemmi, 'Intensities'):
            intens = gemmi.Intensities()
            intens.import_xds(xds)
            hkl = np.array(intens.miller_array, dtype=np.int32)
        else:
            return {"success": False, "message": "gemmi version too old for anisotropy analysis"}
    except Exception as e:
        return {"success": False, "message": "Cannot extract HKL data: " + str(e)}

    n_refl = len(hkl)
    if n_refl < 100:
        return {"success": False, "message": "Too few reflections (" + str(n_refl) + ")"}

    # Get intensity and sigma arrays
    try:
        if hasattr(xds, 'iobs_array'):
            iobs = np.array(xds.iobs_array, dtype=np.float64)
            sigma = np.array(xds.sigma_array, dtype=np.float64)
        elif hasattr(gemmi, 'Intensities'):
            intens = gemmi.Intensities()
            intens.import_xds(xds)
            iobs = np.array(intens.value_array, dtype=np.float64)
            sigma = np.array(intens.sigma_array, dtype=np.float64)
        else:
            return {"success": False, "message": "Cannot extract intensity data"}
    except Exception as e:
        return {"success": False, "message": "Cannot extract intensities: " + str(e)}

    # ── Compute reciprocal-space metric tensor ──
    # G* = (a* b* c*) orthogonalization matrix
    a, b, c = cell.a, cell.b, cell.c
    al, be, ga = math.radians(cell.alpha), math.radians(cell.beta), math.radians(cell.gamma)

    # Reciprocal cell parameters
    vol = cell.volume
    if vol < 1e-6:
        return {"success": False, "message": "Invalid unit cell (zero volume)"}

    sa, sb, sg_ = math.sin(al), math.sin(be), math.sin(ga)
    ca, cb, cg = math.cos(al), math.cos(be), math.cos(ga)

    a_star = b * c * sa / vol
    b_star = a * c * sb / vol
    c_star = a * b * sg_ / vol

    # Compute d-spacing for each reflection
    d_arr = np.array([cell.calculate_d(h) for h in hkl], dtype=np.float64)

    # ── Classify reflections by dominant axis ──
    # Use fractional Miller index contribution to determine which axis
    # a reflection is most aligned with.
    # For a reflection (h,k,l), the fractional contributions to 1/d² from
    # each axis direction are computed using the metric tensor.
    # We use a simplified projection: compute the component of 1/d² along
    # each reciprocal axis.

    h_arr = hkl[:, 0].astype(np.float64)
    k_arr = hkl[:, 1].astype(np.float64)
    l_arr = hkl[:, 2].astype(np.float64)

    # Reciprocal metric tensor elements (for the squared contributions)
    # 1/d² = h²a*² + k²b*² + l²c*² + cross terms
    # We attribute the "axis contribution" using only the diagonal terms
    # to classify reflections.
    comp_a = (h_arr * a_star) ** 2
    comp_b = (k_arr * b_star) ** 2
    comp_c = (l_arr * c_star) ** 2
    comp_total = comp_a + comp_b + comp_c
    # Avoid division by zero
    comp_total = np.where(comp_total > 0, comp_total, 1.0)

    frac_a = comp_a / comp_total
    frac_b = comp_b / comp_total
    frac_c = comp_c / comp_total

    # Classify: a reflection belongs to axis X if frac_X > threshold
    # Use 0.5 — reflection is "predominantly" along that axis
    CONE_THRESH = 0.5
    mask_a = frac_a >= CONE_THRESH
    mask_b = frac_b >= CONE_THRESH
    mask_c = frac_c >= CONE_THRESH

    # Filter out bad data
    valid = (sigma > 0) & (d_arr > 0) & np.isfinite(iobs) & np.isfinite(sigma)

    # ── Compute per-axis shell statistics ──
    def _axis_shells(mask, d_vals, i_vals, s_vals, n_bins):
        """Compute resolution shell statistics for a subset of reflections."""
        sel = mask & valid
        if np.sum(sel) < 20:
            return [], None

        ds = d_vals[sel]
        iv = i_vals[sel]
        sv = s_vals[sel]

        # Bin by 1/d² for even shell spacing
        inv_d2 = 1.0 / (ds * ds)
        lo, hi = np.min(inv_d2), np.max(inv_d2)
        if hi - lo < 1e-9:
            return [], None

        edges = np.linspace(lo, hi, n_bins + 1)
        bin_idx = np.digitize(inv_d2, edges) - 1
        bin_idx = np.clip(bin_idx, 0, n_bins - 1)

        shells = []
        all_ln_i = []
        all_ss = []  # sin²θ/λ² = 1/(4d²)

        for bi in range(n_bins):
            bm = bin_idx == bi
            n_in = int(np.sum(bm))
            if n_in < 3:
                shells.append({
                    "d_max": round(1.0 / math.sqrt(edges[bi]) if edges[bi] > 0 else 999, 3),
                    "d_min": round(1.0 / math.sqrt(edges[bi + 1]) if edges[bi + 1] > 0 else 0.1, 3),
                    "n_refl": n_in,
                    "mean_i_sigma": None,
                    "cc_half": None,
                })
                continue

            bi_i = iv[bm]
            bi_s = sv[bm]
            bi_d = ds[bm]

            # Mean I/σ
            i_over_sig = bi_i / bi_s
            mean_isig = float(np.mean(i_over_sig))

            # CC½ via random half-dataset split
            cc_half = None
            if n_in >= 10:
                try:
                    perm = np.random.permutation(n_in)
                    half1 = bi_i[perm[:n_in // 2]]
                    half2 = bi_i[perm[n_in // 2:2 * (n_in // 2)]]
                    if len(half1) >= 5 and len(half2) >= 5:
                        mn = min(len(half1), len(half2))
                        h1 = half1[:mn]
                        h2 = half2[:mn]
                        c12 = np.corrcoef(h1, h2)[0, 1]
                        if np.isfinite(c12):
                            cc_half = round(float(c12) * 100, 1)
                except Exception:
                    pass

            d_max = round(1.0 / math.sqrt(edges[bi]) if edges[bi] > 0 else 999, 3)
            d_min = round(1.0 / math.sqrt(edges[bi + 1]) if edges[bi + 1] > 0 else 0.1, 3)

            shells.append({
                "d_max": d_max,
                "d_min": d_min,
                "n_refl": n_in,
                "mean_i_sigma": round(mean_isig, 2),
                "cc_half": cc_half,
            })

            # Collect for Wilson B fit
            pos_mask = bi_i > 0
            if np.sum(pos_mask) >= 3:
                ln_mean_i = math.log(float(np.mean(bi_i[pos_mask])))
                mid_inv_d2 = (edges[bi] + edges[bi + 1]) / 2.0
                ss = mid_inv_d2 / 4.0  # sin²θ/λ²
                all_ln_i.append(ln_mean_i)
                all_ss.append(ss)

        # Wilson B from linear fit: ln(<I>) = A - 2B·sin²θ/λ²
        b_factor = None
        if len(all_ss) >= 3:
            try:
                ss_arr = np.array(all_ss)
                ln_arr = np.array(all_ln_i)
                # Linear regression: ln_I = intercept + slope * ss
                # slope = -2B, so B = -slope/2
                A = np.vstack([ss_arr, np.ones(len(ss_arr))]).T
                result = np.linalg.lstsq(A, ln_arr, rcond=None)
                slope = result[0][0]
                b_factor = round(-slope / 2.0, 2)
            except Exception:
                pass

        return shells, b_factor

    # Set random seed for reproducible CC½
    np.random.seed(42)

    axis_results = {}
    b_factors = {}

    for axis_name, mask in [("a_star", mask_a), ("b_star", mask_b), ("c_star", mask_c)]:
        shells, b_fac = _axis_shells(mask, d_arr, iobs, sigma, n_shells)
        axis_results[axis_name] = shells
        b_factors[axis_name] = b_fac

    # ── Isotropic Wilson B for comparison ──
    _, b_iso = _axis_shells(np.ones(n_refl, dtype=bool), d_arr, iobs, sigma, n_shells)

    # ── Compute anisotropy metrics ──
    valid_b = {k: v for k, v in b_factors.items() if v is not None}

    fractional_anisotropy = None
    delta_b = {}
    recommendation = "Insufficient data for anisotropy assessment."

    if len(valid_b) >= 2:
        b_vals = list(valid_b.values())
        b_max = max(b_vals)
        b_min = min(b_vals)
        b_mean = sum(b_vals) / len(b_vals)

        if b_mean > 0:
            fractional_anisotropy = round((b_max - b_min) / b_mean, 3)
        else:
            fractional_anisotropy = 0.0

        # Pairwise ΔB
        axes = list(valid_b.keys())
        for i_ax in range(len(axes)):
            for j_ax in range(i_ax + 1, len(axes)):
                key = axes[i_ax] + "_vs_" + axes[j_ax]
                delta_b[key] = round(abs(valid_b[axes[i_ax]] - valid_b[axes[j_ax]]), 2)

        # Per-axis effective resolution (where I/σ drops below 2.0)
        eff_res = {}
        for ax_name, shells in axis_results.items():
            last_good = None
            for sh in shells:
                if sh["mean_i_sigma"] is not None and sh["mean_i_sigma"] >= 2.0:
                    last_good = sh["d_min"]
            eff_res[ax_name] = last_good

        # ── Recommendation ──
        if fractional_anisotropy is not None:
            if fractional_anisotropy < 0.25:
                recommendation = ("Isotropic — fractional anisotropy {:.2f}. "
                                  "Standard isotropic resolution cutoff is appropriate."
                                  ).format(fractional_anisotropy)
            elif fractional_anisotropy < 0.5:
                recommendation = ("Mild anisotropy detected (FA = {:.2f}). "
                                  "Consider anisotropic truncation (STARANISO) to retain "
                                  "stronger data along the best-diffracting axis while "
                                  "removing noise along the worst."
                                  ).format(fractional_anisotropy)
            else:
                recommendation = ("Severe anisotropy (FA = {:.2f}). "
                                  "Strongly recommend anisotropic truncation via STARANISO. "
                                  "An isotropic cutoff will either discard good data along the "
                                  "best axis or include noise along the worst axis."
                                  ).format(fractional_anisotropy)

            # Add effective resolution info
            res_parts = []
            for ax_name in ["a_star", "b_star", "c_star"]:
                r = eff_res.get(ax_name)
                label = ax_name.replace("_star", "*").replace("_", "")
                if r is not None:
                    res_parts.append("{}: {:.2f} Å".format(label, r))
                else:
                    res_parts.append("{}: N/A".format(label))
            if res_parts:
                recommendation += " Effective resolution (I/σ ≥ 2): " + ", ".join(res_parts) + "."

    # Count reflections per axis
    axis_counts = {
        "a_star": int(np.sum(mask_a & valid)),
        "b_star": int(np.sum(mask_b & valid)),
        "c_star": int(np.sum(mask_c & valid)),
        "unassigned": int(np.sum(~(mask_a | mask_b | mask_c) & valid)),
        "total": int(np.sum(valid)),
    }

    return {
        "success": True,
        "message": "Anisotropy analysis complete",
        "cell": cell_params,
        "spacegroup": sg_name,
        "per_axis": axis_results,
        "b_factors": b_factors,
        "b_iso": b_iso,
        "fractional_anisotropy": fractional_anisotropy,
        "delta_b": delta_b,
        "recommendation": recommendation,
        "axis_counts": axis_counts,
        "n_shells": n_shells,
    }
