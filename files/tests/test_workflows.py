"""HTTP-to-process workflow tests using scratch projects and deterministic tools.

The actual handler, job owner, runner, editor, metadata and LP parsers execute.
Only executable discovery/launch is adapted to run the fixture Python program.
These tests verify orchestration, not crystallographic numerical correctness.
"""
import contextlib
import http.client
import json
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
            name = cls.paths.get(str(cmd[0]))
            if name:
                cmd = [sys.executable, str(HERE/'fixtures/workflow_tool.py'), name] + list(cmd[1:])
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
        self.assertEqual(m.xdsinp_values(text)["NAME_TEMPLATE_OF_DATA_FRAMES"], str(self.p / "xtal_imp_????.cbf"))

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


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Workflows))
    sys.exit(0 if result.wasSuccessful() else 1)
