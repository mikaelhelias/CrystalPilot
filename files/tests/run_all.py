#!/usr/bin/env python3
"""CrystalPilot regression battery - run this before every build hand-over.

    py -3 tests/run_all.py                 build newest+1, then all checks
    py -3 tests/run_all.py --no-build      check the newest existing build
    py -3 tests/run_all.py --api           also run the API/e2e suite inside WSL
    py -3 tests/run_all.py --api --real    ... including a real XSCALE run on a
                                           copy of the 'test' project (needs the
                                           reflection file to be reachable)
    py -3 tests/run_all.py --api --real-xds  ... plus the full real chain on a
                                           frame subset: XDS (all steps), XSCALE,
                                           XDSCONV, POINTLESS/AIMLESS/CTRUNCATE
                                           (when CCP4 is set up), gemmi, XDSCC12.
                                           CP_REAL_PROJECT=<name> (default test),
                                           CP_REAL_XDS_RANGE=<frames> (default 60)

Steps: build -> py_compile -> pyflakes (if installed) -> JS syntax of the
frontend -> unit checks -> review regressions -> HTTP workflow tests -> optional
browser checks (--review-ui) and real-program API suite (--api).
Exit code 0 only when everything passed.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = HERE.parent
PY = sys.executable


def run(label, cmd, cwd=FILES, ok_codes=(0,), env=None):
    print("\n== " + label)
    print("   $ " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, env=env)
    out = (r.stdout or "") + (r.stderr or "")
    print("\n".join("   " + l for l in out.rstrip().splitlines()))
    good = r.returncode in ok_codes
    print("   -> " + ("OK" if good else "FAILED (exit %d)" % r.returncode))
    return good, out


def newest_build():
    c = sorted(FILES.glob("xds-gui-v*.py"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))
    return c[-1] if c else None


def main():
    args = set(sys.argv[1:])
    results = []

    # 1. build
    if "--no-build" in args:
        build = newest_build()
        if not build:
            sys.exit("no build found")
        print("== using existing build " + build.name)
    else:
        prev = newest_build()
        n = int(re.search(r"v(\d+)", prev.name).group(1)) + 1 if prev else 1
        build = FILES / ("xds-gui-v%d.py" % n)
        if "--same" in args and prev:
            build = prev
        ok, _ = run("build " + build.name, [PY, "build.py", "--output", build.name])
        results.append(("build", ok))
        if not ok:
            sys.exit(1)

    # 2. compile
    ok, _ = run("py_compile", [PY, "-m", "py_compile", build.name]); results.append(("py_compile", ok))

    # 3. pyflakes (optional tool): only undefined names and syntax count as failures
    try:
        import pyflakes  # noqa: F401
        ok, out = run("pyflakes", [PY, "-m", "pyflakes", build.name], ok_codes=(0, 1))
        bad = [l for l in out.splitlines() if "undefined name" in l or "invalid syntax" in l]
        ok = not bad
        if bad:
            print("   undefined names / syntax:\n" + "\n".join("   " + b for b in bad))
        results.append(("pyflakes", ok))
    except ImportError:
        print("\n== pyflakes: not installed (pip install pyflakes) - skipped")

    # 4. JS syntax of the frontend
    node = shutil.which("node")
    if node:
        ok, out = run("frontend JS syntax", [node, str(HERE / "jscheck.js"), str(FILES / "src" / "frontend.html")])
        ok = ok and "0 with syntax errors" in out
        results.append(("js syntax", ok))
    else:
        print("\n== node not found - JS syntax check skipped")

    # 4b. the Windows installer: the scripts parse, the wizard renders its pages
    if os.name == "nt":
        win = FILES.parent / "windows"
        scripts = ", ".join("'" + str(win / n) + "'" for n in ("wizard.ps1", "launch.ps1", "CrystalPilot-Uninstall.ps1"))
        # (-Command appends any further arguments to the command text, so the list is embedded)
        parse = ("$bad = 0; foreach ($f in @(" + scripts + ")) { $t = $null; $e = $null; "
                 "[void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$t, [ref]$e); "
                 "if ($e) { $bad++; Write-Host ('parse errors in ' + $f); $e | ForEach-Object { Write-Host ('   ' + $_.Message) } } "
                 "else { Write-Host ('ok ' + $f) } }; exit $bad")
        ps = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", parse]
        ok, _ = run("installer scripts parse", ps)
        preview = Path(os.environ.get("TEMP", ".")) / "cp-wizard-preview"
        shutil.rmtree(preview, ignore_errors=True)
        ok2, _ = run("installer wizard renders its pages", ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA", "-File",
                                                              str(win / "wizard.ps1"), "-Preview", str(preview)])
        pages = sorted(p.name for p in preview.glob("wizard_*.png")) if preview.exists() else []
        ok2 = ok2 and len(pages) == 6          # 5 pages + the finish page of a failed installation
        print("   pages: " + ", ".join(pages))
        results.append(("installer", ok and ok2))

    # 5. unit checks against the build
    ok, _ = run("unit checks", [PY, str(HERE / "test_units.py"), str(build)]); results.append(("unit checks", ok))
    ok, _ = run("review regressions", [PY, str(HERE / "test_review_fixes.py"), str(build)])
    results.append(("review regressions", ok))
    ok, _ = run("workflow tests", [PY, str(HERE / "test_workflows.py"), str(build)])
    results.append(("workflow tests", ok))
    if "--review-ui" in args:
        if node:
            ok, _ = run("review browser checks", [node, str(HERE / "ui" / "review_fixes.js")])
        else:
            print("node is required for --review-ui")
            ok = False
        results.append(("review browser checks", ok))

    # 6. API / e2e suite (Linux side)
    if "--api" in args:
        script = HERE / "api" / "api_tests.sh"
        env = dict(os.environ)
        extra = []
        if "--real" in args or "--real-xds" in args:
            env["CP_REAL_XSCALE"] = "1"; extra.append("CP_REAL_XSCALE=1")
        if "--real-xds" in args:
            env["CP_REAL_XDS"] = "1"; extra.append("CP_REAL_XDS=1")
        for k in ("CP_REAL_PROJECT", "CP_REAL_XDS_RANGE"):
            if os.environ.get(k):
                extra.append(k + "=" + os.environ[k])
        ui = "--ui" in args and "--real-xds" in args
        if ui:
            extra.append("CP_KEEP_SERVER=1"); env["CP_KEEP_SERVER"] = "1"
        if os.name == "nt":
            wsl_script = subprocess.run(["wsl.exe", "-e", "wslpath", "-u", str(script)], capture_output=True, text=True).stdout.strip()
            wsl_build = subprocess.run(["wsl.exe", "-e", "wslpath", "-u", str(build)], capture_output=True, text=True).stdout.strip()
            cmd = ["wsl.exe", "-u", "root", "-e", "env", "APP=" + wsl_build] + extra + ["bash", wsl_script]
        else:
            cmd = ["bash", str(script)]
            env["APP"] = str(build)
        if not ui:
            ok, _ = run("API suite", cmd, env=env); results.append(("api suite", ok))
        else:
            # The API suite leaves its last server running (SERVER_READY line) so the
            # browser pass can drive the same project; a stop file ends it.
            print("\n== API suite (keeping the real-chain server for the browser pass)")
            print("   $ " + " ".join(cmd))
            api = subprocess.Popen(cmd, cwd=str(FILES), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, bufsize=1)
            lines, ready = [], None
            for line in api.stdout:
                lines.append(line.rstrip("\n"))
                if line.startswith("SERVER_READY"):
                    ready = dict(kv.split("=", 1) for kv in line.split()[1:])
                    break
            print("\n".join("   " + l for l in lines))
            if ready:
                # the real master file comes from the API suite (the local data set's XDS.INP)
                master = ready.get("master", "")
                fx = FILES / "tests" / "fixtures" / "XDS.INP"
                m = re.search(r"NAME_TEMPLATE_OF_DATA_FRAMES=\s*(\S+)", fx.read_text(errors="replace")) if fx.exists() and not master else None
                if m:
                    tmpl = m.group(1)
                    # <prefix>_??????.h5 -> <prefix>_master.h5 (Eiger naming)
                    master = re.sub(r"_\?+\.h5$", "_master.h5", tmpl) if tmpl.endswith(".h5") else ""
                uenv = dict(os.environ, CP_UI_URL="http://127.0.0.1:" + ready.get("port", "8082"), CP_UI_PROJECT="real", CP_UI_MASTER=master)
                node = shutil.which("node")
                if node:
                    ok_ui, _ = run("browser pass (headless Edge/Chrome)", [node, str(HERE / "ui" / "ui_pass.js")], env=uenv)
                else:
                    print("   node not found - browser pass skipped"); ok_ui = False
                results.append(("browser pass", ok_ui))
                stop_cmd = ["wsl.exe", "-u", "root", "-e", "touch", ready.get("dir", "/tmp/cp_api_d") + "/stop"] if os.name == "nt" else ["touch", ready.get("dir", "/tmp/cp_api_d") + "/stop"]
                subprocess.run(stop_cmd)
            rest = api.stdout.read()
            api.wait()
            print("\n".join("   " + l for l in (rest or "").rstrip().splitlines()))
            ok = api.returncode == 0 and ready is not None
            print("   -> " + ("OK" if ok else "FAILED (exit %s)" % api.returncode))
            results.append(("api suite", ok))

    print("\n==== SUMMARY for " + build.name)
    for name, ok in results:
        print("  %-12s %s" % (name, "ok" if ok else "FAILED"))
    failed = [n for n, ok in results if not ok]
    if failed:
        print("\nNOT READY: " + ", ".join(failed))
        sys.exit(1)
    print("\nREADY: " + build.name)


if __name__ == "__main__":
    main()
