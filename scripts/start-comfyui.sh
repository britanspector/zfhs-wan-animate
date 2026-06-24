#!/usr/bin/env bash
# Start ComfyUI for zfhs-wan-animate (no zealman-app dependency).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY_ROOT="${COMFYUI_ROOT:-/root/ComfyUI}"
COMFY_PORT="${COMFY_STOP_PORT:-6006}"
PYTHON_BIN="${COMFY_PYTHON:-/root/miniconda3/bin/python}"

log_info() { echo "[start-comfyui] $(date '+%Y-%m-%d %H:%M:%S') - $*"; }
log_warn() { echo "[start-comfyui] WARN: $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2; }
log_error() { echo "[start-comfyui] ERROR: $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2; }

export PATH="/usr/local/bin:/root/miniconda3/bin:${PATH:-}"

if [[ "${OMP_NUM_THREADS:-}" == "0" ]]; then
  export OMP_NUM_THREADS=1
  log_info "Fixed OMP_NUM_THREADS: 0 -> 1"
fi

export NUMBA_THREADING_LAYER="${NUMBA_THREADING_LAYER:-workqueue}"
export NO_ALBUMENTATIONS_UPDATE="${NO_ALBUMENTATIONS_UPDATE:-1}"
export PYTHONWARNINGS="${PYTHONWARNINGS:+$PYTHONWARNINGS,}ignore::UserWarning:pydantic._internal._fields,ignore:pkg_resources is deprecated:UserWarning"

if [[ "${SKIP_MODEL_SETUP:-}" != "1" ]]; then
  log_info "Setting up P07 model symlinks..."
  bash "${ROOT}/scripts/setup_models.sh" || log_warn "Model setup reported issues (continuing)"
else
  log_info "SKIP_MODEL_SETUP=1, skipping model symlinks"
fi

if [[ -f "${ROOT}/scripts/install_custom_nodes.sh" ]]; then
  bash "${ROOT}/scripts/install_custom_nodes.sh" --check-only || true
fi

if [[ ! -f "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    log_error "Python not found: ${COMFY_PYTHON:-/root/miniconda3/bin/python}"
    exit 1
  fi
fi

LD_CACHE="/tmp/.comfyui-ld-cache"
if [[ -f "$LD_CACHE" ]]; then
  EXTRA_LD="$(cat "$LD_CACHE")"
  log_info "Loaded LD_LIBRARY_PATH from cache"
else
  EXTRA_LD="$("$PYTHON_BIN" -c "
import site, glob, os
prefix = os.path.dirname(os.path.dirname('${PYTHON_BIN}'))
parts = [os.path.join(prefix, 'lib')]
try:
    sp = site.getsitepackages()[0]
    nv = [p for p in glob.glob(os.path.join(sp, 'nvidia', '*', 'lib')) if os.path.isdir(p)]
    if nv:
        parts.append(':'.join(sorted(nv)))
    llama = os.path.join(sp, 'llama_cpp', 'lib')
    if os.path.isdir(llama):
        parts.append(llama)
except Exception:
    pass
print(':'.join(parts))
" 2>/dev/null || echo "$(dirname "$(dirname "$PYTHON_BIN")")/lib")"
  echo "$EXTRA_LD" > "$LD_CACHE"
  log_info "Resolved and cached LD_LIBRARY_PATH"
fi

if [[ -z "${LD_LIBRARY_PATH:-}" ]]; then
  export LD_LIBRARY_PATH="$EXTRA_LD"
else
  export LD_LIBRARY_PATH="$EXTRA_LD:${LD_LIBRARY_PATH}"
fi

if [[ ! -d "$COMFY_ROOT" ]]; then
  log_error "ComfyUI directory not found: $COMFY_ROOT"
  exit 1
fi

cd "$COMFY_ROOT"

if [[ ! -f "main.py" ]]; then
  log_error "main.py not found in $COMFY_ROOT"
  exit 1
fi

rm -rf custom_nodes/.ipynb_checkpoints 2>/dev/null || true

set +e
PORT_PIDS="$(lsof -Pi ":$COMFY_PORT" -sTCP:LISTEN -t 2>/dev/null)"
set -e

if [[ -n "$PORT_PIDS" ]]; then
  log_warn "Port $COMFY_PORT in use, terminating listener(s)..."
  echo "$PORT_PIDS" | xargs kill -9 2>/dev/null || true
  for _ in 1 2 3; do
    if ! lsof -Pi ":$COMFY_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

log_info "Starting ComfyUI on port $COMFY_PORT..."
exec "$PYTHON_BIN" main.py \
  --port "$COMFY_PORT" \
  --listen 127.0.0.1 \
  --enable-cors-header "*"
