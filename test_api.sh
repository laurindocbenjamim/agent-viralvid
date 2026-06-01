#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# ViralVid AI Clipper – API Test Script
# Tests: session creation, options, job submit, status polling
# ============================================================

BASE_URL="${1:-http://127.0.0.1:8000}"
COOKIE_JAR=$(mktemp)
VERBOSE=false

usage() {
  echo "Usage: $0 [BASE_URL]"
  echo "  BASE_URL  Server URL (default: http://127.0.0.1:8000)"
  exit 1
}

info()  { echo -e "\033[36m[INFO]\033[0m $*"; }
ok()    { echo -e "\033[32m[PASS]\033[0m $*"; }
fail()  { echo -e "\033[31m[FAIL]\033[0m $*"; }
warn()  { echo -e "\033[33m[WARN]\033[0m $*"; }

# Cleanup
trap 'rm -f "$COOKIE_JAR"' EXIT

# -----------------------------------------------------------
# 1. Health check – options endpoint
# -----------------------------------------------------------
info "1. Checking /api/clipper/options ..."
OPTIONS=$(curl -sf "$BASE_URL/api/clipper/options") || {
  fail "Server not reachable at $BASE_URL — is it running?"
  info "Start it with: cd $(dirname "$0") && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
  exit 1
}
echo "$OPTIONS" | python3 -c "
import json,sys; d=json.load(sys.stdin)
required = ['clip_objectives','target_durations','subtitle_styles','subtitle_positions','crop_modes']
for k in required:
    assert k in d, f'Missing key: {k}'
print('  objectives:', d['clip_objectives'])
print('  durations:', d['target_durations'])
print('  styles:',    d['subtitle_styles'])
print('  positions:', d['subtitle_positions'])
print('  crops:',     d['crop_modes'])
"
ok "Options endpoint OK"

# -----------------------------------------------------------
# 2. Session creation
# -----------------------------------------------------------
info "2. Creating anonymous session..."
SESSION_RESP=$(curl -sf -c "$COOKIE_JAR" -X POST "$BASE_URL/api/auth/session") || {
  fail "Session creation failed"; exit 1
}
SESSION_ID=$(echo "$SESSION_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('session_id','?'))")
ok "Session created: $SESSION_ID"

# -----------------------------------------------------------
# 3. Submit a valid job
# -----------------------------------------------------------
info "3. Submitting clipping job for https://youtu.be/vfu2zKpQjfE ..."
SUBMIT_RESP=$(curl -sf -b "$COOKIE_JAR" -X POST "$BASE_URL/api/clipper/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "video_source": "https://youtu.be/i5UJ3ugs0dY",
    "video_language": "pt-BR",  
    "clip_objective": "Viral/Engraçado",
    "target_duration": "15-30",
    "max_clips": 3,
    "subtitle_style": "Minimalista",
    "subtitle_position": "bottom",
    "crop_mode": "center"
  }') || { fail "Job submission failed"; exit 1; }


TASK_ID=$(echo "$SUBMIT_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['task_id'])")
STATUS=$(echo "$SUBMIT_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
ok "Job submitted — task_id: $TASK_ID, initial status: $STATUS"

# -----------------------------------------------------------
# 4. Poll until completion (max 5 minutes)
# -----------------------------------------------------------
info "4. Polling status (timeout: 5 min)..."
POLL_INTERVAL=5
MAX_POLLS=$((300 / POLL_INTERVAL))
COMPLETED=false

for i in $(seq 1 $MAX_POLLS); do
  sleep $POLL_INTERVAL
  POLL_RESP=$(curl -sf "$BASE_URL/api/clipper/status/$TASK_ID" 2>/dev/null || echo '{}')
  CURRENT_STATUS=$(echo "$POLL_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null)
  echo "  [poll $i] status: $CURRENT_STATUS"

  if [ "$CURRENT_STATUS" = "Concluido" ]; then
    COMPLETED=true
    CLIP_COUNT=$(echo "$POLL_RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('clips',[])))" 2>/dev/null)
    ok "Pipeline completed! Generated $CLIP_COUNT clip(s)."
    echo ""
    echo "$POLL_RESP" | python3 -m json.tool 2>/dev/null
    break
  fi

  if echo "$CURRENT_STATUS" | grep -q "^Erro"; then
    fail "Pipeline error: $CURRENT_STATUS"
    echo ""
    echo "$POLL_RESP" | python3 -m json.tool 2>/dev/null
    exit 1
  fi
done

if [ "$COMPLETED" = false ]; then
  fail "Timed out waiting for pipeline to complete (> 5 min)."
  info "Check server logs for details."
  exit 1
fi

# -----------------------------------------------------------
# 5. Test error cases
# -----------------------------------------------------------
info ""
info "5. Testing error cases..."

# 5a. Submit without cookie → 401
info "  5a. Submit without cookie..."
NOCOOKIE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/clipper/submit" \
  -H "Content-Type: application/json" \
  -d '{"video_source":"https://youtu.be/test","video_language":"en-US"}')
if [ "$NOCOOKIE" = "401" ]; then
  ok "     Unauthenticated request correctly returned 401"
else
  fail "   Expected 401, got $NOCOOKIE"
fi

# 5b. Invalid payload → 422
info "  5b. Submit with invalid objective..."
INVALID=$(curl -s -b "$COOKIE_JAR" -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/clipper/submit" \
  -H "Content-Type: application/json" \
  -d '{"video_source":"https://youtu.be/test","video_language":"en-US","clip_objective":"INVALID"}')
if [ "$INVALID" = "422" ]; then
  ok "     Invalid input correctly returned 422"
else
  fail "   Expected 422, got $INVALID"
fi

# 5c. Poll nonexistent task → 404
info "  5c. Poll nonexistent task..."
NOTFOUND=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/clipper/status/nonexistent-task-id")
if [ "$NOTFOUND" = "404" ]; then
  ok "     Nonexistent task correctly returned 404"
else
  fail "   Expected 404, got $NOTFOUND"
fi

# -----------------------------------------------------------
# Summary
# -----------------------------------------------------------
echo ""
echo "═══════════════════════════════════════════════════════"
ok " ALL TESTS PASSED"
echo " Server: $BASE_URL"
echo " Task:   $TASK_ID"
echo "═══════════════════════════════════════════════════════"
echo ""
info "To view the frontend, open: $BASE_URL/"
info "Clips are served at:      $BASE_URL/clips/$TASK_ID/"
echo ""
