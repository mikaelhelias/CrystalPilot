#!/usr/bin/env python3
"""CrystalPilot regression battery - unit level.

Runs against the assembled single-file build (newest files/xds-gui-v*.py, or
the path given as first argument).  No third-party test framework: each check
is a function; a failure prints the reason and the exit code is non-zero.

    py -3 tests/test_units.py            # newest build
    py -3 tests/test_units.py xds-gui-v342.py

Fixtures in tests/fixtures/ are real files from a processed data set (Eiger,
XDS.INP written by CrystalPilot, LP files, XSCALE.INP written by the old
"Save new" button).  Whenever a bug is found in production, add the file that
triggered it here and a check that fails on the old behaviour.
"""
import atexit
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = HERE.parent
FIX = HERE / "fixtures"


# ── loading the build ────────────────────────────────────────────────────────
def newest_build():
    cands = sorted(FILES.glob("xds-gui-v*.py"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))
    if not cands:
        sys.exit("no xds-gui-v*.py build found in " + str(FILES))
    return cands[-1]


def _remove_scratch(scratch):
    """Delete the scratch folder, also the folders a check made unreadable on purpose."""
    os.chdir(str(Path(__file__).resolve().parent))
    def _unlock(func, p, _exc):
        os.chmod(p, 0o700)
        parent = os.path.dirname(p)
        if parent:
            os.chmod(parent, 0o700)
        func(p)
    shutil.rmtree(str(scratch), onerror=_unlock)


