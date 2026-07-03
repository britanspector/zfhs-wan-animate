# zfhs-model-downloader

在 Linux 上独立下载 P07 Wan2.2 Animate 所需的 **11 个模型文件**（约 33.5GB），无需安装 ComfyUI。

**默认下载目录**：`/autodl-fs/data/zfhs-wan-animate/models`（AutoDL 上 `/autodl-fs` 挂载点下可写区；若仅有 `/autodl-fs` 可写则使用 `/autodl-fs/zfhs-wan-animate/models`）。

下载完成后可直接在 AutoDL 实例上运行 `setup_models.sh` 建立软链，无需再拷贝。

## 环境要求

- Linux，bash，Python 3.8+
- 磁盘可用空间 **≥ 40GB**
- 可访问 HuggingFace 和/或 ModelScope（国内建议配置代理或镜像）
- 可选：`HF_TOKEN` 环境变量（访问 gated 的 zealman/nahz202 仓库）

## 快速开始

```bash
tar -xzf zfhs-model-downloader.tar.gz
cd zfhs-model-downloader
pip install -r requirements.txt

# 默认下载到 /autodl-fs/data/zfhs-wan-animate/models（AutoDL）
./run-download.sh

# 或指定其他存储路径
export ZFHS_MODELS_STORE=/data/zfhs-models
bash scripts/download_models.sh --download-only --skip-network-turbo
python3 scripts/verify_models.py
```

## 常用命令

```bash
# 检查计划（不下载）
bash scripts/download_models.sh --dry-run --download-only

# 只下载某一个模型
bash scripts/download_models.sh --download-only --only vitpose,yolov10m

# 强制重新下载
bash scripts/download_models.sh --download-only --force --only lora_fun
```

## 目录结构（下载后）

```
/autodl-fs/data/zfhs-wan-animate/
├── models/
│   ├── diffusion_models/Wan/
│   ├── vae/
│   ├── text_encoders/
│   ├── clip_vision/
│   ├── loras/Wan/
│   └── detection/
└── .cache/          # 下载缓存（成功后自动清理）
```

## 拷到其他机器

若在其他 Linux 下载后需拷到 AutoDL：

```bash
# 在下载机上
rsync -avP /autodl-fs/data/zfhs-wan-animate/models/ user@autodl-host:/autodl-fs/data/zfhs-wan-animate/models/

# 在 AutoDL 实例上（进入完整 zfhs-wan-animate 项目）
bash scripts/setup_models.sh
python3 scripts/verify_assets.py --strict-models
```

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `ZFHS_MODELS_STORE` | `/autodl-fs/data/zfhs-wan-animate/models` | 模型实体存储目录（AutoDL） |
| `HF_HOME` | `{store父目录}/.cache/huggingface` | HuggingFace 缓存 |
| `MODELSCOPE_CACHE` | `{store父目录}/.cache/modelscope` | ModelScope 缓存 |
| `HF_TOKEN` | — | 可选，访问 gated HF 仓库 |

## 下载源说明

模型清单见 `manifest/models.yaml`。每个模型按序尝试 HuggingFace 主源，失败后自动回退 ModelScope 或公开 HF 备用源。下载成功后会自动清理 autodl-fs 下的缓存以节省空间。
