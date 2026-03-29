"""
实时状态通知器
监听 Claude Agent 执行状态并推送到飞书
支持动态更新卡片 + 表情回应状态指示
"""
import json
import time
import threading
from typing import Optional
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from reaction_indicator import ReactionIndicator, StatusEmoji


class StatusNotifier:
    """实时状态通知（支持动态更新 + 表情回应）"""

    def __init__(self, client: lark.Client, chat_id: str, user_message_id: str = None):
        self.client = client
        self.chat_id = chat_id
        self.user_message_id = user_message_id  # 用户消息 ID（用于添加表情回应）
        self.current_status = None
        self.status_message_id = None
        self.start_time = time.time()
        self.update_timer = None
        self.is_active = True
        self.current_card_data = None  # 保存当前卡片数据用于更新

        # 表情回应指示器（轻量级状态提示）
        self.reaction_indicator = ReactionIndicator(client) if user_message_id else None

        # 统计信息
        self.tool_count = 0  # 工具调用次数
        self.token_usage = {"input": 0, "output": 0}  # token 使用量
        self.current_step = ""  # 当前步骤描述
        self.thinking_buffer = ""  # 思考内容缓冲区（保留完整思考）
        self.last_thinking_update = 0  # 上次更新思考内容的时间
        self.current_tool_info = ""  # 当前工具执行信息

    def _send_status_card(self, title: str, content: str, color: str = "blue") -> Optional[str]:
        """发送状态卡片，返回消息 ID（支持分区显示）"""
        try:
            # 添加运行时间
            elapsed = int(time.time() - self.start_time)
            time_str = f"{elapsed}s" if elapsed < 60 else f"{elapsed//60}m {elapsed%60}s"

            # 构建统计信息
            stats = f"⏱️ {time_str}"
            if self.tool_count > 0:
                stats += f" | 🔧 {self.tool_count} 次工具调用"
            if self.token_usage["input"] > 0 or self.token_usage["output"] > 0:
                total_tokens = self.token_usage["input"] + self.token_usage["output"]
                stats += f" | 🎯 {total_tokens:,} tokens"

            # 构建分区内容
            elements = []

            # 如果有思考内容，添加思考区域
            if self.thinking_buffer:
                thinking_display = self.thinking_buffer[-800:] if len(self.thinking_buffer) > 800 else self.thinking_buffer
                if len(self.thinking_buffer) > 800:
                    thinking_display = "..." + thinking_display

                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**💭 思考过程：**\n```\n{thinking_display}\n```"
                    }
                })
                elements.append({"tag": "hr"})  # 分隔线

            # 添加当前状态区域
            if self.current_tool_info:
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**⚙️ 当前操作：**\n{self.current_tool_info}"
                    }
                })
            else:
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                })

            # 添加统计信息
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": stats
                }
            })

            card = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": color
                },
                "elements": elements
            }

            # 保存卡片数据用于后续更新
            self.current_card_data = {
                "title": title,
                "content": content,
                "color": color
            }

            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(self.chat_id)
                    .msg_type("interactive")
                    .content(json.dumps(card))
                    .build()) \
                .build()

            response = self.client.im.v1.message.create(request)
            if response.success():
                return response.data.message_id
            return None

        except Exception as e:
            print(f"发送状态卡片失败: {e}")
            return None

    def _update_status_card(self):
        """更新状态卡片（更新运行时间和统计信息）"""
        if not self.status_message_id or not self.is_active:
            return

        try:
            # 计算运行时间
            elapsed = int(time.time() - self.start_time)
            time_str = f"{elapsed}s" if elapsed < 60 else f"{elapsed//60}m {elapsed%60}s"

            # 构建统计信息
            stats = f"⏱️ {time_str}"
            if self.tool_count > 0:
                stats += f" | 🔧 {self.tool_count} 次工具调用"
            if self.token_usage["input"] > 0 or self.token_usage["output"] > 0:
                total_tokens = self.token_usage["input"] + self.token_usage["output"]
                stats += f" | 🎯 {total_tokens:,} tokens"

            # 构建分区内容
            elements = []

            # 如果有思考内容，添加思考区域
            if self.thinking_buffer:
                thinking_display = self.thinking_buffer[-800:] if len(self.thinking_buffer) > 800 else self.thinking_buffer
                if len(self.thinking_buffer) > 800:
                    thinking_display = "..." + thinking_display

                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**💭 思考过程：**\n```\n{thinking_display}\n```"
                    }
                })
                elements.append({"tag": "hr"})

            # 添加当前状态区域
            if self.current_tool_info:
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**⚙️ 当前操作：**\n{self.current_tool_info}"
                    }
                })
            elif self.current_card_data:
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": self.current_card_data.get("content", "")
                    }
                })

            # 添加统计信息
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": stats
                }
            })

            # 构建更新后的卡片
            card = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": self.current_card_data.get("title", "执行中") if self.current_card_data else "执行中"},
                    "template": self.current_card_data.get("color", "blue") if self.current_card_data else "blue"
                },
                "elements": elements
            }

            # 使用 patch API 更新消息
            patch_request = PatchMessageRequest.builder() \
                .message_id(self.status_message_id) \
                .request_body(PatchMessageRequestBody.builder()
                    .content(json.dumps(card))
                    .build()) \
                .build()

            self.client.im.v1.message.patch(patch_request)

        except Exception as e:
            print(f"更新状态卡片失败: {e}")

    def _update_loop(self):
        """更新循环（在后台线程中运行）"""
        last_update = time.time()
        while self.is_active and self.current_status not in ["completed", "error"]:
            current_time = time.time()
            # 每1秒更新一次，使用固定间隔
            if current_time - last_update >= 1.0:
                # 先更新时间戳，避免 API 延迟影响下次更新
                last_update = last_update + 1.0  # 使用固定增量而不是 current_time
                self._update_status_card()
            time.sleep(0.1)  # 短暂休眠避免CPU占用

    def _start_update_timer(self):
        """启动定时更新（使用后台线程而不是递归定时器）"""
        if self.update_timer:
            return  # 已经在运行

        def run_update_loop():
            self._update_loop()

        self.update_timer = threading.Thread(target=run_update_loop, daemon=True)
        self.update_timer.start()

    def _stop_update_timer(self):
        """停止定时更新"""
        self.is_active = False
        if self.update_timer:
            # 等待线程结束
            if self.update_timer.is_alive():
                self.update_timer.join(timeout=2.0)
            self.update_timer = None

    def notify_thinking(self):
        """通知：正在思考"""
        if self.current_status != "thinking":
            self.current_status = "thinking"
            self.thinking_buffer = ""  # 清空思考缓冲区

            # 添加表情回应（轻量级提示）
            if self.reaction_indicator and self.user_message_id:
                self.reaction_indicator.show_thinking(self.user_message_id)

            self.status_message_id = self._send_status_card(
                "🤔 正在思考",
                "Claude 正在分析你的请求...",
                "blue"
            )
            # 启动定时更新
            self._start_update_timer()

    def notify_thinking_text(self, text: str):
        """通知：思考内容（流式更新）"""
        import time

        # 累积思考内容（保留完整内容）
        self.thinking_buffer += text

        # 限制更新频率（每 0.5 秒更新一次，避免过于频繁）
        current_time = time.time()
        if current_time - self.last_thinking_update < 0.5:
            return

        self.last_thinking_update = current_time
        self.current_status = "thinking"

        # 更新卡片数据
        self.current_card_data = {
            "title": "🤔 正在思考",
            "content": "",  # 内容在 _update_status_card 中构建
            "color": "blue"
        }

        # 更新卡片
        self._update_status_card()

    def notify_tool_use(self, tool_name: str, tool_input: dict = None):
        """通知：执行工具"""
        print(f"[DEBUG] notify_tool_use 被调用: tool_name={tool_name}")
        # 增加工具调用计数
        self.tool_count += 1

        # 更新表情回应（根据工具类型）
        if self.reaction_indicator and self.user_message_id:
            self.reaction_indicator.show_tool_execution(self.user_message_id, tool_name)

        tool_icons = {
            "Read": "📖",
            "Write": "✍️",
            "Edit": "✏️",
            "Bash": "⚙️",
            "Glob": "🔍",
            "Grep": "🔎",
            "AskUserQuestion": "❓",
        }

        icon = tool_icons.get(tool_name, "🔧")
        content = f"{icon} 正在执行: **{tool_name}**"

        # 添加工具参数信息
        if tool_input:
            if tool_name == "Read" and "file_path" in tool_input:
                content += f"\n📄 文件: `{tool_input['file_path']}`"
            elif tool_name == "Write" and "file_path" in tool_input:
                content += f"\n📝 创建: `{tool_input['file_path']}`"
            elif tool_name == "Edit" and "file_path" in tool_input:
                content += f"\n✏️ 编辑: `{tool_input['file_path']}`"
            elif tool_name == "Bash" and "command" in tool_input:
                cmd = tool_input['command']
                if len(cmd) > 50:
                    cmd = cmd[:50] + "..."
                content += f"\n💻 命令: `{cmd}`"
            elif tool_name == "Grep" and "pattern" in tool_input:
                content += f"\n🔎 搜索: `{tool_input['pattern']}`"

        self.current_status = f"tool_{tool_name}"
        self.current_step = f"执行 {tool_name}"
        self.current_tool_info = content  # 保存工具信息用于分区显示

        # 更新卡片数据
        self.current_card_data = {
            "title": f"{icon} 执行中",
            "content": content,
            "color": "blue"
        }

        # 更新卡片（保留思考内容）
        self._update_status_card()

    def notify_plan_mode(self, plan_content: str = None):
        """通知：Plan 模式等待批准"""
        content = "📋 Claude 已制定执行计划，等待你的批准"
        if plan_content:
            # 截取计划的前200个字符
            preview = plan_content[:200] + "..." if len(plan_content) > 200 else plan_content
            content += f"\n\n**计划预览**:\n{preview}"

        self.current_status = "plan_waiting"

        # 更新表情回应
        if self.reaction_indicator and self.user_message_id:
            self.reaction_indicator.show_plan_mode(self.user_message_id)

        if self.status_message_id:
            self.current_card_data = {
                "title": "📋 等待批准",
                "content": content,
                "color": "orange"
            }
            self._update_status_card()
        else:
            self.status_message_id = self._send_status_card(
                "📋 等待批准",
                content,
                "orange"
            )

    def notify_waiting_user(self, question: str = None):
        """通知：等待用户回答"""
        content = "⏸️ 等待你的回答"
        if question:
            content += f"\n\n**问题**: {question}"

        self.current_status = "waiting_user"

        # 更新表情回应
        if self.reaction_indicator and self.user_message_id:
            self.reaction_indicator.show_waiting(self.user_message_id)

        if self.status_message_id:
            self.current_card_data = {
                "title": "⏸️ 等待回答",
                "content": content,
                "color": "orange"
            }
            self._update_status_card()
        else:
            self.status_message_id = self._send_status_card(
                "⏸️ 等待回答",
                content,
                "orange"
            )

    def notify_error(self, error_msg: str):
        """通知：执行错误"""
        self.current_status = "error"
        self._stop_update_timer()

        # 更新表情回应
        if self.reaction_indicator and self.user_message_id:
            self.reaction_indicator.show_error(self.user_message_id)

        if self.status_message_id:
            self.current_card_data = {
                "title": "❌ 执行错误",
                "content": f"```\n{error_msg}\n```",
                "color": "red"
            }
            self._update_status_card()
        else:
            self.status_message_id = self._send_status_card(
                "❌ 执行错误",
                f"```\n{error_msg}\n```",
                "red"
            )

    def notify_completed(self):
        """通知：执行完成"""
        self.current_status = "completed"
        self._stop_update_timer()

        # 更新表情回应为完成状态
        if self.reaction_indicator and self.user_message_id:
            self.reaction_indicator.show_completed(self.user_message_id)

        elapsed = int(time.time() - self.start_time)
        time_str = f"{elapsed}s" if elapsed < 60 else f"{elapsed//60}m {elapsed%60}s"

        # 构建完成统计
        stats = f"⏱️ 总耗时: {time_str}"
        if self.tool_count > 0:
            stats += f"\n🔧 工具调用: {self.tool_count} 次"
        if self.token_usage["input"] > 0 or self.token_usage["output"] > 0:
            total_tokens = self.token_usage["input"] + self.token_usage["output"]
            stats += f"\n🎯 Token 消耗: {total_tokens:,} (输入: {self.token_usage['input']:,}, 输出: {self.token_usage['output']:,})"

        if self.status_message_id:
            self.current_card_data = {
                "title": "✅ 执行完成",
                "content": stats,
                "color": "green"
            }
            self._update_status_card()
        else:
            self.status_message_id = self._send_status_card(
                "✅ 执行完成",
                stats,
                "green"
            )

    def update_token_usage(self, input_tokens: int, output_tokens: int):
        """更新 token 使用量"""
        self.token_usage["input"] += input_tokens
        self.token_usage["output"] += output_tokens
