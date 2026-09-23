class XDSINPGenerator:
    """Generate a minimal but complete XDS.INP from image header metadata."""

    # Map detector name prefixes to XDS DETECTOR= keyword and characteristics
    # (xds_name, overload, sensor_thickness, min_valid, value_range_lo, value_range_hi)
    _DETECTOR_DB = {
        'PILATUS':  ('PILATUS',  1048576, 0.32,  0, 6000, 30000),
        'EIGER2':   ('EIGER',    131071,  0.45,  0, 6000, 30000),
        'EIGER':    ('EIGER',    65535,   0.45,  0, 6000, 30000),
        'ADSC':     ('ADSC',     65535,   0.0,   1, 6, 30000),
        'Rayonix':  ('CCDCHESS', 65535,   0.0,   1, 6, 30000),
        'MarCCD':   ('CCDCHESS', 65535,   0.0,   1, 6, 30000),
        'MAR345':   ('MAR345',   130000,  0.0,   0, 0, 131072),
        'MAR555':   ('MARCCD',   65000,   0.0,   0, 0, 65000),
        'R-AXIS':   ('RAXIS',    1000000, 0.0,   0, 6, 30000),
        'Saturn':   ('SATURN',   262112,  0.0,   0, 6, 30000),
        'Bruker':   ('BRUKER',   250000,  0.0,   0, 6, 30000),
        'NOIR':     ('ADSC',     65535,   0.0,   1, 6, 30000),
    }

    @staticmethod
    def frame_numbers(template):
        """(first, last, count) of the frames on disk for a ?-template, or None.

        Frames are not always numbered from 1 (0-899, 101-1000, a sweep
        continued in a second run), so DATA_RANGE must come from the files.
        """
        import glob as _glob, os as _os, re as _re
        template = str(template)
        name = _os.path.basename(template)
        m = _re.search(r"\?+(?=[^?]*$)", name)
        if not m:
            return None
        rx = _re.compile("^" + _re.escape(name[:m.start()]) + r"(\d{%d})" % (m.end() - m.start()) + _re.escape(name[m.end():]) + "$")
        numbers = []
        for path in _glob.glob(template.replace("?", "[0-9]")):
            hit = rx.match(_os.path.basename(path))
            if hit:
                numbers.append(int(hit.group(1)))
        if not numbers:
            return None
        return min(numbers), max(numbers), len(numbers)

    @staticmethod
    def _lookup_detector(det_name):
        """Find detector DB entry by matching prefix of det_name."""
        if not det_name:
            return None
        # Substring match: Eiger master files describe the detector as e.g.
        # "Dectris EIGER2 Si 16M", so a prefix test would never hit.  The DB
        # lists EIGER2 before EIGER so the more specific key wins.
        up = det_name.upper()
        for prefix, info in XDSINPGenerator._DETECTOR_DB.items():
            if prefix.upper() in up:
                return info
        return None

    @staticmethod
    def generate(template_path, header, lib_path=None):
        """Generate XDS.INP content from a NAME_TEMPLATE and image header dict.

        Args:
            template_path: XDS-style template (with ?????? wildcards)
            header: dict from ImageHeaderReader.read()
            lib_path: optional path to HDF5 reader library (dectris-neggia.so)
                      for Eiger/HDF5 data.  Injected as LIB= in XDS.INP.

        Returns:
            (content_str, warnings_list)
        """
        warnings = []

        def _g(key, fallback=None):
            v = header.get(key)
            if v is not None:
                try: return float(v)
                except Exception: pass
            if fallback is not None:
                warnings.append(f'{key} not found in image header, using default {fallback}')
            return fallback

        nx = int(_g('nx', 0))
        ny = int(_g('ny', 0))
        qx = _g('x_pixel_size')
        qy = _g('y_pixel_size')
        wavelength = _g('wavelength')
        det_dist = _g('detector_distance')
        orgx = _g('beam_center_x')
        orgy = _g('beam_center_y')
        osc = _g('osc_range')
        osc_start = _g('osc_start', 0.0)
        nframes = int(_g('nframes', 1))
        det_name = header.get('detector_name', '')

        # Beam center: if in mm, need to convert; if already pixels, use directly
        # Our header reader always returns pixels, so use as-is
        # Default beam center = image center if not found
        if orgx is None and nx > 0 and qx:
            orgx = nx / 2.0
            warnings.append('Beam center X not in header, defaulting to image center')
        if orgy is None and ny > 0 and qy:
            orgy = ny / 2.0
            warnings.append('Beam center Y not in header, defaulting to image center')

        # Detector lookup
        det_info = XDSINPGenerator._lookup_detector(det_name)
        if det_info is None:
            # Guess from pixel size
            if qx and abs(qx - 0.172) < 0.005:
                det_info = XDSINPGenerator._DETECTOR_DB['PILATUS']
                det_name = det_name or 'PILATUS (guessed from pixel size)'
            elif qx and abs(qx - 0.075) < 0.005:
                det_info = XDSINPGenerator._DETECTOR_DB['EIGER']
                det_name = det_name or 'EIGER (guessed from pixel size)'
            else:
                det_info = ('PILATUS', 1048576, 0.32, 0, 6000, 30000)
                warnings.append('Could not identify detector type, defaulting to PILATUS. '
                                'Verify DETECTOR=, OVERLOAD=, SENSOR_THICKNESS=, and '
                                'VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS=.')

        xds_det, overload, sensor_thick, min_valid, vr_lo, vr_hi = det_info

        # Prefer the limits recorded in the image header: Eiger master files
        # state the count-rate correction cutoff (XDS OVERLOAD=) and the sensor
        # thickness (0.45 mm Si vs 0.75 mm CdTe) explicitly.
        _hdr_overload = _g('overload')
        if _hdr_overload and _hdr_overload > 0:
            overload = int(_hdr_overload)
        _hdr_thick = _g('sensor_thickness')
        if _hdr_thick and _hdr_thick > 0:
            sensor_thick = _hdr_thick

        # The frame numbers on disk (the caller may know them); numbering need not start at 1
        try:
            first_frame = int(header.get('first_frame', 1))
        except (TypeError, ValueError):
            first_frame = 1
        try:
            last_frame = int(header.get('last_frame', first_frame + nframes - 1))
        except (TypeError, ValueError):
            last_frame = first_frame + nframes - 1

        # Spot range: first 90 degrees or first 50 frames minimum
        if osc and osc > 0 and nframes > 1:
            frames_for_90 = int(90.0 / osc)
            spot_end = min(frames_for_90, nframes)
        else:
            spot_end = min(50, nframes)
        spot_end = max(spot_end, min(50, nframes))  # at least 50 frames if available

        lines = []
        lines.append('! XDS.INP generated by CrystalPilot')
        lines.append('! *** VERIFY ALL PARAMETERS BEFORE PROCESSING ***')
        if warnings:
            for w in warnings:
                lines.append(f'!   WARNING: {w}')
        lines.append('')

        lines.append('JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT')
        lines.append('')

        lines.append(f'DETECTOR= {xds_det}')
        lines.append(f'OVERLOAD= {overload}')
        if sensor_thick > 0:
            lines.append(f'SENSOR_THICKNESS= {sensor_thick}')
        lines.append(f'MINIMUM_VALID_PIXEL_VALUE= {min_valid}')
        # VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS: not needed for pixel-counting
        # detectors (EIGER, PILATUS) which have built-in pixel masking via
        # MINIMUM_VALID_PIXEL_VALUE. Only active for CCD-type detectors.
        if xds_det in ('EIGER', 'PILATUS'):
            lines.append(f'!VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS= {vr_lo} {vr_hi}')
        else:
            lines.append(f'VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS= {vr_lo} {vr_hi}')
        lines.append('TRUSTED_REGION= 0.0 1.05')
        lines.append('')

        if nx and ny:
            lines.append(f'NX= {nx}')
            lines.append(f'NY= {ny}')
        if qx and qy:
            lines.append(f'QX= {qx}')
            lines.append(f'QY= {qy}')
        if orgx is not None and orgy is not None:
            lines.append(f'ORGX= {orgx:.1f}')
            lines.append(f'ORGY= {orgy:.1f}')
        if det_dist is not None:
            lines.append(f'DETECTOR_DISTANCE= {det_dist:.2f}')
        lines.append('')

        # Axis conventions (most common: single-axis phi/omega, beam along Z)
        lines.append('DIRECTION_OF_DETECTOR_X-AXIS= 1.0 0.0 0.0')
        lines.append('DIRECTION_OF_DETECTOR_Y-AXIS= 0.0 1.0 0.0')
        lines.append('ROTATION_AXIS= 1.0 0.0 0.0')
        lines.append('INCIDENT_BEAM_DIRECTION= 0.0 0.0 1.0')
        lines.append('FRACTION_OF_POLARIZATION= 0.99')
        lines.append('POLARIZATION_PLANE_NORMAL= 0.0 1.0 0.0')
        lines.append('')

        if wavelength:
            lines.append(f'X-RAY_WAVELENGTH= {wavelength}')
        else:
            lines.append('!X-RAY_WAVELENGTH= ')
            warnings.append('Wavelength not found in image header — set manually')
        if osc:
            lines.append(f'OSCILLATION_RANGE= {osc}')
        else:
            lines.append('!OSCILLATION_RANGE= ')
            warnings.append('Oscillation range not found in image header — set manually')
        if osc_start is not None:
            lines.append(f'STARTING_ANGLE= {osc_start}')
        # STARTING_ANGLE is read from the first file, so it belongs to the first frame number
        lines.append(f'STARTING_FRAME= {first_frame}')
        lines.append('')

        lines.append(f'NAME_TEMPLATE_OF_DATA_FRAMES= {template_path}')

        # HDF5 data (Eiger detectors) requires XDS to load an external reader
        # library via the LIB= keyword.  Inject it when the template points to
        # .h5 files and a library path is available.
        _tmpl_ext = template_path.rsplit('.', 1)[-1].lower() if '.' in template_path else ''
        if _tmpl_ext in ('h5', 'hdf5'):
            if lib_path:
                lines.append(f'LIB= {lib_path}')
            else:
                lines.append('!LIB=  ! <-- SET PATH TO dectris-neggia.so for HDF5 data')
                warnings.append('HDF5 template detected but no LIB= path provided. '
                                'XDS needs dectris-neggia.so (or equivalent) to read Eiger HDF5 data. '
                                'Set the HDF5 Library Path in AutoPilot settings or add LIB= manually.')

        lines.append(f'DATA_RANGE= {first_frame} {last_frame}')
        lines.append(f'SPOT_RANGE= {first_frame} {first_frame + spot_end - 1}')
        # a second wedge from the end, only where it does not overlap the first
        if last_frame - first_frame + 1 >= 2 * spot_end:
            lines.append(f'SPOT_RANGE= {last_frame - spot_end + 1} {last_frame}')
        lines.append(f'BACKGROUND_RANGE= {first_frame} {first_frame + min(10, nframes) - 1}')
        lines.append('')

        lines.append('!SPACE_GROUP_NUMBER= 0')
        lines.append('!UNIT_CELL_CONSTANTS= 0 0 0 0 0 0')
        lines.append('!EXCLUDE_DATA_RANGE= ')
        lines.append("FRIEDEL'S_LAW= TRUE")
        lines.append('')

        return _with_cpu_keywords('\n'.join(lines), 'xds'), warnings


