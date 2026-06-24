# wan-animate-api

P07 Wan2.2 Animate 薄网关，对齐 zealman 面板 API 契约，默认端口 **6020**。

## 启动

```bash
cd /root/zfhs-wan-animate
pip install -r requirements.txt
uvicorn app:app --app-dir wan-animate-api --host 0.0.0.0 --port 6020
```

## 主要端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/gpu/info` | GPU 信息 |
| GET | `/api/comfy/status` | ComfyUI 状态 |
| POST | `/api/comfy/start` | 启动 ComfyUI |
| POST | `/api/comfy/stop` | 停止 ComfyUI |
| POST | `/api/comfy/upload/file` | 上传角色图/参考视频 |
| GET | `/api/comfy/view` | 预览 input/output |
| POST | `/api/comfy/proxy/interrupt` | 中断当前生成 |
| GET | `/api/comfy/proxy/history` | 代理 ComfyUI history |
| GET | `/api/workflow/list` | 工作流列表 |
| GET | `/api/workflow/config/{id}` | 初始化参数 |
| POST | `/api/workflow/generate` | 提交生成 |
| GET | `/api/workflow/result?prompt_id=` | 轮询结果 |
| GET | `/api/workflow/history` | 本地任务历史 |
| GET | `/output/{subfolder}/{filename}` | 输出视频直链 |

## 示例：提交生成

```bash
curl -X POST http://127.0.0.1:6020/api/workflow/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow_id": "P07-动作迁移-Wan2.2AnimateV4",
    "input_values": {
      "57:image": "image (17).png",
      "997:video": "5053929f....mp4",
      "1001:value": 468,
      "1002:value": 832,
      "1003:value": 300
    }
  }'
```

## 验收

```bash
# 先启动 API，再运行
python wan-animate-api/scripts/test_api_acceptance.py
```

验收不等待完整生成，仅验证入队、参数 patch、history、interrupt。
