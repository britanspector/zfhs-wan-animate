#!/bin/bash
# Check zfhs-wan-animate AutoDL service status.
set -e

export PATH="/root/miniconda3/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
ROOT="/root/zfhs-wan-animate"

# shellcheck source=/dev/null
[[ -f /etc/profile.d/autodl.env.sh ]] && source /etc/profile.d/autodl.env.sh

echo "=========================================="
echo "zfhs-wan-animate AutoDL 服务状态"
echo "=========================================="
echo ""

check_port() {
    local port="$1" label="$2"
    echo "端口 ${port} (${label})"
    if lsof -i ":${port}" >/dev/null 2>&1; then
        echo "  OK 已监听"
        lsof -i ":${port}" | head -3 | sed 's/^/  /'
    else
        echo "  FAIL 未监听"
    fi
    echo ""
}

check_port 6006 "ComfyUI"
check_port 6020 "Web API (internal)"
check_port 8888 "Jupyter (internal)"
check_port 6008 "nginx gateway"

echo "健康检查"
for spec in "6006:/system_stats:ComfyUI" "6020:/api/health:Web API" "8888:/jupyter/api/status:Jupyter" "6008:/api/health:Gateway"; do
    IFS=':' read -r port path name <<< "$spec"
    if curl -s -o /dev/null --max-time 3 "http://127.0.0.1:${port}${path}" 2>/dev/null; then
        echo "  OK  ${name}"
    else
        echo "  FAIL ${name}"
    fi
done
echo ""

echo "公网地址"
echo "  ComfyUI:  ${AutoDLService6006URL:-（未注入，见控制台「自定义服务」）}"
echo "  Web:      ${AutoDLService6008URL:-（未注入）}/"
echo "  Jupyter:  ${AutoDLService6008URL:-（未注入）}/jupyter/"
echo ""

if curl -s http://127.0.0.1:6008/api/services 2>/dev/null | python3 -m json.tool 2>/dev/null; then
    :
else
    echo "（/api/services 暂不可用）"
fi
echo ""

echo "日志"
echo "  ${ROOT}/.run/comfyui.log"
echo "  ${ROOT}/.run/api.log"
echo "  ${ROOT}/.run/jupyter.log"
echo "  ${ROOT}/.run/nginx-error.log"
echo "  /tmp/zfhs-wan-animate-autostart.log"
echo "  /tmp/zfhs-wan-animate-daemon.log"
echo ""
