#!/usr/bin/env bash
# Copy P07 custom nodes from host ComfyUI into docker/vendor for self-contained builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_ROOT="${COMFYUI_ROOT:-/root/ComfyUI}/custom_nodes"
DST_ROOT="${ROOT}/docker/vendor/custom_nodes"

nodes=(
  ComfyUI-WanVideoWrapper
  ComfyUI-WanAnimatePreprocess
  ComfyUI-KJNodes
  ComfyUI-VideoHelperSuite
  ComfyUI-Easy-Use
  reservedvram
  comfyui_memory_cleanup
  ComfyUI_essentials
)

mkdir -p "${DST_ROOT}"
for name in "${nodes[@]}"; do
  src="${SRC_ROOT}/${name}"
  dst="${DST_ROOT}/${name}"
  if [[ ! -d "${src}" ]]; then
    echo "Missing custom node: ${src}" >&2
    exit 1
  fi
  rm -rf "${dst}"
  cp -a "${src}" "${dst}"
  echo "Copied ${name}"
done

echo "Vendor custom nodes ready at ${DST_ROOT}"
