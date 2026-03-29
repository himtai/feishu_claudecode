# 飞书 Claude Agent

在飞书中使用完整的 Claude Code 能力，通过 WebSocket 长连接接收消息，无需公网 IP。

## 功能特性

- **完整 Claude Code 能力** — 读写文件、执行命令、搜索代码、网络抓取
- **双重状态显示** — 表情回应（即时反馈）+ 动态卡片（详细进度）
- **会话持续性** — 支持多轮对话，上下文自动保持
- **交互式选择** — 自动检测选项列表，用户可回复编号继续
- **文件/图片发送** — Claude 可主动发送文件和图片到飞书
- **用户命令** — `/new` 新对话、`/cancel` 取消任务、`/status` 查看状态

## 状态指示

执行过程中，用户消息上会自动显示表情回应，同时推送动态卡片：

| 表情 | 含义 |
|------|------|
| 💭 | 思考中 |
| 📖 | 读取文件 |
| 🧠 | 写入/编辑文件 |
| 👀 | 搜索代码 |
| 🎯 | 执行命令 |
| 🤫 | 等待用户回答 |
| 😌 | 等待批准（计划模式）|
| ✅ | 完成 |
| ❌ | 出错 |

## 前提条件

本项目基于 [Claude Code](https://claude.ai/code) 运行，部署前需确保：

1. **安装 Claude Code CLI**
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **登录 Claude Code**
   ```bash
   claude
   ```
   按提示完成登录，确保 `claude` 命令可正常使用。

3. **Python 3.8+**

> 飞书机器人在收到消息时会以子进程方式启动 Claude Agent，与你在终端中直接使用的 Claude Code 相互独立，共用同一套安装和 API 配额。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 飞书应用凭证
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret

# Anthropic API
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_BASE_URL=https://api.anthropic.com  # 可选，自定义端点

# Claude Agent 工作目录
PROJECT_ROOT=/path/to/your/workspace
```

### 3. 飞书应用配置

**开发配置 → 事件与回调：**
- 开启**长连接**模式（无需公网 IP）
- 订阅事件：`im.message.receive_v1`

**开发配置 → 回调配置：**
- 添加**卡片回传交互**（用于按钮点击回调）

**权限管理：**
- `im:message`（消息发送）
- `im:message.reaction`（消息表情回应）
- `im:message:send_as_bot`（机器人发送消息）

### 4. 启动服务

```bash
env -u CLAUDECODE python3 -u feishu_websocket.py > feishu_latest.log 2>&1 &
```

> 注意：必须用 `env -u CLAUDECODE` 启动，避免与外部 Claude Code 环境冲突。

## 项目结构

```
feishu_claudecode/
├── feishu_websocket.py       # 主程序，WebSocket 长连接
├── execute_claude.py         # Claude Agent 执行器（子进程）
├── async_message_handler.py  # 异步消息处理
├── session_manager.py        # 会话状态管理
├── status_notifier.py        # 实时状态通知（动态卡片）
├── reaction_indicator.py     # 表情回应状态指示器
├── file_uploader.py          # 飞书文件上传
├── feishu_tools.py           # Claude 可调用的飞书工具
├── send_to_feishu.py         # 主动发送文件/图片
├── start.sh / stop.sh        # 启停脚本
└── requirements.txt
```

## 技术架构

```
用户发送消息
    ↓
feishu_websocket.py（WebSocket 接收）
    ↓
async_message_handler.py（异步处理）
    ↓
execute_claude.py（子进程运行 Claude Agent）
    ↓
StatusNotifier
    ├── 表情回应（在用户消息上显示状态）
    └── 动态卡片（实时更新详细进度）
    ↓
结果发送回飞书
```

## 注意事项

- Claude Agent 运行在 `plan` 模式，危险操作需用户批准
- 会话 30 分钟无活动后自动清除
- `.env` 文件包含敏感凭证，已加入 `.gitignore`
