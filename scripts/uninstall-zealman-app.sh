#!/usr/bin/env bash
# Stop zealman-app processes, remove autostart hooks, and delete /root/zealman-app.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZEALMAN_DIR="/root/zealman-app"

log() { echo "[uninstall-zealman-app] $*"; }

stop_zealman_processes() {
  log "停止 zealman-app 相关进程..."
  pkill -f "${ZEALMAN_DIR}/scripts/daemon.sh" 2>/dev/null || true
  pkill -f "${ZEALMAN_DIR}/scripts/improved-autostart.sh" 2>/dev/null || true
  if lsof -Pi :6008 -sTCP:LISTEN 2>/dev/null | grep -q "node"; then
    log "停止占用 6008 的 node server.js..."
    pkill -f "node server.js" 2>/dev/null || true
    sleep 2
  fi
}

clean_rc_local() {
  if [[ ! -f /etc/rc.local ]]; then
    return
  fi
  if grep -q "zealman-app" /etc/rc.local; then
    log "清理 /etc/rc.local 中的 zealman 自启动..."
    python3 << 'PYEOF'
from pathlib import Path
path = Path("/etc/rc.local")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
out = []
skip = False
for line in lines:
    if "zealman-app" in line or "Zealman-AutoDL" in line:
        skip = True
        continue
    if skip:
        if line.strip() == "fi":
            skip = False
        continue
    out.append(line)
path.write_text("".join(out), encoding="utf-8")
PYEOF
  fi
}

clean_profile_d() {
  local f="/etc/profile.d/zealman-autostart.sh"
  if [[ -f "$f" ]]; then
    log "删除 $f"
    rm -f "$f"
  fi
}

clean_shell_file() {
  local file="$1"
  [[ -f "$file" ]] || return
  if grep -q "zealman-app" "$file"; then
    log "清理 $file 中的 zealman 自启动..."
    python3 - "$file" << 'PYEOF'
import sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
blocks = [
    "# ==================== Zealman-AutoDL 自动启动 ====================",
]
lines = text.splitlines(keepends=True)
out = []
skip = False
for line in lines:
    if "Zealman-AutoDL" in line or (
        not skip and "zealman-app" in line and "improved-autostart" in line
    ):
        skip = True
        continue
    if skip:
        if line.strip() == "# ================================================================":
            skip = False
        elif line.strip() == "fi" and "zealman" not in line.lower():
            skip = False
            continue
        continue
    out.append(line)
path.write_text("".join(out), encoding="utf-8")
PYEOF
  fi
}

delete_zealman_dir() {
  if [[ -d "$ZEALMAN_DIR" ]]; then
    log "删除目录: $ZEALMAN_DIR"
    rm -rf "$ZEALMAN_DIR"
  else
    log "目录已不存在: $ZEALMAN_DIR"
  fi
}

verify_no_refs() {
  log "验证自启动残留..."
  local refs=0
  for f in /etc/rc.local /etc/profile.d/zealman-autostart.sh /root/.bashrc /root/.profile; do
    if [[ -f "$f" ]] && grep -q "zealman-app" "$f" 2>/dev/null; then
      log "WARN: 仍有引用: $f"
      refs=1
    fi
  done
  if pgrep -af "$ZEALMAN_DIR" >/dev/null 2>&1; then
    log "WARN: 仍有 zealman-app 进程"
    pgrep -af "$ZEALMAN_DIR" || true
    refs=1
  fi
  if [[ "$refs" -eq 0 ]]; then
    log "无 zealman-app 自启动与进程残留"
  fi
}

main() {
  log "开始卸载 zealman-app..."
  stop_zealman_processes
  clean_rc_local
  clean_profile_d
  clean_shell_file /root/.bashrc
  clean_shell_file /root/.profile
  delete_zealman_dir
  verify_no_refs
  log "完成。请运行: bash ${ROOT}/scripts/setup_comfy_p07_template.sh"
  log "并重启服务: bash ${ROOT}/scripts/start-autodl-services.sh"
}

main "$@"
