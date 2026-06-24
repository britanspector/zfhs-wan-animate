#!/usr/bin/env bash
# First-time setup for standalone zfhs-wan-animate on AutoDL (no zealman-app).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "[bootstrap] $*"; }

if [[ ! -f config/local.yaml ]]; then
  log "Creating config/local.yaml from example..."
  cp config/local.yaml.example config/local.yaml
fi

log "Linking P07 models from AutoDL platform cache..."
bash scripts/setup_models.sh --strict

log "Checking / installing custom nodes..."
bash scripts/install_custom_nodes.sh --install-missing

log "Verifying assets..."
python3 scripts/verify_assets.py --strict-models

if [[ -f wan-animate-web/package.json ]]; then
  if command -v npm >/dev/null 2>&1; then
    log "Building frontend..."
    (cd wan-animate-web && npm ci && npm run build)
  else
    log "WARN: npm not found, skip frontend build"
  fi
else
  log "WARN: wan-animate-web not found, skip frontend build"
fi

echo ""
log "Bootstrap complete."
echo "Start with: bash scripts/start-wan-animate.sh --with-comfy"
echo "Web UI:     http://127.0.0.1:6020/"
echo "ComfyUI:    http://127.0.0.1:6006/"
