class LPParser:
    """Parse XDS .LP files for key metrics"""
    
    @staticmethod
    def parse_idxref(lp_content):
        """Extract key metrics from IDXREF.LP"""
        metrics = {}
        lines = lp_content.split('\n')
        
        # Find SUBTREE and POPULATION
        for i, line in enumerate(lines):
            if 'SUBTREE' in line and 'POPULATION' in line:
                # Skip blank or separator lines after the header to find data
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line or next_line.startswith('-'):
                        continue
                    parts = next_line.split()
                    if len(parts) >= 2:
                        try:
                            metrics['subtree'] = int(parts[0])
                            metrics['population'] = int(parts[1])
                        except (ValueError, IndexError):
                            pass
                    break
        
        # Find indexed spots and parse numbers
        for line in lines:
            if 'OUT OF' in line and 'SPOTS INDEXED' in line:
                metrics['indexed_spots'] = line.strip()
                import re
                m_idx = re.search(r'(\d+)\s+OUT OF\s+(\d+)', line)
                if m_idx:
                    metrics['indexed_count'] = int(m_idx.group(1))
                    metrics['total_spots'] = int(m_idx.group(2))
                break

        # Standard deviations of spot and spindle positions
        # XDS outputs these as e.g.:
        #   STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     1.34
        # Some versions include '=' before the value, some do not.
        # Strategy: try '= value' first, fall back to last token on line.
        for line in lines:
            if 'STANDARD DEVIATION OF SPOT' in line and 'POSITION' in line:
                parts = line.strip().split()
                found = False
                for j, p in enumerate(parts):
                    if p == '=' and j + 1 < len(parts):
                        try:
                            metrics['sigma_spot'] = float(parts[j+1])
                            found = True
                        except Exception:
                            pass
                        break
                if not found and parts:
                    try: metrics['sigma_spot'] = float(parts[-1])
                    except Exception: pass
            if 'STANDARD DEVIATION OF SPINDLE' in line and 'POSITION' in line:
                parts = line.strip().split()
                found = False
                for j, p in enumerate(parts):
                    if p == '=' and j + 1 < len(parts):
                        try:
                            metrics['sigma_spindle'] = float(parts[j+1])
                            found = True
                        except Exception:
                            pass
                        break
                if not found and parts:
                    try: metrics['sigma_spindle'] = float(parts[-1])
                    except Exception: pass

        # Refined beam center and detector distance
        # These appear in the "REFINEMENT" section near the end
        # We want the LAST occurrence (final refined values)
        for line in lines:
            if 'ORGX=' in line and 'ORGY=' in line:
                parts = line.strip().split()
                for j, p in enumerate(parts):
                    if p == 'ORGX=' and j + 1 < len(parts):
                        try: metrics['orgx'] = float(parts[j+1])
                        except Exception: pass
                    if p == 'ORGY=' and j + 1 < len(parts):
                        try: metrics['orgy'] = float(parts[j+1])
                        except Exception: pass
            if 'DETECTOR_DISTANCE=' in line:
                parts = line.strip().split()
                for j, p in enumerate(parts):
                    if p == 'DETECTOR_DISTANCE=' and j + 1 < len(parts):
                        try: metrics['detector_distance'] = float(parts[j+1])
                        except Exception: pass

        # The ORGX=/DETECTOR_DISTANCE= lines above are only the echo of the input
        # parameters; the refined values are printed as "DETECTOR ORIGIN (PIXELS) AT"
        # and "CRYSTAL TO DETECTOR DISTANCE (mm)" - the last occurrence wins.
        for line in lines:
            if 'DETECTOR ORIGIN (PIXELS) AT' in line:
                nums = line.split('AT', 1)[1].split()
                try:
                    metrics['orgx'], metrics['orgy'] = float(nums[0]), float(nums[1])
                except (ValueError, IndexError):
                    pass
            elif 'CRYSTAL TO DETECTOR DISTANCE (mm)' in line:
                try:
                    metrics['detector_distance'] = float(line.split(')', 1)[1].split()[0])
                except (ValueError, IndexError):
                    pass

        # Initial beam center and distance (from input parameters, first occurrence)
        # These appear early in the file before refinement
        initial_org_found = False
        initial_dist_found = False
        for line in lines:
            if not initial_org_found and 'ORGX=' in line and 'ORGY=' in line:
                parts = line.strip().split()
                for j, p in enumerate(parts):
                    if p == 'ORGX=' and j + 1 < len(parts):
                        try: metrics['orgx_initial'] = float(parts[j+1])
                        except Exception: pass
                    if p == 'ORGY=' and j + 1 < len(parts):
                        try: metrics['orgy_initial'] = float(parts[j+1])
                        except Exception: pass
                initial_org_found = True
            if not initial_dist_found and 'DETECTOR_DISTANCE=' in line:
                parts = line.strip().split()
                for j, p in enumerate(parts):
                    if p == 'DETECTOR_DISTANCE=' and j + 1 < len(parts):
                        try: metrics['detector_distance_initial'] = float(parts[j+1])
                        except Exception: pass
                initial_dist_found = True

        # Find selected lattice (line with * in Bravais lattice table)
        in_lattice_table = False
        lattices = []
        for line in lines:
            if 'LATTICE-  BRAVAIS-   QUALITY' in line:
                in_lattice_table = True
                continue
            if in_lattice_table:
                stripped = line.strip()
                if stripped.startswith('*'):
                    parts = stripped.split()
                    if len(parts) >= 9:
                        lattices.append({
                            'character': parts[1],
                            'bravais': parts[2],
                            'quality': parts[3],
                            'a': parts[4],
                            'b': parts[5],
                            'c': parts[6],
                            'alpha': parts[7],
                            'beta': parts[8],
                            'gamma': parts[9] if len(parts) > 9 else parts[8]
                        })
                elif stripped == '' or (stripped and not stripped[0].isdigit() and stripped[0] != '*'):
                    if lattices:
                        break
        
        if lattices:
            metrics['lattices'] = lattices
        
        return metrics
    
    @staticmethod
    def parse_idxref_quick(lp_content):
        """Fast lightweight IDXREF.LP parser for auto-indexing trials.

        Returns dict with: indexed_count, total_spots, indexed_fraction,
        sigma_spot, sigma_spindle, mosaicity, error_type, subtrees.
        Designed to be called many times quickly during auto-index search.
        """
        import re
        result = {
            'indexed_count': 0, 'total_spots': 0, 'indexed_fraction': 0.0,
            'sigma_spot': None, 'sigma_spindle': None, 'mosaicity': None,
            'error_type': None, 'success': False, 'subtrees': [],
            'index_origins': [],     # INDEX_ORIGIN alternatives from IDXREF
            'selected_origin': None, # the origin IDXREF actually chose
        }
        lines = lp_content.split('\n')

        # -- Detect error type -------------------------------------------
        for line in lines:
            if '!!! ERROR !!!' in line or '!!! ERROR IN' in line:
                upper = line.upper()
                if 'INSUFFICIENT PERCENTAGE' in upper:
                    result['error_type'] = 'insufficient_indexed'
                elif 'CANNOT INDEX' in upper or 'NO SOLUTION' in upper:
                    result['error_type'] = 'no_solution'
                else:
                    result['error_type'] = 'unknown'
                break

        # -- Indexed spots -----------------------------------------------
        for line in lines:
            if 'OUT OF' in line and 'SPOTS INDEXED' in line:
                m = re.search(r'(\d+)\s+OUT OF\s+(\d+)', line)
                if m:
                    result['indexed_count'] = int(m.group(1))
                    result['total_spots'] = int(m.group(2))
                    if result['total_spots'] > 0:
                        result['indexed_fraction'] = result['indexed_count'] / result['total_spots']
                break

        # -- Subtree populations (for multiple lattice detection) --------
        for i, line in enumerate(lines):
            if 'SUBTREE' in line and 'POPULATION' in line:
                for j in range(i + 1, min(i + 15, len(lines))):
                    stripped = lines[j].strip()
                    if not stripped or stripped.startswith('-'):
                        continue
                    parts = stripped.split()
                    if len(parts) >= 2:
                        try:
                            result['subtrees'].append({
                                'id': int(parts[0]),
                                'population': int(parts[1])
                            })
                        except ValueError:
                            break
                    else:
                        break
                break

        # -- RMSD values -------------------------------------------------
        for line in lines:
            if 'STANDARD DEVIATION OF SPOT' in line and 'POSITION' in line:
                parts = line.strip().split()
                for j, p in enumerate(parts):
                    if p == '=' and j + 1 < len(parts):
                        try: result['sigma_spot'] = float(parts[j+1])
                        except Exception: pass
                        break
                if result['sigma_spot'] is None and parts:
                    try: result['sigma_spot'] = float(parts[-1])
                    except Exception: pass
            if 'STANDARD DEVIATION OF SPINDLE' in line and 'POSITION' in line:
                parts = line.strip().split()
                for j, p in enumerate(parts):
                    if p == '=' and j + 1 < len(parts):
                        try: result['sigma_spindle'] = float(parts[j+1])
                        except Exception: pass
                        break
                if result['sigma_spindle'] is None and parts:
                    try: result['sigma_spindle'] = float(parts[-1])
                    except Exception: pass

        # -- Crystal mosaicity -------------------------------------------
        for line in lines:
            if 'CRYSTAL MOSAICITY' in line and 'DEGREES' in line:
                parts = line.strip().split()
                for j, p in enumerate(parts):
                    if p == '=' and j + 1 < len(parts):
                        try: result['mosaicity'] = float(parts[j+1])
                        except Exception: pass
                        break
                if result['mosaicity'] is None and parts:
                    try: result['mosaicity'] = float(parts[-1])
                    except Exception: pass

        # -- INDEX_ORIGIN alternatives table -----------------------------
        # The table appears after "SELECTION OF THE INDEX ORIGIN" header.
        # Format:  h  k  l  QUALITY  DELTA  XD  YD  X  Y  Z  DH  DK  DL
        # (3 ints + 10 floats = 13 tokens per data row)
        # Ends at "SELECTED:" line.
        for i, line in enumerate(lines):
            if 'SELECTION OF THE INDEX ORIGIN' in line:
                # Scan forward for data rows (skip header lines)
                for j in range(i + 1, min(i + 50, len(lines))):
                    row = lines[j].strip()
                    if not row:
                        continue
                    if row.startswith('SELECTED'):
                        # Parse: SELECTED:    INDEX_ORIGIN=  h  k  l
                        sel_parts = row.split('=')
                        if len(sel_parts) >= 2:
                            hkl_parts = sel_parts[-1].strip().split()
                            if len(hkl_parts) >= 3:
                                try:
                                    result['selected_origin'] = [
                                        int(hkl_parts[0]),
                                        int(hkl_parts[1]),
                                        int(hkl_parts[2]),
                                    ]
                                except ValueError:
                                    pass
                        break
                    # Data rows have 13 tokens: h k l QUALITY DELTA
                    # XD YD X Y Z DH DK DL
                    tokens = row.split()
                    if len(tokens) < 13:
                        continue
                    try:
                        h, k, l = int(tokens[0]), int(tokens[1]), int(tokens[2])
                        quality = float(tokens[3])
                        delta = float(tokens[4])
                        dh = float(tokens[10])
                        dk = float(tokens[11])
                        dl = float(tokens[12])
                        result['index_origins'].append({
                            'origin': [h, k, l],
                            'quality': quality,
                            'delta': delta,
                            'dh': dh, 'dk': dk, 'dl': dl,
                        })
                    except (ValueError, IndexError):
                        continue
                break

        # -- Determine success -------------------------------------------
        if result['error_type'] is None and result['indexed_fraction'] >= 0.5:
            result['success'] = True
        elif result['error_type'] is None and result['indexed_fraction'] > 0:
            # No error but low fraction — partial success
            result['success'] = False

        return result

    @staticmethod
    def parse_colspot_quick(lp_content):
        """Fast COLSPOT.LP parser for auto-indexing trials.

        Returns dict with: total_spots, signal_pixel, n_images_scanned,
        spots_per_image (average NSTRONG per frame).
        """
        result = {
            'total_spots': 0, 'signal_pixel': None,
            'n_images_scanned': 0, 'spots_per_image': 0.0,
        }
        # Parse per-image table for NSTRONG
        image_nstrong = []
        in_table = False
        for line in lp_content.splitlines():
            stripped = line.strip()
            upper = stripped.upper()
            # Total spots — match any line with "NUMBER OF DIFFRACTION SPOTS"
            # XDS versions use: LOCATED, ACCEPTED, SAVED
            # We want the last such line (ACCEPTED comes after LOCATED)
            if 'NUMBER OF DIFFRACTION SPOTS' in upper:
                parts = stripped.split()
                for p in reversed(parts):
                    try:
                        result['total_spots'] = int(p)
                        break
                    except ValueError:
                        continue
            # SIGNAL_PIXEL
            if upper.startswith('SIGNAL_PIXEL') and '=' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    try:
                        result['signal_pixel'] = float(parts[-1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
            # Per-image NSTRONG table
            if 'FRAME #' in upper or 'FRAME#' in upper.replace(' ', ''):
                in_table = True
                continue
            if in_table:
                parts = stripped.split()
                if len(parts) >= 3:
                    try:
                        frame = int(parts[0])
                        nstrong = int(parts[2])
                        if 0 < frame < 100000:
                            image_nstrong.append(nstrong)
                    except (ValueError, IndexError):
                        if image_nstrong:
                            in_table = False
                elif stripped == '' and image_nstrong:
                    in_table = False

        result['n_images_scanned'] = len(image_nstrong)
        if image_nstrong:
            result['spots_per_image'] = sum(image_nstrong) / len(image_nstrong)
        return result

    @staticmethod
    def parse_correct(lp_content):
        """Extract key metrics from CORRECT.LP"""
        metrics = {}
        lines = lp_content.split('\n')

        # Detect FRIEDEL'S_LAW setting used in CORRECT
        # Match multiple patterns found across XDS versions:
        #   "FRIEDEL'S_LAW=         FALSE"  (parameter echo near top)
        #   "CORRECTIONS ACTIVE   ACTIVE  FRIEDEL'S_LAW=  FALSE"
        #   "CALCULATIONS ASSUME FRIEDEL'S_LAW= TRUE"  (older versions)
        for line in lines:
            if "FRIEDEL'S_LAW=" in line:
                after = line.split("FRIEDEL'S_LAW=")[1].strip().split()[0]
                if after.startswith('TRUE'):
                    metrics['friedels_law'] = 'TRUE'
                elif after.startswith('FALSE'):
                    metrics['friedels_law'] = 'FALSE'
                if 'friedels_law' in metrics:
                    break
        
        # Find space group and unit cell
        for i, line in enumerate(lines):
            if 'SPACE_GROUP_NUMBER=' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    try:
                        metrics['space_group'] = int(parts[1].strip())
                    except Exception:
                        pass
            
            if 'UNIT_CELL_CONSTANTS=' in line:
                # Extract unit cell values
                parts = line.split('=')[1].strip().split()
                if len(parts) >= 6:
                    try:
                        metrics['unit_cell'] = {
                            'a': float(parts[0]),
                            'b': float(parts[1]),
                            'c': float(parts[2]),
                            'alpha': float(parts[3]),
                            'beta': float(parts[4]),
                            'gamma': float(parts[5])
                        }
                    except Exception:
                        pass
        
        # Find statistics table (bottom/LAST table with SUBSET OF INTENSITY DATA)
        all_tables = []
        current_table = []
        in_stats_table = False
        header_line = None
        blank_count = 0
        
        for i, line in enumerate(lines):
            if 'SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE' in line:
                # Start of a new table - save previous if exists
                if current_table:
                    all_tables.append(current_table)
                current_table = []
                in_stats_table = True
                header_line = i + 1
                blank_count = 0
                continue
            
            if in_stats_table:
                # Skip the header lines
                if header_line and i <= header_line + 1:
                    continue
                
                stripped = line.strip()
                # Blank line: allow up to 2 blank lines before total row
                if stripped == '':
                    if current_table:
                        blank_count += 1
                        if blank_count > 2:
                            in_stats_table = False
                    continue
                
                # Check if this is a data row or total row
                first_token = stripped.split()[0]
                is_data = first_token[0].replace('.', '').replace('-', '').isdigit() or first_token.lower() == 'total'
                if not is_data:
                    if current_table:
                        in_stats_table = False
                    continue
                
                blank_count = 0
                # Parse data row
                parts = stripped.split()
                if len(parts) >= 11:
                    try:
                        current_table.append({
                            'resolution': parts[0],
                            'observed': parts[1],
                            'unique': parts[2],
                            'possible': parts[3],
                            'completeness': parts[4],
                            'r_obs': parts[5],
                            'r_exp': parts[6],
                            'compared': parts[7],
                            'i_sigma': parts[8],
                            'r_meas': parts[9],
                            'cc_half': parts[10],
                            'anomal_corr': parts[11] if len(parts) > 11 else '',
                            'siganom': parts[12] if len(parts) > 12 else '',
                            'nano': parts[13] if len(parts) > 13 else ''
                        })
                    except Exception:
                        pass
        
        # Add the last table if exists
        if current_table:
            all_tables.append(current_table)
        
        # Use the LAST table
        if all_tables:
            metrics['statistics_table'] = all_tables[-1]
            metrics['cutoffs'] = LPParser.determine_resolution_cutoff(all_tables[-1])

        # Extract the actual low-resolution limit from the
        # "RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR ..." table.
        # That table has two resolution columns per row (low  high),
        # e.g.  "19.920   9.533   16.70  ...".
        # The first data row's first column is the true low-resolution limit.
        for i, line in enumerate(lines):
            if 'RESOLUTION RANGE' in line and 'I/Sigma' in line and 'Chi' in line:
                # Skip 1-2 header/sub-header lines ("observed  expected")
                for j in range(i + 1, min(i + 4, len(lines))):
                    row = lines[j].strip()
                    if not row:
                        continue
                    # Skip sub-header lines (contain letters like "observed")
                    if any(c.isalpha() for c in row):
                        continue
                    # First all-numeric data row
                    parts = row.split()
                    if len(parts) >= 2:
                        try:
                            lo = float(parts[0])
                            metrics['resolution_range_low'] = round(lo, 3)
                        except (ValueError, IndexError):
                            pass
                    break

        # Extract ISa (a, b, ISa from error model)
        # CORRECT.LP has two possible formats:
        #   a        b          ISa              (summary)
        #   a        b          ISa    ISa0   INPUT DATA SET  (per-dataset)
        # We want the ISa value from whichever format appears.
        for i, line in enumerate(lines):
            stripped = line.strip()
            if ('ISa' in stripped and
                    stripped.replace(' ', '').startswith('ab') and
                    'ISa' in stripped):
                # Next non-empty line has the values
                for j in range(i + 1, min(i + 5, len(lines))):
                    row = lines[j].strip()
                    if not row:
                        continue
                    parts = row.split()
                    if len(parts) >= 3:
                        try:
                            float(parts[0])
                            metrics['isa'] = {'a': parts[0], 'b': parts[1], 'isa': parts[2]}
                        except (ValueError, IndexError):
                            pass
                    break
                break

        # Extract CHI^2-VALUE OF FIT OF CORRECTION FACTORS (there are 3 in CORRECT.LP)
        # XDS may output "CHI^2-VALUE" or "CHI**2-VALUE" depending on version
        chi2_values = []
        for line in lines:
            if ('CHI^2-VALUE OF FIT' in line or 'CHI**2-VALUE OF FIT' in line
                    or 'CHI^2-VALUE  OF  FIT' in line):
                parts = line.strip().split()
                # Value is the last token on the line
                try:
                    chi2_values.append(float(parts[-1]))
                except (ValueError, IndexError):
                    pass
        if chi2_values:
            metrics['chi2_values'] = chi2_values

        # Extract refined beam center (ORGX, ORGY) from CORRECT.LP
        for line in lines:
            if 'DETECTOR ORIGIN (ACTIVE PIXEL UNITS) AT' in line or \
               ('ORGX=' in line and 'ORGY=' in line and 'DETECTOR' not in line):
                try:
                    parts = line.strip().split()
                    orgx_idx = None
                    orgy_idx = None
                    for k, p in enumerate(parts):
                        if p.startswith('ORGX='):
                            orgx_idx = k
                        elif p.startswith('ORGY='):
                            orgy_idx = k
                    if orgx_idx is not None and orgy_idx is not None:
                        ox = float(parts[orgx_idx].split('=')[1])
                        oy = float(parts[orgy_idx].split('=')[1])
                        metrics['refined_beam_center'] = {'orgx': ox, 'orgy': oy}
                except (ValueError, IndexError):
                    pass
        # ORGX=/ORGY= is the input echo; CORRECT prints the refined origin as
        # "DETECTOR ORIGIN (PIXELS) AT x y" - that one, the last, is the refined beam centre
        for line in lines:
            if 'DETECTOR ORIGIN (PIXELS) AT' in line:
                nums = line.split('AT', 1)[1].split()
                try:
                    metrics['refined_beam_center'] = {'orgx': float(nums[0]), 'orgy': float(nums[1])}
                except (ValueError, IndexError):
                    pass

        # ── Crystal mosaicity (refined value, last one printed) ────────
        # Format:  CRYSTAL MOSAICITY (DEGREES)     0.135
        for line in lines:
            if 'CRYSTAL MOSAICITY (DEGREES)' in line:
                try:
                    metrics['mosaicity'] = float(line.split()[-1])
                except (ValueError, IndexError):
                    pass

        # ── Wilson line (B-factor) ─────────────────────────────────────
        # Format: WILSON LINE (using all data) : A=   7.372  B=  20.624  CORRELATION=  0.98
        for line in lines:
            if 'WILSON LINE' in line and 'CORRELATION' in line:
                try:
                    wl = {}
                    for token in ['A=', 'B=', 'CORRELATION=']:
                        idx = line.index(token)
                        rest = line[idx + len(token):].strip().split()[0]
                        wl[token.rstrip('=').lower()] = float(rest)
                    metrics['wilson_line'] = wl
                except (ValueError, IndexError):
                    pass
                break

        # ── Wilson statistics table ────────────────────────────────────
        # Section: "WILSON STATISTICS OF DATA SET" followed by a table
        # Actual columns:  #  RES  SS  <I>  log(<I>)  BO
        wilson_table = []
        in_wilson = False
        wilson_header_passed = False
        for i, line in enumerate(lines):
            if 'WILSON STATISTICS OF DATA SET' in line:
                in_wilson = True
                wilson_header_passed = False
                continue
            if in_wilson:
                stripped = line.strip()
                if not stripped:
                    if wilson_table:
                        in_wilson = False
                    continue
                # Skip header/description lines: look for the column header line
                if '#' in stripped and 'RES' in stripped and 'SS' in stripped:
                    wilson_header_passed = True
                    continue
                # Also skip lines that are part of the description (contain letters but aren't data)
                if not wilson_header_passed:
                    continue
                parts = stripped.split()
                if len(parts) >= 5:
                    try:
                        int(parts[0])  # first col is # reflections (integer)
                        float(parts[1])  # second col is RES
                        wilson_table.append(parts)
                    except ValueError:
                        if wilson_table:
                            in_wilson = False
        if wilson_table:
            metrics['wilson_table_raw'] = wilson_table

        # ── Higher order moments of Wilson distribution ────────────────
        # Section: "HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF ACENTRIC DATA"
        # Actual header:  #  RES  <I**2>/2<I>**2  <I**3>/6<I>**3  <I**4>/24<I>**4
        moments_table = []
        in_moments = False
        moments_header_passed = False
        for i, line in enumerate(lines):
            if 'HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF ACENTRIC DATA' in line:
                in_moments = True
                moments_header_passed = False
                moments_table = []  # reset in case centric came first
                continue
            if in_moments:
                stripped = line.strip()
                if not stripped:
                    if moments_table:
                        in_moments = False
                    continue
                # Skip header lines: "AS COMPARED", column headers with #/RES/<I**2>, denominator line
                if 'COMPARED' in stripped or 'EXPECTED' in stripped:
                    continue
                if '#' in stripped and 'RES' in stripped:
                    moments_header_passed = True
                    continue
                if '<I>' in stripped:
                    continue
                if not moments_header_passed:
                    continue
                parts = stripped.split()
                if len(parts) >= 4:
                    try:
                        int(parts[0])  # first col is # reflections
                        # second col is RES or 'overall'
                        if parts[1] != 'overall':
                            float(parts[1])
                        moments_table.append(parts)
                    except ValueError:
                        if moments_table:
                            in_moments = False
        if moments_table:
            metrics['wilson_moments'] = moments_table

        # ── Alien reflections (Wilson outliers) ────────────────────────
        # Format:  h  k  l  RES  Z  Intensity  Sigma  "alien"
        # Example:  56   22  -21    1.18  314.73  0.1593E+05  0.4012E+04 "alien"
        aliens = []
        for line in lines:
            stripped = line.strip()
            if '"alien"' in stripped or stripped.endswith('alien'):
                parts = stripped.replace('"alien"', '').replace('alien', '').strip().split()
                if len(parts) >= 5:
                    try:
                        h, k, l = int(parts[0]), int(parts[1]), int(parts[2])
                        res = float(parts[3])
                        z_val = float(parts[4])
                        aliens.append({'h': h, 'k': k, 'l': l, 'res': res, 'z': z_val})
                    except (ValueError, IndexError):
                        pass
        if aliens:
            metrics['aliens'] = aliens

        # ── Space group decision table ─────────────────────────────────
        # CORRECT.LP contains a table comparing point groups:
        #  SPACE-GROUP        UNIT CELL CONSTANTS            UNIQUE  Rmeas  COMPARED  LATTICE-
        #   NUMBER     a      b      c   alpha  beta  gamma                          CHARACTER
        #     1       74.1   78.6  124.0  71.8  74.8  90.4    6959   22.5    5309    31 aP     *
        sg_table = []
        in_sg_table = False
        sg_header_seen = False
        for i, line in enumerate(lines):
            if 'SPACE-GROUP' in line and 'UNIT CELL CONSTANTS' in line and 'UNIQUE' in line:
                in_sg_table = True
                sg_header_seen = False
                continue
            if in_sg_table:
                stripped = line.strip()
                if not stripped:
                    if sg_table:
                        in_sg_table = False
                    continue
                if 'NUMBER' in stripped and ('alpha' in stripped or 'gamma' in stripped):
                    sg_header_seen = True
                    continue
                if not sg_header_seen:
                    continue
                parts = stripped.split()
                if len(parts) >= 10:
                    try:
                        sg_num = int(parts[0])
                        a_v = float(parts[1]); b_v = float(parts[2]); c_v = float(parts[3])
                        al_v = float(parts[4]); be_v = float(parts[5]); ga_v = float(parts[6])
                        unique = int(parts[7]); rmeas = float(parts[8]); compared = int(parts[9])
                        selected = '*' in stripped
                        latt_char = parts[10] if len(parts) >= 11 else ''
                        bravais = parts[11] if len(parts) >= 12 else ''
                        sg_table.append({
                            'sg_number': sg_num,
                            'unit_cell': [a_v, b_v, c_v, al_v, be_v, ga_v],
                            'unique': unique, 'rmeas': rmeas, 'compared': compared,
                            'lattice_character': latt_char, 'bravais': bravais,
                            'selected': selected
                        })
                    except (ValueError, IndexError):
                        if sg_table:
                            in_sg_table = False
                else:
                    if sg_table:
                        in_sg_table = False
        if sg_table:
            metrics['sg_decision_table'] = sg_table

        # ── Systematic absences along principal axes ───────────────────
        # Table: "REFLECTIONS OF TYPE H,0,0  0,K,0  0,0,L OR EXPECTED TO BE ABSENT (*)"
        # Columns vary by XDS version. Common formats:
        #   H  K  L  RESOLUTION  INTENSITY  SIGMA  [*]
        #   H  K  L  RESOLUTION  INTENSITY  SIGMA  INTENSITY/SIGMA  #OBSERVED [*]
        sysabs = []
        in_sysabs = False
        sysabs_header_passed = False
        for i, line in enumerate(lines):
            if 'REFLECTIONS OF TYPE' in line and '0,0,L' in line:
                in_sysabs = True
                sysabs_header_passed = False
                sysabs = []
                continue
            if in_sysabs:
                stripped = line.strip()
                if not stripped:
                    if sysabs:
                        in_sysabs = False
                    continue
                if stripped.startswith('---'):
                    continue
                if stripped.startswith('H') and 'K' in stripped and 'L' in stripped:
                    sysabs_header_passed = True
                    continue
                if not sysabs_header_passed:
                    continue
                has_star = '*' in stripped
                clean = stripped.replace('*', ' ').strip()
                parts = clean.split()
                if len(parts) >= 6:
                    try:
                        h = int(parts[0]); k = int(parts[1]); l = int(parts[2])
                        res = float(parts[3])
                        intensity_s = parts[4]
                        sigma_s = parts[5]
                        isig_s = parts[6] if len(parts) >= 7 else ''
                        nobs_s = parts[7] if len(parts) >= 8 else ''
                        # Parse I/sigma: use column if present, else compute
                        try:
                            isig_val = float(isig_s) if isig_s else None
                        except ValueError:
                            isig_val = None
                        if isig_val is None:
                            try:
                                iv = float(intensity_s); sv = float(sigma_s)
                                isig_val = iv / sv if sv > 0 else None
                            except (ValueError, ZeroDivisionError):
                                isig_val = None
                        sysabs.append({
                            'h': h, 'k': k, 'l': l, 'res': res,
                            'intensity': intensity_s, 'sigma': sigma_s,
                            'isig': round(isig_val, 2) if isig_val is not None else None,
                            'nobs': nobs_s,
                            'expected_absent': has_star
                        })
                    except (ValueError, IndexError):
                        if sysabs:
                            in_sysabs = False
                else:
                    if sysabs:
                        in_sysabs = False
        if sysabs:
            metrics['systematic_absences'] = sysabs

        # ── Per-axis screw axis pattern analysis ───────────────────────
        # Group reflections by axis (h00, 0k0, 00l), then for each axis
        # test periodicities 2,3,4,6. Compare mean |I/sigma| of
        # "should-be-absent" vs "allowed" index classes.
        if sysabs:
            axis_groups = {'h00': [], '0k0': [], '00l': []}
            for r in sysabs:
                if r['isig'] is None:
                    continue
                star = r.get('expected_absent', False)
                if r['k'] == 0 and r['l'] == 0 and r['h'] != 0:
                    axis_groups['h00'].append((abs(r['h']), r['isig'], star))
                elif r['h'] == 0 and r['l'] == 0 and r['k'] != 0:
                    axis_groups['0k0'].append((abs(r['k']), r['isig'], star))
                elif r['h'] == 0 and r['k'] == 0 and r['l'] != 0:
                    axis_groups['00l'].append((abs(r['l']), r['isig'], star))

            axis_analysis = {}
            for axis_name, refls in axis_groups.items():
                if len(refls) < 3:
                    continue
                # Test periodicities 2, 3, 4, 6
                # Detection uses multiple complementary criteria:
                # 1. Ratio of mean|I/σ| absent vs allowed (classic approach)
                # 2. Fraction of absent-class reflections that are weak (|I/σ| ≤ 2)
                # 3. Mean raw I/σ of absent class near zero (truly absent → symmetric around 0)
                # 4. Contrast: mean|I/σ| of allowed class significantly exceeds absent class
                best_period = None
                best_score = -1  # composite score, higher = stronger evidence
                best_detail = None
                best_confidence = None
                for period in [2, 3, 4, 6]:
                    allowed_raw = [isig for (idx, isig, _st) in refls if idx % period == 0]
                    absent_raw = [isig for (idx, isig, _st) in refls if idx % period != 0]
                    if len(allowed_raw) < 1 or len(absent_raw) < 2:
                        continue
                    mean_allowed = sum(abs(v) for v in allowed_raw) / len(allowed_raw)
                    mean_absent_abs = sum(abs(v) for v in absent_raw) / len(absent_raw)
                    mean_absent_raw = sum(v for v in absent_raw) / len(absent_raw)
                    # Fraction of absent reflections with |I/σ| ≤ 2 (weak/noise)
                    n_weak = sum(1 for v in absent_raw if abs(v) <= 2.0)
                    frac_weak = n_weak / len(absent_raw)
                    # Fraction with I/σ ≤ 1 (very weak / negative)
                    n_vweak = sum(1 for v in absent_raw if v <= 1.0)
                    frac_vweak = n_vweak / len(absent_raw)

                    # Star-annotation check: if XDS marks odd-index as *
                    # (expected absent), check how many of those are weak
                    star_absent = [(isig, st) for (idx, isig, st) in refls
                                   if idx % period != 0 and st]
                    n_star_weak = sum(1 for (v, _) in star_absent if abs(v) <= 3.0)
                    frac_star_weak = (n_star_weak / len(star_absent)) if star_absent else 0

                    if mean_allowed < 0.5:
                        continue  # Allowed class too weak to judge anything

                    ratio = mean_absent_abs / mean_allowed if mean_allowed > 0 else 999

                    # Score each criterion independently (0 or 1), then combine
                    score = 0.0

                    # Criterion 1: ratio-based (absent much weaker than allowed)
                    if ratio < 0.25:
                        score += 2.0
                    elif ratio < 0.50:
                        score += 1.0
                    elif ratio < 0.70:
                        score += 0.5

                    # Criterion 2: most absent reflections are weak
                    if frac_weak >= 0.75:
                        score += 2.0
                    elif frac_weak >= 0.55:
                        score += 1.0
                    elif frac_weak >= 0.40:
                        score += 0.5

                    # Criterion 3: mean raw I/σ of absent class near zero
                    # (truly absent reflections have noise-like distribution around 0)
                    if abs(mean_absent_raw) < 0.5:
                        score += 1.5
                    elif abs(mean_absent_raw) < 1.0:
                        score += 1.0
                    elif abs(mean_absent_raw) < 1.5:
                        score += 0.5

                    # Criterion 4: clear separation — allowed mean exceeds absent mean
                    contrast = mean_allowed - mean_absent_abs
                    if contrast > 2.0:
                        score += 1.5
                    elif contrast > 1.0:
                        score += 1.0
                    elif contrast > 0.5:
                        score += 0.5

                    # Criterion 5: XDS star annotations — if XDS marks reflections
                    # as expected-absent (*) and most of those are indeed weak
                    if len(star_absent) >= 3:
                        if frac_star_weak >= 0.80:
                            score += 2.0
                        elif frac_star_weak >= 0.60:
                            score += 1.0

                    # Determine confidence from composite score
                    # Max possible score = 9.0 (with star annotations)
                    if score >= 4.0:
                        confidence = 'high'
                    elif score >= 2.5:
                        confidence = 'suggestive'
                    else:
                        confidence = None

                    if confidence and score > best_score:
                        best_period = period
                        best_score = score
                        best_confidence = confidence
                        best_detail = {
                            'period': period,
                            'confidence': confidence,
                            'n_allowed': len(allowed_raw),
                            'n_absent': len(absent_raw),
                            'mean_isig_allowed': round(mean_allowed, 1),
                            'mean_isig_absent': round(mean_absent_abs, 1),
                            'mean_isig_absent_raw': round(mean_absent_raw, 1),
                            'frac_weak_absent': round(frac_weak, 2),
                            'ratio': round(ratio, 3),
                            'score': round(score, 1)
                        }
                if best_detail:
                    axis_analysis[axis_name] = best_detail
                else:
                    # No screw detected — report summary for context
                    all_isig = [isig for (_, isig, _st) in refls]
                    axis_analysis[axis_name] = {
                        'period': 0,
                        'n_reflections': len(refls),
                        'mean_isig': round(sum(abs(v) for v in all_isig) / len(all_isig), 1) if all_isig else 0
                    }

            if axis_analysis:
                metrics['axis_analysis'] = axis_analysis

            # Check if any * annotations exist (XDS-assigned expected absences)
            has_star_annotations = any(r['expected_absent'] for r in sysabs)
            metrics['has_star_annotations'] = has_star_annotations

        # ── Expected vs detected screw axes + SG suggestion ───────────
        # Lookup: for each chiral SG, which screw axes are expected on h00/0k0/00l?
        # Key = SG number, Value = dict of axis -> expected period (0=none, 2=2₁, etc.)
        # Only covers protein-relevant chiral space groups with screw axes along principal axes.
        # Enantiomorphic pairs share identical axial absence patterns.
        # Format: {sg: {'h00': period, '0k0': period, '00l': period, 'name': str}}
        sg_screw_table = {
            # Monoclinic (unique axis b: screw only on 0k0)
            3: {'h00':0,'0k0':0,'00l':0, 'name':'P2'},
            4: {'h00':0,'0k0':2,'00l':0, 'name':'P2₁'},
            5: {'h00':0,'0k0':0,'00l':0, 'name':'C2'},
            # Orthorhombic P
            16: {'h00':0,'0k0':0,'00l':0, 'name':'P222'},
            17: {'h00':0,'0k0':0,'00l':2, 'name':'P222₁'},
            18: {'h00':2,'0k0':2,'00l':0, 'name':'P2₁2₁2'},
            19: {'h00':2,'0k0':2,'00l':2, 'name':'P2₁2₁2₁'},
            # Orthorhombic C/I/F
            20: {'h00':0,'0k0':0,'00l':2, 'name':'C222₁'},
            21: {'h00':0,'0k0':0,'00l':0, 'name':'C222'},
            22: {'h00':0,'0k0':0,'00l':0, 'name':'F222'},
            23: {'h00':0,'0k0':0,'00l':0, 'name':'I222'},
            24: {'h00':0,'0k0':0,'00l':0, 'name':'I2₁2₁2₁'},  # Indistinguishable from I222 by absences (I-centering masks 2₁)
            # Tetragonal P (screw along c only for principal axis)
            75: {'h00':0,'0k0':0,'00l':0, 'name':'P4'},
            76: {'h00':0,'0k0':0,'00l':4, 'name':'P4₁'},
            77: {'h00':0,'0k0':0,'00l':2, 'name':'P4₂'},
            78: {'h00':0,'0k0':0,'00l':4, 'name':'P4₃'},
            89: {'h00':0,'0k0':0,'00l':0, 'name':'P422'},
            90: {'h00':0,'0k0':0,'00l':0, 'name':'P42₁2'},
            91: {'h00':0,'0k0':0,'00l':4, 'name':'P4₁22'},
            92: {'h00':0,'0k0':0,'00l':4, 'name':'P4₁2₁2'},
            93: {'h00':0,'0k0':0,'00l':2, 'name':'P4₂22'},
            94: {'h00':0,'0k0':0,'00l':2, 'name':'P4₂2₁2'},
            95: {'h00':0,'0k0':0,'00l':4, 'name':'P4₃22'},
            96: {'h00':0,'0k0':0,'00l':4, 'name':'P4₃2₁2'},
            # Tetragonal I (I-centering: h+k+l=2n; observed 00l has only even l)
            79: {'h00':0,'0k0':0,'00l':0, 'name':'I4'},
            80: {'h00':0,'0k0':0,'00l':4, 'name':'I4₁'},       # 4₁ screw: l=4n (period 4 in even-only 00l series)
            97: {'h00':0,'0k0':0,'00l':0, 'name':'I422'},
            98: {'h00':0,'0k0':0,'00l':4, 'name':'I4₁22'},     # 4₁ screw: l=4n
            # Trigonal P (screw along c)
            143: {'h00':0,'0k0':0,'00l':0, 'name':'P3'},
            144: {'h00':0,'0k0':0,'00l':3, 'name':'P3₁'},
            145: {'h00':0,'0k0':0,'00l':3, 'name':'P3₂'},
            149: {'h00':0,'0k0':0,'00l':0, 'name':'P312'},
            150: {'h00':0,'0k0':0,'00l':0, 'name':'P321'},
            151: {'h00':0,'0k0':0,'00l':3, 'name':'P3₁12'},
            152: {'h00':0,'0k0':0,'00l':3, 'name':'P3₁21'},
            153: {'h00':0,'0k0':0,'00l':3, 'name':'P3₂12'},
            154: {'h00':0,'0k0':0,'00l':3, 'name':'P3₂21'},
            # Trigonal R
            146: {'h00':0,'0k0':0,'00l':0, 'name':'R3'},
            155: {'h00':0,'0k0':0,'00l':0, 'name':'R32'},
            # Hexagonal P (screw along c)
            168: {'h00':0,'0k0':0,'00l':0, 'name':'P6'},
            169: {'h00':0,'0k0':0,'00l':6, 'name':'P6₁'},
            170: {'h00':0,'0k0':0,'00l':6, 'name':'P6₅'},
            171: {'h00':0,'0k0':0,'00l':3, 'name':'P6₂'},
            172: {'h00':0,'0k0':0,'00l':3, 'name':'P6₄'},
            173: {'h00':0,'0k0':0,'00l':2, 'name':'P6₃'},
            177: {'h00':0,'0k0':0,'00l':0, 'name':'P622'},
            178: {'h00':0,'0k0':0,'00l':6, 'name':'P6₁22'},
            179: {'h00':0,'0k0':0,'00l':6, 'name':'P6₅22'},
            180: {'h00':0,'0k0':0,'00l':3, 'name':'P6₂22'},
            181: {'h00':0,'0k0':0,'00l':3, 'name':'P6₄22'},
            182: {'h00':0,'0k0':0,'00l':2, 'name':'P6₃22'},
            # Cubic P (cubic 3-fold makes h00=0k0=00l equivalent)
            195: {'h00':0,'0k0':0,'00l':0, 'name':'P23'},
            198: {'h00':2,'0k0':2,'00l':2, 'name':'P2₁3'},
            207: {'h00':0,'0k0':0,'00l':0, 'name':'P432'},
            208: {'h00':2,'0k0':2,'00l':2, 'name':'P4₂32'},
            212: {'h00':4,'0k0':4,'00l':4, 'name':'P4₃32'},    # 4₃ screw: h=4n on all axes
            213: {'h00':4,'0k0':4,'00l':4, 'name':'P4₁32'},    # 4₁ screw: h=4n on all axes
            # Cubic I (I-centering: h+k+l=2n; observed h00 has only even h)
            197: {'h00':0,'0k0':0,'00l':0, 'name':'I23'},
            199: {'h00':0,'0k0':0,'00l':0, 'name':'I2₁3'},     # Indistinguishable from I23 by absences (I-centering masks 2₁)
            211: {'h00':0,'0k0':0,'00l':0, 'name':'I432'},
            214: {'h00':4,'0k0':4,'00l':4, 'name':'I4₁32'},    # 4₁ screw: h=4n on all axes
            # Cubic F (F-centering: h,k,l all even or all odd; observed h00 has only even h)
            196: {'h00':0,'0k0':0,'00l':0, 'name':'F23'},
            209: {'h00':0,'0k0':0,'00l':0, 'name':'F432'},
            210: {'h00':4,'0k0':4,'00l':4, 'name':'F4₁32'},    # 4₁ screw: h=4n on all axes
        }

        # Group SGs by Laue group (same point group symmetry)
        # Maps: frozenset of SG numbers -> Laue group label
        laue_groups = {
            'P 1 2/m 1': [3, 4],
            'C 1 2/m 1': [5],
            'P mmm': [16, 17, 18, 19],
            'C mmm': [20, 21],
            'F mmm': [22],
            'I mmm': [23, 24],
            'P 4/m': [75, 76, 77, 78],
            'P 4/mmm': [89, 90, 91, 92, 93, 94, 95, 96],
            'I 4/m': [79, 80],
            'I 4/mmm': [97, 98],
            'P -3': [143, 144, 145],
            'P -3 1 m': [149, 151, 153],
            'P -3 m 1': [150, 152, 154],
            'R -3': [146],
            'R -3 m': [155],
            'P 6/m': [168, 169, 170, 171, 172, 173],
            'P 6/mmm': [177, 178, 179, 180, 181, 182],
            'P m -3': [195, 198],
            'P m -3 m': [207, 208, 212, 213],
            'I m -3': [197, 199],
            'I m -3 m': [211, 214],
            'F m -3': [196],
            'F m -3 m': [209, 210],
        }

        current_sg = metrics.get('space_group')
        axis_an = metrics.get('axis_analysis', {})

        if current_sg and current_sg in sg_screw_table:
            expected = sg_screw_table[current_sg]

            # Build expected screws summary
            expected_screws = {}
            for ax in ['h00', '0k0', '00l']:
                if expected[ax] > 0:
                    expected_screws[ax] = expected[ax]

            # Build detected screws summary (high confidence only)
            detected_screws = {}
            # Build suggested screws summary (suggestive confidence)
            suggested_screws = {}
            for ax in ['h00', '0k0', '00l']:
                if ax in axis_an and axis_an[ax].get('period', 0) > 0:
                    conf = axis_an[ax].get('confidence', 'high')
                    if conf == 'high':
                        detected_screws[ax] = axis_an[ax]['period']
                    else:
                        suggested_screws[ax] = axis_an[ax]['period']

            metrics['expected_screws'] = expected_screws
            metrics['detected_screws'] = detected_screws
            metrics['suggested_screws'] = suggested_screws
            metrics['current_sg_name'] = expected['name']

            # Find which Laue group the current SG belongs to
            my_laue_sgs = None
            my_laue_name = None
            for lg_name, sg_list in laue_groups.items():
                if current_sg in sg_list:
                    my_laue_sgs = sg_list
                    my_laue_name = lg_name
                    break

            # Suggest space groups consistent with detected screws
            # High-confidence detections must match; suggestive detections
            # are treated as compatible with either screw or no-screw.
            if my_laue_sgs and axis_an:
                suggestions = []
                for cand_sg in my_laue_sgs:
                    if cand_sg not in sg_screw_table:
                        continue
                    cand = sg_screw_table[cand_sg]
                    match = True
                    for ax in ['h00', '0k0', '00l']:
                        det = detected_screws.get(ax, 0)
                        sug = suggested_screws.get(ax, 0)
                        exp = cand[ax]
                        if ax in axis_an:
                            info = axis_an[ax]
                            if det > 0:
                                # High-confidence detection: candidate must match
                                if exp != det:
                                    match = False
                            elif sug > 0:
                                # Suggestive detection: compatible with either
                                # the suggested period or no screw — don't exclude
                                pass
                            else:
                                # No screw detected: candidate should not expect one
                                # (but be lenient if few reflections)
                                if exp > 0 and info.get('n_reflections', 99) >= 4:
                                    match = False
                    if match:
                        suggestions.append({
                            'sg_number': cand_sg,
                            'name': cand['name'],
                            'screws': {ax: cand[ax] for ax in ['h00','0k0','00l'] if cand[ax] > 0}
                        })

                if suggestions:
                    metrics['sg_suggestions'] = suggestions
                    metrics['laue_group'] = my_laue_name

        # ── Number of systematic absent reflections ────────────────────
        for line in lines:
            if 'NUMBER OF SYSTEMATIC ABSENT REFLECTIONS' in line:
                parts = line.strip().split()
                try:
                    metrics['n_systematic_absences'] = int(parts[-1])
                except (ValueError, IndexError):
                    pass
                break

        # ── Resolution cutoff recommendation ──────────────────────────
        # Find the last shell where CC½ is marked with * (significant at 0.1% level)
        if 'statistics_table' in metrics:
            last_starred_res = None
            for row in metrics['statistics_table']:
                if row.get('resolution', '').lower() == 'total':
                    continue
                cc = str(row.get('cc_half', ''))
                if '*' in cc:
                    last_starred_res = row['resolution']
            if last_starred_res is not None:
                try:
                    metrics['recommended_resolution_cutoff'] = float(last_starred_res)
                except (ValueError, TypeError):
                    pass

        return metrics

    @staticmethod
    def parse_integrate(lp_content):
        """Extract key metrics from INTEGRATE.LP: mosaicity trend (SIGMAB, SIGMAR per image) and suggested values."""
        metrics = {}
        lines = lp_content.split('\n')

        # Parse per-image table: IMAGE IER SCALE NBKG NOVL NEWALD NSTRONG NREJ SIGMAB SIGMAR
        image_stats = []
        in_image_table = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'IMAGE' in stripped and 'IER' in stripped and 'SIGMAB' in stripped and 'SIGMAR' in stripped:
                in_image_table = True
                continue
            if in_image_table:
                if not stripped:
                    if image_stats:
                        in_image_table = False
                    continue
                parts = stripped.split()
                if len(parts) >= 10:
                    try:
                        img = int(parts[0])
                        ier = int(parts[1])
                        scale = float(parts[2])
                        novl = int(parts[4])
                        nstrong = int(parts[6])
                        nrej = int(parts[7])
                        sigmab = float(parts[-2])
                        sigmar = float(parts[-1])
                        image_stats.append({'image': img, 'ier': ier, 'scale': scale,
                                            'novl': novl, 'nstrong': nstrong, 'nrej': nrej,
                                            'sigmab': sigmab, 'sigmar': sigmar})
                    except (ValueError, IndexError):
                        pass
                else:
                    if image_stats:
                        in_image_table = False

        if image_stats:
            metrics['image_stats'] = image_stats

        # Parse SUGGESTED VALUES at end of file
        for i, line in enumerate(lines):
            if 'SUGGESTED VALUES FOR INPUT PARAMETERS' in line:
                for j in range(i + 1, min(i + 10, len(lines))):
                    row = lines[j].strip()
                    if row.startswith('BEAM_DIVERGENCE_E.S.D.'):
                        try:
                            metrics['beam_divergence_esd'] = float(row.split('=')[1].strip())
                        except (ValueError, IndexError):
                            pass
                    elif row.startswith('BEAM_DIVERGENCE='):
                        try:
                            metrics['beam_divergence'] = float(row.split('=')[1].strip())
                        except (ValueError, IndexError):
                            pass
                    elif row.startswith('REFLECTING_RANGE_E.S.D.'):
                        try:
                            metrics['mosaicity'] = float(row.split('=')[1].strip())
                        except (ValueError, IndexError):
                            pass
                    elif row.startswith('REFLECTING_RANGE='):
                        try:
                            metrics['reflecting_range'] = float(row.split('=')[1].strip())
                        except (ValueError, IndexError):
                            pass

        return metrics

    @staticmethod
    def parse_xscale(lp_content):
        """Extract key metrics from XSCALE.LP"""
        metrics = {}
        lines = lp_content.split('\n')

        # Detect FRIEDEL'S_LAW setting
        for line in lines:
            if "FRIEDEL'S_LAW=" in line and 'INPUT' not in line:
                after = line.split("FRIEDEL'S_LAW=")[1].strip().split()[0]
                if after.startswith('TRUE'):
                    metrics['friedels_law'] = 'TRUE'
                elif after.startswith('FALSE'):
                    metrics['friedels_law'] = 'FALSE'

        # Find space group and unit cell
        for i, line in enumerate(lines):
            if 'SPACE_GROUP_NUMBER=' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    try:
                        metrics['space_group'] = int(parts[1].strip())
                    except Exception:
                        pass
            if 'UNIT_CELL_CONSTANTS=' in line:
                parts = line.split('=')[1].strip().split()
                if len(parts) >= 6:
                    try:
                        metrics['unit_cell'] = {
                            'a': float(parts[0]), 'b': float(parts[1]), 'c': float(parts[2]),
                            'alpha': float(parts[3]), 'beta': float(parts[4]), 'gamma': float(parts[5])
                        }
                    except Exception:
                        pass

        # Find statistics table (SUBSET OF INTENSITY DATA)
        all_tables = []
        current_table = []
        in_stats_table = False
        header_line = None

        for i, line in enumerate(lines):
            if 'SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE' in line:
                if current_table:
                    all_tables.append(current_table)
                current_table = []
                in_stats_table = True
                header_line = i + 1
                continue

            if in_stats_table:
                if header_line and i <= header_line + 1:
                    continue
                stripped = line.strip()
                if stripped == '':
                    if current_table:
                        in_stats_table = False
                    continue
                first_token = stripped.split()[0]
                is_data = first_token[0].replace('.', '').replace('-', '').isdigit() or first_token.lower() == 'total'
                if not is_data:
                    if current_table:
                        in_stats_table = False
                    continue
                parts = stripped.split()
                if len(parts) >= 11:
                    try:
                        current_table.append({
                            'resolution': parts[0],
                            'observed': parts[1],
                            'unique': parts[2],
                            'possible': parts[3],
                            'completeness': parts[4],
                            'r_obs': parts[5],
                            'r_exp': parts[6],
                            'compared': parts[7],
                            'i_sigma': parts[8],
                            'r_meas': parts[9],
                            'cc_half': parts[10],
                            'anomal_corr': parts[11] if len(parts) > 11 else '',
                            'siganom': parts[12] if len(parts) > 12 else '',
                            'nano': parts[13] if len(parts) > 13 else ''
                        })
                    except Exception:
                        pass

        if current_table:
            all_tables.append(current_table)
        if all_tables:
            metrics['statistics_table'] = all_tables[-1]
            metrics['cutoffs'] = LPParser.determine_resolution_cutoff(all_tables[-1])

        # Extract the actual low-resolution limit from the
        # "RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR ..." table.
        for i, line in enumerate(lines):
            if 'RESOLUTION RANGE' in line and 'I/Sigma' in line and 'Chi' in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    row = lines[j].strip()
                    if not row:
                        continue
                    if any(c.isalpha() for c in row):
                        continue
                    parts = row.split()
                    if len(parts) >= 2:
                        try:
                            lo = float(parts[0])
                            metrics['resolution_range_low'] = round(lo, 3)
                        except (ValueError, IndexError):
                            pass
                    break

        # Extract ISa / ISa0 table
        isa_table = []
        for i, line in enumerate(lines):
            if 'ISa' in line and 'ISa0' in line and 'INPUT DATA SET' in line:
                # Data rows follow this header line
                for j in range(i + 1, len(lines)):
                    row = lines[j].strip()
                    if not row:
                        break
                    parts = row.split()
                    if len(parts) >= 5:
                        try:
                            float(parts[0])  # test that first field is numeric (a)
                            isa_table.append({
                                'a': parts[0],
                                'b': parts[1],
                                'isa': parts[2],
                                'isa0': parts[3],
                                'dataset': ' '.join(parts[4:])
                            })
                        except (ValueError, IndexError):
                            break
                    else:
                        break
                break
        if isa_table:
            metrics['isa_table'] = isa_table

        return metrics

    @staticmethod
    def parse_colspot(lp_content):
        """Parse COLSPOT.LP for spot-finding diagnostics"""
        metrics = {}
        try:
            for line in lp_content.splitlines():
                upper = line.strip().upper()
                # Total spots saved
                if 'NUMBER OF DIFFRACTION SPOTS' in upper and ('SAVED' in upper or 'ACCEPTED' in upper):
                    parts = line.strip().split()
                    for p in reversed(parts):
                        try:
                            metrics['total_spots'] = int(p)
                            break
                        except ValueError:
                            continue
                # Signal pixel threshold (not MAXIMUM_NUMBER_OF_STRONG_PIXELS)
                if line.strip().upper().startswith('SIGNAL_PIXEL') and '=' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            val = float(parts[-1].strip().split()[0])
                            metrics['signal_pixel'] = val
                        except (ValueError, IndexError):
                            pass
                # Background pixel threshold
                if line.strip().upper().startswith('BACKGROUND_PIXEL') and '=' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            val = float(parts[-1].strip().split()[0])
                            metrics['background_pixel'] = val
                        except (ValueError, IndexError):
                            pass
                # Equivalence classes
                if 'NUMBER OF EQUIVALENCE CLASSES' in upper:
                    parts = line.strip().split()
                    for p in reversed(parts):
                        try:
                            metrics['n_equiv_classes'] = int(p)
                            break
                        except ValueError:
                            continue
            # Parse SPOT_RANGE
            spot_ranges = []
            for line in lp_content.splitlines():
                stripped = line.strip()
                if stripped.upper().startswith('SPOT_RANGE'):
                    parts = stripped.split('=', 1)
                    if len(parts) == 2:
                        spot_ranges.append(parts[1].strip())
            if spot_ranges:
                metrics['spot_ranges'] = spot_ranges
            # Parse per-image table: FRAME # NBKG NSTRONG I/O-FLAG
            image_spots = []
            in_table = False
            for line in lp_content.splitlines():
                stripped = line.strip()
                if 'FRAME #' in stripped.upper() or 'FRAME#' in stripped.upper().replace(' ', ''):
                    in_table = True
                    continue
                if in_table:
                    parts = stripped.split()
                    if len(parts) >= 3:
                        try:
                            frame = int(parts[0])
                            nstrong = int(parts[2])
                            if 0 < frame < 100000:
                                image_spots.append([frame, nstrong])
                        except (ValueError, IndexError):
                            if image_spots:
                                break
                    elif stripped == '' and image_spots:
                        break
            if image_spots:
                metrics['image_spots'] = image_spots
                metrics['n_images_scanned'] = len(image_spots)
        except Exception:
            pass
        return metrics

    @staticmethod
    def parse_init(lp_content):
        """Parse INIT.LP for gain and background diagnostics"""
        metrics = {}
        try:
            for line in lp_content.splitlines():
                upper = line.strip().upper()
                if 'GAIN' in upper and '=' in line and 'CORRECTION' not in upper:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        try:
                            val = float(parts[-1].strip().split()[0])
                            if 0.01 <= val <= 1000:
                                metrics['gain'] = val
                        except (ValueError, IndexError):
                            pass
            image_backgrounds = []
            for line in lp_content.splitlines():
                stripped = line.strip()
                parts = stripped.split()
                if len(parts) >= 2 and len(parts) <= 4:
                    try:
                        img = int(parts[0])
                        mean_val = float(parts[1])
                        if 0 < img < 100000 and 0 <= mean_val < 100000:
                            image_backgrounds.append([img, mean_val])
                    except (ValueError, IndexError):
                        pass
            if image_backgrounds:
                metrics['image_backgrounds'] = image_backgrounds
                vals = [x[1] for x in image_backgrounds]
                mean_bg = sum(vals) / len(vals) if vals else 0
                metrics['mean_background'] = mean_bg
                if mean_bg > 0:
                    bad = [x for x in image_backgrounds if x[1] > 2.5 * mean_bg]
                    metrics['bad_frames'] = bad
                    metrics['n_bad_frames'] = len(bad)
        except Exception:
            pass
        return metrics

    @staticmethod
    def matthews_coefficient(unit_cell, space_group, mol_weight):
        """Calculate Matthews coefficient and solvent content.

        Args:
            unit_cell: dict with keys a, b, c, alpha, beta, gamma
            space_group: int (space group number)
            mol_weight: float (molecular weight in Da)

        Returns:
            list of dicts with keys: n_copies, vm, solvent_pct
            for n = 1..max plausible copies, or empty list on error.
        """
        import math

        # Number of general equivalent positions (Z) per space group number.
        # Source: International Tables for Crystallography, Vol. A.
        # Verified against CCP4/Phenix/PDB conventions.
        _SG_Z = {
            1:1, 2:2, 3:2, 4:2, 5:4, 6:2, 7:2, 8:4, 9:4, 10:4,
            11:4, 12:8, 13:4, 14:4, 15:8, 16:4, 17:4, 18:4, 19:4, 20:8,
            21:8, 22:16, 23:8, 24:8, 25:4, 26:4, 27:4, 28:4, 29:4, 30:4,
            31:4, 32:4, 33:4, 34:4, 35:8, 36:8, 37:8, 38:8, 39:8, 40:8,
            41:8, 42:16, 43:16, 44:8, 45:8, 46:8, 47:8, 48:8, 49:8, 50:8,
            51:8, 52:8, 53:8, 54:8, 55:8, 56:8, 57:8, 58:8, 59:8, 60:8,
            61:8, 62:8, 63:16, 64:16, 65:16, 66:16, 67:16, 68:16, 69:32,
            70:32, 71:16, 72:16, 73:16, 74:16, 75:4, 76:4, 77:4, 78:4,
            79:8, 80:8, 81:4, 82:8, 83:8, 84:8, 85:8, 86:8, 87:16, 88:16,
            89:8, 90:8, 91:8, 92:8, 93:8, 94:8, 95:8, 96:8, 97:16, 98:16,
            99:8, 100:8, 101:8, 102:8, 103:8, 104:8, 105:8, 106:8,
            107:16, 108:16, 109:16, 110:16, 111:8, 112:8, 113:8, 114:8,
            115:8, 116:8, 117:8, 118:8, 119:16, 120:16, 121:16, 122:16,
            123:16, 124:16, 125:16, 126:16, 127:16, 128:16, 129:16, 130:16,
            131:16, 132:16, 133:16, 134:16, 135:16, 136:16, 137:16, 138:16,
            139:32, 140:32, 141:32, 142:32,
            143:3, 144:3, 145:3, 146:9, 147:6, 148:18, 149:6, 150:6,
            151:6, 152:6, 153:6, 154:6, 155:18, 156:6, 157:6, 158:6,
            159:6, 160:18, 161:18, 162:12, 163:12, 164:12, 165:12,
            166:36, 167:36, 168:6, 169:6, 170:6, 171:6, 172:6, 173:6,
            174:6, 175:12, 176:12, 177:12, 178:12, 179:12, 180:12,
            181:12, 182:12, 183:12, 184:12, 185:12, 186:12, 187:12,
            188:12, 189:12, 190:12, 191:24, 192:24, 193:24, 194:24,
            195:12, 196:48, 197:24, 198:12, 199:24, 200:24, 201:24,
            202:96, 203:96, 204:48, 205:24, 206:48, 207:24, 208:24,
            209:96, 210:96, 211:48, 212:24, 213:24, 214:48, 215:24,
            216:96, 217:48, 218:24, 219:96, 220:48, 221:48, 222:48,
            223:48, 224:48, 225:192, 226:192, 227:192, 228:192, 229:96,
            230:96,
        }

        try:
            a = unit_cell['a']
            b = unit_cell['b']
            c = unit_cell['c']
            al = math.radians(unit_cell['alpha'])
            be = math.radians(unit_cell['beta'])
            ga = math.radians(unit_cell['gamma'])

            # Unit cell volume
            ca, cb, cg = math.cos(al), math.cos(be), math.cos(ga)
            vol = a * b * c * math.sqrt(
                1 - ca*ca - cb*cb - cg*cg + 2*ca*cb*cg
            )

            if vol <= 0 or mol_weight <= 0:
                return []

            sg = int(space_group)
            if sg < 1 or sg > 230:
                return []
            z = _SG_Z.get(sg)
            if z is None:
                return []

            results = []
            for n in range(1, 25):
                vm = vol / (n * z * mol_weight)
                # Plausible range: 1.5 to 6.0 A^3/Da (Matthews 1968)
                if vm < 1.0:
                    break
                solvent = 1.0 - (1.23 / vm)
                solvent_pct = solvent * 100.0
                if solvent_pct < 10:
                    break
                results.append({
                    'n_copies': n,
                    'vm': round(vm, 2),
                    'solvent_pct': round(solvent_pct, 1)
                })

            return results
        except Exception:
            return []



    @staticmethod
    def parse_pointless(log_content):
        """Parse POINTLESS log output for Laue group, space group determination, and key results.

        Returns dict with:
          - laue_groups: list of {name, number, reindex, score, confidence}
          - space_groups: list of {name, number, sysabs_prob, total_prob, reindex, conditions}
          - best_solution: {space_group, laue_group, reindex, laue_prob, sysabs_prob, total_prob,
                           sg_confidence, laue_confidence, unit_cell, resolution}
          - symmetry_operators: list of {operator, cc, r_factor, present}
        """
        result = {
            'laue_groups': [],
            'space_groups': [],
            'best_solution': {},
            'symmetry_operators': [],
        }
        lines = log_content.split('\n')

        # ── Parse Best Solution block ──
        # $TEXT:Result: $$ $$
        # Best Solution:   space group P 21 21 21
        # Reindex operator: [h,k,l]
        # Laue group probability:          0.984
        # Systematic absence probability:  0.720
        # Total probability:               0.708
        # Space group confidence:          0.649
        # Laue group confidence            0.981
        # Unit cell:  45.59  46.91 149.84  90.00  90.00  90.00
        in_result = False
        for i, line in enumerate(lines):
            s = line.strip()

            if s.startswith('Best Solution:'):
                in_result = True
                # Extract SG name after "space group" or "point group"
                for token in ('space group', 'point group'):
                    if token in s:
                        result['best_solution']['space_group'] = s.split(token, 1)[1].strip()
                        break
                continue

            if in_result:
                if s.startswith('Reindex operator:'):
                    result['best_solution']['reindex'] = s.split(':', 1)[1].strip()
                elif s.startswith('Laue group probability:'):
                    try: result['best_solution']['laue_prob'] = float(s.split(':',1)[1].strip())
                    except Exception: pass
                elif s.startswith('Systematic absence probability:'):
                    try: result['best_solution']['sysabs_prob'] = float(s.split(':',1)[1].strip())
                    except Exception: pass
                elif s.startswith('Total probability:'):
                    try: result['best_solution']['total_prob'] = float(s.split(':',1)[1].strip())
                    except Exception: pass
                elif s.startswith('Space group confidence:'):
                    try: result['best_solution']['sg_confidence'] = float(s.split(':',1)[1].strip())
                    except Exception: pass
                elif 'Laue group confidence' in s:
                    try:
                        val = s.split('confidence', 1)[1].strip().lstrip(':').strip()
                        result['best_solution']['laue_confidence'] = float(val)
                    except Exception: pass
                elif s.startswith('Unit cell:'):
                    uc_str = s.split(':', 1)[1].strip()
                    parts = uc_str.split()
                    if len(parts) >= 6:
                        try:
                            result['best_solution']['unit_cell'] = {
                                'a': float(parts[0]), 'b': float(parts[1]), 'c': float(parts[2]),
                                'alpha': float(parts[3]), 'beta': float(parts[4]), 'gamma': float(parts[5])
                            }
                        except Exception: pass
                    # Check for resolution on same line (after unit cell values)
                    if 'to' in uc_str:
                        try:
                            res_parts = uc_str.split('to')
                            if len(res_parts) >= 2:
                                # "74.92 to 2.77" or similar
                                lo = res_parts[0].strip().split()[-1]
                                hi = res_parts[1].strip().split()[0]
                                result['best_solution']['resolution'] = f"{lo} to {hi}"
                        except Exception: pass
                elif s == '' or s.startswith('$$') or s.startswith('<!--'):
                    in_result = False

        # ── Parse Laue group table ──
        # Look for the table with: Laue group  Lklhd  Nops  ...  Reindex operator
        in_laue = False
        for i, line in enumerate(lines):
            s = line.strip()
            if 'Laue group' in s and 'Lklhd' in s and 'Reindex' in s:
                in_laue = True
                continue
            if in_laue:
                if not s or s.startswith('---') or s.startswith('==='):
                    if result['laue_groups']:
                        in_laue = False
                    continue
                # Try to parse a data row. Format varies but typically:
                # P mmm    (*) 0.984  3  ... [h,k,l]
                # The (*) marks the chosen group
                parts = s.split()
                if len(parts) < 3:
                    in_laue = False
                    continue
                try:
                    # Find the score (first float-like token after group name)
                    chosen = '(*)' in s
                    clean = s.replace('(*)', '   ')
                    tokens = clean.split()
                    # Laue group name: everything before first number
                    name_parts = []
                    score_idx = 0
                    for j, t in enumerate(tokens):
                        try:
                            float(t)
                            score_idx = j
                            break
                        except ValueError:
                            name_parts.append(t)
                    if name_parts and score_idx > 0:
                        name = ' '.join(name_parts)
                        score = float(tokens[score_idx])
                        # Reindex is usually the last bracketed token
                        reindex = ''
                        for t in reversed(tokens):
                            if t.startswith('[') and t.endswith(']'):
                                reindex = t
                                break
                        result['laue_groups'].append({
                            'name': name,
                            'score': score,
                            'chosen': chosen,
                            'reindex': reindex,
                        })
                except (ValueError, IndexError):
                    pass

        # ── Parse space group table ──
        # SysAbsProb  Reindex  Conditions
        # P 21 21 21 ( 19)  0.708  0.720  h00: h=2n, 0k0: k=2n, 00l: l=2n ...
        in_sg = False
        for i, line in enumerate(lines):
            s = line.strip()
            if 'SysAbsProb' in s and 'Conditions' in s:
                in_sg = True
                continue
            if in_sg:
                if not s or s.startswith('---') or s.startswith('Space group confidence'):
                    if result['space_groups']:
                        in_sg = False
                    continue
                # Parse: "P 21 21 21 ( 19) 0.708 0.720 h00: h=2n, ..."
                # Look for ( NN ) pattern to find the SG number
                m = re.search(r'\(\s*(\d+)\s*\)', s)
                if m:
                    sg_num = int(m.group(1))
                    before = s[:m.start()].strip()  # SG name
                    after = s[m.end():].strip()      # scores + conditions
                    tokens = after.split()
                    total_prob = None
                    sysabs_prob = None
                    conditions = ''
                    if len(tokens) >= 2:
                        try:
                            total_prob = float(tokens[0])
                            sysabs_prob = float(tokens[1])
                        except Exception: pass
                        # Everything after the two numbers is conditions
                        remaining = after
                        for t in tokens[:2]:
                            remaining = remaining.replace(t, '', 1).strip()
                        conditions = remaining.strip()
                    result['space_groups'].append({
                        'name': before,
                        'number': sg_num,
                        'total_prob': total_prob,
                        'sysabs_prob': sysabs_prob,
                        'conditions': conditions,
                    })

        # ── Parse individual symmetry operator scores ──
        # Look for: "Symm operator   Cc  ..."
        in_symop = False
        for i, line in enumerate(lines):
            s = line.strip()
            if ('identity' in s.lower() or 'along' in s.lower()) and ('CC' in line or 'Rmeas' in line):
                in_symop = True
                continue
            if in_symop:
                if not s:
                    if result['symmetry_operators']:
                        in_symop = False
                    continue
                parts = s.split()
                if len(parts) >= 3:
                    try:
                        # Attempt to find a CC value (float)
                        for j in range(1, len(parts)):
                            try:
                                cc = float(parts[j])
                                result['symmetry_operators'].append({
                                    'operator': parts[0],
                                    'cc': cc,
                                })
                                break
                            except ValueError:
                                continue
                    except Exception: pass

        # ── Extract Selecting space group line ──
        for line in lines:
            s = line.strip()
            if s.startswith('Selecting space group'):
                result['best_solution'].setdefault('selecting_line', s)
            elif s.startswith('Selecting point group'):
                result['best_solution'].setdefault('selecting_line', s)

        # ── Extract space group number from best solution name ──
        if result['best_solution'].get('space_group') and result['space_groups']:
            best_name = ' '.join(result['best_solution']['space_group'].split())  # normalize ws
            for sg in result['space_groups']:
                sg_norm = ' '.join(sg['name'].split())
                if sg_norm == best_name:
                    result['best_solution']['sg_number'] = sg['number']
                    break
        # Fallback 1: parse from "Selecting space group ... ( NN )" line
        if 'sg_number' not in result.get('best_solution', {}):
            for line in lines:
                m = re.search(r'Selecting (?:space|point) group\s+.+?\(\s*(\d+)\s*\)', line)
                if m:
                    result['best_solution']['sg_number'] = int(m.group(1))
                    break
        # Fallback 2: "Space group number   NN"
        if 'sg_number' not in result.get('best_solution', {}):
            for line in lines:
                m = re.search(r'Space group number\s+(\d+)', line)
                if m:
                    result['best_solution']['sg_number'] = int(m.group(1))
                    break
        # Fallback 3: find SG name followed by ( NN ) anywhere in log
        if 'sg_number' not in result.get('best_solution', {}) and result['best_solution'].get('space_group'):
            sg_name = re.escape(result['best_solution']['space_group'])
            for line in lines:
                m = re.search(sg_name + r'\s*\(\s*(\d+)\s*\)', line)
                if m:
                    result['best_solution']['sg_number'] = int(m.group(1))
                    break

        return result

    # ── XDSCC12 output parser ─────────────────────────────────────────────────
    @staticmethod
    def parse_xdscc12(lp_content):
        """Parse XDSCC12 output (stdout saved as XDSCC12.LP).

        Returns dict with per-frame ΔCC½ data suitable for plotting.
        Reference: Assmann, Brehm & Diederichs (2016) J. Appl. Cryst. 49, 1021-1028.
        """
        result = {
            'overall_cc_half': None,
            'avg_cc_half': None,
            'resolution_shells': [],
            'cc_half_shells': [],
            'cc_star_shells': [],
            'frames': [],
            'frame_shells': [],
            'anomalous_frames': [],
            'anomalous_frame_shells': [],
            'summary': {},
            'frames_per_batch': None,
        }
        lines = lp_content.split('\n')

        for i, line in enumerate(lines):
            stripped = line.strip()

            # ── Frames per batch: "5  frames will be batched" ──
            if 'frames will be batched' in stripped:
                parts = stripped.split()
                if parts and parts[0].isdigit():
                    try:
                        result['frames_per_batch'] = int(parts[0])
                    except ValueError:
                        pass

            # ── Header statistics ──
            # "overall CC1/2:    83.328 nref=   14986"
            if stripped.startswith('overall CC1/2:') and 'ano' not in stripped.lower():
                parts = stripped.split()
                for j, p in enumerate(parts):
                    if p == 'CC1/2:' and j + 1 < len(parts):
                        try:
                            result['overall_cc_half'] = float(parts[j + 1])
                        except ValueError:
                            pass
                        break

            # "<CC1/2>:    44.468"
            if stripped.startswith('<CC1/2>:') and 'ano' not in stripped.lower():
                parts = stripped.split()
                if len(parts) >= 2:
                    try:
                        result['avg_cc_half'] = float(parts[1])
                    except ValueError:
                        pass

            # "  10 resolution shells ..."
            # followed by shell boundary values on the next line
            if 'resolution shells' in stripped and len(stripped) > 0 and stripped[0].isdigit():
                for k in range(i + 1, min(i + 3, len(lines))):
                    candidate = lines[k].strip()
                    if candidate:
                        try:
                            result['resolution_shells'] = [float(x) for x in candidate.split()]
                        except ValueError:
                            pass
                        break

            # "CC1/2 in resolution shells:" followed by values
            if stripped == 'CC1/2 in resolution shells:':
                for k in range(i + 1, min(i + 3, len(lines))):
                    candidate = lines[k].strip()
                    if candidate:
                        try:
                            result['cc_half_shells'] = [float(x) for x in candidate.split()]
                        except ValueError:
                            pass
                        break

            # "CC* in resolution shells:" followed by values
            if stripped == 'CC* in resolution shells:':
                for k in range(i + 1, min(i + 3, len(lines))):
                    candidate = lines[k].strip()
                    if candidate:
                        try:
                            result['cc_star_shells'] = [float(x) for x in candidate.split()]
                        except ValueError:
                            pass
                        break

            # ── Per-frame "a " lines (isomorphous ΔCC½) ──
            # a  <batch> <nref_only> <cc_with_only> <cc_without_only> <delta_only>
            #    <nref_all> <cc_with_all> <cc_without_all> <delta_all>
            if len(stripped) > 2 and stripped[0] == 'a' and stripped[1] == ' ':
                parts = stripped.split()
                if len(parts) >= 10 and parts[0] == 'a':
                    try:
                        result['frames'].append({
                            'batch': int(parts[1]),
                            'nref_only': int(parts[2]),
                            'cc_with_only': float(parts[3]),
                            'cc_without_only': float(parts[4]),
                            'delta_only': float(parts[5]),
                            'nref_all': int(parts[6]),
                            'cc_with_all': float(parts[7]),
                            'cc_without_all': float(parts[8]),
                            'delta_all': float(parts[9]),
                        })
                    except (ValueError, IndexError):
                        pass

            # ── Per-frame resolution shells: "b " lines ──
            if len(stripped) > 2 and stripped[0] == 'b' and stripped[1] == ' ':
                parts = stripped.split()
                if len(parts) >= 2 and parts[0] == 'b':
                    try:
                        result['frame_shells'].append(
                            [float(x) for x in parts[1:]]
                        )
                    except ValueError:
                        pass

            # ── Anomalous per-frame: "d " lines ──
            if len(stripped) > 2 and stripped[0] == 'd' and stripped[1] == ' ':
                parts = stripped.split()
                if len(parts) >= 10 and parts[0] == 'd':
                    try:
                        result['anomalous_frames'].append({
                            'batch': int(parts[1]),
                            'nref_only': int(parts[2]),
                            'cc_with_only': float(parts[3]),
                            'cc_without_only': float(parts[4]),
                            'delta_only': float(parts[5]),
                            'nref_all': int(parts[6]),
                            'cc_with_all': float(parts[7]),
                            'cc_without_all': float(parts[8]),
                            'delta_all': float(parts[9]),
                        })
                    except (ValueError, IndexError):
                        pass

            # ── Anomalous resolution shells: "e " lines ──
            if len(stripped) > 2 and stripped[0] == 'e' and stripped[1] == ' ':
                parts = stripped.split()
                if len(parts) >= 2 and parts[0] == 'e':
                    try:
                        result['anomalous_frame_shells'].append(
                            [float(x) for x in parts[1:]]
                        )
                    except ValueError:
                        pass

            # ── Summary statistics ──
            low = stripped.lower()
            if 'median of delta-cc1/2' in low and '"only"' in stripped:
                eqparts = stripped.split('=')
                if len(eqparts) >= 2:
                    try:
                        result['summary']['median_delta_only'] = float(eqparts[-1].strip())
                    except ValueError:
                        pass
            elif 'median of delta-cc1/2' in low and '"all"' in stripped:
                eqparts = stripped.split('=')
                if len(eqparts) >= 2:
                    try:
                        result['summary']['median_delta_all'] = float(eqparts[-1].strip())
                    except ValueError:
                        pass
            elif 'noise' in low and 'mad' in low:
                eqparts = stripped.split('=')
                if len(eqparts) >= 2:
                    try:
                        val = float(eqparts[-1].strip())
                        if 'median_delta_only' in result['summary'] and 'mad_delta_only' not in result['summary']:
                            result['summary']['mad_delta_only'] = val
                        elif 'median_delta_all' in result['summary'] and 'mad_delta_all' not in result['summary']:
                            result['summary']['mad_delta_all'] = val
                    except ValueError:
                        pass

        # ── Compute frames_per_batch from consecutive batch numbers if not parsed ──
        # XDSCC12 batch numbers represent the last frame of each batch.
        # The step between consecutive batches = frames_per_batch.
        if result['frames_per_batch'] is None and len(result['frames']) >= 2:
            steps = []
            for fi in range(1, min(10, len(result['frames']))):
                step = result['frames'][fi]['batch'] - result['frames'][fi - 1]['batch']
                if step > 0:
                    steps.append(step)
            if steps:
                from collections import Counter
                result['frames_per_batch'] = Counter(steps).most_common(1)[0][0]

        return result

    # ── AutoPilot Error Diagnosis ─────────────────────────────────────────────
    # Machine-readable error detection for automatic reprocessing.
    # Returns a list of structured diagnostics with suggested parameter fixes.
    # Reference: XDSwiki "Problems" page; Kabsch (2010) Acta Cryst. D66, 125-132.

    @staticmethod
    def diagnose_idxref(lp_content):
        """Diagnose IDXREF.LP errors and return actionable fix suggestions.

        Returns list of dicts, each with:
          - error:   str  — canonical error identifier
          - message: str  — human-readable description
          - fix:     dict — parameter changes to apply to XDS.INP
          - severity: 'fatal' | 'warning' | 'info'
          - strategy: 'retry_idxref' | 'skip_to_integrate' | 'autoindex' | 'info_only'
        """
        import re
        diagnostics = []
        lines = lp_content.split('\n')
        upper_text = lp_content.upper()

        # ── 1. INSUFFICIENT PERCENTAGE OF INDEXED REFLECTIONS ──────────
        # XDS prints: "!!! ERROR !!! INSUFFICIENT PERCENTAGE (< XX%) ..."
        # Most common IDXREF failure. Often benign — processing can continue.
        if 'INSUFFICIENT PERCENTAGE' in upper_text:
            # Parse indexed fraction for severity grading
            frac = 0.0
            for line in lines:
                m = re.search(r'(\d+)\s+OUT OF\s+(\d+)\s+SPOTS INDEXED', line)
                if m:
                    indexed = int(m.group(1))
                    total = int(m.group(2))
                    frac = indexed / total if total > 0 else 0
                    break

            if frac >= 0.30:
                # Decent fraction — likely ice rings or satellite crystals.
                # Safe to continue with DEFPIX INTEGRATE CORRECT.
                diagnostics.append({
                    'error': 'insufficient_indexed_moderate',
                    'message': f'Indexed {frac:.0%} of spots — continuing is usually safe',
                    'fix': {},  # no XDS.INP changes; just change JOB=
                    'severity': 'warning',
                    'strategy': 'skip_to_integrate',
                })
            else:
                # Very low fraction — try lowering MINIMUM_FRACTION first,
                # then fall back to full auto-indexing.
                diagnostics.append({
                    'error': 'insufficient_indexed_severe',
                    'message': f'Only {frac:.0%} of spots indexed — will attempt auto-indexing',
                    'fix': {'MINIMUM_FRACTION_OF_INDEXED_SPOTS': '0.2'},
                    'severity': 'fatal',
                    'strategy': 'autoindex',
                })

        # ── 2. SOLUTION IS INACCURATE ──────────────────────────────────
        # Triggered when RMSD of spot positions exceeds default threshold.
        # Fix: relax positional tolerances. Common with split/smeared spots.
        if 'SOLUTION IS INACCURATE' in upper_text:
            sigma_spot = None
            sigma_spindle = None
            for line in lines:
                if 'STANDARD DEVIATION OF SPOT' in line and 'POSITION' in line:
                    parts = line.strip().split()
                    try:
                        sigma_spot = float(parts[-1])
                    except (ValueError, IndexError):
                        pass
                if 'STANDARD DEVIATION OF SPINDLE' in line and 'POSITION' in line:
                    parts = line.strip().split()
                    try:
                        sigma_spindle = float(parts[-1])
                    except (ValueError, IndexError):
                        pass

            fix = {}
            if sigma_spot is not None and sigma_spot > 3.0:
                # Set tolerance to 2× observed RMSD, minimum 6.0
                fix['MAXIMUM_ERROR_OF_SPOT_POSITION'] = str(max(6.0, round(sigma_spot * 2, 1)))
            if sigma_spindle is not None and sigma_spindle > 2.0:
                fix['MAXIMUM_ERROR_OF_SPINDLE_POSITION'] = str(max(4.0, round(sigma_spindle * 2, 1)))

            diagnostics.append({
                'error': 'solution_inaccurate',
                'message': 'Spot position RMSD exceeds threshold — relaxing tolerances',
                'fix': fix if fix else {
                    'MAXIMUM_ERROR_OF_SPOT_POSITION': '6.0',
                    'MAXIMUM_ERROR_OF_SPINDLE_POSITION': '4.0',
                },
                'severity': 'warning',
                'strategy': 'retry_idxref',
            })

        # ── 3. REFINEMENT DID NOT CONVERGE ─────────────────────────────
        # Usually caused by large detector distance making POSITION
        # unrefmnable. Fix: remove POSITION from REFINE(IDXREF).
        if 'REFINEMENT DID NOT CONVERGE' in upper_text:
            diagnostics.append({
                'error': 'refinement_not_converged',
                'message': 'Refinement did not converge — removing POSITION from IDXREF refinement',
                'fix': {'REFINE(IDXREF)': 'CELL BEAM ORIENTATION AXIS'},
                'severity': 'warning',
                'strategy': 'retry_idxref',
            })

        # ── 4. Half-integer difference vectors / too-short cell ────────
        # Detected from CLUSTER INDICES table: if many indices are near 0.5,
        # the cell axis is likely doubled. Common with Pilatus/Eiger data
        # when SEPMIN/CLUSTER_RADIUS are too large.
        # We check for half-integer patterns in the cluster index columns.
        half_int_count = 0
        cluster_count = 0
        in_cluster_table = False
        for line in lines:
            if 'CLUSTER COORDINATES AND INDICES' in line:
                in_cluster_table = True
                continue
            if in_cluster_table:
                stripped = line.strip()
                if not stripped:
                    if cluster_count > 0:
                        break
                    continue
                parts = stripped.split()
                if len(parts) >= 7:
                    try:
                        int(parts[0])  # row number
                        # Cluster indices are the last 3 columns
                        for idx_str in parts[-3:]:
                            val = float(idx_str)
                            frac = abs(val - round(val))
                            if 0.35 < frac < 0.65:  # close to 0.5
                                half_int_count += 1
                        cluster_count += 1
                    except (ValueError, IndexError):
                        if cluster_count > 0:
                            break

        if cluster_count > 0 and half_int_count > cluster_count * 0.3:
            diagnostics.append({
                'error': 'half_integer_indices',
                'message': 'Half-integer cluster indices detected — reducing SEPMIN/CLUSTER_RADIUS',
                'fix': {'SEPMIN': '4.0', 'CLUSTER_RADIUS': '2'},
                'severity': 'warning',
                'strategy': 'retry_idxref',
            })

        # ── 5. CANNOT READ SPOT.XDS ───────────────────────────────────
        if 'CANNOT READ SPOT.XDS' in upper_text:
            diagnostics.append({
                'error': 'cannot_read_spot_xds',
                'message': 'Cannot read SPOT.XDS — check NAME_TEMPLATE_OF_DATA_FRAMES',
                'fix': {},
                'severity': 'fatal',
                'strategy': 'info_only',
            })

        # ── 6. Very few spots indexed from many found ──────────────────
        # Even without an explicit error, if < 50% are indexed, something
        # may be wrong (wrong beam center, wrong detector, satellite crystals).
        # Parse the indexed fraction from the "SPOTS INDEXED" line.
        for line in lines:
            m = re.search(r'(\d+)\s+OUT OF\s+(\d+)\s+SPOTS INDEXED', line)
            if m:
                indexed = int(m.group(1))
                total = int(m.group(2))
                frac = indexed / total if total > 0 else 0
                # Only flag as issue if no prior INSUFFICIENT PERCENTAGE error caught it
                has_indexed_diag = any(d['error'].startswith('insufficient_indexed') for d in diagnostics)
                if not has_indexed_diag:
                    if total > 100 and frac < 0.05:
                        diagnostics.append({
                            'error': 'very_few_indexed',
                            'message': f'Only {indexed}/{total} ({frac:.0%}) spots indexed — fundamental parameter problem',
                            'fix': {},
                            'severity': 'fatal',
                            'strategy': 'autoindex',
                        })
                    elif total > 100 and frac < 0.50:
                        diagnostics.append({
                            'error': 'low_indexed_fraction',
                            'message': f'{indexed}/{total} ({frac:.0%}) spots indexed — below 50% threshold',
                            'fix': {},
                            'severity': 'warning',
                            'strategy': 'info_only',
                        })
                break

        return diagnostics

    @staticmethod
    def diagnose_integrate(lp_content):
        """Diagnose INTEGRATE.LP errors and return actionable fix suggestions.

        Returns list of dicts with same structure as diagnose_idxref.
        """
        diagnostics = []
        lines = lp_content.split('\n')
        upper_text = lp_content.upper()

        # ── 1. AUTOMATIC DETERMINATION OF SPOT SIZE PARAMETERS FAILED ──
        # Fix: increase DELPHI (escalate: 10 → 20 → 45).
        if 'AUTOMATIC DETERMINATION OF SPOT SIZE PARAMETERS HAS FAILED' in upper_text:
            diagnostics.append({
                'error': 'spot_size_failed',
                'message': 'Spot size auto-determination failed — increasing DELPHI',
                'fix': {'DELPHI': '10'},  # caller will escalate on subsequent retries
                'severity': 'fatal',
                'strategy': 'retry_integrate',
                '_delphi_escalation': [10, 20, 45, 90],
            })

        # ── 2. CANNOT ALLOCATE MEMORY (too few reflections) ───────────
        if 'CANNOT ALLOCATE MEMORY' in upper_text:
            diagnostics.append({
                'error': 'allocate_memory',
                'message': 'Cannot allocate memory (too few reflections per batch) — increasing DELPHI',
                'fix': {'DELPHI': '20'},
                'severity': 'fatal',
                'strategy': 'retry_integrate',
                '_delphi_escalation': [20, 45, 90],
            })

        # ── 3. Cell / distance runaway detection ──────────────────────
        # Parse the per-image table and check if POSITION (detector distance)
        # or cell parameters drift monotonically.
        # We look at the IER column: IER != 0 means refinement trouble.
        # Also check if the last few SIGMAR values blow up.
        ier_nonzero = 0
        total_images = 0
        sigmar_vals = []
        for line in lines:
            stripped = line.strip()
            # Parse IMAGE IER SCALE ... SIGMAB SIGMAR table rows
            if stripped and stripped[0].isdigit():
                parts = stripped.split()
                if len(parts) >= 10:
                    try:
                        img = int(parts[0])
                        ier = int(parts[1])
                        sigmar = float(parts[-1])
                        total_images += 1
                        if ier != 0:
                            ier_nonzero += 1
                        sigmar_vals.append(sigmar)
                    except (ValueError, IndexError):
                        pass

        # Check for runaway: last 10 SIGMAR values much larger than first 10
        if len(sigmar_vals) > 20:
            first_10 = [v for v in sigmar_vals[:10] if v > 0]
            last_10 = [v for v in sigmar_vals[-10:] if v > 0]
            if first_10 and last_10:
                avg_first = sum(first_10) / len(first_10)
                avg_last = sum(last_10) / len(last_10)
                if avg_first > 0 and avg_last / avg_first > 3.0:
                    diagnostics.append({
                        'error': 'parameter_runaway',
                        'message': 'Geometric parameters diverging — removing CELL from INTEGRATE refinement',
                        'fix': {'REFINE(INTEGRATE)': 'BEAM POSITION ORIENTATION'},
                        'severity': 'warning',
                        'strategy': 'retry_integrate',
                    })

        # ── 4. Many images with IER != 0 ──────────────────────────────
        if total_images > 10 and ier_nonzero > total_images * 0.3:
            # Don't duplicate if runaway already diagnosed
            if not any(d['error'] == 'parameter_runaway' for d in diagnostics):
                diagnostics.append({
                    'error': 'high_ier_rate',
                    'message': f'{ier_nonzero}/{total_images} images with integration errors',
                    'fix': {'DELPHI': '20'},
                    'severity': 'warning',
                    'strategy': 'retry_integrate',
                })

        return diagnostics

    @staticmethod
    def diagnose_correct(lp_content, statistics_table=None):
        """Diagnose CORRECT.LP issues and return suggestions.

        Returns list of dicts with same structure as diagnose_idxref.
        Unlike IDXREF/INTEGRATE, CORRECT rarely has fatal errors.
        This mostly identifies quality issues that benefit from reprocessing.
        """
        diagnostics = []
        upper_text = lp_content.upper()

        # ── 1. Ice rings detected in statistics table ──────────────────
        # If statistics_table provided, use existing detect_ice_rings.
        if statistics_table:
            ice_rings = LPParser.detect_ice_rings(statistics_table)
            # Data are only thrown away on strong or moderate evidence: the same
            # rings the ice-ring panel pre-ticks and the figures mark.
            detected = [r for r in ice_rings if LPParser.ice_ring_is_actionable(r)]
            if detected:
                exclude_ranges = {}
                for ring in detected:
                    key = 'EXCLUDE_RESOLUTION_RANGE'
                    if key not in exclude_ranges:
                        exclude_ranges[key] = []
                    exclude_ranges[key].append(f"{ring['lo']} {ring['hi']}")

                # Build fix dict: EXCLUDE_RESOLUTION_RANGE entries
                fix = {}
                for ring in detected:
                    # Use individual entries; XDS supports multiple
                    fix.setdefault('_exclude_resolution_ranges', []).append(
                        {'lo': ring['lo'], 'hi': ring['hi'], 'label': ring['label']}
                    )

                confidence_counts = {}
                for r in detected:
                    c = r.get('confidence', 'weak')
                    confidence_counts[c] = confidence_counts.get(c, 0) + 1
                summary_parts = []
                for c in ('strong', 'moderate', 'weak'):
                    if c in confidence_counts:
                        summary_parts.append(f"{confidence_counts[c]} {c}")

                diagnostics.append({
                    'error': 'ice_rings_detected',
                    'message': f'Ice rings detected ({", ".join(summary_parts)}) — adding exclusion ranges',
                    'fix': fix,
                    'severity': 'warning',
                    'strategy': 'retry_correct',
                })

        # ── 2. Very low ISa (overall data quality) ────────────────────
        # ISa < 5 indicates severe systematic problems.
        # CORRECT.LP prints:
        #    a        b          ISa    ISa0   INPUT DATA SET
        #  5.607E-01  5.363E-01    1.82    2.10 XDS_ASCII.HKL
        # OR in the summary section:
        #    a        b          ISa
        #  1.658E+00  1.369E-01    2.10
        lines = lp_content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Match header line — can have ISa0 and INPUT DATA SET columns too
            if ('ISa' in stripped and
                    stripped.replace(' ', '').startswith('ab') and
                    'ISa' in stripped):
                # Parse the data line(s) following the header
                for row in lines[i + 1:i + 5]:
                    parts = row.strip().split()
                    if len(parts) >= 3:
                        try:
                            # Column 3 is ISa (columns: a, b, ISa, [ISa0], [filename])
                            float(parts[0])  # verify it's a data row
                            isa_val = float(parts[2])
                            if isa_val < 5.0:
                                diagnostics.append({
                                    'error': 'low_isa',
                                    'message': f'ISa = {isa_val:.1f} — very low data quality (< 5.0)',
                                    'fix': {},
                                    'severity': 'warning',
                                    'strategy': 'info_only',
                                })
                            break
                        except (ValueError, IndexError):
                            continue
                break

        return diagnostics

    @staticmethod
    def determine_resolution_cutoff(statistics_table, criterion='isig2'):
        """Determine resolution cutoff from CORRECT/XSCALE statistics table.

        Args:
            statistics_table: list of dicts from parse_correct/parse_xscale
            criterion: one of 'isig2', 'cc_half_50', 'r_obs_55', 'cc_half_sig'

        Returns dict with:
          - resolution: float or None — suggested cutoff (Å)
          - criterion: str — which criterion was used
          - shell_index: int or None — index in table
          - all_cutoffs: dict — cutoffs for all four criteria
        """
        result = {
            'resolution': None, 'criterion': criterion,
            'shell_index': None, 'all_cutoffs': {}
        }

        if not statistics_table:
            return result

        # Parse shells (skip 'total' row)
        shells = []
        for i, row in enumerate(statistics_table):
            res_str = row.get('resolution', '')
            if not res_str or res_str.lower() == 'total':
                continue
            try:
                d = float(res_str)
            except (ValueError, TypeError):
                continue
            try:
                isig = float(row.get('i_sigma', ''))
            except (ValueError, TypeError):
                isig = None
            try:
                cc = float(row.get('cc_half', '').replace('*', '').replace('%', ''))
            except (ValueError, TypeError):
                cc = None
            try:
                robs = float(row.get('r_obs', '').replace('%', ''))
            except (ValueError, TypeError):
                robs = None
            try:
                nano = int(row.get('nano', '0'))
            except (ValueError, TypeError):
                nano = 0
            try:
                siganom = float(row.get('siganom', '0'))
            except (ValueError, TypeError):
                siganom = 0.0

            shells.append({
                'idx': i, 'd': d, 'isig': isig, 'cc': cc,
                'robs': robs, 'nano': nano, 'siganom': siganom,
            })

        if not shells:
            return result

        # One definition for the whole program (interface, AutoPilot, batch,
        # figures): the point where the statistic crosses its threshold,
        # interpolated linearly in 1/d² between the two shells around it.
        # The log prints the HIGH limit of each shell, but the statistic is the
        # mean over the whole shell: it is attached to the middle of the shell
        # in 1/d². (Attached to the limit, every cut-off came out about half a
        # shell too optimistic.) The first shell starts at 1/d² = 0.
        low_edge = 0.0
        for s in shells:
            high_edge = 1.0 / (s['d'] * s['d'])
            s['inv_d2'] = 0.5 * (low_edge + high_edge)
            low_edge = high_edge
            s['star'] = '*' in str(statistics_table[s['idx']].get('cc_half', ''))

        def _crossing(field, threshold, cross_above):
            """(d, reached). reached is False when every shell passes."""
            for k in range(1, len(shells)):
                v0, v1 = shells[k - 1][field], shells[k][field]
                if v0 is None or v1 is None:
                    continue
                if cross_above:
                    crossed = v0 <= threshold < v1
                else:
                    crossed = v0 >= threshold > v1
                if crossed:
                    frac = (threshold - v0) / (v1 - v0)
                    inv = shells[k - 1]['inv_d2'] + frac * (shells[k]['inv_d2'] - shells[k - 1]['inv_d2'])
                    if inv > 0:
                        return (1.0 / inv) ** 0.5, True
            # No clean crossing. If the last shell fails (values not monotonic),
            # cut at the last shell that still passes; if all fail, the first.
            last = shells[-1][field]
            if len(shells) >= 2 and last is not None:
                fails = last > threshold if cross_above else last < threshold
                if fails:
                    for s in reversed(shells):
                        v = s[field]
                        if v is None:
                            continue
                        if (v <= threshold) if cross_above else (v >= threshold):
                            return s['d'], True
                    return shells[0]['d'], True
            # Every shell passes: all the data can be kept.
            return (shells[-1]['d'] if last is not None else None), False

        reached = {}
        for key, field, threshold, above in (('isig2', 'isig', 2.0, False),
                                             ('cc_half_50', 'cc', 50.0, False),
                                             ('r_obs_55', 'robs', 55.0, True)):
            value, reached[key] = _crossing(field, threshold, above)
            result['all_cutoffs'][key] = round(value, 2) if value is not None else None

        # ── CC½ significance ──────────────────────────────────────────
        # The last shell whose CC½ XDS marks with '*' (significant at the 0.1 %
        # level; Karplus & Diederichs, 2012). Not a fixed percentage.
        starred = [s for s in shells if s['star']]
        if starred:
            result['all_cutoffs']['cc_half_sig'] = starred[-1]['d']
            reached['cc_half_sig'] = starred[-1] is not shells[-1]
        else:
            # A log without significance marks: fall back on I/σ.
            result['all_cutoffs']['cc_half_sig'] = result['all_cutoffs']['isig2']
            reached['cc_half_sig'] = reached['isig2']
        result['reached'] = reached

        # Select the requested criterion
        chosen = result['all_cutoffs'].get(criterion)
        result['resolution'] = chosen

        # The shell the cut-off falls in or next to (for marking a table row)
        if chosen is not None:
            nearest = min(shells, key=lambda s: abs(s['d'] - chosen))
            result['shell_index'] = nearest['idx']

        return result

    @staticmethod
    def generate_resolution_shells(d_max, d_min, n_shells=20):
        """Generate evenly-spaced resolution shells in 1/d² space.

        Args:
            d_max: low-resolution limit (Å), e.g. 50.0
            d_min: high-resolution limit (Å), e.g. 2.0
            n_shells: number of shells

        Returns list of (d_hi, d_lo) tuples from low-res to high-res.
        Each shell is defined by its outer (higher-res) boundary.
        """
        if d_max <= d_min or d_max <= 0 or d_min <= 0:
            return []

        import math
        s2_min = 1.0 / (d_max * d_max)
        s2_max = 1.0 / (d_min * d_min)
        step = (s2_max - s2_min) / n_shells

        shells = []
        for i in range(n_shells):
            s2_lo = s2_min + i * step
            s2_hi = s2_min + (i + 1) * step
            d_lo = 1.0 / math.sqrt(s2_lo) if s2_lo > 0 else d_max
            d_hi = 1.0 / math.sqrt(s2_hi)
            shells.append((round(d_hi, 2), round(d_lo, 2)))

        return shells

    # ── Ice Ring Detection ─────────────────────────────────────────────────────
    # Standard ice ring d-spacings (Å) and recommended exclusion half-widths.
    # Hexagonal ice Ih: Dowell & Rinfret (1960) Nature 188, 1144.
    # Cubic ice Ic: Kuhs et al. (1987) J. Physique 48, C1-631.
    # Half-widths chosen to match common practice in XDS/autoPROC/xia2.
    ICE_RING_POSITIONS = [
        # (d_spacing_Å, half_width_Å, label, form)
        (3.897, 0.030, '3.90', 'Ih'),
        (3.669, 0.025, '3.67', 'Ih'),
        (3.441, 0.025, '3.44', 'Ih'),
        (2.671, 0.020, '2.67', 'Ih'),
        (2.249, 0.020, '2.25', 'Ih/Ic'),
        (2.072, 0.015, '2.07', 'Ih'),
        (1.948, 0.015, '1.95', 'Ih'),
        (1.918, 0.015, '1.92', 'Ih'),
        (1.883, 0.015, '1.88', 'Ih'),
        (1.721, 0.015, '1.72', 'Ih'),
    ]

    @staticmethod
    def ice_ring_is_actionable(ring):
        """The one rule for acting on a detected ring (excluding it, marking it)."""
        return bool(ring.get('detected') and ring.get('in_range', True)
                    and ring.get('confidence') in ('strong', 'moderate'))

    @staticmethod
    def detect_ice_rings(statistics_table):
        """Analyse CORRECT.LP resolution shell statistics for ice ring signatures.

        For each known ice ring position that falls within the data resolution
        range, compare the shell overlapping that position against its immediate
        neighbours.  Ice rings cause:
          - intensity spikes  (I/sigma anomalously high relative to neighbours)
          - completeness drops (reflections near ice rings are rejected)
          - R-meas spikes     (poor merging of ice-contaminated reflections)

        Returns a list of dicts, one per ice ring position, with:
          - d, label, form: ring identity
          - lo, hi: suggested EXCLUDE_RESOLUTION_RANGE bounds
          - in_range: bool, whether the ring falls within data limits
          - detected: bool, whether statistical evidence of ice was found
          - confidence: 'strong' | 'moderate' | 'weak' | None
          - indicators: dict of what was detected
          - shell_idx: index into statistics_table of the overlapping shell (or None)
        """
        # Parse shells into numeric arrays
        shells = []
        for si, row in enumerate(statistics_table):
            res = row.get('resolution', '')
            if not res or res.lower() == 'total':
                continue
            try:
                d = float(res)
            except (ValueError, TypeError):
                continue
            if d <= 0:
                continue
            try:
                i_sig = float(row.get('i_sigma', ''))
            except (ValueError, TypeError):
                i_sig = None
            try:
                comp = float(str(row.get('completeness', '')).replace('%', ''))
            except (ValueError, TypeError):
                comp = None
            try:
                r_meas = float(str(row.get('r_meas', '')).replace('%', ''))
            except (ValueError, TypeError):
                r_meas = None
            shells.append({
                'idx': si, 'd': d, 'i_sigma': i_sig,
                'completeness': comp, 'r_meas': r_meas
            })

        if not shells:
            return []

        # Data resolution limits
        d_max = max(s['d'] for s in shells)  # low-res limit
        d_min = min(s['d'] for s in shells)  # high-res limit

        results = []
        for d_ring, hw, label, form in LPParser.ICE_RING_POSITIONS:
            entry = {
                'd': d_ring, 'label': label, 'form': form,
                'lo': round(d_ring + hw, 3),
                'hi': round(d_ring - hw, 3),
                'in_range': d_min <= d_ring <= d_max,
                'detected': False, 'confidence': None,
                'indicators': {}, 'shell_idx': None
            }

            if not entry['in_range']:
                results.append(entry)
                continue

            # Find the shell whose d-spacing is closest to this ring
            best_si = None
            best_dist = 999.0
            for i, s in enumerate(shells):
                dist = abs(s['d'] - d_ring)
                if dist < best_dist:
                    best_dist = dist
                    best_si = i

            if best_si is None:
                results.append(entry)
                continue

            entry['shell_idx'] = shells[best_si]['idx']
            ring_shell = shells[best_si]

            # Collect neighbour shells (up to 2 on each side, excluding the ring shell)
            neighbours = []
            for offset in [-2, -1, 1, 2]:
                ni = best_si + offset
                if 0 <= ni < len(shells):
                    neighbours.append(shells[ni])

            if not neighbours:
                results.append(entry)
                continue

            # -- Indicator 1: completeness drop --
            if ring_shell['completeness'] is not None:
                neigh_comp = [n['completeness'] for n in neighbours if n['completeness'] is not None]
                if neigh_comp:
                    avg_comp = sum(neigh_comp) / len(neigh_comp)
                    comp_drop = avg_comp - ring_shell['completeness']
                    if comp_drop > 3.0:
                        entry['indicators']['completeness_drop'] = round(comp_drop, 1)

            # -- Indicator 2: R-meas spike --
            if ring_shell['r_meas'] is not None:
                neigh_rmeas = [n['r_meas'] for n in neighbours if n['r_meas'] is not None]
                if neigh_rmeas:
                    avg_rmeas = sum(neigh_rmeas) / len(neigh_rmeas)
                    if avg_rmeas > 0:
                        rmeas_ratio = ring_shell['r_meas'] / avg_rmeas
                        if rmeas_ratio > 1.3:
                            entry['indicators']['rmeas_spike'] = round(rmeas_ratio, 2)

            # -- Indicator 3: I/sigma anomaly --
            if ring_shell['i_sigma'] is not None:
                neigh_isig = [n['i_sigma'] for n in neighbours if n['i_sigma'] is not None]
                if neigh_isig:
                    avg_isig = sum(neigh_isig) / len(neigh_isig)
                    if avg_isig > 0:
                        isig_ratio = ring_shell['i_sigma'] / avg_isig
                        if isig_ratio > 1.5:
                            entry['indicators']['isigma_spike'] = round(isig_ratio, 2)
                        elif isig_ratio < 0.6 and avg_isig > 1.0:
                            entry['indicators']['isigma_drop'] = round(isig_ratio, 2)

            # -- Score the detection --
            n_indicators = len(entry['indicators'])
            if n_indicators >= 3:
                entry['detected'] = True
                entry['confidence'] = 'strong'
            elif n_indicators == 2:
                entry['detected'] = True
                entry['confidence'] = 'moderate'
            elif n_indicators == 1:
                # One indicator alone is weak evidence unless it is a large one:
                # completeness more than 8 points below the neighbours, or R-meas
                # or I/sigma more than twice theirs.
                ind = entry['indicators']
                large = (ind.get('completeness_drop', 0) > 8.0
                         or ind.get('rmeas_spike', 0) > 2.0
                         or ind.get('isigma_spike', 0) > 2.0)
                entry['detected'] = True
                entry['confidence'] = 'moderate' if large else 'weak'

            results.append(entry)

        return results
