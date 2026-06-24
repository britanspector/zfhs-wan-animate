# zfhs-wan-animate

Wan2.2 Animate V4（面板 P07）工作流资产剥离、Python CLI 与 HTTP API。默认 ComfyUI `http://127.0.0.1:6006`，API 网关 `http://127.0.0.1:6020`。

> **开发与构建全景**：[docs/PROJECT_DEVELOPMENT.md](docs/PROJECT_DEVELOPMENT.md) — 抽离方式、分阶段交付、资产迁移、前端开发与 Docker 打包。

## 一键启动（推荐）

```bash
cd /root/zfhs-wan-animate
bash scripts/start-wan-animate.sh --with-comfy          # ComfyUI + Web (6020)
bash scripts/start-wan-animate.sh --with-comfy --dev    # 额外启动 Vite 热更新 (5173)
bash scripts/start-wan-animate.sh --stop                # 停止本脚本拉起的进程
```

## 双工作流预设

| 预设 | 文件 | 说明 |
|------|------|------|
| **v4** 标准动作迁移 | `workflows/p07_animate_v4.json` | 更贴近参考视频整体观感 |
| **v5** 保身份动作迁移 | `workflows/p07_animate_v5.json` | 保留人物形象，主要迁移动作姿态 |

前端 6020 页面可在「工作流预设」切换，并在「高级参数」折叠区内按分组微调：

| 类别 | 参数键 | 说明 |
|------|--------|------|
| 身份与姿态 | `62:pose_strength` | 姿态跟随强度（越高越像参考视频动作） |
| | `62:face_strength` | 表情/脸型跟随（越低越保留原图） |
| | `996:draw_head` | 姿态骨架是否绘制头部 |
| | `64:crop_position` | 参考图裁剪锚点（`top` / `center`） |
| 采样 | `27:steps` | 采样步数（1–8） |
| | `27:denoise_strength` | 去噪强度（0–1） |
| LoRA | `171:strength_0`…`strength_4` | 各 LoRA 开关与强度（0=关闭） |
| 提示词 | `65:positive_prompt` / `negative_prompt` | 正/负向提示词 |

## 端口对照

| 端口 | 服务 | 用途 |
|------|------|------|
| **6006** | ComfyUI 原生 Web UI | **节点画布**、Load 工作流、Queue Prompt |
| **6020** | wan-animate-api + 莫兰迪前端 | 项目封装的一键生成页（**不是** ComfyUI 画布） |
| 5173 | Vite dev | 开发前端，代理到 6020 |

- 代码 / CLI / Notebook 均通过 HTTP 直连 ComfyUI **6006**
- 画布 Load 请用 UI 格式 JSON：`/root/zealman-app/comfyui-workflows/P视频-动作迁移/P07-动作迁移-Wan2.2AnimateV4.json`
- **URL 自动加载 P07**（重启 ComfyUI 后）：`http://127.0.0.1:6006/?template=p07_wan22_animate_v4&source=zealman-workflow-templates`
- API Prompt 格式：`workflows/p07_animate_v4.json`

## Notebook 分步运行

在 Jupyter 中打开 [`notebooks/p07_pipeline.ipynb`](notebooks/p07_pipeline.ipynb)，从上到下依次执行，从配置 → 验资产 → 上传 → 提交 → 轮询 → 预览，默认 **5 秒**试跑。

```bash
# 确保 ComfyUI 已在 6006 运行
bash /root/zealman-app/start-comfyui.sh
```

详见 [notebooks/README.md](notebooks/README.md)（内核选择、素材路径、排错）。

安装 ComfyUI P07 模板 URL（可选）：

```bash
bash scripts/setup_comfy_p07_template.sh
# 重启 ComfyUI 后书签打开：
# http://127.0.0.1:6006/?template=p07_wan22_animate_v4&source=zealman-workflow-templates
```

## 快速开始（CLI）

