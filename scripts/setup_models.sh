#!/usr/bin/env bash
# Symlink P07 models from AutoDL platform cache into {COMFYUI_ROOT}/models/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY_ROOT="${COMFYUI_ROOT:-/root/ComfyUI}"
MANIFEST="${ZFHS_MODEL_SOURCES:-${ROOT}/manifest/model_sources.autodl.yaml}"
STRICT=false

log_info() { echo "[setup_models] $*"; }
log_warn() { echo "[setup_models] WARN: $*" >&2; }
log_error() { echo "[setup_models] ERROR: $*" >&2; }

usage() {
  cat <<EOF
Usage: bash scripts/setup_models.sh [OPTIONS]

Symlink P07 model files from AutoDL cache into ComfyUI models directory.

Options:
  --strict    Exit 1 if any source is missing or link fails
  -h, --help  Show this help

Environment:
  COMFYUI_ROOT        ComfyUI install (default: /root/ComfyUI)
  ZFHS_MODEL_SOURCES  Override manifest path
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) STRICT=true ;;
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
  log_error "python3 is required to parse $MANIFEST"
  exit 1
fi

mapfile -t ENTRIES < <(python3 - "$MANIFEST" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

for item in data.get("models", []):
    category = item.get("category", "")
    rel = item.get("path", "")
    source = item.get("source", "")
    if category and rel and source:
        print(f"{category}\t{rel}\t{source}")
PY
)

if [[ ${#ENTRIES[@]} -eq 0 ]]; then
  log_error "No model entries found in $MANIFEST"
  exit 1
fi

created=0
skipped=0
missing=0
errors=0

link_model() {
  local category="$1"
  local rel="$2"
  local source="$3"
  local target="${COMFY_ROOT}/models/${category}/${rel}"

  if [[ ! -e "$source" ]]; then
    log_warn "Source missing, skip: $source -> $target"
    missing=$((missing + 1))
    return 0
  fi

  mkdir -p "$(dirname "$target")"

  if [[ -L "$target" ]]; then
    local current_target source_real
    current_target="$(readlink -f "$target" 2>/dev/null || true)"
    source_real="$(readlink -f "$source" 2>/dev/null || true)"
    if [[ -n "$current_target" && "$current_target" == "$source_real" ]]; then
      log_info "Already linked: $target"
      skipped=$((skipped + 1))
      return 0
    fi
    log_info "Relinking: $target"
    rm -f "$target"
  elif [[ -e "$target" ]]; then
    log_warn "Target exists and is not a symlink, skip: $target"
    skipped=$((skipped + 1))
    return 0
  fi

  if ln -s "$source" "$target"; then
    log_info "Linked: $source -> $target"
    created=$((created + 1))
  else
    log_error "Failed to link: $source -> $target"
    errors=$((errors + 1))
  fi
}

log_info "Manifest: $MANIFEST"
log_info "ComfyUI models root: ${COMFY_ROOT}/models"

for entry in "${ENTRIES[@]}"; do
  IFS=$'\t' read -r category rel source <<<"$entry"
  link_model "$category" "$rel" "$source"
done

echo ""
log_info "Done: created=${created} skipped=${skipped} missing=${missing} errors=${errors}"

if [[ $errors -gt 0 ]]; then
  exit 1
fi

if $STRICT && [[ $missing -gt 0 ]]; then
  log_error "Strict mode: $missing model source(s) missing from AutoDL cache"
  log_error "Ensure you are on a compatible AutoDL image or update manifest/model_sources.autodl.yaml"
  exit 1
fi

exit 0
