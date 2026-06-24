# P3 验收记录

- **日期**: 2026-06-22
- **前端构建**: `npm run build` 成功（`dist/`）
- **API 验收**: `test_api_acceptance.py` 19 项全部通过
- **SPA 托管**: `GET http://127.0.0.1:6020/` → 200
- **配置**: `workflow/config` 含 `video_preview_url`

## 启动命令

```bash
uvicorn app:app --app-dir wan-animate-api --host 0.0.0.0 --port 6020
cd wan-animate-web && npm run dev   # http://127.0.0.1:5173
```

## P3 交付范围

- 莫兰迪色系双栏 UI（上传/控制/预览）
- ComfyUI 启停、GPU 检测、generate/result/interrupt/history
- WebSocket 进度代理 `/api/comfy/proxy/ws`
- CORS + 生产静态托管