# XSCALE.INP is hierarchical.  A keyword in the wrong level makes XSCALE stop
# with "!!! ERROR !!! MISPLACED PARAMETER", so every keyword is filed here.
_XSCALE_OUTPUT_KEYS = {"FRIEDEL'S_LAW", "MERGE", "STRICT_ABSORPTION_CORRECTION"}
_XSCALE_INPUT_KEYS = {"INCLUDE_RESOLUTION_RANGE", "CORRECTIONS", "CRYSTAL_NAME", "NBATCH",
                      "STARTING_DOSE", "DOSE_RATE", "EXCLUDE_RESOLUTION_RANGE"}
# everything else (SPACE_GROUP_NUMBER, UNIT_CELL_CONSTANTS, RESOLUTION_SHELLS,
# REFERENCE_DATA_SET, REIDX, WFAC1, MINIMUM_I/SIGMA, MAXIMUM_NUMBER_OF_PROCESSORS,
# SNRC, 0-DOSE_SIGNIFICANCE_LEVEL, PRINT_CORRELATIONS ...) is global.


def _xscale_key(line):
    """Keyword of an XSCALE.INP line, commented or not ('' for other lines)."""
    s = line.strip().lstrip('!').strip()
    if '=' not in s:
        return ''
    k = s.split('=', 1)[0].strip().upper()
    return k if k and ' ' not in k else ''


