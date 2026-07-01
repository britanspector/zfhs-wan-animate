#!/bin/bash
# Monitor zfhs-wan-animate AutoDL services and restart if unhealthy.
LOG_FILE="/tmp/zfhs-wan-animate-daemon.log"
ROOT="/root/zfhs-wan-animate"

echo "$(date): 守护进程启动" >> "$LOG_FILE"

while true; do
    gateway_ok=false
    comfy_ok=false
    if curl -s -o /dev/null --max-time 3 http://127.0.0.1:6008/api/health 2>/dev/null; then
        gateway_ok=true
    fi
    if curl -s -o /dev/null --max-time 3 http://127.0.0.1:6006/system_stats 2>/dev/null; then
        comfy_ok=true
    fi

    if [ "$gateway_ok" != true ] || [ "$comfy_ok" != true ]; then
        echo "$(date): 服务异常 (gateway=$gateway_ok comfy=$comfy_ok)，尝试重启..." >> "$LOG_FILE"
        bash "$ROOT/scripts/start-autodl-services.sh" >> "$LOG_FILE" 2>&1 || true
    fi

    sleep 300
done
