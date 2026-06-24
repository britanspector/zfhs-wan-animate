#!/usr/bin/env python3
"""Generate asset inventory (models, custom nodes, sizes) for Docker migration docs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def fmt_bytes(n: int) -> str:
    for unit, div in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
        if n >= div:
            return f"{n / div:.2f} {unit}"
    return f"{n} B"


def file_size(path: Path) -> int:
    if not path.exists():
        return -1
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


def dir_size(path: Path) -> int:
    if not path.is_dir():
        return file_size(path)
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            fp = Path(root) / name
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def inventory_models(comfy_root: Path) -> list[dict]:
    data = load_yaml(ROOT / "manifest" / "models.yaml")
    rows: list[dict] = []
    for item in data.get("models", []):
        category = item.get("category", "")
        rel = item.get("path", "")
        full = comfy_root / "models" / category / rel
        sz = file_size(full)
        rows.append(
            {
                "id": item.get("id", ""),
                "path": f"models/{category}/{rel}",
                "size": sz,
                "size_human": fmt_bytes(sz) if sz >= 0 else "MISSING",
                "download_url": item.get("download_url"),
                "exists": full.is_file(),
            }
        )
    return rows


def inventory_nodes(comfy_root: Path) -> list[dict]:
    data = load_yaml(ROOT / "manifest" / "custom_nodes.yaml")
    rows: list[dict] = []
    for item in data.get("required", []):
        name = item.get("name", "")
        full = comfy_root / "custom_nodes" / name
        sz = dir_size(full) if full.exists() else -1
        rows.append(
            {
                "name": name,
                "provides": item.get("provides", ""),
                "size": sz,
                "size_human": fmt_bytes(sz) if sz >= 0 else "MISSING",
                "exists": full.is_dir(),
            }
        )
    return rows


def render_markdown(models: list[dict], nodes: list[dict], comfy_root: Path) -> str:
    model_total = sum(m["size"] for m in models if m["size"] > 0)
    node_total = sum(n["size"] for n in nodes if n["size"] > 0)
    lines = [
        "# P07 资产移植清单",
        "",
        "> 由 `scripts/inventory_assets.py` 自动生成，请勿手工编辑。",
        "",
        f"扫描根目录：`{comfy_root}`",
        "",
        "## 模型文件（需外部挂载，不烘焙进瘦镜像）",
        "",
        f"合计（已存在文件）：**{fmt_bytes(model_total)}**",
        "",
        "| 路径 | 大小 | 下载源 | 状态 |",
        "|------|------|--------|------|",
    ]
    for m in models:
        url = m["download_url"] or "从现有环境复制"
        if url and url != "从现有环境复制" and not url.startswith("http"):
            url = f"HF `{url}`"
        status = "OK" if m["exists"] else "缺失"
        lines.append(f"| `{m['path']}` | {m['size_human']} | {url} | {status} |")

    lines.extend(
        [
            "",
            "### 目标目录结构",
            "",
            "```",
            "models/",
            "├── diffusion_models/Wan/",
            "├── vae/",
            "├── text_encoders/",
            "├── clip_vision/",
            "├── loras/Wan/",
            "└── detection/",
            "```",
            "",
            "## Custom Nodes（烘焙进 Docker 镜像）",
            "",
            f"合计：**{fmt_bytes(node_total)}**",
            "",
            "| 目录 | 大小 | 提供节点 | 状态 |",
            "|------|------|----------|------|",
        ]
    )
    for n in nodes:
        status = "OK" if n["exists"] else "缺失"
        lines.append(f"| `{n['name']}` | {n['size_human']} | {n['provides']} | {status} |")

    lines.extend(
        [
            "",
            "## 运行时数据卷",
            "",
            "| 容器路径 | 用途 |",
            "|----------|------|",
            "| `/app/ComfyUI/models` | 模型权重（只读挂载） |",
            "| `/app/ComfyUI/input` | 上传图/视频 |",
            "| `/app/ComfyUI/output` | 生成结果 |",
            "| `/app/data` | API 任务历史 `jobs.json` |",
            "",
            "## 示例素材（可选）",
            "",
            "- `input/image (17).png`",
            "- `input/5053929f1d2c2ef117a3a8b8c02075c7da53e5380365bc2f8a87992986058e39.mp4`（需含音轨）",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory P07 assets for Docker migration")
    parser.add_argument(
        "--comfy-root",
        default=os.environ.get("COMFYUI_ROOT", "/root/ComfyUI"),
        help="ComfyUI root directory",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write docs/ASSETS_MIGRATION.md",
    )
    args = parser.parse_args()
    comfy_root = Path(args.comfy_root)

    models = inventory_models(comfy_root)
    nodes = inventory_nodes(comfy_root)
    md = render_markdown(models, nodes, comfy_root)
    print(md)

    if args.write:
        out = ROOT / "docs" / "ASSETS_MIGRATION.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"\nWrote {out}", file=sys.stderr)

    missing_models = sum(1 for m in models if not m["exists"])
    missing_nodes = sum(1 for n in nodes if not n["exists"])
    return 1 if missing_models or missing_nodes else 0


if __name__ == "__main__":
    raise SystemExit(main())
