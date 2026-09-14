#!/bin/bash
# CrystalPilot regression battery - API / end-to-end level (Linux or WSL).
#
#   APP=/path/to/xds-gui-vNNN.py bash tests/api/api_tests.sh
#   CP_REAL_XSCALE=1 ...   also run the real xscale_par on a COPY of the
#                          project named in CP_REAL_PROJECT (default 'test')
#                          from $HOME/crystalpilot_projects - the original is
#                          never modified.
#
# Starts throwaway servers on ports 8078/8079/8081 with a fake xds_par (a
# shell script that forks a child, so stop/timeout must kill a whole tree).
# Every check prints ok/FAIL; the exit code is the number of failures.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
FILES=$(cd "$HERE/../.." && pwd)
APP=${APP:-$(ls -1 "$FILES"/xds-gui-v*.py 2>/dev/null | sort -t v -k3 -n | tail -1)}
[ -f "$APP" ] || { echo "APP not found: $APP"; exit 99; }
PY=${PY:-$HOME/.crystalpilot/venv/bin/python}; [ -x "$PY" ] || PY=python3
XDS_REAL=${XDS_REAL:-$HOME/.crystalpilot/xds}
echo "build: $(basename "$APP")   python: $PY"
pass=0; fail=0
ok()   { echo "ok   $1"; pass=$((pass+1)); }
bad()  { echo "FAIL $1"; fail=$((fail+1)); }
check(){ if eval "$2"; then ok "$1"; else bad "$1 -- $3"; fi; }
CURL=$(command -v curl)
start_server() {  # $1=port $2=token $3=projects $4=xds $5=settings-json
    ( cd "$(dirname "$3")" && XDS_GUI_SETTINGS="$5" XDS_GUI_TOKEN="$2" HDF5_USE_FILE_LOCKING=FALSE \
      nohup "$PY" -u "$APP" --port "$1" --host 127.0.0.1 --projects-dir "$3" --xds-path "$4" > "$(dirname "$3")/server.log" 2>&1 & echo $! > "$(dirname "$3")/server.pid" )
    for i in $(seq 1 40); do "$CURL" -fs "http://127.0.0.1:$1/health" >/dev/null 2>&1 && return 0; sleep 0.5; done
    return 1
}
stop_server() { kill "$(cat "$1/server.pid" 2>/dev/null)" 2>/dev/null; sleep 1; pkill -f "$(basename "$APP") --port $2" 2>/dev/null; }
ensure_drive() {  # $1 = a path; under WSL, mount the Windows drive it lives on if WSL was restarted
    case "$1" in /mnt/[a-z]/*) ;; *) return 0 ;; esac
    local mp; mp=$(echo "$1" | cut -d/ -f1-3)
    mountpoint -q "$mp" && return 0
    local letter; letter=$(basename "$mp" | tr 'a-z' 'A-Z')
    mkdir -p "$mp" 2>/dev/null
    if timeout 20 mount -t drvfs "$letter:" "$mp" -o noatime 2>/dev/null; then echo "   mounted $letter: at $mp"; else echo "   could not mount $letter: at $mp"; fi
}

# ══════════════════════════════════════════════════════════════════════════
if [ "${CP_SKIP_BASIC:-0}" != 1 ]; then   # CP_SKIP_BASIC=1: only the real-program sections
echo "=== 1. robustness (fake xds_par, port 8078)"
T=/tmp/cp_api_a; PORT=8078; U="http://127.0.0.1:$PORT"; TOK=tA
rm -rf "$T"; mkdir -p "$T/projects" "$T/xds"
cat > "$T/xds/xds_par" <<'EOF'
#!/bin/sh
step=$(grep -m1 '^JOB=' XDS.INP | sed 's/JOB= *//')
echo "fake xds_par step=$step pid=$$"
( sleep 120 ) & child=$!
echo "child=$child"
echo " ***** $step ***** " > "$step.LP"
wait $child
EOF
chmod +x "$T/xds/xds_par"; touch "$T/xds/xscale_par" "$T/xds/xdsconv"; chmod +x "$T/xds/xscale_par" "$T/xds/xdsconv"
echo '{"step_timeout": 8}' > "$T/settings.json"
c() { "$CURL" -s -H "X-CrystalPilot-Token: $TOK" "$@"; }
if start_server $PORT $TOK "$T/projects" "$T/xds" "$T/settings.json"; then ok "server up"; else bad "server up -- $(tail -3 $T/server.log)"; fi
c -X POST "$U/api/projects" -H 'Content-Type: application/json' -d '{"name":"my proj","description":"","data_path":""}' >/dev/null
printf 'JOB= XYCORR\nNAME_TEMPLATE_OF_DATA_FRAMES= /tmp/x_????.cbf\n' > "$T/projects/my proj/XDS.INP"
R=$(c "$U/api/projects/my%20proj/xdsinp"); check "encoded project name resolves" "echo '$R' | grep -q NAME_TEMPLATE" "$R"
C=$(c -o /tmp/cp_api_out --path-as-is -w '%{http_code}' "$U/api/projects/../lp/CORRECT"); check "traversal -> 400 JSON" "[ $C = 400 ] && grep -q error /tmp/cp_api_out" "code=$C"
C=$(c -o /dev/null -w '%{http_code}' "$U/api/stream?project=my%20proj&stop_at=NOPE"); check "unknown stop_at -> 400" "[ $C = 400 ]" "code=$C"
C=$(c -o /dev/null -w '%{http_code}' "$U/api/frame?path=/tmp/x.cbf&frame=abc"); check "bad frame param -> 400/503" "[ $C = 400 ] || [ $C = 503 ]" "code=$C"
mkdir -p "$T/projects/broken"; echo '{ not json' > "$T/projects/broken/metadata.json"
R=$(c "$U/api/projects"); check "corrupt metadata skipped" "echo '$R' | grep -q 'my proj'" "$R"
printf ' ***** CORRECT ***** \n UNIT CELL \xe5 test\n' > "$T/projects/my proj/CORRECT.LP"
C=$(c -o /tmp/cp_api_out -w '%{http_code}' "$U/api/projects/my%20proj/lp/CORRECT"); check "LP with non-UTF8 byte served" "[ $C = 200 ]" "code=$C"
c -N "$U/api/stream?project=my%20proj&step=XYCORR" > "$T/sse1.log" 2>&1 &
sleep 2; CH=$(grep -o 'child=[0-9]*' "$T/sse1.log" | head -1 | cut -d= -f2)
check "fake xds started, child known" "[ -n \"$CH\" ] && kill -0 $CH 2>/dev/null" "$(head -3 $T/sse1.log)"
R=$(c -X POST "$U/api/stop" -H 'Content-Type: application/json' -d '{"project_name":"my proj"}'); sleep 2
check "stop reports one process" "echo '$R' | grep -q '\"stopped\": 1'" "$R"
check "stop killed the child too" "! kill -0 $CH 2>/dev/null && [ -z \"$(pgrep -f 'sleep 120')\" ]" "$(pgrep -af 'sleep 120')"
timeout 40 "$CURL" -s -N -H "X-CrystalPilot-Token: $TOK" "$U/api/stream?project=my%20proj&step=INIT" > "$T/sse2.log" 2>&1
check "timeout reported (step_timeout=8)" "grep -q 'time limit' $T/sse2.log && grep -q '\"status\": \"timeout\"' $T/sse2.log" "$(tail -3 $T/sse2.log)"
sleep 1; check "no orphan after timeout" "[ -z \"$(pgrep -f 'sleep 120')\" ]" "$(pgrep -af 'sleep 120')"
c -N "$U/api/stream?project=my%20proj&step=COLSPOT" > "$T/sse3.log" 2>&1 &
sleep 1.5; timeout 10 "$CURL" -s -N -H "X-CrystalPilot-Token: $TOK" "$U/api/stream?project=my%20proj&step=COLSPOT" > "$T/sse4.log" 2>&1
check "second run in same folder refused" "grep -q 'already running' $T/sse4.log" "$(head -2 $T/sse4.log)"
c -X POST "$U/api/stop" -H 'Content-Type: application/json' -d '{}' >/dev/null; sleep 2
R=$(c -X POST "$U/api/run" -H 'Content-Type: application/json' -d '{}'); check "/api/run without project -> JSON error" "echo '$R' | grep -q error" "$R"
# XSCALE.INP: 'Save new' with empty inputs must produce a valid file with the project's HKL
mkdir -p "$T/projects/my proj/run1"; printf '!FORMAT=XDS_ASCII\n' > "$T/projects/my proj/run1/XDS_ASCII.HKL"
"$PY" - "$T/projects/my proj/metadata.json" "$T/projects/my proj/run1" <<'EOF'
import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["last_run_folder"]=sys.argv[2]; json.dump(d, open(p,"w"))
EOF
c -X POST "$U/api/projects/my%20proj/xscaleinp/params" -H 'Content-Type: application/json' -d '{"fresh": true, "params": {"SPACE_GROUP_NUMBER": "20", "UNIT_CELL_CONSTANTS": "98 119 161 90 90 90", "INCLUDE_RESOLUTION_RANGE": "80 1.75", "RESOLUTION_SHELLS": "7 5 4", "STRICT_ABSORPTION_CORRECTION": "FALSE", "OUTPUT_FILE": "merged.ahkl", "FRIEDEL'"'"'S_LAW": "TRUE", "MERGE": "FALSE", "INPUT_FILE": []}}' >/dev/null
F="$T/projects/my proj/XSCALE.INP"
check "xscale 'Save new': INPUT_FILE resolved to the run folder" "grep -q 'INPUT_FILE= .*/run1/XDS_ASCII.HKL' \"$F\"" "$(cat "$F")"
check "xscale 'Save new': globals before OUTPUT_FILE" "[ \$(grep -n '^SPACE_GROUP_NUMBER' \"$F\" | cut -d: -f1) -lt \$(grep -n '^OUTPUT_FILE' \"$F\" | cut -d: -f1) ]" "$(cat "$F")"
R=$(c "$U/api/xscale-detect-hkl?project=my%20proj"); check "detect-hkl lists the run-folder HKL" "echo '$R' | grep -q run1" "$R"
stop_server "$T" $PORT; pkill -f 'sleep 120' 2>/dev/null; rm -rf "$T"

# ══════════════════════════════════════════════════════════════════════════
echo "=== 2. access control (port 8079)"
T=/tmp/cp_api_b; PORT=8079; U="http://127.0.0.1:$PORT"; TOK=testtoken123
rm -rf "$T"; mkdir -p "$T/projects" "$T/xds"
if start_server $PORT $TOK "$T/projects" "$T/xds" "$T/settings.json"; then ok "server up"; else bad "server up -- $(tail -3 $T/server.log)"; fi
check "binds 127.0.0.1 only" "ss -ltn | grep ':$PORT ' | grep -q '127.0.0.1:$PORT'" "$(ss -ltn | grep ":$PORT ")"
C=$("$CURL" -s -o /tmp/cp_api_out -w '%{http_code}' "$U/api/projects"); check "no token -> 403" "[ $C = 403 ]" "code=$C"
C=$("$CURL" -s -o /dev/null -w '%{http_code}' -H "X-CrystalPilot-Token: $TOK" "$U/api/projects"); check "header token -> 200" "[ $C = 200 ]" "code=$C"
C=$("$CURL" -s -o /dev/null -w '%{http_code}' "$U/api/projects?token=$TOK"); check "query token -> 200" "[ $C = 200 ]" "code=$C"
C=$("$CURL" -s -o /dev/null -w '%{http_code}' -H 'X-CrystalPilot-Token: wrong' "$U/api/projects"); check "wrong token -> 403" "[ $C = 403 ]" "code=$C"
"$CURL" -s -c "$T/jar" -o /dev/null "$U/"
check "page sets the port-specific cookie" "grep -q cp_token_$PORT $T/jar" "$(cat $T/jar)"
C=$("$CURL" -s -b "$T/jar" -o /dev/null -w '%{http_code}' "$U/api/projects"); check "cookie -> 200" "[ $C = 200 ]" "code=$C"
# as an EventSource asks (the Accept header the standard requires), so the
# reason for a refusal comes back in the stream rather than as a bare 404
timeout 5 "$CURL" -s -N -b "$T/jar" -H 'Accept: text/event-stream' "$U/api/stream?project=nope&step=XYCORR" > "$T/sse.log" 2>&1
check "SSE accepts the cookie" "grep -q 'event:' $T/sse.log" "$(head -2 $T/sse.log)"
H=$("$CURL" -s -D - -o /dev/null -H 'Origin: http://evil.example' -H "X-CrystalPilot-Token: $TOK" "$U/api/projects"); check "no CORS on /api" "! echo \"$H\" | grep -qi access-control" "$H"
H=$("$CURL" -s -D - -o /dev/null "$U/health"); check "/health readable cross-origin (loading screen)" "echo \"$H\" | grep -qi 'access-control-allow-origin: \*'" "$H"
C=$("$CURL" -s -o /dev/null -w '%{http_code}' "$U/assets/logo.jpg"); check "assets open" "[ $C = 200 ]" "code=$C"
stop_server "$T" $PORT; rm -rf "$T"

# ══════════════════════════════════════════════════════════════════════════
if [ "${CP_REAL_XSCALE:-0}" = "1" ]; then
    echo "=== 3. real XSCALE on a copy of project '${CP_REAL_PROJECT:-test}' (port 8081)"
    SRC="$HOME/crystalpilot_projects/${CP_REAL_PROJECT:-test}"
    lrf=$(grep -o '"last_run_folder": "[^"]*"' "$SRC/metadata.json" 2>/dev/null | sed 's/.*: "//; s/"$//'); [ -n "$lrf" ] && ensure_drive "$lrf"
    if [ -f "$SRC/metadata.json" ] && [ -x "$XDS_REAL/xscale_par" ]; then
        T=/tmp/cp_api_c; PORT=8081; U="http://127.0.0.1:$PORT"; TOK=tC
        rm -rf "$T"; mkdir -p "$T/projects/p"; cp "$SRC/metadata.json" "$T/projects/p/"; [ -f "$SRC/XSCALE.INP" ] && cp "$SRC/XSCALE.INP" "$T/projects/p/"
        c() { "$CURL" -s -H "X-CrystalPilot-Token: $TOK" "$@"; }
        if start_server $PORT $TOK "$T/projects" "$XDS_REAL" "$T/settings.json"; then ok "server up"; else bad "server up -- $(tail -3 $T/server.log)"; fi
        c -X POST "$U/api/projects/p/xscaleinp/params" -H 'Content-Type: application/json' -d '{"fresh": true, "params": {"OUTPUT_FILE": "merged.ahkl", "FRIEDEL'"'"'S_LAW": "TRUE", "MERGE": "FALSE", "INPUT_FILE": []}}' >/dev/null
        check "real: XSCALE.INP has an INPUT_FILE" "grep -q 'INPUT_FILE= /' $T/projects/p/XSCALE.INP" "$(cat $T/projects/p/XSCALE.INP)"
        t0=$(date +%s); timeout 1200 "$CURL" -s -N -H "X-CrystalPilot-Token: $TOK" "$U/api/xscale/stream?project=p" > "$T/sse.log" 2>&1
        echo "   xscale took $(( $(date +%s) - t0 )) s"
        check "real: XSCALE completed" "grep -q '\"status\": \"completed\"' $T/sse.log" "$(grep -A1 step_done $T/sse.log | tail -1)"
        check "real: no error in XSCALE.LP" "! grep -q '!!! ERROR' $T/projects/p/XSCALE.LP" "$(grep -n ERROR $T/projects/p/XSCALE.LP | head -2)"
        check "real: merged.ahkl written" "[ -s $T/projects/p/merged.ahkl ]" "$(ls $T/projects/p)"
        stop_server "$T" $PORT; rm -rf "$T"
    else
        echo "   skipped: need $SRC/metadata.json and $XDS_REAL/xscale_par"
    fi
fi

fi  # CP_SKIP_BASIC

# ══════════════════════════════════════════════════════════════════════════
if [ "${CP_REAL_XDS:-0}" = "1" ]; then
    echo "=== 4. real chain on a frame subset: XDS -> XSCALE -> XDSCONV -> CCP4 -> gemmi -> XDSCC12 (port 8082)"
    SRCP="$HOME/crystalpilot_projects/${CP_REAL_PROJECT:-test}"
    SRCINP="$SRCP/XDS.INP"; [ -f "$SRCINP" ] || SRCINP="$FILES/tests/fixtures/XDS.INP"
    N=${CP_REAL_XDS_RANGE:-60}
    tmpl=$(grep -m1 '^NAME_TEMPLATE_OF_DATA_FRAMES' "$SRCINP" | sed 's/^[^=]*= *//; s/ *!.*//')
    fdir=$(dirname "$tmpl")
    ensure_drive "$fdir"
    if [ ! -d "$fdir" ] || [ ! -x "$XDS_REAL/xds_par" ]; then
        echo "   skipped: frames folder $fdir or $XDS_REAL/xds_par not reachable"
    else
        T=/tmp/cp_api_d; PORT=8082; U="http://127.0.0.1:$PORT"; TOK=tD
        rm -rf "$T"; mkdir -p "$T/projects"; echo '{}' > "$T/settings.json"
        c()  { "$CURL" -s -H "X-CrystalPilot-Token: $TOK" "$@"; }
        cj() { "$CURL" -s -H "X-CrystalPilot-Token: $TOK" -H 'Content-Type: application/json' "$@"; }
        stream() {  # $1=label $2=url-path-and-query $3=timeout -> writes $T/$1.log
            timeout "$3" "$CURL" -s -N -H "X-CrystalPilot-Token: $TOK" "$U$2" > "$T/$1.log" 2>&1
        }
        done_ok() { grep -q "\"step\": \"$2\", \"status\": \"completed\"" "$T/$1.log"; }
        explain() {  # what the program said: first log lines, then the error/step_done events
            { grep -h 'event: log' -A1 "$T/$1.log" | grep data: | head -12; grep -h 'error_msg\|step_done' -A1 "$T/$1.log" | grep data: | tail -2; } | cut -c1-300 | tr '\n' '|'
        }
        if start_server $PORT $TOK "$T/projects" "$XDS_REAL" "$T/settings.json"; then ok "server up"; else bad "server up -- $(tail -3 $T/server.log)"; fi
        # CCP4: the Windows bridge installed by the WSL setup, or a Linux CCP4 on PATH
        CCP4B=""
        [ -x "$HOME/.crystalpilot/ccp4win/pointless" ] && CCP4B="$HOME/.crystalpilot/ccp4win"
        [ -z "$CCP4B" ] && command -v pointless >/dev/null 2>&1 && CCP4B=$(dirname "$(command -v pointless)")
        if [ -n "$CCP4B" ]; then cj -X POST "$U/api/config" -d "{\"ccp4_bin\": \"$CCP4B\"}" >/dev/null; echo "   CCP4: $CCP4B"; else echo "   CCP4: none found - POINTLESS/AIMLESS/f2mtz checks skipped"; fi
        cj -X POST "$U/api/projects" -d '{"name":"real","description":"","data_path":""}' >/dev/null
        if [ -n "${CP_REAL_IMPORT:-}" ] && [ -f "$HOME/crystalpilot_projects/$CP_REAL_IMPORT/metadata.json" ]; then
            # Manual mode: start from a COMPLETE processing the user already did.  The
            # project's inputs and the XDS outputs of its last run are copied into the
            # test project (the original and its run folder are never written to).
            IMP="$HOME/crystalpilot_projects/$CP_REAL_IMPORT"
            IRF=$(grep -o '"last_run_folder": "[^"]*"' "$IMP/metadata.json" | sed 's/.*: "//; s/"$//'); [ -n "$IRF" ] && ensure_drive "$IRF"
            [ -d "$IRF" ] || IRF="$IMP"
            echo "   importing project '$CP_REAL_IMPORT' (XDS output from $IRF) ..."
            cp -f "$IMP"/*.INP "$T/projects/real/" 2>/dev/null
            for f in XSCALE.LP XSCALE.LP.prev1 XSCALE.LP.prev2 merged.ahkl; do [ -f "$IMP/$f" ] && cp -f "$IMP/$f" "$T/projects/real/$f"; done
            IMPORTED=1
            for f in XDS.INP XYCORR.LP INIT.LP COLSPOT.LP IDXREF.LP DEFPIX.LP INTEGRATE.LP CORRECT.LP CORRECT.LP.prev1 CORRECT.LP.prev2 IDXREF.LP.prev1 IDXREF.LP.prev2 XDS_ASCII.HKL INTEGRATE.HKL SPOT.XDS XPARM.XDS GXPARM.XDS BKGINIT.cbf BKGPIX.cbf ABS.cbf BLANK.cbf GAIN.cbf X-CORRECTIONS.cbf Y-CORRECTIONS.cbf; do
                [ -f "$IRF/$f" ] && cp -f "$IRF/$f" "$T/projects/real/$f"
            done
            "$PY" - "$T/projects/real/metadata.json" <<'EOF'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["last_run_folder"] = ""; d["last_xscale_folder"] = ""; d["last_xdsconv_folder"] = ""
d["completed_steps"] = ["XYCORR", "INIT", "COLSPOT", "IDXREF", "DEFPIX", "INTEGRATE", "CORRECT"]
json.dump(d, open(p, "w"), indent=2)
EOF
            check "import: CORRECT.LP, XDS_ASCII.HKL and XDS.INP present" "[ -s $T/projects/real/CORRECT.LP ] && [ -s $T/projects/real/XDS_ASCII.HKL ] && [ -s $T/projects/real/XDS.INP ]" "$(ls $T/projects/real | tr '\n' ' ')"
            printf 'event: step_done\ndata: {"step": "IDXREF", "status": "completed", "error": null}\n\nevent: step_done\ndata: {"step": "CORRECT", "status": "completed", "error": null}\n\n' > "$T/xds1.log"; cp "$T/xds1.log" "$T/xds2.log"
            R=$(c "$U/api/projects/real/metrics/CORRECT"); check "import: CORRECT metrics parse (full data set)" "echo '$R' | grep -q '\"unit_cell\"'" "$(echo "$R" | cut -c1-200)"
        else
        cp "$SRCINP" "$T/projects/real/XDS.INP"
        cj -X POST "$U/api/projects/real/xdsinp/params" -d "{\"params\": {\"DATA_RANGE\": [1, $N], \"SPOT_RANGE\": [[1, $N]], \"BACKGROUND_RANGE\": [1, 10]}}" >/dev/null
        check "real xds: subset ranges written by the editor" "grep -q \"^DATA_RANGE= 1 $N\" $T/projects/real/XDS.INP && [ \$(grep -c '^SPOT_RANGE' $T/projects/real/XDS.INP) = 1 ]" "$(grep RANGE $T/projects/real/XDS.INP)"
        echo "   frames: $tmpl  (1-$N)"
        t0=$(date +%s); stream xds1 "/api/stream?project=real&steps=XYCORR,INIT,COLSPOT,IDXREF" 1800; echo "   XYCORR..IDXREF took $(( $(date +%s) - t0 )) s"
        for s in XYCORR INIT COLSPOT IDXREF; do check "real xds: $s completed" "done_ok xds1 $s" "$(explain xds1)"; done
        if done_ok xds1 IDXREF; then
            R=$(c "$U/api/projects/real/metrics/IDXREF"); check "real xds: IDXREF metrics parsed" "echo '$R' | grep -q 'unit_cell\|lattice'" "$(echo "$R" | cut -c1-200)"
            t0=$(date +%s); stream xds2 "/api/stream?project=real&steps=DEFPIX,INTEGRATE,CORRECT" 1800; echo "   DEFPIX..CORRECT took $(( $(date +%s) - t0 )) s"
            for s in DEFPIX INTEGRATE CORRECT; do check "real xds: $s completed" "done_ok xds2 $s" "$(explain xds2)"; done
        fi
        fi
        if done_ok xds2 CORRECT 2>/dev/null; then
            R=$(c "$U/api/projects/real/metrics/CORRECT"); check "real xds: CORRECT metrics have a unit cell and statistics" "echo '$R' | grep -q '\"unit_cell\"' && echo '$R' | grep -q 'statistics'" "$(echo "$R" | cut -c1-200)"
            c -o "$T/lp.json" "$U/api/projects/real/lp/CORRECT"   # LP text contains quotes: compare via file, not eval
            check "real xds: LP viewer finds CORRECT.LP" "grep -q '\"source\": \"' $T/lp.json && grep -q 'STANDARD ERROR OF REFLECTION' $T/lp.json" "$(head -c 200 $T/lp.json)"
            R=$(c "$U/api/projects/real/matthews?mw=30000"); check "real xds: Matthews from CORRECT.LP" "echo '$R' | grep -q '\"results\"'" "$R"
            # XSCALE from the XSCALE tab's "Save new" with an empty input list
            if [ -n "${IMPORTED:-}" ] && [ -s "$T/projects/real/XSCALE.LP" ] && [ -s "$T/projects/real/merged.ahkl" ]; then
                echo "   XSCALE: using the imported XSCALE.INP / XSCALE.LP / merged.ahkl (not re-run)"
                printf 'event: step_done
data: {"step": "XSCALE", "status": "completed", "error": null}

' > "$T/xscale.log"
            else
            cj -X POST "$U/api/projects/real/xscaleinp/params" -d '{"fresh": true, "params": {"OUTPUT_FILE": "merged.ahkl", "FRIEDEL'"'"'S_LAW": "TRUE", "MERGE": "FALSE", "INPUT_FILE": []}}' >/dev/null
            t0=$(date +%s); stream xscale "/api/xscale/stream?project=real" 1200; echo "   XSCALE took $(( $(date +%s) - t0 )) s"
            fi
            check "real xscale: completed, merged.ahkl written" "done_ok xscale XSCALE && [ -s $T/projects/real/merged.ahkl ]" "$(explain xscale)"
            R=$(c "$U/api/projects/real/xscalelp"); check "real xscale: XSCALE.LP parsed" "echo '$R' | grep -q 'content\|statistics'" "$(echo "$R" | cut -c1-120)"
            # XDSCONV (+ f2mtz/cad when CCP4 is there)
            printf "INPUT_FILE= merged.ahkl\nOUTPUT_FILE= temp.hkl CCP4_I+F\nFRIEDEL'S_LAW= TRUE\nGENERATE_FRACTION_OF_TEST_REFLECTIONS= 0.05\n" > "$T/xdsconv.inp"
            cj -X POST "$U/api/projects/real/xdsconvinp" -d "{\"content\": $("$PY" -c 'import json,sys; print(json.dumps(open(sys.argv[1]).read()))' "$T/xdsconv.inp")}" >/dev/null
            t0=$(date +%s); stream xdsconv "/api/xdsconv/stream?project=real" 900; echo "   XDSCONV took $(( $(date +%s) - t0 )) s"
            check "real xdsconv: completed" "done_ok xdsconv XDSCONV" "$(explain xdsconv)"
            if [ -n "$CCP4B" ]; then
                check "real f2mtz+cad: MTZ created" "grep -q 'MTZ file created' $T/xdsconv.log" "$(explain xdsconv)"
                t0=$(date +%s); stream pointless "/api/pointless/stream?project=real" 900; echo "   POINTLESS took $(( $(date +%s) - t0 )) s"
                check "real pointless: completed" "done_ok pointless POINTLESS" "$(explain pointless)"
                R=$(c "$U/api/projects/real/pointless-cached"); check "real pointless: results cached/parsed" "echo '$R' | grep -q 'best_solution\|has_results'" "$(echo "$R" | cut -c1-160)"
                t0=$(date +%s); stream aimless "/api/aimless/stream?project=real" 1200; echo "   AIMLESS took $(( $(date +%s) - t0 )) s"
                check "real aimless: AIMLESS completed" "done_ok aimless AIMLESS" "$(explain aimless)"
                check "real aimless: CTRUNCATE completed" "done_ok aimless CTRUNCATE" "$(explain aimless)"
                R=$(c "$U/api/projects/real/aimless-cached"); check "real aimless: results cached" "echo '$R' | grep -q 'has_results\|overall'" "$(echo "$R" | cut -c1-160)"
            fi
            if "$PY" -c 'import gemmi' 2>/dev/null; then
                t0=$(date +%s); stream gemmi "/api/gemmi-mtz/stream?project=real&input_file=merged.ahkl" 900; echo "   gemmi MTZ took $(( $(date +%s) - t0 )) s"
                check "real gemmi: MTZ conversion completed" "grep -q '\"status\": \"completed\"' $T/gemmi.log" "$(explain gemmi)"
            else
                echo "   gemmi not installed in $PY - skipped"
            fi
            R=$(c "$U/api/xdscc12/check")
            if echo "$R" | grep -q '"found": true'; then
                t0=$(date +%s); stream xdscc12 "/api/xdscc12/stream?project=real" 900; echo "   XDSCC12 took $(( $(date +%s) - t0 )) s"
                check "real xdscc12: completed" "done_ok xdscc12 XDSCC12" "$(explain xdscc12)"
            else
                echo "   XDSCC12 not installed - skipped"
            fi
            R=$(c "$U/api/projects/real/locations"); check "real: locations report lists CORRECT.LP and XSCALE.LP" "echo '$R' | grep -q 'CORRECT.LP\": \"/' && echo '$R' | grep -q 'XSCALE.LP\": \"/'" "$(echo "$R" | cut -c1-300)"
            # Harvest real outputs as unit-test fixtures (only files not yet present)
            H="$FILES/tests/fixtures/real"; mkdir -p "$H"
            echo "   outputs in project: $(ls "$T/projects/real" | tr '\n' ' ')"
            for f in CORRECT.LP IDXREF.LP INTEGRATE.LP COLSPOT.LP INIT.LP XYCORR.LP DEFPIX.LP XSCALE.LP XSCALE.INP XDSCONV.LP XDSCONV.INP pointless.log pointless.xml aimless.log aimless.xml ctruncate.log XDS.INP; do
                [ -f "$T/projects/real/$f" ] && [ ! -f "$H/$f" ] && cp "$T/projects/real/$f" "$H/$f" && echo "   harvested fixture real/$f"
            done
            # Every remaining endpoint, on the same outputs
            if [ "${CP_SWEEP:-1}" = 1 ]; then . "$HERE/sweep.sh"; fi
        fi
        if [ "${CP_KEEP_SERVER:-0}" = 1 ]; then
            # The browser pass (tests/ui) drives this server; it creates $T/stop when done.
            case "$tmpl" in *.h5) UIMASTER=$(echo "$tmpl" | sed 's/_?*\.h5$/_master.h5/') ;; *) UIMASTER="" ;; esac
            echo "SERVER_READY port=$PORT token=$TOK dir=$T master=$UIMASTER"
            for i in $(seq 1 2400); do [ -f "$T/stop" ] && break; sleep 1; done
        fi
        stop_server "$T" $PORT; rm -rf "$T"
    fi
fi

echo "RESULT: $pass passed, $fail failed"
exit $fail
