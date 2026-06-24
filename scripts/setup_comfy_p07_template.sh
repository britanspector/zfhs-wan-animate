#!/bin/bash
# Symlink P07 UI workflow for ComfyUI ?template= URL loading.
# URL: http://127.0.0.1:6006/?template=p07_wan22_animate_v4&source=zealman-workflow-templates
set -e

P07_UI_SRC="/root/zealman-app/comfyui-workflows/P视频-动作迁移/P07-动作迁移-Wan2.2AnimateV4.json"
TEMPLATE_DIR="/root/ComfyUI/custom_nodes/zealman-workflow-templates/example_workflows"
TEMPLATE_LINK="${TEMPLATE_DIR}/p07_wan22_animate_v4.json"

mkdir -p "$TEMPLATE_DIR"
touch /root/ComfyUI/custom_nodes/zealman-workflow-templates/__init__.py

if [ ! -f "$P07_UI_SRC" ]; then
  echo "ERROR: P07 UI workflow not found: $P07_UI_SRC" >&2
  exit 1
fi

ln -sf "$P07_UI_SRC" "$TEMPLATE_LINK"
echo "Linked: $TEMPLATE_LINK -> $P07_UI_SRC"
echo "Open: http://127.0.0.1:6006/?template=p07_wan22_animate_v4&source=zealman-workflow-templates"
echo "Restart ComfyUI if it was already running."
