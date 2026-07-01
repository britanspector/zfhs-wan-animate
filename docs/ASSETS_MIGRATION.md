# P07 资产清单

> 由 `scripts/inventory_assets.py` 自动生成。修改分类逻辑请编辑该脚本后执行
> `python3 scripts/inventory_assets.py --write` 重新生成。

扫描 ComfyUI 根目录：`/root/ComfyUI`

## 概述

P07 共依赖 **11 个模型文件**（约 33.5GB）、**8 个 custom node 包**、**30 个工作流节点类型**（v4/v5 共用）。

在 AutoDL 上，模型**实体**存放在平台公共缓存（`/.autodl-model/data/...` 或 `/.autodl/...`），
`{COMFYUI_ROOT}/models/` 下仅为软链，**不占实例系统盘**。Custom nodes、项目代码、输入输出在**系统盘**。

`/.autodl` 通常软链到 `../../.autodl-model/data`，二者同根。

## 存储位置总览

| 资产类型 | 实体位置 | ComfyUI 可见路径 | 说明 |
|----------|----------|------------------|------|
| 模型权重（11） | AutoDL 公共缓存 | `models/` 软链 | `scripts/setup_models.sh` |
| Custom nodes（8） | 实例系统盘 | `custom_nodes/` | 镜像预装或 `install_custom_nodes.sh` |
| 工作流 JSON | 项目 Git（系统盘） | — | `workflows/p07_animate_v*.json` |
| 上传/输出 | 实例系统盘 | `input/`、`output/` | 运行时数据 |
| API 任务历史 | 实例系统盘 | `wan-animate-api/data/` | `jobs.json` |

## 模型文件

合计（已解析文件大小）：**33.46 GB**

实体均在 **AutoDL 公共缓存**；下表「公共缓存源」来自 `manifest/model_sources.autodl.yaml`。

| ID | 相对路径 | 大小 | 公共缓存源 | HF 备用下载 | 链接状态 |
|----|----------|------|------------|-------------|----------|
| `main_diffusion` | `models/diffusion_models/Wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors` | 16.13 GB | `…data/e2/aa/e0/e2aae0903f2ff169572eda014f55ef73` | `nahz202/Wan_2.2_Repackaged/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors` | 软链→公共缓存 |
| `vae` | `models/vae/wan_2.1_vae.safetensors` | 242.06 MB | `…data/0d/d0/84/0dd084bcf4728fe874a9e3b18110af74` | `zealman/Wan_2.2/wan_2.1_vae.safetensors` | 软链→公共缓存 |
| `text_encoder` | `models/text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors` | 6.27 GB | `…data/26/dd/20/26dd20d732632a3d32a0bbefca75ab57` | `zealman/Wan_2.2/umt5-xxl-enc-fp8_e4m3fn.safetensors` | 软链→公共缓存 |
| `clip_vision` | `models/clip_vision/clip_vision_h.safetensors` | 1.18 GB | `…data/96/43/19/964319b47fb4966f8276a2d6fadad334` | `zealman/Wan_2.2/clip_vision_h.safetensors` | 软链→公共缓存 |
| `lora_relight` | `models/loras/Wan/WanAnimate_relight_lora_fp16.safetensors` | 1.34 GB | `…data/03/30/74/0330745fc9fe8bd0ecba6a444b4f561d` | `zealman/Wan22-Animate/WanAnimate_relight_lora_fp16.safetensors` | 软链→公共缓存 |
| `lora_lightning` | `models/loras/Wan/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors` | 585.14 MB | `…data/23/31/a8/2331a89a1dbccadafc8492738502d076` | `zealman/Wan22-Animate/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors` | 软链→公共缓存 |
| `lora_fastwan` | `models/loras/Wan/FastWan_T2V_14B_480p_lora_rank_128_bf16.safetensors` | 1.17 GB | `…data/66/4d/38/664d38a1f04732ba2eee22bf7cca76c0` | `zealman/Wan22-Animate/FastWan_T2V_14B_480p_lora_rank_128_bf16.safetensors` | 软链→公共缓存 |
| `lora_pusa` | `models/loras/Wan/Wan21-PusaV1-LoRA-14B-rank512-bf16.safetensors` | 4.57 GB | `…todl/a9/a4/d2/a9a4d26c423330c14310f15877fbafe4` | `zealman/Wan22-Animate/Wan21-PusaV1-LoRA-14B-rank512-bf16.safetensors` | 软链→公共缓存 |
| `lora_fun` | `models/loras/Wan/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors` | 818.69 MB | `…data/43/d9/0b/43d90b355008606144003907ea00121c` | `zealman/Wan22-Animate/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors` | 软链→公共缓存 |
| `vitpose` | `models/detection/vitpose-l-wholebody.onnx` | 1.15 GB | `…data/29/90/c4/2990c41fc85966b4bb820b961f174c49` | `JunkyByte/easy_ViTPose/onnx/wholebody/vitpose-l-wholebody.onnx` | 软链→公共缓存 |
| `yolov10m` | `models/detection/yolov10m.onnx` | 58.80 MB | `…data/69/6c/94/696c94dc87fc83a1b681483e7df42c59` | `Wan-AI/Wan2.2-Animate-14B/process_checkpoint/det/yolov10m.onnx` | 软链→公共缓存 |

