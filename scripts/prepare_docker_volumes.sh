#!/usr/bin/env bash
# Symlink host ComfyUI models into docker/volumes/models for local compose testing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY_ROOT="${COMFYUI_ROOT:-/root/ComfyUI}"
DST="${ROOT}/docker/volumes/models"

log() { echo "[prepare_docker_volumes] $*"; }

log "Ensuring P07 model symlinks under ${COMFY_ROOT}/models ..."
bash "${ROOT}/scripts/setup_models.sh"

SRC="${COMFY_ROOT}/models"
if [[ ! -d "${SRC}" ]]; then
  echo "Source models dir not found: ${SRC}" >&2
  exit 1
fi

mkdir -p "${DST}"
log "Linking ${SRC}/* -> ${DST}/"
shopt -s nullglob
for item in "${SRC}"/*; do
  name="$(basename "${item}")"
  target="${DST}/${name}"
  if [[ -e "${target}" || -L "${target}" ]]; then
    continue
  fi
  ln -s "${item}" "${target}"
done
log "Done. Run: cd docker && docker compose up -d"
