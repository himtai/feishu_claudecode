# 表情回应状态指示器

## 功能说明

在保留原有动态卡片的基础上，新增了**表情回应（Reaction）**功能，用于在用户消息上显示轻量级的状态提示。

灵感来自 [OpenClaw 项目](https://github.com/openclaw/openclaw) 的飞书集成实现。

## 工作原理

使用飞书的 **Message Reaction API**（消息表情回应）来模拟状态指示：
- 在用户消息上添加表情回应
- 根据不同状态切换不同表情
- 任务完成后移除表情

## 支持的状态表情

| 状态 | 表情类型 | 说明 |
|------|---------|------|
| 思考中 | `THINKING` | 💭 Claude 正在思考 |
| 正在输入 | `Typing` | ⌨️ 正在输入（OpenClaw 风格） |
| 读取文件 | `StatusReading` | 📖 读取文件 |
| 写入文件 | `SMART` | 🧠 写入/编辑文件 |
| 搜索 | `GLANCE` | 👀 搜索代码 |
| 执行命令 | `OnIt` | 🎯 执行 Bash 命令 |
| 工具执行 | `MUSCLE` | 💪 通用工具执行 |
| 等待用户 | `SILENT` | 🤫 等待用户回答 |
| 计划模式 | `EYESCLOSED` | 😌 等待批准计划 |
| 完成 | `DONE` | ✅ 任务完成 |
| 错误 | `ERROR` | ❌ 执行错误 |

## 双重状态显示

现在系统同时使用两种方式显示状态：

### 1. 表情回应（轻量级）
- ✅ 即时反馈，用户一眼就能看到状态
- ✅ 不占用聊天空间
- ✅ 自动切换，无需手动管理
- ✅ 避免了原生 input_status API 的兼容性问题

### 2. 动态卡片（详细信息）
- ✅ 显示思考过程（流式更新）
- ✅ 显示当前操作（工具执行详情）
- ✅ 显示统计信息（运行时间、工具次数、Token 消耗）
- ✅ 实时更新（每秒刷新）

## 使用方法

### 基本用法

```python
from reaction_indicator import ReactionIndicator, StatusEmoji
import lark_oapi as lark

# 创建客户端
client = lark.Client.builder() \
    .app_id(app_id) \
    .app_secret(app_secret) \
    .build()

# 创建表情回应指示器
indicator = ReactionIndicator(client)

# 显示思考状态
indicator.show_thinking(message_id)

# 显示工具执行状态（自动选择合适的表情）
indicator.show_tool_execution(message_id, "Read")

# 显示完成状态
indicator.show_completed(message_id)

# 清除表情
indicator.clear_status()
```

### 集成到 StatusNotifier

```python
from status_notifier import StatusNotifier

# 创建状态通知器（传入用户消息 ID）
notifier = StatusNotifier(client, chat_id, user_message_id)

# 通知思考（自动添加表情回应）
notifier.notify_thinking()

# 通知工具执行（自动切换表情）
notifier.notify_tool_use("Read", {"file_path": "/path/to/file"})

# 通知完成（自动切换为完成表情）
notifier.notify_completed()
```

## 测试

运行测试脚本查看效果：

```bash
# 先在飞书中发送一条消息，获取 message_id
# 然后运行测试
python3 test_reaction.py <chat_id> <message_id>
```

测试脚本会依次展示所有状态表情，每个状态停留 2 秒。

## 技术细节

### 防止重复添加

```python
# 如果是相同的表情和消息，跳过（避免重复推送通知）
if (self.current_message_id == message_id and
    self.current_emoji == emoji_type and
    self.current_reaction_id):
    return True
```

### 自动切换表情

```python
# 移除旧表情，添加新表情
if self.current_reaction_id:
    self._remove_reaction(self.current_message_id, self.current_reaction_id)
reaction_id = self._add_reaction(message_id, emoji_type)
```

### 工具类型映射

```python
TOOL_EMOJI_MAP = {
    "Read": StatusEmoji.READING,      # 📖
    "Write": StatusEmoji.WRITING,     # 🧠
    "Edit": StatusEmoji.WRITING,      # 🧠
    "Grep": StatusEmoji.SEARCH,       # 👀
    "Glob": StatusEmoji.SEARCH,       # 👀
    "Bash": StatusEmoji.EXECUTE,      # 🎯
}
```

## 优势

相比原生 `input_status` API：

1. ✅ **稳定可靠** - 使用成熟的 Message Reaction API
2. ✅ **视觉明确** - 用户能清楚看到具体的状态表情
3. ✅ **无兼容性问题** - 不依赖可能不可用的 API
4. ✅ **丰富的状态** - 支持多种状态，不只是"正在输入"
5. ✅ **自动管理** - 自动切换和清除，无需手动维护

## 参考

- [OpenClaw 项目](https://github.com/openclaw/openclaw)
- [飞书表情回应 API](https://open.feishu.cn/document/server-docs/im-v1/message-reaction/emojis-introduce)
- [飞书支持的表情列表](https://github.com/go-lark/lark/blob/main/emoji.go)

## 更新日志

### 2026-03-21
- ✅ 创建 `reaction_indicator.py` 模块
- ✅ 集成到 `StatusNotifier`
- ✅ 支持根据工具类型自动选择表情
- ✅ 添加测试脚本
- ✅ 完善文档
