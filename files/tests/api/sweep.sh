# Sourced by api_tests.sh inside the real-chain section (same server, project 'real').
# Calls every remaining endpoint of the interface with real inputs and requires a
# valid answer.  Variables/functions come from api_tests.sh: T PORT U TOK c cj
# stream done_ok explain check ok bad tmpl fdir CURL PY FILES CCP4B.
echo "=== 5. endpoint sweep on project 'real' (every remaining route)"
P="$T/projects/real"
MASTER=$(ls "$fdir"/*_master.h5 2>/dev/null | head -1)
enc()  { "$PY" -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }
has()  { grep -q -- "$1" "$T/out.json"; }
g() {  # GET  $1=path $2=grep marker expected in the body
    C=$(c -o "$T/out.json" -w '%{http_code}' "$U$1")
    check "GET  $1" "[ $C = 200 ] && has '$2'" "code=$C $(head -c 240 "$T/out.json" | tr '\n' ' ')"
}
p() {  # POST $1=path $2=json body $3=marker
    C=$(cj -o "$T/out.json" -w '%{http_code}' -X POST "$U$1" -d "$2")
    check "POST $1" "[ $C = 200 ] && has '$3'" "code=$C $(head -c 240 "$T/out.json" | tr '\n' ' ')"
}
# ── project, inputs, logs, metrics ──────────────────────────────────────────
g "/api/projects" '"real"'
g "/api/projects/real" 'output_dir'
for s in XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT; do g "/api/projects/real/lp/$s" '"content"'; done
for s in IDXREF INTEGRATE COLSPOT INIT CORRECT; do g "/api/projects/real/metrics/$s" '"metrics"'; done
g "/api/projects/real/xdsinp" '"content"'
g "/api/projects/real/xscaleinp" '"content"'
g "/api/projects/real/xscalelp" 'XSCALE'
g "/api/projects/real/xdsconvinp" '"content"'
g "/api/projects/real/xdsconvlp" 'XDSCONV'
g "/api/projects/real/xscale-subfolders" '{'
g "/api/projects/real/locations" 'xds_output'
g "/api/projects/real/generate-xdsinp" 'DETECTOR'
g "/api/xscale-detect-hkl?project=real" '"files"'
# ── illustrated manual (served without token when docs/manual exists) ────────
C=$("$CURL" -s -o "$T/out.json" -w '%{http_code}' "$U/manual/"); check "GET  /manual/ reports availability" "[ $C = 200 ] && has '\"available\"'" "code=$C $(head -c 200 $T/out.json)"
if grep -q '"available": true' "$T/out.json"; then
    C=$("$CURL" -s -o /dev/null -w '%{http_code}' "$U/manual/CrystalPilot-Manual.html"); check "GET  /manual/CrystalPilot-Manual.html" "[ $C = 200 ]" "code=$C"
    C=$("$CURL" -s -o "$T/idx.json" -w '%{http_code}' "$U/manual/CrystalPilot-Manual.index.json"); check "GET  /manual/CrystalPilot-Manual.index.json (Docs search index)" "[ $C = 200 ] && grep -q '\"a\": *\"ch-' $T/idx.json" "code=$C $(head -c 120 $T/idx.json)"
fi
C=$("$CURL" -s -o /dev/null -w '%{http_code}' --path-as-is "$U/manual/../src/config.py"); check "GET  /manual/ refuses paths outside the folder" "[ $C = 404 ]" "code=$C"
# ── configuration / environment ─────────────────────────────────────────────
g "/api/environment" '"checks"'
g "/api/config" 'projects_dir'
g "/api/ccp4check" '"found"'
g "/api/xdscheck" '"xds"'
g "/api/deps" '"ready"'
g "/api/ls?path=$(enc "$P")" '"entries"'
p "/api/config" '{"parallel": true}' '"parallel"'
p "/api/projects/real/settings" '{"viewer_template": "/tmp/x_??????.h5"}' 'Settings saved'
p "/api/open-folder" "{\"path\": \"$P\", \"dry\": true}" '"ok": true'
# ── frame viewer on the real master file ────────────────────────────────────
g "/api/h5/nframes?path=$(enc "$MASTER")" 'nframes'
g "/api/fv-xdsinp?path=$(enc "$P/XDS.INP")" '{'
g "/api/fv-spots?dir=$(enc "$P")" '{'
g "/api/frames/list?template=$(enc "$tmpl")" '"files"'
C=$(c -o "$T/frame.json" -w '%{http_code}' "$U/api/frame?path=$(enc "$MASTER")&frame=1&vmin=0&vmax=99.5")
# the viewer receives {"image": "<base64 PNG>", ...}; iVBORw0KGgo is the PNG signature in base64
check "GET  /api/frame renders a PNG from the real master" "[ $C = 200 ] && grep -q '\"image\": \"iVBORw0KGgo' $T/frame.json && [ \$(stat -c %s $T/frame.json) -gt 20000 ]" "code=$C $(head -c 200 $T/frame.json | tr '\n' ' ')"
# ── history and comparison: needs a previous run of each program ────────────
if [ "${CP_SKIP_RERUNS:-0}" != 1 ]; then   # CP_SKIP_RERUNS=1: the imported .prev files are the history
stream rerun1 "/api/stream?project=real&steps=IDXREF" 900;                    check "rerun IDXREF (history)" "done_ok rerun1 IDXREF" "$(explain rerun1)"
stream rerun2 "/api/stream?project=real&steps=DEFPIX,INTEGRATE,CORRECT" 900;  check "rerun CORRECT (history)" "done_ok rerun2 CORRECT" "$(explain rerun2)"
stream rerun3 "/api/xscale/stream?project=real" 600;                           check "rerun XSCALE (history)" "done_ok rerun3 XSCALE" "$(explain rerun3)"
fi
check "CORRECT.LP.prev1 rotated" "[ -f $P/CORRECT.LP.prev1 ] && [ -f $P/IDXREF.LP.prev1 ] && [ -f $P/XSCALE.LP.prev1 ]" "$(ls $P | grep prev)"
g "/api/projects/real/compare-correct" '"current"'
g "/api/projects/real/compare-idxref" '"current"'
g "/api/projects/real/compare-xscale" '"current"'
g "/api/projects/real/history-correct" '{'
g "/api/projects/real/history-idxref" '{'
g "/api/projects/real/history-xscale" '{'
for f in CORRECT IDXREF XSCALE; do
    what=$(echo $f | tr 'A-Z' 'a-z')
    # body via a file: a full-data CORRECT.LP (150 kB) exceeds the 128 kB single-argument limit of exec()
    "$PY" -c 'import json,sys; open(sys.argv[2], "w").write(json.dumps({"lp_content": open(sys.argv[1], errors="replace").read()}))' "$P/$f.LP" "$T/lp_body.json"
    C=$(cj -o "$T/out.json" -w '%{http_code}' -X POST "$U/api/projects/real/compare-$what-file" -d "@$T/lp_body.json")
    check "POST /api/projects/real/compare-$what-file" "[ $C = 200 ] && has current" "code=$C $(head -c 240 "$T/out.json" | tr '\n' ' ')"
done
# (routes exercised by the loop above: compare-correct-file compare-idxref-file compare-xscale-file)
# ── spot data, ice rings, integration parameters (Data Processing tab helpers) ─
g "/api/projects/real/spot-data" '{'
g "/api/projects/real/ice-rings" '{'
g "/api/projects/real/integrate-params" '{'
# ── tables and exports ──────────────────────────────────────────────────────
g "/api/projects/real/export-data/correct" ','
g "/api/projects/real/export-data/integrate" ','
g "/api/projects/real/table1data" '{'
p "/api/projects/real/export-table1" '{"rows": [["Resolution range", "50-1.8"], ["Completeness (%)", "99.1"]]}' '.'
# ── CCP4 results ────────────────────────────────────────────────────────────
if [ -n "$CCP4B" ]; then
    g "/api/projects/real/pointless-log-raw" 'POINTLESS\|content'
    g "/api/projects/real/pointless-log" '{'
    g "/api/projects/real/pointless-cached" '{'
    g "/api/projects/real/anisotropy-analyze" '{'
    g "/api/projects/real/aimless-log-raw" 'AIMLESS\|content'
    g "/api/projects/real/aimless-log" '{'
    g "/api/projects/real/ctruncate-log" '{'
    g "/api/projects/real/aimless-cached" '{'
fi
# ── XDSCC12 / AutoPilot / gemmi ─────────────────────────────────────────────
g "/api/xdscc12/check" '"found"'
C=$(c -o "$T/out.json" -w '%{http_code}' "$U/api/projects/real/xdscc12-results"); check "GET  xdscc12-results answers" "[ $C = 200 ] || [ $C = 404 ]" "code=$C"
C=$(c -o "$T/out.json" -w '%{http_code}' "$U/api/projects/real/xdscc12-lp");      check "GET  xdscc12-lp answers" "[ $C = 200 ] || [ $C = 404 ]" "code=$C"
g "/api/projects/real/autopilot-cached" '{'
g "/api/autopilot/status" 'running'
g "/api/autopilot/status?project=real" 'running'
g "/api/gemmi/lp-stats?project=real&source=correct" '{'
g "/api/gemmi/lp-stats?project=real&source=xscale" '{'
if "$PY" -c 'import gemmi' 2>/dev/null; then
    for a in merging_stats completeness lattice_symmetry; do
        p "/api/gemmi/analyze" "{\"analysis\": \"$a\", \"project\": \"real\", \"input_file\": \"$P/XDS_ASCII.HKL\"}" '"success": true'
    done
    p "/api/gemmi/anomalous" '{"element": "Se", "wavelength": 0.9793}' '{'
    p "/api/gemmi/deposition" "{\"project\": \"real\", \"input_file\": \"$P/merged.ahkl\"}" '{'
    CIF=$(ls "$P"/*.cif 2>/dev/null | head -1)
    if [ -n "$CIF" ]; then g "/api/gemmi/download-cif?path=$(enc "$CIF")" 'data_\|_refln\|_diffrn'
    else C=$(c -o "$T/out.json" -w '%{http_code}' "$U/api/gemmi/download-cif?path=$(enc "$P/none.cif")"); check "GET  /api/gemmi/download-cif answers for a missing file" "[ $C = 404 ] || [ $C = 400 ]" "code=$C"; fi
    p "/api/gemmi/polarization" "{\"project\": \"real\", \"input_file\": \"$P/XDS_ASCII.HKL\"}" '{'
fi
# ── publication figures (matplotlib PNGs from the shell table) ──────────────
p "/api/figures" '{"project": "real", "source": "CORRECT"}' 'CORRECT_CC_HALF_vs_Resolution.png'
check "figures: the PNGs are on disk next to CORRECT.LP" "[ -s $P/CORRECT_CC_HALF_vs_Resolution.png ] && [ -s $P/CORRECT_I_SIGMA_vs_Resolution.png ]" "$(ls $P | grep -i vs_Resolution | tr '\n' ' ')"
check "figures: the overview sheet and the vector copies are there too" "[ -s $P/CORRECT_Resolution_Statistics.png ] && head -c 4 $P/CORRECT_CC_HALF_vs_Resolution.pdf | grep -q PDF" "$(ls $P | grep -iE 'Resolution_Statistics|[.]pdf' | tr '\n' ' ')"
C=$(c -o "$T/fig.png" -w '%{http_code}' "$U/api/figure?project=real&name=CORRECT_CC_HALF_vs_Resolution.png")
check "GET  /api/figure serves a PNG" "[ $C = 200 ] && head -c 4 $T/fig.png | grep -q PNG" "code=$C $(ls -l $T/fig.png 2>/dev/null | awk '{print $5}')"
C=$(c -o /dev/null -w '%{http_code}' "$U/api/figure?project=real&name=..%2F..%2F..%2Fetc%2Fpasswd")
check "GET  /api/figure refuses a name that is not one of its own" "[ $C = 400 ]" "code=$C"
# ── batch processing on the real data (a real batch is started, then stopped) ─
g "/api/batch/strategy" '"presets"'
# the frames are reached through a folder with a blank in its name, as under /mnt/c/Users/<First Last>/:
# XDS cannot read such a path, so AutoPilot must go through a link without blanks
BLANKDIR="$T/image folder"
mkdir -p "$BLANKDIR" && for f in "$fdir"/*; do ln -sf "$f" "$BLANKDIR/"; done
p "/api/batch/discover" "{\"folder\": \"$BLANKDIR\", \"depth\": 1}" '"datasets"'
DS=$("$PY" -c 'import json,sys; d=json.load(open(sys.argv[1]))["datasets"]; print(json.dumps(d[:1]))' "$T/out.json" 2>/dev/null)
# the data set JSON holds a blank now (the folder name): test it through a file, not inside the check string
printf %s "$DS" > "$T/ds.json"
check "batch: discovery finds the real data set" "grep -q '\"template\"' $T/ds.json" "$(head -c 300 $T/out.json)"
# a folder dropped on the page: the browser gives only its name and files; the server finds where it is
F1=$(ls "$fdir" | head -1); S1=$(stat -c %s "$fdir/$F1")
p "/api/batch/locate-folder" "{\"name\": \"$(basename "$fdir")\", \"files\": [{\"name\": \"$F1\", \"size\": $S1}], \"hints\": [\"$(dirname "$fdir")\"]}" "$(basename "$fdir")"
check "AutoPilot: a dropped folder is found on the server by its name and files" "grep -q '\"folders\": \[\"' $T/out.json" "$(head -c 300 $T/out.json)"
# the beamline's XDS.INP: a copy of the real project's, in a folder whose name contains a keyword
mkdir -p "$T/beamline/fast_dp_1" && cp "$P/XDS.INP" "$T/beamline/fast_dp_1/XDS.INP"
p "/api/batch/xdsinp-search" "{\"datasets\": $DS, \"roots\": [\"$T/beamline\"], \"keywords\": [\"fast_dp\", \"processing\", \"autoproc\"]}" '"keyword": "fast_dp"'
check "AutoPilot: the XDS.INP search matches the real frames (template and header)" "grep -q '\"state\": \"imported\"' $T/out.json && grep -q '\"header_checked\": true' $T/out.json" "$(head -c 400 $T/out.json)"
DS=$("$PY" -c 'import json,sys; d=json.loads(sys.argv[1]); d[0]["xdsinp"]=sys.argv[2]; print(json.dumps(d))' "$DS" "$T/beamline/fast_dp_1/XDS.INP" 2>/dev/null)
DS1=$("$PY" -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])[0]))' "$DS" 2>/dev/null)
p "/api/batch/xdsinp-preview" "{\"path\": \"$T/beamline/fast_dp_1/XDS.INP\", \"dataset\": $DS1}" 'Imported by CrystalPilot'
p "/api/batch/create" "{\"name\": \"sweep batch\", \"datasets\": $DS, \"strategy\": {\"optimize\": \"never\", \"dcc_half\": \"off\", \"autoindex_tier\": \"off\"}, \"search\": {\"keywords\": [\"fast_dp\"]}}" '"items"'
BID=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$T/out.json" 2>/dev/null)
BPROJ=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["items"][0]["project"])' "$T/out.json" 2>/dev/null)
g "/api/batch/list" "$BID"
p "/api/batch/start" "{\"id\": \"$BID\"}" 'started'
sleep 8
g "/api/batch?id=$BID" '"active": true'
p "/api/batch/skip" "{\"id\": \"$BID\"}" '"running"'
p "/api/batch/stop" "{\"id\": \"$BID\"}" '"running"'
for i in $(seq 1 60); do c -o "$T/out.json" "$U/api/batch?id=$BID"; grep -q '"active": false' "$T/out.json" && break; sleep 1; done
check "batch: stopping ends the batch and the data set" "grep -q '\"active\": false' $T/out.json && grep -qE '\"status\": \"(stopped|skipped)\"' $T/out.json" "$(head -c 400 $T/out.json)"
check "AutoPilot: the chosen beamline XDS.INP was imported into the project" "grep -q 'Imported by CrystalPilot' $T/projects/$BPROJ/XDS.INP && grep -q NAME_TEMPLATE_OF_DATA_FRAMES $T/projects/$BPROJ/XDS.INP" "$(head -c 300 $T/projects/$BPROJ/XDS.INP 2>/dev/null | tr '\n' ' ')"
TPL=$(grep -m1 '^NAME_TEMPLATE_OF_DATA_FRAMES' "$T/projects/$BPROJ/XDS.INP" 2>/dev/null | cut -d= -f2- | sed 's/^ *//')
check "AutoPilot: an image folder with blanks is reached through a link XDS can read" "[ -L $T/projects/$BPROJ/frames ] && echo \"$TPL\" | grep -q '/frames/' && ! echo \"$TPL\" | grep -q ' '" "template=[$TPL]"
g "/api/batch/log?id=$BID&project=$BPROJ" '"log"'
C=$(c -o /dev/null -w '%{http_code}' "$U/api/batch/log?id=$BID&project=real")
check "GET  /api/batch/log refuses a project that is not in the batch" "[ $C = 400 ]" "code=$C"
p "/api/batch/merge-plan" "{\"id\": \"$BID\", \"projects\": [\"real\"]}" '"xscale_inp"'
check "batch: the merge preview reads the real project's reflection file" "grep -q 'INPUT_FILE= inputs/01_real.HKL' $T/out.json" "$(head -c 400 $T/out.json)"
C=$(c -o "$T/out.json" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d "{\"id\": \"$BID\", \"projects\": [\"real\"]}" "$U/api/batch/merge")
check "POST /api/batch/merge refuses fewer than two data sets" "[ $C = 400 ] && grep -q 'at least two' $T/out.json" "code=$C $(head -c 200 $T/out.json)"
# ── a problem report (nothing is sent: a zip and a mail text) ─────────────
p "/api/bug-report" '{"description": "sweep: IDXREF fails", "project": "real", "include_project": true, "page_errors": ["TypeError: sweep"]}' '"mail_body"'
REPORT=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/out.json" 2>/dev/null)
C=$(c -o "$T/report.zip" -w '%{http_code}' "$U/api/bug-report?name=$(enc "$REPORT")")
check "GET  /api/bug-report serves the report" "[ $C = 200 ] && \"$PY\" -c 'import sys,zipfile; n=zipfile.ZipFile(sys.argv[1]).namelist(); sys.exit(0 if \"REPORT.txt\" in n and \"project/XDS.INP\" in n else 1)' $T/report.zip" "code=$C"
check "problem report: the API token is not in it" "! \"$PY\" -c 'import sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); sys.exit(0 if any(sys.argv[2] in z.read(n).decode(\"utf-8\",\"replace\") for n in z.namelist()) else 1)' $T/report.zip \"$TOK\"" "token found in the report"
C=$(c -o /dev/null -w '%{http_code}' "$U/api/bug-report?name=..%2F..%2Fetc%2Fpasswd")
check "GET  /api/bug-report refuses a name it did not write" "[ $C = 400 ]" "code=$C"
# ── export the project, and the log file ────────────────────────────────────
p "/api/export" '{"project": "real", "reflections": false}' '"entries"'
EXPORT=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$T/out.json" 2>/dev/null)
check "export: the zip is on disk" "[ -s $P/$EXPORT ]" "$EXPORT $(ls -l $P/$EXPORT 2>/dev/null | awk '{print $5}')"
C=$(c -o "$T/export.zip" -w '%{http_code}' "$U/api/export?project=real&name=$(enc "$EXPORT")")
check "GET  /api/export serves the zip" "[ $C = 200 ] && \"$PY\" -c 'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).testzip()' $T/export.zip" "code=$C"
check "export: the archive holds the logs but not the frames" "\"$PY\" -c 'import sys,zipfile; n=[x.split(\"/\")[-1] for x in zipfile.ZipFile(sys.argv[1]).namelist()]; sys.exit(0 if (\"CORRECT.LP\" in n and \"README.txt\" in n and not [f for f in n if f.endswith(\"-CORRECTIONS.cbf\") or f.endswith(\".h5\")]) else 1)' $T/export.zip" "$("$PY" -c 'import sys,zipfile; print(sorted(x.split("/")[-1] for x in zipfile.ZipFile(sys.argv[1]).namelist())[:14])' "$T/export.zip" 2>/dev/null)"
C=$(c -o /dev/null -w '%{http_code}' "$U/api/export?project=real&name=..%2F..%2Fetc%2Fpasswd")
check "GET  /api/export refuses a name that is not this project's" "[ $C = 400 ]" "code=$C"
LOGF="$T/projects/logs/crystalpilot.log"
check "log file: written in the projects folder" "[ -s $LOGF ]" "$(ls -l $LOGF 2>/dev/null)"
check "log file: the API token is not in it" "! grep -q -- \"$TOK\" $LOGF" "$(grep -o 'API token: [^ ]*' $LOGF | head -1)"
# ── run folders ─────────────────────────────────────────────────────────────
p "/api/run-folder" "{\"project_name\": \"real\", \"folder\": \"$P/sub1\"}" '"path"'
p "/api/run-folder/list" "{\"project_name\": \"real\", \"base_folder\": \"$P\"}" 'next_num'
p "/api/xscale-run-folder" '{"project_name": "real"}' 'folder_name'
check "run-folder copied XDS.INP into the sub folder" "[ -f $P/sub1/XDS.INP ]" "$(ls $P/sub1)"
# ── auto-indexing (real COLSPOT/IDXREF trials, quick tier) ──────────────────
if [ "${CP_SKIP_RERUNS:-0}" != 1 ]; then
t0=$(date +%s); stream ai "/api/autoindex/stream?project=real&tier=quick" 1500; echo "   auto-indexing quick tier took $(( $(date +%s) - t0 )) s"
check "auto-indexing quick tier finished" "grep -q 'event: ai_done' $T/ai.log" "$(tail -c 400 $T/ai.log | tr '\n' ' ')"
g "/api/projects/real/autoindex-cached" 'has_results'
fi
p "/api/autoindex/stop" '{}' 'message'
p "/api/autopilot/stop" '{}' 'message'
p "/api/stop" '{}' 'stopped'
# ── AutoPilot: the automated pipeline with retries, on the same 60-frame XDS.INP
# (CP_SKIP_AUTOPILOT=1 to leave it out).  The template mode would generate an
# XDS.INP for all 1800 frames, so the existing subset file is used instead.
if [ "${CP_SKIP_AUTOPILOT:-0}" != 1 ]; then
    t0=$(date +%s); stream ap "/api/autopilot/stream?project=real&criterion=isig2&friedel=TRUE&${CP_AUTOPILOT_OPTS:-optimize=1&dcc_half=1}" 7200; echo "   AutoPilot took $(( $(date +%s) - t0 )) s"
    check "AutoPilot: finished (ap_done)" "grep -q 'event: ap_done' $T/ap.log" "$(tail -c 400 $T/ap.log | tr '\n' ' ')"
    check "AutoPilot: reports success" "grep -A1 'event: ap_done' $T/ap.log | grep -q '\"status\": \"\(success\|completed\|done\)\"'" "$(grep -A1 'event: ap_done' $T/ap.log | tail -1 | cut -c1-300)"
    check "AutoPilot: ran XDS, XSCALE and produced results" "grep -q 'ap_phase' $T/ap.log && [ -f $P/AUTOPILOT_RESULTS.json ]" "$(ls $P | tr '\n' ' ')"
    # a success must rest on THIS run's CORRECT.LP - not on an old one, and not on none (v344 left only CORRECT.LP.previous_attempt)
    check "AutoPilot: left a fresh CORRECT.LP in the project" "[ -f $P/CORRECT.LP ] && [ $(stat -c %Y $P/CORRECT.LP) -ge $t0 ]" "$(ls $P | grep -i correct | tr '\n' ' ') ap_done: $(grep -A1 'event: ap_done' $T/ap.log | tail -1 | cut -c1-200)"
    C=$(c -o "$T/out.json" -w '%{http_code}' "$U/api/projects/real/autopilot-cached"); check "AutoPilot: cached results available" "[ $C = 200 ] && grep -q '\"has_results\": true' $T/out.json" "$(head -c 300 $T/out.json)"
    g "/api/autopilot/status?project=real" '"has_results": true'
fi
# ── auto import: the generated XDS.INP must carry values read from the frame header ─
C=$(c -o "$T/out.json" -w '%{http_code}' "$U/api/projects/real/generate-xdsinp")
check "auto import: generate-xdsinp read the real master header (wavelength, detector size, distance)" "[ $C = 200 ] && grep -q 'X-RAY_WAVELENGTH= 0.9' $T/out.json && grep -q 'NX= 4150' $T/out.json && grep -q 'DETECTOR_DISTANCE= ' $T/out.json && grep -q 'OSCILLATION_RANGE= 0.2' $T/out.json" "code=$C $(head -c 400 $T/out.json | tr '\n' ' ')"
# ── project lifecycle ───────────────────────────────────────────────────────
p "/api/projects" '{"name": "todelete", "description": "", "data_path": ""}' '"name"'
C=$(c -o "$T/out.json" -w '%{http_code}' -X DELETE "$U/api/projects/todelete?files=true"); check "DELETE /api/projects/<name>" "[ $C = 200 ] && [ ! -d $T/projects/todelete ]" "code=$C"
# ── first Save Parameters in a project without XDS.INP (0.6.7: the file held only the
#    form fields, no detector axes, and XYCORR stopped with INCORRECT DETECTOR SPECIFICATION)
for q in inpbase inpbare; do cj -X POST "$U/api/projects" -d "{\"name\": \"$q\", \"description\": \"\", \"data_path\": \"\"}" >/dev/null; done
BODY=$("$PY" -c 'import json,sys; print(json.dumps({"base": open(sys.argv[1]).read(), "params": {"NX": "4150", "LIB": "__commented__"}}))' "$P/XDS.INP")
C=$(cj -o "$T/out.json" -w '%{http_code}' -X POST "$U/api/projects/inpbase/xdsinp/params" -d "$BODY")
check "Save Parameters after 'Load from other XDS.INP' in a new project keeps that file's geometry" "[ $C = 200 ] && grep -q '^ *DIRECTION_OF_DETECTOR_X-AXIS=' $T/projects/inpbase/XDS.INP && grep -q '^ *DIRECTION_OF_DETECTOR_Y-AXIS=' $T/projects/inpbase/XDS.INP && grep -q '^ *ROTATION_AXIS=' $T/projects/inpbase/XDS.INP" "code=$C $(grep -E 'DIRECTION|ROTATION' $T/projects/inpbase/XDS.INP | tr '\n' ' ')"
C=$(cj -o "$T/out.json" -w '%{http_code}' -X POST "$U/api/projects/inpbare/xdsinp/params" -d "{\"params\": {\"NX\": \"4150\", \"NY\": \"4371\", \"QX\": \"0.075\", \"QY\": \"0.075\"}}")
check "Save Parameters typed into a new project writes the standard detector axes" "[ $C = 200 ] && grep -q '^DIRECTION_OF_DETECTOR_X-AXIS= 1.0 0.0 0.0' $T/projects/inpbare/XDS.INP && grep -q '^DIRECTION_OF_DETECTOR_Y-AXIS= 0.0 1.0 0.0' $T/projects/inpbare/XDS.INP" "code=$C $(head -c 300 $T/projects/inpbare/XDS.INP | tr '\n' ' ')"
if [ -n "$CP_REAL_XDS" ] && [ -x "$XDS_REAL/xds" ]; then
    (cd $T/projects/inpbase && sed -i 's/^ *JOB=.*/JOB= XYCORR/' XDS.INP && timeout 60 "$XDS_REAL/xds" > xycorr.out 2>&1)
    check "real XDS: XYCORR runs on that saved XDS.INP (no INCORRECT DETECTOR SPECIFICATION)" "[ -s $T/projects/inpbase/XYCORR.LP ] && ! grep -q '!!! ERROR' $T/projects/inpbase/xycorr.out" "$(grep '!!!' $T/projects/inpbase/xycorr.out | head -2)"
fi
for q in inpbase inpbare; do c -X DELETE "$U/api/projects/$q?files=true" >/dev/null; done
# ── resolution cut-off in a project without XSCALE.INP (0.6.7: INCLUDE_RESOLUTION_RANGE was
#    dropped - no INPUT_FILE to put it under - and XSCALE ran at full resolution)
cj -X POST "$U/api/projects" -d '{"name": "xsnoinp", "description": "", "data_path": ""}' >/dev/null
HKLSRC=$(ls "$P/XDS_ASCII.HKL" "$P"/*/XDS_ASCII.HKL 2>/dev/null | head -1)
if [ -n "$HKLSRC" ]; then
    cp "$HKLSRC" "$T/projects/xsnoinp/XDS_ASCII.HKL"
    C=$(cj -o "$T/out.json" -w '%{http_code}' -X POST "$U/api/projects/xsnoinp/xscaleinp/params" -d '{"params": {"INCLUDE_RESOLUTION_RANGE": "999 2.50", "RESOLUTION_SHELLS": "4.0 3.0 2.5"}}')
    check "XSCALE cut-off saved in a project without XSCALE.INP keeps INCLUDE_RESOLUTION_RANGE under an INPUT_FILE" "[ $C = 200 ] && grep -A3 '^ *INPUT_FILE= .*XDS_ASCII.HKL' $T/projects/xsnoinp/XSCALE.INP | grep -q 'INCLUDE_RESOLUTION_RANGE= *999 2.50'" "code=$C $(tr '\n' '|' < $T/projects/xsnoinp/XSCALE.INP)"
fi
c -X DELETE "$U/api/projects/xsnoinp?files=true" >/dev/null
