class XDSINPEditor:
    """Parse and edit individual parameters in XDS.INP content"""

    # Parameters that can be toggled (commented/uncommented)
    TOGGLEABLE = {"SPACE_GROUP_NUMBER", "UNIT_CELL_CONSTANTS", "EXCLUDE_DATA_RANGE", "SIGNAL_PIXEL",
                  "STRICT_ABSORPTION_CORRECTION", "MINIMUM_I/SIGMA", "REFLECTIONS/CORRECTION_FACTOR",
                  "CORRECTIONS", "REFINE(INTEGRATE)", "INCLUDE_RESOLUTION_RANGE", "RESOLUTION_SHELLS",
                  "LIB", "MINIMUM_FRACTION_OF_INDEXED_SPOTS"}

    # Parameters that can appear multiple times in XDS.INP
    REPEATABLE = {"SPOT_RANGE", "DATA_RANGE", "EXCLUDE_DATA_RANGE", "EXCLUDE_RESOLUTION_RANGE"}

    # Geometry / orientation parameters that must NEVER be modified by the
    # key-parameter editor.  These are beamline-specific and set once during
    # XDS.INP generation or by the user manually.  Overwriting them with
    # defaults causes indexing failures on non-standard goniometer setups.
    PROTECTED = {
        "DIRECTION_OF_DETECTOR_X-AXIS",
        "DIRECTION_OF_DETECTOR_Y-AXIS",
        "ROTATION_AXIS",
        "INCIDENT_BEAM_DIRECTION",
        "FRACTION_OF_POLARIZATION",
        "POLARIZATION_PLANE_NORMAL",
    }

    # A keyword followed by '=' (XDS keywords may contain ' / ( ) - . digits)
    _PAIR_RE = re.compile(r"([^\s=!]+)\s*=")

    @staticmethod
    def _split_pairs(text):
        """Split one XDS.INP line into its KEY=VALUE pairs and trailing comment.

        'NX= 2463 NY= 2527 ! detector'  ->  ([['NX', '2463'], ['NY', '2527']], '! detector')
        XDS allows several keywords per line; beamline templates use that a lot.
        """
        body, comment = text, ''
        if '!' in text:
            body, comment = text.split('!', 1)
            comment = '!' + comment
        found = list(XDSINPEditor._PAIR_RE.finditer(body))
        pairs = []
        for i, m in enumerate(found):
            end = found[i + 1].start() if i + 1 < len(found) else len(body)
            pairs.append([m.group(1), body[m.end():end].strip()])
        return pairs, comment.strip()

    @staticmethod
    def _join_pairs(pairs, comment):
        s = '  '.join(f'{k}= {v}'.rstrip() for k, v in pairs)
        return (s + ('  ' + comment if comment else '')).rstrip()

    @staticmethod
    def apply_params(content, params):
        """
        Apply a dict of {PARAM_NAME: value_or_None} to XDS.INP text.
        - value=None means: comment the line out (prefix with '!')
        - For toggleable params, value='__commented__' also comments it out.
        - Range params (DATA_RANGE, OSCILLATION_RANGE, EXCLUDE_DATA_RANGE, SPOT_RANGE) expect
          a list/tuple of 2 values, OR an array of [start, end] pairs for multiple ranges.
        - UNIT_CELL_CONSTANTS expects a list of 6 values.
        Lines holding several keywords ('NX= 2463 NY= 2527 QX= 0.172 QY= 0.172')
        keep the keywords that were not edited.
        Returns the modified content string.
        """
        lines = content.split('\n')
        for param, value in params.items():
            pu = param.upper()
            if pu in XDSINPEditor.PROTECTED:
                continue
            comment_out = value is None or value == '__commented__'
            multi = (not comment_out and pu in XDSINPEditor.REPEATABLE and
                     isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)))
            parsed = []
            for i, line in enumerate(lines):
                commented = line.lstrip().startswith('!')
                text = line.lstrip('! \t') if commented else line
                pairs, tail = XDSINPEditor._split_pairs(text)
                hit = any(k.upper() == pu for k,v in pairs)
                if commented and not re.match(re.escape(pu) + r'\s*=', text, re.I):
                    hit = False
                parsed.append((line, commented, pairs, tail, hit))
            active = [i for i,(_,c,_,_,hit) in enumerate(parsed) if hit and not c]
            comments = [i for i,(_,c,_,_,hit) in enumerate(parsed) if hit and c]
            selected = active[-1] if active else (comments[0] if comments else None)
            out, ranges_written = [], False
            for i,(line,commented,pairs,tail,hit) in enumerate(parsed):
                if not hit or (commented and not multi and (active or comment_out)):
                    out.append(line)
                    continue
                remaining = [[k,v] for k,v in pairs if k.upper() != pu]
                old_values = [v for k,v in pairs if k.upper() == pu]
                if not multi and not comment_out and i == selected and commented and len(pairs) > 1:
                    # The only occurrence is on a commented line that holds other keywords too
                    # ('!SPACE_GROUP_NUMBER= 0  UNIT_CELL_CONSTANTS= 0 0 0 0 0 0'): activate this
                    # keyword on its own line; its neighbours stay commented.
                    out.append(XDSINPEditor._join_pairs([[param, XDSINPEditor._format_value(param, value)]], ''))
                    others = [[k, v] for k, v in pairs if k.upper() != pu]
                    out.append('!' + XDSINPEditor._join_pairs(others, tail))
                    continue
                if not multi and not comment_out and i == selected:
                    # Preserve the location and neighbors of the effective key.
                    new_pairs = []
                    last = max(j for j,(k,v) in enumerate(pairs) if k.upper() == pu)
                    for j,(k,v) in enumerate(pairs):
                        if k.upper() != pu:
                            new_pairs.append([k,v])
                        elif j == last:
                            new_pairs.append([param, XDSINPEditor._format_value(param, value)])
                    out.append(XDSINPEditor._join_pairs(new_pairs, tail))
                    continue
                if remaining:
                    out.append(('!' if commented else '') + XDSINPEditor._join_pairs(remaining, tail))
                elif tail:
                    out.append(tail)
                if comment_out and not commented:
                    out.extend('!' + param + '= ' + v for v in old_values)
                if multi and not ranges_written:
                    for rng in value:
                        prefix = '!' if len(rng) >= 3 and rng[2] else ''
                        out.append(prefix + param + '= ' + XDSINPEditor._format_value(param, rng[:2]))
                    ranges_written = True
            if selected is None:
                if multi:
                    for rng in value:
                        prefix = '!' if len(rng) >= 3 and rng[2] else ''
                        out.append(prefix + param + '= ' + XDSINPEditor._format_value(param, rng[:2]))
                elif not comment_out:
                    out.append(param + '= ' + XDSINPEditor._format_value(param, value))
                elif pu in XDSINPEditor.TOGGLEABLE:
                    out.append('!' + param + '= ')
            lines = out
        return '\n'.join(lines)

    @staticmethod
    def _format_value(param, value):
        """Format a parameter value to its XDS string representation.

        XDS.INP values are whitespace-separated numbers or words, so any list
        or tuple (ranges, cell constants, vectors, BACKGROUND_RANGE, ...)
        becomes its elements joined by spaces.  Writing Python's '[1, 10]'
        would make XDS stop with ILLEGAL KEYWORD OR PARAMETER VALUE."""
        if isinstance(value, (list, tuple)):
            return ' '.join(str(v) for v in value)
        if isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        return str(value)

