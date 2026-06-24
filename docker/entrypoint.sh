#!/usr/bin/env bash
set -euo pipefail

COMFY_ROOT="${COMFYUI_ROOT:-/app/ComfyUI}"
COMFY_PORT="${COMFY_STOP_PORT:-6006}"
COMFY_URL="${COMFYUI_URL:-http://127.0.0.1:${COMFY_PORT}}"
PYTHON_BIN="${COMFY_PYTHON:-/opt/venv/bin/python}"
API_HOST="${WAN_ANIMATE_API_HOST:-0.0.0.0}"
API_PORT="${WAN_ANIMATE_API_PORT:-6020}"
APP_DIR="/app/zfhs-wan-animate"
DATA_DIR="${WAN_ANIMATE_DATA_DIR:-/app/data}"
JOBS_PATH="${WAN_ANIMATE_JOBS_PATH:-${DATA_DIR}/jobs.json}"

export COMFYUI_ROOT="${COMFY_ROOT}"
export COMFYUI_URL="${COMFY_URL}"
export COMFY_PYTHON="${PYTHON_BIN}"
export WAN_ANIMATE_DATA_DIR="${DATA_DIR}"
export WAN_ANIMATE_JOBS_PATH="${JOBS_PATH}"
export PYTHONPATH="${APP_DIR}/src:${APP_DIR}/wan-animate-api:${PYTHONPATH:-}"

mkdir -p "${DATA_DIR}" "${COMFY_ROOT}/input" "${COMFY_ROOT}/output" "${COMFY_ROOT}/models"
touch "${JOBS_PATH}" 2>/dev/null || true

resolve_ld() {
  local cache="/tmp/.comfyui-ld-cache"
  if [[ -f "${cache}" ]]; then
    export LD_LIBRARY_PATH="$(cat "${cache}"):${LD_LIBRARY_PATH:-}"
    return
  fi
  local extra
  extra="$("${PYTHON_BIN}" -c "import site, glob, os; sp=site.getsitepackages()[0]; parts=['/opt/venv/lib']; nv=[p for p in glob.glob(os.path.join(sp,'nvidia','*','lib')) if os.path.isdir(p)]; parts.extend(sorted(nv)); print(':'.join(parts))" 2>/dev/null || echo '/opt/venv/lib')"
  echo "${extra}" > "${cache}"
  export LD_LIBRARY_PATH="${extra}:${LD_LIBRARY_PATH:-}"
}

wait_comfy() {
  local deadline=$((SECONDS + 180))
  while (( SECONDS < deadline )); do
    if curl -sf "${COMFY_URL}/system_stats" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

stop_children() {
  if [[ -n "${COMFY_PID:-}" ]] && kill -0 "${COMFY_PID}" 2>/dev/null; then
    kill "${COMFY_PID}" 2>/dev/null || true
    wait "${COMFY_PID}" 2>/dev/null || true
  fi
  if [[ -n "${API_PID:-}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
    wait "${API_PID}" 2>/dev/null || true
  fi
}

trap stop_children SIGTERM SIGINT

resolve_ld

echo "[entrypoint] asset verify (models may be mounted externally)..."
"${PYTHON_BIN}" "${APP_DIR}/scripts/verify_assets.py" || true

if curl -sf "${COMFY_URL}/system_stats" >/dev/null 2>&1; then
  echo "[entrypoint] ComfyUI already running at ${COMFY_URL}"
else
  echo "[entrypoint] starting ComfyUI on port ${COMFY_PORT}..."
  cd "${COMFY_ROOT}"
  nohup "${PYTHON_BIN}" main.py \
    --port "${COMFY_PORT}" \
    --listen 127.0.0.1 \
    --enable-cors-header "*" \
    > "${COMFY_ROOT}/wan_animate_entrypoint.log" 2>&1 &
  COMFY_PID=$!
  wait_comfy || {
    echo "[entrypoint] ComfyUI failed to become ready; tail log:"
    tail -n 40 "${COMFY_ROOT}/wan_animate_entrypoint.log" || true
    exit 1
  }
  echo "[entrypoint] ComfyUI ready"
fi

echo "[entrypoint] starting wan-animate-api on ${API_HOST}:${API_PORT}..."
cd "${APP_DIR}"
"${PYTHON_BIN}" -m uvicorn app:app \
  --app-dir wan-animate-api \
  --host "${API_HOST}" \
  --port "${API_PORT}" &
API_PID=$!
wait "${API_PID}"
