#!/usr/bin/env bash
# Validate Docker packaging files without requiring a running Docker daemon.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

required=(
  docker/Dockerfile
  docker/docker-compose.yml
  docker/entrypoint.sh
  docker/healthcheck.sh
  docker/requirements-comfy.txt
  docker/patches/onnx_models.py
  docs/DOCKER.md
  docs/ASSETS_MIGRATION.md
  docker/vendor/custom_nodes/ComfyUI-WanVideoWrapper
)

for f in "${required[@]}"; do
  if [[ -d "${f}" ]]; then
    [[ -e "${f}" ]] || { echo "MISSING ${f}" >&2; exit 1; }
  else
    [[ -f "${f}" ]] || { echo "MISSING ${f}" >&2; exit 1; }
  fi
done

python3 -c "import yaml; yaml.safe_load(open('docker/docker-compose.yml'))"
python3 scripts/inventory_assets.py --comfy-root "${COMFYUI_ROOT:-/root/ComfyUI}" >/dev/null

if command -v docker >/dev/null 2>&1; then
  echo "docker found — run: cd docker && docker compose build"
else
  echo "docker not installed on this host — file validation only (OK)"
fi

echo "validate_docker_setup: OK"
