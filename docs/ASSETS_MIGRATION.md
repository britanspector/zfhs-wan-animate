# P07 资产移植清单

> 由 `scripts/inventory_assets.py` 自动生成，请勿手工编辑。

扫描根目录：`/root/ComfyUI`

## 模型文件（需外部挂载，不烘焙进瘦镜像）

合计（已存在文件）：**33.46 GB**

| 路径 | 大小 | 下载源 | 状态 |
|------|------|--------|------|
| `models/diffusion_models/Wan/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors` | 16.13 GB | HF `nahz202/Wan_2.2_Repackaged/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors` | OK |
| `models/vae/wan_2.1_vae.safetensors` | 242.06 MB | HF `zealman/Wan_2.2/wan_2.1_vae.safetensors` | OK |
| `models/text_encoders/umt5-xxl-enc-fp8_e4m3fn.safetensors` | 6.27 GB | HF `zealman/Wan_2.2/umt5-xxl-enc-fp8_e4m3fn.safetensors` | OK |
| `models/clip_vision/clip_vision_h.safetensors` | 1.18 GB | HF `zealman/Wan_2.2/clip_vision_h.safetensors` | OK |
| `models/loras/Wan/WanAnimate_relight_lora_fp16.safetensors` | 1.34 GB | HF `zealman/Wan22-Animate/WanAnimate_relight_lora_fp16.safetensors` | OK |
| `models/loras/Wan/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors` | 585.14 MB | HF `zealman/Wan22-Animate/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors` | OK |
| `models/loras/Wan/FastWan_T2V_14B_480p_lora_rank_128_bf16.safetensors` | 1.17 GB | HF `zealman/Wan22-Animate/FastWan_T2V_14B_480p_lora_rank_128_bf16.safetensors` | OK |
| `models/loras/Wan/Wan21-PusaV1-LoRA-14B-rank512-bf16.safetensors` | 4.57 GB | HF `zealman/Wan22-Animate/Wan21-PusaV1-LoRA-14B-rank512-bf16.safetensors` | OK |
| `models/loras/Wan/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors` | 818.69 MB | HF `zealman/Wan22-Animate/Wan2.2-Fun-A14B-InP-low-noise-HPS2.1.safetensors` | OK |
| `models/detection/vitpose-l-wholebody.onnx` | 1.15 GB | 从现有环境复制 | OK |
| `models/detection/yolov10m.onnx` | 58.80 MB | 从现有环境复制 | OK |

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

## Custom Nodes（烘焙进 Docker 镜像）

合计：**65.24 MB**

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

## 运行时数据卷

| 容器路径 | 用途 |
|----------|------|
| `/app/ComfyUI/models` | 模型权重（只读挂载） |
| `/app/ComfyUI/input` | 上传图/视频 |
| `/app/ComfyUI/output` | 生成结果 |
| `/app/data` | API 任务历史 `jobs.json` |

## 示例素材（可选）

- `input/image (17).png`
- `input/5053929f1d2c2ef117a3a8b8c02075c7da53e5380365bc2f8a87992986058e39.mp4`（需含音轨）
