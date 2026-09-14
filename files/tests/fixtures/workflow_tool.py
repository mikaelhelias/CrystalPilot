"""Deterministic external-tool stand-in. Only reads/writes its scratch cwd."""
import json
from pathlib import Path
import re
import shutil
import sys
import time

tool = sys.argv[1]
fixtures = Path(__file__).parent / 'real'
control = json.loads(Path('control.json').read_text()) if Path('control.json').exists() else {}
inp = Path('XDS.INP' if tool == 'xds' else tool.upper() + '.INP')
jobs = re.search(r'^JOB\s*=\s*(.*)', inp.read_text(), re.M).group(1).split() if tool == 'xds' else [tool.upper()]
for step in jobs:
    with Path('executed.jsonl').open('a') as f:
        f.write(json.dumps(step) + '\n')
    print('starting ' + step, flush=True)
    mode = control.get(step, 'ok')
    if mode == 'quiet':
        time.sleep(30)
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
