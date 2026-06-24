# P07 Notebook 使用说明

## 文件

| 文件 | 说明 |
|------|------|
| [`p07_pipeline.ipynb`](p07_pipeline.ipynb) | 分步教学 Notebook，从代码层跑通 P07 生成 |

## 前置条件

1. ComfyUI 已在 **6006** 端口运行：

```bash
bash scripts/start-comfyui.sh
# 或
bash scripts/start-wan-animate.sh --with-comfy
curl -s http://127.0.0.1:6006/system_stats
```

2. 已安装项目依赖：

```bash
cd /root/zfhs-wan-animate
pip install -r requirements.txt
```

3. 资产就绪（模型、custom nodes）：

```bash
python scripts/verify_assets.py
```

4. Jupyter 内核：选择 **Python 3**（与 ComfyUI 同一 conda 环境 `/root/miniconda3` 为佳）。

## 端口对照

| 端口 | 服务 | 何时使用 |
|------|------|----------|
| **6006** | ComfyUI 原生 UI | 打开节点画布、Load 工作流、手动 Queue |
| **6020** | wan-animate-api + Web | 莫兰迪一键生成页 |
| Notebook | HTTP → 6006 | 本 Notebook 与 CLI 相同 |

AutoDL 访问 ComfyUI 画布：在控制台映射 **6006**，或 SSH 隧道：

```bash
ssh -L 6006:127.0.0.1:6006 user@<autodl-host>
```

浏览器打开：`http://127.0.0.1:6006`

## 在 ComfyUI 画布中 Load 工作流

本仓库 `workflows/p07_animate_v4.json` 是 **API Prompt 格式**（供 `/prompt` 接口），**不能**直接在画布中拖拽使用。

图形界面请 Load **UI 格式** JSON：

```
assets/workflows/ui/p07_animate_v4_ui.json
```

加载后设置：

- 节点 **57**：角色参考图
- 节点 **997**：动作视频
- 节点 **1001 / 1002 / 1003**：宽 / 高 / 帧数

然后点击 **Queue Prompt**。

## URL 自动加载 P07（推荐书签）

运行一次安装脚本（或 `bash scripts/setup_comfy_p07_template.sh`），重启 ComfyUI 后打开：

```text
http://127.0.0.1:6006/?template=p07_wan22_animate_v4&source=zealman-workflow-templates
```

画布会自动加载 P07 节点图（无需手动 Load）。

## 示例素材

默认使用 `config/local.yaml` 或 `config/default.yaml` 中的 `samples` 路径。

在 Notebook 第 1 格可设置 **`USER_IMAGE` / `USER_VIDEO`**（填路径则覆盖配置；留 `None` 则用 `local.yaml` 的 samples）：

```python
USER_IMAGE: str | None = "/root/ComfyUI/input/wonyoung.jpg"
USER_VIDEO: str | None = "/root/ComfyUI/input/AI小红狗.mp4"
```

也可直接改 `config/local.yaml` 的 `samples` 段。

## 工作流 v4 / v5 与调参

第 2 格（Step 1b）可设置：

- `WORKFLOW_VARIANT = "v4"` 或 `"v5"`
- `TUNABLES` 字典覆盖节点参数（格式 `节点ID:字段名`）

留空 `TUNABLES` 时使用对应 JSON 文件内默认值。

### 可调参数一览

| 类别 | 键 | 说明 |
|------|-----|------|
| 身份与姿态 | `62:pose_strength` | 姿态跟随强度 |
| | `62:face_strength` | 表情/脸型跟随（越低越保留原图） |
| | `996:draw_head` | 姿态骨架是否绘制头部 |
| | `64:crop_position` | 参考图裁剪（`top` / `center`） |
| 采样 | `27:steps` | 采样步数（1–8，Lightning LoRA 建议 4） |
| | `27:denoise_strength` | 去噪强度（0–1） |
| LoRA | `171:strength_0` | 重光照 LoRA（0=关） |
| | `171:strength_1` | Lightning 4步 LoRA |
| | `171:strength_2` | FastWan T2V LoRA |
| | `171:strength_3` | PusaV1 LoRA |
| | `171:strength_4` | Fun InP LoRA |
| 提示词 | `65:positive_prompt` | 正向提示词 |
| | `65:negative_prompt` | 负向提示词 |

示例：

```python
TUNABLES = {
    "27:steps": 4,
    "27:denoise_strength": 1.0,
    "171:strength_2": 0,  # 关闭 FastWan
    "65:positive_prompt": "保持参考图人物身份与画质...",
}
```

## 运行顺序

在 Jupyter 中打开 `p07_pipeline.ipynb`，**从上到下依次执行**每个 Code cell。

默认 **5 秒**试跑（约 2–3 分钟）；改为 30 秒时 WanVideo Sampler（节点 27）可能需要 10+ 分钟。

## 排错

| 现象 | 处理 |
|------|------|
| `ComfyUI unreachable` | 确认 6006 已启动 |
| 模型 missing | 运行 `bash scripts/setup_models.sh` 或对照 `docs/ASSETS_MIGRATION.md` |
| 轮询超时 | 增大 `SECONDS` 对应超时已自动计算；检查 `nvidia-smi` |
| ONNX 姿态检测失败 | 重启 ComfyUI，确保 `LD_LIBRARY_PATH` 含 cudnn |
