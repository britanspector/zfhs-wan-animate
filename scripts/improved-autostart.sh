#!/bin/bash
# zfhs-wan-animate AutoDL cold-start script (no duplicate runs).
set -e

export PATH="/root/miniconda3/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

ROOT="/root/zfhs-wan-animate"
LOG_FILE="/tmp/zfhs-wan-animate-autostart.log"
LOCK_FILE="/tmp/zfhs-wan-animate-autostart.lock"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" | tee -a "$LOG_FILE"
}

if [ -f "$LOCK_FILE" ]; then
    lock_pid=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
        log "启动脚本已在运行 (PID: $lock_pid)，跳过"
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT INT TERM

gateway_ok=false
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:6008/api/health 2>/dev/null; then
    gateway_ok=true
fi
comfy_ok=false
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:6006/system_stats 2>/dev/null; then
    comfy_ok=true
fi

if [ "$gateway_ok" = true ] && [ "$comfy_ok" = true ]; then
    log "服务栈已在运行（6006 + 6008）"
    bash "$ROOT/scripts/run-warmup.sh" >> "$LOG_FILE" 2>&1 || true
    exit 0
fi

if [ ! -d "$ROOT" ]; then
    log "ERROR: 项目目录不存在: $ROOT"
    exit 1
fi

cd "$ROOT"

log "启动 AutoDL 三服务栈..."
bash "$ROOT/scripts/start-autodl-services.sh" >> "$LOG_FILE" 2>&1

start_ts=$(date +%s%N)
for i in $(seq 1 90); do
  gw=false
  cf=false
  curl -s -o /dev/null --max-time 2 http://127.0.0.1:6008/api/health 2>/dev/null && gw=true
  curl -s -o /dev/null --max-time 2 http://127.0.0.1:6006/system_stats 2>/dev/null && cf=true
  if [ "$gw" = true ] && [ "$cf" = true ]; then
    elapsed_ms=$(( ( $(date +%s%N) - start_ts ) / 1000000 ))
    log "服务栈启动成功（${elapsed_ms}ms / poll=${i}）"
    curl -s -o /dev/null --max-time 2 http://127.0.0.1:6008/api/services 2>/dev/null || true
    exit 0
  fi
  if [ "$i" -le 20 ]; then
    sleep 2
  else
    sleep 3
  fi
done

log "ERROR: 服务栈启动超时，查看 $ROOT/.run/*.log"
exit 1
