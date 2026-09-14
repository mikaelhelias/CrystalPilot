class ImageHeaderReader:
    """Read geometry metadata from diffraction image headers.

    Supports CBF (Pilatus), HDF5/NeXus (Eiger), SMV/ADSC (.img),
    MarCCD/Rayonix (.tiff), MAR345, and R-AXIS (.osc).

    Returns a dict with canonical keys:
        wavelength          (Å)
        detector_distance   (mm)
        x_pixel_size        (mm)
        y_pixel_size        (mm)
        beam_center_x       (pixels)
        beam_center_y       (pixels)
        osc_range           (degrees)
        osc_start           (degrees)
        nx, ny              (pixels — image dimensions)
        nframes             (total frames)
        detector_name       (human-readable, if identified)
    """

    # Detector lookup table: (NX, NY, fmt_hint, qx, qy, name)
    _DET_LIST = [
        (2463, 2527, 'cbf',  0.172,  0.172,  'PILATUS 6M'),
        (2463, 5071, 'cbf',  0.172,  0.172,  'PILATUS 12M'),
        (1475, 1679, 'cbf',  0.172,  0.172,  'PILATUS 3M'),
        ( 981, 1043, 'cbf',  0.172,  0.172,  'PILATUS 1M'),
        ( 487,  619, 'cbf',  0.172,  0.172,  'PILATUS 300K'),
        ( 487,  407, 'cbf',  0.172,  0.172,  'PILATUS 200K'),
        ( 487,  195, 'cbf',  0.172,  0.172,  'PILATUS 100K'),
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
        (2048, 2048, 'img',  0.1024, 0.1024, 'ADSC Q210'),
        (4096, 4096, 'img',  0.051,  0.051,  'ADSC Q210r'),
        (3072, 3072, 'img',  0.10259,0.10259,'ADSC Q315'),
        (6144, 6144, 'img',  0.0513, 0.0513, 'ADSC Q315r'),
        (2304, 2304, 'img',  0.0816, 0.0816, 'ADSC Q4r'),
        (4096, 4096, 'tif',  0.07342,0.07342,'Rayonix MX300'),
        (3072, 3072, 'tif',  0.07345,0.07345,'Rayonix MX225'),
        (2048, 2048, 'tif',  0.079,  0.079,  'Rayonix MX165'),
        (2300, 2300, 'mar',  0.150,  0.150,  'MAR345 2300'),
        (3450, 3450, 'mar',  0.100,  0.100,  'MAR345 3450'),
        (3000, 3000, 'osc',  0.100,  0.100,  'R-AXIS IV/V'),
    ]

    @staticmethod
    def read(filepath):
        """Read image header from filepath. Returns dict of canonical metadata."""
        filepath = str(filepath)
        ext = Path(filepath).suffix.lower()
        header = {}

        try:
            if ext in ('.h5', '.hdf5'):
                header = ImageHeaderReader._read_hdf5(filepath)
            else:
                header = ImageHeaderReader._read_fabio(filepath, ext)
        except Exception as e:
            header['_error'] = str(e)

        # Lookup detector by dimensions if pixel size still unknown
        nx = int(header.get('nx', 0))
        ny = int(header.get('ny', 0))
        if nx > 0 and ny > 0 and 'x_pixel_size' not in header:
            fmt_lower = ext.lstrip('.').lower()
            for dnx, dny, fmt, qx, qy, name in ImageHeaderReader._DET_LIST:
                if dnx == nx and dny == ny:
                    if fmt is None or fmt in fmt_lower:
                        header['x_pixel_size'] = str(qx)
                        header['y_pixel_size'] = str(qy)
                        header['detector_name'] = name
                        break

        # Name the detector from its dimensions when the header did not say
        if nx > 0 and ny > 0 and 'detector_name' not in header:
            fmt_lower = ext.lstrip('.').lower()
            for dnx, dny, fmt, qx, qy, name in ImageHeaderReader._DET_LIST:
                if dnx == nx and dny == ny and (fmt is None or fmt in fmt_lower):
                    header['detector_name'] = name
                    break

        return header

    @staticmethod
    def _read_hdf5(filepath):
        """Extract header from HDF5/Eiger master file."""
        filepath = _resolve_h5_template(filepath)
        import h5py
        try:
            import hdf5plugin  # noqa: F401
        except ImportError:
            pass

        # Metadata always comes from the master file when one exists —
        # data chunk files (PREFIX_data_000001.h5) carry no geometry at all.
        _master = _h5_find_master(filepath)
        if _master:
            filepath = _master

        def _h5log(msg):
            try:
                print(msg)
            except Exception:
                pass

        header = {}

        import numpy as np

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
                if isinstance(u, (bytes, np.bytes_)): u = u.decode()
                return str(u).lower().strip()
            except Exception:
                return ''

        def _to_mm(v, units):
            """Detector distance / sensor thickness to mm.  Without units a
            value below 1 is taken as metres (NeXus default)."""
            av = abs(v)
            if units in ('mm', 'millimeter', 'millimetre', 'millimeters', 'millimetres'):
                return av
            elif units in ('cm', 'centimeter', 'centimetre'):
                return av * 10.0
            elif units in ('m', 'meter', 'meters', 'metre', 'metres'):
                return av * 1000.0
            elif units in ('um', 'µm', 'micrometer', 'micrometre', 'micron', 'microns'):
                return av / 1000.0
            else:
                return av * 1000.0 if av < 1.0 else av

        def _pixel_to_mm(v, units):
            """Pixel size to mm.  Pixels are 0.05-0.2 mm, so an unlabelled
            value below 1 is already mm (7.5e-05 is metres, 75 is microns)."""
            av = abs(v)
            if units in ('mm', 'millimeter', 'millimetre', 'millimeters', 'millimetres'):
                return av
            elif units in ('m', 'meter', 'meters', 'metre', 'metres'):
                return av * 1000.0
            elif units in ('um', 'µm', 'micrometer', 'micrometre', 'micron', 'microns'):
                return av / 1000.0
            elif units in ('cm', 'centimeter', 'centimetre'):
                return av * 10.0
            if av < 0.001:
                return av * 1000.0      # metres without a units attribute
            if av >= 1.0:
                return av / 1000.0      # microns without a units attribute
            return av

        with h5py.File(filepath, 'r') as f:
            # Image dimensions from first data chunk
            if 'entry/data' in f:
                edata = f['entry/data']
                chunk_keys = sorted(k for k in edata.keys() if k.startswith('data_'))
                total_frames = 0
                for ck in chunk_keys:
                    try:
                        ds = edata[ck]
                        if ds.ndim == 3:
                            if 'ny' not in header:
                                header['ny'] = str(ds.shape[1])
                                header['nx'] = str(ds.shape[2])
                            total_frames += ds.shape[0]
                    except Exception:
                        pass
                if total_frames > 0:
                    header['nframes'] = str(total_frames)
            if 'entry/data/data' in f and 'ny' not in header:
                ds = f['entry/data/data']
                if ds.ndim == 3:
                    header['ny'] = str(ds.shape[1])
                    header['nx'] = str(ds.shape[2])
                    header['nframes'] = str(ds.shape[0])

            # ── DECTRIS detector identity and limits (SIMPLON master layout) ──
            def _h5text(path):
                try:
                    v = f[path][()]
                    if hasattr(v, 'flat') and not isinstance(v, (bytes, str)):
                        v = v.flat[0]
                    if isinstance(v, (bytes, np.bytes_)):
                        v = v.decode('utf-8', 'replace')
                    v = str(v).strip()
                    return v or None
                except Exception:
                    return None
            _det = '/entry/instrument/detector/'
            _spec = _det + 'detectorSpecific/'
            _desc = _h5text(_det + 'description')
            if _desc:
                header['detector_name'] = _desc          # e.g. "Dectris EIGER2 Si 16M"
            _mat = _h5text(_det + 'sensor_material')
            if _mat:
                header['sensor_material'] = _mat
            try:
                _ds = f[_det + 'sensor_thickness']
                _thick = _h5scalar(_ds)
                if _thick and _thick > 0:
                    header['sensor_thickness'] = str(round(_to_mm(_thick, _h5units(_ds)), 4))
            except Exception:
                pass
            try:
                _cut = _h5scalar(f[_spec + 'countrate_correction_count_cutoff'])
                if _cut and _cut > 0:
                    header['overload'] = str(int(_cut))  # XDS OVERLOAD= for Eiger
            except Exception:
                pass
            try:
                _bits = _h5scalar(f[_det + 'bit_depth_readout'])
                if _bits and _bits > 0:
                    header['bit_depth'] = str(int(_bits))
            except Exception:
                pass
            # nimages × ntrigger is the declared frame count; use it when the
            # data links could not be followed (chunk files not copied yet).
            try:
                _nimg = _h5scalar(f[_spec + 'nimages'])
                _ntrig = _h5scalar(f[_spec + 'ntrigger']) or 1
                _declared = int(_nimg * _ntrig) if _nimg else 0
                if _declared > 0 and int(header.get('nframes', 0)) == 0:
                    header['nframes'] = str(_declared)
            except Exception:
                pass

            # Explicit NeXus paths — must match frame viewer's comprehensive list
            _paths = [
                # detector distance
                ('detector_distance', '/entry/instrument/detector/distance'),
                ('detector_distance', '/entry/instrument/detector/detector_distance'),
                ('detector_distance', '/entry/instrument/detector/sample_detector_distance'),
                ('detector_distance', '/entry/instrument/detector/detector_distance/value'),
                ('detector_distance', '/entry/instrument/detector_z/value'),
                ('detector_distance', '/entry/instrument/detector_z/data'),
                ('detector_distance', '/entry/instrument/detector/detectorSpecific/detector_distance'),
                # wavelength — comprehensive list for all known Eiger firmware versions
                ('wavelength', '/entry/instrument/beam/incident_wavelength'),
                ('wavelength', '/entry/instrument/monochromator/wavelength'),
                ('wavelength', '/entry/sample/beam/incident_wavelength'),
                ('wavelength', '/entry/instrument/beam/wavelength'),
                ('wavelength', '/entry/instrument/beam/photon_wavelength'),
                ('wavelength', '/entry/instrument/monochromator/incident_wavelength'),
                ('wavelength', '/entry/instrument/beam/incident_wavelength/value'),
                ('wavelength', '/entry/instrument/detector/detectorSpecific/wavelength'),
                # pixel size
                ('x_pixel_size', '/entry/instrument/detector/x_pixel_size'),
                ('y_pixel_size', '/entry/instrument/detector/y_pixel_size'),
                ('x_pixel_size', '/entry/instrument/detector/detectorSpecific/x_pixel_size'),
                ('y_pixel_size', '/entry/instrument/detector/detectorSpecific/y_pixel_size'),
                # beam center
                ('beam_center_x', '/entry/instrument/detector/beam_center_x'),
                ('beam_center_y', '/entry/instrument/detector/beam_center_y'),
                ('beam_center_x', '/entry/instrument/detector/detectorSpecific/beam_center_x'),
                ('beam_center_y', '/entry/instrument/detector/detectorSpecific/beam_center_y'),
                # oscillation range — must be in explicit paths for debug visibility
                ('osc_range', '/entry/sample/goniometer/omega_range_average'),
                ('osc_range', '/entry/sample/goniometer/oscillation_range'),
                ('osc_range', '/entry/sample/goniometer/omega_range'),
                ('osc_range', '/entry/sample/goniometer/angle_increment'),
                ('osc_range', '/entry/sample/goniometer/omega_increment'),
                ('osc_range', '/entry/sample/goniometer/phi_range_average'),
                ('osc_range', '/entry/sample/goniometer/phi_increment'),
                ('osc_range', '/entry/instrument/detector/detectorSpecific/omega_range_average'),
                ('osc_range', '/entry/instrument/detector/detectorSpecific/omega_increment'),
                ('osc_range', '/entry/instrument/detector/detectorSpecific/angle_increment'),
                ('osc_range', '/entry/sample/transformations/omega_range_average'),
                ('osc_range', '/entry/sample/transformations/omega_increment'),
                ('osc_range', '/entry/scan/omega_increment'),
                ('osc_range', '/entry/scan/angle_increment'),
                # oscillation start
                ('osc_start', '/entry/sample/goniometer/omega_start'),
                ('osc_start', '/entry/sample/goniometer/phi_start'),
                ('osc_start', '/entry/instrument/detector/detectorSpecific/omega_start'),
            ]
            _debug_log = []
            for canon, epath in _paths:
                if canon in header:
                    _debug_log.append(f'  SKIP {epath} ({canon} already set)')
                    continue
                try:
                    ds = f[epath]
                    if not isinstance(ds, h5py.Dataset):
                        _debug_log.append(f'  SKIP {epath} (not a Dataset, type={type(ds).__name__})')
                        continue
                    v = _h5scalar(ds)
                    if v is None:
                        _debug_log.append(f'  SKIP {epath} (scalar=None)')
                        continue
                    units = _h5units(ds)
                    _debug_log.append(f'  FOUND {epath} = {v} units={units!r}')
                    if canon == 'wavelength':
                        if units in ('m', 'meter', 'meters', 'metre', 'metres'):
                            v = v * 1e10
                        elif units in ('nm', 'nanometer', 'nanometre', 'nanometers', 'nanometres'):
                            v = v * 10.0
                        elif units in ('angstrom', 'angstroms', '\u00c5', 'a', '\u212b'):
                            pass  # already Angstroms
                        elif units in ('ev', 'electronvolt', 'electron_volt'):
                            v = 12398.419 / v if v > 0 else None
                        elif units in ('kev', 'kiloelectronvolt'):
                            v = 12398.419 / (v * 1000.0) if v > 0 else None
                        elif not units:
                            # No units: heuristic — if value is reasonable for Å (0.1–10), use as-is
                            # if very small (< 0.01), likely meters; if large (> 100), likely eV
                            if v > 100:
                                v = 12398.419 / v  # probably eV
                            elif v < 0.01:
                                v = v * 1e10  # probably meters
                            # else: assume Angstroms
                        if v is not None and 0.1 < v < 20:
                            header[canon] = str(round(v, 6))
                        else:
                            _debug_log.append(f'  REJECT {epath}: wavelength={v} outside 0.1-20 Å')
                            continue
                    elif canon in ('detector_distance', 'x_pixel_size', 'y_pixel_size'):
                        v = _to_mm(v, units) if canon == 'detector_distance' else _pixel_to_mm(v, units)
                        header[canon] = str(round(v, 6))
                    elif canon == 'osc_range':
                        # Oscillation range must be positive and < 90 degrees
                        if v > 0 and v < 90:
                            header[canon] = str(round(v, 6))
                        else:
                            _debug_log.append(f'  REJECT {epath}: osc_range={v} outside 0-90°')
                            continue
                    elif canon == 'osc_start':
                        header[canon] = str(round(v, 4))
                    else:
                        header[canon] = str(round(v, 6))
                except Exception as exc:
                    _debug_log.append(f'  ERR  {epath}: {exc}')
            _h5log(f'[ImageHeaderReader] HDF5 explicit paths for {filepath}:')
            for ln in _debug_log:
                _h5log(ln)
            _h5log(f'[ImageHeaderReader] Header so far: { {k: v for k,v in header.items() if not k.startswith("_")} }')

            # Photon energy → wavelength (if direct wavelength not found)
            if 'wavelength' not in header:
                for epath in ('/entry/instrument/beam/photon_energy',
                              '/entry/instrument/monochromator/energy',
                              '/entry/instrument/beam/energy',
                              '/entry/instrument/detector/detectorSpecific/photon_energy',
                              '/entry/instrument/beam/incident_energy'):
                    try:
                        ds = f[epath]
                        if not isinstance(ds, h5py.Dataset):
                            continue
                        eV = _h5scalar(ds)
                        if eV is None or eV <= 0: continue
                        u = _h5units(ds)
                        _debug_log.append(f'  ENERGY {epath} = {eV} units={u!r}')
                        if u in ('kev', 'kiloelectronvolt', 'kiloelectronvolts'):
                            eV = eV * 1000.0
                        elif u in ('ev', 'electronvolt', 'electronvolts', ''):
                            # Heuristic: if value < 100, likely keV not eV
                            if eV < 100:
                                eV = eV * 1000.0
                        wl = 12398.419 / eV
                        if 0.1 < wl < 20:
                            header['wavelength'] = str(round(wl, 6))
                            _debug_log.append(f'  -> wavelength = {wl:.6f} A from energy {eV} eV')
                            break
                    except Exception:
                        pass

            # Oscillation from NeXus — try many known paths (all known Eiger firmware
            # versions, DECTRIS SIMPLON API, NeXus NXtransformations, and beamline-
            # specific custom layouts)
            _osc_scalar_paths = [
                '/entry/sample/goniometer/omega_range_average',
                '/entry/sample/goniometer/oscillation_range',
                '/entry/sample/goniometer/omega_range',
                '/entry/sample/goniometer/angle_increment',
                '/entry/sample/goniometer/omega_increment',
                '/entry/sample/goniometer/phi_range_average',
                '/entry/sample/goniometer/phi_increment',
                '/entry/sample/goniometer/phi_range',
                '/entry/sample/goniometer/chi_increment',
                '/entry/sample/goniometer/kappa_increment',
                # DECTRIS detectorSpecific (newer firmware)
                '/entry/instrument/detector/detectorSpecific/omega_range_average',
                '/entry/instrument/detector/detectorSpecific/omega_increment',
                '/entry/instrument/detector/detectorSpecific/angle_increment',
                # NXtransformations (NeXus 2014+ standard)
                '/entry/sample/transformations/omega_range_average',
                '/entry/sample/transformations/omega_increment',
                # Some beamlines put it directly under scan
                '/entry/scan/omega_increment',
                '/entry/scan/angle_increment',
            ]
            for osc_path in _osc_scalar_paths:
                if 'osc_range' in header:
                    break
                try:
                    ds = f[osc_path]
                    if not isinstance(ds, h5py.Dataset):
                        continue
                    v = _h5scalar(ds)
                    if v is not None and v > 0 and v < 90:
                        header['osc_range'] = str(round(v, 6))
                        _debug_log.append(f'  OSC_RANGE from {osc_path} = {v}')
                        break
                except Exception:
                    pass

            # Compute oscillation from total range / nimages if available
            if 'osc_range' not in header:
                for total_path in ('/entry/sample/goniometer/omega_range_total',
                                   '/entry/instrument/detector/detectorSpecific/omega_range_total'):
                    try:
                        ds = f[total_path]
                        total_v = _h5scalar(ds)
                        nf = int(header.get('nframes', 0))
                        if total_v and total_v > 0 and nf > 0:
                            osc = total_v / nf
                            if 0 < osc < 90:
                                header['osc_range'] = str(round(osc, 6))
                                _debug_log.append(f'  OSC_RANGE from {total_path}/nframes = {total_v}/{nf} = {osc}')
                                break
                    except Exception:
                        pass

            # Compute from omega/phi angle arrays if still missing
            if 'osc_range' not in header:
                for arr_path in ('/entry/sample/goniometer/omega',
                                 '/entry/sample/goniometer/phi',
                                 '/entry/sample/transformations/omega',
                                 '/entry/sample/transformations/phi'):
                    try:
                        ds = f[arr_path]
                        if ds.ndim == 1 and ds.shape[0] >= 2:
                            v0 = float(ds[0])
                            v1 = float(ds[1])
                            delta = abs(v1 - v0)
                            if 0 < delta < 90:
                                header['osc_range'] = str(round(delta, 6))
                                header['osc_start'] = str(round(v0, 4))
                                _debug_log.append(f'  OSC_RANGE from array diff {arr_path}[1]-[0] = {delta}')
                                break
                            # Try endpoints: total_range / n_elements
                            elif ds.shape[0] > 2:
                                vn = float(ds[-1])
                                total = abs(vn - v0)
                                npts = ds.shape[0]
                                step = total / npts if npts > 0 else 0
                                if 0 < step < 90:
                                    header['osc_range'] = str(round(step, 6))
                                    header['osc_start'] = str(round(v0, 4))
                                    _debug_log.append(f'  OSC_RANGE from array endpoints {arr_path} total={total}/{npts} = {step}')
                                    break
                    except Exception:
                        pass

            # Oscillation start
            if 'osc_start' not in header:
                for start_path in ('/entry/sample/goniometer/omega_start',
                                   '/entry/sample/goniometer/phi_start',
                                   '/entry/sample/goniometer/omega',
                                   '/entry/sample/goniometer/phi',
                                   '/entry/sample/transformations/omega',
                                   '/entry/sample/transformations/phi',
                                   '/entry/instrument/detector/detectorSpecific/omega_start'):
                    try:
                        ds = f[start_path]
                        v = _h5scalar(ds)
                        if v is not None:
                            header['osc_start'] = str(round(v, 4))
                            break
                    except Exception:
                        pass

            # Subgroup walk for anything still missing
            _geo_keys = {
                'detector_distance', 'distance', 'sample_detector_distance',
                'beam_center_x', 'beam_center_y',
                'x_pixel_size', 'y_pixel_size',
                'incident_wavelength', 'wavelength', 'photon_wavelength',
                'omega_range_average', 'oscillation_range', 'angle_increment',
                'omega_increment', 'phi_increment', 'chi_increment',
                'photon_energy',
            }
            _key_canon = {
                'incident_wavelength': 'wavelength',
                'photon_wavelength': 'wavelength',
                'distance': 'detector_distance',
                'sample_detector_distance': 'detector_distance',
                'omega_range_average': 'osc_range',
                'oscillation_range': 'osc_range',
                'angle_increment': 'osc_range',
                'omega_increment': 'osc_range',
                'phi_increment': 'osc_range',
                'chi_increment': 'osc_range',
            }
            def _walk(name, obj):
                try:
                    if not isinstance(obj, h5py.Dataset): return
                    key = name.split('/')[-1].lower()
                    if key not in _geo_keys: return
                    v = _h5scalar(obj)
                    if v is None or v == 0: return
                    canon = _key_canon.get(key, key)
                    if canon in header: return
                    units = _h5units(obj)
                    if canon in ('detector_distance', 'x_pixel_size', 'y_pixel_size'):
                        v = _to_mm(v, units) if canon == 'detector_distance' else _pixel_to_mm(v, units)
                    elif canon == 'wavelength':
                        if units in ('m', 'meter', 'meters', 'metre'): v *= 1e10
                        elif units in ('nm', 'nanometer', 'nanometre'): v *= 10.0
                        elif units in ('angstrom', 'angstroms', '\u00c5', 'a', '\u212b'): pass
                        elif not units and v < 0.01: v *= 1e10
                        if not (0.1 < v < 20): return  # reject unreasonable wavelength
                    elif key == 'photon_energy':
                        # an energy only stands in for a wavelength the file does not state
                        # (detectorSpecific/photon_energy is the detector's threshold setting)
                        if 'wavelength' in header: return
                        # Convert energy to wavelength
                        if units in ('kev', 'kiloelectronvolt'): v *= 1000.0
                        elif not units and v < 100: v *= 1000.0  # heuristic: likely keV
                        wl = 12398.419 / v if v > 0 else 0
                        if not (0.1 < wl < 20): return
                        canon = 'wavelength'
                        v = wl
                    elif canon == 'osc_range':
                        if not (0 < v < 90): return  # reject unreasonable oscillation
                    header[canon] = str(round(v, 6))
                except Exception:
                    pass
            for subgrp in ('entry/instrument', 'entry/sample'):
                if subgrp in f:
                    try: f[subgrp].visititems(_walk)
                    except Exception: pass

            # Diagnostic: print oscillation status
            if 'osc_range' in header:
                _h5log(f'[ImageHeaderReader] Oscillation: osc_range={header["osc_range"]}, osc_start={header.get("osc_start", "NOT FOUND")}')
            else:
                _h5log('[ImageHeaderReader] WARNING: osc_range NOT FOUND in HDF5 file. XDS requires OSCILLATION_RANGE.')
                _h5log('[ImageHeaderReader] Searched explicit paths, scalar paths, total_range/nimages, array diffs, and subgroup walk.')

        header['_h5_debug'] = '\n'.join(_debug_log) if _debug_log else 'no explicit path log'
        return header

    @staticmethod
    def _read_fabio(filepath, ext):
        """Extract header from non-HDF5 images via fabio."""
        import fabio
        header = {}

        if ext == '.osc':
            from fabio.raxisimage import RaxisImage
            img_obj = RaxisImage()
            img_obj.read(filepath)
        else:
            img_obj = fabio.open(filepath)

        header['ny'] = str(img_obj.data.shape[0])
        header['nx'] = str(img_obj.data.shape[1])
        header['nframes'] = str(getattr(img_obj, 'nframes', 1))

        def _unwrap(v):
            if isinstance(v, tuple) and len(v) == 1: return v[0]
            return v
        raw = {k.strip(): str(_unwrap(v)).strip() for k, v in img_obj.header.items()}

        def _flt(s):
            try: return float(str(s).split()[0])
            except Exception: return None

        # ── CBF: pilatus_headers ──
        ph = getattr(img_obj, 'pilatus_headers', None)
        if ph is not None:
            try:
                if 'Pixel_size' in ph:
                    px = ph['Pixel_size']
                    header['x_pixel_size'] = str(round(float(px[0]) * 1000.0, 6))
                    header['y_pixel_size'] = str(round(float(px[1]) * 1000.0, 6))
                if 'Detector_distance' in ph:
                    header['detector_distance'] = str(round(abs(float(ph['Detector_distance'])) * 1000.0, 4))
                if 'Wavelength' in ph:
                    header['wavelength'] = str(round(float(ph['Wavelength']), 6))
                if 'Beam_xy' in ph:
                    bxy = ph['Beam_xy']
                    header['beam_center_x'] = str(round(float(bxy[0]), 4))
                    header['beam_center_y'] = str(round(float(bxy[1]), 4))
                if 'Alpha_increment' in ph:
                    v = float(ph['Alpha_increment'])
                    if v > 0:
                        header['osc_range'] = str(round(v, 6))
                if 'Phi_increment' in ph:
                    v = float(ph['Phi_increment'])
                    if v > 0 and 'osc_range' not in header:
                        header['osc_range'] = str(round(v, 6))
                if 'Start_angle' in ph:
                    header['osc_start'] = str(round(float(ph['Start_angle']), 4))
            except (TypeError, IndexError, ValueError, KeyError):
                pass  # Non-standard CBF (e.g. XDS diagnostic)

        # ── CBF fallback: _array_data.header_contents miniheader ──
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
                    m2 = _re.search(r'Pixel_size\s+[\d.eE+\-]+\s+\S+\s+x\s+([\d.eE+\-]+)', _mini, _re.IGNORECASE)
                    vy = float(m2.group(1)) * 1000.0 if m2 else v
                    header['y_pixel_size'] = str(round(vy, 6))
            if 'beam_center_x' not in header:
                m2 = _re.search(r'Beam_xy\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)', _mini, _re.IGNORECASE)
                if m2:
                    header['beam_center_x'] = str(round(float(m2.group(1)), 4))
                    header['beam_center_y'] = str(round(float(m2.group(2)), 4))
            # Oscillation
            if 'osc_range' not in header:
                v = _mini_flt(r'Angle_increment\s+([\d.eE+\-]+)', _mini)
                if v: header['osc_range'] = str(round(v, 6))
            if 'osc_start' not in header:
                v = _mini_flt(r'Start_angle\s+([\d.eE+\-]+)', _mini)
                if v is not None: header['osc_start'] = str(round(v, 4))

        # ── ADSC/SMV .img ──
        if 'x_pixel_size' not in header:
            v = _flt(raw.get('PIXEL_SIZE'))
            if v:
                header['x_pixel_size'] = str(round(v, 6))
                header['y_pixel_size'] = str(round(v, 6))
        if 'detector_distance' not in header:
            v = _flt(raw.get('DISTANCE'))
            if v: header['detector_distance'] = str(round(abs(v), 4))
        if 'wavelength' not in header:
            v = _flt(raw.get('WAVELENGTH'))
            if v and v > 0.01: header['wavelength'] = str(round(v, 6))
        if 'beam_center_x' not in header:
            cx = _flt(raw.get('BEAM_CENTER_X'))
            cy = _flt(raw.get('BEAM_CENTER_Y'))
            qx = _flt(header.get('x_pixel_size'))
            if cx and cy and qx:
                header['beam_center_x'] = str(round(cx / qx, 4))
                header['beam_center_y'] = str(round(cy / qx, 4))
        if 'osc_range' not in header:
            for okey in ('OSC_RANGE', 'ROTATION_RANGE', 'PHI_RANGE',
                         'OMEGA_RANGE', 'ROTATION_WIDTH', 'DELTA_PHI',
                         'DELTA_OMEGA', 'ANGULAR_RANGE', 'SCAN_RANGE',
                         'ROTATION_ANGLE', 'OSCILLATION_RANGE'):
                v = _flt(raw.get(okey))
                if v and v > 0:
                    header['osc_range'] = str(round(v, 6))
                    break
        # SMV fallback: compute from OSC_END - OSC_START (common in ADSC headers)
        if 'osc_range' not in header:
            osc_s = _flt(raw.get('OSC_START'))
            osc_e = _flt(raw.get('OSC_END'))
            if osc_s is not None and osc_e is not None and abs(osc_e - osc_s) > 0:
                header['osc_range'] = str(round(abs(osc_e - osc_s), 6))
        if 'osc_start' not in header:
            for skey in ('OSC_START', 'PHI', 'OMEGA', 'ROTATION_START',
                         'PHI_START', 'OMEGA_START'):
                v = _flt(raw.get(skey))
                if v is not None:
                    header['osc_start'] = str(round(v, 4))
                    break

        # ── R-AXIS / OSC ──
        if 'x_pixel_size' not in header:
            v = _flt(raw.get('X Pixel Length'))
            if v:
                header['x_pixel_size'] = str(round(v, 6))
                vy = _flt(raw.get('Y Pixel Length')) or v
                header['y_pixel_size'] = str(round(vy, 6))
        if 'detector_distance' not in header:
            v = _flt(raw.get('Crystal-to-detector Distance'))
            if v: header['detector_distance'] = str(round(abs(v), 4))
        if 'wavelength' not in header:
            v = _flt(raw.get('Wavelength'))
            if v and v > 0.01: header['wavelength'] = str(round(v, 6))
        if 'beam_center_x' not in header:
            cx = _flt(raw.get('Direct beam X position'))
            cy = _flt(raw.get('Direct beam Y position'))
            qx = _flt(header.get('x_pixel_size'))
            if cx and cy and qx:
                header['beam_center_x'] = str(round(cx * 0.1 / qx, 4))
                header['beam_center_y'] = str(round(cy * 0.1 / qx, 4))
        # R-AXIS oscillation: try several known header keys, then compute from start/end
        if 'osc_range' not in header:
            for okey in ('Oscillation Range', 'Phi oscillation range',
                         'Omega oscillation range', 'oscillation_range'):
                v = _flt(raw.get(okey))
                if v and v > 0:
                    header['osc_range'] = str(round(v, 6))
                    break
        if 'osc_range' not in header:
            # Compute from end - start (fabio RIGAKU_KEYS use these exact names)
            for (skey, ekey) in [('Phi Oscillation Start', 'Phi Oscillation Stop'),
                                 ('Phi start', 'Phi end'),
                                 ('Omega start', 'Omega end'),
                                 ('Start Phi', 'End Phi'),
                                 ('Start Omega', 'End Omega'),
                                 ('Goniometer Start ax.1', 'Goniometer End ax.1')]:
                s = _flt(raw.get(skey))
                e = _flt(raw.get(ekey))
                if s is not None and e is not None and abs(e - s) > 0:
                    header['osc_range'] = str(round(abs(e - s), 6))
                    if 'osc_start' not in header:
                        header['osc_start'] = str(round(s, 4))
                    break
        if 'osc_start' not in header:
            for skey in ('Phi Oscillation Start', 'Phi Datum',
                         'Phi start', 'Omega start', 'Start Phi', 'Start Omega',
                         'Goniometer Start ax.1'):
                v = _flt(raw.get(skey))
                if v is not None:
                    header['osc_start'] = str(round(v, 4))
                    break

        # Generic fallback: scan all raw header keys for oscillation-related values
        if 'osc_range' not in header:
            for rk, rv in raw.items():
                rkl = rk.lower()
                if (('osc' in rkl or 'rotation' in rkl) and 'range' in rkl) or 'increment' in rkl:
                    v = _flt(rv)
                    if v and 0 < v < 90:
                        header['osc_range'] = str(round(v, 6))
                        break

        # Identify detector name from dimensions + format if not yet set
        if 'detector_name' not in header:
            nx = int(header.get('nx', 0))
            ny = int(header.get('ny', 0))
            if nx > 0 and ny > 0:
                fmt_lower = ext.lstrip('.').lower()
                for dnx, dny, fmt, qx, qy, dname in ImageHeaderReader._DET_LIST:
                    if dnx == nx and dny == ny:
                        if fmt is None or fmt in fmt_lower:
                            header['detector_name'] = dname
                            break

        return header


