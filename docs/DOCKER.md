# Docker 部署指南

## 架构

单容器运行 ComfyUI（6006，容器内）+ wan-animate-api/前端（6020）。模型权重通过卷挂载，不烘焙进镜像。

详见 [ASSETS_MIGRATION.md](./ASSETS_MIGRATION.md)。

## 前置条件

- Docker 24+、`docker compose` v2
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- GPU 驱动支持 CUDA 12.8
- 已按资产文档准备 `docker/volumes/models/`（约 33.5GB）

## 快速开始

```bash
# 1. 准备构建 vendor（从宿主机 ComfyUI 复制 8 个 custom nodes）
bash scripts/prepare_docker_build.sh

# 2. 准备模型卷（约 33.5GB，可软链）
bash scripts/prepare_docker_volumes.sh

# 3. 构建并启动
cd docker
docker compose build
docker compose up -d

# 4. 健康检查
curl http://127.0.0.1:6020/api/health
curl http://127.0.0.1:6020/api/comfy/status
```

浏览器访问：`http://<host>:6020/`

## 构建说明

| 项 | 值 |
|----|-----|
| Dockerfile | `docker/Dockerfile` |
| 构建上下文 | `zfhs-wan-animate/` 仓库根目录 |
| 构建前准备 | `scripts/prepare_docker_build.sh`（复制 custom nodes 到 `docker/vendor/`） |
| 基础镜像 | `nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04` |
| ComfyUI 版本 | `v0.25.0`（build-arg `COMFYUI_REF`） |
| 预估瘦镜像体积 | 8–12 GB（不含模型） |

手动构建：

```bash
bash scripts/prepare_docker_build.sh
docker build -f docker/Dockerfile -t zfhs-wan-animate:latest .
```

## 发布到仓库

```bash
export REGISTRY=your.registry.example/team
export TAG=0.4.0
docker tag zfhs-wan-animate:latest ${REGISTRY}/zfhs-wan-animate:${TAG}
docker push ${REGISTRY}/zfhs-wan-animate:${TAG}
```

拉取运行：

```bash
REGISTRY=your.registry.example/team TAG=0.4.0 docker compose pull
docker compose up -d
```

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `COMFYUI_ROOT` | `/app/ComfyUI` | ComfyUI 根目录 |
| `COMFYUI_URL` | `http://127.0.0.1:6006` | API 连接 ComfyUI |
| `WAN_ANIMATE_API_PORT` | `6020` | 对外端口 |
| `WAN_ANIMATE_DATA_DIR` | `/app/data` | 任务历史目录 |
| `COMFY_PYTHON` | `/opt/venv/bin/python` | Python 解释器 |

## 卷挂载

| 宿主机 | 容器 | 说明 |
|--------|------|------|
| `docker/volumes/models` | `/app/ComfyUI/models` | 模型（只读） |
| `docker/volumes/input` | `/app/ComfyUI/input` | 上传素材 |
| `docker/volumes/output` | `/app/ComfyUI/output` | 生成结果 |
| `docker/volumes/data` | `/app/data` | `jobs.json` |

## 验收

```bash
# 容器内资产检查（模型卷就绪后应全绿）
docker compose exec wan-animate python scripts/verify_assets.py --strict-models

# API 验收（不跑完整生成）
docker compose exec wan-animate python wan-animate-api/scripts/test_api_acceptance.py
```

## 排错

| 现象 | 处理 |
|------|------|
| `ComfyUI failed to become ready` | `docker compose logs wan-animate`，查看 `/app/ComfyUI/wan_animate_entrypoint.log` |
| ONNX cuDNN 错误 | 确认镜像内 `LD_LIBRARY_PATH` 含 nvidia cudnn；重启容器 |
| 模型缺失 | 检查 `docker/volumes/models` 目录结构，对照 `ASSETS_MIGRATION.md` |
| 健康检查失败 | 等待 `start_period` 180s；确认 GPU 已分配给容器 |

## AutoDL 裸机开发

复制 `config/local.yaml.example` 为 `config/local.yaml`，覆盖 `/root/ComfyUI` 路径。Docker 默认使用 `config/default.yaml`（`/app/...`）。
