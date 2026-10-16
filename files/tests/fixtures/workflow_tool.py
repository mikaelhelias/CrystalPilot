"""Deterministic external-tool stand-in. Only reads/writes its scratch cwd."""
import json
from pathlib import Path
import re
import shutil
import sys
import time

tool = sys.argv[1]
fixtures = Path(__file__).parent / 'real'
# Auto-indexing trial folders link the project's files (Linux, macOS; Windows
# makes no links): a run is controlled and recorded where it happens, never
# through such a link.
_ctl = Path('control.json')
control = json.loads(_ctl.read_text()) if _ctl.is_file() and not _ctl.is_symlink() else {}
if Path('executed.jsonl').is_symlink():
    Path('executed.jsonl').unlink()
inp = Path('XDS.INP' if tool == 'xds' else tool.upper() + '.INP')
jobs = re.search(r'^JOB\s*=\s*(.*)', inp.read_text(), re.M).group(1).split() if tool == 'xds' else [tool.upper()]
for step in jobs:
    with Path('executed.jsonl').open('a') as f:
        f.write(json.dumps(step) + '\n')
    print('starting ' + step, flush=True)
    mode = control.get(step, 'ok')
    if mode == 'quiet':
        time.sleep(30)
    if mode == 'wait':            # until the test writes 'release' (or 30 s)
        deadline = time.time() + 30
        while not Path('release').exists() and time.time() < deadline:
            time.sleep(0.05)
    if mode == 'exit':
        raise SystemExit(7)
    if mode == 'exit_again' and Path('executed.jsonl').read_text().splitlines().count(json.dumps(step)) > 1:
        raise SystemExit(7)   # the step works once, fails when it runs again
    if mode == 'missing':
        continue
    if mode == 'lp_error':
        Path(step + '.LP').write_text('!!! ERROR !!! invalid test input\n')
        break
    if tool in ('f2mtz', 'cad'):
        Path(sys.argv[sys.argv.index('HKLOUT') + 1]).write_bytes(b'fresh test MTZ output')
        continue
    source = fixtures / (step + '.LP')
    if step == 'XPLAN':
        Path('XPLAN.LP').write_text('Simulated successful XPLAN\n')
    else:
        shutil.copyfile(source, step + '.LP')
    if step == 'CORRECT' and control.get('axial') == 'P41212':
        # axial reflections of a P4(1)2(1)2 crystal: h00 only h=2n, 00l only l=4n.
        # XDS's own choice (no SPACE_GROUP_NUMBER) is the group without screws, P422.
        given = re.search(r'^\s*SPACE_GROUP_NUMBER\s*=\s*(\d+)', inp.read_text(), re.M)
        sg = int(given.group(1)) if given and int(given.group(1)) else 89
        lines = Path('CORRECT.LP').read_text().split('\n')
        top = next(i for i, l in enumerate(lines) if 'H    K    L  RESOLUTION' in l)
        end = next(i for i, l in enumerate(lines) if 'COMPLETENESS AND QUALITY' in l)
        rows = []
        for hkl, n, period in (((1, 0, 0), 30, 2), ((0, 0, 1), 40, 4)):
            for i in range(1, n + 1):
                absent = i % period != 0
                isig = 0.3 if absent else 31.0
                rows.append('%5d%5d%5d%10.3f  %11.4E %11.4E %12.2f %11d%s' % (
                    hkl[0] * i, hkl[1] * i, hkl[2] * i, 100.0 / i, isig, 1.0, isig, 4,
                    '*' if absent and sg == 92 else ' '))
        lines = [' SPACE_GROUP_NUMBER=   %d' % sg if 'SPACE_GROUP_NUMBER=' in l else l for l in lines]
        Path('CORRECT.LP').write_text('\n'.join(lines[:top + 1] + [''] + rows + [''] + lines[end:]))
    if step == 'CORRECT':
        header = "!FORMAT=XDS_ASCII MERGE=FALSE FRIEDEL'S_LAW=TRUE\n!SPACE_GROUP_NUMBER=20\n!UNIT_CELL_CONSTANTS=98.56 119.66 161.55 90 90 90\n!END_OF_HEADER\n"
        Path('XDS_ASCII.HKL').write_text(header + '1 1 1 100 3 1 1 1 1 1\n' * 200 + '!END_OF_DATA\n')
        Path('GXPARM.XDS').write_text('test geometry\n')
    if step == 'XSCALE':
        output = re.search(r'^OUTPUT_FILE\s*=\s*(\S+)', inp.read_text(), re.M).group(1)
        shutil.copyfile('XDS_ASCII.HKL', output)
    if step == 'XDSCONV':
        Path('F2MTZ.INP').write_text('END\n')
        Path('temp.hkl').write_text('test conversion input\n')
