#!/bin/bash
# Configure AutoDL container autostart for zfhs-wan-animate.
set -e

export PATH="/root/miniconda3/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
ROOT="/root/zfhs-wan-animate"
AUTOSTART="${ROOT}/scripts/improved-autostart.sh"
DAEMON="${ROOT}/scripts/daemon.sh"

echo "=========================================="
echo "zfhs-wan-animate AutoDL 开机自启配置"
echo "=========================================="

setup_rc_local() {
    if [ ! -f /etc/rc.local ]; then
        cat > /etc/rc.local << 'EOF'
#!/bin/bash
sleep 5
if [ -f /root/zfhs-wan-animate/scripts/improved-autostart.sh ]; then
    nohup bash /root/zfhs-wan-animate/scripts/improved-autostart.sh > /tmp/zfhs-rc-local.log 2>&1 &
fi
if [ -f /root/zfhs-wan-animate/scripts/daemon.sh ]; then
    nohup bash /root/zfhs-wan-animate/scripts/daemon.sh > /dev/null 2>&1 &
fi
exit 0
EOF
        chmod +x /etc/rc.local
    else
        if ! grep -q "zfhs-wan-animate" /etc/rc.local 2>/dev/null; then
            sed -i '/^exit 0/i \
if [ -f /root/zfhs-wan-animate/scripts/improved-autostart.sh ]; then\
    nohup bash /root/zfhs-wan-animate/scripts/improved-autostart.sh > /tmp/zfhs-rc-local.log 2>&1 &\
fi\
if [ -f /root/zfhs-wan-animate/scripts/daemon.sh ]; then\
    nohup bash /root/zfhs-wan-animate/scripts/daemon.sh > /dev/null 2>&1 &\
fi\
' /etc/rc.local
        fi
    fi
    echo "OK /etc/rc.local"
}

setup_profile_d() {
    cat > /etc/profile.d/zfhs-wan-animate-autostart.sh << 'EOF'
#!/bin/bash
if [ -f /root/zfhs-wan-animate/scripts/improved-autostart.sh ]; then
    nohup bash /root/zfhs-wan-animate/scripts/improved-autostart.sh > /tmp/zfhs-profile-d.log 2>&1 &
fi
EOF
    chmod +x /etc/profile.d/zfhs-wan-animate-autostart.sh
    echo "OK /etc/profile.d/zfhs-wan-animate-autostart.sh"
}

setup_bashrc() {
    if ! grep -q "zfhs-wan-animate.*improved-autostart" /root/.bashrc 2>/dev/null; then
        cat >> /root/.bashrc << 'EOF'

# zfhs-wan-animate AutoDL autostart
if [ -f "/root/zfhs-wan-animate/scripts/improved-autostart.sh" ]; then
    nohup bash /root/zfhs-wan-animate/scripts/improved-autostart.sh > /tmp/zfhs-bashrc.log 2>&1 &
fi
EOF
    fi
    echo "OK .bashrc"
}

chmod +x "$AUTOSTART" "$DAEMON" "${ROOT}/scripts/check-service.sh" "${ROOT}/scripts/start-autodl-services.sh"

setup_rc_local
setup_profile_d
setup_bashrc

if ! pgrep -f "zfhs-wan-animate/scripts/daemon.sh" >/dev/null 2>&1; then
    nohup bash "$DAEMON" > /dev/null 2>&1 &
    echo "OK 守护进程已启动"
fi

echo ""
echo "测试启动..."
bash "$AUTOSTART"
echo ""
echo "运行检查: ${ROOT}/scripts/check-service.sh"
echo "完成。容器重启后服务将通过 rc.local 自动拉起。"