```bash
cd /root/zfhs-wan-animate
pip install -r requirements.txt

# 资产自检
python scripts/verify_assets.py

# 使用与面板相同的示例素材
python scripts/run_p07.py \
  --image "/root/ComfyUI/input/image (17).png" \
  --video "/root/ComfyUI/input/5053929f1d2c2ef117a3a8b8c02075c7da53e5380365bc2f8a87992986058e39.mp4" \
  --width 468 --height 832 --seconds 30 \
  --comfy-url http://127.0.0.1:6006
```

## P2 API 网关

```bash
uvicorn app:app --app-dir wan-animate-api --host 0.0.0.0 --port 6020

# 后端验收（不跑完全程生成）
python wan-animate-api/scripts/test_api_acceptance.py
```

详见 [wan-animate-api/README.md](wan-animate-api/README.md)。

## P3 莫兰迪前端

```bash
# 终端 1：API
uvicorn app:app --app-dir wan-animate-api --host 0.0.0.0 --port 6020

# 终端 2：开发前端
cd wan-animate-web && npm install && npm run dev
```

生产：`cd wan-animate-web && npm run build`，API 自动托管 `dist/`（访问 http://127.0.0.1:6020/）。

详见 [wan-animate-web/README.md](wan-animate-web/README.md)。

## 音轨说明

工作流节点 **867** 通过 `audio: ["997", 2]` 将参考视频音轨 mux 进输出；若 VHS 输出无声，CLI/API 会用 ffmpeg 从参考视频复制音轨（`audio_fallback_enabled`）。

## 环境变量

| 变量 | 说明 |
|------|------|
| `COMFYUI_URL` | ComfyUI 地址 |
| `COMFYUI_ROOT` | ComfyUI 安装目录 |
| `ZFHS_WORKFLOW_PATH` | 工作流 JSON 路径 |
| `WAN_ANIMATE_API_PORT` | API 端口（默认 6020） |
| `WAN_ANIMATE_DATA_DIR` | 任务历史目录（Docker 默认 `/app/data`） |
| `COMFY_START_SCRIPT` | 外部启动脚本（Docker 留空，直接 `main.py`） |

AutoDL 裸机开发：复制 `config/local.yaml.example` → `config/local.yaml`，覆盖 `/root/ComfyUI` 路径。

## P4 Docker（瘦镜像）

模型权重（约 33.5GB）**不烘焙**，需挂载数据卷。详见：

- [docs/DOCKER.md](docs/DOCKER.md) — 构建、compose、健康检查、发布
- [docs/ASSETS_MIGRATION.md](docs/ASSETS_MIGRATION.md) — 模型/节点移植清单（`scripts/inventory_assets.py --write` 可刷新）

```bash
bash scripts/prepare_docker_build.sh   # 复制 custom nodes
bash scripts/prepare_docker_volumes.sh # 软链模型卷
bash scripts/validate_docker_setup.sh  # 离线校验（无需 docker 守护进程）
cd docker && docker compose build && docker compose up -d
```

## 目录说明

- `workflows/` — P07 API prompt
- `manifest/` — 模型、插件、节点清单
- `src/zfhs_wan_animate/` — 核心库
- `wan-animate-api/` — FastAPI 薄网关
- `wan-animate-web/` — React 莫兰迪单页前端
- `notebooks/` — P07 分步教学 Notebook
- `scripts/` — CLI 与验证脚本
- `docker/` — Dockerfile、compose、启动与健康检查脚本
- `docs/` — Docker、资产迁移与 [开发全景](docs/PROJECT_DEVELOPMENT.md)

## 节点映射

| 节点 | 字段 | 默认 |
|------|------|------|
| 57 | 角色图 | — |
| 997 | 动作视频（含音轨） | — |
| 1001/1002 | 宽/高 | 468×832 |
| 1003 | 帧数 | seconds×30 |
| 867 | 输出 | VHS_VideoCombine + 参考音轨 |
