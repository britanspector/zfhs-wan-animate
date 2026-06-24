#!/usr/bin/env bash
# Install or verify P07 custom nodes under {COMFYUI_ROOT}/custom_nodes/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY_ROOT="${COMFYUI_ROOT:-/root/ComfyUI}"
VENDOR_ROOT="${ROOT}/docker/vendor/custom_nodes"
MANIFEST="${ROOT}/manifest/custom_nodes.yaml"
MODE="check-only"

log_info() { echo "[install_custom_nodes] $*"; }
log_warn() { echo "[install_custom_nodes] WARN: $*" >&2; }

usage() {
  cat <<EOF
Usage: bash scripts/install_custom_nodes.sh [OPTIONS]

Options:
  --check-only        Only report missing nodes (default)
  --install-missing   Copy missing nodes from docker/vendor/custom_nodes/
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) MODE="check-only" ;;
    --install-missing) MODE="install-missing" ;;
    -h|--help) usage; exit 0 ;;
    *) log_warn "Unknown option: $1"; usage; exit 1 ;;
  esac
  shift
done

if [[ ! -f "$MANIFEST" ]]; then
  log_warn "Manifest not found: $MANIFEST"
  exit 0
fi

mapfile -t NODE_NAMES < <(python3 - "$MANIFEST" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

for item in data.get("required", []):
    name = item.get("name", "")
    if name:
        print(name)
PY
)

missing=()
installed=0

for name in "${NODE_NAMES[@]}"; do
  target="${COMFY_ROOT}/custom_nodes/${name}"
  if [[ -d "$target" ]]; then
    log_info "OK: $name"
    continue
  fi

  missing+=("$name")

  if [[ "$MODE" != "install-missing" ]]; then
    log_warn "Missing: $name"
    continue
  fi

  src="${VENDOR_ROOT}/${name}"
  if [[ ! -d "$src" ]]; then
    log_warn "Missing and no vendor copy: $name (run scripts/prepare_docker_build.sh on a machine with ComfyUI)"
    continue
  fi

  mkdir -p "$(dirname "$target")"
  cp -a "$src" "$target"
  log_info "Installed from vendor: $name"
  installed=$((installed + 1))
done

if [[ ${#missing[@]} -gt 0 && "$MODE" == "check-only" ]]; then
  log_warn "${#missing[@]} custom node(s) missing under ${COMFY_ROOT}/custom_nodes/"
  log_warn "On compatible AutoDL images they are usually pre-installed."
  log_warn "Otherwise run: bash scripts/install_custom_nodes.sh --install-missing"
  exit 0
fi

if [[ "$MODE" == "install-missing" ]]; then
  log_info "Installed ${installed} node(s), still missing: $((${#missing[@]} - installed))"
fi

exit 0
