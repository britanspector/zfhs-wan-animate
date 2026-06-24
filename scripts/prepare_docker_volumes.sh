#!/usr/bin/env bash
# Symlink host ComfyUI models into docker/volumes/models for local compose testing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${COMFYUI_ROOT:-/root/ComfyUI}/models"
DST="${ROOT}/docker/volumes/models"

if [[ ! -d "${SRC}" ]]; then
  echo "Source models dir not found: ${SRC}" >&2
  exit 1
fi

mkdir -p "${DST}"
echo "Linking ${SRC}/* -> ${DST}/"
shopt -s nullglob
for item in "${SRC}"/*; do
  name="$(basename "${item}")"
  target="${DST}/${name}"
  if [[ -e "${target}" || -L "${target}" ]]; then
    continue
  fi
  ln -s "${item}" "${target}"
done
echo "Done. Run: cd docker && docker compose up -d"
