"""Job ownership, cancellation and process lifecycle shared by all runners."""
import contextlib
import functools
import inspect
import time


class DirectoryBusyError(RuntimeError):
    pass


_proc_lock = threading.RLock()
_JOB_LOCAL = threading.local()
_JOBS = {}                 # job id -> ProcessingJob
_PROCS = {}                # id(Popen) -> process registration
_BUSY_DIRS = {}            # canonical path -> (owner, acquisition count)
_current_proc = None       # compatibility for callers inspecting the latest process


class ProcessingJob:
    def __init__(self, project, kind):
        self.id = _secrets.token_hex(12)
        self.project = project
        self.kind = kind
        self.cancelled = threading.Event()
        self.outputs = {}


def _job_stopped():
    job = getattr(_JOB_LOCAL, 'job', None)
    return bool(job and job.cancelled.is_set())


def _jobs_running(project=None, kind=None):
    with _proc_lock:
        return any((project is None or j.project == project) and
                   (kind is None or j.kind == kind) for j in _JOBS.values())


def _current_output_error(path):
    job = getattr(_JOB_LOCAL, 'job', None)
    outcome = job.outputs.get(_directory_key(path), 'ok') if job else 'ok'
    return None if outcome == 'ok' else outcome


def _directory_key(path):
    return os.path.normcase(str(Path(path).resolve()))


def _claim_dir(work_dir):
    key = _directory_key(work_dir)
    owner = getattr(_JOB_LOCAL, 'job', None) or getattr(_JOB_LOCAL, 'reservation', None)
    with _proc_lock:
        previous = _BUSY_DIRS.get(key)
        if previous:
            if owner is None or previous[0] is not owner:
                return False
            _BUSY_DIRS[key] = (owner, previous[1] + 1)
        else:
            _BUSY_DIRS[key] = (owner, 1)
        return True


def _release_dir(work_dir):
    key = _directory_key(work_dir)
    with _proc_lock:
        previous = _BUSY_DIRS.get(key)
        if previous:
            if previous[1] == 1:
                del _BUSY_DIRS[key]
            else:
                _BUSY_DIRS[key] = (previous[0], previous[1] - 1)


@contextlib.contextmanager
def _directory_reservation(paths):
    previous = getattr(_JOB_LOCAL, 'reservation', None)
    if previous is None:
        _JOB_LOCAL.reservation = object()
    claimed = []
    try:
        for path in sorted({_directory_key(p) for p in paths}):
            if not _claim_dir(path):
                raise DirectoryBusyError('another program is already running in ' + path + ' (stop it first)')
            claimed.append(path)
        yield
    finally:
        for path in reversed(claimed):
            _release_dir(path)
        _JOB_LOCAL.reservation = previous


