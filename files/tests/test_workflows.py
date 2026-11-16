"""HTTP-to-process workflow tests using scratch projects and deterministic tools.

The actual handler, job owner, runner, editor, metadata and LP parsers execute.
Only executable discovery/launch is adapted to run the fixture Python program.
These tests verify orchestration, not crystallographic numerical correctness.
"""
import contextlib
import http.client
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest
import urllib.parse
from unittest.mock import patch

import test_units as battery

HERE = Path(__file__).resolve().parent
build = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else battery.newest_build()
m, scratch = battery.load_module(build)


def events_from(text):
    events = []
    for block in text.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line)
        if 'event' in fields and 'data' in fields:
            events.append((fields['event'], json.loads(fields['data'])))
    return events


class Workflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = contextlib.ExitStack()
        cls.bin = scratch / 'tools'; cls.bin.mkdir()
        cls.paths = {}
        for name in ('xds','xscale','xdsconv','f2mtz','cad'):
            path = cls.bin / name; path.touch(); cls.paths[str(path)] = name
        original = m.subprocess.Popen
        def popen(cmd, **kwargs):
            # on Linux the CPU/RAM limits put taskset / the cgroup shell in
            # front of the program: the stand-in replaces it where it is
            cmd = list(cmd)
            at = next((i for i, c in enumerate(cmd) if str(c) in cls.paths), None)
            if at is not None:
                cmd[at:at + 1] = [sys.executable, str(HERE/'fixtures/workflow_tool.py'), cls.paths[str(cmd[at])]]
            return original(cmd, **kwargs)
        cls.stack.enter_context(patch.object(m.subprocess, 'Popen', side_effect=popen))
        for name in ('xds','xscale','xdsconv'):
            cls.stack.enter_context(patch.object(m, '_find_'+name+'_exe', return_value=cls.bin/name))
        cls.stack.enter_context(patch.object(m, 'CCP4_BIN', str(cls.bin)))
        cls.server = m.ThreadingHTTPServer(('127.0.0.1', 0), m.XDSGUIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        m._stop_procs()
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(5)
        cls.stack.close()

    def setUp(self):
        # a question to the user answers at once here; the test of the wait sets its own time
        waiting = patch.object(m, 'AGENT_APPROVAL_WAIT', 0)
        waiting.start()
        self.addCleanup(waiting.stop)
        self.name = self._testMethodName + ' project'
        self.request('POST','/api/projects', {'name':self.name})
        self.p = m._pdir(self.name)
        self.url = '/api/projects/' + urllib.parse.quote(self.name, safe='')
        self.request('POST', self.url+'/xdsinp', {'content':'JOB= XYCORR\nDATA_RANGE= 1 60\nOSCILLATION_RANGE= 0.1\n'})

    def tearDown(self):
        self.assertFalse(m._jobs_running(self.name))
        with m._proc_lock:
            self.assertFalse(m._PROCS)
            self.assertFalse(m._BUSY_DIRS)

    def request(self, method, path, data=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1',self.server.server_address[1],timeout=15)
        try:
            conn.request(method,path,json.dumps(data) if data is not None else None,
                         {'Content-Type':'application/json','X-CrystalPilot-Token':m.API_TOKEN,**(headers or {})})
            response=conn.getresponse(); text=response.read().decode()
            value=events_from(text) if response.getheader('Content-Type')=='text/event-stream' else json.loads(text)
            return response.status,value
        finally:
            conn.close()

    def stream(self, route='/api/stream', **params):
        params={'project':self.name,**params}
        status,events=self.request('GET',route+'?'+urllib.parse.urlencode(params))
        self.assertEqual(status,200,events)
        return events

    def control(self, **modes):
        (self.p/'control.json').write_text(json.dumps(modes))

    def executed(self):
        path=self.p/'executed.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_terminal(self, events, status, name='done'):
        terminals=[d for e,d in events if e==name]
        self.assertEqual(len(terminals),1,events[-4:])
        self.assertEqual(terminals[0]['status'],status,events[-4:])

    def test_complete_processing_and_conversion_workflow(self):
        events=self.stream()
        self.assertEqual([d['step'] for e,d in events if e=='step_done'],m.XDS_PIPELINE)
        self.assert_terminal(events,'completed')
        self.assertEqual(self.request('GET',self.url)[1]['completed_steps'],m.XDS_PIPELINE)
        self.assertIn('unit_cell',self.request('GET',self.url+'/metrics/CORRECT')[1]['metrics'])
        self.request('POST',self.url+'/xscaleinp',{'content':"OUTPUT_FILE= scaled.ahkl\nFRIEDEL'S_LAW= TRUE\nINPUT_FILE= XDS_ASCII.HKL\n"})
        self.assert_terminal(self.stream('/api/xscale/stream'),'completed')
        self.request('POST',self.url+'/xdsconvinp',{'content':'INPUT_FILE= scaled.ahkl\nOUTPUT_FILE= temp.hkl CCP4_I+F\n'})
        events=self.stream('/api/xdsconv/stream')
        self.assertEqual([d['step'] for e,d in events if e=='step_done'],['XDSCONV','f2mtz','cad'])
        self.assert_terminal(events,'completed')
        self.assertTrue((self.p/'temp.mtz').is_file())

    def test_failed_rerun_invalidates_downstream_completion_and_recovers(self):
        self.assert_terminal(self.stream(),'completed')
        self.control(INIT='exit')
        events=self.stream(steps='INIT,COLSPOT,IDXREF')
        self.assert_terminal(events,'error')
        self.assertEqual(self.request('GET',self.url)[1]['completed_steps'],['XYCORR'])
        self.assertEqual(self.executed()[-1],'INIT')
        self.control()
        self.assert_terminal(self.stream(),'completed')
        self.assertEqual(self.request('GET',self.url)[1]['completed_steps'],m.XDS_PIPELINE)

    def test_synchronous_pipeline_stops_at_first_failure(self):
        self.control(INIT='lp_error')
        status,data=self.request('POST','/api/run',{'project_name':self.name})
        self.assertEqual(status,200)
        self.assertEqual([r['step'] for r in data['results']],['XYCORR','INIT'])
        self.assertEqual(data['results'][-1]['status'],'failed')
        self.assertEqual(self.executed(),['XYCORR','INIT'])

    def test_no_output_is_a_terminal_error(self):
        self.control(INIT='missing')
        events=self.stream(steps='INIT,COLSPOT')
        self.assert_terminal(events,'error')
        self.assertTrue(any('fresh output' in d.get('message','') for e,d in events if e=='error_msg'))
        self.assertEqual(self.executed(),['INIT'])

    def test_conversion_failure_does_not_run_cad_or_accept_stale_mtz(self):
        self.request('POST',self.url+'/xdsconvinp',{'content':'OUTPUT_FILE= temp.hkl CCP4_I+F\n'})
        (self.p/'temp_f2mtz.mtz').write_bytes(b'old')
        (self.p/'temp.mtz').write_bytes(b'old final')
        self.control(F2MTZ='exit')
        events=self.stream('/api/xdsconv/stream')
        self.assert_terminal(events,'error')
        self.assertEqual(self.executed(),['XDSCONV','F2MTZ'])
        self.assertEqual((self.p/'temp.mtz').read_bytes(),b'old final')

    def test_stop_blocks_competing_write_and_allows_retry(self):
        self.control(INIT='quiet')
        result=[]
        thread=threading.Thread(target=lambda:result.extend(self.stream(steps='INIT,COLSPOT')))
        thread.start()
        try:
            deadline=time.monotonic()+5
            while not self.executed() and time.monotonic()<deadline:time.sleep(.02)
            self.assertEqual(self.executed(),['INIT'])
            self.assertEqual(self.request('POST',self.url+'/xdsinp',{'content':'bad'})[0],409)
            self.assertEqual(self.request('POST','/api/stop',{'project_name':self.name})[0],200)
        finally:
            m._stop_procs(self.name);thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assert_terminal(result,'stopped')
        self.assertEqual(self.executed(),['INIT'])
        self.control()
        self.assert_terminal(self.stream(step='INIT'),'completed')

    def test_run_outlives_its_page_and_can_be_followed_again(self):
        # the page that started the run goes away while the run is going
        self.control(INIT='wait')
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_address[1],timeout=15)
        conn.request('GET','/api/stream?'+urllib.parse.urlencode({'project':self.name,'steps':'INIT,COLSPOT'}),
                     headers={'X-CrystalPilot-Token':m.API_TOKEN})
        response=conn.getresponse(); seen=b''
        while b'starting INIT' not in seen:
            seen+=response.fp.readline()
        self.assertIn(b'event: job\ndata: ',seen)
        self.assertIn(b'\nid: 0\n',seen)
        conn.close()
        try:
            status,data=self.request('GET','/api/jobs?'+urllib.parse.urlencode({'project':self.name}))
            self.assertEqual(status,200)
            job=data['jobs'][0]
            self.assertEqual((job['kind'],job['running'],job['followable'],job['title']),('xds',True,True,'INIT to COLSPOT'))
            (self.p/'release').touch()
            # a new page follows it: everything from the start, then the rest until the end
            status,events=self.request('GET','/api/jobs/stream?id='+job['id'])
            self.assertEqual(status,200)
            self.assertEqual([d['step'] for e,d in events if e=='step_start'],['INIT','COLSPOT'])
            self.assertEqual([d['step'] for e,d in events if e=='step_done'],['INIT','COLSPOT'])
            self.assert_terminal(events,'completed')
            # after a lost connection: only what came after the last event received
            status,again=self.request('GET','/api/jobs/stream?id='+job['id'],headers={'Last-Event-ID':'0'})
            self.assertEqual(again,events[1:])
            status,data=self.request('GET','/api/jobs?'+urllib.parse.urlencode({'project':self.name}))
            self.assertEqual((data['jobs'][0]['running'],data['jobs'][0]['status']),(False,'completed'))
            self.assertEqual(self.request('GET','/api/jobs/stream?id=nosuchrun')[0],404)
        finally:
            (self.p/'release').touch()
            deadline=time.monotonic()+10
            while m._jobs_running(self.name) and time.monotonic()<deadline:time.sleep(.05)

    def test_timeout_is_terminal_and_releases_job(self):
        self.control(INIT='quiet')
        with patch.object(m,'XDS_STEP_TIMEOUT',.2):events=self.stream(steps='INIT,COLSPOT')
        self.assert_terminal(events,'timeout')
        self.assertTrue(any('0.2 s' in d.get('message','') for e,d in events if e=='error_msg'))
        self.assertEqual(self.executed(),['INIT'])

    def test_invalid_requests_fail_before_starting_work(self):
        for value in ([], 'text', 42):
            self.assertEqual(self.request('POST','/api/run',value)[0],400)
        for steps in ('INIT,TYPO','INIT,','TYPO'):
            self.assertEqual(self.request('GET','/api/stream?'+urllib.parse.urlencode({'project':self.name,'steps':steps}))[0],400)
        for route in ('/api/stream','/api/autoindex/stream','/api/autopilot/stream','/api/xscale/stream','/api/xdsconv/stream'):
            self.assertEqual(self.request('GET',route)[0],400)
            self.assertEqual(self.request('GET',route+'?project=absent')[0],404)
            # A browser's EventSource shows neither status nor body, so it is told
            # in the stream instead; the page's log printed only "connection
            # closed" for a while (v344).
            status,events=self.request('GET',route+'?project=absent',headers={'Accept':'text/event-stream'})
            self.assertEqual(status,200,events)
            self.assertTrue(any(e.endswith('done') and d.get('status')=='error' and 'not found' in d.get('message','').lower()
                                for e,d in events),events)
        self.assertEqual(self.executed(),[])

    def test_unexpected_stream_failure_sends_final_error_and_can_retry(self):
        for route,fn,terminal in (('/api/stream','stream_xds','done'),('/api/autoindex/stream','stream_autoindex','ai_done'),('/api/autopilot/stream','stream_autopilot','ap_done')):
            # Fail inside each real job, after its reservation and HTTP headers.
            with patch.object(m,'_record_run_folder',side_effect=OSError('disk write failed')) if fn!='stream_autoindex' else patch.object(m,'_read_text_lenient',side_effect=OSError('input read failed')):
                events=self.stream(route)
            self.assert_terminal(events,'error',terminal)
        self.assert_terminal(self.stream(step='INIT'),'completed')

    def test_metadata_write_failure_is_visible(self):
        original=m.ProjectManager.update
        def update(name,data):
            if data.get('completed_steps')==['INIT']:raise OSError('metadata disk full')
            return original(name,data)
        with patch.object(m.ProjectManager,'update',side_effect=update):events=self.stream(step='INIT')
        self.assert_terminal(events,'error')
        self.assertTrue(any('metadata disk full' in d.get('message','') for e,d in events))
        self.assertEqual(self.request('GET',self.url)[1]['completed_steps'],[])

    def test_invalid_run_folder_is_terminal(self):
        path=self.p/'not_a_directory';path.write_text('file')
        self.assert_terminal(self.stream(step='INIT',run_folder=str(path)),'error')

    def test_autopilot_full_workflow(self):
        events=self.stream('/api/autopilot/stream',optimize='0',dcc_half='0')
        self.assert_terminal(events,'completed','ap_done')
        final=[d['summary'] for e,d in events if e=='ap_done'][0]
        self.assertTrue(final['mtz_file'])
        self.assertEqual(self.request('GET',self.url)[1]['completed_steps'],[s for s in m.XDS_PIPELINE if s!='XPLAN'])
        self.assertEqual(json.loads((self.p/'AUTOPILOT_RESULTS.json').read_text())['status'],'completed')

    def test_autopilot_takes_the_screw_axes_from_the_absences(self):
        # XDS chooses P422; h00 shows a 2(1) and 00l a 4(1): CORRECT runs again in P4(1)2(1)2
        self.control(axial='P41212')
        events=self.stream('/api/autopilot/stream',optimize='0',dcc_half='0')
        self.assert_terminal(events,'completed','ap_done')
        log='\n'.join(d.get('text','') for e,d in events if e=='ap_log')
        self.assertIn('0,0,l only every 4th present',log)
        self.assertIn('h,0,0 only every 2nd present',log)
        self.assertIn('P4₁2₁2 (#92), not P422 (#89)',log)
        self.assertIn('enantiomorph P4₃2₁2',log)
        final=[d['summary'] for e,d in events if e=='ap_done'][0]
        self.assertEqual(final['space_group'],92)
        self.assertIn('P4₁2₁2',final['sg_note'])

    def test_external_folder_workflow_records_outputs_and_serves_metrics(self):
        folder=self.p/'external run'
        self.assert_terminal(self.stream(steps='INTEGRATE,CORRECT',run_folder=str(folder)),'completed')
        metadata=self.request('GET',self.url)[1]
        self.assertEqual(Path(metadata['last_run_folder']),folder)
        self.assertFalse((self.p/'CORRECT.LP').exists())
        lp=self.request('GET',self.url+'/lp/CORRECT')[1]
        self.assertEqual(Path(lp['source']),folder/'CORRECT.LP')
        self.assertIn('unit_cell',self.request('GET',self.url+'/metrics/CORRECT')[1]['metrics'])

    def test_run_folder_persistence_failure_prevents_processing(self):
        original=m.ProjectManager.update
        def update(name,data):
            if 'last_run_folder' in data:raise OSError('cannot persist output location')
            return original(name,data)
        with patch.object(m.ProjectManager,'update',side_effect=update):events=self.stream(step='INIT')
        self.assert_terminal(events,'error')
        self.assertEqual(self.executed(),[])

    def test_autopilot_stop_does_not_keep_previous_success_as_current(self):
        previous=self.p/'AUTOPILOT_RESULTS.json'
        previous.write_text('{"status":"completed","mtz_file":"old.mtz"}')
        m.ProjectManager.update(self.name,{'completed_steps':list(m.XDS_PIPELINE)})
        self.control(XYCORR='quiet')
        result=[]
        thread=threading.Thread(target=lambda:result.extend(self.stream('/api/autopilot/stream',optimize='0',dcc_half='0')))
        thread.start()
        try:
            deadline=time.monotonic()+5
            while not self.executed() and time.monotonic()<deadline:time.sleep(.02)
            self.assertEqual(self.executed(),['XYCORR'])
            self.request('POST','/api/autopilot/stop',{'project_name':self.name})
        finally:
            m._stop_procs(self.name);thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assert_terminal(result,'stopped','ap_done')
        self.assertFalse(previous.exists())
        self.assertTrue(previous.with_name(previous.name+'.previous_attempt').exists())
        self.assertEqual(self.request('GET',self.url)[1]['completed_steps'],[])

    def test_failed_rerun_keeps_the_last_good_log_readable(self):
        # v344 moved CORRECT.LP aside before every attempt and never brought it
        # back: after AutoPilot's failed re-integration the page said
        # "CORRECT.LP not found" and the history had nothing to compare.
        self.assert_terminal(self.stream(),'completed')
        before=self.request('GET',self.url+'/lp/CORRECT')[1]['content']
        self.control(CORRECT='exit')
        self.assert_terminal(self.stream(step='CORRECT'),'error')
        status,d=self.request('GET',self.url+'/lp/CORRECT')
        self.assertEqual(status,200,d);self.assertEqual(d['content'],before)
        self.assertEqual(self.request('GET',self.url+'/metrics/CORRECT')[0],200)
        self.assertGreaterEqual(len(self.request('GET',self.url+'/history-correct')[1]['runs']),1)
        self.assertFalse((self.p/'CORRECT.LP.previous_attempt').exists())
        # the same through AutoPilot: PROCESS succeeds, the OPTIMIZE re-integration fails
        self.control()
        events=self.stream('/api/autopilot/stream',optimize='0',dcc_half='0')
        self.assert_terminal(events,'completed','ap_done')
        good=self.request('GET',self.url+'/lp/CORRECT')[1]['content']
        self.control(INTEGRATE='exit')
        events=self.stream('/api/autopilot/stream',optimize='0',dcc_half='0')
        self.assertTrue(any(e=='ap_done' for e,d in events))
        status,d=self.request('GET',self.url+'/lp/CORRECT')
        self.assertEqual(status,200,d);self.assertEqual(d['content'],good)

    # ── batch processing ────────────────────────────────────────────────────
    def _batch_with(self, labels, strategy=None):
        """A batch of fresh projects that already have the fixture XDS.INP."""
        datasets = [{"kind": "series", "template": str(self.p / (label + "_????.cbf")), "label": label, "folder": str(self.p)}
                    for label in labels]
        state = m.batch_create("test batch", datasets, strategy or {"optimize": "never", "dcc_half": "off"})
        for item in state["items"]:
            (m._pdir(item["project"]) / "XDS.INP").write_text(
                "JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nDATA_RANGE= 1 60\nOSCILLATION_RANGE= 0.1\n", encoding="utf-8")
        self.addCleanup(self._batch_cleanup, state)
        return state

    def _batch_cleanup(self, state):
        m.batch_stop(state["id"])
        self._batch_wait(state["id"], 60)

    def _batch_wait(self, batch_id, seconds=90):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if m._BATCH_ACTIVE["id"] != batch_id:
                return m.batch_state(batch_id)
            time.sleep(0.2)
        raise AssertionError("batch did not finish in %d s" % seconds)

    def test_batch_processes_every_dataset_and_reads_their_metrics(self):
        state = self._batch_with(["xtal_a", "xtal_b"])
        m.batch_start(state["id"])
        done = self._batch_wait(state["id"])
        self.assertEqual([i["status"] for i in done["items"]], ["done", "done"], done["items"])
        self.assertEqual(done["status"], "done")
        for item in done["items"]:
            self.assertEqual(str(item["metrics"].get("space_group")), "20", item["metrics"])
            self.assertTrue((m._batch_dir(state["id"]) / "logs" / (item["project"] + ".log")).is_file())
        # the queue is resumable state on disk, not memory
        self.assertEqual(m.batch_load(state["id"])["items"][1]["status"], "done")

    def test_batch_carries_on_after_a_dataset_fails(self):
        state = self._batch_with(["xtal_bad", "xtal_good"])
        (m._pdir(state["items"][0]["project"]) / "control.json").write_text(json.dumps({"XYCORR": "exit"}))
        m.batch_start(state["id"])
        done = self._batch_wait(state["id"])
        self.assertEqual([i["status"] for i in done["items"]], ["failed", "done"], done["items"])
        self.assertTrue(done["items"][0]["error"], done["items"][0])

    def test_batch_stop_leaves_the_rest_queued_and_start_resumes(self):
        state = self._batch_with(["xtal_slow", "xtal_next"])
        (m._pdir(state["items"][0]["project"]) / "control.json").write_text(json.dumps({"XYCORR": "quiet"}))
        m.batch_start(state["id"])
        deadline = time.time() + 20
        while time.time() < deadline and m.batch_state(state["id"])["items"][0]["status"] != "running":
            time.sleep(0.1)
        time.sleep(0.5)
        m.batch_stop(state["id"])
        stopped = self._batch_wait(state["id"])
        self.assertEqual(stopped["status"], "stopped")
        # the interrupted data set goes back in the queue, so Resume processes it again
        self.assertEqual([i["status"] for i in stopped["items"]], ["queued", "queued"], stopped["items"])
        self.assertIn("Resume", stopped["items"][0]["error"])
        # a second start carries on with what is left
        first = m._pdir(state["items"][0]["project"])
        (first / "control.json").write_text("{}")
        m.batch_start(state["id"])
        resumed = self._batch_wait(state["id"])
        self.assertEqual(resumed["items"][1]["status"], "done", resumed["items"])
        # the interrupted data set was processed again, from a fresh XDS.INP (the old one put aside)
        self.assertNotEqual(resumed["items"][0]["status"], "queued", resumed["items"][0])
        self.assertTrue((first / "XDS.INP.interrupted_run").is_file())

    def _imported_batch(self, label, strategy):
        """A one-data-set run whose XDS.INP is imported from a 'beamline' file with a space group."""
        beamline = self.p / "beamline" / "fast_dp"
        beamline.mkdir(parents=True)
        source = beamline / "XDS.INP"
        source.write_text("JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\n"
                          "NAME_TEMPLATE_OF_DATA_FRAMES= /beamline/raw/%s_????.cbf\nDATA_RANGE= 1 60\nOSCILLATION_RANGE= 0.1\n"
                          "SPACE_GROUP_NUMBER= 19\nUNIT_CELL_CONSTANTS= 78 78 37 90 90 90\nCLUSTER_NODES= n1 n2\n" % label, encoding="utf-8")
        datasets = [{"kind": "series", "template": str(self.p / (label + "_????.cbf")), "label": label,
                     "folder": str(self.p), "first": 1, "last": 60, "xdsinp": str(source)}]
        state = m.batch_create("imported", datasets, strategy)
        self.addCleanup(self._batch_cleanup, state)
        return state

    def test_imported_xdsinp_first_run_is_without_its_space_group(self):
        state = self._imported_batch("xtal_imp", {"optimize": "never", "dcc_half": "off", "autoindex_tier": "off"})
        m.batch_start(state["id"])
        done = self._batch_wait(state["id"])
        item = done["items"][0]
        self.assertEqual(item["status"], "done", item)
        self.assertTrue(item["attempt"].startswith("1 of 2"), item)
        text = (m._pdir(item["project"]) / "XDS.INP").read_text(encoding="utf-8")
        self.assertIn("Imported by CrystalPilot", text)
        self.assertNotIn("SPACE_GROUP_NUMBER", m.xdsinp_values(text))
        self.assertNotIn("CLUSTER_NODES", m.xdsinp_values(text))
        # the image folder (this project's) has a blank: on Linux and macOS the template goes
        # through a link without blanks (batch_xds_safe_template); Windows makes no link
        tmpl = m.xdsinp_values(text)["NAME_TEMPLATE_OF_DATA_FRAMES"]
        self.assertEqual(os.path.basename(tmpl), "xtal_imp_????.cbf")
        self.assertEqual(os.path.realpath(os.path.join(str(m._pdir(item["project"])), os.path.dirname(tmpl))),
                         os.path.realpath(str(self.p)))

    def test_imported_xdsinp_space_group_route_runs_each_attempt_until_one_succeeds(self):
        state = self._imported_batch("xtal_route", {"optimize": "never", "dcc_half": "off", "autoindex_tier": "off"})
        (m._pdir(state["items"][0]["project"]) / "control.json").write_text(json.dumps({"XYCORR": "exit"}))
        m.batch_start(state["id"])
        done = self._batch_wait(state["id"])
        item = done["items"][0]
        self.assertEqual(item["status"], "failed", item)
        self.assertTrue(item["attempt"].startswith("2 of 2: with the imported space group 19"), item)
        log = (m._batch_dir(state["id"]) / "logs" / (item["project"] + ".log")).read_text(encoding="utf-8")
        self.assertIn("Attempt 1 of 2: without the imported space group 19", log)
        self.assertIn("Attempt 2 of 2: with the imported space group 19", log)
        text = (m._pdir(item["project"]) / "XDS.INP").read_text(encoding="utf-8")
        self.assertEqual(m.xdsinp_values(text).get("SPACE_GROUP_NUMBER"), "19")

    def _project_busy_at_terminal(self, route, terminal, **params):
        """Read a run's events as the browser does; was the project folder still
        reserved when the terminal event arrived?  Releasing is made slow, so an
        event sent before the release is always caught."""
        original = m._release_dir
        def slow_release(path):
            time.sleep(.3); original(path)
        key = m._directory_key(self.p)
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=60)
        busy = None
        with patch.object(m, '_release_dir', side_effect=slow_release):
            conn.request('GET', route + '?' + urllib.parse.urlencode({'project': self.name, **params}),
                         headers={'X-CrystalPilot-Token': m.API_TOKEN})
            response = conn.getresponse()
            while True:
                line = response.readline()
                if not line:
                    break
                if line.strip() == ('event: ' + terminal).encode():
                    busy = key in m._BUSY_DIRS
                    break
            response.read(); conn.close()
        self.assertIsNotNone(busy, 'no ' + terminal + ' event')
        return busy

    def test_a_run_says_done_only_after_the_project_folder_is_free(self):
        # the browser starts the next step the moment "done" arrives
        self.assertFalse(self._project_busy_at_terminal('/api/stream', 'done', step='XYCORR'),
                         '"done" came before the project folder was released')

    def test_open_project_is_processed_in_place_with_its_own_xdsinp(self):
        own = "JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nDATA_RANGE= 1 60\nOSCILLATION_RANGE= 0.1\n" \
              "NAME_TEMPLATE_OF_DATA_FRAMES= /hand/made/x_????.cbf\nORGX= 1234 ORGY= 1300\n"
        (self.p / "XDS.INP").write_text(own, encoding="utf-8")
        before = sorted(p.name for p in m.PROJECTS_DIR.iterdir())
        state = m.batch_create("in place", [{"kind": "project", "template": "/hand/made/x_????.cbf", "label": self.name,
                                             "existing_project": self.name}], {"optimize": "never", "dcc_half": "off"})
        self.addCleanup(self._batch_cleanup, state)
        self.assertEqual(state["items"][0]["project"], self.name)
        self.assertEqual(sorted(p.name for p in m.PROJECTS_DIR.iterdir() if p.name != "batches"),
                         sorted(n for n in before if n != "batches"))            # no new project
        m.batch_start(state["id"])
        done = self._batch_wait(state["id"])
        self.assertEqual(done["items"][0]["status"], "done", done["items"][0])
        values = m.xdsinp_values((self.p / "XDS.INP").read_text(encoding="utf-8"))
        self.assertEqual(values.get("ORGX"), "1234")                            # the hand-made geometry, not a regenerated file
        log = (m._batch_dir(state["id"]) / "logs" / (self.name + ".log")).read_text(encoding="utf-8")
        self.assertIn("the project's own", log)
        with self.assertRaises(ValueError):
            m.batch_create("twice", [{"template": "x", "existing_project": self.name}] * 2, {})

    # ── group B: requests from other web sites, --restrict-browse ─────────────
    def test_loopback_server_refuses_requests_for_other_host_names(self):
        with patch.object(m, "HOST", "127.0.0.1"):
            status, body = self.request("GET", "/api/projects", headers={"Host": "attacker.example:%d" % self.server.server_address[1]})
            self.assertEqual(status, 403, body)
            for good in ("localhost:%d", "127.0.0.1:%d", "[::1]:%d", "app.localhost:%d"):
                status, _ = self.request("GET", "/api/projects", headers={"Host": good % self.server.server_address[1]})
                self.assertEqual(status, 200, good)
        with patch.object(m, "HOST", "0.0.0.0"):
            self.assertEqual(self.request("GET", "/api/projects", headers={"Host": "workstation.lab:1"})[0], 200)

    def test_restrict_browse_keeps_every_path_route_inside_the_projects_folder(self):
        outside = scratch / "outside_projects"
        outside.mkdir(exist_ok=True)
        (outside / "XDS.INP").write_text("JOB= XYCORR\n")
        sibling = Path(str(m.PROJECTS_DIR.resolve()) + "2")                     # a name that only starts like it
        sibling.mkdir(exist_ok=True)
        with patch.object(m, "RESTRICT_BROWSE", True):
            q = urllib.parse.quote
            for route in ("/api/fv-xdsinp?path=" + q(str(outside / "XDS.INP")), "/api/fv-spots?dir=" + q(str(outside)),
                          "/api/frames/list?template=" + q(str(outside / "x_????.cbf"))):
                self.assertEqual(self.request("GET", route)[0], 403, route)
            self.assertEqual(self.request("GET", "/api/fv-xdsinp?path=" + q(str(self.p / "XDS.INP")))[0], 200)
            status, listing = self.request("GET", "/api/ls?path=" + q(str(sibling)))
            self.assertEqual(Path(listing["cwd"]), m.PROJECTS_DIR.resolve(), listing)
            self.assertEqual(self.request("POST", "/api/open-folder", {"path": str(outside), "dry": True})[0], 403)
            self.assertEqual(self.request("POST", "/api/run-folder", {"project_name": self.name, "folder": str(outside / "run")})[0], 403)
            self.assertFalse((outside / "run").exists())
            status, _ = self.request("POST", "/api/batch/create", {"name": "x", "strategy": {},
                                     "datasets": [{"template": str(self.p / "a_????.cbf"), "xdsinp": str(outside / "XDS.INP")}]})
            self.assertEqual(status, 403)
            # the program locations are set where the server starts: a client cannot point them elsewhere
            before = (str(m.xds_runner.xds_path), m.CCP4_BIN, m.NEGGIA_LIB)
            for key in ("xds_path", "ccp4_bin", "neggia_lib"):
                status, body = self.request("POST", "/api/config", {key: str(outside)})
                self.assertEqual(status, 403, (key, body))
            self.assertEqual((str(m.xds_runner.xds_path), m.CCP4_BIN, m.NEGGIA_LIB), before)
            # the same values sent back with another setting are accepted
            self.assertEqual(self.request("POST", "/api/config", {"xds_path": before[0], "parallel": m.XDS_PARALLEL})[0], 200)

    # ── group C: Stop hits the program it belongs to ─────────────────────────
    def test_stop_with_a_kind_leaves_other_programs_of_the_project_running(self):
        self.control(INIT="quiet")
        result = []
        thread = threading.Thread(target=lambda: result.extend(self.stream(steps="INIT")))
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not self.executed() and time.monotonic() < deadline:
                time.sleep(0.02)
            status, body = self.request("POST", "/api/stop", {"project_name": self.name, "kind": "xscale"})
            self.assertEqual((status, body.get("stopped")), (200, 0), body)          # no XSCALE running: XDS keeps going
            self.assertTrue(m._jobs_running(self.name))
            self.assertEqual(self.request("POST", "/api/stop", {"project_name": self.name, "kind": "bogus"})[0], 400)
            status, body = self.request("POST", "/api/stop", {"project_name": self.name, "kind": "xds"})
            self.assertEqual(body.get("stopped"), 1, body)
        finally:
            thread.join(15)
        self.assert_terminal(result, "stopped")

    def test_kill_all_programs_on_shutdown_ends_them_before_returning(self):
        self.control(INIT="quiet")
        thread = threading.Thread(target=lambda: self.stream(steps="INIT"))
        thread.start()
        deadline = time.monotonic() + 5
        while not self.executed() and time.monotonic() < deadline:
            time.sleep(0.02)
        with m._proc_lock:
            procs = [r["proc"] for r in m._PROCS.values()]
        self.assertTrue(procs)
        m._kill_all_procs()
        self.assertTrue(all(proc.poll() is not None for proc in procs))            # dead now, not when a monitor gets to it
        thread.join(15)

    def test_if_better_restores_the_first_integration_when_reintegration_loses(self):
        (self.p / "XDS.INP").write_text("JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nDATA_RANGE= 1 60\nOSCILLATION_RANGE= 0.1\n")
        # the AutoPilot tab's route never asks for 'if_better' (only a batch does): drive it directly
        collected = []
        with patch.object(m, "_ap_optimize_is_better", return_value=(False, "ISa 21.20 -> 18.00")):
            m.stream_autopilot(self.name, collected.append, optimize="if_better", dcc_half=False)
        text = "".join(collected)
        self.assertIn("Re-integration rejected: ISa 21.20 -> 18.00", text)
        self.assertIn("First integration restored", text)
        summary = [json.loads(block.split("data: ", 1)[1]) for block in text.split("\n\n")
                   if block.startswith("event: ap_done")][-1]["summary"]
        self.assertIs(summary["optimization"]["kept"], False, summary.get("optimization"))
        self.assertTrue((self.p / "pre_optimize" / "CORRECT.LP").is_file())

    def test_autopilot_excludes_frames_by_the_only_column_and_writes_them(self):
        (self.p / "XDS.INP").write_text("JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nDATA_RANGE= 1 100\nOSCILLATION_RANGE= 0.1\n")
        lines = []
        for i in range(100):
            only = -3.0 if 50 <= i < 54 else 0.1 + 0.01 * (i % 5)
            every = -50.0 if i == 20 else 0.1
            lines.append("a %d 1000 90.0 90.0 %.2f 1000 90.0 90.0 %.2f" % (i + 1, only, every))
        tool = self.p / "fake_xdscc12"
        tool.write_text("")
        real_run = m._run_streaming

        commands = []

        def run(cmd, cwd, on_line, **kwargs):
            if cmd[0] != str(tool):
                return real_run(cmd, cwd, on_line, **kwargs)
            commands.append(cmd)
            for line in lines:
                on_line(line)
            return 0, "ok"

        collected = []
        with patch.object(m, "XDSCC12_BIN", str(tool)), patch.object(m, "_run_streaming", run):
            m.stream_autopilot(self.name, collected.append, optimize=True, dcc_half=True)
        text = "".join(collected)
        summary = [json.loads(block.split("data: ", 1)[1]) for block in text.split("\n\n")
                   if block.startswith("event: ap_done")][-1]["summary"]
        record = summary["dcc_half"]
        self.assertEqual((record["n_excluded"], record["column"], record["n_total"], record["left_out"]), (4, "only", 100, 0), record)
        written = (self.p / "XDS.INP").read_text()
        self.assertRegex(written, r"(?m)^EXCLUDE_DATA_RANGE\s*=\s*51\s+54")
        self.assertNotRegex(written, r"(?m)^EXCLUDE_DATA_RANGE\s*=\s*21\s+21")
        self.assertIn("Re-integrating with bad frames excluded", text)
        self.assertEqual(len(commands), 1, commands)
        self.assertEqual(commands[0][1], "-dmax", commands)
        self.assertEqual(float(commands[0][2]), record["dmax"])
        self.assertEqual(commands[0][-1], "XDS_ASCII.HKL")

    def test_the_tab_runs_xdscc12_to_the_high_resolution_limit_it_is_given(self):
        (m._project_out_dir(self.p) / "XDS_ASCII.HKL").write_text("!END_OF_HEADER\n!END_OF_DATA\n")
        tool = self.p / "fake_xdscc12"
        tool.write_text("")
        commands = []

        def run(cmd, cwd, on_line, **kwargs):
            commands.append(cmd)
            on_line("a 1 1000 90.0 90.0 0.10 1000 90.0 90.0 0.10")
            return 0, "ok"

        with patch.object(m, "XDSCC12_BIN", str(tool)), patch.object(m, "_run_streaming", run):
            for dmax in ("2.4", "", "x"):
                m.stream_xdscc12(self.name, [].append, batch_width="1", nbin="5", dmax=dmax)
        self.assertEqual(commands[0][-3:], ["-dmax", "2.40", "XDS_ASCII.HKL"], commands)
        self.assertNotIn("-dmax", commands[1], commands)
        self.assertNotIn("-dmax", commands[2], commands)

    def test_if_better_restores_the_first_integration_when_reintegration_fails(self):
        (self.p / "XDS.INP").write_text("JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nDATA_RANGE= 1 60\nOSCILLATION_RANGE= 0.1\n")
        self.control(INTEGRATE="exit_again")
        collected = []
        m.stream_autopilot(self.name, collected.append, optimize="if_better", dcc_half=False)
        text = "".join(collected)
        self.assertIn("Re-integration failed", text)
        self.assertIn("First integration restored", text)
        summary = [json.loads(block.split("data: ", 1)[1]) for block in text.split("\n\n")
                   if block.startswith("event: ap_done")][-1]["summary"]
        self.assertIs(summary["optimization"]["kept"], False, summary.get("optimization"))
        self.assertTrue(m._pfile(self.p, "CORRECT.LP").is_file())

    def test_autopilot_result_save_failure_is_terminal(self):
        original=m.ProjectManager._write_meta
        def write(path,data):
            if path.name=='AUTOPILOT_RESULTS.json':raise OSError('result cache disk full')
            return original(path,data)
        with patch.object(m.ProjectManager,'_write_meta',side_effect=write):
            events=self.stream('/api/autopilot/stream',optimize='0',dcc_half='0')
        self.assert_terminal(events,'error','ap_done')
        self.assertFalse((self.p/'AUTOPILOT_RESULTS.json').exists())

    def test_quick_autoindex_workflow_finishes_and_caches_results(self):
        events=self.stream('/api/autoindex/stream',tier='quick')
        self.assert_terminal(events,'completed','ai_done')
        result=[d for e,d in events if e=='ai_results']
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]['any_success'])
        self.assertGreater(result[0]['total_trials'],0)
        self.assertTrue(self.request('GET',self.url+'/autoindex-cached')[1]['has_results'])
        self.assertFalse((self.p/'_autoindex').exists())

    def test_launch_failure_finishes_stream_and_releases_reservation(self):
        with patch.object(m.subprocess,'Popen',side_effect=OSError('executable launch denied')):
            events=self.stream(step='INIT')
        self.assert_terminal(events,'error')
        self.assertEqual(self.executed(),[])
        self.assert_terminal(self.stream(step='INIT'),'completed')

    def test_autopilot_cannot_diagnose_old_logs_after_preparation_failure(self):
        self.assert_terminal(self.stream('/api/autopilot/stream',optimize='0',dcc_half='0'),'completed','ap_done')
        executed=self.executed()
        original=m.os.replace
        def replace(src,dst):
            if str(dst).endswith('.LP.previous_attempt'):raise PermissionError('previous log is locked')
            return original(src,dst)
        with patch.object(m.os,'replace',side_effect=replace):
            events=self.stream('/api/autopilot/stream',optimize='0',dcc_half='0')
        terminal=[d for e,d in events if e=='ap_done']
        self.assertEqual(len(terminal),1)
        self.assertIn(terminal[0]['status'],('error','failed'))
        self.assertEqual(self.executed(),executed)

    # ── agent route ─────────────────────────────────────────────────────────
    AGENT_KEY = 'agent-key-for-the-tests'

    def agent_on(self, level='own'):
        for name, value in (('AGENT_LEVEL', level), ('AGENT_KEY', self.AGENT_KEY)):
            patcher = patch.object(m, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def mcp_raw(self, method, body=None, headers=None):
        """A request with no page token or cookie, only what is given."""
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=120)
        try:
            all_headers = {'Content-Type': 'application/json', **(headers or {})}
            conn.request(method, '/api/mcp', json.dumps(body) if body is not None else None, all_headers)
            response = conn.getresponse()
            text = response.read().decode()
            return response.status, (json.loads(text) if text else None)
        finally:
            conn.close()

    def rpc(self, method, params=None, key=None):
        status, reply = self.mcp_raw('POST', {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}},
                                     {'Authorization': 'Bearer ' + (key or self.AGENT_KEY)})
        self.assertEqual(status, 200, reply)
        return reply

    def tool(self, tool_name, **arguments):
        reply = self.rpc('tools/call', {'name': tool_name, 'arguments': arguments})
        self.assertIn('result', reply, reply)
        result = reply['result']
        text = result['content'][0]['text']
        return (text if result['isError'] else json.loads(text)), result['isError']

    def tool_ok(self, tool_name, **arguments):
        value, failed = self.tool(tool_name, **arguments)
        self.assertFalse(failed, value)
        return value

    def dataset_folder(self, label='frames'):
        """Frames with a beamline XDS.INP beside them, as find_datasets meets them."""
        folder = scratch / ('agent_data_' + self._testMethodName) / label
        (folder / 'fast_dp').mkdir(parents=True, exist_ok=True)
        for n in range(1, 7):
            (folder / ('xtal_%04d.cbf' % n)).write_bytes(b'')
        (folder / 'fast_dp' / 'XDS.INP').write_text(
            'JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nNAME_TEMPLATE_OF_DATA_FRAMES= ' + str(folder / 'xtal_????.cbf')
            + '\nDATA_RANGE= 1 60\nOSCILLATION_RANGE= 0.1\n', encoding='utf-8')
        return folder

    def wait_job(self, job_id, seconds=90):
        deadline = time.time() + seconds
        while time.time() < deadline:
            status = self.tool_ok('job_status', job_id=job_id)
            if not status['running']:
                return status
            time.sleep(0.2)
        self.fail('job did not finish')

    def test_agent_route_is_off_until_chosen_and_needs_its_own_key(self):
        message = {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}
        good = {'Authorization': 'Bearer ' + self.AGENT_KEY}
        self.assertEqual(m.AGENT_LEVEL, 'off')
        self.assertEqual(self.mcp_raw('POST', message, good)[0], 403)
        self.agent_on()
        self.assertEqual(self.mcp_raw('POST', message)[0], 401)
        self.assertEqual(self.mcp_raw('POST', message, {'Authorization': 'Bearer wrong'})[0], 401)
        # the page's token and cookie are not the agent key, and the agent key is not the page's token
        self.assertEqual(self.mcp_raw('POST', message, {'X-CrystalPilot-Token': m.API_TOKEN})[0], 401)
        self.assertEqual(self.mcp_raw('POST', message, {'Cookie': 'cp_token_%d=%s' % (self.server.server_address[1], m.API_TOKEN)})[0], 401)
        self.assertEqual(self.mcp_raw('POST', message, {'Authorization': 'Bearer ' + m.API_TOKEN})[0], 401)
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=15)
        conn.request('GET', '/api/projects', headers=good)
        self.assertEqual(conn.getresponse().status, 403)
        conn.close()
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=15)
        conn.request('POST', '/api/agent', json.dumps({'level': 'full'}), {'Content-Type': 'application/json', **good})
        self.assertEqual(conn.getresponse().status, 403)
        conn.close()
        self.assertEqual(self.mcp_raw('POST', message, {**good, 'Origin': 'http://evil.example'})[0], 403)
        self.assertEqual(self.mcp_raw('POST', message, {**good, 'Origin': 'http://localhost:8000'})[0], 200)
        self.assertEqual(self.mcp_raw('GET', None, good)[0], 405)
        self.assertEqual(self.mcp_raw('DELETE', None, good)[0], 405)
        self.assertEqual(self.mcp_raw('POST', {'jsonrpc': '2.0', 'method': 'notifications/initialized'}, good)[0], 202)
        self.assertEqual(self.mcp_raw('POST', message, {**good, 'MCP-Protocol-Version': '1999-01-01'})[0], 400)
        with patch.object(m, 'HOST', '0.0.0.0'):
            self.assertEqual(self.mcp_raw('POST', message, good)[0], 403)
        with patch.object(m, 'RESTRICT_BROWSE', True):
            self.assertEqual(self.mcp_raw('POST', message, good)[0], 403)

    def test_agent_initialize_and_levels_decide_which_tools_exist(self):
        self.agent_on('read')
        reply = self.rpc('initialize', {'protocolVersion': '2025-06-18', 'clientInfo': {'name': 'test client'}, 'capabilities': {}})
        self.assertEqual(reply['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(reply['result']['serverInfo']['version'], m.VERSION)
        self.assertEqual(self.rpc('initialize', {'protocolVersion': '2099-01-01'})['result']['protocolVersion'], m.AGENT_PROTOCOL_VERSIONS[0])
        self.assertEqual(self.rpc('no/such/method')['error']['code'], -32601)
        names = [t['name'] for t in self.rpc('tools/list')['result']['tools']]
        self.assertIn('get_statistics', names)
        self.assertNotIn('run_autopilot', names)
        refused = self.rpc('tools/call', {'name': 'run_autopilot', 'arguments': {'datasets': []}})
        self.assertEqual(refused['error']['code'], -32602)
        with patch.object(m, 'AGENT_LEVEL', 'own'):
            tools = {t['name']: t for t in self.rpc('tools/list')['result']['tools']}
            self.assertIn('run_autopilot', tools)
            self.assertFalse(tools['run_autopilot']['annotations']['readOnlyHint'])
            self.assertTrue(tools['get_statistics']['annotations']['readOnlyHint'])

    def test_agent_panel_sets_the_level_and_makes_a_key_that_survives_and_can_be_replaced(self):
        self.addCleanup(lambda: m.agent_configure({'level': 'off'}, 1))
        status, off = self.request('GET', '/api/agent')
        self.assertEqual((status, off['level'], off['key']), (200, 'off', ''))
        on = self.request('POST', '/api/agent', {'level': 'own'})[1]
        self.assertEqual(on['level'], 'own')
        self.assertGreater(len(on['key']), 20)
        self.assertTrue(on['url'].endswith('/api/mcp'))
        self.assertEqual(self.rpc('ping', key=on['key'])['result'], {})
        saved = json.loads(m.SETTINGS_FILE.read_text(encoding='utf-8'))
        self.assertEqual((saved['agent_level'], saved['agent_key']), ('own', on['key']))
        new = self.request('POST', '/api/agent', {'new_key': True})[1]
        self.assertNotEqual(new['key'], on['key'])
        self.assertEqual(self.mcp_raw('POST', {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}, {'Authorization': 'Bearer ' + on['key']})[0], 401)
        self.assertEqual(self.request('POST', '/api/agent', {'level': 'everything'})[0], 400)
        self.assertEqual(self.request('POST', '/api/agent', {'level': 'off'})[1]['level'], 'off')
        self.assertEqual(self.mcp_raw('POST', {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}, {'Authorization': 'Bearer ' + new['key']})[0], 403)
        with patch.object(m, 'RESTRICT_BROWSE', True):
            self.assertEqual(self.request('POST', '/api/agent', {'level': 'own'})[0], 403)

    def test_agent_key_never_reaches_a_log_a_report_or_an_export(self):
        self.agent_on()
        self.assertNotIn(self.AGENT_KEY, m._report_redact('key ' + self.AGENT_KEY))
        self.assertNotIn(self.AGENT_KEY, m._LogTee._redact('key ' + self.AGENT_KEY))
        self.assertFalse(m._export_wanted(m.AGENT_LOG_NAME, True))

    def test_agent_reads_results_as_numbers_and_files_in_parts(self):
        self.agent_on('read')
        self.assert_terminal(self.stream(), 'completed')
        listed = self.tool_ok('list_projects')
        self.assertIn(self.name, [p['name'] for p in listed['projects']])
        self.assertIn('xds', [p['id'] for p in listed['programs']])
        project = self.tool_ok('get_project', project=self.name)
        self.assertEqual(project['completed_steps'], m.XDS_PIPELINE)
        self.assertIn('XDS.INP', project['input_files'])
        stats = self.tool_ok('get_statistics', project=self.name)
        self.assertIsInstance(stats['space_group']['number'], (int, float))
        self.assertIsInstance(stats['cell']['a_A'], float)
        self.assertNotIn('shells', stats)
        full = self.tool_ok('get_statistics', project=self.name, detail='full', source='CORRECT')
        self.assertEqual(len(full['shells']), full['n_shells'])
        self.assertEqual(sorted(full['cutoffs']), sorted(['isig2', 'cc_half_50', 'cc_half_sig', 'r_obs_55']))
        self.assertIsInstance(self.tool_ok('get_diagnostics', project=self.name, step='CORRECT')['autopilot_diagnostics'], list)
        self.assertEqual(self.tool_ok('compare_runs', project=self.name)['step'], 'CORRECT')
        evidence = self.tool_ok('get_space_group_evidence', project=self.name)
        self.assertIn('current', evidence)
        self.assertIn(evidence['verdict']['screw_axes_verdict'], ('clear', 'weak', 'enantiomorphs', 'undecided', 'differs', 'no axial data'))
        self.assertIn('aP always fits', evidence['lattice_note'])
        tail = self.tool_ok('read_project_file', project=self.name, file='CORRECT.LP', limit=3)
        self.assertLessEqual(len(tail['text'].splitlines()), 3)
        whole = self.tool_ok('read_project_file', project=self.name, file='xds.inp', offset=1, limit=1)
        self.assertEqual(whole['first_line'], 1)
        self.assertEqual(whole['text'].split()[0], 'JOB=')
        self.assertEqual(self.tool_ok('read_project_file', project=self.name, file='XDS.INP', search='oscillation')['matches'], 1)
        self.assertTrue(self.tool('read_project_file', project=self.name, file='../metadata.json')[1])
        self.assertTrue(self.tool('get_statistics', project='no such project')[1])
        self.assertIn('files', self.tool_ok('get_analysis', project=self.name, kind='hkl_files'))
        self.assertTrue(self.tool('get_analysis', project=self.name, kind='nonsense')[1])

    def test_agent_run_gets_what_the_wizard_gets_and_leaves_a_record(self):
        self.agent_on('own')
        folder = self.dataset_folder()
        found = self.tool_ok('find_datasets', folders=[str(folder)])
        self.assertEqual(len(found['datasets']), 1, found)
        entry = found['datasets'][0]
        self.assertEqual(entry['xdsinp_state'], 'imported')
        self.assertTrue(entry['recommended'])
        strategy = {'optimize': 'never', 'dcc_half': 'off'}
        # the page's route, with what the wizard sends for the same data set and choices
        wizard = {k: entry[k] for k in ('kind', 'template', 'label', 'folder', 'frames', 'first', 'last', 'xdsinp')}
        page_run = self.request('POST', '/api/batch/create', {'name': 'page', 'datasets': [dict(wizard, project='page_' + self.name.split()[0][:30])], 'strategy': strategy})[1]
        self.assertEqual(self.request('POST', '/api/batch/start', {'id': page_run['id']})[0], 200)
        self._batch_wait(page_run['id'])
        started = self.tool_ok('run_autopilot', datasets=[dict(entry, project='agent_' + self.name.split()[0][:30])], strategy=strategy, reason='test of the record')
        self.assertEqual(started['status'], 'running', started)
        self.assertEqual(started['strategy'], m.normalize_strategy(strategy))
        ended = self.wait_job(started['job_id'])
        self.assertEqual(ended['status'], 'ended', ended)
        self.assertEqual(ended['counts'], {'done': 1}, ended)
        self.assertEqual(ended['items'][0]['status'], 'done', ended)
        self.assertEqual(ended['items'][0]['results']['space_group'], 20)
        self.assertIn('log_tail', ended)
        agent_project = started['projects'][0]
        page_project = page_run['items'][0]['project']
        read = lambda p: (m._pdir(p) / 'XDS.INP').read_text(encoding='utf-8')
        self.assertEqual(read(agent_project), read(page_project))
        results = lambda p: {k: v for k, v in m.batch_metrics(p).items() if k != 'mtz'}      # the MTZ's path names its project
        self.assertEqual(results(agent_project), results(page_project))
        self.assertTrue(m.batch_load(started['job_id'][6:])['name'].startswith('Agent: '))
        self.assertEqual(m.ProjectManager.get(agent_project)['created_by'], 'agent')
        self.assertNotIn('created_by', m.ProjectManager.get(page_project))
        record = [json.loads(line) for line in (m._pdir(agent_project) / m.AGENT_LOG_NAME).read_text(encoding='utf-8').splitlines()]
        self.assertEqual([r['outcome'] for r in record], ['started', 'done'])
        self.assertEqual(record[0]['reason'], 'test of the record')
        self.assertEqual(record[0]['job_id'], started['job_id'])
        self.assertFalse((m._pdir(page_project) / m.AGENT_LOG_NAME).exists())

    def test_agent_run_by_label_alone_gets_the_data_set_find_datasets_gave(self):
        self.agent_on('own')
        folder = self.dataset_folder()
        entry = self.tool_ok('find_datasets', folders=[str(folder)])['datasets'][0]
        # what a small model sent: the label, with keys of its own
        message, failed = self.tool('run_autopilot', datasets=[{'label': 'no such data set', 'selection': 1}])
        self.assertTrue(failed)
        self.assertIn(entry['label'], message)
        self.assertIn('no such data set', message)
        started = self.tool_ok('run_autopilot', datasets=[{'existing_project': None, 'label': entry['label'], 'selection': 1}],
                               strategy={'optimize': 'never', 'dcc_half': 'off'})
        ended = self.wait_job(started['job_id'])
        self.assertEqual(ended['counts'], {'done': 1}, ended)
        item = m.batch_load(started['job_id'][6:])['items'][0]
        self.assertEqual((item['template'], item['xdsinp']), (entry['template'], entry['xdsinp']))
        # the overall statistics are the ones AutoPilot reports, and say where they come from
        results = ended['items'][0]['results']
        summary = json.loads((m._pdir(started['projects'][0]) / 'AUTOPILOT_RESULTS.json').read_text(encoding='utf-8'))
        total = [r for r in summary.get('stats_table') or [] if r.get('resolution') == 'total']
        if total:
            self.assertEqual(results['statistics_from'], summary.get('stats_source') or 'CORRECT')
            self.assertEqual(results['completeness_pct'], m._agent_num(total[0]['completeness']))
        else:
            self.assertEqual(results['statistics_from'], 'CORRECT')
        # what the user asks after a run is in the reply, read from the project's files
        report = ended['items'][0]['report']
        self.assertIn('ISa', ended['glossary']['isa'])
        self.assertEqual(report['space_group']['current'].split('(#')[1].rstrip(')'), str(results['space_group']))
        self.assertIn(report['space_group']['screw_axes_verdict'], ('clear', 'weak', 'enantiomorphs', 'undecided', 'differs', 'no axial data'))
        self.assertEqual(report['cell']['a'], results['cell'][0])
        stats = self.tool_ok('get_statistics', project=started['projects'][0])
        self.assertIn('overall_to_A', stats)
        self.assertIn('not the data', stats['glossary']['isa'])
        if stats['source'] == 'CORRECT':
            self.assertIn('not a resolution cut-off', stats['overall_note'])

    def test_agent_can_list_datasets_without_the_xdsinp_search_and_the_run_still_searches(self):
        self.agent_on('own')
        folder = self.dataset_folder()
        listed = self.tool_ok('find_datasets', folders=[str(folder)], search_xdsinp=False)
        entry = listed['datasets'][0]
        self.assertEqual(entry['xdsinp_state'], 'not searched')
        self.assertNotIn('xdsinp', entry)
        self.assertNotIn('xdsinp_files_looked_at', listed)
        started = self.tool_ok('run_autopilot', datasets=[entry], strategy={'optimize': 'never', 'dcc_half': 'off'})
        self.assertEqual(self.wait_job(started['job_id'])['counts'], {'done': 1})
        batch = m.batch_load(started['job_id'][6:])
        self.assertTrue(batch['items'][0]['xdsinp'].endswith('XDS.INP'), batch['items'][0])

    def test_agent_slow_xdsinp_search_never_blocks_a_call_or_writes_one_from_the_header(self):
        self.agent_on('own')
        folder = self.dataset_folder()
        original, release = m.find_xdsinp_candidates, threading.Event()
        self.addCleanup(release.set)
        calls = []
        def slow(*args, **kwargs):
            calls.append(1)
            release.wait(30)
            return original(*args, **kwargs)
        with patch.object(m, 'find_xdsinp_candidates', side_effect=slow), patch.object(m, 'AGENT_SEARCH_WAIT_SECONDS', 0.05):
            first = self.tool_ok('find_datasets', folders=[str(folder)])
            self.assertTrue(first['xdsinp_search_running'], first)
            self.assertEqual(first['datasets'][0]['xdsinp_state'], 'searching')
            self.assertNotIn('xdsinp', first['datasets'][0])
            # a run from that reply waits for the search: it must not write XDS.INP from the header
            message, failed = self.tool('run_autopilot', datasets=[first['datasets'][0]], strategy={'optimize': 'never', 'dcc_half': 'off'})
            self.assertTrue(failed, message)
            self.assertIn('still going', message)
            self.assertEqual(self.tool_ok('list_projects')['autopilot_running'], None)
            self.assertTrue(self.tool_ok('find_datasets', folders=[str(folder)])['xdsinp_search_running'])
            self.assertEqual(len(calls), 2)     # find_datasets' search, and the run's for its one data set; asking again starts none
            release.set()
            deadline = time.time() + 15
            while time.time() < deadline:
                collected = self.tool_ok('find_datasets', folders=[str(folder)])
                if not collected.get('xdsinp_search_running'):
                    break
                time.sleep(0.05)
        self.assertEqual(collected['datasets'][0]['xdsinp_state'], 'imported', collected)
        self.assertTrue(collected['datasets'][0]['xdsinp'].endswith('XDS.INP'))
        self.assertEqual(len(calls), 2)
        # a failed search says so, and the next call tries again
        with patch.object(m, 'find_xdsinp_candidates', side_effect=OSError('share went away')):
            message, failed = self.tool('find_datasets', folders=[str(folder)], also_search=[str(folder.parent)])
            self.assertTrue(failed)
            self.assertIn('search failed', message)
        self.assertEqual(self.tool_ok('find_datasets', folders=[str(folder)], also_search=[str(folder.parent)])['datasets'][0]['xdsinp_state'], 'imported')

    # ── controls for working by hand ────────────────────────────────────────
    def own_project(self, name=None):
        """A project of the agent's own, with XDS.INP from a beamline file beside the frames."""
        name = name or ('own_' + self._testMethodName[-40:])
        folder = self.dataset_folder()
        self.tool_ok('create_project', name=name, reason='test')
        written = self.tool_ok('generate_xdsinp', project=name, template=str(folder / 'xtal_????.cbf'), from_xdsinp=str(folder / 'fast_dp' / 'XDS.INP'))
        self.assertGreater(written['lines'], 3, written)
        self.addCleanup(lambda: m.ProjectManager.delete(name))
        return name

    def wait_run(self, job_id, seconds=60):
        deadline = time.time() + seconds
        while time.time() < deadline:
            status = self.tool_ok('job_status', job_id=job_id)
            if not status['running']:
                return status
            time.sleep(0.05)
        self.fail('run did not finish')

    def test_agent_works_by_hand_from_new_project_to_results(self):
        self.agent_on('own')
        project = self.own_project()
        self.assertTrue(self.tool_ok('get_project', project=project)['created_by_agent'])
        started = self.tool_ok('run_program', project=project, program='xds', options={'steps': ['XYCORR', 'INIT', 'COLSPOT', 'IDXREF']}, reason='first steps')
        self.assertTrue(started['job_id'].startswith('run:'))
        ended = self.wait_run(started['job_id'])
        self.assertEqual(ended['status'], 'completed', ended)
        self.assertEqual([s['step'] for s in ended['steps']], ['XYCORR', 'INIT', 'COLSPOT', 'IDXREF'])
        self.assertTrue(ended['log_tail'])
        # the rest, then re-integration with the refined geometry
        self.assertEqual(self.wait_run(self.tool_ok('run_program', project=project, program='xds', options={'steps': ['DEFPIX', 'INTEGRATE', 'CORRECT']})['job_id'])['status'], 'completed')
        self.assertIsInstance(self.tool_ok('get_statistics', project=project)['overall']['completeness_pct'], float)
        again = self.wait_run(self.tool_ok('run_program', project=project, program='xds', options={'reintegrate': True})['job_id'])
        self.assertEqual(again['status'], 'completed', again)
        self.assertTrue((m._pdir(project) / 'XPARM.XDS').read_text().startswith('test geometry'))
        # the same run is listed for the page, marked as an agent's
        listed = self.request('GET', '/api/jobs?project=' + urllib.parse.quote(project))[1]['jobs']
        self.assertTrue(all(j['agent'] and j['followable'] and not j['background'] for j in listed), listed)
        self.assertEqual(self.request('GET', '/api/jobs?project=' + urllib.parse.quote(self.name))[1]['jobs'], [])
        record = [json.loads(line) for line in (m._pdir(project) / m.AGENT_LOG_NAME).read_text(encoding='utf-8').splitlines()]
        outcomes = [r['outcome'] for r in record if r['tool'] == 'run_program']
        self.assertEqual(outcomes, ['started', 'completed'] * 3)
        self.assertEqual(record[0]['tool'], 'create_project')

    def test_agent_runs_every_other_program_and_reports_failures(self):
        self.agent_on('own')
        project = self.own_project()
        self.assertEqual(self.wait_run(self.tool_ok('run_program', project=project, program='xds')['job_id'])['status'], 'completed')
        (m._pdir(project) / 'XDS.INP').read_text()
        self.tool_ok('set_parameters', project=project, file='XSCALE.INP', params={'OUTPUT_FILE': 'scaled.ahkl', "FRIEDEL'S_LAW": 'TRUE', 'INPUT_FILE': 'XDS_ASCII.HKL'})
        self.assertEqual(self.wait_run(self.tool_ok('run_program', project=project, program='xscale')['job_id'])['status'], 'completed')
        self.assertIsInstance(self.tool_ok('get_statistics', project=project, source='XSCALE')['n_shells'], int)
        # XSCALE ran after CORRECT: the statistics without a source are its, and CORRECT's say how far they reach
        self.assertEqual(self.tool_ok('get_statistics', project=project)['source'], 'XSCALE')
        self.assertIn('not a resolution cut-off', self.tool_ok('get_statistics', project=project, source='CORRECT')['overall_note'])
        message = self.wait_run(self.tool_ok('run_program', project=project, program='xdsconv')['job_id'])
        self.assertEqual(message['status'], 'error')
        self.assertIn('XDSCONV.INP', message['errors'][0])
        written = self.tool_ok('set_parameters', project=project, file='XDSCONV.INP', params={'INPUT_FILE': 'scaled.ahkl', 'OUTPUT_FILE': 'temp.hkl CCP4_I+F', "FRIEDEL'S_LAW": 'FALSE'})
        self.assertEqual(len([c for c in written['changes'] if c.startswith('+')]), 3, written)
        self.assertEqual(self.wait_run(self.tool_ok('run_program', project=project, program='xdsconv', options={'mtz_name': 'final.mtz'})['job_id'])['status'], 'completed')
        trial = self.wait_run(self.tool_ok('run_program', project=project, program='autoindex', options={'tier': 'quick'})['job_id'], 90)
        self.assertEqual(trial['status'], 'completed', trial)
        applied = self.tool_ok('apply_suggestion', project=project, kind='autoindex_trial')
        self.assertTrue(any('SIGNAL_PIXEL' in c for c in applied['changes']), applied)
        self.assertTrue(self.tool('apply_suggestion', project=project, kind='autoindex_trial', params={'trial': 99})[1])
        for bad in ({'program': 'nonsense'}, {'program': 'xds', 'options': {'steps': ['NOPE']}}, {'program': 'xds', 'options': {'nonsense': 1}},
                    {'program': 'autoindex', 'options': {'tier': 'huge'}}, {'program': 'xds', 'options': {'reintegrate': True, 'steps': ['CORRECT']}},
                    {'program': 'pointless', 'options': {'input_file': '/etc/passwd'}}, {'program': 'gemmi_mtz', 'options': {'input_file': '../../x'}},
                    {'program': 'xdsconv', 'options': {'mtz_name': '../x.mtz'}}, {'program': 'xds', 'new_run_folder': True, 'options': {'steps': ['CORRECT']}},
                    {'program': 'pointless', 'new_run_folder': True}):
            self.assertTrue(self.tool('run_program', project=project, **bad)[1], bad)
        failing = self.own_project('own_failing_' + self._testMethodName[-20:])
        (m._pdir(failing) / 'control.json').write_text(json.dumps({'XYCORR': 'exit'}))
        failed = self.wait_run(self.tool_ok('run_program', project=failing, program='xds', options={'steps': ['XYCORR']})['job_id'])
        self.assertNotEqual(failed['status'], 'completed', failed)
        self.assertTrue(failed['steps'] or failed['errors'], failed)

    def test_agent_run_can_be_stopped_goes_one_at_a_time_and_outlasts_the_job_list(self):
        self.agent_on('own')
        project = self.own_project()
        (m._pdir(project) / 'control.json').write_text(json.dumps({'XYCORR': 'quiet'}))
        job = self.tool_ok('run_program', project=project, program='xds', options={'steps': ['XYCORR']})['job_id']
        deadline = time.time() + 15
        while time.time() < deadline and not (m._pdir(project) / 'executed.jsonl').exists():
            time.sleep(0.05)
        self.assertTrue(self.tool_ok('job_status', job_id=job, wait_seconds=0)['running'])
        # a run that does not move: the answer waits, then says so
        t0 = time.time()
        waited = self.tool_ok('job_status', job_id=job, wait_seconds=3)
        self.assertTrue(waited['running'])
        self.assertGreaterEqual(time.time() - t0, 2.5)
        self.assertGreaterEqual(waited['waited_seconds'], 2.5)
        self.assertEqual(waited['check_after_seconds'], 0)
        # while it goes on the answer is brief; the whole state on request
        self.assertNotIn('log_tail', waited)
        self.assertEqual(waited['steps_done'], [])
        self.assertLess(len(json.dumps(waited)), 600)
        self.assertIn('log_tail', self.tool_ok('job_status', job_id=job, wait_seconds=0, detail='full'))
        # numbers read while the run goes on say they are not its result
        self.assertIn('still running', self.tool_ok('get_analysis', project=project, kind='hkl_files')['still_running'])
        self.assertNotIn('still_running', self.tool_ok('get_analysis', project=self.name, kind='hkl_files'))
        message, failed = self.tool('run_program', project=project, program='xds')
        self.assertTrue(failed)
        self.assertIn('one runs at a time', message)
        message, failed = self.tool('run_autopilot', datasets=[{'existing_project': project}])
        self.assertTrue(failed)
        self.assertIn('one runs at a time', message)
        self.assertTrue(self.tool_ok('stop_job', job_id=job, reason='test')['was_running'])
        ended = self.wait_run(job, 30)
        self.assertEqual(ended['status'], 'stopped', ended)
        self.assertTrue(self.tool('stop_job', job_id='run:nonsense')[1])
        self.assertTrue(self.tool('job_status', job_id='run:nonsense')[1])
        # once the job list has forgotten it (after 30 minutes or a restart) the project's log answers
        with m._proc_lock:
            m._DONE_JOBS.pop(job[4:], None)
        self.assertEqual(self.tool_ok('job_status', job_id=job)['status'], 'stopped')
        # a start with no end: the program stopped with the server
        log = m._pdir(project) / m.AGENT_LOG_NAME
        with open(str(log), 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({'job_id': 'run:lost', 'outcome': 'started', 'tool': 'run_program'}) + '\n')
        self.assertEqual(self.tool_ok('job_status', job_id='run:lost')['status'], 'interrupted')

    def test_agent_changes_input_files_with_their_rules(self):
        self.agent_on('own')
        project = self.own_project()
        done = self.tool_ok('set_parameters', project=project, params={'SIGNAL_PIXEL': 6, 'SPOT_RANGE': [[1, 10], [20, 30]]}, reason='weak spots')
        self.assertIn('+SIGNAL_PIXEL= 6', done['changes'])
        text = (m._pdir(project) / 'XDS.INP').read_text()
        self.assertIn('SPOT_RANGE= 1 10\nSPOT_RANGE= 20 30', text)
        self.assertIn('note', self.tool_ok('set_parameters', project=project, params={'SIGNAL_PIXEL': 6}))
        self.assertIn('!SIGNAL_PIXEL', '\n'.join(self.tool_ok('set_parameters', project=project, params={'SIGNAL_PIXEL': None})['changes']))
        for refused in ({'LIB': '/tmp/x.so'}, {'JOB': 'ALL'}, {'ROTATION_AXIS': '0 1 0'}, {'NX': '1\nLIB= /x'}):
            self.assertTrue(self.tool('set_parameters', project=project, params=refused)[1], refused)
        self.assertTrue(self.tool('set_parameters', project=project, file='OTHER.INP', params={'NX': 1})[1])
        self.assertTrue(self.tool('apply_space_group', project=project, number=999, cell=[1, 2, 3, 90, 90, 90])[1])
        self.assertTrue(self.tool('apply_space_group', project=project, number=19)[1])
        self.assertTrue(self.tool_ok('apply_space_group', project=project, number=19, cell=[78.1, 80.2, 37.3, 90, 90, 90])['changes'])
        values = m.xdsinp_values((m._pdir(project) / 'XDS.INP').read_text())
        self.assertEqual((values['SPACE_GROUP_NUMBER'], values['UNIT_CELL_CONSTANTS']), ('19', '78.1 80.2 37.3 90 90 90'))
        # the stamp the page checks before it saves a form over this change
        self.assertTrue(self.request('GET', '/api/projects/' + project)[1]['agent_changed_inp'])
        self.assertNotIn('agent_changed_inp', self.request('GET', self.url)[1])
        # a project with no XDS.INP yet is told where to start, and an existing one is not replaced by accident
        self.tool_ok('create_project', name='empty_' + project[:30])
        self.addCleanup(lambda: m.ProjectManager.delete('empty_' + project[:30]))
        self.assertIn('no XDS.INP', self.tool('set_parameters', project='empty_' + project[:30], params={'NX': 1})[0])
        self.assertIn('already has', self.tool('generate_xdsinp', project=project)[0])
        self.assertTrue(self.tool('create_project', name='bad name/x')[1])
        self.assertTrue(self.tool('create_project', name=project)[1])
        self.assertTrue(self.tool('generate_xdsinp', project=project, overwrite=True, template=str(self.dataset_folder() / 'xtal_????.cbf'), from_xdsinp=str(self.dataset_folder() / 'xtal_0001.cbf'))[1])

    def test_agent_applies_the_pages_suggestions(self):
        self.agent_on('own')
        project = self.own_project()
        self.assertEqual(self.wait_run(self.tool_ok('run_program', project=project, program='xds')['job_id'])['status'], 'completed')
        path = m._pdir(project) / 'XDS.INP'
        # resolution in XDS.INP: nine shells; a low limit above the cut-off stays
        self.tool_ok('apply_suggestion', project=project, kind='resolution_cutoff', params={'resolution': 2.05})
        values = m.xdsinp_values(path.read_text())
        self.assertEqual(values['INCLUDE_RESOLUTION_RANGE'], '50 2.05')
        self.assertEqual(values['RESOLUTION_SHELLS'], m.xds_shells(2.05))
        self.tool_ok('set_parameters', project=project, params={'INCLUDE_RESOLUTION_RANGE': '30 2.05'})
        self.tool_ok('apply_suggestion', project=project, kind='resolution_cutoff', params={'resolution': 1.9})
        self.assertEqual(m.xdsinp_values(path.read_text())['INCLUDE_RESOLUTION_RANGE'], '30 1.90')
        self.assertTrue(self.tool('apply_suggestion', project=project, kind='resolution_cutoff')[1])
        # resolution in XSCALE.INP
        self.tool_ok('apply_suggestion', project=project, kind='resolution_cutoff', params={'resolution': 2.05, 'file': 'XSCALE.INP'})
        xscale = (m._pdir(project) / 'XSCALE.INP').read_text()
        self.assertIn('INCLUDE_RESOLUTION_RANGE= 999 2.05', xscale)
        self.assertIn(m.xscale_shells(2.05), xscale)
        # ice rings: what was already excluded stays
        self.tool_ok('set_parameters', project=project, params={'EXCLUDE_RESOLUTION_RANGE': [['5.00', '4.90']]})
        self.tool_ok('apply_suggestion', project=project, kind='ice_rings', params={'rings': 'standard'})
        ranges = m._agent_active_ranges(path.read_text(), 'EXCLUDE_RESOLUTION_RANGE')
        self.assertIn(['5.00', '4.90'], ranges)
        self.assertEqual(len(ranges), len(m.LPParser.ICE_RING_POSITIONS) + 1)
        self.assertTrue(self.tool('apply_suggestion', project=project, kind='ice_rings', params={'rings': 'some'})[1])
        # frames: a batch number is the last frame of its batch, and earlier exclusions stay
        (m._pdir(project) / 'XDSCC12.LP').write_text('')
        with patch.object(m.LPParser, 'parse_xdscc12', return_value={'frames': [{'batch': 5 * (i + 1), 'delta_only': 0.1, 'delta_all': 0.1} for i in range(9)], 'frames_per_batch': 5, 'summary': {}}):
            self.tool_ok('set_parameters', project=project, params={'EXCLUDE_DATA_RANGE': [[1, 2]]})
            self.tool_ok('apply_suggestion', project=project, kind='frame_exclusions', params={'ranges': [{'start': 10, 'end': 15}, {'start': 5, 'end': 5}]})
            self.assertEqual(m._agent_active_ranges(path.read_text(), 'EXCLUDE_DATA_RANGE'), [['1', '2'], ['6', '15'], ['1', '5']])
            self.assertIn('no frames', self.tool('apply_suggestion', project=project, kind='frame_exclusions')[0])
            self.assertTrue(self.tool('apply_suggestion', project=project, kind='frame_exclusions', params={'ranges': [{'start': 'x'}]})[1])
        self.assertTrue(self.tool('apply_suggestion', project=project, kind='nonsense')[1])
        before = path.read_text()
        with patch.object(m.LPParser, 'parse_integrate', return_value={'beam_divergence': 0.123, 'reflecting_range': 0.456}):
            result = self.tool('apply_suggestion', project=project, kind='beam_parameters')
        if not result[1]:
            self.assertNotEqual(path.read_text(), before)

    def test_agent_levels_guard_the_controls_on_a_users_project(self):
        self.agent_on('own')
        self.assert_terminal(self.stream(), 'completed')
        before = (self.p / 'XDS.INP').read_text()
        attempts = [('run_program', {'program': 'xds'}), ('run_program', {'program': 'xds', 'new_run_folder': True}), ('set_parameters', {'params': {'NX': 1}}),
                    ('apply_space_group', {'number': 19, 'cell': [1, 2, 3, 90, 90, 90]}), ('apply_suggestion', {'kind': 'resolution_cutoff', 'params': {'resolution': 2}}),
                    ('generate_xdsinp', {'overwrite': True}), ('export_results', {'what': 'table1'})]
        for tool, extra in attempts:
            message, failed = self.tool(tool, project=self.name, **extra)
            self.assertTrue(failed, tool)
            self.assertIn("user's", message, tool)
        with patch.object(m, 'AGENT_LEVEL', 'read'):
            names = [t['name'] for t in self.rpc('tools/list')['result']['tools']]
            for name in ('run_program', 'set_parameters', 'apply_space_group', 'apply_suggestion', 'generate_xdsinp', 'create_project', 'merge_datasets', 'export_results'):
                self.assertNotIn(name, names)
            for name in ('view_frame', 'search_manual', 'plan_merge', 'job_status'):
                self.assertIn(name, names)
        with patch.object(m, 'AGENT_LEVEL', 'full'):
            for tool, extra in attempts[:1] + attempts[2:5]:
                message, failed = self.tool(tool, project=self.name, **extra)
                self.assertTrue(failed, tool)
                self.assertIn('overwrite', message, tool)
            self.assertEqual((self.p / 'XDS.INP').read_text(), before)
            # a new numbered folder keeps the earlier results and needs no overwrite
            job = self.tool_ok('run_program', project=self.name, program='xds', new_run_folder=True)
            self.assertEqual(self.wait_run(job['job_id'])['status'], 'completed')
            self.assertTrue((self.p / '1' / 'CORRECT.LP').is_file())
            self.assertTrue((self.p / 'CORRECT.LP').is_file())
            # the next run stays in that folder and takes the project's current XDS.INP there, as the page does
            done = self.allowed('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 7})
            self.assertTrue(done['changes'])
            again = self.allowed('run_program', project=self.name, program='xds', overwrite=True, options={'steps': ['CORRECT']})
            self.assertEqual(self.wait_run(again['job_id'])['status'], 'completed')
            self.assertIn('SIGNAL_PIXEL= 7', (self.p / '1' / 'XDS.INP').read_text())
            self.assertTrue(self.tool_ok('export_results', project=self.name, what='table1')['path'].endswith('_Table1.csv'))

    def test_agent_merges_and_exports(self):
        self.agent_on('own')
        folder_a, folder_b = self.dataset_folder('a'), self.dataset_folder('b')
        strategy = {'optimize': 'never', 'dcc_half': 'off'}
        found = self.tool_ok('find_datasets', folders=[str(folder_a), str(folder_b)])['datasets']
        self.assertEqual(len(found), 2, found)
        suffix = self._testMethodName[-12:]
        job = self.tool_ok('run_autopilot', datasets=[dict(found[0], project='ma_' + suffix), dict(found[1], project='mb_' + suffix)], strategy=strategy)['job_id']
        self.assertEqual(self.wait_job(job)['counts'], {'done': 2})
        plan = self.tool_ok('plan_merge', job_id=job)
        self.assertEqual(len(plan['inputs']), 2, plan)
        self.assertIn('INPUT_FILE', plan['xscale_inp'])
        self.assertTrue(self.tool('plan_merge', job_id=job, friedel='MAYBE')[1])
        merge = self.tool_ok('merge_datasets', job_id=job, reason='test')
        self.assertEqual(sorted(merge['inputs']), sorted(['ma_' + suffix, 'mb_' + suffix]))
        deadline = time.time() + 30
        while time.time() < deadline:
            status = self.tool_ok('job_status', job_id=job)
            if status['merges'][-1]['status'] != 'running':
                break
            time.sleep(0.05)
        self.assertEqual(status['merges'][-1]['status'], 'done', status['merges'])
        # exports land in the project
        project = 'ma_' + suffix
        table = self.tool_ok('export_results', project=project, what='table1')
        self.assertTrue(Path(table['path']).read_text(encoding='utf-8').startswith('Parameter,Value'))
        self.assertIn('Completeness (%)', Path(table['path']).read_text(encoding='utf-8'))
        package = self.tool_ok('export_results', project=project, what='package', params={'reflections': False})
        self.assertTrue(package['path'].endswith('.zip'), package)
        self.assertTrue(self.tool('export_results', project=project, what='nonsense')[1])
        self.assertIn('results', self.tool_ok('search_manual', query='xscale') if (Path(m.__file__).parent.parent / 'docs' / 'manual' / 'CrystalPilot-Manual.index.json').exists() else {'results': []})

    def test_agent_view_frame_says_what_is_wrong(self):
        self.agent_on('read')
        (self.p / 'XDS.INP').unlink()
        self.assertIn('no XDS.INP', self.tool('view_frame', project=self.name)[0])
        (self.p / 'XDS.INP').write_text('JOB= XYCORR\n')
        self.assertIn('names no images', self.tool('view_frame', project=self.name)[0])
        (self.p / 'XDS.INP').write_text('NAME_TEMPLATE_OF_DATA_FRAMES= /no/such/x_????.cbf\n')
        self.assertTrue(self.tool('view_frame', project=self.name, frame=0)[1])
        self.assertTrue(self.tool('view_frame', project=self.name, frame=1)[1])

    # ── trust: undo, approval on the page, the record, the methods text ────
    def allowed(self, tool_name, **arguments):
        """A call that asks the user: the answer given on the page's route, then the same call again."""
        first = self.tool_ok(tool_name, **arguments)
        self.assertEqual(first['status'], 'waiting_for_the_user', first)
        self.assertEqual(self.request('POST', '/api/agent/approvals', {'id': first['approval_id'], 'answer': 'allow'})[0], 200)
        return self.tool_ok(tool_name, **arguments)

    def test_agent_change_to_a_users_project_waits_for_the_user_on_the_page(self):
        self.agent_on('full')
        before = (self.p / 'XDS.INP').read_text()
        ask = {'project': self.name, 'overwrite': True, 'params': {'SIGNAL_PIXEL': 7}, 'reason': 'weak spots'}
        first = self.tool_ok('set_parameters', **ask)
        self.assertEqual(first['status'], 'waiting_for_the_user', first)
        self.assertEqual((self.p / 'XDS.INP').read_text(), before)
        # the page sees the question, with the agent's reason; asking again adds none
        again = self.tool_ok('set_parameters', **ask)
        self.assertEqual(again['approval_id'], first['approval_id'])
        questions = self.request('GET', '/api/agent/approvals')[1]['questions']
        self.assertEqual([q['id'] for q in questions], [first['approval_id']])
        self.assertEqual(questions[0]['reason'], 'weak spots')
        self.assertIn('XDS.INP', questions[0]['doing'])
        # only the page can answer: the agent key opens no such route
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=15)
        conn.request('POST', '/api/agent/approvals', json.dumps({'id': first['approval_id'], 'answer': 'allow'}),
                     {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.AGENT_KEY})
        self.assertEqual(conn.getresponse().status, 403)
        conn.close()
        self.assertEqual(self.request('POST', '/api/agent/approvals', {'id': first['approval_id'], 'answer': 'maybe'})[0], 400)
        self.assertEqual(self.request('POST', '/api/agent/approvals', {'id': 'nonsense', 'answer': 'allow'})[0], 404)
        # refused: nothing changes, and it does not count as an answer for later
        self.assertEqual(self.request('POST', '/api/agent/approvals', {'id': first['approval_id'], 'answer': 'refuse'})[0], 200)
        message, failed = self.tool('set_parameters', **ask)
        self.assertTrue(failed)
        self.assertIn('refused', message)
        self.assertEqual((self.p / 'XDS.INP').read_text(), before)
        # allowed: this one call goes through, the next asks again, and a different call was never allowed
        second = self.tool_ok('set_parameters', **ask)
        self.assertEqual(second['status'], 'waiting_for_the_user')
        self.request('POST', '/api/agent/approvals', {'id': second['approval_id'], 'answer': 'allow'})
        other = self.tool_ok('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 99})
        self.assertEqual(other['status'], 'waiting_for_the_user')
        self.assertIn('SIGNAL_PIXEL= 7', '\n'.join(self.tool_ok('set_parameters', **ask)['changes']))
        self.assertEqual(self.tool_ok('set_parameters', **ask)['status'], 'waiting_for_the_user')
        # a question nobody answers lapses
        with patch.object(m, 'AGENT_APPROVAL_SECONDS', -1):
            self.assertEqual(self.request('GET', '/api/agent/approvals')[1]['questions'], [])
        # the agent's own projects ask nothing, and a run on a user's project is asked about too
        project = self.own_project()
        self.assertTrue(self.tool_ok('set_parameters', project=project, overwrite=True, params={'SIGNAL_PIXEL': 3})['changes'])
        self.assertEqual(self.tool_ok('run_autopilot', datasets=[{'existing_project': self.name}], overwrite=True)['status'], 'waiting_for_the_user')
        with m._AGENT_APPROVAL_LOCK:
            m._AGENT_APPROVALS.clear()

    def test_agent_call_that_asks_the_user_waits_for_the_answer_given_meanwhile(self):
        self.agent_on('full')
        before = (self.p / 'XDS.INP').read_text()

        def answer(choice):
            for _ in range(100):
                questions = self.request('GET', '/api/agent/approvals')[1]['questions']
                if questions:
                    self.request('POST', '/api/agent/approvals', {'id': questions[0]['id'], 'answer': choice})
                    return
                time.sleep(0.05)

        with patch.object(m, 'AGENT_APPROVAL_WAIT', 10):
            # allowed while the call waits: done in this one call
            helper = threading.Thread(target=answer, args=('allow',))
            helper.start()
            t0 = time.time()
            done = self.tool_ok('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 6})
            helper.join(5)
            self.assertLess(time.time() - t0, 8)
            self.assertIn('SIGNAL_PIXEL= 6', '\n'.join(done['changes']))
            # refused while the call waits: refused in this one call
            helper = threading.Thread(target=answer, args=('refuse',))
            helper.start()
            message, failed = self.tool('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 9})
            helper.join(5)
            self.assertTrue(failed)
            self.assertIn('refused', message)
        with patch.object(m, 'AGENT_APPROVAL_WAIT', 1):
            # no answer in time: the call says so and nothing happened
            waiting = self.tool_ok('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 11})
            self.assertEqual(waiting['status'], 'waiting_for_the_user')
        self.assertNotIn('SIGNAL_PIXEL= 9', (self.p / 'XDS.INP').read_text())
        self.assertNotIn('SIGNAL_PIXEL= 11', (self.p / 'XDS.INP').read_text())
        self.assertNotEqual((self.p / 'XDS.INP').read_text(), before)
        with m._AGENT_APPROVAL_LOCK:
            m._AGENT_APPROVALS.clear()

    def test_agent_change_can_be_undone_by_the_agent_and_on_the_page(self):
        self.agent_on('own')
        project = self.own_project()
        path = m._pdir(project) / 'XDS.INP'
        start = path.read_text()
        one = self.tool_ok('set_parameters', project=project, params={'SIGNAL_PIXEL': 6})
        two = self.tool_ok('apply_space_group', project=project, number=19, cell=[78, 80, 37, 90, 90, 90])
        self.assertLess(one['undo'], two['undo'])
        self.assertIsNone(self.tool_ok('set_parameters', project=project, params={'SIGNAL_PIXEL': 6}).get('undo'))
        after_two = path.read_text()
        back = self.tool_ok('revert_change', project=project, change_id=two['undo'], reason='wrong group')
        self.assertEqual(back['file'], 'XDS.INP')
        self.assertEqual(m.xdsinp_values(path.read_text()).get('SIGNAL_PIXEL'), '6')
        self.assertNotIn('SPACE_GROUP_NUMBER', m.xdsinp_values(path.read_text()))
        # a revert can be reverted, and on the page too
        status, undone = self.request('POST', '/api/projects/' + project + '/agent-revert', {'change_id': back['undo'], 'from_page': True})
        self.assertEqual(status, 200, undone)
        self.assertEqual(path.read_text().strip(), after_two.strip())
        status, undone = self.request('POST', '/api/projects/' + project + '/agent-revert', {'change_id': one['undo'], 'from_page': True})
        self.assertEqual(status, 200, undone)
        self.assertEqual(path.read_text().strip(), start.strip())
        entries = self.request('GET', '/api/projects/' + project + '/agent-log')[1]['entries']
        self.assertEqual(entries[0]['client'], 'the page')
        self.assertEqual(entries[0]['tool'], 'revert_change')
        self.assertTrue(entries[0]['change_id'])
        # bad numbers, and a file the agent created goes away again
        self.assertTrue(self.tool('revert_change', project=project, change_id=999)[1])
        self.assertTrue(self.tool('revert_change', project=project, change_id='../x')[1])
        fresh = self.tool_ok('set_parameters', project=project, file='XDSCONV.INP', params={'INPUT_FILE': 'x'})
        self.assertTrue((m._pdir(project) / 'XDSCONV.INP').is_file())
        self.tool_ok('revert_change', project=project, change_id=fresh['undo'])
        self.assertFalse((m._pdir(project) / 'XDSCONV.INP').exists())
        # copies stay out of an export, and an own-level agent can't undo in a user's project
        self.assertFalse(m._export_wanted('0001.saved', True))
        self.assertIn("user's", self.tool('revert_change', project=self.name, change_id=1)[0])
        self.assertEqual(self.request('GET', self.url + '/agent-log')[1]['entries'], [])
        # undoing in a user's project is a change there too, so the page is asked
        self.agent_on('full')
        start = (self.p / 'XDS.INP').read_text()
        change = self.allowed('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 8})
        self.assertNotEqual((self.p / 'XDS.INP').read_text(), start)
        self.allowed('revert_change', project=self.name, change_id=change['undo'])
        self.assertEqual((self.p / 'XDS.INP').read_text().strip(), start.strip())

    def test_an_object_argument_sent_as_json_text_is_read_and_a_wrong_one_is_explained(self):
        self.agent_on('own')
        project = self.own_project()
        changed = self.tool_ok('set_parameters', project=project, params='{"SIGNAL_PIXEL": 7}')
        self.assertIn('SIGNAL_PIXEL= 7', json.dumps(changed))
        message, failed = self.tool('set_parameters', project=project, params='resolution 2.0')
        self.assertTrue(failed)
        self.assertIn('params must be an object', message)
        self.assertIn('INCLUDE_RESOLUTION_RANGE', message)
        self.assertIn('resolution 2.0', message)
        # a keyword whose value is an object is refused before anything is written or asked
        start = self.tool_ok('read_project_file', project=project, file='XDS.INP', limit=500)['text']
        message, failed = self.tool('set_parameters', project=project, params='{"SIGNAL_PIXEL": {"value": 6}}')
        self.assertTrue(failed)
        self.assertIn('not an object', message)
        # a keyword the program does not read is refused, with the nearest real ones
        message, failed = self.tool('set_parameters', project=project, params={'resolution_cutoff': 2.0})
        self.assertTrue(failed)
        self.assertIn('RESOLUTION_CUTOFF is not a keyword XDS reads', message)
        self.assertIn('Use INCLUDE_RESOLUTION_RANGE instead, for example params {"INCLUDE_RESOLUTION_RANGE": "50 2.0"', message)
        self.assertNotIn('failed 2 times', message)
        # the same failing call again is told it will keep failing
        message, failed = self.tool('set_parameters', project=project, params={'resolution_cutoff': 2.0})
        self.assertIn('failed 2 times with the same arguments', message)
        message, failed = self.tool('set_parameters', project=project, params={'NEAR_SIGNAL_PIXL': 2.0})
        self.assertIn('Did you mean', message)
        self.assertNotIn('failed', message)
        message, failed = self.tool('set_parameters', project=project, file='XSCALE.INP', params={'MINIMUM_ZETA': 0.1})
        self.assertTrue(failed)
        self.assertIn('not a keyword XSCALE reads', message)
        self.assertEqual(self.tool_ok('read_project_file', project=project, file='XDS.INP', limit=500)['text'], start)
        # one the user's file already has stays the user's call
        path = m._pdir(project) / 'XDS.INP'
        path.write_text(path.read_text().rstrip('\n') + '\n!LOCAL_EXTRA_KEYWORD= 1\n')
        self.assertIn('LOCAL_EXTRA_KEYWORD= 2', json.dumps(self.tool_ok('set_parameters', project=project, params={'LOCAL_EXTRA_KEYWORD': 2})))

    def test_methods_text_says_only_what_the_project_shows(self):
        self.agent_on('own')
        project = self.own_project()
        self.tool_ok('set_parameters', project=project, params={'EXCLUDE_DATA_RANGE': [[20, 20], [27, 30]], 'X-RAY_WAVELENGTH': '0.9793', 'DETECTOR': 'EIGER', 'DETECTOR_DISTANCE': '197.4'})
        before_run = self.request('GET', '/api/projects/' + project + '/methods')[1]
        self.assertIn('CORRECT has not run', before_run['warnings'][0])
        self.assertNotIn('Overall statistics', before_run['text'])
        self.assertEqual(self.wait_run(self.tool_ok('run_program', project=project, program='xds')['job_id'])['status'], 'completed')
        written = self.request('GET', '/api/projects/' + project + '/methods')[1]
        words = written['text']
        self.assertIn('Frames 20 and 27-30 were excluded.', words)
        self.assertIn('at a wavelength of 0.9793 Å', words)
        self.assertIn('on an EIGER detector at 197.4 mm', words)
        self.assertIn('(Kabsch, 2010)', words)
        self.assertIn('Overall statistics, with the outer shell in parentheses', words)
        self.assertIn('scaled by the CORRECT step', words)
        self.assertIn('AI agent', words)
        self.assertIn('Kabsch, W. (2010). Acta Cryst. D66, 125-132.', written['references'])
        # what did not happen is not claimed
        for absent in ('XSCALE', 'POINTLESS', 'AIMLESS', 'XDSCONV', 'XDSCC12', 'CORRECT step of XDS and', 'Integration was repeated'):
            self.assertNotIn(absent, words, absent)
        self.assertEqual(self.tool_ok('get_analysis', project=project, kind='methods')['text'], words)
        target = self.tool_ok('export_results', project=project, what='methods')
        self.assertTrue(Path(target['path']).read_text(encoding='utf-8').startswith('Diffraction images'))
        # a project no agent touched does not say one did
        self.assert_terminal(self.stream(), 'completed')
        self.assertNotIn('AI agent', self.request('GET', self.url + '/methods')[1]['text'])
        # an agent's change after the user's run, kept or undone, is not how the data were made
        self.agent_on('full')
        change = self.allowed('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 8})
        self.allowed('revert_change', project=self.name, change_id=change['undo'])
        self.assertNotIn('AI agent', self.request('GET', self.url + '/methods')[1]['text'])
        # a change made before the user's next run is said, and the run stays the user's
        self.allowed('set_parameters', project=self.name, overwrite=True, params={'SIGNAL_PIXEL': 8})
        time.sleep(1.2)
        self.assert_terminal(self.stream(), 'completed')
        words = self.request('GET', self.url + '/methods')[1]['text']
        self.assertIn('Input files were changed by an AI agent', words)
        self.assertNotIn('Processing was carried out', words)
        # the file changed after the run: the reader is told
        path = self.p / 'XDS.INP'
        future = time.time() + 60
        os.utime(str(path), (future, future))
        self.assertTrue(any('after the last CORRECT' in w for w in self.request('GET', self.url + '/methods')[1]['warnings']))

    def test_agent_levels_protect_the_users_projects(self):
        self.agent_on('own')
        message, failed = self.tool('run_autopilot', datasets=[{'existing_project': self.name}])
        self.assertTrue(failed)
        self.assertIn("user's", message)
        self.assertTrue(self.tool('run_autopilot', datasets=[{'template': '/no/such/folder/x_????.cbf'}])[1])
        # a project's XDS.INP can be read back, so xdsinp must not be a way to read any file
        secret = self.dataset_folder() / 'secret.txt'
        secret.write_text('not an input file', encoding='utf-8')
        message, failed = self.tool('run_autopilot', datasets=[{'template': str(self.dataset_folder() / 'xtal_????.cbf'), 'xdsinp': str(secret)}])
        self.assertTrue(failed)
        self.assertIn('named XDS.INP', message)
        self.assertTrue(self.tool('run_autopilot', datasets=[{'template': str(self.dataset_folder() / 'xtal_????.cbf')}], strategy={'friedel': 'MAYBE'})[1])
        self.assertTrue(self.tool('run_autopilot', datasets=[{'template': str(self.dataset_folder() / 'xtal_????.cbf')}], strategy={'nonsense': 1})[1])
        with patch.object(m, 'AGENT_LEVEL', 'full'):
            message, failed = self.tool('run_autopilot', datasets=[{'existing_project': self.name}])
            self.assertTrue(failed)
            self.assertIn('overwrite', message)
        self.assertEqual(m.batch_list() and [b for b in m.batch_list() if self.name in b['name']], [])
        self.assertFalse((self.p / m.AGENT_LOG_NAME).exists())

    def test_agent_stops_only_its_own_runs_and_one_run_goes_at_a_time(self):
        self.agent_on('own')
        state = self._batch_with(['xtal_slow_page'])
        (m._pdir(state['items'][0]['project']) / 'control.json').write_text(json.dumps({'XYCORR': 'quiet'}))
        m.batch_start(state['id'])
        deadline = time.time() + 15
        while time.time() < deadline and m.batch_state(state['id'])['items'][0]['status'] != 'running':
            time.sleep(0.05)
        message, failed = self.tool('stop_job', job_id='batch:' + state['id'])
        self.assertTrue(failed)
        self.assertIn('page', message)
        message, failed = self.tool('run_autopilot', datasets=[{'template': str(self.dataset_folder() / 'xtal_????.cbf')}])
        self.assertTrue(failed)
        self.assertIn('one runs at a time', message)
        self.assertTrue(self.tool_ok('job_status', job_id='batch:' + state['id'], wait_seconds=0)['running'])
        with patch.object(m, 'AGENT_LEVEL', 'full'):
            self.assertTrue(self.tool_ok('stop_job', job_id='batch:' + state['id'])['was_running'])
        self.assertEqual(self._batch_wait(state['id'], 30)['items'][0]['status'], 'queued')
        self.assertTrue(self.tool('job_status', job_id='nonsense')[1])

    def test_autopilot_folder_words_live_on_the_server_for_page_and_agent(self):
        self.addCleanup(lambda: m._save_settings(autopilot_keywords=list(m.XDSINP_KEYWORDS_DEFAULT)))
        self.assertEqual(m.autopilot_keywords(), m.XDSINP_KEYWORDS_DEFAULT)
        self.assertEqual(self.request('POST', '/api/config', {'autopilot_keywords': ['  XIA2 ', 'fast_dp', '']})[0], 200)
        config = self.request('GET', '/api/config')[1]
        self.assertEqual(config['autopilot_keywords'], ['xia2', 'fast_dp'])
        self.assertIs(config['prefs_on_server'], True)
        self.agent_on('read')
        self.assertEqual(self.tool_ok('find_datasets', folders=[str(self.dataset_folder())])['keywords'], ['xia2', 'fast_dp'])
        self.assertEqual(self.request('POST', '/api/config', {'autopilot_keywords': []})[0], 200)
        self.assertEqual(m.autopilot_keywords(), [])
        with patch.object(m, 'RESTRICT_BROWSE', True):
            shared = self.request('GET', '/api/config')[1]
            self.assertIs(shared['prefs_on_server'], False)
            self.assertIsNone(shared['autopilot_keywords'])
            self.assertIsNone(shared['cutoff_preference'])
            self.assertIsNone(shared['lib_from_xdsinp'])
            self.assertEqual(self.request('POST', '/api/config', {'cutoff_preference': 'robs', 'lib_from_xdsinp': True})[0], 200)
        self.assertNotEqual(m._load_settings().get('cutoff_preference'), 'robs')

    def test_settings_that_decide_results_live_on_the_server(self):
        self.addCleanup(lambda: m.SETTINGS_FILE.write_text('{}', encoding='utf-8'))
        self.assertEqual(self.request('POST', '/api/config', {'cutoff_preference': 'nonsense', 'lib_from_xdsinp': 'yes'})[0], 200)
        config = self.request('GET', '/api/config')[1]
        self.assertIsNone(config['cutoff_preference'])
        self.assertIsNone(config['lib_from_xdsinp'])
        self.assertEqual(self.request('POST', '/api/config', {'cutoff_preference': 'robs', 'lib_from_xdsinp': False})[0], 200)
        config = self.request('GET', '/api/config')[1]
        self.assertEqual(config['cutoff_preference'], 'robs')
        self.assertIs(config['lib_from_xdsinp'], False)
        # the autofill follows the saved preference unless asked for another
        self.assert_terminal(self.stream(), 'completed')
        saved = self.request('GET', self.url + '/xscale-autofill')[1]
        self.assertEqual(saved['cutoff'], 'robs', saved)
        self.assertEqual(self.request('GET', self.url + '/xscale-autofill?mode=isig')[1]['cutoff'], 'isig')

    def test_page_rules_reach_the_page_and_the_agent_alike(self):
        self.agent_on('read')
        self.assert_terminal(self.stream(), 'completed')
        for step in ('CORRECT', 'IDXREF'):
            page = self.request('GET', self.url + '/metrics/' + step)[1]
            self.assertIsInstance(page['diagnostics'], list)
            self.assertEqual(self.tool_ok('get_diagnostics', project=self.name, step=step)['advice'], page['diagnostics'])
            again = self.request('POST', '/api/rules/diagnostics', {'step': step, 'metrics': page['metrics']})[1]['diagnostics']
            if step == 'CORRECT':
                # from the metrics alone: what AutoPilot acts on comes from the log, after these
                self.assertEqual(again, page['diagnostics'][:len(again)])
                self.assertTrue(any(d['title'].startswith('Ice rings detected') for d in page['diagnostics']))
        self.assertEqual(self.request('POST', '/api/rules/diagnostics', {'step': 'XYCORR', 'metrics': {}})[0], 400)
        autofill = self.request('GET', self.url + '/xscale-autofill?mode=cc50')[1]
        self.assertEqual(self.tool_ok('get_analysis', project=self.name, kind='xscale_autofill', params={'mode': 'cc50'}), autofill)
        table = self.request('GET', self.url + '/table1data')[1]['rows']
        self.assertEqual(table[0], {'section': 'Data Collection'})
        self.assertTrue(any(r.get('value') == 'calculating…' for r in table))
        from_agent = self.tool_ok('get_analysis', project=self.name, kind='table1', detail='full')['rows']
        labels = [r['label'] for r in from_agent if 'label' in r]
        self.assertIn('R-meas (%)', labels)
        self.assertFalse([l for l in labels if '<' in l or '&' in l], labels)
        self.assertFalse(any(r.get('value') == 'calculating…' for r in from_agent))
        self.assertEqual(self.request('GET', '/api/rules/xscale-shells?high=2')[1]['shells'], m.xscale_shells(2.0))
        self.assertEqual(self.request('GET', '/api/rules/xscale-shells?high=x')[0], 400)
        frames = [{'batch': i + 1, 'delta_only': -1.0 if i >= 90 else 0.5} for i in range(100)]
        suggested = self.request('POST', '/api/rules/frame-suggestions', {'data': {'frames': frames, 'summary': {}}, 'strategies': {'outlier2': False}})[1]
        self.assertEqual(suggested['diagnostics']['hasRadDamage'], True, suggested)
        self.assertEqual(self.request('POST', '/api/rules/frame-suggestions', {'data': {}})[0], 400)
        message, failed = self.tool('get_analysis', project=self.name, kind='frame_suggestions')
        self.assertTrue(failed)
        self.assertIn('XDSCC12', message)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Workflows))
    sys.exit(0 if result.wasSuccessful() else 1)
