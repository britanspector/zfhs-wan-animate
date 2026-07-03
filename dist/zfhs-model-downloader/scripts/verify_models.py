#!/usr/bin/env python3
"""Verify P07 model files exist in ZFHS_MODELS_STORE (no ComfyUI required)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_MIN_BYTES = 1_000_000


def default_models_store() -> Path:
    env = os.environ.get("ZFHS_MODELS_STORE")
    if env:
        return Path(env)
    if Path("/autodl-fs/data").is_dir():
        return Path("/autodl-fs/data/zfhs-wan-animate/models")
    return Path("/autodl-fs/zfhs-wan-animate/models")


def load_yaml(path: Path) -> dict:
    import yaml

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Verify models in ZFHS_MODELS_STORE")
    parser.add_argument(
        "--store",
        default=os.environ.get("ZFHS_MODELS_STORE") or str(default_models_store()),
        help="Model entity storage directory",
    )
    parser.add_argument(
        "--manifest",
        default=os.environ.get("ZFHS_MODEL_MANIFEST", str(root / "manifest" / "models.yaml")),
        help="Path to models.yaml",
    )
    args = parser.parse_args()

    store = Path(args.store).resolve()
    manifest = Path(args.manifest)
    if not manifest.is_file():
        print(f"[verify_models] ERROR: manifest not found: {manifest}", file=sys.stderr)
        return 1

    data = load_yaml(manifest)
    ok: list[str] = []
    errors: list[str] = []

    for item in data.get("models", []):
        model_id = item.get("id", "")
        category = item.get("category", "")
        rel = item.get("path", "")
        min_size = int(item.get("min_size_bytes", DEFAULT_MIN_BYTES))
        target = store / category / rel
        label = f"{category}/{rel}"

        if not target.is_file() or target.is_symlink():
            errors.append(f"missing: {label} ({target})")
            continue
        size = target.stat().st_size
        if size < min_size:
            errors.append(f"too small: {label} ({size} < {min_size} bytes)")
            continue
        ok.append(f"{model_id}: {label} ({size} bytes)")

    print(f"=== verify_models ({len(ok)} ok, {len(errors)} errors) ===")
    for line in ok:
        print(f"  OK   {line}")
    for line in errors:
        print(f"  FAIL {line}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