def _processing_job(kind):
    """Reserve every shared directory before a runner changes any files."""
    def decorate(fn):
        signature = inspect.signature(fn)
        @functools.wraps(fn)
        def run(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            project = bound.arguments['project_name']
            project_dir = _pdir(project)
            paths = [project_dir]
            for output_kind in ('xds', 'xscale', 'xdsconv'):
                paths.append(_project_out_dir(project_dir, output_kind))
            for field in ('run_folder', 'work_dir'):
                if bound.arguments.get(field):
                    paths.append(Path(bound.arguments[field]))
            previous = getattr(_JOB_LOCAL, 'job', None)
            job = previous or ProcessingJob(project, kind)
            _JOB_LOCAL.job = job
            if bound.arguments.get('write_fn'):
                original_writer = bound.arguments['write_fn']
                stream_status = ['completed']
                terminal = {'autopilot': 'ap_done', 'autoindex': 'ai_done'}.get(kind, 'done')
                def write_event(event):
                    event_name = event.split('\n', 1)[0].partition(':')[2].strip()
                    if event_name in ('error_msg', 'ap_error'):
                        stream_status[0] = 'error'
                    if event_name in ('step_done', terminal):
                        payload = json.loads(event.split('\ndata: ', 1)[1])
                        status = payload.get('status')
                        if event_name == 'step_done' and status in ('error', 'failed', 'timeout', 'stopped'):
                            stream_status[0] = status
                        if event_name == terminal:
                            payload.setdefault('status', 'stopped' if job.cancelled.is_set() else stream_status[0])
                            event = 'event: ' + terminal + '\ndata: ' + json.dumps(payload) + '\n\n'
                    original_writer(event)
                bound.arguments['write_fn'] = write_event
            try:
                with _directory_reservation(paths):
                    if previous is None:
                        with _proc_lock:
                            _JOBS[job.id] = job
                    return fn(*bound.args, **bound.kwargs)
            except DirectoryBusyError as e:
                writer = bound.arguments.get('write_fn')
                if writer:
                    event = 'ap_error' if kind == 'autopilot' else 'error_msg'
                    done = {'autopilot': 'ap_done', 'autoindex': 'ai_done'}.get(kind, 'done')
                    writer('event: ' + event + '\ndata: ' + json.dumps({'message': str(e)}) + '\n\n')
                    writer('event: ' + done + '\ndata: ' + json.dumps({'status': 'error'}) + '\n\n')
                    return
                result = {'step': bound.arguments.get('step'), 'status': 'error', 'error_message': str(e)}
                return [result] if fn.__name__ == 'run_pipeline' else result
            finally:
                if previous is None:
                    with _proc_lock:
                        _JOBS.pop(job.id, None)
                _JOB_LOCAL.job = previous
        return run
    return decorate


def _set_proc(proc, key=''):
    global _current_proc
    if proc is None:
        raise ValueError('Unregister the specific process with _unset_proc(proc)')
    job = getattr(_JOB_LOCAL, 'job', None)
    registration = {'proc': proc, 'project': job.project if job else key,
                    'job': job, 'cancelled': threading.Event()}
    with _proc_lock:
        _PROCS[id(proc)] = registration
        _current_proc = proc
    return registration


def _unset_proc(proc):
    global _current_proc
    with _proc_lock:
        _PROCS.pop(id(proc), None)
        _current_proc = next((r['proc'] for r in _PROCS.values()), None)


def _kill_proc_tree(proc):
    """Terminate our owned process group even if its parent has exited."""
    if proc is None:
        return
    if os.name == 'nt':
        try:
            result = subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            if result.returncode != 0 and proc.poll() is None:
                proc.kill()
        except Exception:
            if proc.poll() is None:
                proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            proc.poll()  # reap the parent while observing the whole group
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _stop_procs(key=None, kind=None):
    """Cancel matching jobs, including gaps between subprocesses."""
    with _proc_lock:
        jobs = [j for j in _JOBS.values() if (key is None or j.project == key) and (kind is None or j.kind == kind)]
        for job in jobs:
            job.cancelled.set()
        victims = [r for r in _PROCS.values() if (key is None or r['project'] == key) and
                   (kind is None or (r['job'] and r['job'].kind == kind))]
        for registration in victims:
            registration['cancelled'].set()
    running = sum(r['proc'].poll() is None for r in victims)
    # Monitor threads own the kill operation, keeping Stop requests responsive.
    return running


def _kill_all_procs():
    """Kill every registered program and its children now, and wait for them.

    For server shutdown: _stop_procs() only raises the cancel flags and leaves
    the killing to the monitor threads, which are daemons and die with the
    interpreter - the programs run in their own session, so Ctrl+C never
    reaches them and XDS would go on writing into the project.
    """
    _stop_procs()
    with _proc_lock:
        procs = [r['proc'] for r in _PROCS.values()]
    for proc in procs:
        try:
            if proc.poll() is None:
                _kill_proc_tree(proc)
        except Exception:
            pass
    return len(procs)


def _output_stamp(path):
    try:
        st = Path(path).stat()
        return (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    except FileNotFoundError:
        return None


def _xds_expected_outputs(work_dir):
    params = _parse_xdsinp_params(_read_text_lenient(Path(work_dir) / 'XDS.INP'))
    return [step + '.LP' for step in params.get('JOB', '').split() if step in XDS_PIPELINE]


def _run_streaming(cmd, cwd, on_line, timeout=None, env=None, stdin_text=None, stdin_file=None,
                   should_stop=None, key='', register=True, expected_outputs=()):
    """Return (exit code, outcome), checking cancellation and output freshness."""
    if timeout is None:
        timeout = XDS_STEP_TIMEOUT
    job = getattr(_JOB_LOCAL, 'job', None)
    # Capture job cancellation here: the monitor is a different thread.
    outputs = [Path(cwd) / p for p in expected_outputs]
    def result(rc, outcome):
        # Preparation and launch failures also belong to this attempt; otherwise
        # an AutoPilot diagnostic could accept an old LP that could not be moved.
        if job:
            for output in outputs:
                job.outputs[_directory_key(output)] = outcome
        return rc, outcome
    if (job and job.cancelled.is_set()) or (should_stop and should_stop()):
        return result(-1, 'stopped')
    if not _claim_dir(cwd):
        return result(-1, 'error: another program is already running in ' + str(cwd) + ' (stop it first)')
    try:
        stamps = [_output_stamp(p) for p in outputs]
        # Old LPs must not be diagnosed as output of a failed new attempt.
        # Keep them recoverable; the runner's numbered history was rotated first.
        for path in outputs:
            if path.suffix.upper() == '.LP' and path.is_file():
                os.replace(str(path), str(path) + '.previous_attempt')
    except Exception as e:
        _release_dir(cwd)
        return result(-1, 'error: cannot prepare outputs: ' + str(e))
    kw = dict(cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
              text=True, bufsize=1, env=env, errors='replace')
    if os.name != 'nt':
        kw['start_new_session'] = True
    if stdin_file is not None:
        kw['stdin'] = stdin_file
    elif stdin_text is not None:
        kw['stdin'] = subprocess.PIPE
    try:
        proc = subprocess.Popen(cmd, **kw)
    except Exception as e:
        _release_dir(cwd)
        return result(-1, 'error: ' + str(e))
    # Trials remain registered as part of their owning job even when legacy
    # callers ask not to expose a standalone helper in the process registry.
    registration = _set_proc(proc, key) if register or job else None
    state = {'outcome': 'ok'}
    finished = threading.Event()
    started = time.monotonic()
    def monitor():
        while not finished.wait(0.05):
            cancelled = (job and job.cancelled.is_set()) or (registration and registration['cancelled'].is_set())
            try:
                cancelled = cancelled or (should_stop and should_stop())
            except Exception as e:
                state['outcome'] = 'error: ' + str(e)
                _kill_proc_tree(proc)
                return
            if cancelled:
                state['outcome'] = 'stopped'
            elif timeout and timeout > 0 and time.monotonic() - started >= timeout:
                state['outcome'] = 'timeout'
            else:
                continue
            _kill_proc_tree(proc)
            return
    watcher = threading.Thread(target=monitor, daemon=True)
    watcher.start()
    try:
        if stdin_text is not None:
            try:
                proc.stdin.write(stdin_text)
                proc.stdin.close()
            except BrokenPipeError:
                pass
        for line in proc.stdout:
            on_line(line.rstrip('\r\n'))
        proc.wait()
    except Exception as e:
        state['outcome'] = 'error: ' + str(e)
        _kill_proc_tree(proc)
    finally:
        finished.set()
        watcher.join(timeout=12)
        proc.stdout.close()
        if registration:
            _unset_proc(proc)
        _release_dir(cwd)
    rc = proc.returncode if proc.returncode is not None else -1
    if state['outcome'] == 'ok':
        if (job and job.cancelled.is_set()) or (registration and registration['cancelled'].is_set()):
            state['outcome'] = 'stopped'
        elif rc != 0:
            state['outcome'] = 'error: process exited with code ' + str(rc)
        else:
            stale = [str(p) for p, stamp in zip(outputs, stamps) if _output_stamp(p) in (None, stamp)]
            if stale:
                state['outcome'] = 'error: no fresh output: ' + ', '.join(stale)
    if state['outcome'] != 'ok':
        # A failed attempt that wrote nothing must not leave the reader without
        # the last good log: the LP moved aside above comes back where the LP
        # viewer, the metrics and the run history look for it. The attempt
        # itself stays recorded as failed (job.outputs), so a diagnostic still
        # cannot pass the old log off as this run's output. An LP the failed
        # program did write is kept - it carries the error the reader needs.
        for path in outputs:
            previous = Path(str(path) + '.previous_attempt')
            if path.suffix.upper() == '.LP' and not path.exists() and previous.is_file():
                try:
                    os.replace(str(previous), str(path))
                except OSError:
                    pass
    return result(rc, state['outcome'])


def _run_checked(*args, **kwargs):
    """For conversion steps whose callers handle exceptions rather than outcomes."""
    rc, outcome = _run_streaming(*args, **kwargs)
    if outcome != 'ok':
        raise RuntimeError(_outcome_message(outcome, 'Program', kwargs.get('timeout')))
    return rc
