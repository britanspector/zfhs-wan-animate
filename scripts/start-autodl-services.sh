#!/usr/bin/env bash
# AutoDL three-service stack: ComfyUI (6006) + Web (6020 internal) + Jupyter (8888) + nginx (6008).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="${ROOT}/.run"
API_PID="${PID_DIR}/wan-animate-api.pid"
COMFY_PID="${PID_DIR}/comfyui.pid"
JUPYTER_PID="${PID_DIR}/jupyter.pid"
NGINX_PID="${PID_DIR}/nginx.pid"

API_PORT="${WAN_ANIMATE_API_PORT:-6020}"
API_HOST="${WAN_ANIMATE_API_HOST:-127.0.0.1}"
GATEWAY_PORT="${WAN_ANIMATE_GATEWAY_PORT:-6008}"
COMFY_PORT=6006
JUPYTER_PORT="${JUPYTER_PORT:-8888}"

log() { echo "[start-autodl-services] $*"; }

port_listening() {
  lsof -Pi ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

stop_pidfile() {
  local file="$1" name="$2"
  if [[ -f "$file" ]]; then
    local pid
    pid="$(cat "$file")"
    if kill -0 "$pid" 2>/dev/null; then
      log "停止 ${name} (pid ${pid})"
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$file"
  fi
}

kill_on_port() {
  local port="$1"
  if port_listening "$port"; then
    local pids
    pids="$(lsof -t -i:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      log "清理端口 ${port} 占用: ${pids}"
      echo "$pids" | xargs -r kill -9 2>/dev/null || true
      sleep 1
    fi
  fi
}

DO_STOP=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --stop) DO_STOP=true ;;
    -h|--help)
      cat <<EOF
用法: bash scripts/start-autodl-services.sh [--stop]

AutoDL 三服务栈:
  6006  ComfyUI 画布        -> AutoDLService6006URL
  6008  nginx 网关          -> AutoDLService6008URL
  6020  Web API (内部)      -> 经 6008 /
  8888  Jupyter (内部)      -> 经 6008 /jupyter/

环境变量:
  SKIP_PORT_6008_CLEANUP=1  跳过释放 6008 端口占用
EOF
      exit 0
      ;;
    *) log "未知参数: $1"; exit 1 ;;
  esac
  shift
done

mkdir -p "$PID_DIR"
export PATH="/root/miniconda3/bin:/usr/local/bin:${PATH:-}"

# shellcheck source=/dev/null
[[ -f /etc/profile.d/autodl.env.sh ]] && source /etc/profile.d/autodl.env.sh

if $DO_STOP; then
  stop_pidfile "$NGINX_PID" "nginx"
  stop_pidfile "$JUPYTER_PID" "Jupyter"
  stop_pidfile "$API_PID" "API"
  stop_pidfile "$COMFY_PID" "ComfyUI"
  kill_on_port "$GATEWAY_PORT"
  log "已停止 AutoDL 服务栈"
  exit 0
fi

if [[ "${SKIP_PORT_6008_CLEANUP:-0}" != "1" ]]; then
  if pgrep -f "node server.js" >/dev/null 2>&1; then
    log "释放 6008 端口占用（停止 node server.js）..."
    pkill -f "node server.js" 2>/dev/null || true
    sleep 2
  fi
  kill_on_port "$GATEWAY_PORT"
fi

# 1. ComfyUI
if port_listening "$COMFY_PORT"; then
  log "ComfyUI 已在端口 ${COMFY_PORT} 运行"
else
  log "后台启动 ComfyUI..."
  nohup bash "${ROOT}/scripts/start-comfyui.sh" > "${PID_DIR}/comfyui.log" 2>&1 &
  echo $! > "$COMFY_PID"
fi

# 2. Web API (internal)
WEB_DIST="${ROOT}/wan-animate-web/dist"
if [[ ! -f "${WEB_DIST}/index.html" ]]; then
  log "构建前端 dist..."
  (cd "${ROOT}/wan-animate-web" && npm run build)
fi

if port_listening "$API_PORT"; then
  log "API 已在端口 ${API_PORT} 运行"
else
  export WAN_ANIMATE_PUBLIC_BASE_URL="${WAN_ANIMATE_PUBLIC_BASE_URL:-${AutoDLService6008URL:-}}"
  if [[ -n "$WAN_ANIMATE_PUBLIC_BASE_URL" ]]; then
    log "公网 Web base: ${WAN_ANIMATE_PUBLIC_BASE_URL}"
  fi
  log "启动 API (uvicorn ${API_HOST}:${API_PORT})..."
  cd "$ROOT"
  nohup uvicorn app:app --app-dir wan-animate-api --host "$API_HOST" --port "$API_PORT" \
    > "${PID_DIR}/api.log" 2>&1 &
  echo $! > "$API_PID"
fi

# 3. Jupyter
JUPYTER_FORCE_RESTART=1 bash "${ROOT}/scripts/start-jupyter.sh"

# 4. nginx gateway
bash "${ROOT}/scripts/start-nginx-gateway.sh"

# Health checks
log "等待服务就绪..."
COMFY_OK=false
API_OK=false
JUPYTER_OK=false
GATEWAY_OK=false

for i in $(seq 1 60); do
  port_listening "$COMFY_PORT" && curl -s -o /dev/null --max-time 2 "http://127.0.0.1:${COMFY_PORT}/system_stats" 2>/dev/null && COMFY_OK=true
  curl -s -o /dev/null --max-time 2 "http://127.0.0.1:${API_PORT}/api/health" 2>/dev/null && API_OK=true
  curl -s -o /dev/null --max-time 2 "http://127.0.0.1:${JUPYTER_PORT}/jupyter/api/status" 2>/dev/null && JUPYTER_OK=true
  curl -s -o /dev/null --max-time 2 "http://127.0.0.1:${GATEWAY_PORT}/api/health" 2>/dev/null && GATEWAY_OK=true
  if $COMFY_OK && $API_OK && $JUPYTER_OK && $GATEWAY_OK; then
    break
  fi
  sleep 2
done

if $COMFY_OK && $API_OK; then
  bash "${ROOT}/scripts/run-warmup.sh" || log "WARN: background warmup launch failed"
fi

PUBLIC_6006="${AutoDLService6006URL:-http://127.0.0.1:${COMFY_PORT}}"
PUBLIC_6008="${AutoDLService6008URL:-http://127.0.0.1:${GATEWAY_PORT}}"

echo ""
echo "=========================================="
echo " AutoDL 三服务已启动"
echo "=========================================="
echo " ComfyUI 画布:  ${PUBLIC_6006}"
echo " Web 一键生成:  ${PUBLIC_6008}/"
echo " Jupyter:       ${PUBLIC_6008}/jupyter/lab?token=<见 /api/services>"
echo " P07 模板:      ${PUBLIC_6006}/?template=p07_wan22_animate_v4&source=zfhs-workflow-templates"
echo ""
echo " 本地: ComfyUI :${COMFY_PORT} | API :${API_PORT} | Jupyter :${JUPYTER_PORT} | 网关 :${GATEWAY_PORT}"
echo " 状态: ComfyUI=$($COMFY_OK && echo OK || echo WAIT) API=$($API_OK && echo OK || echo WAIT) Jupyter=$($JUPYTER_OK && echo OK || echo WAIT) Gateway=$($GATEWAY_OK && echo OK || echo WAIT)"
echo " 停止: bash scripts/start-autodl-services.sh --stop"
echo "=========================================="

if ! $GATEWAY_OK; then
  log "WARN: 网关健康检查未通过，查看 ${PID_DIR}/nginx-error.log 与 api.log"
  exit 1
fi
