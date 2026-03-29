#!/bin/bash
# 停止飞书 Claude Agent

echo "🛑 停止飞书 Claude Agent..."

pkill -f "python3.*feishu_websocket.py"

sleep 2

if ps aux | grep -v grep | grep "python3.*feishu_websocket.py" > /dev/null; then
    echo "❌ 停止失败，进程仍在运行"
    ps aux | grep -v grep | grep "python3.*feishu_websocket.py"
else
    echo "✅ 服务已停止"
fi
