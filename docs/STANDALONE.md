# 独立部署指南（脱离 zealman-app）

本文档说明如何在 **AutoDL 同类实例**上独立运行 `zfhs-wan-animate`，无需安装或启动 `zealman-app`。

## 前提条件

| 项 | 要求 |
|----|------|
| 平台 | AutoDL（或具备 `/.autodl-model`、`/.autodl` 平台模型缓存的环境） |
| ComfyUI | 已安装在 `/root/ComfyUI`（或设置 `COMFYUI_ROOT`） |
| Python | `/root/miniconda3` 或设置 `COMFY_PYTHON` |
| 模型缓存 | 平台缓存中已存在 P07 所需 hash（与当前镜像同族） |
| GPU | NVIDIA + CUDA 12.x |

模型实体文件**不在 Git 仓库内**。项目通过 [`manifest/model_sources.autodl.yaml`](../manifest/model_sources.autodl.yaml) 将 AutoDL 缓存软链到 `{COMFYUI_ROOT}/models/`。

## 新服务器首次部署

```bash
git clone <your-repo-url> /root/zfhs-wan-animate
cd /root/zfhs-wan-animate
pip install -r requirements.txt

bash scripts/bootstrap.sh
bash scripts/start-wan-animate.sh --with-comfy
```

`bootstrap.sh` 会依次：

1. 创建 `config/local.yaml`（若不存在）
2. `scripts/setup_models.sh --strict` — 从平台缓存建立 11 个模型软链
3. `scripts/install_custom_nodes.sh --install-missing` — 从 `docker/vendor` 补装缺失节点
4. `scripts/verify_assets.py --strict-models` — 验收
5. 构建前端 `wan-animate-web/dist`

## 日常启动

```bash
cd /root/zfhs-wan-animate
bash scripts/start-wan-animate.sh --with-comfy
```

- Web 一键生成：http://127.0.0.1:6020/
- ComfyUI 画布：http://127.0.0.1:6006/

仅启动 ComfyUI（含模型链接）：

```bash
bash scripts/start-comfyui.sh
```

## 代码更新后（git pull）

```bash
cd /root/zfhs-wan-animate
git pull
bash scripts/setup_models.sh          # 刷新模型软链
bash scripts/start-wan-animate.sh --stop
bash scripts/start-wan-animate.sh --with-comfy
```

若前端有变更：

```bash
cd wan-animate-web && npm ci && npm run build && cd ..
```

## 模型挂载机制

与 zealman-app 相同，使用 **符号链接** 而非复制文件：

```
/.autodl-model/data/<hash>  ──ln -s──>  /root/ComfyUI/models/<category>/<file>
```

区别：本项目只维护 P07 所需的 **11 个文件**，映射表在仓库内 [`manifest/model_sources.autodl.yaml`](../manifest/model_sources.autodl.yaml)，**不读取** `zealman-app/modellink/user_models.json`，**不调用** `update-symlinks.sh`。

手动执行：

```bash
bash scripts/setup_models.sh          # 缺源时 WARN，继续
bash scripts/setup_models.sh --strict # 缺源时 exit 1（bootstrap 使用）
```

## ComfyUI 启动

项目自有 [`scripts/start-comfyui.sh`](../scripts/start-comfyui.sh)：

1. 运行 `setup_models.sh`（可用 `SKIP_MODEL_SETUP=1` 跳过）
2. 检查 custom nodes（`install_custom_nodes.sh --check-only`）
3. 解析 `LD_LIBRARY_PATH`
4. 启动 `main.py --port 6006`

不依赖 `zealman-app/start-comfyui.sh` 或 `/.autodl/users/...` 外部只读脚本。

## Custom nodes

P07 依赖 8 个 custom nodes，清单见 [`manifest/custom_nodes.yaml`](../manifest/custom_nodes.yaml)。

- 同类 AutoDL ComfyUI 镜像通常已预装
- 若缺失：`bash scripts/install_custom_nodes.sh --install-missing`（需先在本机执行 `prepare_docker_build.sh` 填充 `docker/vendor/custom_nodes/`）

## 画布 UI 工作流

UI 格式 JSON 已内置：[`assets/workflows/ui/p07_animate_v4_ui.json`](../assets/workflows/ui/p07_animate_v4_ui.json)

可选安装 ComfyUI 模板 URL：

```bash
bash scripts/setup_comfy_p07_template.sh
# 重启 ComfyUI 后：
# http://127.0.0.1:6006/?template=p07_wan22_animate_v4&source=zealman-workflow-templates
```

## 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `COMFYUI_ROOT` | ComfyUI 安装目录 | `/root/ComfyUI` |
| `COMFYUI_URL` | ComfyUI HTTP 地址 | `http://127.0.0.1:6006` |
| `COMFY_PYTHON` | Python 解释器 | `/root/miniconda3/bin/python` |
| `COMFY_START_SCRIPT` | API 启动 ComfyUI 的脚本 | 空（或 `scripts/start-comfyui.sh`） |
| `ZFHS_MODEL_SOURCES` | 模型映射表路径 | `manifest/model_sources.autodl.yaml` |
| `SKIP_MODEL_SETUP` | `1` 时跳过模型软链 | 未设置 |
| `WAN_ANIMATE_API_PORT` | API 端口 | `6020` |

## 故障排查

| 现象 | 处理 |
|------|------|
| `Source missing` / 模型 missing | 确认在同族 AutoDL 镜像；或更新 `manifest/model_sources.autodl.yaml` 中的 hash |
| custom_node missing | `bash scripts/install_custom_nodes.sh --install-missing` |
| 6006 端口占用 | `start-comfyui.sh` 会自动清理；或 `bash scripts/start-wan-animate.sh --stop` |
| ComfyUI 启动失败 | 查看 `.run/comfyui.log` |
| 前端 404 | `cd wan-animate-web && npm run build` |

## 与 zealman-app 的关系

- **历史**：本项目从 zealman 面板 P07 工作流抽离
- **运行时**：无依赖；不需要 clone、启动或读取 zealman-app
- **模型**：共用 AutoDL 平台缓存，但链接逻辑由本项目 `setup_models.sh` 独立完成

## 相关文档

- [README.md](../README.md) — 快速开始
- [DOCKER.md](./DOCKER.md) — Docker 部署
- [ASSETS_MIGRATION.md](./ASSETS_MIGRATION.md) — 模型清单
