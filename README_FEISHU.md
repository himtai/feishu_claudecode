# 飞书 Claude Agent 使用指南

## 功能特性

✅ **完整的 Claude Code 能力**
- 文件读取、编辑、创建
- 执行 Shell 命令
- 代码搜索和分析
- 网络搜索和抓取

✅ **实时反馈**
- 工具调用过程可视化
- 执行状态实时更新
- 错误信息即时提示

✅ **会话管理**
- 支持多轮对话
- 上下文自动保持
- 可随时重置会话

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
nano .env
```

### 3. 运行服务

```bash
python feishu_agent_bot.py
```

### 4. 配置 ngrok（本地测试）

```bash
ngrok http 8080
```

### 5. 配置飞书事件订阅

- 请求地址: `https://your-ngrok-url.ngrok.io/webhook`
- 订阅事件: `im.message.receive_v1`

## 使用示例

### 基础操作

**查看文件**
```
读取 src/main.py 文件的内容
```

**编辑代码**
```
帮我重构 auth.py，将所有的同步函数改为异步函数
```

**执行命令**
```
运行 pytest 并告诉我测试结果
```

### 高级操作

**代码分析**
```
分析整个项目，找出所有的性能瓶颈
```

**批量修改**
```
将所有 Python 文件的 print 语句改为使用 logging
```

**调试问题**
```
tests/test_api.py 测试失败了，帮我找出原因并修复
```

### 特殊命令

- `/help` - 显示帮助信息
- `/cancel` - 取消当前正在执行的任务
- `/reset` - 重置会话，清除历史记录
- `/status` - 查看当前状态

## 工作流程示例

### 场景1：修复 Bug

**用户**: "用户登录接口返回 500 错误，帮我排查"

**Agent 执行过程**:
1. 🔧 Read - 读取登录接口代码
2. 🔧 Grep - 搜索相关日志
3. 🔧 Bash - 查看错误日志
4. 🔧 Edit - 修复代码
5. 🔧 Bash - 运行测试验证

**飞书反馈**:
- 实时显示每个工具的调用
- 显示找到的问题
- 显示修复方案
- 显示测试结果

### 场景2：添加新功能

**用户**: "添加一个用户注册接口，包括邮箱验证"

**Agent 执行过程**:
1. 🔧 Read - 读取现有代码结构
2. 🔧 Write - 创建新的路由文件
3. 🔧 Edit - 更新主路由配置
4. 🔧 Write - 创建测试文件
5. 🔧 Bash - 运行测试

### 场景3：代码审查

**用户**: "审查 PR #123 的代码质量"

**Agent 执行过程**:
1. 🔧 Bash - 获取 PR 差异
2. 🔧 Read - 读取变更的文件
3. 🔧 WebSearch - 查找最佳实践
4. 📝 生成审查报告

## 权限管理

Agent 在执行危险操作时会请求确认：

- ⚠️ 删除文件
- ⚠️ 修改关键配置
- ⚠️ 执行系统命令
- ⚠️ 网络请求

你可以在飞书中批准或拒绝这些操作。

## 高级配置

### 自定义工具集

编辑 `feishu_agent_bot.py` 中的 `allowed_tools`:

```python
allowed_tools=[
    "Read", "Write", "Edit",  # 文件操作
    "Bash",                    # 命令执行
    "Glob", "Grep",           # 搜索
    "WebSearch", "WebFetch",  # 网络
    "Agent"                    # 子代理
]
```

### 权限模式

- `default` - 需要确认危险操作（推荐）
- `acceptEdits` - 自动批准文件编辑
- `bypassPermissions` - 跳过所有确认（谨慎使用）

### 项目路径

设置 `PROJECT_ROOT` 环境变量指定工作目录：

```bash
PROJECT_ROOT=/home/user/my-project
```

## 生产部署

### 使用 Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "feishu_agent_bot.py"]
```

### 使用 Systemd

```ini
[Unit]
Description=Feishu Claude Agent Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/feishu-agent
EnvironmentFile=/opt/feishu-agent/.env
ExecStart=/usr/bin/python3 feishu_agent_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 使用云服务

推荐部署到：
- 阿里云 ECS
- 腾讯云 CVM
- AWS EC2

确保：
- ✅ 配置 HTTPS（飞书要求）
- ✅ 设置防火墙规则
- ✅ 配置日志收集
- ✅ 设置监控告警

## 安全建议

1. **API Key 安全**
   - 使用环境变量，不要硬编码
   - 定期轮换密钥
   - 限制 API Key 权限

2. **文件访问控制**
   - 限制 `PROJECT_ROOT` 范围
   - 不要使用 root 用户运行
   - 定期审查文件操作日志

3. **命令执行限制**
   - 避免使用 `bypassPermissions` 模式
   - 审查所有 Bash 命令
   - 设置命令超时

4. **网络安全**
   - 使用 HTTPS
   - 配置 IP 白名单
   - 启用请求签名验证

## 故障排查

### 机器人不响应

1. 检查服务是否运行: `ps aux | grep feishu_agent_bot`
2. 查看日志: `tail -f /var/log/feishu-agent.log`
3. 验证 ngrok/域名是否可访问
4. 检查飞书事件订阅配置

### API 调用失败

1. 验证 API Key: `echo $ANTHROPIC_API_KEY`
2. 检查网络连接: `curl https://api.anthropic.com`
3. 查看 API 配额和限制

### 权限错误

1. 检查飞书应用权限配置
2. 重新发布应用版本
3. 验证用户是否在应用可见范围内

## 常见问题

**Q: 可以同时处理多个用户的请求吗？**
A: 可以，每个用户有独立的会话和任务队列。

**Q: 会话会保持多久？**
A: 会话会一直保持，直到用户发送 `/reset` 或服务重启。

**Q: 可以访问私有仓库吗？**
A: 可以，只要服务器有相应的 SSH 密钥或访问令牌。

**Q: 支持哪些编程语言？**
A: 支持所有语言，Claude 可以理解和编辑任何文本文件。

**Q: 如何限制 Agent 的权限？**
A: 通过 `allowed_tools` 和 `permission_mode` 配置。

## 更新日志

### v1.0.0 (2024-01-XX)
- ✅ 基础功能实现
- ✅ 工具调用可视化
- ✅ 会话管理
- ✅ 特殊命令支持

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
