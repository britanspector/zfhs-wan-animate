# P4 Docker 镜像准备 — 验收记录

## 交付物

| 项 | 路径 |
|----|------|
| Dockerfile | `docker/Dockerfile` |
| Compose | `docker/docker-compose.yml` |
| 启动脚本 | `docker/entrypoint.sh` |
| 健康检查 | `docker/healthcheck.sh` |
| Comfy 依赖 | `docker/requirements-comfy.txt` |
| ONNX 补丁 | `docker/patches/onnx_models.py` |
| 资产移植文档 | `docs/ASSETS_MIGRATION.md` |
| Docker 指南 | `docs/DOCKER.md` |
| 资产统计脚本 | `scripts/inventory_assets.py` |
| 构建准备 | `scripts/prepare_docker_build.sh` |
| 模型卷准备 | `scripts/prepare_docker_volumes.sh` |
| 离线校验 | `scripts/validate_docker_setup.sh` |

## 离线验收（本机 2026-06-24）

- [x] `scripts/validate_docker_setup.sh` 通过（修复目录检测后）
- [x] `scripts/prepare_docker_build.sh` 复制 8 个 custom nodes 到 `docker/vendor/`
- [x] `scripts/prepare_docker_volumes.sh` 软链模型卷
- [x] `scripts/verify_assets.py` 在宿主机全绿（模型已链接）
- [x] `scripts/inventory_assets.py --write` 生成 `docs/ASSETS_MIGRATION.md`
- [x] 安装 `docker.io`、`docker-compose-v2`、`nvidia-container-toolkit`
- [ ] `docker compose build` — **AutoDL 嵌套容器**无 `unshare` 权限，构建失败：
  ```
  Error response from daemon: unshare: operation not permitted
  ```
  需在具备完整 Docker 权限的宿主机或 CI 上执行构建（见 [DOCKER.md](docs/DOCKER.md)）

## 镜像策略

- **瘦镜像**：不含 33.5GB 模型，通过 `docker/volumes/models` 挂载
- **烘焙**：ComfyUI v0.25.0、8 个 custom nodes、Python 依赖、前端 dist、ONNX GPU 补丁

## 构建命令（完整权限主机）

```bash
source /etc/network_turbo          # AutoDL 下载加速（可选）
bash scripts/prepare_docker_build.sh
bash scripts/prepare_docker_volumes.sh
cd docker && docker compose build && docker compose up -d
curl http://127.0.0.1:6020/api/health
docker compose exec wan-animate python wan-animate-api/scripts/test_api_acceptance.py
```

## GHCR 发布（构建成功后）

```bash
docker tag zfhs-wan-animate:latest ghcr.io/britanspector/zfhs-wan-animate:0.5.0
echo "$GITHUB_TOKEN" | docker login ghcr.io -u britanspector --password-stdin
docker push ghcr.io/britanspector/zfhs-wan-animate:0.5.0
```
