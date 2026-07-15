#!/usr/bin/env bash
# Background ComfyUI warmup after service stack is ready.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="${ROOT}/.run"
LOCK_FILE="/tmp/zfhs-wan-animate-warmup.lock"
LOG_FILE="${PID_DIR}/warmup.log"
PYTHON_BIN="${COMFY_PYTHON:-/root/miniconda3/bin/python}"

log() { echo "[run-warmup] $*"; }

if [[ "${SKIP_WARMUP:-0}" == "1" ]]; then
  log "SKIP_WARMUP=1, skip"
  exit 0
fi

mkdir -p "$PID_DIR"

if [[ -f "$LOCK_FILE" ]]; then
  lock_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
    log "warmup already running (pid ${lock_pid})"
    exit 0
  fi
  rm -f "$LOCK_FILE"
fi

COMFY_PID=""
if [[ -f "${PID_DIR}/comfyui.pid" ]]; then
  COMFY_PID="$(cat "${PID_DIR}/comfyui.pid" 2>/dev/null || true)"
fi

export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"
export WAN_ANIMATE_DATA_DIR="${WAN_ANIMATE_DATA_DIR:-${ROOT}/wan-animate-api/data}"

log "starting background warmup (comfy_pid=${COMFY_PID:-unknown})"
nohup "$PYTHON_BIN" "${ROOT}/scripts/warmup_comfy.py" \
  ${COMFY_PID:+--comfy-pid "$COMFY_PID"} \
  >> "$LOG_FILE" 2>&1 &
echo $! > "$LOCK_FILE"
log "warmup pid $(cat "$LOCK_FILE"), log: ${LOG_FILE}"
