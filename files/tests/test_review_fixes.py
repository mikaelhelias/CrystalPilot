"""Behavioral regressions for the September 2026 review. Uses scratch projects."""
import contextlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import unittest
import urllib.parse
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_units as battery
build = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else battery.newest_build()
m, scratch = battery.load_module(build)
server = m.ThreadingHTTPServer(('127.0.0.1', 0), m.XDSGUIHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()


def request(method, path, data=None, auth=True):
    c = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=10)
    headers = {'Content-Type': 'text/plain', 'Origin': 'http://unrelated.example'}
    if auth:
        headers['X-CrystalPilot-Token'] = m.API_TOKEN
    c.request(method, path, json.dumps(data) if data is not None else None, headers)
    r = c.getresponse()
    status, body = r.status, r.read()
    c.close()
    return status, json.loads(body) if body else None


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.name = self._testMethodName
        m.ProjectManager.create(self.name)
        self.p = m._pdir(self.name)
        self.url = '/api/projects/' + self.name
        (self.p/'XDS.INP').write_text('JOB= INIT\nNX= 100\n')

    def test_auth_and_exact_routes(self):
        before = (self.p/'XDS.INP').read_text()
        for prefix in ('/noauth/projects/', '/api/wrong/', '/foo/projects/'):
            for auth in (False, True):
                path = prefix + self.name + '/xdsinp'
                self.assertIn(request('POST',path,{'content':'changed'},auth)[0],(403,404))
                self.assertIn(request('GET',path,auth=auth)[0],(403,404))
        self.assertEqual(request('GET', self.url+'/xdsinp', auth=False)[0],403)
        self.assertEqual((self.p/'XDS.INP').read_text(),before)
        self.assertEqual(request('GET','/health',auth=False)[0],200)

    def test_names_metadata_settings_and_list_removal(self):
        for name in ('my proj', "O'Brien", 'unicode-μ', 'literal%20name', 'xdsinp-test', 'locations', 'ice-rings-data', '%2e%2e'):
            m.ProjectManager.create(name)
            p = m._pdir(name)
            (p/'data.keep').write_text('keep me')
            url = '/api/projects/' + urllib.parse.quote(name,safe='')
            status,data = request('GET',url)
            self.assertEqual(status,200,(name,data)); self.assertEqual(data['name'],name)
            self.assertEqual(request('POST',url+'/settings',{'viewer_template':'saved'})[0],200)
            self.assertEqual(m.ProjectManager.get(name)['viewer_template'],'saved')
            self.assertEqual(request('DELETE',url)[0],200)
            self.assertTrue((p/'data.keep').exists())
            self.assertFalse((p/'metadata.json').exists())
            self.assertNotIn(name,[p['name'] for p in request('GET','/api/projects')[1]])

    def test_encoded_traversal_rejected(self):
        for segment in ('%2e%2e','a%2fb','a%5cb'):
            self.assertEqual(request('GET','/api/projects/'+segment+'/xdsinp')[0],400)

    def test_busy_write_and_run_leave_input_and_history_intact(self):
        (self.p/'CORRECT.LP').write_text('old lp')
        before = (self.p/'XDS.INP').read_text()
        self.assertTrue(m._claim_dir(self.p))
        try:
            self.assertEqual(request('POST',self.url+'/xdsinp',{'content':'bad'})[0],409)
            self.assertEqual(request('DELETE',self.url)[0],409)
            self.assertEqual(request('POST','/api/run-folder',{'project_name':self.name,'folder':str(self.p/'new')})[0],409)
            events=[]
            with patch.object(m,'_find_xds_exe',return_value=Path(sys.executable)):
                m.stream_xds(self.name,['CORRECT'],events.append)
            self.assertTrue(any('already running' in e for e in events))
            self.assertEqual((self.p/'XDS.INP').read_text(),before)
            self.assertFalse((self.p/'CORRECT.LP.prev1').exists())
            self.assertFalse((self.p/'new').exists())
        finally:
            m._release_dir(self.p)

    def test_canonical_directory_and_nested_reservation(self):
        (self.p/'child').mkdir()
        self.assertTrue(m._claim_dir(self.p))
        try: self.assertFalse(m._claim_dir(self.p/'child'/'..'))
        finally: m._release_dir(self.p)
        with m._directory_reservation([self.p]):
            with m._directory_reservation([self.p/'child'/'..']): pass
        self.assertTrue(m._claim_dir(self.p)); m._release_dir(self.p)

    def _step_with_script(self,script):
        original=m._run_streaming
        def run(cmd,cwd,on_line,**kwargs):
            return original([sys.executable,'-c',script],cwd,on_line,**kwargs)
        with patch.object(m,'_find_xds_exe',return_value=Path(sys.executable)),patch.object(m,'_run_streaming',side_effect=run):
            return m.xds_runner.run_step(self.name,'INIT')

    def test_failed_process_cannot_reuse_old_output_but_leaves_it_readable(self):
        (self.p/'INIT.LP').write_text('old success')
        self.assertNotEqual(self._step_with_script('raise SystemExit(7)')['status'],'completed')
        # the old log is not this run's output - and it is still where the LP
        # viewer and the history look for it (v344 left it as .previous_attempt)
        self.assertEqual((self.p/'INIT.LP').read_text(),'old success')
        self.assertFalse((self.p/'INIT.LP.previous_attempt').exists())
        # a failed run that did write a log keeps that log: it carries the error
        self.assertNotEqual(self._step_with_script("from pathlib import Path; Path('INIT.LP').write_text('!!! ERROR !!! bad input'); raise SystemExit(7)")['status'],'completed')
        self.assertIn('ERROR',(self.p/'INIT.LP').read_text())

    def test_zero_exit_requires_fresh_output_and_success_path_works(self):
        (self.p/'INIT.LP').write_text('old success')
        self.assertNotEqual(self._step_with_script('pass')['status'],'completed')
        r=self._step_with_script("from pathlib import Path; Path('INIT.LP').write_text('fresh success')")
        self.assertEqual(r['status'],'completed',r)

    def test_f2mtz_cannot_accept_old_mtz(self):
        output=self.p/'old.mtz'; output.write_bytes(b'old mtz')
        with self.assertRaises(RuntimeError):
            m._run_checked([sys.executable,'-c','pass'],self.p,lambda t:None,expected_outputs=[output])

    def test_quiet_cancellation_and_timeout(self):
        flag=threading.Event(); timer=threading.Timer(.2,flag.set); timer.start()
        started=time.monotonic()
        try:
            rc,outcome=m._run_streaming([sys.executable,'-c','import time; time.sleep(30)'],self.p,lambda t:None,
                                       should_stop=flag.is_set,timeout=8)
        finally: timer.join()
        self.assertEqual(outcome,'stopped'); self.assertLess(time.monotonic()-started,7)
        rc,outcome=m._run_streaming([sys.executable,'-c','import time; time.sleep(30)'],self.p,lambda t:None,timeout=.3)
        self.assertEqual(outcome,'timeout')

    def test_registry_keeps_overlapping_processes(self):
        ready=[threading.Event(),threading.Event()]; results={}
        def worker(i):
            folder=self.p/str(i); folder.mkdir()
            results[i]=m._run_streaming([sys.executable,'-u','-c','import time; print("ready"); time.sleep(20)'],folder,
                                       lambda t:ready[i].set(),key=self.name,timeout=5)
        threads=[threading.Thread(target=worker,args=(i,)) for i in range(2)]
        for t in threads:t.start()
        try:
            self.assertTrue(all(e.wait(4) for e in ready))
            self.assertEqual(m._stop_procs(self.name),2)
        finally:
            m._stop_procs(self.name)
            for t in threads:t.join(10)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertEqual([results[i][1] for i in range(2)],['stopped','stopped'])

    @unittest.skipIf(os.name=='nt','POSIX process group test')
    def test_parent_exit_does_not_leave_term_resistant_child(self):
        code='import os,signal,time\npid=os.fork()\nif pid==0:\n signal.signal(signal.SIGTERM,signal.SIG_IGN)\n print(os.getpid(),flush=True)\n time.sleep(30)\nelse:\n time.sleep(30)\n'
        p=subprocess.Popen([sys.executable,'-c',code],start_new_session=True,stdout=subprocess.PIPE,text=True)
        try:
            child=int(p.stdout.readline()); m._kill_proc_tree(p)
            state=Path('/proc')/str(child)/'stat'
            deadline=time.monotonic()+2
            while state.exists() and state.read_text().split()[2]!='Z' and time.monotonic()<deadline:
                time.sleep(.02)
            if state.exists():self.assertEqual(state.read_text().split()[2],'Z')
            self.assertIsNotNone(p.poll())
        finally:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            p.wait(); p.stdout.close()

    def test_pipeline_cancellation_between_steps(self):
        events=[]; original=m._run_streaming
        def run(cmd,cwd,on_line,**kwargs):
            return original([sys.executable,'-c',"from pathlib import Path; Path('INIT.LP').write_text('ok')"],cwd,on_line,**kwargs)
        def send(event):
            events.append(event)
            if 'event: step_done' in event:m._stop_procs(self.name)
        with patch.object(m,'_find_xds_exe',return_value=Path(sys.executable)),patch.object(m,'_run_streaming',side_effect=run):
            m.stream_xds(self.name,['INIT','CORRECT'],send)
        self.assertEqual(m._parse_xdsinp_params((self.p/'XDS.INP').read_text())['JOB'],'INIT')
        self.assertFalse(m._jobs_running(self.name))

    def test_autopilot_pins_output_directory(self):
        old=self.p/'previous';old.mkdir();(old/'CORRECT.LP').write_text('old')
        m.ProjectManager.update(self.name,{'last_run_folder':str(old),'last_xscale_folder':str(old)})
        class EndProbe(Exception):pass
        def first_run(work_dir,*args,**kwargs):
            self.assertEqual(work_dir,self.p)
            for kind in ('xds','xscale','xdsconv'):self.assertEqual(m._project_out_dir(self.p,kind),self.p)
            self.assertEqual(m._pfile(self.p,'CORRECT.LP'),self.p/'CORRECT.LP')
            raise EndProbe()
        with patch.object(m,'_find_xds_exe',return_value=Path(sys.executable)),patch.object(m,'_find_xscale_exe',return_value=Path(sys.executable)),patch.object(m,'_ap_run_xds',side_effect=first_run):
            with self.assertRaises(EndProbe):m.stream_autopilot(self.name,lambda t:None)
        self.assertFalse(m._jobs_running(self.name))

    def test_edit_repeated_mixed_line_and_duplicate_keys(self):
        out=m.XDSINPEditor.apply_params('NX= 100 SPOT_RANGE= 1 10\nSPOT_RANGE= 20 30',{'SPOT_RANGE':[[40,50]]})
        self.assertIn('NX= 100',out); self.assertNotIn('1 10',out); self.assertNotIn('20 30',out)
        self.assertEqual(out.count('SPOT_RANGE='),1)
        out=m.XDSINPEditor.apply_params('SIGNAL_PIXEL= 3\nNX= 100 SIGNAL_PIXEL= 8',{'SIGNAL_PIXEL':15})
        self.assertEqual(m._parse_xdsinp_params(out)['SIGNAL_PIXEL'],'15')
        self.assertEqual(out.count('SIGNAL_PIXEL='),1)

    def test_autopilot_status_and_stop_are_project_scoped(self):
        other = self.name + '_other'
        m.ProjectManager.create(other)
        ready = [threading.Event(), threading.Event()]
        release = threading.Event()
        cancelled = {}
        @m._processing_job('autopilot')
        def run(project_name, i):
            ready[i].set()
            release.wait(5)
            cancelled[project_name] = m._job_stopped()
        threads = [threading.Thread(target=run,args=(name,i)) for i,name in enumerate((self.name,other))]
        for thread in threads:thread.start()
        try:
            self.assertTrue(all(event.wait(3) for event in ready))
            self.assertTrue(request('GET','/api/autopilot/status?project='+self.name)[1]['running'])
            self.assertEqual(request('POST','/api/autopilot/stop',{'project_name':self.name})[0],200)
        finally:
            release.set()
            for thread in threads:thread.join(6)
        self.assertEqual(cancelled,{self.name:True,other:False})
        self.assertFalse(request('GET','/api/autopilot/status?project='+self.name)[1]['running'])

    def test_autopilot_failure_retains_fresh_diagnostics(self):
        @m._processing_job('autopilot')
        def run(project_name):
            (self.p/'IDXREF.LP').write_text('old successful log')
            code="from pathlib import Path; Path('IDXREF.LP').write_text('!!! ERROR !!! INSUFFICIENT PERCENTAGE OF INDEXED REFLECTIONS'); raise SystemExit(7)"
            m._run_streaming([sys.executable,'-c',code],self.p,lambda t:None,expected_outputs=['IDXREF.LP'])
            text,error,message=m._ap_check_lp(self.p,'IDXREF')
            self.assertTrue(error);self.assertIn('INSUFFICIENT',text);self.assertIn('INSUFFICIENT',message)
        run(self.name)

    def test_xdsconv_does_not_reuse_old_f2mtz_input(self):
        (self.p/'XDSCONV.INP').write_text('OUTPUT_FILE= temp.hkl CCP4_I+F\n')
        (self.p/'F2MTZ.INP').write_text('old conversion instructions')
        events=[]
        def fake_run(*args,**kwargs):
            (self.p/'XDSCONV.LP').write_text('successful new run')
            return 0,'ok'
        with patch.object(m,'_find_xdsconv_exe',return_value=Path(sys.executable)),patch.object(m,'CCP4_BIN',str(self.p)),patch.object(m,'_run_streaming',side_effect=fake_run),patch.object(m,'_run_checked') as checked:
            m.stream_xdsconv(self.name,events.append)
        checked.assert_not_called()
        self.assertTrue(any('No fresh F2MTZ.INP' in event for event in events))

    def test_xscale_keeps_per_input_identity_when_reordered(self):
        src='OUTPUT_FILE= result.hkl\nINPUT_FILE= a.hkl\n CRYSTAL_NAME= A\n INCLUDE_RESOLUTION_RANGE= 50 2\nINPUT_FILE= b.hkl\n CRYSTAL_NAME= B\n INCLUDE_RESOLUTION_RANGE= 50 3\n'
        out=m._xscale_apply_params(src,{'INPUT_FILE':['b.hkl','a.hkl','new.hkl']})
        sections=out.split('INPUT_FILE=')
        self.assertIn('CRYSTAL_NAME= B',sections[1]);self.assertIn('50 3',sections[1])
        self.assertIn('CRYSTAL_NAME= A',sections[2]);self.assertNotIn('CRYSTAL_NAME',sections[3])

    def test_saved_ccp4_setting_survives_module_startup(self):
        settings=self.p/'settings.json';settings.write_text('{"ccp4_bin":"/custom/ccp4/bin"}')
        env=dict(os.environ,XDS_GUI_SETTINGS=str(settings),XDS_GUI_PROJECTS=str(self.p/'isolated'))
        code='import runpy; m=runpy.run_path('+repr(str(build))+'); print("CCP4_SAVED="+m["CCP4_BIN"])'
        result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('CCP4_SAVED=/custom/ccp4/bin',result.stdout)

    def test_build_verify_rejects_body_and_value_changes(self):
        spec=importlib.util.spec_from_file_location('builder',HERE.parent/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
        first=self.p/'a.py';second=self.p/'b.py'
        first.write_text('VERSION="1"\ndef f():\n return 1\n')
        second.write_text('VERSION="2"\ndef f():\n return 2\n')
        with contextlib.redirect_stdout(io.StringIO()):self.assertFalse(b.verify(first,second))

    @unittest.skipIf(os.name=='nt','Bash config writer test')
    def test_actual_installer_config_writers_quote_paths(self):
        root=HERE.parents[1]
        for rel in ('linux/install-linux.sh','windows/wsl-install.sh'):
            source=(root/rel).read_text()
            block=source[source.index('{\n    echo "# CrystalPilot'):]
            block=block[:block.index('\n} >')+2]
            value=str(self.p/"space and ' apostrophe & literal")
            script='set -e\nPORT=8100\nPROJECTS='+repr(value)+'\n'
            # Pass values as positional data rather than embedding them in shell code.
            script='set -e\nPORT=8100\nPROJECTS="$1"\nPROJECTS_DIR="$1"\nXDS_DIR="$1"\nCCP4_SETUP="$1"\nCCP4_WIN="$1"\nCCP4_MODE=linux\nVENV_PY="$1"\n'+block+' > "$2"\nunset PROJECTS_DIR\n. "$2"\nprintf "%s" "$PROJECTS_DIR"'
            result=subprocess.run(['bash','-c',script,'probe',value,str(self.p/'config.env')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,value)
            if rel.startswith('windows/'):
                readers='\n'.join(line for line in source.splitlines() if 'prev_setup=$' in line or 'prev_win=$' in line or 'prev_pd=$' in line)
                script='set -e\nCPDIR="$1"\n'+readers+'\nprintf "%s\\n" "$prev_setup" "$prev_win" "$PROJECTS_DIR"'
                result=subprocess.run(['bash','-c',script,'probe',str(self.p)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.splitlines(),[value]*3)

    def test_gemmi_flags_equivalence_reexport_and_rng(self):
        try:import gemmi;import numpy as np
        except ImportError:self.skipTest('Gemmi/NumPy unavailable')
        hkl=self.p/'data.HKL'
        rows=[f'{sign*h} {sign*k} {sign} {100+j} 3 1 1 {j+1} 1 1 1 0' for h in range(1,5) for k in range(1,5) for sign in (1,-1) for j in range(3)]
        header="!FORMAT=XDS_ASCII    MERGE=FALSE    FRIEDEL'S_LAW=FALSE\n!SPACE_GROUP_NUMBER=1\n!UNIT_CELL_CONSTANTS= 40 40 40 90 90 90\n!X-RAY_WAVELENGTH=1\n!NUMBER_OF_ITEMS_IN_EACH_DATA_RECORD=12\n"
        header+=''.join('!ITEM_'+k+'='+str(i)+'\n' for i,k in enumerate(['H','K','L','IOBS','SIGMA(IOBS)','XD','YD','ZD','RLP','PEAK','CORR','MAXC'],1))
        hkl.write_text(header+'!END_OF_HEADER\n'+'\n'.join(rows)+'\n!END_OF_DATA\n')
        out=self.p/'out.mtz'; before=np.random.get_state()
        self.assertTrue(m.convert_xds_to_mtz(hkl,out)['success'])
        after=np.random.get_state();self.assertTrue(np.array_equal(before[1],after[1]));self.assertEqual(before[2:],after[2:])
        mtz=gemmi.read_mtz_file(str(out));data=np.array(mtz,copy=True);asu=gemmi.ReciprocalAsu(mtz.spacegroup);ops=mtz.spacegroup.operations()
        flags={}
        for row in data:flags.setdefault(tuple(asu.to_asu([int(v) for v in row[:3]],ops)[0]),set()).add(int(row[-1]))
        self.assertTrue(all(len(v)==1 for v in flags.values()))
        m.convert_xds_to_mtz(hkl,out)
        self.assertTrue(np.array_equal(data[:,-1],np.array(gemmi.read_mtz_file(str(out)),copy=True)[:,-1]))
        # An externally established master must win over deterministic defaults.
        data[:,-1]=7;mtz.set_data(data);mtz.write_to_file(str(out))
        m.convert_xds_to_mtz(hkl,out)
        self.assertTrue(np.all(np.array(gemmi.read_mtz_file(str(out)),copy=True)[:,-1]==7))
        data[0,-1]=8;mtz.set_data(data);mtz.write_to_file(str(out));before_bytes=out.read_bytes()
        with self.assertRaisesRegex(ValueError,'conflicting flags'):m.convert_xds_to_mtz(hkl,out)
        self.assertEqual(out.read_bytes(),before_bytes)
        # P4 rotates (h,k,l) to (-k,h,l), beyond repeats and Friedel mates.
        hkl.write_text(hkl.read_text().replace('SPACE_GROUP_NUMBER=1\n','SPACE_GROUP_NUMBER=75\n')
                       .replace('!END_OF_DATA','-2 1 1 100 3 1 1 1 1 1 1 0\n!END_OF_DATA'))
        m.convert_xds_to_mtz(hkl,self.p/'symmetry.mtz')
        symmetric=gemmi.read_mtz_file(str(self.p/'symmetry.mtz'))
        array=np.array(symmetric,copy=True);asu=gemmi.ReciprocalAsu(symmetric.spacegroup)
        groups={}
        for row in array:groups.setdefault(tuple(asu.to_asu([int(v) for v in row[:3]],symmetric.spacegroup.operations())[0]),set()).add(row[-1])
        self.assertTrue(all(len(v)==1 for v in groups.values()))


if __name__=='__main__':
    try:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReviewRegressions)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        m._stop_procs();server.shutdown();server.server_close();server_thread.join()
    sys.exit(0 if result.wasSuccessful() else 1)
