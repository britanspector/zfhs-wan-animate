#!/usr/bin/env bash
# Download P07 models (HF + ModelScope fallback) into {ZFHS_MODELS_STORE}/
# Then symlink into {COMFYUI_ROOT}/models/ via setup_models.sh (see docs/ASSETS_MIGRATION.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY_ROOT="${COMFYUI_ROOT:-/root/ComfyUI}"

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
MODELS_STORE="${ZFHS_MODELS_STORE:-${AUTODL_FS_BASE}/zfhs-wan-animate/models}"
STORE_PARENT="$(dirname "$MODELS_STORE")"
MANIFEST="${ZFHS_MODEL_MANIFEST:-${ROOT}/manifest/models.yaml}"

export ZFHS_MODELS_STORE="$MODELS_STORE"
export HF_HOME="${HF_HOME:-${STORE_PARENT}/.cache/huggingface}"
export MODELSCOPE_CACHE="${MODELSCOPE_CACHE:-${STORE_PARENT}/.cache/modelscope}"

FORCE=false
DRY_RUN=false
ONLY_IDS=""
NO_CLEANUP_CACHE=false
SKIP_NETWORK_TURBO=false
DO_VERIFY=true
DOWNLOAD_ONLY=false

log_info() { echo "[download_models] $*"; }
log_error() { echo "[download_models] ERROR: $*" >&2; }

usage() {
  cat <<EOF
Usage: bash scripts/download_models.sh [OPTIONS]

Download P07 models into autodl-fs local storage (HF with ModelScope/public HF fallback).
Skips existing regular files in the store unless --force.
After successful download: cleans autodl-fs caches, runs setup_models.sh, verify (default).
Use --download-only on machines without ComfyUI (skip setup/verify_assets).

Options:
  --force                 Remove existing files in the store and re-download
  --dry-run               Print planned actions only
  --only IDS              Comma-separated model ids (e.g. vitpose,yolov10m)
  --download-only         Only download to ZFHS_MODELS_STORE (no ComfyUI symlink/verify_assets)
  --no-cleanup-cache      Skip cache cleanup after successful download
  --skip-network-turbo    Do not source /etc/network_turbo (AutoDL)
  --no-verify             Skip verify_assets.py after download
  --verify                Run verify_assets.py --strict-models (default)
  -h, --help              Show this help

Environment:
  ZFHS_MODELS_STORE       Model entity storage (default: /autodl-fs/data/zfhs-wan-animate/models on AutoDL)
  HF_HOME                 HuggingFace cache (default: sibling .cache/huggingface)
  MODELSCOPE_CACHE        ModelScope cache (default: sibling .cache/modelscope)
  HF_TOKEN                Optional; enables gated HuggingFace repos
  SKIP_NETWORK_TURBO=1    Same as --skip-network-turbo
  COMFYUI_ROOT            ComfyUI install for symlinks (default: /root/ComfyUI)
  ZFHS_MODEL_MANIFEST     Override manifest path (default: manifest/models.yaml)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=true ;;
    --dry-run) DRY_RUN=true ;;
    --no-cleanup-cache) NO_CLEANUP_CACHE=true ;;
    --download-only) DOWNLOAD_ONLY=true; DO_VERIFY=false ;;
    --skip-network-turbo) SKIP_NETWORK_TURBO=true ;;
    --no-verify) DO_VERIFY=false ;;
    --verify) DO_VERIFY=true ;;
    --only)
      shift
      ONLY_IDS="${1:-}"
      if [[ -z "$ONLY_IDS" ]]; then
        log_error "--only requires a comma-separated id list"
        exit 1
      fi
      ;;
    -h|--help) usage; exit 0 ;;
    *) log_error "Unknown option: $1"; usage; exit 1 ;;
  esac
  shift
done

if [[ ! -f "$MANIFEST" ]]; then
  log_error "Manifest not found: $MANIFEST"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  log_error "python3 is required"
  exit 1
fi

if [[ -f /etc/network_turbo && "${SKIP_NETWORK_TURBO}" != "true" && "${SKIP_NETWORK_TURBO:-0}" != "1" ]]; then
  # shellcheck source=/dev/null
  source /etc/network_turbo 2>/dev/null || true
fi

log_info "ComfyUI models root: ${COMFY_ROOT}/models"
mkdir -p "$MODELS_STORE" "$HF_HOME" "$MODELSCOPE_CACHE"

PY_ARGS=(python3 "${ROOT}/scripts/download_models.py" --manifest "$MANIFEST" --store "$MODELS_STORE")
PY_ARGS+=(--hf-home "$HF_HOME" --modelscope-cache "$MODELSCOPE_CACHE")
$FORCE && PY_ARGS+=(--force)
$DRY_RUN && PY_ARGS+=(--dry-run)
$NO_CLEANUP_CACHE && PY_ARGS+=(--no-cleanup-cache)
[[ -n "$ONLY_IDS" ]] && PY_ARGS+=(--only "$ONLY_IDS")

if ! "${PY_ARGS[@]}"; then
  exit 1
fi

if $DRY_RUN; then
  exit 0
fi

if $DOWNLOAD_ONLY; then
  log_info "Download-only mode: skipping ComfyUI setup and verify_assets"
  exit 0
fi

log_info "Linking models into ComfyUI..."
bash "${ROOT}/scripts/setup_models.sh"

if $DO_VERIFY; then
  log_info "Verifying models..."
  python3 "${ROOT}/scripts/verify_assets.py" --strict-models
fi

exit 0
