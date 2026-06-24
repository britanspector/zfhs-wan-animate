#!/bin/bash
# One-click start: wan-animate-api (6020) + optional ComfyUI (6006) + optional Vite dev (5173)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="${ROOT}/.run"
API_PID="${PID_DIR}/wan-animate-api.pid"
COMFY_PID="${PID_DIR}/comfyui.pid"
VITE_PID="${PID_DIR}/vite.pid"
API_PORT="${WAN_ANIMATE_API_PORT:-6020}"
COMFY_PORT=6006
VITE_PORT=5173

WITH_COMFY=false
DEV_MODE=false
DO_STOP=false

log() { echo "[start-wan-animate] $*"; }

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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-comfy) WITH_COMFY=true ;;
    --dev) DEV_MODE=true ;;
    --stop) DO_STOP=true ;;
    -h|--help)
      cat <<EOF
用法: bash scripts/start-wan-animate.sh [选项]

  --with-comfy   若 6006 未监听则后台启动 ComfyUI
  --dev          同时启动 Vite 开发前端 (5173)
  --stop         停止本脚本启动的进程

示例:
  bash scripts/start-wan-animate.sh --with-comfy
  bash scripts/start-wan-animate.sh --with-comfy --dev
EOF
      exit 0
      ;;
    *) log "未知参数: $1"; exit 1 ;;
  esac
  shift
done

mkdir -p "$PID_DIR"

if $DO_STOP; then
  stop_pidfile "$VITE_PID" "Vite"
  stop_pidfile "$API_PID" "API"
  stop_pidfile "$COMFY_PID" "ComfyUI"
  log "已停止"
  exit 0
fi

export PATH="/root/miniconda3/bin:/usr/local/bin:$PATH"

if $WITH_COMFY; then
  if port_listening "$COMFY_PORT"; then
    log "ComfyUI 已在端口 ${COMFY_PORT} 运行"
  else
    COMFY_SCRIPT="/root/zealman-app/start-comfyui.sh"
    if [[ -x "$COMFY_SCRIPT" ]] || [[ -f "$COMFY_SCRIPT" ]]; then
      log "后台启动 ComfyUI..."
      nohup bash "$COMFY_SCRIPT" > "${PID_DIR}/comfyui.log" 2>&1 &
      echo $! > "$COMFY_PID"
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        port_listening "$COMFY_PORT" && break
        sleep 2
      done
      if port_listening "$COMFY_PORT"; then
        log "ComfyUI 已启动: http://127.0.0.1:${COMFY_PORT}"
      else
        log "WARN: ComfyUI 可能仍在启动，查看 ${PID_DIR}/comfyui.log"
      fi
    else
      log "WARN: 未找到 ${COMFY_SCRIPT}，请手动启动 ComfyUI"
    fi
  fi
fi

WEB_DIST="${ROOT}/wan-animate-web/dist"
if [[ ! -f "${WEB_DIST}/index.html" ]]; then
  log "构建前端 dist..."
  (cd "${ROOT}/wan-animate-web" && npm run build)
fi

if port_listening "$API_PORT"; then
  log "API 端口 ${API_PORT} 已被占用，跳过启动"
else
  log "启动 API (uvicorn :${API_PORT})..."
  cd "$ROOT"
  nohup uvicorn app:app --app-dir wan-animate-api --host 0.0.0.0 --port "$API_PORT" \
    > "${PID_DIR}/api.log" 2>&1 &
  echo $! > "$API_PID"
  sleep 1
fi

if $DEV_MODE; then
  if port_listening "$VITE_PORT"; then
    log "Vite 端口 ${VITE_PORT} 已被占用"
  else
    log "启动 Vite dev (:${VITE_PORT})..."
    (cd "${ROOT}/wan-animate-web" && nohup npm run dev -- --host 0.0.0.0 --port "$VITE_PORT" \
      > "${PID_DIR}/vite.log" 2>&1 &)
    echo $! > "$VITE_PID"
  fi
fi

echo ""
echo "=========================================="
echo " ComfyUI 画布:  http://127.0.0.1:${COMFY_PORT}"
echo " Web 一键生成:  http://127.0.0.1:${API_PORT}"
if $DEV_MODE; then
  echo " Vite 开发:     http://127.0.0.1:${VITE_PORT}"
fi
echo " P07 模板 URL:  http://127.0.0.1:${COMFY_PORT}/?template=p07_wan22_animate_v4&source=zealman-workflow-templates"
echo " 停止: bash scripts/start-wan-animate.sh --stop"
echo "=========================================="
