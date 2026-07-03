#!/usr/bin/env python3
"""Generate asset inventory (models, custom nodes, workflow nodes) for migration docs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# class_type -> custom node package (built-in nodes listed explicitly)
NODE_PACKAGE_MAP: dict[str, str] = {
    "LoadImage": "ComfyUI 内置",
    "CLIPVisionLoader": "ComfyUI 内置",
    "ImageFromBatch": "ComfyUI 内置",
    "ImageBatch": "ComfyUI 内置",
    "RepeatImageBatch": "ComfyUI 内置",
    "PrimitiveFloat": "ComfyUI 内置",
    "WanVideoModelLoader": "ComfyUI-WanVideoWrapper",
    "WanVideoSampler": "ComfyUI-WanVideoWrapper",
    "WanVideoDecode": "ComfyUI-WanVideoWrapper",
    "WanVideoVAELoader": "ComfyUI-WanVideoWrapper",
    "WanVideoTextEncodeCached": "ComfyUI-WanVideoWrapper",
    "WanVideoClipVisionEncode": "ComfyUI-WanVideoWrapper",
    "WanVideoAnimateEmbeds": "ComfyUI-WanVideoWrapper",
    "WanVideoBlockSwap": "ComfyUI-WanVideoWrapper",
    "WanVideoLoraSelectMulti": "ComfyUI-WanVideoWrapper",
    "WanVideoContextOptions": "ComfyUI-WanVideoWrapper",
    "WanVideoSetLoRAs": "ComfyUI-WanVideoWrapper",
    "WanVideoSetBlockSwap": "ComfyUI-WanVideoWrapper",
    "OnnxDetectionModelLoader": "ComfyUI-WanAnimatePreprocess",
    "PoseAndFaceDetection": "ComfyUI-WanAnimatePreprocess",
    "DrawViTPose": "ComfyUI-WanAnimatePreprocess",
    "ImageResizeKJv2": "ComfyUI-KJNodes",
    "INTConstant": "ComfyUI-KJNodes",
    "VHS_LoadVideo": "ComfyUI-VideoHelperSuite",
    "VHS_VideoCombine": "ComfyUI-VideoHelperSuite",
    "VHS_VideoInfo": "ComfyUI-VideoHelperSuite",
    "easy mathInt": "ComfyUI-Easy-Use",
    "ReservedVRAMSetter": "reservedvram",
    "VRAMCleanup": "comfyui_memory_cleanup",
    "BatchCount+": "ComfyUI_essentials",
}


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


def load_autodl_sources() -> dict[str, str]:
    data = load_yaml(ROOT / "manifest" / "model_sources.autodl.yaml")
    return {item["id"]: item.get("source", "") for item in data.get("models", [])}


def model_link_info(path: Path) -> tuple[str, str]:
    """Return (link_type, resolved_target)."""
    if not path.exists():
        return "missing", ""
    if path.is_symlink():
        try:
            target = os.readlink(path)
            resolved = str(path.resolve())
            if "/autodl-fs/" in target or "/autodl-fs/" in resolved:
                return "symlink_autodl_fs", resolved
            if target.startswith("/.autodl") or resolved.startswith("/.autodl"):
                return "symlink_public", resolved
            return "symlink", resolved
        except OSError:
            return "symlink", ""
    if path.is_file():
        return "file", str(path.resolve())
    return "missing", ""


def inventory_models(comfy_root: Path) -> list[dict]:
    data = load_yaml(ROOT / "manifest" / "models.yaml")
    autodl_sources = load_autodl_sources()
    rows: list[dict] = []
    for item in data.get("models", []):
        model_id = item.get("id", "")
        category = item.get("category", "")
        rel = item.get("path", "")
        full = comfy_root / "models" / category / rel
        sz = file_size(full)
        link_type, link_target = model_link_info(full)
        sources = item.get("download_sources") or []
        fallback_count = max(0, len(sources) - 1) if sources else 0
        rows.append(
            {
                "id": model_id,
                "path": f"models/{category}/{rel}",
                "size": sz,
                "size_human": fmt_bytes(sz) if sz >= 0 else "MISSING",
                "download_url": item.get("download_url"),
                "download_sources_count": len(sources),
                "fallback_count": fallback_count,
                "autodl_source": autodl_sources.get(model_id, ""),
                "storage": "autodl_fs",
                "link_type": link_type,
                "link_target": link_target,
                "exists": link_type != "missing",
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
                "storage": "system_disk",
                "exists": full.is_dir(),
            }
        )
    return rows


def inventory_workflow_nodes() -> dict[str, list[str]]:
    class_types: set[str] = set()
    for wf in sorted((ROOT / "workflows").glob("p07_animate_v*.json")):
        with wf.open(encoding="utf-8") as f:
            data = json.load(f)
        for node in data.values():
            if isinstance(node, dict) and "class_type" in node:
                class_types.add(node["class_type"])

    grouped: dict[str, list[str]] = {}
    for ct in sorted(class_types):
        pkg = NODE_PACKAGE_MAP.get(ct, "未知")
        grouped.setdefault(pkg, []).append(ct)
    return grouped


def link_status_label(m: dict) -> str:
    lt = m["link_type"]
    if lt == "symlink_autodl_fs":
        return "软链→autodl-fs"
    if lt == "symlink_public":
        return "软链→公共缓存"
    if lt == "symlink":
        return "软链"
    if lt == "file":
        return "实体文件"
    return "缺失"


def render_markdown(
    models: list[dict],
    nodes: list[dict],
    workflow_nodes: dict[str, list[str]],
    comfy_root: Path,
) -> str:
    model_total = sum(m["size"] for m in models if m["size"] > 0)
    node_total = sum(n["size"] for n in nodes if n["size"] > 0)
    wf_count = sum(len(v) for v in workflow_nodes.values())

    lines = [
        "# P07 资产清单",
        "",
        "> 由 `scripts/inventory_assets.py` 自动生成。修改分类逻辑请编辑该脚本后执行",
        "> `python3 scripts/inventory_assets.py --write` 重新生成。",
        "",
        f"扫描 ComfyUI 根目录：`{comfy_root}`",
        "",
        "## 概述",
        "",
        "P07 共依赖 **11 个模型文件**（约 33.5GB）、**8 个 custom node 包**、**30 个工作流节点类型**（v4/v5 共用）。",
        "",
        "模型**实体**存放在 autodl-fs 共享盘（`/root/autodl-fs/zfhs-wan-animate/models/`），",
        "`{COMFYUI_ROOT}/models/` 下仅为软链，**不占实例系统盘**。Custom nodes、项目代码、输入输出在**系统盘**。",
        "",
        "首次部署运行 `bash scripts/download_models.sh`（HF 优先，失败自动回退 ModelScope/公开 HF 备用源，成功后清理 autodl-fs 缓存）；换实例后运行 `bash scripts/setup_models.sh` 刷新软链。",
        "",
        "## 存储位置总览",
        "",
        "| 资产类型 | 实体位置 | ComfyUI 可见路径 | 说明 |",
        "|----------|----------|------------------|------|",
        "| 模型权重（11） | autodl-fs 本地存储 | `models/` 软链 | `scripts/download_models.sh` / `setup_models.sh` |",
        "| Custom nodes（8） | 实例系统盘 | `custom_nodes/` | 镜像预装或 `install_custom_nodes.sh` |",
        "| 工作流 JSON | 项目 Git（系统盘） | — | `workflows/p07_animate_v*.json` |",
        "| 上传/输出 | 实例系统盘 | `input/`、`output/` | 运行时数据 |",
        "| API 任务历史 | 实例系统盘 | `wan-animate-api/data/` | `jobs.json` |",
        "",
        "## 模型文件",
        "",
        f"合计（已解析文件大小）：**{fmt_bytes(model_total)}**",
        "",
        "实体均在 **autodl-fs**；下表「存储源」来自 `manifest/model_sources.autodl.yaml`。",
        "",
        "| ID | 相对路径 | 大小 | 存储源 | HF 主源 | 备用源 | 链接状态 |",
        "|----|----------|------|--------|---------|--------|----------|",
    ]

    for m in models:
        url = m["download_url"] or "—"
        if url != "—" and not str(url).startswith("http"):
            url = f"`{url}`"
        source = m["autodl_source"] or "—"
        if len(source) > 48:
            source = "…" + source[-46:]
        fallback = (
            f"{m['fallback_count']} 个" if m.get("fallback_count", 0) > 0 else "—"
        )
        lines.append(
            f"| `{m['id']}` | `{m['path']}` | {m['size_human']} | `{source}` | {url} | {fallback} | {link_status_label(m)} |"
        )

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
            "### 部署命令",
            "",
            "| 场景 | 命令 |",
            "|------|------|",
            "| 首次部署 / 缺模型实体 | `bash scripts/download_models.sh` |",
            "| 换实例后刷新软链 | `bash scripts/setup_models.sh` |",
            "| 强制重新下载某个模型 | `bash scripts/download_models.sh --force --only <id>` |",
            "| 跳过清缓存（调试） | `bash scripts/download_models.sh --no-cleanup-cache` |",
            "| 验收 | `python3 scripts/verify_assets.py --strict-models` |",
            "",
            "## Custom Nodes（系统盘）",
            "",
            f"合计：**{fmt_bytes(node_total)}**",
            "",
            "路径：`{COMFYUI_ROOT}/custom_nodes/`。缺失时从 `docker/vendor/custom_nodes/` 复制。",
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
            f"## 工作流节点（v4/v5 共用，共 {wf_count} 个 class_type）",
            "",
            "自 `workflows/p07_animate_v4.json` / `p07_animate_v5.json` 提取，按 custom node 包分组。",
            "",
        ]
    )
    for pkg in sorted(workflow_nodes.keys(), key=lambda x: (x != "ComfyUI 内置", x)):
        nodes_list = ", ".join(f"`{n}`" for n in workflow_nodes[pkg])
        lines.append(f"- **{pkg}**：{nodes_list}")

    lines.extend(
        [
            "",
            "## 项目内资产（系统盘 / Git）",
            "",
            "| 路径 | 说明 |",
            "|------|------|",
            f"| `{ROOT}` | 项目源码、manifest、API/Web |",
            "| `workflows/p07_animate_v4.json` | 标准动作迁移工作流 |",
            "| `workflows/p07_animate_v5.json` | 保身份动作迁移工作流 |",
            "| `manifest/models.yaml` | 模型清单与多源下载配置（`download_sources`） |",
            "| `manifest/model_sources.autodl.yaml` | autodl-fs 本地存储路径映射 |",
            "",
            "## 运行时数据（系统盘）",
            "",
            "| 路径 | 用途 |",
            "|------|------|",
            f"| `{comfy_root}/input` | 上传图/视频 |",
            f"| `{comfy_root}/output` | 生成结果 |",
            f"| `{ROOT}/wan-animate-api/data/jobs.json` | API 任务历史 |",
            "",
            "Docker 容器内对应：`/app/ComfyUI/models`（只读挂载）、`/app/ComfyUI/input`、`/app/ComfyUI/output`、`/app/data`。",
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
    parser = argparse.ArgumentParser(description="Inventory P07 assets for migration docs")
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
    workflow_nodes = inventory_workflow_nodes()
    md = render_markdown(models, nodes, workflow_nodes, comfy_root)
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