def _xscale_set(lines, key, value, indent):
    """Set key=value inside one section (list of lines), in place.

    - an existing line (active or commented) with that key is replaced
    - value '__commented__' comments the existing line out instead
    - otherwise the line is appended to the section
    """
    ukey = key.upper()
    for idx, ln in enumerate(lines):
        if _xscale_key(ln) == ukey:
            if value == '__commented__':
                if not ln.strip().startswith('!'):
                    lines[idx] = indent + '! ' + ln.strip()
            else:
                lines[idx] = f'{indent}{key}= {value}'
            return
    if value != '__commented__':
        lines.append(f'{indent}{key}= {value}')


def _xscale_apply_params(content, params):
    """Merge parameter values into XSCALE.INP content, section by section.

    params: {KEYWORD: value | '__commented__' | None, 'INPUT_FILE': [paths]}
      * INPUT_FILE (non-empty list) replaces the input files of the first
        OUTPUT_FILE block; per-input parameters already present are kept.
      * An empty INPUT_FILE list leaves the existing input files alone.
      * Global keywords go before the first OUTPUT_FILE, output keywords right
        after it, input keywords after every INPUT_FILE of the first block.
      * Keywords found in the wrong section of an existing file are moved to
        the right one, so a previously broken file is repaired on save.
    Other OUTPUT_FILE blocks and all comments are preserved.
    """
    params = dict(params or {})
    input_files = params.pop('INPUT_FILE', None)
    output_name = params.pop('OUTPUT_FILE', None)

    lines = content.split('\n') if content else []
    header, blocks, cur = [], [], None
    for ln in lines:
        if _xscale_key(ln) == 'OUTPUT_FILE' and not ln.strip().startswith('!'):
            cur = {'out': ln.strip(), 'body': []}
            blocks.append(cur)
        elif cur is None:
            header.append(ln)
        else:
            cur['body'].append(ln)
    if not blocks:
        blocks.append({'out': 'OUTPUT_FILE= ' + (output_name or 'merged.ahkl'), 'body': []})
    elif output_name and output_name != '__commented__':
        blocks[0]['out'] = 'OUTPUT_FILE= ' + output_name

    # First block: output keywords, then the inputs with their own keywords
    first = blocks[0]
    outp, inputs, cur_in, stray_input_params = [], [], None, []
    for ln in first['body']:
        k = _xscale_key(ln)
        active = not ln.strip().startswith('!')
        if k == 'INPUT_FILE' and active:
            cur_in = {'line': '  ' + ln.strip(), 'body': []}
            inputs.append(cur_in)
        elif k and active and k not in _XSCALE_OUTPUT_KEYS and k not in _XSCALE_INPUT_KEYS and k != 'INPUT_FILE':
            header.append(ln.strip())            # global keyword misplaced in the block
        elif cur_in is None:
            if k in _XSCALE_INPUT_KEYS and active:
                stray_input_params.append(ln.strip())   # input keyword before any INPUT_FILE
            else:
                outp.append(ln)
        else:
            cur_in['body'].append(ln)

    if isinstance(input_files, list):
        files = [str(f).strip() for f in input_files if f and str(f).strip()]
        if files:
            existing = {}
            for inp in inputs:
                filename = inp['line'].split('=', 1)[1].split('!')[0].strip()
                existing.setdefault(filename, []).append(inp)
            rebuilt = []
            for filename in files:
                matches = existing.get(filename, [])
                old = matches.pop(0) if matches else None
                rebuilt.append({'line': '  INPUT_FILE= ' + filename,
                                'body': list(old['body']) if old else []})
            inputs = rebuilt
    for stray in stray_input_params:
        k = _xscale_key(stray)
        v = stray.split('=', 1)[1].strip()
        for inp in inputs:
            _xscale_set(inp['body'], k, v, '    ')

    for key, value in params.items():
        if value is None or value == '':
            continue
        ukey = key.upper()
        if ukey in _XSCALE_INPUT_KEYS:
            for inp in inputs:
                _xscale_set(inp['body'], key, value, '    ')
        elif ukey in _XSCALE_OUTPUT_KEYS:
            _xscale_set(outp, key, value, '  ')
        else:
            _xscale_set(header, key, value, '')

    def _tidy(seq):
        while seq and not seq[-1].strip():
            seq.pop()
        return seq

    out = _tidy([l for l in header])
    if out:
        out.append('')
    out.append(first['out'])
    out.extend(_tidy(outp))
    for inp in inputs:
        out.append(inp['line'])
        out.extend(_tidy(inp['body']))
    for blk in blocks[1:]:
        out.append('')
        out.append(blk['out'])
        out.extend(_tidy(blk['body']))
    return '\n'.join(out) + '\n'
