#!/usr/bin/env bash
# Download P07 model files from Hugging Face into {COMFYUI_ROOT}/models/
# Use when AutoDL public cache is unavailable (see docs/ASSETS_MIGRATION.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY_ROOT="${COMFYUI_ROOT:-/root/ComfyUI}"
MANIFEST="${ZFHS_MODEL_MANIFEST:-${ROOT}/manifest/models.yaml}"
FORCE=false
DRY_RUN=false
ONLY_IDS=""

log_info() { echo "[download_models] $*"; }
log_warn() { echo "[download_models] WARN: $*" >&2; }
log_error() { echo "[download_models] ERROR: $*" >&2; }

usage() {
  cat <<EOF
Usage: bash scripts/download_models.sh [OPTIONS]

Download P07 models from Hugging Face into ComfyUI models directory.
Skips existing regular files and valid public-cache symlinks unless --force.

Options:
  --force       Remove symlinks/existing files and re-download
  --dry-run     Print planned actions only
  --only IDS    Comma-separated model ids (e.g. vitpose,yolov10m)
  -h, --help    Show this help

Environment:
  COMFYUI_ROOT          ComfyUI install (default: /root/ComfyUI)
  ZFHS_MODEL_MANIFEST   Override manifest path (default: manifest/models.yaml)

After download:
  python3 scripts/verify_assets.py --strict-models
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=true ;;
    --dry-run) DRY_RUN=true ;;
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

mapfile -t ENTRIES < <(python3 - "$MANIFEST" "$ONLY_IDS" <<'PY'
import sys
import yaml

manifest_path, only_raw = sys.argv[1], sys.argv[2]
only = {x.strip() for x in only_raw.split(",") if x.strip()} if only_raw else set()

with open(manifest_path, encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

for item in data.get("models", []):
    mid = item.get("id", "")
    if only and mid not in only:
        continue
    category = item.get("category", "")
    rel = item.get("path", "")
    url = item.get("download_url") or ""
    print(f"{mid}\t{category}\t{rel}\t{url}")
PY
)

if [[ ${#ENTRIES[@]} -eq 0 ]]; then
  log_error "No model entries matched in $MANIFEST"
  exit 1
fi

is_public_symlink() {
  local target="$1"
  [[ -L "$target" ]] || return 1
  local link dest
  link="$(readlink "$target" 2>/dev/null || true)"
  dest="$(readlink -f "$target" 2>/dev/null || true)"
  [[ "$link" == /.autodl* || "$dest" == /.autodl* ]]
}

download_hf() {
  local repo_file="$1"
  local dest_dir="$2"
  local filename="$3"

  local repo="${repo_file%/*}"
  local file_in_repo="${repo_file#*/}"

  if [[ -z "$repo" || -z "$file_in_repo" || "$repo" == "$file_in_repo" ]]; then
    log_error "Invalid download_url format (expected repo_id/path): $repo_file"
    return 1
  fi

  mkdir -p "$dest_dir"

  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$repo" "$file_in_repo" --local-dir "$dest_dir" --local-dir-use-symlinks False
    return 0
  fi

  if command -v hf >/dev/null 2>&1; then
    hf download "$repo" "$file_in_repo" --local-dir "$dest_dir"
    return 0
  fi

  python3 - "$repo" "$file_in_repo" "$dest_dir" "$filename" <<'PY'
import sys
from pathlib import Path

repo, file_in_repo, dest_dir, filename = sys.argv[1:5]
try:
    from huggingface_hub import hf_hub_download
except ImportError as e:
    print("huggingface_hub not installed; pip install huggingface_hub", file=sys.stderr)
    raise SystemExit(1) from e

path = hf_hub_download(repo_id=repo, filename=file_in_repo, local_dir=dest_dir)
out = Path(dest_dir) / filename
src = Path(path)
if src.resolve() != out.resolve():
    if out.exists() or out.is_symlink():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.symlink_to(src.resolve())
PY
}

downloaded=0
skipped=0
failed=0

log_info "Manifest: $MANIFEST"
log_info "ComfyUI models root: ${COMFY_ROOT}/models"
$DRY_RUN && log_info "DRY RUN — no files will change"

for entry in "${ENTRIES[@]}"; do
  IFS=$'\t' read -r mid category rel url <<<"$entry"
  target="${COMFY_ROOT}/models/${category}/${rel}"
  filename="$(basename "$rel")"
  dest_dir="$(dirname "$target")"

  if [[ -z "$url" ]]; then
    log_error "No download_url for model id=${mid}"
    failed=$((failed + 1))
    continue
  fi

  if [[ -f "$target" && ! -L "$target" ]] && ! $FORCE; then
    log_info "Skip (file exists): $target"
    skipped=$((skipped + 1))
    continue
  fi

  if is_public_symlink "$target" && ! $FORCE; then
    log_info "Skip (public-cache symlink): $target -> $(readlink -f "$target")"
    skipped=$((skipped + 1))
    continue
  fi

  if $DRY_RUN; then
    log_info "Would download: $mid -> $target (from HF $url)"
    if $FORCE && [[ -e "$target" || -L "$target" ]]; then
      log_info "  would remove: $target"
    fi
    downloaded=$((downloaded + 1))
    continue
  fi

  if $FORCE && [[ -e "$target" || -L "$target" ]]; then
    log_info "Removing: $target"
    rm -f "$target"
  fi

  log_info "Downloading: $mid ($url)"
  if download_hf "$url" "$dest_dir" "$filename"; then
    downloaded=$((downloaded + 1))
  else
    log_error "Failed: $mid"
    failed=$((failed + 1))
  fi
done

echo ""
log_info "Done: downloaded=${downloaded} skipped=${skipped} failed=${failed}"

if [[ $failed -gt 0 ]]; then
  exit 1
fi

if ! $DRY_RUN; then
  log_info "Verify: python3 scripts/verify_assets.py --strict-models"
fi

exit 0
