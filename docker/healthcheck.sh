#!/usr/bin/env bash
set -euo pipefail

API_PORT="${WAN_ANIMATE_API_PORT:-6020}"
BASE="http://127.0.0.1:${API_PORT}"

curl -sf "${BASE}/api/health" | grep -q '"ok"[[:space:]]*:[[:space:]]*true'
curl -sf "${BASE}/api/comfy/status" | grep -q '"running"[[:space:]]*:[[:space:]]*true'