### 目标目录结构

```
models/
├── diffusion_models/Wan/
├── vae/
├── text_encoders/
├── clip_vision/
├── loras/Wan/
└── detection/
```

### 部署命令

| 场景 | 命令 |
|------|------|
| AutoDL 同族镜像（公共缓存已有） | `bash scripts/setup_models.sh` |
| 缓存缺 hash / 非 AutoDL 环境 | `bash scripts/download_models.sh` |
| 已有软链，需下载实体到系统盘 | `bash scripts/download_models.sh --force` |
| 验收 | `python3 scripts/verify_assets.py --strict-models` |

## Custom Nodes（系统盘）

合计：**65.24 MB**

路径：`{COMFYUI_ROOT}/custom_nodes/`。缺失时从 `docker/vendor/custom_nodes/` 复制。

| 目录 | 大小 | 提供节点 | 状态 |
|------|------|----------|------|
| `ComfyUI-WanVideoWrapper` | 46.78 MB | WanVideoModelLoader, WanVideoSampler, WanVideoDecode, WanVideoVAELoader, WanVideoTextEncode, WanVideoClipVisionEncode, WanVideoAnimateEmbeds, WanVideoBlockSwap, WanVideoLoraSelectMulti, WanVideoContextOptions | OK |
| `ComfyUI-WanAnimatePreprocess` | 1.03 MB | PoseAndFaceDetection, OnnxDetectionModelLoader, DrawViTPose | OK |
| `ComfyUI-KJNodes` | 3.63 MB | ImageResizeKJv2, INTConstant | OK |
| `ComfyUI-VideoHelperSuite` | 602.59 KB | VHS_LoadVideo, VHS_VideoCombine, VHS_VideoInfo | OK |
| `ComfyUI-Easy-Use` | 12.52 MB | easy mathInt | OK |
| `reservedvram` | 29.96 KB | ReservedVRAMSetter | OK |
| `comfyui_memory_cleanup` | 230.57 KB | VRAMCleanup | OK |
| `ComfyUI_essentials` | 440.54 KB | BatchCount+ | OK |

## 工作流节点（v4/v5 共用，共 30 个 class_type）

自 `workflows/p07_animate_v4.json` / `p07_animate_v5.json` 提取，按 custom node 包分组。

- **ComfyUI 内置**：`CLIPVisionLoader`, `ImageBatch`, `ImageFromBatch`, `LoadImage`, `PrimitiveFloat`, `RepeatImageBatch`
- **ComfyUI-Easy-Use**：`easy mathInt`
- **ComfyUI-KJNodes**：`INTConstant`, `ImageResizeKJv2`
- **ComfyUI-VideoHelperSuite**：`VHS_LoadVideo`, `VHS_VideoCombine`, `VHS_VideoInfo`
- **ComfyUI-WanAnimatePreprocess**：`DrawViTPose`, `OnnxDetectionModelLoader`, `PoseAndFaceDetection`
- **ComfyUI-WanVideoWrapper**：`WanVideoAnimateEmbeds`, `WanVideoBlockSwap`, `WanVideoClipVisionEncode`, `WanVideoContextOptions`, `WanVideoDecode`, `WanVideoLoraSelectMulti`, `WanVideoModelLoader`, `WanVideoSampler`, `WanVideoSetBlockSwap`, `WanVideoSetLoRAs`, `WanVideoTextEncodeCached`, `WanVideoVAELoader`
- **ComfyUI_essentials**：`BatchCount+`
- **comfyui_memory_cleanup**：`VRAMCleanup`
- **reservedvram**：`ReservedVRAMSetter`

## 项目内资产（系统盘 / Git）

| 路径 | 说明 |
|------|------|
| `/root/zfhs-wan-animate` | 项目源码、manifest、API/Web |
| `workflows/p07_animate_v4.json` | 标准动作迁移工作流 |
| `workflows/p07_animate_v5.json` | 保身份动作迁移工作流 |
| `manifest/models.yaml` | 模型清单与 HF 下载路径 |
| `manifest/model_sources.autodl.yaml` | AutoDL 公共缓存 hash 映射 |

## 运行时数据（系统盘）

| 路径 | 用途 |
|------|------|
| `/root/ComfyUI/input` | 上传图/视频 |
| `/root/ComfyUI/output` | 生成结果 |
| `/root/zfhs-wan-animate/wan-animate-api/data/jobs.json` | API 任务历史 |

Docker 容器内对应：`/app/ComfyUI/models`（只读挂载）、`/app/ComfyUI/input`、`/app/ComfyUI/output`、`/app/data`。

## 示例素材（可选）

- `input/image (17).png`
- `input/5053929f1d2c2ef117a3a8b8c02075c7da53e5380365bc2f8a87992986058e39.mp4`（需含音轨）
