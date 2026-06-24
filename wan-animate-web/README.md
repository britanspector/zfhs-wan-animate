# wan-animate-web

P07 Wan2.2 Animate V4 莫兰迪色系单页应用。

## 开发

```bash
cd /root/zfhs-wan-animate/wan-animate-web
npm install
npm run dev
```

访问 http://127.0.0.1:5173（Vite 将 `/api` 与 `/output` 代理到 6020）。

**需先启动 API：**

```bash
cd /root/zfhs-wan-animate
uvicorn app:app --app-dir wan-animate-api --host 0.0.0.0 --port 6020
```

## 生产构建

```bash
npm run build
```

构建产物在 `dist/`。若存在，API 服务会自动托管静态文件于 `/`。

也可单独预览：

```bash
npm run preview
```

## 功能

- 双栏布局：角色图/动作视频上传、宽高与时长控制、生成/停止
- ComfyUI 启停、GPU 检测
- WebSocket 进度（经 `/api/comfy/proxy/ws`）
- 结果轮询与历史记录加载
- 莫兰迪低饱和 UI
