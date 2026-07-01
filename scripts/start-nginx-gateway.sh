#!/usr/bin/env bash
# Start nginx gateway on port 6008 (Web + Jupyter path routing).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="${ROOT}/.run"
NGINX_PID="${PID_DIR}/nginx.pid"
NGINX_CONF="${ROOT}/autodl/nginx-6008.conf"
GATEWAY_PORT="${WAN_ANIMATE_GATEWAY_PORT:-6008}"

log() { echo "[start-nginx-gateway] $*"; }

port_listening() {
  lsof -Pi ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

ensure_nginx() {
  if command -v nginx >/dev/null 2>&1; then
    return 0
  fi
  log "安装 nginx..."
  if command -v apt-get >/dev/null 2>&1; then
    DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y nginx >/dev/null 2>&1
  fi
  if ! command -v nginx >/dev/null 2>&1; then
    log "ERROR: 未找到 nginx，请手动安装"
    exit 1
  fi
}

stop_existing() {
  if [[ -f "$NGINX_PID" ]]; then
    local pid
    pid="$(cat "$NGINX_PID" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      log "停止已有 nginx (pid ${pid})"
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$NGINX_PID"
  fi
  if port_listening "$GATEWAY_PORT"; then
    local pids
    pids="$(lsof -t -i:"$GATEWAY_PORT" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      log "清理端口 ${GATEWAY_PORT} 占用: ${pids}"
      echo "$pids" | xargs -r kill -9 2>/dev/null || true
      sleep 1
    fi
  fi
}

mkdir -p "$PID_DIR"
ensure_nginx

if [[ ! -f "$NGINX_CONF" ]]; then
  log "ERROR: 未找到配置 ${NGINX_CONF}"
  exit 1
fi

if nginx -t -c "$NGINX_CONF" 2>"${PID_DIR}/nginx-test.log"; then
  :
else
  log "ERROR: nginx 配置校验失败"
  cat "${PID_DIR}/nginx-test.log" >&2
  exit 1
fi

if port_listening "$GATEWAY_PORT"; then
  if [[ -f "$NGINX_PID" ]] && kill -0 "$(cat "$NGINX_PID")" 2>/dev/null; then
    log "nginx 网关已在端口 ${GATEWAY_PORT} 运行"
    exit 0
  fi
  stop_existing
fi

stop_existing
log "启动 nginx 网关 (0.0.0.0:${GATEWAY_PORT})..."
nohup nginx -c "$NGINX_CONF" > "${PID_DIR}/nginx.log" 2>&1 &
sleep 1

if port_listening "$GATEWAY_PORT"; then
  if [[ -f "$NGINX_PID" ]]; then
    log "nginx 已启动 (pid $(cat "$NGINX_PID"))"
  else
    log "nginx 已启动 (端口 ${GATEWAY_PORT})"
  fi
else
  log "ERROR: nginx 启动失败，查看 ${PID_DIR}/nginx-error.log"
  exit 1
fi
