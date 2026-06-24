# GitHub 推送设置

本机已生成 SSH 密钥并创建初始 commit。将下方公钥添加到 GitHub 账户后即可推送。

## 1. 添加 SSH 公钥

打开 [GitHub SSH Keys](https://github.com/settings/keys) → **New SSH key**，粘贴：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMk0XLOSBL3UcGBQVkSSCinaovhGnGVsWCmAwQa7K1zQ zfhs-wan-animate-autodl
```

## 2. 验证与推送

```bash
source /etc/network_turbo
ssh -T git@github.com
bash scripts/push_to_github.sh
```

或使用 HTTPS + Personal Access Token：

```bash
git remote set-url origin https://github.com/britanspector/zfhs-wan-animate.git
git push -u origin main   # 用户名 + PAT 作为密码
```

## 3. 仓库信息

- 远端：`git@github.com:britanspector/zfhs-wan-animate.git`
- 分支：`main`
- 初始 commit 消息：`Initial commit: P07 Wan Animate standalone module.`

## 不提交的内容

见根目录 `.gitignore`：`config/local.yaml`、`node_modules`、`docker/vendor/custom_nodes/`、模型卷等。
