# 飞书发送工具使用说明

## 发送图片或文件到飞书

当你需要发送图片或文件给用户时，使用以下命令：

```bash
python3 send_to_feishu.py <chat_id> <file_path>
```

### 参数说明
- `chat_id`: 用户的聊天 ID（在飞书消息处理中会自动提供）
- `file_path`: 要发送的文件的绝对路径

### 示例

发送图片：
```bash
python3 send_to_feishu.py oc_a705f033b1636946865d62db4bce6061 /mnt/f/claude\ code/feishu_claudecode/downloads/output.png
```

发送文件：
```bash
python3 send_to_feishu.py oc_a705f033b1636946865d62db4bce6061 /mnt/f/claude\ code/feishu_claudecode/workspace/report.txt
```

### 注意事项
- 文件路径必须是绝对路径
- 支持的图片格式：.png, .jpg, .jpeg, .gif, .webp
- 其他格式会作为文件发送
- 脚本会自动判断文件类型并选择合适的发送方式

### 在飞书 Agent 中使用

当用户要求你发送图片或文件时，你可以：

1. 处理/生成文件
2. 使用 Bash 工具执行 `python3 send_to_feishu.py` 命令
3. 系统会自动将文件发送给用户

**重要**：chat_id 会在运行时环境中提供，通常是 `oc_a705f033b1636946865d62db4bce6061`
