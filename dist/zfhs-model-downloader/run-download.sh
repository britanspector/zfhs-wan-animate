#!/usr/bin/env bash
# One-click: install deps, download all models, verify store.
set -euo pipefail

PKG_ROOT="$(cd "$(dirname "$0")" && pwd)"

resolve_autodl_fs_base() {
  if [[ -d /autodl-fs/data ]]; then
    echo /autodl-fs/data
  elif [[ -d /autodl-fs ]]; then
    echo /autodl-fs
  else
    echo /autodl-fs/data
  fi
}

AUTODL_FS_BASE="$(resolve_autodl_fs_base)"
STORE_PARENT="${AUTODL_FS_BASE}/zfhs-wan-animate"
export ZFHS_MODELS_STORE="${ZFHS_MODELS_STORE:-${STORE_PARENT}/models}"
export HF_HOME="${HF_HOME:-${STORE_PARENT}/.cache/huggingface}"
export MODELSCOPE_CACHE="${MODELSCOPE_CACHE:-${STORE_PARENT}/.cache/modelscope}"

echo "[run-download] ZFHS_MODELS_STORE=${ZFHS_MODELS_STORE}"
echo "[run-download] Installing Python dependencies..."
python3 -m pip install -q -r "${PKG_ROOT}/requirements.txt"

cd "${PKG_ROOT}"
bash scripts/download_models.sh --download-only --skip-network-turbo --no-verify "$@"
python3 scripts/verify_models.py --store "${ZFHS_MODELS_STORE}"
