#!/usr/bin/env python3
"""Download P07 models from manifest with HF / ModelScope fallback and cache cleanup."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_MIN_BYTES = 1_000_000


def default_models_store() -> Path:
    env = os.environ.get("ZFHS_MODELS_STORE")
    if env:
        return Path(env)
    if Path("/autodl-fs/data").is_dir():
        return Path("/autodl-fs/data/zfhs-wan-animate/models")
    return Path("/autodl-fs/zfhs-wan-animate/models")


@dataclass
class DownloadSource:
    provider: str
    repo: str = ""
    file: str = ""
    model_id: str = ""
    file_path: str = ""

    def label(self) -> str:
        if self.provider == "hf":
            return f"hf:{self.repo}/{self.file}"
        if self.provider == "modelscope":
            return f"modelscope:{self.model_id}/{self.file_path}"
        return self.provider


@dataclass
class ModelEntry:
    model_id: str
    category: str
    rel_path: str
    min_size_bytes: int
    sources: list[DownloadSource]


@dataclass
class ModelResult:
    model_id: str
    status: str  # downloaded | skipped | failed | dry_run
    target: str = ""
    message: str = ""
    cache_paths: list[str] = field(default_factory=list)


def log_info(msg: str) -> None:
    print(f"[download_models] {msg}")


def log_warn(msg: str) -> None:
    print(f"[download_models] WARN: {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[download_models] ERROR: {msg}", file=sys.stderr)


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_hf_url(url: str) -> DownloadSource | None:
    parts = url.strip().split("/")
    if len(parts) < 3:
        return None
    return DownloadSource(provider="hf", repo=f"{parts[0]}/{parts[1]}", file="/".join(parts[2:]))


def parse_source(raw: dict[str, Any]) -> DownloadSource | None:
    provider = str(raw.get("provider", "")).strip().lower()
    if provider == "hf":
        repo = str(raw.get("repo", "")).strip()
        file = str(raw.get("file", "")).strip()
        if repo and file:
            return DownloadSource(provider="hf", repo=repo, file=file)
        return None
    if provider == "modelscope":
        model_id = str(raw.get("model_id", "")).strip()
        file_path = str(raw.get("file_path", "")).strip()
        if model_id and file_path:
            return DownloadSource(provider="modelscope", model_id=model_id, file_path=file_path)
        return None
    return None


def load_models(manifest_path: Path, only_ids: set[str]) -> list[ModelEntry]:
    data = load_yaml(manifest_path)
    entries: list[ModelEntry] = []
    for item in data.get("models", []):
        mid = str(item.get("id", "")).strip()
        if only_ids and mid not in only_ids:
            continue
        category = str(item.get("category", "")).strip()
        rel = str(item.get("path", "")).strip()
        min_size = int(item.get("min_size_bytes", DEFAULT_MIN_BYTES))

        sources: list[DownloadSource] = []
        for raw in item.get("download_sources") or []:
            src = parse_source(raw)
            if src:
                sources.append(src)
        if not sources:
            url = str(item.get("download_url", "")).strip()
            src = parse_hf_url(url) if url else None
            if src:
                sources.append(src)

        if not rel or not sources:
            log_warn(f"Skipping invalid manifest entry id={mid!r}")
            continue
        entries.append(
            ModelEntry(
                model_id=mid,
                category=category,
                rel_path=rel,
                min_size_bytes=min_size,
                sources=sources,
            )
        )
    return entries


def download_hf(source: DownloadSource) -> Path:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as e:
        raise RuntimeError("huggingface_hub not installed; pip install huggingface_hub") from e

    path = hf_hub_download(repo_id=source.repo, filename=source.file)
    return Path(path).resolve()


def download_modelscope(source: DownloadSource) -> Path:
    try:
        from modelscope.hub.file_download import model_file_download
    except ImportError as e:
        raise RuntimeError("modelscope not installed; pip install modelscope") from e

    path = model_file_download(model_id=source.model_id, file_path=source.file_path)
    return Path(path).resolve()


def is_retryable_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    retry_tokens = (
        "401",
        "403",
        "404",
        "gated",
        "unauthorized",
        "not found",
        "connection",
        "timeout",
        "timed out",
        "network",
        "repository not found",
        "does not exist",
    )
    if any(t in msg for t in retry_tokens):
        return True
    name = type(exc).__name__.lower()
    return any(t in name for t in ("http", "gated", "notfound", "connection", "timeout"))


def download_from_source(source: DownloadSource) -> Path:
    if source.provider == "hf":
        return download_hf(source)
    if source.provider == "modelscope":
        return download_modelscope(source)
    raise ValueError(f"Unknown provider: {source.provider}")


def copy_to_target(src: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)


def process_model(
    entry: ModelEntry,
    store: Path,
    *,
    force: bool,
    dry_run: bool,
) -> ModelResult:
    target = (store / entry.category / entry.rel_path).resolve()
    result = ModelResult(model_id=entry.model_id, status="failed", target=str(target))

    if target.is_file() and not target.is_symlink() and not force:
        if target.stat().st_size >= entry.min_size_bytes:
            result.status = "skipped"
            result.message = f"exists ({target.stat().st_size} bytes)"
            return result

    if dry_run:
        labels = ", ".join(s.label() for s in entry.sources)
        result.status = "dry_run"
        result.message = f"would download from [{labels}]"
        return result

    if force and target.exists():
        log_info(f"Removing: {target}")
        target.unlink()

    last_err = ""
    for source in entry.sources:
        log_info(f"Trying {entry.model_id}: {source.label()}")
        try:
            src = download_from_source(source)
            copy_to_target(src, target)
            size = target.stat().st_size
            if size < entry.min_size_bytes:
                target.unlink(missing_ok=True)
                raise RuntimeError(
                    f"file too small after copy ({size} < {entry.min_size_bytes})"
                )
            result.status = "downloaded"
            result.message = f"ok via {source.label()} ({size} bytes)"
            result.cache_paths.append(str(src))
            return result
        except Exception as e:
            last_err = f"{source.label()}: {type(e).__name__}: {e}"
            log_warn(f"Source failed for {entry.model_id}: {last_err}")
            if not is_retryable_error(e):
                log_warn(f"Non-retryable error, skipping remaining sources for {entry.model_id}")
                break

    result.message = last_err or "no sources succeeded"
    return result


def cleanup_caches(
    store: Path,
    hf_home: Path,
    modelscope_cache: Path,
    results: list[ModelResult],
) -> None:
    """Remove download caches under autodl-fs after successful deployment."""
    completed = [
        r for r in results if r.status in ("downloaded", "skipped") and r.target
    ]
    if not completed:
        return

    target_paths = {Path(r.target).resolve() for r in completed}
    target_sizes = set()
    for tp in target_paths:
        if tp.is_file():
            target_sizes.add(tp.stat().st_size)

    # HF blobs recorded during this run
    for r in completed:
        for cp in r.cache_paths:
            p = Path(cp)
            if p.is_file() and p.resolve() != Path(r.target).resolve():
                try:
                    p.unlink()
                    log_info(f"Removed HF cache file: {p}")
                except OSError as e:
                    log_warn(f"Could not remove {p}: {e}")

    # ModelScope temp dirs
    if modelscope_cache.is_dir():
        for temp in list(modelscope_cache.rglob("._____temp")):
            try:
                shutil.rmtree(temp)
                log_info(f"Removed ModelScope temp: {temp}")
            except OSError as e:
                log_warn(f"Could not remove {temp}: {e}")

        for root_name in ("hub", "models"):
            root = modelscope_cache / root_name
            if not root.is_dir():
                continue
            for f in root.rglob("*"):
                if not f.is_file():
                    continue
                if f.suffix in (".mdl", ".msc"):
                    continue
                resolved = f.resolve()
                if resolved in target_paths:
                    continue
                try:
                    if f.stat().st_size in target_sizes:
                        f.unlink()
                        log_info(f"Removed ModelScope cache duplicate: {f}")
                except OSError:
                    pass

    # Stale HF local-dir artifacts under store
    if store.is_dir():
        for cache_dir in store.rglob(".cache"):
            if cache_dir.is_dir():
                try:
                    shutil.rmtree(cache_dir)
                    log_info(f"Removed store artifact: {cache_dir}")
                except OSError as e:
                    log_warn(f"Could not remove {cache_dir}: {e}")

    # Prune empty dirs in caches (keep .mdl/.msc metadata)
    for cache_root in (hf_home, modelscope_cache):
        if not cache_root.is_dir():
            continue
        for dirpath in sorted(cache_root.rglob("*"), reverse=True):
            if dirpath.is_dir() and not any(dirpath.iterdir()):
                try:
                    dirpath.rmdir()
                except OSError:
                    pass


def check_dependencies(entries: list[ModelEntry]) -> bool:
    ok = True
    needs_hf = any(s.provider == "hf" for e in entries for s in e.sources)
    needs_ms = any(s.provider == "modelscope" for e in entries for s in e.sources)

    if needs_hf:
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            log_error("Missing dependency: pip install huggingface_hub")
            ok = False

    if needs_ms:
        try:
            import modelscope  # noqa: F401
        except ImportError:
            log_error("Missing dependency: pip install modelscope")
            ok = False

    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download P07 models with multi-source fallback")
    parser.add_argument("--manifest", default=os.environ.get("ZFHS_MODEL_MANIFEST", ""))
    parser.add_argument("--store", default=os.environ.get("ZFHS_MODELS_STORE") or str(default_models_store()))
    parser.add_argument("--hf-home", default=os.environ.get("HF_HOME", ""))
    parser.add_argument("--modelscope-cache", default=os.environ.get("MODELSCOPE_CACHE", ""))
    parser.add_argument("--only", default="", help="Comma-separated model ids")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-cleanup-cache", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    manifest = Path(args.manifest) if args.manifest else root / "manifest" / "models.yaml"
    store = Path(args.store).resolve()
    store_parent = store.parent
    hf_home = Path(args.hf_home).resolve() if args.hf_home else store_parent / ".cache" / "huggingface"
    modelscope_cache = (
        Path(args.modelscope_cache).resolve()
        if args.modelscope_cache
        else store_parent / ".cache" / "modelscope"
    )

    if not manifest.is_file():
        log_error(f"Manifest not found: {manifest}")
        return 1

    only_ids = {x.strip() for x in args.only.split(",") if x.strip()}
    entries = load_models(manifest, only_ids)
    if not entries:
        log_error("No model entries matched")
        return 1

    if not args.dry_run and not check_dependencies(entries):
        return 1

    log_info(f"Manifest: {manifest}")
    log_info(f"Models store: {store}")
    log_info(f"HF_HOME: {hf_home}")
    log_info(f"MODELSCOPE_CACHE: {modelscope_cache}")
    if args.dry_run:
        log_info("DRY RUN — no files will change")

    results: list[ModelResult] = []
    for entry in entries:
        result = process_model(entry, store, force=args.force, dry_run=args.dry_run)
        results.append(result)
        if result.status == "skipped":
            log_info(f"Skip ({result.model_id}): {result.target} — {result.message}")
        elif result.status == "downloaded":
            log_info(f"OK ({result.model_id}): {result.target} — {result.message}")
        elif result.status == "dry_run":
            log_info(f"Would download ({result.model_id}): {result.target} — {result.message}")
        else:
            log_error(f"Failed ({result.model_id}): {result.message}")

    downloaded = sum(1 for r in results if r.status == "downloaded")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")
    dry_run = sum(1 for r in results if r.status == "dry_run")

    print("")
    log_info(
        f"Done: downloaded={downloaded} skipped={skipped} failed={failed}"
        + (f" dry_run={dry_run}" if args.dry_run else "")
    )

    if args.json:
        print(
            json.dumps(
                {
                    "downloaded": downloaded,
                    "skipped": skipped,
                    "failed": failed,
                    "results": [r.__dict__ for r in results],
                },
                indent=2,
            )
        )

    if failed > 0:
        return 1

    if not args.dry_run and not args.no_cleanup_cache:
        log_info("Cleaning autodl-fs download caches...")
        cleanup_caches(store, hf_home, modelscope_cache, results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
