#!/usr/bin/env bash
# Start Jupyter Lab for project notebook (internal :8888, public via nginx /jupyter/).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="${ROOT}/.run"
JUPYTER_PID="${PID_DIR}/jupyter.pid"
JUPYTER_LOG="${PID_DIR}/jupyter.log"
JUPYTER_TOKEN_FILE="${PID_DIR}/jupyter.token"
JUPYTER_PORT="${JUPYTER_PORT:-8888}"
NOTEBOOK_FILE="中升智学动作迁移实验项目教学代码.ipynb"
FORCE_RESTART="${JUPYTER_FORCE_RESTART:-1}"

log() { echo "[start-jupyter] $*"; }

port_listening() {
  lsof -Pi ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

is_our_jupyter() {
  if [[ -f "$JUPYTER_PID" ]]; then
    local pid
    pid="$(cat "$JUPYTER_PID")"
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

stop_jupyter_on_port() {
  local pids
  pids="$(lsof -t -i:"$JUPYTER_PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    log "停止端口 ${JUPYTER_PORT} 上的 Jupyter: ${pids}"
    echo "$pids" | xargs -r kill 2>/dev/null || true
    sleep 2
    echo "$pids" | xargs -r kill -9 2>/dev/null || true
    sleep 1
  fi
  rm -f "$JUPYTER_PID"
}

export PATH="/root/miniconda3/bin:/usr/local/bin:${PATH:-}"

if ! command -v jupyter >/dev/null 2>&1; then
  log "ERROR: 未找到 jupyter，请安装: pip install jupyterlab"
  exit 1
fi

if [[ ! -f "${ROOT}/notebooks/${NOTEBOOK_FILE}" ]]; then
  log "ERROR: 未找到 notebook: ${ROOT}/notebooks/${NOTEBOOK_FILE}"
  exit 1
fi

mkdir -p "$PID_DIR"

if port_listening "$JUPYTER_PORT"; then
  if [[ "$FORCE_RESTART" == "1" ]] && ! is_our_jupyter; then
    log "检测到非本项目 Jupyter，强制重启以应用 default_url..."
    stop_jupyter_on_port
  elif is_our_jupyter; then
    log "Jupyter 已在端口 ${JUPYTER_PORT} 运行 (本项目)"
    exit 0
  else
    log "Jupyter 已在端口 ${JUPYTER_PORT} 运行，跳过 (设 JUPYTER_FORCE_RESTART=1 强制重启)"
    exit 0
  fi
fi

TOKEN="${AutodlAutoPanelToken:-${JUPYTER_TOKEN:-}}"
if [[ -z "$TOKEN" ]] && [[ -f "$JUPYTER_TOKEN_FILE" ]]; then
  TOKEN="$(cat "$JUPYTER_TOKEN_FILE")"
fi
if [[ -z "$TOKEN" ]]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  echo "$TOKEN" > "$JUPYTER_TOKEN_FILE"
  log "已生成 Jupyter token 并写入 ${JUPYTER_TOKEN_FILE}"
fi

DEFAULT_URL="/lab/tree/notebooks/${NOTEBOOK_FILE}"

log "启动 Jupyter Lab (0.0.0.0:${JUPYTER_PORT}, base_url=/jupyter/)..."
log "默认打开: ${DEFAULT_URL}"
cd "$ROOT"
nohup jupyter lab \
  --ip=0.0.0.0 \
  --port="$JUPYTER_PORT" \
  --no-browser \
  --ServerApp.base_url=/jupyter/ \
  --ServerApp.token="$TOKEN" \
  --ServerApp.allow_origin='*' \
  --ServerApp.allow_remote_access=True \
  --ServerApp.trust_xheaders=True \
  --ServerApp.disable_check_xsrf=True \
  --ServerApp.default_url="$DEFAULT_URL" \
  --LabApp.news_url="" \
  --notebook-dir="$ROOT" \
  > "$JUPYTER_LOG" 2>&1 &
echo $! > "$JUPYTER_PID"

for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if curl -s -o /dev/null --max-time 2 "http://127.0.0.1:${JUPYTER_PORT}/jupyter/api/status?token=${TOKEN}" 2>/dev/null; then
    log "Jupyter 已启动: http://127.0.0.1:${JUPYTER_PORT}/jupyter/lab?token=${TOKEN}"
    log "公网入口（经 6008）: 见 curl http://127.0.0.1:6008/api/services"
    exit 0
  fi
  sleep 1
done

log "WARN: Jupyter 可能仍在启动，查看 ${JUPYTER_LOG}"
