# AutoDL 三服务部署

在 AutoDL 实例上将 **ComfyUI 画布**、**Web 一键生成**、**Jupyter Notebook** 封装为开机自启的公网可访问服务。

## 公网入口

AutoDL 仅为 **6006** 与 **6008** 提供公网映射（[开放端口文档](https://www.autodl.com/docs/port/)）。实例内会注入：

| 环境变量 | 端口 | 服务 |
|----------|------|------|
| `AutoDLService6006URL` | 6006 | ComfyUI 画布 |
| `AutoDLService6008URL` | 6008 | nginx 网关（Web + Jupyter） |

| 功能 | 内部端口 | 公网 URL |
|------|----------|----------|
| ComfyUI 画布 | 6006 | `{AutoDLService6006URL}` |
| Web 一键生成 | 6020 → 6008 `/` | `{AutoDLService6008URL}/` |
| Jupyter Notebook | 8888 → 6008 `/jupyter/` | `{AutoDLService6008URL}/jupyter/lab?token={AutodlAutoPanelToken}`（默认打开教学代码 notebook） |

生成结果视频公网地址：`{AutoDLService6008URL}/output/zfhs-wan-animate/角色迁移_{图名}_{视频名}_*.mp4`（经 6008 网关代理到 API，勿使用 `127.0.0.1:6020`）。

P07 模板直达：

```
{AutoDLService6006URL}/?template=p07_wan22_animate_v4&source=zfhs-workflow-templates
```

## 一键部署

```bash
cd /root/zfhs-wan-animate
bash scripts/bootstrap.sh
bash scripts/start-wan-animate.sh --autodl
# 或
bash scripts/start-autodl-services.sh
```

配置开机自启（容器重启后自动拉起，无需 SSH）：

```bash
bash scripts/setup-autodl-autostart.sh
```

检查状态：

```bash
bash scripts/check-service.sh
```

## 架构

```
公网 u...:8443  ──► ComfyUI :6006
公网 uu...:8443 ──► nginx :6008
                      ├─ /          → wan-animate-api :6020
                      └─ /jupyter/  → jupyter-lab :8888
```

配置文件：[`autodl/nginx-6008.conf`](../autodl/nginx-6008.conf)

## API：服务发现

```bash
curl http://127.0.0.1:6008/api/services
curl http://127.0.0.1:6008/api/external-url-6006
curl http://127.0.0.1:6008/api/external-url-6008
```

## 后台预热

服务栈 HTTP 就绪后，`scripts/run-warmup.sh` 会在后台提交一次 10 秒短任务，加载文本编码器、姿态检测 ONNX 与 Wan 采样模型，到达关键节点后自动 `interrupt`，**不阻塞**公网入口可用。

- 日志：`.run/warmup.log`
- 状态：`wan-animate-api/data/.warmup_state.json`（与 ComfyUI PID 绑定，同进程不重复预热）
- 禁用：`SKIP_WARMUP=1`
- 手动：`bash scripts/run-warmup.sh` 或 `python scripts/warmup_comfy.py --dry-run`

## 停止服务

```bash
bash scripts/start-autodl-services.sh --stop
# 或
bash scripts/start-wan-animate.sh --stop
```

## 日志

| 文件 | 说明 |
|------|------|
| `.run/comfyui.log` | ComfyUI |
| `.run/api.log` | Web API |
| `.run/jupyter.log` | Jupyter |
| `.run/nginx-error.log` | nginx 网关 |
| `.run/warmup.log` | 后台模型预热（实例启动后自动） |
| `/tmp/zfhs-wan-animate-autostart.log` | 开机自启 |
| `/tmp/zfhs-wan-animate-daemon.log` | 守护进程 |

## iframe 嵌入

Web 一键生成页可通过 iframe 嵌入业务系统，但跨源 / 混合内容环境容易导致浏览器节流 `setTimeout`、WebSocket 握手挂起。

| 要求 | 说明 |
|------|------|
| 父页 HTTPS | 父页使用 **HTTPS**；避免 `http://` 父页嵌入 `https://` 公网 6008 子页 |
| 尽量同站 | 父页与 `{AutoDLService6008URL}` 同站或同级域名更稳；跨站亦可，但依赖进度降级逻辑 |
| sandbox | 勿使用会禁用脚本或限制网络的 `sandbox`；需要 WS 时不要 `allow-same-origin` 缺失导致隔离异常 |
| allow | 可保留 `fullscreen` / clipboard 等按需权限，勿过度收紧到阻断页面功能 |

前端已支持：WS 打开失败时仍提交任务；多次重连；断线后轮询 `GET /api/workflow/progress` 补进度。直连公网地址或同站 HTTPS 父页仍然最稳。本地可用仓库根目录 `iframe-test.html` + `python3 -m http.server 8765` 做对照测试。

## 排错

| 现象 | 处理 |
|------|------|
| 6008 无法访问 | `bash scripts/check-service.sh`；确认 6008 未被其他进程占用 |
| Jupyter 403 / 无法打开 | 公网 URL 必须带 `?token=`，见 `curl http://127.0.0.1:6008/api/services` |
| Jupyter 404 | 确认 `jupyter` 在 8888 且 `base_url=/jupyter/`；设 `JUPYTER_FORCE_RESTART=1` 重启 |
| ComfyUI 启动慢 | 首次加载模型需 1–2 分钟，守护进程会自动重试 |
| 首跑生成偏慢 | 实例启动后会在后台自动预热（约 3–4 分钟），日志见 `.run/warmup.log`；设 `SKIP_WARMUP=1` 可禁用 |
| nginx 未安装 | `start-nginx-gateway.sh` 会尝试 `apt-get install nginx` |
| 公网 URL 为空 | 在 AutoDL 控制台「自定义服务」复制地址；或 `source /etc/profile.d/autodl.env.sh` |
| iframe 内进度卡在 0:00 | 确认父页 HTTPS；查看 Network 是否有 `POST /api/workflow/generate`；无请求则清缓存后硬刷新前端构建产物 |

## 验证清单

- [ ] `https://u...:8443/` 打开 ComfyUI
- [ ] `https://uu...:8443/` 打开莫兰迪 Web 页
- [ ] `https://uu...:8443/jupyter/lab?token=...` 打开 Jupyter Lab 并默认进入教学代码 notebook
- [ ] 实例重启后（不 SSH）三入口仍可访问