def load_module(path):
    # The module creates ./projects at import unless --projects-dir is present:
    # import it from a scratch folder so the source tree stays clean.
    # on the project's drive (<repo>/.tmp, ignored by git), removed when the checks end
    tmp = Path(os.environ.get("CP_TMP") or Path(__file__).resolve().parents[2] / ".tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="cp_units_", dir=str(tmp)))
    atexit.register(_remove_scratch, scratch)
    os.chdir(scratch)
    os.environ["XDS_GUI_SETTINGS"] = str(scratch / "settings.json")
    os.environ["XDS_GUI_PROJECTS"] = str(scratch / "projects")
    spec = importlib.util.spec_from_file_location("cp", str(path))
    m = importlib.util.module_from_spec(spec)
    sys.argv = ["cp"]
    spec.loader.exec_module(m)
    return m, scratch


# ── tiny runner ──────────────────────────────────────────────────────────────
RESULTS = []


class SkipCheck(Exception):
    """A check that cannot run here (a package this machine does not have)."""


def check(name):
    def deco(fn):
        RESULTS.append((name, fn))
        return fn
    return deco


def fixture(name):
    p = FIX / name
    if not p.exists():
        raise AssertionError("missing fixture " + str(p))
    return p.read_text(encoding="utf-8", errors="replace")


# ── XSCALE layout rules (independent of the app's writer) ────────────────────
XS_OUTPUT_KEYS = {"FRIEDEL'S_LAW", "MERGE", "STRICT_ABSORPTION_CORRECTION"}
XS_INPUT_KEYS = {"INCLUDE_RESOLUTION_RANGE", "CORRECTIONS", "CRYSTAL_NAME", "NBATCH",
                 "STARTING_DOSE", "DOSE_RATE", "EXCLUDE_RESOLUTION_RANGE"}


def xscale_layout_errors(text):
    """XSCALE stops with MISPLACED PARAMETER when a keyword sits in the wrong
    section.  Returns a list of human-readable problems ([] = fine)."""
    problems, section, saw_output, saw_input = [], "global", False, False
    for n, raw in enumerate(text.split("\n"), 1):
        s = raw.strip()
        if not s or s.startswith("!") or "=" not in s:
            continue
        key = s.split("=", 1)[0].strip().upper()
        if key == "OUTPUT_FILE":
            section, saw_output, saw_input = "output", True, False
            continue
        if key == "INPUT_FILE":
            if not saw_output:
                problems.append("line %d: INPUT_FILE before any OUTPUT_FILE" % n)
            section, saw_input = "input", True
            continue
        if key in XS_OUTPUT_KEYS:
            if section == "global":
                problems.append("line %d: %s before OUTPUT_FILE" % (n, key))
        elif key in XS_INPUT_KEYS:
            if not saw_input:
                problems.append("line %d: %s before any INPUT_FILE" % (n, key))
        else:  # global keyword
            if saw_output:
                problems.append("line %d: global keyword %s after OUTPUT_FILE" % (n, key))
    if not saw_output:
        problems.append("no OUTPUT_FILE")
    if not saw_input:
        problems.append("no INPUT_FILE")
    return problems


# ═════════════════════════════════════════════════════════════════════════════
def define_checks(m, scratch):

    # ── XSCALE.INP writer ────────────────────────────────────────────────
    USER_PARAMS = {"SPACE_GROUP_NUMBER": "20", "UNIT_CELL_CONSTANTS": "98.56 119.66 161.55 90 90 90",
                   "INCLUDE_RESOLUTION_RANGE": "80 1.75", "RESOLUTION_SHELLS": "7.09 5.02 4.10 3.56",
                   "STRICT_ABSORPTION_CORRECTION": "FALSE", "OUTPUT_FILE": "merged.ahkl",
                   "FRIEDEL'S_LAW": "TRUE", "MERGE": "FALSE", "INPUT_FILE": ["/data/run1/XDS_ASCII.HKL"]}

    @check("xscale writer: fresh file from the XSCALE-tab form has a valid layout")
    def _():
        out = m._xscale_apply_params("", dict(USER_PARAMS))
        errs = xscale_layout_errors(out)
        assert not errs, errs + [out]
        for k in USER_PARAMS:
            if k != "INPUT_FILE":
                assert re.search(r"^\s*" + re.escape(k) + r"=", out, re.M), "missing " + k + "\n" + out
        assert "INPUT_FILE= /data/run1/XDS_ASCII.HKL" in out

    @check("xscale writer: repairs the file the old 'Save new' button wrote (real fixture)")
    def _():
        broken = fixture("xscale_savenew_broken.INP")
        assert xscale_layout_errors(broken), "fixture should be broken"
        out = m._xscale_apply_params(broken, {"INPUT_FILE": ["/data/run1/XDS_ASCII.HKL"]})
        errs = xscale_layout_errors(out)
        assert not errs, errs + [out]
        assert "RESOLUTION_SHELLS= 7.09" in out and "SPACE_GROUP_NUMBER= 20" in out

    @check("xscale writer: empty INPUT_FILE list keeps existing inputs")
    def _():
        base = m._xscale_apply_params("", dict(USER_PARAMS))
        out = m._xscale_apply_params(base, {"INPUT_FILE": [], "SPACE_GROUP_NUMBER": "19"})
        assert "INPUT_FILE= /data/run1/XDS_ASCII.HKL" in out and "SPACE_GROUP_NUMBER= 19" in out
        assert not xscale_layout_errors(out)

    @check("xscale writer: several inputs, per-input keywords repeated under each")
    def _():
        p = dict(USER_PARAMS); p["INPUT_FILE"] = ["/a/XDS_ASCII.HKL", "/b/XDS_ASCII.HKL"]
        out = m._xscale_apply_params("", p)
        assert out.count("INPUT_FILE=") == 2 and out.count("INCLUDE_RESOLUTION_RANGE= 80 1.75") == 2, out
        assert not xscale_layout_errors(out)

    @check("xscale writer: comments and a second OUTPUT_FILE block survive")
    def _():
        src = "! my note\nSPACE_GROUP_NUMBER= 1\nOUTPUT_FILE= a.ahkl\n  INPUT_FILE= x.HKL\nOUTPUT_FILE= b.ahkl\n  INPUT_FILE= y.HKL\n"
        out = m._xscale_apply_params(src, {"SPACE_GROUP_NUMBER": "5"})
        assert "! my note" in out and "OUTPUT_FILE= b.ahkl" in out and "INPUT_FILE= y.HKL" in out
        assert "SPACE_GROUP_NUMBER= 5" in out and "SPACE_GROUP_NUMBER= 1" not in out

    @check("xscale run pre-check: recognises INPUT_FILE lines the writer produces")
    def _():
        out = m._xscale_apply_params("", dict(USER_PARAMS))
        assert any(m._xscale_key(l) == "INPUT_FILE" and not l.strip().startswith("!") for l in out.split("\n"))

    # ── XDS.INP editor ───────────────────────────────────────────────────
    E = m.XDSINPEditor

    @check("editor: real XDS.INP round trip keeps every keyword")
    def _():
        src = fixture("XDS.INP")
        before = m._parse_xdsinp_params(src)
        out = E.apply_params(src, {"SPACE_GROUP_NUMBER": "20", "DETECTOR_DISTANCE": "200.0"})
        after = m._parse_xdsinp_params(out)
        for k, v in before.items():
            if k not in ("SPACE_GROUP_NUMBER", "DETECTOR_DISTANCE"):
                assert after.get(k) == v, "%s changed: %r -> %r" % (k, v, after.get(k))
        assert after["SPACE_GROUP_NUMBER"] == "20" and after["DETECTOR_DISTANCE"] == "200.0"

    @check("editor: multi-keyword line keeps the other keywords")
    def _():
        out = E.apply_params("NX= 2463 NY= 2527 QX= 0.172 QY= 0.172\nDETECTOR= PILATUS", {"NX": "1000"})
        assert "NX= 1000" in out and "NY= 2527" in out and "QX= 0.172" in out and "QY= 0.172" in out, out
        out = E.apply_params("NX= 2463 NY= 2527 QX= 0.172", {"NY": "9"})
        assert "NX= 2463  NY= 9  QX= 0.172" in out and "\nNY= 9" not in out, out

    @check("editor: comment tail kept, comment-out, uncomment, protected keys, toggles")
    def _():
        assert "DETECTOR_DISTANCE= 250.5  ! from header" in E.apply_params("DETECTOR_DISTANCE= 200.0 ! from header", {"DETECTOR_DISTANCE": "250.5"})
        assert "!SPACE_GROUP_NUMBER= 19" in E.apply_params("SPACE_GROUP_NUMBER= 19", {"SPACE_GROUP_NUMBER": None})
        out = E.apply_params("!SPACE_GROUP_NUMBER= 0", {"SPACE_GROUP_NUMBER": "96"})
        assert "SPACE_GROUP_NUMBER= 96" in out and "!SPACE_GROUP_NUMBER" not in out
        assert "ROTATION_AXIS= -1 0 0" in E.apply_params("ROTATION_AXIS= -1 0 0", {"ROTATION_AXIS": "1 0 0"})
        out = E.apply_params("! set SPACE_GROUP_NUMBER= 0 to let XDS decide\nSPACE_GROUP_NUMBER= 19", {"SPACE_GROUP_NUMBER": "96"})
        assert "! set SPACE_GROUP_NUMBER= 0 to let XDS decide" in out and "SPACE_GROUP_NUMBER= 96" in out and "= 19" not in out
        out = E.apply_params("!SPACE_GROUP_NUMBER= 0\nSPACE_GROUP_NUMBER= 19", {"SPACE_GROUP_NUMBER": "96"})
        assert out == "!SPACE_GROUP_NUMBER= 0\nSPACE_GROUP_NUMBER= 96", out
        out = E.apply_params("EXCLUDE_DATA_RANGE= 1 5\n!EXCLUDE_DATA_RANGE= 7 9\nJOB= ALL", {"EXCLUDE_DATA_RANGE": [[10, 20], [30, 40, True]]})
        assert "EXCLUDE_DATA_RANGE= 10 20" in out and "!EXCLUDE_DATA_RANGE= 30 40" in out and "1 5" not in out
        out = E.apply_params("!UNIT_CELL_CONSTANTS= 0 0 0 0 0 0", {"UNIT_CELL_CONSTANTS": [78.1, 78.1, 37.2, 90, 90, 90]})
        assert "UNIT_CELL_CONSTANTS= 78.1 78.1 37.2 90 90 90" in out and "!UNIT_CELL" not in out
        assert "FRIEDEL'S_LAW= FALSE  STRICT_ABSORPTION_CORRECTION= FALSE" in E.apply_params("FRIEDEL'S_LAW= TRUE  STRICT_ABSORPTION_CORRECTION= FALSE", {"FRIEDEL'S_LAW": "FALSE"})

    @check("editor: list values become space-separated for ANY keyword (never '[1, 10]')")
    def _():
        out = E.apply_params(fixture("XDS.INP"), {"BACKGROUND_RANGE": [1, 10], "DATA_RANGE": [1, 60],
                                                  "SPOT_RANGE": [[1, 60]], "ROTATION_AXIS": [1, 0, 0],
                                                  "INCLUDE_RESOLUTION_RANGE": (50, 1.8), "FRIEDEL'S_LAW": False})
        assert "[" not in out and "]" not in out, out
        p = m._parse_xdsinp_params(out)
        assert p["BACKGROUND_RANGE"] == "1 10" and p["DATA_RANGE"] == "1 60" and p["SPOT_RANGE"] == "1 60"
        assert p["INCLUDE_RESOLUTION_RANGE"] == "50 1.8" and p["FRIEDEL'S_LAW"] == "FALSE"

    @check("xdsinp parser: real XDS.INP gives the expected geometry keys")
    def _():
        p = m._parse_xdsinp_params(fixture("XDS.INP"))
        for k in ("DETECTOR", "NX", "NY", "QX", "ORGX", "DETECTOR_DISTANCE", "X-RAY_WAVELENGTH", "NAME_TEMPLATE_OF_DATA_FRAMES", "DATA_RANGE"):
            assert k in p, "missing " + k
        assert p["DETECTOR"] == "EIGER" and p["NX"] == "4150"

    # ── LP parsers on real output ────────────────────────────────────────
    LP = m.LPParser

    @check("parse_correct: real CORRECT.LP gives cell, space group, statistics")
    def _():
        r = LP.parse_correct(fixture("CORRECT.LP"))
        uc, sg = r.get("unit_cell"), r.get("space_group")
        assert uc and sg, r.keys()
        assert 90 < float(uc["a"]) < 110 and int(sg) == 20, (uc, sg)
        table = r.get("statistics_table") or r.get("resolution_shells") or []
        assert len(table) >= 5, "no statistics table (%d rows)" % len(table)

    @check("parse_idxref: real IDXREF.LP gives lattice candidates and a cell")
    def _():
        r = LP.parse_idxref(fixture("IDXREF.LP"))
        assert r, "empty"
        lat = r.get("lattice_candidates") or r.get("lattices") or r.get("bravais") or []
        assert len(lat) >= 5 or r.get("unit_cell"), list(r.keys())

    @check("parse_integrate / parse_colspot / parse_init: real files parse without error")
    def _():
        assert isinstance(LP.parse_integrate(fixture("INTEGRATE.LP")), dict)
        c = LP.parse_colspot(fixture("COLSPOT.LP")); assert isinstance(c, dict)
        assert isinstance(LP.parse_init(fixture("INIT.LP")), dict)

    @check("parse_xscale: LP with MISPLACED PARAMETER does not crash and reports no table")
    def _():
        r = LP.parse_xscale(fixture("xscale_misplaced.LP"))
        assert isinstance(r, dict)

    @check("matthews: P212121 (19) lysozyme-like cell gives plausible Vm")
    def _():
        res = LP.matthews_coefficient({"a": 79, "b": 79, "c": 38, "alpha": 90, "beta": 90, "gamma": 90}, 19, 14300)
        assert res and 1.5 < res[0]["vm"] < 4.5, res

    @check("determine_resolution_cutoff on the real CORRECT.LP table")
    def _():
        r = LP.parse_correct(fixture("CORRECT.LP"))
        table = r.get("statistics_table") or []
        if table:
            cut = LP.determine_resolution_cutoff(table, "isig2")
            assert cut.get("all_cutoffs"), cut

    @check("cut-offs: one definition - interpolated in 1/d², significance = the '*' of XDS")
    def _():
        # In the fixture I/sigma is 2.14 in the 1.84 A shell and 0.68 in the 1.68 A
        # shell. The old backend answered 1.68 (it kept the whole failing shell)
        # while the page interpolated: AutoPilot and the buttons disagreed.
        r = LP.parse_correct(fixture("CORRECT.LP"))
        cuts = r["cutoffs"]["all_cutoffs"]
        # A shell's value sits in the middle of the shell (in 1/d²), not at its
        # high limit: shells end at 2.05, 1.84 and 1.68 A, so 2.14 belongs to
        # the middle of 2.05-1.84 and 0.68 to the middle of 1.84-1.68.
        e0, e1, e2 = 1 / 2.05 ** 2, 1 / 1.84 ** 2, 1 / 1.68 ** 2
        m1, m2 = (e0 + e1) / 2, (e1 + e2) / 2
        expect = (1 / (m1 + (2.0 - 2.14) / (0.68 - 2.14) * (m2 - m1))) ** 0.5
        assert abs(cuts["isig2"] - expect) < 0.006, (cuts["isig2"], expect)
        assert 1.84 < cuts["isig2"] < 2.05, cuts   # 2.14 is the mean of a shell that ends at 1.84
        assert cuts["cc_half_sig"] == r["recommended_resolution_cutoff"] == 1.68, cuts
        assert r["cutoffs"]["reached"]["isig2"] is True
        # significance is the star, not a percentage: 12.0* is significant, 3.0 is not
        rows = [{"resolution": d, "i_sigma": "9", "r_obs": "5%", "cc_half": c}
                for d, c in (("3.00", "99.0*"), ("2.50", "20.0*"), ("2.20", "12.0*"), ("2.00", "3.0"))]
        assert LP.determine_resolution_cutoff(rows, "cc_half_sig")["resolution"] == 2.20
        # every shell passes: keep all the data and say the criterion was not reached
        good = [{"resolution": d, "i_sigma": "9", "r_obs": "5%", "cc_half": "99.0*"} for d in ("3.00", "2.00")]
        res = LP.determine_resolution_cutoff(good, "isig2")
        assert res["resolution"] == 2.0 and res["reached"]["isig2"] is False, res
        # the page takes the server's numbers instead of trusting its own copy
        html = m.get_frontend_html()
        assert html.count("m.cutoffs.all_cutoffs") >= 2 and "cm.cutoffs.all_cutoffs" in html

    @check("Table 1: true low-resolution limit, mosaicity, and no approximate R-pim")
    def _():
        r = LP.parse_correct(fixture("CORRECT.LP"))
        # the shell table's first row (4.04) is the HIGH limit of the first shell
        assert r["resolution_range_low"] == 19.948 and r["statistics_table"][0]["resolution"] == "4.04"
        assert r["mosaicity"] == 0.135, r.get("mosaicity")
        html = m.get_frontend_html()
        render = html[html.index("function t1Render("):html.index("function _t1Rows(")]
        assert "resolution_range_low" in render and "stats[0].resolution" not in render
        assert "calcRpim" not in html and "Math.sqrt(redund)" not in html, "R-meas/sqrt(N) is back"
        assert "d.rpim" in render
        # without a statistics table nothing is invented
        got = m._table1_rpim_for({"xscale": {}, "correct": {}})
        assert got["overall"] is None and got["reason"]

    def _xds_ascii_header():
        # the 12-item record gemmi expects of an unmerged XDS_ASCII.HKL, P1, 30 x 40 x 50 A
        head = ["!FORMAT=XDS_ASCII    MERGE=FALSE    FRIEDEL'S_LAW=TRUE", "!SPACE_GROUP_NUMBER=1",
                "!UNIT_CELL_CONSTANTS= 30 40 50 90 90 90", "!X-RAY_WAVELENGTH=1",
                "!NUMBER_OF_ITEMS_IN_EACH_DATA_RECORD=12"]
        head += ["!ITEM_%s=%d" % (k, i) for i, k in enumerate(
            ['H', 'K', 'L', 'IOBS', 'SIGMA(IOBS)', 'XD', 'YD', 'ZD', 'RLP', 'PEAK', 'CORR', 'MAXC'], 1)]
        return head + ["!END_OF_HEADER"]

    @check("Table 1: exact R-pim from unmerged reflections, checked against the log")
    def _():
        try:
            import gemmi, numpy  # noqa: F401
        except ImportError:
            raise SkipCheck("gemmi/numpy not installed here")
        d = scratch / "rpim"; d.mkdir(exist_ok=True)
        # P1 cell, three unique reflections measured 2, 3 and 2 times
        obs = [((1, 0, 0), [100.0, 110.0]), ((0, 1, 0), [50.0, 56.0, 53.0]), ((0, 0, 1), [20.0, 24.0])]
        lines = _xds_ascii_header()
        for (h, k, l), values in obs:
            lines += ["%d %d %d %.3f %.3f 1 1 1 1 100 100 0" % (h, k, l, v, 5.0) for v in values]
        lines.append("!END_OF_DATA")
        (d / "XDS_ASCII.HKL").write_text("\n".join(lines) + "\n")
        num = den = num_m = 0.0
        for _hkl, values in obs:
            n, mean = len(values), sum(values) / len(values)
            dev = sum(abs(v - mean) for v in values)
            num += (1.0 / (n - 1)) ** 0.5 * dev; num_m += (n / (n - 1.0)) ** 0.5 * dev; den += sum(values)
        table = [{"resolution": "30.00", "observed": "7", "unique": "3", "r_meas": "%.1f%%" % (100 * num_m / den)},
                 {"resolution": "total", "observed": "7", "unique": "3", "r_meas": "%.1f%%" % (100 * num_m / den)}]
        got = m.table1_rpim(d / "XDS_ASCII.HKL", table)
        assert got["overall"] == "%.1f" % (100 * num / den), (got, 100 * num / den)
        # a log that does not belong to the file: the value is withheld, with the reason
        wrong = [dict(row, r_meas="55.0%") for row in table]
        got = m.table1_rpim(d / "XDS_ASCII.HKL", wrong)
        assert got["overall"] is None and "R-meas" in got["reason"], got

    @check("anisotropy: CC½ pairs observations of the SAME reflection")
    def _():
        try:
            import gemmi, numpy as np  # noqa: F401
        except ImportError:
            raise SkipCheck("gemmi/numpy not installed here")
        d = scratch / "aniso"; d.mkdir(exist_ok=True)
        rng = np.random.RandomState(1)
        lines = _xds_ascii_header()
        for h in range(1, 16):
            for k in range(0, 4):
                for l in range(0, 4):
                    true = float(rng.exponential(1000.0)) + 50.0
                    for _rep in range(4):     # precise repeats: CC½ must be near 100 %
                        lines.append("%d %d %d %.3f %.3f 1 1 1 1 100 100 0" % (h, k, l, true * (1 + 0.01 * rng.randn()), true * 0.01))
        lines.append("!END_OF_DATA")
        (d / "XDS_ASCII.HKL").write_text("\n".join(lines) + "\n")
        res = m.analyze_anisotropy(str(d / "XDS_ASCII.HKL"))
        assert res.get("success"), res
        per = res["per_axis"]
        shells = per["a_star"]["shells"] if isinstance(per.get("a_star"), dict) else per["a_star"]
        ccs = [s["cc_half"] for s in shells if s.get("cc_half") is not None]
        # four repeats with sigma = 1 % of I: merged I/sigma is 100 * sqrt(4) = 200,
        # the I/sigma of a single observation would be 100
        isigs = [s["mean_i_sigma"] for s in shells if s.get("mean_i_sigma") is not None]
        assert isigs and all(190 < v < 210 for v in isigs), isigs
        # the old code correlated unrelated reflections and gave values around zero
        assert ccs and min(ccs) > 90.0, ccs

    # ── helpers ──────────────────────────────────────────────────────────
    @check("_is_xds_reflection_file: .HKL/.ahkl/XDS header yes, mtz no")
    def _():
        d = scratch / "refl"; d.mkdir(exist_ok=True)
        (d / "merged.ahkl").write_text("!FORMAT=XDS_ASCII    MERGE=TRUE\n")
        (d / "x.mtz").write_bytes(b"MTZ \x00\x01")
        (d / "noext").write_text("!FORMAT=XDS_ASCII\n")
        assert m._is_xds_reflection_file(d / "merged.ahkl") and m._is_xds_reflection_file("XDS_ASCII.HKL")
        assert m._is_xds_reflection_file(d / "noext") and not m._is_xds_reflection_file(d / "x.mtz")

    @check("project names: decode at URL boundary only, reject traversal and separators")
    def _():
        assert m._pdir(m._url_project_name("my%20proj")).name == "my proj"
        assert m._pdir("my%20proj").name == "my%20proj"
        for bad in ("..", "a/b", "a\\b", ""):
            try:
                m._pdir(bad)
            except ValueError:
                continue
            raise AssertionError("accepted %r" % bad)

    @check("_h5_find_master: template / chunk / master all resolve to the master")
    def _():
        d = scratch / "h5"; d.mkdir(exist_ok=True)
        (d / "lyso_1_master.h5").write_bytes(b"\x89HDF")
        (d / "lyso_1_data_000001.h5").write_bytes(b"\x89HDF")
        for p in ("lyso_1_master.h5", "lyso_1_data_000001.h5", "lyso_1_??????.h5", "lyso_1_data_??????.h5"):
            assert m._h5_find_master(d / p) == str(d / "lyso_1_master.h5"), p
        assert m._h5_find_master(d / "other_master.h5") is None

    # ── CCP4 detection (CCP4 9 is unpacked wherever the user likes) ──────
    @check("CCP4: found through $CCP4 / $CBIN, and without f2mtz")
    def _():
        root = scratch / "ccp4root" / "ccp4-9.0"
        (root / "bin").mkdir(parents=True, exist_ok=True)
        for n in ("pointless", "aimless", "ctruncate", "cad"):     # no f2mtz
            (root / "bin" / n).write_text("", encoding="utf-8")
        assert m._is_ccp4_bin(root / "bin")
        assert not m._is_ccp4_bin(root)
        keep = {k: os.environ.get(k) for k in ("PATH", "CCP4", "CBIN", "CCP4_MASTER", "CCP4_BIN")}
        try:
            os.environ["PATH"] = str(scratch / "nothing-here")     # no CCP4 on PATH
            for k in ("CCP4", "CBIN", "CCP4_MASTER", "CCP4_BIN"):
                os.environ.pop(k, None)
            os.environ["CCP4"] = str(root)
            assert m._find_ccp4_bin() == str(root / "bin"), "via $CCP4"
            os.environ.pop("CCP4")
            os.environ["CBIN"] = str(root / "bin")
            assert m._find_ccp4_bin() == str(root / "bin"), "via $CBIN"
            os.environ.pop("CBIN")
            # $CCP4_MASTER points at the folder that holds ccp4-9.0
            os.environ["CCP4_MASTER"] = str(root.parent)
            assert m._find_ccp4_bin() == str(root / "bin"), "via $CCP4_MASTER"
        finally:
            for k, v in keep.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    # ── what the user types into a path field ────────────────────────────
    @check("path settings: blanks, quotes, ~ and a folder all give a usable path")
    def _():
        d = scratch / "cleanpath"; d.mkdir(exist_ok=True)
        so = d / "dectris-neggia.so"
        so.write_bytes(b"\x7fELF")
        names = ("dectris-neggia.so", "dectris-neggia.dylib")
        assert m._clean_path_setting(str(so) + "  ", names) == str(so), "trailing blank"
        assert m._clean_path_setting('"' + str(so) + '"', names) == str(so), "quoted"
        assert m._clean_path_setting(str(d), names) == str(so), "folder instead of file"
        assert m._clean_path_setting("", names) == "", "empty stays empty"
        assert m._clean_path_setting(None, names) == "", "None stays empty"
        assert m._clean_path_setting("~/x.so", names) == str(Path.home() / "x.so"), "~ expanded"
        # a path that does not exist is returned as given (the caller refuses it)
        assert m._clean_path_setting("/no/such/file.so", names) == str(Path("/no/such/file.so"))

    # ── HDF5 preflight: can XDS reach the frames it is about to read? ────
    def _pre_inp(folder, template, lib="auto"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "neggia.so").write_bytes(b"\x7fELF")
        if lib == "auto":
            lib = "LIB= %s\n" % (folder / "neggia.so")
        inp = folder / "XDS.INP"
        inp.write_text("JOB= XYCORR\nNAME_TEMPLATE_OF_DATA_FRAMES= %s\n%sDATA_RANGE= 1 100\n"
                       % (template, lib), encoding="utf-8")
        return inp

    @check("h5 preflight: CBF data is not an HDF5 problem - stays quiet")
    def _():
        d = scratch / "pre_cbf"
        assert m._check_h5_frames(_pre_inp(d, str(d / "img_?????.cbf"))) == (False, [])

    @check("h5 preflight: the master XDS would open is missing -> fatal, and it is named")
    def _():
        d = scratch / "pre_nomaster"
        fatal, lines = m._check_h5_frames(_pre_inp(d, str(d / "lyso_??????.h5")))
        assert fatal and any("lyso_master.h5" in l for l in lines), lines

    @check("h5 preflight: HDF5 without LIB= is fatal; two LIB= lines are flagged")
    def _():
        d = scratch / "pre_lib"
        fatal, lines = m._check_h5_frames(_pre_inp(d, str(d / "lyso_??????.h5"), lib=""))
        assert fatal and any("LIB=" in l for l in lines), lines
        d2 = scratch / "pre_lib2"
        so = d2 / "neggia.so"
        inp2 = _pre_inp(d2, str(d2 / "lyso_??????.h5"), lib="LIB= %s\nLIB= %s\n" % (so, so))
        assert any("LIB= lines" in l for l in m._check_h5_frames(inp2)[1])

    @check("h5 preflight: a template naming one file is refused (XDS: INVALID NAME_TEMPLATE)")
    def _():
        d = scratch / "pre_nowild"
        for name, want in (("lyso_master.h5", "lyso_??????.h5"),
                           ("lyso_data_000001.h5", "lyso_??????.h5")):
            inp = _pre_inp(d, str(d / name))
            (d / name).write_bytes(bytes([0x89]) + b"HDF")
            fatal, lines = m._check_h5_frames(inp)
            assert fatal, name
            assert any("NAME_TEMPLATE_OF_DATA_FRAMES names one file" in l for l in lines), lines
            assert any(want in l for l in lines), (name, lines)

    @check("h5 preflight: a _data_?????? template is explained (XDS looks for _data_master)")
    def _():
        d = scratch / "pre_datawild"
        inp = _pre_inp(d, str(d / "lyso_data_??????.h5"))
        fatal, lines = m._check_h5_frames(inp)
        assert fatal and any("_data_" in l and "without _data" in l for l in lines), lines

    @check("h5 preflight: master with missing data files -> fatal; complete set -> quiet")
    def _():
        try:
            import h5py, numpy as np
        except Exception:
            return          # no h5py on this interpreter - the WSL suite covers it
        d = scratch / "pre_links"
        inp = _pre_inp(d, str(d / "lyso_??????.h5"))
        with h5py.File(d / "lyso_master.h5", "w") as f:
            g = f.create_group("entry/data")
            for n in (1, 2):
                g["data_%06d" % n] = h5py.ExternalLink("lyso_data_%06d.h5" % n, "/entry/data/data")
        fatal, lines = m._check_h5_frames(inp)
        assert fatal and any("lyso_data_000001.h5" in l for l in lines), lines
        for n in (1, 2):
            with h5py.File(d / ("lyso_data_%06d.h5" % n), "w") as f:
                f.create_dataset("entry/data/data", data=np.zeros((50, 4, 4), dtype="uint16"))
        assert m._check_h5_frames(inp) == (False, [])

    @check("XDSINPGenerator: Eiger header gives EIGER, LIB line, ranges, no misplaced keys")
    def _():
        hdr = {"nx": "4150", "ny": "4371", "x_pixel_size": "0.075", "y_pixel_size": "0.075", "wavelength": "0.9793",
               "detector_distance": "197.44", "beam_center_x": "2008.9", "beam_center_y": "2253.1", "osc_range": "0.1",
               "osc_start": "0", "nframes": "3600", "detector_name": "Dectris EIGER2 Si 16M", "overload": "29991", "sensor_thickness": "0.45"}
        txt, warns = m.XDSINPGenerator.generate("/data/x_??????.h5", hdr, lib_path="/opt/neggia.so")
        p = m._parse_xdsinp_params(txt)
        assert p["DETECTOR"] == "EIGER" and p["OVERLOAD"] == "29991" and p["LIB"] == "/opt/neggia.so"
        assert p["DATA_RANGE"] == "1 3600" and p["X-RAY_WAVELENGTH"] == "0.9793"

    @check("_run_streaming: runs a command, streams lines, reports ok; timeout kills")
    def _():
        lines = []
        if os.name == "nt":
            rc, outcome = m._run_streaming(["cmd", "/c", "echo one&& echo two"], scratch, lines.append, timeout=20, register=False)
        else:
            rc, outcome = m._run_streaming(["sh", "-c", "echo one; echo two"], scratch, lines.append, timeout=20, register=False)
        assert rc == 0 and outcome == "ok" and lines == ["one", "two"], (rc, outcome, lines)
        t0 = time.time()
        slow = ["cmd", "/c", "ping -n 30 127.0.0.1 >nul"] if os.name == "nt" else ["sh", "-c", "sleep 30"]
        rc, outcome = m._run_streaming(slow, scratch, lambda t: None, timeout=2, register=False)
        assert outcome == "timeout" and time.time() - t0 < 15, (rc, outcome)

    @check("_run_streaming: refuses a second program in the same folder")
    def _():
        import threading
        d = scratch / "busy"; d.mkdir(exist_ok=True)
        slow = ["cmd", "/c", "ping -n 4 127.0.0.1 >nul"] if os.name == "nt" else ["sh", "-c", "sleep 3"]
        res = {}
        th = threading.Thread(target=lambda: res.setdefault("a", m._run_streaming(slow, d, lambda t: None, timeout=20, register=False)))
        th.start(); time.sleep(0.7)
        rc, outcome = m._run_streaming(["cmd", "/c", "echo x"] if os.name == "nt" else ["sh", "-c", "echo x"], d, lambda t: None, timeout=5, register=False)
        th.join()
        assert "already running" in outcome, outcome
        assert res["a"][1] == "ok"

    @check("ProjectManager: create / update under lock / corrupt metadata skipped / delete")
    def _():
        m.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        m.ProjectManager.create("unit proj", "d", "")
        m.ProjectManager.update("unit proj", {"last_run_folder": "/x"})
        assert m.ProjectManager.get("unit proj")["last_run_folder"] == "/x"
        (m.PROJECTS_DIR / "broken").mkdir(exist_ok=True)
        (m.PROJECTS_DIR / "broken" / "metadata.json").write_text("{ not json")
        names = [p["name"] for p in m.ProjectManager.list_all()]
        assert "unit proj" in names and "broken" not in names, names
        m.ProjectManager.delete("unit proj", delete_files=True)
        assert not (m.PROJECTS_DIR / "unit proj").exists()

    @check("config: version, localhost default, token, step timeout, assets")
    def _():
        assert re.match(r"^\d+\.\d+\.\d+[a-z]?$", m.VERSION), m.VERSION   # 0.6.6, and 0.6.6b for a follow-up build
        assert m.HOST == "127.0.0.1" and len(m.API_TOKEN) >= 20 and m.XDS_STEP_TIMEOUT > 0
        assert set(m.STATIC_ASSETS) >= {"logo.png", "logo.jpg", "diffraction_bg.jpg", "splash.jpg"}
        # the header logo is the CrystalPilot PNG; logo.jpg is its alias
        assert m.STATIC_ASSETS["logo.png"][1][:8] == b"\x89PNG\r\n\x1a\n"
        assert m.STATIC_ASSETS["logo.jpg"][1] == m.STATIC_ASSETS["logo.png"][1]
        assert all(len(v[1]) > 10000 for v in m.STATIC_ASSETS.values())

    # ── parsers on outputs harvested by the real chain (tests/fixtures/real) ─
    REAL = FIX / "real"

    def real(name):
        p = REAL / name
        if not p.exists():
            raise AssertionError("missing harvested fixture %s - run 'py -3 tests/run_all.py --api --real-xds' once to collect it" % p)
        return p.read_text(encoding="utf-8", errors="replace")

    @check("real outputs: parse_pointless finds a space group in the harvested pointless.log")
    def _():
        r = LP.parse_pointless(real("pointless.log"))
        assert isinstance(r, dict) and (r.get("best_solution") or r.get("space_group") or r.get("sg_number") or r.get("solutions")), list(r.keys())

    @check("real outputs: AIMLESS and CTRUNCATE logs parse to statistics")
    def _():
        a = m._parse_aimless_log(real("aimless.log"))
        assert isinstance(a, dict) and a, "empty aimless parse"
        txt = json.dumps(a)
        assert re.search(r"[Rr]meas|[Rr]_?merge|CC|completeness|resolution", txt), txt[:300]
        c = m._parse_ctruncate_log(real("ctruncate.log"))
        assert isinstance(c, dict), type(c)

    @check("real outputs: parse_xscale on the harvested XSCALE.LP gives a statistics table")
    def _():
        r = LP.parse_xscale(real("XSCALE.LP"))
        table = r.get("statistics_table") or r.get("shells") or []
        assert len(table) >= 3, list(r.keys())

    @check("real outputs: CORRECT.LP (subset run) parses to cell + table; XDSCONV.LP mentions the output")
    def _():
        r = LP.parse_correct(real("CORRECT.LP"))
        assert r.get("unit_cell") and (r.get("statistics_table") or r.get("resolution_shells")), list(r.keys())
        assert "XDSCONV" in real("XDSCONV.LP")

    @check("real outputs: XSCALE.INP written by the app has a valid layout")
    def _():
        errs = xscale_layout_errors(real("XSCALE.INP"))
        assert not errs, errs

    # ── every server route is exercised by some test ─────────────────────
    @check("route inventory: endpoint names are mentioned in the test sources (not execution coverage)")
    def _():
        src = Path(m.__file__).read_text(encoding="utf-8", errors="replace")
        routes = set(re.findall(r'path == "(/[^"]+)"', src))
        routes |= set(re.findall(r'path\.endswith\("(/[^"]+)"\)', src))
        routes |= set(re.findall(r'"(/[a-z0-9_-]+(?:/[a-z0-9_-]+)*)" in path', src))
        skip = {"/", "/index.html", "/favicon.ico", "/assets/", "/api/deps/install", "/api/gemmi/install", "/api/xdscc12/download"}
        tests_text = ""
        for p in [HERE / "api" / "api_tests.sh", HERE / "api" / "sweep.sh", HERE / "ui" / "ui_pass.js", HERE / "test_units.py"]:
            if p.exists():
                tests_text += p.read_text(encoding="utf-8", errors="replace")
        missing = sorted(r for r in routes if r not in skip and r.strip("/").split("/")[-1] not in tests_text)
        assert not missing, "routes without a test: " + ", ".join(missing)

    @check("frontend: served page contains no calls to undefined onclick handlers")
    def _():
        html = m.get_frontend_html()
        calls = set(re.findall(r'on[a-z]+="([A-Za-z_$][A-Za-z0-9_$]*)\(', html))
        defs = set(re.findall(r'function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(', html))
        defs |= set(re.findall(r'(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?(?:function|\()', html))
        missing = sorted(c for c in calls - defs if c not in ("if",))
        assert not missing, missing
        ids = re.findall(r' id="([A-Za-z0-9_-]+)"', html)
        dups = sorted({i for i in ids if ids.count(i) > 1})
        assert not dups, "duplicate element ids: " + ", ".join(dups)

    @check("batch strategy: the defaults are AutoPilot's own, and the choices map onto it")
    def _():
        s = m.normalize_strategy({})
        k = m.strategy_autopilot_kwargs(s)
        # with no choices made, a batch processes exactly as the AutoPilot tab does
        assert k["criterion"] == "isig2" and k["friedel"] == "TRUE", k
        assert k["optimize"] is True and k["dcc_half"] is True and k["exclude_ice"] is True, k
        assert k["autoindex_tier"] == "medium" and "space_group" not in k and "resolution_range" not in k, k
        assert m.strategy_autopilot_kwargs({"optimize": "never"})["optimize"] is False
        assert m.strategy_autopilot_kwargs({"optimize": "if_better"})["optimize"] == "if_better"
        fixed = m.strategy_autopilot_kwargs({"sg_mode": "fixed", "space_group": "19", "unit_cell": "78.1, 78.1 37.2 90 90 90"})
        assert fixed["space_group"] == "19" and fixed["unit_cell"] == "78.1 78.1 37.2 90 90 90", fixed
        # a high limit alone does not cut low-resolution data (999, not 50 A)
        assert m.strategy_autopilot_kwargs({"res_high": "2.1"})["resolution_range"] == (999.0, 2.1)
        for bad in ({"sg_mode": "fixed", "space_group": "999"}, {"sg_mode": "fixed", "space_group": "19", "unit_cell": "1 2 3"},
                    {"sg_mode": "fixed", "space_group": "19"},                  # XDS needs the cell with the space group
                    {"res_high": "-1"}):
            try:
                m.normalize_strategy(bad)
                raise AssertionError("accepted: %r" % bad)
            except ValueError:
                pass
        # an unknown value falls back to the default rather than reaching AutoPilot
        assert m.normalize_strategy({"autoindex_tier": "everything"})["autoindex_tier"] == "medium"
        for name, preset in m.STRATEGY_PRESETS.items():
            m.strategy_autopilot_kwargs(preset)             # every preset is a valid strategy
        assert m.strategy_autopilot_kwargs(m.STRATEGY_PRESETS["Quick screening"])["optimize"] is False

    @check("batch discovery: Eiger masters and frame series, not stray images or our own folders")
    def _():
        root = scratch / "campaign"
        (root / "xtal1").mkdir(parents=True)
        (root / "xtal1" / "lyso_1_master.h5").write_bytes(b"")
        (root / "xtal1" / "lyso_1_data_000001.h5").write_bytes(b"")
        (root / "xtal2").mkdir()
        for n in range(1, 8):
            (root / "xtal2" / ("thau_01_%04d.cbf" % n)).write_bytes(b"")
        for n in range(1, 4):                                    # three test shots: not a data set
            (root / "xtal2" / ("test_%04d.cbf" % n)).write_bytes(b"")
        (root / "batches" / "old").mkdir(parents=True)          # CrystalPilot's own output
        for n in range(1, 8):
            (root / "batches" / "old" / ("x_%04d.cbf" % n)).write_bytes(b"")
        deep = root / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "far_master.h5").write_bytes(b"")
        found = m.discover_datasets(root, max_depth=3)
        labels = sorted(d["label"] for d in found)
        assert labels == ["lyso_1", "thau_01"], found
        series = [d for d in found if d["kind"] == "series"][0]
        assert series["frames"] == 7 and series["template"].endswith("thau_01_????.cbf"), series
        eiger = [d for d in found if d["kind"] == "eiger"][0]
        assert eiger["template"].endswith("lyso_1_master.h5"), eiger
        assert m._batch_project_name("thau 01/x", set()) == "thau_01_x"
        assert not series["raster"] and not eiger["raster"], found

    @check("AutoPilot discovery: raster scans are flagged (rasterImages folder or 'raster' in the name), rotation data not")
    def _():
        root = scratch / "visit"
        crystal = root / "xtal_7" / "1" / "puck_7"
        (crystal / "rasterImages").mkdir(parents=True)
        (crystal / "xtal_7_3703_master.h5").write_bytes(b"")                                    # the rotation data set
        (crystal / "rasterImages" / "xtal_7_r_Raster_3702_master.h5").write_bytes(b"")          # FMX raster scan
        (root / "xtal_7" / "0" / "puck_7" / "rasterImages").mkdir(parents=True)
        (root / "xtal_7" / "0" / "puck_7" / "rasterImages" / "xtal_7_r_Raster_3701_master.h5").write_bytes(b"")
        (root / "grid").mkdir()
        for n in range(1, 8):
            (root / "grid" / ("xtal_raster_%04d.cbf" % n)).write_bytes(b"")                   # a raster series by its name
            (root / "grid" / ("xtal_rot_%04d.cbf" % n)).write_bytes(b"")
        found = {Path(d["template"]).name: d["raster"] for d in m.discover_datasets(root, max_depth=5)}
        assert found == {"xtal_7_3703_master.h5": False, "xtal_7_r_Raster_3702_master.h5": True,
                         "xtal_7_r_Raster_3701_master.h5": True, "xtal_raster_????.cbf": True, "xtal_rot_????.cbf": False}, found
        html = m.get_frontend_html()
        assert "ds.picked = !ds.raster" in html, "raster scans are not left unticked in the wizard"
        assert 'apw-badge raster' in html

    @check("AutoPilot XDS.INP search: name + header match, folder path, then keyword order, then newest")
    def _():
        from unittest.mock import patch
        base = scratch / "beamline"
        def frames(folder, prefix, n=10):
            folder.mkdir(parents=True, exist_ok=True)
            for i in range(1, n + 1):
                (folder / ("%s_%04d.cbf" % (prefix, i))).write_bytes(b"")
        frames(base / "raw" / "sample" / "xtal1", "thau_1")
        frames(base / "raw" / "sample" / "xtal2", "thau_1")          # same file names, another crystal
        def inp(rel, template, extra="", age=0):
            p = base / "processed" / rel / "XDS.INP"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("JOB= XYCORR INIT\nNAME_TEMPLATE_OF_DATA_FRAMES= %s\n"
                         "X-RAY_WAVELENGTH= 0.9763  DETECTOR_DISTANCE= 250.0\nOSCILLATION_RANGE= 0.1\n%s" % (template, extra), encoding="utf-8")
            t = 1_700_000_000 - age
            os.utime(p, (t, t))
            return str(p.resolve())
        remote = "/data/visitor/mx1/raw/sample/%s/thau_1_????.cbf"
        fast = inp("sample/xtal1/fast_dp_2", remote % "xtal1", "ORGX= 1200 ORGY= 1300\nSPACE_GROUP_NUMBER= 19\n", age=100)
        auto = inp("sample/xtal1/autoPROC.run1", remote % "xtal1", "ORGX= 1210 ORGY= 1300\n", age=0)
        other = inp("sample/xtal2/fast_dp", remote % "xtal2", "ORGX= 1200 ORGY= 1300\n")
        wrong = inp("sample/xtal1/old", remote % "xtal1", "X-RAY_WAVELENGTH= 1.5418\n")
        inp("sample/xtal1/fast_dp_2/lyso", "/x/lyso_1_????.cbf")        # another data set entirely
        datasets = m.discover_datasets(base / "raw", max_depth=3)
        assert len(datasets) == 2, datasets
        header = {"wavelength": "0.9763", "detector_distance": "250.0", "osc_range": "0.1"}
        with patch.object(m, "_dataset_header", return_value=header):
            out = m.find_xdsinp_candidates(datasets, [str(base / "processed")], ["fast_dp", "processing", "autoproc"])
        by_folder = {Path(r["template"]).parent.name: r for r in out["results"]}
        x1 = by_folder["xtal1"]
        assert x1["state"] == "imported" and x1["choice"] == fast, x1
        assert [c["path"] for c in x1["candidates"]][:2] == [fast, auto], x1["candidates"]
        assert x1["candidates"][0]["keyword"] == "fast_dp" and x1["candidates"][0]["space_group"] == "19"
        assert [c["path"] for c in x1["rejected"]] == [wrong] and "wavelength" in x1["rejected"][0]["reason"], x1["rejected"]
        assert by_folder["xtal2"]["choice"] == other, by_folder["xtal2"]
        # a CrystalPilot project's own XDS.INP (local image path, earlier fixes) is never a candidate
        proj = base / "processed" / "sample" / "xtal1" / "cp_project"
        proj.mkdir(parents=True)
        (proj / "metadata.json").write_text('{"name": "cp_project", "completed_steps": []}', encoding="utf-8")
        (proj / "XDS.INP").write_text("NAME_TEMPLATE_OF_DATA_FRAMES= %s\n" % str(base / "raw" / "sample" / "xtal1" / "thau_1_????.cbf"), encoding="utf-8")
        with patch.object(m, "_dataset_header", return_value=header):
            again = m.find_xdsinp_candidates(datasets, [str(base / "processed")], ["fast_dp", "processing", "autoproc"])
        x1again = [r for r in again["results"] if Path(r["template"]).parent.name == "xtal1"][0]
        assert x1again["choice"] == fast and all("cp_project" not in c["path"] for c in x1again["candidates"]), x1again["candidates"]
        import shutil as _sh
        _sh.rmtree(str(proj))
        # a keyword later in the list loses to an earlier one; with no keyword difference the newest wins
        with patch.object(m, "_dataset_header", return_value={}):
            flipped = m.find_xdsinp_candidates(datasets, [str(base / "processed")], ["autoproc", "fast_dp"])
        x1 = [r for r in flipped["results"] if Path(r["template"]).parent.name == "xtal1"][0]
        assert x1["choice"] == auto, x1
        # without header numbers the wavelength cannot reject anything
        assert wrong in [c["path"] for c in x1["candidates"]], x1
        # equally good files that disagree on geometry: the user picks
        p1 = inp("sample/xtal1/processing_a", remote % "xtal1", "ORGX= 1100\n", age=5)
        p2 = inp("sample/xtal1/processing_b", remote % "xtal1", "ORGX= 1300\n", age=6)
        with patch.object(m, "_dataset_header", return_value=header):
            picked = m.find_xdsinp_candidates(datasets[:1] if Path(datasets[0]["template"]).parent.name == "xtal1" else datasets[1:],
                                              [str(base / "processed")], ["processing"])
        r = picked["results"][0]
        assert r["state"] == "pick" and r["choice"] == p1, (r["state"], r["choice"], [c["path"] for c in r["candidates"]])
        assert m._template_key("/a/x_master.h5") == m._template_key("x_??????.h5") == m._template_key("x_data_000001.h5") == "x.h5"
        assert m._template_key("/b/thau_1_????.cbf") == m._template_key("thau_1_0001.cbf") == "thau_1_#.cbf"
        # a run number or temperature in the prefix keeps two runs apart
        assert m._template_key("lyso_001_????.cbf") != m._template_key("lyso_002_????.cbf")
        assert m._template_key("prot_100K_????.cbf") == m._template_key("prot_100K_00001.cbf") != m._template_key("prot_290K_????.cbf")
        with patch.object(m, "IS_WSL", True), patch.dict(os.environ, {"CRYSTALPILOT_DRIVE": ""}):
            assert m.batch_local_path("Z:\\DATA\\run 1") == "/mnt/z/DATA/run 1"
            assert m.batch_local_path("file:///Z:/DATA/run%201") == "/mnt/z/DATA/run 1"
        assert m.batch_local_path("file:///home/me/data") == "/home/me/data"

    @check("AutoPilot: an image folder with blanks is reached through a link XDS can read")
    def _():
        folder = scratch / "First Last" / "xtal 1"
        folder.mkdir(parents=True)
        m.ProjectManager.create("blanks_proj", "", "")
        assert m.batch_xds_safe_template("blanks_proj", "/data/x_????.cbf") == "/data/x_????.cbf"
        try:
            m.ProjectManager.create("blanks_probe", "", "")
            os.symlink(str(folder), str(m._pdir("blanks_probe") / "probe"))
        except (OSError, NotImplementedError):
            raise SkipCheck("this Windows account may not create symbolic links")
        tmpl = str(folder).replace("\\", "/") + "/x_????.cbf"
        safe = m.batch_xds_safe_template("blanks_proj", tmpl)
        assert " " not in safe and safe.endswith("frames/x_????.cbf"), safe
        assert os.path.realpath(str(m._pdir("blanks_proj") / "frames")) == os.path.realpath(str(folder))
        assert m.batch_xds_safe_template("blanks_proj", tmpl) == safe                  # the same link again
        try:
            m.batch_xds_safe_template("blanks_proj", "/data/my frame_????.cbf")
            raise AssertionError("a blank in the file name was accepted")
        except ValueError as exc:
            assert "file names" in str(exc)

    @check("AutoPilot drag and drop: a dropped folder is found by its name and its files, not by name alone")
    def _():
        base = scratch / "dropzone"
        for where in ("trip1/xtal1", "trip2/xtal1"):
            (base / where).mkdir(parents=True)
        (base / "trip1" / "xtal1" / "a_0001.cbf").write_bytes(b"x" * 10)
        (base / "trip2" / "xtal1" / "a_0001.cbf").write_bytes(b"x" * 99)          # same name, other data
        files = [{"name": "a_0001.cbf", "size": 10}]
        found, complete = m.locate_dropped_folder("xtal1", files, [str(base)])
        assert found == [str((base / "trip1" / "xtal1").resolve())] and complete, found
        found, _ = m.locate_dropped_folder("xtal1", [{"name": "a_0001.cbf", "size": 5}], [str(base)], base.resolve())
        assert found == [], found
        assert m.locate_dropped_folder("", files, [str(base)]) == ([], True)

    @check("AutoPilot XDS.INP import: beamline geometry kept, local paths, beamline computer settings out")
    def _():
        src = scratch / "import_src" / "XDS.INP"
        src.parent.mkdir(parents=True, exist_ok=True)
        (src.parent / "XDS.INP").write_text(
            "! beamline file\nJOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\n"
            "NAME_TEMPLATE_OF_DATA_FRAMES= /dls/i04/data/x_??????.h5\nLIB= /dls/software/durin-plugin.so\n"
            "NX= 4148 NY= 4362  QX= 0.075 QY= 0.075  ! detector\nROTATION_AXIS= -1 0 0\n"
            "DATA_RANGE= 1 3600\nMAXIMUM_NUMBER_OF_JOBS= 16  CLUSTER_NODES= node1 node2\n"
            "INCLUDE_RESOLUTION_RANGE= 50 1.2\nX-GEO_CORR= /dls/geo/x.cbf\nSPACE_GROUP_NUMBER= 96\n", encoding="utf-8")
        ds = {"kind": "eiger", "template": "/mnt/z/raw/x_master.h5", "first": None, "last": None}
        text, notes = m.import_xdsinp(src, ds, "/opt/xds/dectris-neggia.so")
        values = m.xdsinp_values(text)
        assert values["NAME_TEMPLATE_OF_DATA_FRAMES"] == "/mnt/z/raw/x_??????.h5", values
        assert values["LIB"] == "/opt/xds/dectris-neggia.so" and values["ROTATION_AXIS"] == "-1 0 0", values
        assert values["NX"] == "4148" and values["QY"] == "0.075" and values["SPACE_GROUP_NUMBER"] == "96", values
        for gone in ("MAXIMUM_NUMBER_OF_JOBS", "CLUSTER_NODES", "INCLUDE_RESOLUTION_RANGE", "X-GEO_CORR"):
            assert gone not in values and ("!" + gone + "=") in text, (gone, text)
        assert any("INCLUDE_RESOLUTION_RANGE" in n for n in notes), notes
        series = {"kind": "series", "template": "/mnt/z/raw/y_????.cbf", "first": 1, "last": 1800}
        text2, notes2 = m.import_xdsinp(src, series, "")
        v2 = m.xdsinp_values(text2)
        assert v2["DATA_RANGE"] == "1 1800" and "LIB" not in v2, v2
        assert any("DATA_RANGE" in n for n in notes2), notes2

    @check("AutoPilot space-group route: without it, with it, then auto-indexing - as chosen")
    def _():
        kwargs = m.strategy_autopilot_kwargs({})
        with_sg = "NAME_TEMPLATE_OF_DATA_FRAMES= x_????.cbf\nSPACE_GROUP_NUMBER= 19\nUNIT_CELL_CONSTANTS= 78 78 37 90 90 90\n"
        runs = m.batch_attempts({}, kwargs, with_sg)
        assert len(runs) == 3, runs
        first, second, third = runs
        assert "SPACE_GROUP_NUMBER" not in m.xdsinp_values(first["xdsinp"]) and first["kwargs"]["autoindex_tier"] == "off"
        assert "space_group" not in first["kwargs"]
        assert second["kwargs"]["space_group"] == "19" and second["kwargs"]["unit_cell"] == "78 78 37 90 90 90"
        assert second["kwargs"]["autoindex_tier"] == "off" and second["xdsinp"] == with_sg
        assert third["kwargs"]["autoindex_tier"] == "medium" and "space_group" not in third["kwargs"]
        assert "UNIT_CELL_CONSTANTS" not in m.xdsinp_values(third["xdsinp"])
        assert len(m.batch_attempts({"autoindex_tier": "off"}, m.strategy_autopilot_kwargs({"autoindex_tier": "off"}), with_sg)) == 2
        used = m.batch_attempts({"sg_route": "use"}, kwargs, with_sg)
        assert len(used) == 1 and used[0]["kwargs"]["space_group"] == "19"
        ignored = m.batch_attempts({"sg_route": "ignore"}, kwargs, with_sg)
        assert len(ignored) == 1 and "SPACE_GROUP_NUMBER" not in m.xdsinp_values(ignored[0]["xdsinp"])
        assert len(m.batch_attempts({}, kwargs, "SPACE_GROUP_NUMBER= 0\n")) == 1
        assert m.batch_attempts({}, kwargs, None) == [{"label": "", "kwargs": kwargs, "xdsinp": None}]
        fixed = {"sg_mode": "fixed", "space_group": "96", "unit_cell": "57 57 150 90 90 90"}
        # a space group without a unit cell in the beamline file cannot be used by XDS
        no_cell = m.batch_attempts({}, kwargs, "SPACE_GROUP_NUMBER= 19\n")
        assert len(no_cell) == 1 and "SPACE_GROUP_NUMBER" not in m.xdsinp_values(no_cell[0]["xdsinp"]), no_cell
        assert len(m.batch_attempts(fixed, m.strategy_autopilot_kwargs(fixed), with_sg)) == 1

    @check("AutoPilot: a beamline file's UNIT_CELL_A/B/C-AXIS kept, one more run without them if the others fail")
    def _():
        kwargs = m.strategy_autopilot_kwargs({})
        axes = ("UNIT_CELL_A-AXIS= 184.1 0.3 -2.0\nUNIT_CELL_B-AXIS= 1.2 321.5 0.4\n"
                "UNIT_CELL_C-AXIS= 0.1 -0.2 65.0\n")
        plain = "NAME_TEMPLATE_OF_DATA_FRAMES= x_????.cbf\n" + axes
        runs = m.batch_attempts({}, kwargs, plain)
        assert len(runs) == 2, runs
        assert runs[0]["xdsinp"] == plain and runs[1]["kwargs"] == kwargs
        v = m.xdsinp_values(runs[1]["xdsinp"])
        assert not any(k in v for k in ("UNIT_CELL_A-AXIS", "UNIT_CELL_B-AXIS", "UNIT_CELL_C-AXIS")), runs[1]["xdsinp"]
        assert v["NAME_TEMPLATE_OF_DATA_FRAMES"] == "x_????.cbf" and "UNIT_CELL_A/B/C-AXIS" in runs[1]["label"]
        # with a space group: the three usual runs, then the auto-indexing one again without the axes
        with_sg = plain + "SPACE_GROUP_NUMBER= 19\nUNIT_CELL_CONSTANTS= 78 78 37 90 90 90\n"
        runs = m.batch_attempts({}, kwargs, with_sg)
        assert len(runs) == 4 and runs[3]["kwargs"] == runs[2]["kwargs"], runs
        assert "UNIT_CELL_B-AXIS" not in m.xdsinp_values(runs[3]["xdsinp"]) and "SPACE_GROUP_NUMBER" not in m.xdsinp_values(runs[3]["xdsinp"])
        # commented axes: nothing extra
        assert len(m.batch_attempts({}, kwargs, "NAME_TEMPLATE_OF_DATA_FRAMES= x_????.cbf\n!UNIT_CELL_A-AXIS= 1 0 0\n")) == 1

    @check("batch merge: consistent data sets in, the rest out with a reason, XSCALE.INP layout valid")
    def _():
        def project(name, sg, cell, isa):
            (m.PROJECTS_DIR / name).mkdir(parents=True, exist_ok=True)
            p = m._pdir(name)
            (p / "metadata.json").write_text('{"name": "%s"}' % name, encoding="utf-8")
            (p / "XDS_ASCII.HKL").write_text("!FORMAT=XDS_ASCII\n!SPACE_GROUP_NUMBER=%s\n!UNIT_CELL_CONSTANTS= %s\n!END_OF_HEADER\n1 1 1 1 1\n" % (sg, cell),
                                             encoding="utf-8")
            (p / "AUTOPILOT_RESULTS.json").write_text('{"resolution": 1.9}', encoding="utf-8")
            lp = fixture("CORRECT.LP").replace("21.2", str(isa)) if isa else fixture("CORRECT.LP")
            (p / "CORRECT.LP").write_text(lp, encoding="utf-8")
        project("m_ref", "20", "98.5 119.6 161.4 90 90 90", None)
        project("m_close", "20", "99.0 120.1 162.0 90 90 90", None)
        project("m_other_sg", "5", "98.5 119.6 161.4 90 90 90", None)
        project("m_far_cell", "20", "108.0 119.6 161.4 90 90 90", None)
        plan = m.merge_plan(["m_ref", "m_close", "m_other_sg", "m_far_cell", "m_missing"], "isig2", reference="m_ref")
        assert [r["project"] for r in plan["inputs"]] == ["m_ref", "m_close"], plan
        reasons = {e["project"]: e["reason"] for e in plan["excluded"]}
        assert "space group" in reasons["m_other_sg"] and "cell" in reasons["m_far_cell"], reasons
        assert "invalid" in reasons.get("m_missing", "") or "XDS_ASCII" in reasons.get("m_missing", ""), reasons
        text = m.merge_xscale_inp(plan, "TRUE", ["inputs/01_m_ref.HKL", "inputs/02_m_close.HKL"])
        errors = xscale_layout_errors(text)
        assert not errors, errors
        assert "REFERENCE_DATA_SET= inputs/01_m_ref.HKL" in text and "INCLUDE_RESOLUTION_RANGE= 999 1.90" in text, text
        assert text.index("REFERENCE_DATA_SET") < text.index("OUTPUT_FILE"), "REFERENCE_DATA_SET is a global keyword"

    @check("LP parsers: the refined beam centre and distance, not the input echo (real IDXREF.LP / CORRECT.LP)")
    def _():
        idx = m.LPParser.parse_idxref(fixture("real/IDXREF.LP"))
        assert (idx["orgx"], idx["orgy"], idx["detector_distance"]) == (2008.90, 2253.10, 197.44), idx
        assert idx["orgx_initial"] == 2008.90 and idx["detector_distance_initial"] == 197.44
        cor = m.LPParser.parse_correct(fixture("real/CORRECT.LP"))
        # CORRECT refined the origin: input 2008.90 2253.10 -> 2004.94 2252.79
        assert cor["refined_beam_center"] == {"orgx": 2004.94, "orgy": 2252.79}, cor.get("refined_beam_center")
        synthetic = fixture("real/IDXREF.LP").replace(" DETECTOR ORIGIN (PIXELS) AT                     2008.90   2253.10",
                                                      " DETECTOR ORIGIN (PIXELS) AT                     2011.50   2250.25")
        moved = m.LPParser.parse_idxref(synthetic)
        assert (moved["orgx"], moved["orgy"]) == (2011.50, 2250.25) and moved["orgx_initial"] == 2008.90, moved

    @check("XDS.INP generator: DATA_RANGE from the frame numbers on disk; spot ranges never overlap")
    def _():
        folder = scratch / "numbering"
        folder.mkdir()
        for n in range(101, 301):
            (folder / ("lyso_100K_%05d.cbf" % n)).write_bytes(b"")
        (folder / "lyso_100K_2_00001.cbf").write_bytes(b"")                  # another sweep: not counted
        tmpl = str(folder / "lyso_100K_?????.cbf")
        assert m.XDSINPGenerator.frame_numbers(tmpl) == (101, 300, 200)
        header = {"wavelength": "0.97", "detector_distance": "250", "osc_range": "0.5", "nframes": "200",
                  "first_frame": 101, "last_frame": 300, "nx": "2463", "ny": "2527", "detector_name": "PILATUS 6M"}
        content, _ = m.XDSINPGenerator.generate(tmpl, header)
        assert "DATA_RANGE= 101 300" in content and "STARTING_FRAME= 101" in content, content
        assert "BACKGROUND_RANGE= 101 110" in content, content
        spots = re.findall(r"^SPOT_RANGE= (\d+) (\d+)", content, re.M)
        assert spots == [("101", "280")], spots                              # 90 deg = 180 frames; a second wedge would overlap
        header.update({"osc_range": "0.1", "nframes": "3600", "first_frame": 1, "last_frame": 3600})
        content, _ = m.XDSINPGenerator.generate(tmpl, header)
        assert re.findall(r"^SPOT_RANGE= (\d+) (\d+)", content, re.M) == [("1", "900"), ("2701", "3600")], content

    @check("AutoPilot auto-indexing fallback: the best successful trial is applied, as the Auto-Index card would")
    def _():
        proj = scratch / "ai_best"
        proj.mkdir()
        assert m._ap_best_autoindex_trial(proj) is None
        trials = [{"success": True, "score": 0.4, "indexed_fraction": 0.6, "label": "a", "signal_pixel": 6, "spot_ranges": [[1, 50]]},
                  {"success": True, "score": 0.9, "indexed_fraction": 0.8, "label": "b", "signal_pixel": 9,
                   "spot_ranges": [[1, 30], [900, 930]], "index_error": 0.08, "min_pixels": 4, "index_origin": [0, 0, 1]},
                  {"success": False, "score": 5.0, "indexed_fraction": 0.1, "label": "c", "signal_pixel": 3, "spot_ranges": [[1, 10]]}]
        (proj / "AUTOINDEX_RESULTS.json").write_text(json.dumps({"all_results": trials}), encoding="utf-8")
        best = m._ap_best_autoindex_trial(proj)
        assert best["label"] == "b", best
        out = m.XDSINPEditor.apply_params("JOB= IDXREF\nSPOT_RANGE= 1 900\nSIGNAL_PIXEL= 6\n", m._ap_autoindex_params(best))
        values = m.xdsinp_values(out)
        assert values["SIGNAL_PIXEL"] == "9" and values["INDEX_ERROR"] == "0.08" and values["INDEX_ORIGIN"] == "0 0 1", out
        assert re.findall(r"^SPOT_RANGE= (.*)$", out, re.M) == ["1 30", "900 930"], out

    @check("group D: XSCALE inputs from a run subfolder keep the reference marker and trailing words")
    def _():
        text = "OUTPUT_FILE= m.ahkl\n  INPUT_FILE=*XDS_ASCII.HKL XDS_ASCII 50\nINPUT_FILE= /abs/b.HKL\n!INPUT_FILE= c.HKL\n"
        out = m._xscale_inputs_from_subfolder(text, "..")
        assert "  INPUT_FILE= *../XDS_ASCII.HKL XDS_ASCII 50" in out, out
        assert "INPUT_FILE= /abs/b.HKL" in out and "!INPUT_FILE= c.HKL" in out, out

    @check("group D: the editor activates a keyword on a commented shared line without waking its neighbours")
    def _():
        out = m.XDSINPEditor.apply_params("!SPACE_GROUP_NUMBER= 0  UNIT_CELL_CONSTANTS= 0 0 0 0 0 0\nJOB= ALL", {"SPACE_GROUP_NUMBER": "19"})
        values = m.xdsinp_values(out)
        assert values.get("SPACE_GROUP_NUMBER") == "19" and "UNIT_CELL_CONSTANTS" not in values, out
        # clearing every exclusion range in the form comments the active ones out
        out2 = m.XDSINPEditor.apply_params("EXCLUDE_DATA_RANGE= 10 20\nEXCLUDE_DATA_RANGE= 30 40\n", {"EXCLUDE_DATA_RANGE": "__commented__"})
        assert "EXCLUDE_DATA_RANGE" not in m.xdsinp_values(out2), out2

    @check("group D: 'only if better' does not keep a re-integration whose value could not be determined")
    def _():
        ok, why = m._ap_optimize_is_better({"resolution": 1.8}, {"resolution": None}, "resolution")
        assert ok is False and "could not be determined" in why, why

    @check("group D: beamline ranges are fitted to the frames on disk, never inverted")
    def _():
        src = scratch / "ranges_src" / "XDS.INP"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("NAME_TEMPLATE_OF_DATA_FRAMES= /b/x_????.cbf\nDATA_RANGE= 1 100\nBACKGROUND_RANGE= 1 10\nSPOT_RANGE= 1 50\nSPOT_RANGE= 60 90\n",
                       encoding="utf-8")
        text, notes = m.import_xdsinp(src, {"kind": "series", "template": "/d/x_????.cbf", "first": 200, "last": 300})
        v = m.xdsinp_values(text)
        assert v["DATA_RANGE"] == "200 300" and v["BACKGROUND_RANGE"] == "200 209", text
        assert "SPOT_RANGE" not in v and text.count("!SPOT_RANGE=") == 2, text

    @check("group D: settings are saved through a temporary file")
    def _():
        assert m._save_settings(test_probe="1") is True
        assert m._load_settings().get("test_probe") == "1"
        assert not list(m.SETTINGS_FILE.parent.glob(m.SETTINGS_FILE.name + ".*.tmp"))

    @check("re-integration judgement: 'keep only if better' compares the chosen metric honestly")
    def _():
        better = m._ap_optimize_is_better
        assert better({"isa": 21.0}, {"isa": 22.5}, "isa")[0] is True
        assert better({"isa": 21.0}, {"isa": 19.0}, "isa")[0] is False
        assert better({"resolution": 1.80}, {"resolution": 1.72}, "resolution")[0] is True
        assert better({"resolution": 1.72}, {"resolution": 1.80}, "resolution")[0] is False
        assert better({"cc_half": "99.1*"}, {"cc_half": "98.4*"}, "cc_half")[0] is False
        ok, why = better({"isa": None}, {"isa": 20}, "isa")
        assert ok is True and "not available" in why, why

    @check("problem report: no user name and no token leave the computer")
    def _():
        import zipfile, json as _json
        bs = chr(92)
        # every place a user name sits in a path - including the forms that
        # got through the first version: JSON's doubled backslashes and the
        # Windows 8.3 short name
        samples = [
            "/home/alice/data/frames",
            "/Users/alice/Desktop",
            "C:" + bs + "Users" + bs + "Alice Smith" + bs + "AppData",
            _json.dumps({"p": "C:" + bs + "Users" + bs + "Alice Smith" + bs + "AppData"}),
            "C:" + bs + "Users" + bs + "ALICES~1" + bs + "AppData" + bs + "Local",
            "/mnt/c/Users/Alice Smith/Downloads",
            "token " + m.API_TOKEN,
        ]
        for text in samples:
            out = m._report_redact(text)
            for leaked in ("alice", "Alice Smith", "ALICES~1", m.API_TOKEN):
                assert leaked not in out, (text, out)
        assert m._report_redact_data({"a": ["/home/bob/x", {"b": "/Users/bob"}]}) == {"a": ["/home/<user>/x", {"b": "/Users/<user>"}]}

    @check("problem report: the zip holds what the author needs; project files only when ticked")
    def _():
        import zipfile
        name = "report test"
        (m.PROJECTS_DIR / name).mkdir(parents=True, exist_ok=True)
        p = m._pdir(name)
        (p / "metadata.json").write_text('{"name": "report test"}', encoding="utf-8")
        (p / "XDS.INP").write_text("JOB= XYCORR\n", encoding="utf-8")
        (p / "IDXREF.LP").write_text("!!! ERROR !!! INSUFFICIENT PERCENTAGE\n", encoding="utf-8")
        without = m.build_problem_report("IDXREF fails", project=name, include_project=False,
                                         page_errors=["TypeError: boom"])
        with zipfile.ZipFile(without["path"]) as zf:
            names = zf.namelist()
        assert "REPORT.txt" in names and "environment.json" in names and "page-errors.txt" in names, names
        assert not [n for n in names if n.startswith("project/")], "project files attached without the tick: %s" % names
        with_files = m.build_problem_report("IDXREF fails", project=name, include_project=True)
        with zipfile.ZipFile(with_files["path"]) as zf:
            names = zf.namelist()
        assert "project/XDS.INP" in names and "project/IDXREF.LP" in names, names
        # an empty description is refused: that is the part nobody else can write
        try:
            m.build_problem_report("   ")
            raise AssertionError("an empty report was accepted")
        except ValueError:
            pass

    @check("problem report: the mail link fits what Windows hands to a mail program")
    def _():
        import urllib.parse
        long_text = "INTEGRATE stopped.\n" + ("A long description with spaces and line breaks.\n" * 200)
        d = m.build_problem_report(long_text)
        link = "mailto:%s?subject=%s&body=%s" % (d["report_email"], urllib.parse.quote(d["mail_subject"], safe=""),
                                                 urllib.parse.quote(d["mail_body"], safe=""))
        assert len(link) <= m.REPORT_MAIL_LINK, len(link)
        assert "shortened" in d["mail_body"], d["mail_body"][-120:]
        assert d["mail_subject"].startswith("CrystalPilot " + m.VERSION), d["mail_subject"]
        assert m._report_matches(d["name"]), d["name"]
        for bad in ("../x.zip", "crystalpilot-report_2026-09-12.zip", "lyso_2026-09-12.zip", ""):
            assert not m._report_matches(bad), bad

    @check("export: one zip with the result, never the frames or the scratch files")
    def _():
        import zipfile
        name = "export test"
        (m.PROJECTS_DIR / name).mkdir(parents=True, exist_ok=True)
        p = m._pdir(name)
        (p / "metadata.json").write_text('{"name": "export test"}', encoding="utf-8")
        wanted = ("XDS.INP", "CORRECT.LP", "XSCALE.INP", "AUTOPILOT_RESULTS.json",
                  "CORRECT_CC_HALF_vs_Resolution.png", "GXPARM.XDS")
        data = ("XDS_ASCII.HKL", "merged.ahkl", "temp.mtz")
        # what makes a project folder big, and what the next run rewrites anyway
        never = ("DX-CORRECTIONS.cbf", "frame_00001.cbf", "lyso_master.h5", "SPOT.XDS", "CORRECT.LP.prev1")
        for f in wanted + data + never:
            (p / f).write_bytes(b"x" * 2048)
        sub = p / "XSCALE_001"; sub.mkdir(exist_ok=True)
        (sub / "XSCALE.LP").write_bytes(b"y" * 2048)

        result = m.export_project(name, reflections=True)
        with zipfile.ZipFile(result["path"]) as zf:
            inside = {Path(n).name for n in zf.namelist()}
            assert "README.txt" in inside, sorted(inside)
            readme = zf.read([n for n in zf.namelist() if n.endswith("README.txt")][0]).decode()
        for f in wanted + data:
            assert f in inside, (f, sorted(inside))
        for f in never:
            assert f not in inside, (f, sorted(inside))
        assert "XSCALE.LP" in inside, "a run sub-folder was not looked into"
        assert m.VERSION in readme and name in readme, readme[:200]

        light = m.export_project(name, reflections=False)
        with zipfile.ZipFile(light["path"]) as zf:
            inside = {Path(n).name for n in zf.namelist()}
        assert "CORRECT.LP" in inside and "XDS_ASCII.HKL" not in inside, sorted(inside)

    @check("export: the download route accepts only this project's own archive")
    def _():
        name = "export test"
        assert m._export_matches(name, m._export_name(name))
        for bad in ("../../etc/passwd", "other_2026-09-12.zip", "export_test_2026-9-12.zip",
                    "export_test.zip", "export_test_2026-09-12.zip.part", "", "."):
            assert not m._export_matches(name, bad), bad

    @check("log file: the program writes one, and the API token never reaches it")
    def _():
        # the console may show the token (whoever sees it runs the program); the
        # log lives in the projects folder, which other people may be able to read
        line = "API token: " + m.API_TOKEN + " (only needed by scripts)"
        redacted = m._LogTee._redact(line)
        assert m.API_TOKEN not in redacted, redacted
        assert "token hidden" in redacted, redacted
        import io as _io
        path = scratch / "logs" / "crystalpilot.log"
        tee = m._LogTee(_io.StringIO(), path)
        tee.write("hello\n")
        assert path.is_file() and "hello" in path.read_text(encoding="utf-8")
        # rotation keeps the old one instead of growing without limit
        big = "x" * 4096
        for _ in range((m.LOG_MAX_BYTES // len(big)) + 2):
            tee.write(big)
        assert path.with_name(path.name + ".1").is_file(), sorted(q.name for q in path.parent.iterdir())

    @check("environment report: names each module, so a feature can be gated on one")
    def _():
        report = m._environment_report()
        assert "modules" in report and "matplotlib" in report["modules"], report.get("modules")
        assert isinstance(report["modules"]["matplotlib"], bool), report["modules"]
        assert "log_file" in report, sorted(report)
        html = m.get_frontend_html()
        # the Figures button must consult it rather than let the click fail
        assert "_figuresPossible" in html and "modules.matplotlib" in html
        assert "exportProject" in html and 'id="export-msg"' in html

    @check("figures: names carry their source and only ours are accepted")
    def _():
        for metric in m.FIGURE_ORDER:
            assert m.figure_file_name("CORRECT", metric).startswith("CORRECT_")
            assert m.figure_file_name("xscale", metric).startswith("XSCALE_")
        # a figure name says which log it came from; anything else is refused,
        # which is what keeps the download route from joining a path
        assert m.figure_source_of("CORRECT_CC_HALF_vs_Resolution.png") == "CORRECT"
        assert m.figure_source_of("XSCALE_I_SIGMA_vs_Resolution.png") == "XSCALE"
        for bad in ("CC_HALF_vs_Resolution.png", "../../etc/passwd", "evil.png", ""):
            assert m.figure_source_of(bad) is None, bad

    @check("figures: the real CORRECT.LP gives the whole set (PNG + PDF + overview)")
    def _():
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            raise SkipCheck("matplotlib not installed here (the Linux side has it)")
        lp = FIX / "CORRECT.LP"
        out = scratch / "figures"
        result = m.publication_figures(lp, out, source="CORRECT")
        names = sorted(f["name"] for f in result["files"])
        # four metrics plus the overview, each as a PNG to look at and a PDF for a journal
        expected = sorted(m.figure_file_name("CORRECT", k, fmt)
                          for k in list(m.FIGURE_ORDER) + ["panel"] for fmt in m.FIGURE_FORMATS)
        assert names == expected, names
        for f in result["files"]:
            path = Path(f["path"])
            assert path.is_file() and path.stat().st_size > 5000, f
            head = path.read_bytes()[:8]
            if f["format"] == "png":
                assert head[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG: " + f["name"]
            else:
                assert head[:4] == b"%PDF", "not a PDF: " + f["name"]
            assert f["points"] >= 5, f
        assert "C222" in result["annotation"] and "98.6" in result["annotation"], result["annotation"]
        # a metric that is not in the table is reported, not invented
        assert m._fig_number("97.4*") == 97.4 and m._fig_number("-1.8") == -1.8
        assert m._fig_number("") is None and m._fig_number("-") is None

    @check("figures: the decision drawn on a figure is the program's own cut-off")
    def _():
        # The figure must not compute a cut-off of its own: the vertical marker
        # comes from determine_resolution_cutoff, the code the cut-off buttons
        # use, or the figure and the interface would state different numbers.
        table = m.LPParser.parse_correct(fixture("CORRECT.LP"))["statistics_table"]
        cutoffs = m.LPParser.determine_resolution_cutoff(table)["all_cutoffs"]
        assert cutoffs.get("cc_half_50") and cutoffs.get("isig2"), cutoffs
        for metric, spec in m.FIGURE_METRICS.items():
            criterion = spec["criterion"]
            assert criterion is None or criterion in cutoffs, (metric, criterion)
        # and the x axis is 1/d², so shells sit where their resolution puts them
        shells = m._fig_shells(m.LPParser.parse_correct(fixture("CORRECT.LP")))
        points = m._fig_points(shells, "cc_half")
        d_first = float(shells[0]["resolution"])
        assert abs(points[0][0] - 1.0 / (d_first * d_first)) < 1e-9, points[0]
        assert points[0][0] < points[-1][0], "1/d² must increase with resolution"

    @check("frontend: every cpds/figure helper the page calls by name exists")
    def _():
        html = m.get_frontend_html()
        # A renamed helper still called from a new handler is invisible to the JS
        # syntax check and to any test that does not run that handler (pubFigures
        # called _dsEsc, gone since the search engines were merged).
        called = set(re.findall(r"\b((?:cpds|cpAsk|pubFigures|chartModalPng|_chartModal|_ds)[A-Za-z0-9_]*)\s*\(", html))
        defined = set(re.findall(r"function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", html))
        defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?(?:function|\()", html))
        # a function kept on `window` (the modal remembers how to redraw itself)
        defined |= set(re.findall(r"window\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=", html))
        missing = sorted(called - defined)
        assert not missing, "called but never defined: " + ", ".join(missing)

    @check("frontend: one search engine (header Ask bar); the Docs tab shows the illustrated manual itself")
    def _():
        html = m.get_frontend_html()
        for name in ('id="askbar-in"', 'id="askbar-pop"', "function cpAskGo", "function cpdsSearch",
                     "function cpdsOpenHit", "function cpdsOpenDocs", "function cpdsMarkHtml"):
            assert name in html, "missing from the page: " + name
        assert html.count("function cpdsSearch") == 1, "the search engine is defined twice"
        # the Docs tab had its own ranking once; two rankings are two manuals
        for gone in ("_dsScore", "_dsSnip", "_dsMark(", "_dsTerms"):
            assert gone not in html, "the Docs tab carries its own search again: " + gone
        assert "cpdsRowHtml" in html, "the Ask bar no longer draws shared rows"
        # the Docs tab is the manual, shown inline, filled when the tab opens; manual hits
        # of the search still open the manual at the section, the words marked (?q=)
        assert 'id="docs-manual-host"' in html and "function _docsLoadManual" in html, "the Docs tab does not show the manual"
        assert "<iframe" not in html.split('id="main-tab-docs"', 1)[1].split('id="main-tab-', 1)[0], "the manual is in a frame again: it belongs on the page"
        assert "tab === 'docs' && typeof _docsLoadManual === 'function'" in html, "switchMainTab does not load the manual"
        assert '"/manual/CrystalPilot-Manual.html?q="' in html, "a manual hit no longer opens the manual at its section"


    # -- Windows paths and the drives WSL did not mount ----------------------
    @check("windows paths: a pasted Explorer path becomes a Linux path (drive mounted on demand)")
    def _():
        root = str(scratch / "mnt") + "/"
        was = (m.IS_WSL, m.WSL_MOUNT_ROOT, m._drvfs_mount)
        m.IS_WSL, m.WSL_MOUNT_ROOT = True, root
        m._drvfs_mount = lambda source, mount_point: True      # pretend the mount worked
        try:
            for typed, want in ((r"D:\data\xtal1", root + "d/data/xtal1"),
                                ("d:/data/xtal1",     root + "d/data/xtal1"),
                                ("D:" + chr(92),      root + "d"),
                                ("D:",                root + "d"),
                                (r'"D:\data"',       root + "d/data"),
                                (r"\\server\share\xtal1", root + "unc/server/share/xtal1"),
                                ("/home/user/data",   "/home/user/data"),
                                ("",                  "")):
                got, problem = m._to_local_path(typed)
                assert got == want, (typed, got, want)
                assert not problem, (typed, problem)
        finally:
            m.IS_WSL, m.WSL_MOUNT_ROOT, m._drvfs_mount = was

    @check("windows paths: a drive that cannot be mounted is reported, not silently swallowed")
    def _():
        was = (m.IS_WSL, m.WSL_MOUNT_ROOT, m._drvfs_mount)
        m.IS_WSL, m.WSL_MOUNT_ROOT = True, str(scratch / "mnt") + "/"
        m._drvfs_mount = lambda source, mount_point: False
        try:
            got, problem = m._to_local_path(r"E:\frames")
            assert got == r"E:\frames", got         # unchanged, so the caller can show what was typed
            assert problem and "E:" in problem, problem
        finally:
            m.IS_WSL, m.WSL_MOUNT_ROOT, m._drvfs_mount = was

    @check("windows paths: outside WSL nothing is translated")
    def _():
        was = m.IS_WSL
        m.IS_WSL = False
        try:
            assert m._to_local_path(r"D:\data") == (r"D:\data", "")
        finally:
            m.IS_WSL = was

    @check("windows paths: the Windows view is the way back (any automount root)")
    def _():
        if os.name == "nt":
            return          # _windows_view resolves POSIX paths; it only means anything inside WSL
        was_wsl, was_root, was_drive = m.IS_WSL, m.WSL_MOUNT_ROOT, os.environ.get("CRYSTALPILOT_DRIVE")
        os.environ.pop("CRYSTALPILOT_DRIVE", None)
        m.IS_WSL = True
        try:
            for root, path, want in (("/mnt/", "/mnt/d/data/xtal1", r"D:\data\xtal1"),
                                     ("/mnt/", "/mnt/d",           "D:" + chr(92)),
                                     ("/mnt/", "/mnt/unc/server/share/x", r"\\server\share\x"),
                                     ("/",     "/c/data",          r"C:\data")):
                m.WSL_MOUNT_ROOT = root
                got = m._windows_view(path)
                assert got == want, (root, path, got, want)
            m.WSL_MOUNT_ROOT = "/mnt/"
            assert not m._windows_view("/home/user/data").startswith("D:")   # a Linux path is not a drive
        finally:
            m.IS_WSL, m.WSL_MOUNT_ROOT = was_wsl, was_root
            if was_drive is not None:
                os.environ["CRYSTALPILOT_DRIVE"] = was_drive

    @check("windows drives: the file browser chips read the automount root, not a fixed /mnt")
    def _():
        html = m.get_frontend_html()
        assert "d.replace('/mnt/', '')" not in html, "the drive buttons still assume /mnt"
        assert "filter(Boolean).pop()" in html, "the drive button label is not taken from the mount point"
        assert "d.problem" in html, "the browser does not show why a drive could not be reached"

    @check("resources: 4 CPU cores by default, clamped to the machine; RAM 0 = no limit")
    def _():
        assert m.CPU_CORES_DEFAULT == 4
        assert m._clamp_cpu_cores(0) == 1 and m._clamp_cpu_cores(10 ** 6) == len(m._cpus_allowed())
        assert m._clamp_ram_gb(0) == 0.0 and m._clamp_ram_gb(-3) == 0.0
        info = m._resource_info()
        for k in ("cpu_cores", "cpu_available", "ram_gb", "ram_total_gb", "ram_mode", "ram_note"):
            assert k in info, k

    @check("resources: the core count replaces the beamline's in XDS.INP and goes first in XSCALE.INP")
    def _():
        d = scratch / "cpu_keywords"
        d.mkdir(exist_ok=True)
        was = m.CPU_CORES
        try:
            m.CPU_CORES = 3
            (d / "XDS.INP").write_text("JOB= XYCORR\nMAXIMUM_NUMBER_OF_JOBS=4 MAXIMUM_NUMBER_OF_PROCESSORS=16 SECONDS=0 ! bl\nNX= 100\n")
            m._write_cpu_keywords("/opt/xds/xds_par", d)
            t = (d / "XDS.INP").read_text()
            v = m._parse_xdsinp_params(t)
            assert v.get("MAXIMUM_NUMBER_OF_PROCESSORS") == "3" and v.get("MAXIMUM_NUMBER_OF_JOBS") == "1", t
            assert v.get("SECONDS") == "0" and v.get("NX") == "100", t
            assert t.count("MAXIMUM_NUMBER_OF_PROCESSORS") == 1, t
            m._write_cpu_keywords("/opt/xds/xds_par", d)
            assert (d / "XDS.INP").read_text() == t, "a second run changed the file again"
            (d / "XSCALE.INP").write_text("OUTPUT_FILE= a.ahkl\nINPUT_FILE= ../XDS_ASCII.HKL\n")
            m._write_cpu_keywords("xscale_par", d)
            x = (d / "XSCALE.INP").read_text()
            assert x.splitlines()[0].startswith("MAXIMUM_NUMBER_OF_PROCESSORS= 3"), x
            assert not xscale_layout_errors(x), xscale_layout_errors(x)
            (d / "XDS.INP").write_text("JOB= XYCORR\n")
            m._write_cpu_keywords("pointless", d)
            assert (d / "XDS.INP").read_text() == "JOB= XYCORR\n", "a non-XDS program touched XDS.INP"
        finally:
            m.CPU_CORES = was

    @check("AutoPilot screw axes: the absences' space group replaces XDS's screw-less choice; enantiomorphs and ambiguity handled")
    def _():
        # XDS chose C222 (#21); 0,0,l shows a 2-fold screw: C222(1) (#20) is the only consistent group
        sug20 = {"sg_number": 20, "name": "C222₁", "screws": {"00l": 2}}
        choice, other = m._sg_from_absences_choice({"space_group": 21, "sg_suggestions": [sug20]})
        assert choice and choice["sg_number"] == 20 and other == [], (choice, other)
        # absences agree with XDS: nothing to do
        choice, why = m._sg_from_absences_choice({"space_group": 20, "current_sg_name": "C222₁", "sg_suggestions": [sug20]})
        assert choice is None and "agree" in why, why
        # enantiomorphs (same screws) cannot be told apart: the first is taken, the other named
        p41 = {"sg_number": 76, "name": "P4₁", "screws": {"00l": 4}}
        p43 = {"sg_number": 78, "name": "P4₃", "screws": {"00l": 4}}
        choice, other = m._sg_from_absences_choice({"space_group": 75, "sg_suggestions": [p41, p43]})
        assert choice["sg_number"] == 76 and other == ["P4₃"], (choice, other)
        # different screw patterns possible (suggestive detections): XDS's choice is kept
        choice, why = m._sg_from_absences_choice({"space_group": 16, "sg_suggestions": [
            {"sg_number": 17, "name": "P222₁", "screws": {"00l": 2}},
            {"sg_number": 18, "name": "P2₁2₁2", "screws": {"h00": 2, "0k0": 2}}]})
        assert choice is None and "allow" in why, why
        # no axial reflections: kept
        assert m._sg_from_absences_choice({"space_group": 21})[0] is None
        # the wizard option: ticked by default, only when the space group is determined per data set
        opt = next(o for o in m.STRATEGY_OPTIONS if o["key"] == "sg_absences")
        assert opt["default"] == "on" and opt["input"] == "checkbox" and opt["depends"] == {"sg_mode": "auto"}
        assert m.strategy_autopilot_kwargs({})["sg_from_absences"] is True
        assert m.strategy_autopilot_kwargs({"sg_absences": "off"})["sg_from_absences"] is False
        import inspect
        assert inspect.signature(m.stream_autopilot).parameters["sg_from_absences"].default is True

    @check("resources: XDS.INP / XSCALE.INP carry the CPU cores by default and follow a change of the setting")
    def _():
        was, was_dir = m.CPU_CORES, m.PROJECTS_DIR
        try:
            m.CPU_CORES = 4
            # a generated XDS.INP has both keywords right after JOB=
            text, _w = m.XDSINPGenerator.generate("/data/x_??????.cbf", {"nx": 2463, "ny": 2527, "pixel_size": 0.172,
                                                   "distance": 200, "wavelength": 1.0, "oscillation": 0.1,
                                                   "beam_x": 1200, "beam_y": 1300, "detector": "PILATUS"})
            lines = [l.strip() for l in text.splitlines()]
            j = next(i for i, l in enumerate(lines) if l.startswith("JOB="))
            assert lines[j + 1].startswith("MAXIMUM_NUMBER_OF_PROCESSORS= 4"), lines[j:j + 3]
            assert lines[j + 2] == "MAXIMUM_NUMBER_OF_JOBS= 1", lines[j:j + 3]
            # a fresh XSCALE.INP from the parameter form: before OUTPUT_FILE, layout valid
            x = m._with_cpu_keywords(m._xscale_apply_params("", {"OUTPUT_FILE": "XSCALE.HKL", "INPUT_FILE": ["../XDS_ASCII.HKL"]}), "xscale")
            xl = [l.strip() for l in x.splitlines() if l.strip()]
            assert xl.index(next(l for l in xl if l.startswith("MAXIMUM_NUMBER_OF_PROCESSORS= 4"))) < \
                   xl.index(next(l for l in xl if l.startswith("OUTPUT_FILE"))), x
            assert not xscale_layout_errors(x), xscale_layout_errors(x)
            # unchanged when already right (no churn), replaced when different
            assert m._with_cpu_keywords(text, "xds") == text
            # a change of the setting reaches every project's files
            root = scratch / "cpu_projects"
            for p in ("p1", "p2"):
                (root / p).mkdir(parents=True, exist_ok=True)
                (root / p / "XDS.INP").write_text(text)
                (root / p / "XSCALE.INP").write_text(x)
            m.PROJECTS_DIR = root
            m.CPU_CORES = 6
            assert m._sync_cpu_keywords_all_projects() == 4
            for p in ("p1", "p2"):
                v = m._parse_xdsinp_params((root / p / "XDS.INP").read_text())
                assert v["MAXIMUM_NUMBER_OF_PROCESSORS"] == "6" and v["MAXIMUM_NUMBER_OF_JOBS"] == "1"
                xs = (root / p / "XSCALE.INP").read_text()
                assert "MAXIMUM_NUMBER_OF_PROCESSORS= 6" in xs and "= 4" not in xs, xs
                assert not xscale_layout_errors(xs), xscale_layout_errors(xs)
            assert m._sync_cpu_keywords_all_projects() == 0, "a second pass changed the files again"
            # a save through _write_inp adds them to a file that has none
            m._write_inp(root / "p1" / "XDS.INP", "JOB= CORRECT\nNX= 100\n")
            v = m._parse_xdsinp_params((root / "p1" / "XDS.INP").read_text())
            assert v.get("MAXIMUM_NUMBER_OF_PROCESSORS") == "6" and v.get("MAXIMUM_NUMBER_OF_JOBS") == "1", v
        finally:
            m.CPU_CORES, m.PROJECTS_DIR = was, was_dir

    @check("input files: a UTF-8 BOM and whole numbers written as decimals (NX= 4150.0) are removed before XDS / XSCALE / XDSCONV read them")
    def _():
        # XDS / XSCALE / XDSCONV stop with ILLEGAL KEYWORD on both (tested with XDS Apr 16, 2026)
        bom = "﻿"
        root = scratch / "clean_inp"
        root.mkdir(parents=True, exist_ok=True)
        src = bom + "JOB= XYCORR\nNX= 4150.0  NY= 4371.0  QX= 0.075  QY= 0.075  ! detector\nDATA_RANGE= 1.0 60.0\n" \
                    "SPOT_RANGE= 1 60\nORGX= 2008.5 ORGY= 2253.0\nX-RAY_WAVELENGTH= 0.979338\n!NX= 12.0\n"
        m._write_inp(root / "XDS.INP", src)
        out = (root / "XDS.INP").read_text(encoding="utf-8")
        assert bom not in out, repr(out[:20])
        v = m._parse_xdsinp_params(out)
        assert v["NX"] == "4150" and v["NY"] == "4371" and v["DATA_RANGE"] == "1 60", v
        assert v["ORGX"] == "2008.5" and v["ORGY"] == "2253.0" and v["QX"] == "0.075", v   # real numbers untouched
        assert "! detector" in out and "!NX= 12.0" in out, out                                 # comments untouched
        assert m._clean_inp_text("NX= 4150.5\n", "xds") == "NX= 4150.5\n"                  # not a whole number: left to XDS
        # STRONG_PIXEL= (older beamline XDS.INP files, e.g. APS gmcaproc): current XDS stops with ILLEGAL KEYWORD
        v = m._parse_xdsinp_params(m._clean_inp_text("   STRONG_PIXEL= 25!10\nNX= 100\n", "xds"))
        assert v.get("SIGNAL_PIXEL") == "25" and "STRONG_PIXEL" not in v, v
        both = m._clean_inp_text("STRONG_PIXEL= 4.0\nSIGNAL_PIXEL= 6.0\n", "xds")               # given twice XDS stops too
        v = m._parse_xdsinp_params(both)
        assert v.get("SIGNAL_PIXEL") == "6.0" and "STRONG_PIXEL" not in v and both.count("SIGNAL_PIXEL=") == 2, both
        assert m._clean_inp_text(both, "xds") == both                                        # a second pass changes nothing
        # a file put in the folder by hand is cleaned just before the program starts
        for name, text in (("XSCALE.INP", bom + "OUTPUT_FILE= merged.ahkl\nINPUT_FILE= XDS_ASCII.HKL\n"),
                           ("XDSCONV.INP", bom + "INPUT_FILE= merged.ahkl\nOUTPUT_FILE= temp.hkl CCP4_I+F\n"),
                           ("XDS.INP", bom + "JOB= XYCORR\nNX= 4150.0\n")):
            (root / name).write_text(text, encoding="utf-8")
        for prog in ("xscale_par", "xdsconv", "xds_par"):
            m._write_cpu_keywords(prog, root)
        for name in ("XSCALE.INP", "XDSCONV.INP", "XDS.INP"):
            assert bom not in (root / name).read_text(encoding="utf-8"), name
        assert "MAXIMUM_NUMBER" not in (root / "XDSCONV.INP").read_text(encoding="utf-8")   # no CPU keywords for XDSCONV
        assert "NX= 4150" in (root / "XDS.INP").read_text(encoding="utf-8").replace("4150.0", "x")


# ═════════════════════════════════════════════════════════════════════════════
def main():
    build = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else newest_build()
    print("build:", build.name)
    m, scratch = load_module(build)
    define_checks(m, scratch)
    failed = 0
    for name, fn in RESULTS:
        try:
            fn()
            print("ok   " + name)
        except SkipCheck as e:
            print("skip " + name + " (" + str(e) + ")")
        except Exception as e:
            failed += 1
            msg = str(e)
            print("FAIL " + name + "\n     " + (msg[:1500] if msg else type(e).__name__))
    print("%d checks, %d failed" % (len(RESULTS), failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
