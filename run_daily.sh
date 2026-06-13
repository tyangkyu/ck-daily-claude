#!/bin/bash
# run_daily.sh — AX Commerce Intelligence Daily Brief 실행 래퍼 (cron용)
# 매일 07:00 KST crontab에서 호출. Claude 앱/승인 불필요, 시스템에서 직접 실행.

set -u

PROJECT_DIR="/Users/kershaw/ck-daily-claude"
LOG="$PROJECT_DIR/run_daily.log"
LOCKFILE="/tmp/ck_daily_claude.lock"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"

cd "$PROJECT_DIR" || { echo "[$(date '+%F %T')] cd 실패" >> "$LOG"; exit 1; }

# ── 중복 실행 방지 ──────────────────────────────
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "[$(date '+%F %T')] 이미 실행 중 (PID $PID). 종료." >> "$LOG"
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# ── 로그 로테이션 (5MB 초과 시) ─────────────────
if [ -f "$LOG" ] && [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 5242880 ]; then
    mv "$LOG" "$LOG.$(date '+%Y%m%d%H%M%S').bak"
fi

RUN_DATE="$(date '+%Y-%m-%d')"
echo "======================================" >> "$LOG"
echo "[$(date '+%F %T')] 실행 시작 — date=$RUN_DATE" >> "$LOG"

# ── .env 로드 (SLACK/ANTHROPIC 키) ───────────────
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "[$(date '+%F %T')] 경고: .env 없음" >> "$LOG"
fi

if [ ! -x "$PYTHON_BIN" ]; then
    echo "[$(date '+%F %T')] 오류: Python 실행 파일 없음: $PYTHON_BIN" >> "$LOG"
    exit 1
fi

# ── 파이프라인 실행 ──────────────────────────────
"$PYTHON_BIN" scripts/daily_pipeline.py --date "$RUN_DATE" --mode send >> "$LOG" 2>&1
EXIT_CODE=$?

# ── 결과 확인 ────────────────────────────────────
STATUS=$("$PYTHON_BIN" -c "import json,sys; print(json.load(open('Reports/$RUN_DATE/run-log.json'))['status'])" 2>/dev/null || echo "unknown")
SLACK=$("$PYTHON_BIN" -c "import json; print(json.load(open('Reports/$RUN_DATE/slack-send-result.json'))['status'])" 2>/dev/null || echo "unknown")
echo "[$(date '+%F %T')] 완료 — exit=$EXIT_CODE pipeline=$STATUS slack=$SLACK" >> "$LOG"

exit $EXIT_CODE
