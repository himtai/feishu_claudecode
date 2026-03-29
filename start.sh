#!/bin/bash
# 飞书 Claude Agent 启动脚本

cd "$(dirname "$0")"

echo "🚀 启动飞书 Claude Agent..."

# 检查环境
if [ ! -f ".env" ]; then
    echo "❌ 错误：.env 文件不存在"
    echo "请复制 .env.example 并配置飞书凭证"
    exit 1
fi

# 停止旧进程
pkill -f "python3.*feishu_websocket.py" 2>/dev/null
sleep 1

# 清理旧日志（如果存在权限问题）
rm -f feishu_latest.log 2>/dev/null

# 启动服务（排除飞书域名走代理，使用独立 Claude 配置避免 OMC 插件开销）
env -u CLAUDECODE \
    no_proxy="open.feishu.cn,feishu.cn,lark.com,msg-frontier.feishu.cn" \
    NO_PROXY="open.feishu.cn,feishu.cn,lark.com,msg-frontier.feishu.cn" \
    CLAUDE_CONFIG_DIR="$(dirname "$0")/.claude_config" \
    NODE_OPTIONS="--dns-result-order=ipv4first" \
    CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK=1 \
    nohup python3 -u feishu_websocket.py > feishu_latest.log 2>&1 &

sleep 3

# 检查是否启动成功
if ps aux | grep -v grep | grep "python3.*feishu_websocket.py" > /dev/null; then
    echo "✅ 服务启动成功"
    echo "📋 查看日志: tail -f feishu_latest.log"
    echo ""
    echo "最近日志："
    tail -10 feishu_latest.log 2>/dev/null || echo "日志文件尚未生成"
else
    echo "❌ 服务启动失败，请查看日志"
    if [ -f feishu_latest.log ]; then
        tail -20 feishu_latest.log
    else
        echo "日志文件不存在"
    fi
fi
