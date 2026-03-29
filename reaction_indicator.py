"""
表情回应指示器
使用飞书的 Message Reaction API 来显示不同的执行状态
灵感来自 OpenClaw 项目
"""
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageReactionRequest,
    CreateMessageReactionRequestBody,
    DeleteMessageReactionRequest,
    Emoji
)
from typing import Optional, Dict
from enum import Enum


class StatusEmoji(Enum):
    """状态表情枚举"""
    THINKING = "THINKING"           # 💭 思考中
    TYPING = "Typing"               # ⌨️ 正在输入（OpenClaw 使用的）
    GEAR = "MUSCLE"                 # 💪 执行工具（用 MUSCLE 代替，因为没有齿轮）
    DONE = "DONE"                   # ✅ 完成
    THUMBSUP = "THUMBSUP"           # 👍 成功
    ERROR = "ERROR"                 # ❌ 错误
    WAIT = "SILENT"                 # 🤫 等待用户
    PLAN = "EYESCLOSED"             # 😌 计划模式
    READING = "StatusReading"       # 📖 读取文件
    WRITING = "SMART"               # 🧠 写入文件
    SEARCH = "GLANCE"               # 👀 搜索
    EXECUTE = "OnIt"                # 🎯 执行命令


class ReactionIndicator:
    """表情回应指示器（轻量级状态提示）"""

    def __init__(self, client: lark.Client):
        self.client = client
        self.current_reaction_id: Optional[str] = None
        self.current_message_id: Optional[str] = None
        self.current_emoji: Optional[str] = None

    def _add_reaction(self, message_id: str, emoji_type: str) -> Optional[str]:
        """添加表情回应

        Args:
            message_id: 消息 ID
            emoji_type: 表情类型（如 "THINKING", "DONE" 等）

        Returns:
            reaction_id: 表情回应 ID，失败返回 None
        """
        try:
            request = CreateMessageReactionRequest.builder() \
                .message_id(message_id) \
                .request_body(CreateMessageReactionRequestBody.builder()
                    .reaction_type(Emoji.builder()
                        .emoji_type(emoji_type)
                        .build())
                    .build()) \
                .build()

            response = self.client.im.v1.message_reaction.create(request)

            if response.success():
                reaction_id = response.data.reaction_id
                print(f"[Reaction] 添加表情成功: {emoji_type} (reaction_id: {reaction_id})")
                return reaction_id
            else:
                print(f"[Reaction] 添加表情失败: code={response.code}, msg={response.msg}")
                return None

        except Exception as e:
            print(f"[Reaction] 添加表情异常: {e}")
            return None

    def _remove_reaction(self, message_id: str, reaction_id: str) -> bool:
        """移除表情回应

        Args:
            message_id: 消息 ID
            reaction_id: 表情回应 ID

        Returns:
            bool: 是否成功
        """
        try:
            request = DeleteMessageReactionRequest.builder() \
                .message_id(message_id) \
                .reaction_id(reaction_id) \
                .build()

            response = self.client.im.v1.message_reaction.delete(request)

            if response.success():
                print(f"[Reaction] 移除表情成功: {reaction_id}")
                return True
            else:
                print(f"[Reaction] 移除表情失败: code={response.code}, msg={response.msg}")
                return False

        except Exception as e:
            print(f"[Reaction] 移除表情异常: {e}")
            return False

    def set_status(self, message_id: str, status_emoji: StatusEmoji) -> bool:
        """设置状态表情

        如果已有表情，先移除再添加新的
        如果是相同表情，则跳过（避免重复通知）

        Args:
            message_id: 消息 ID
            status_emoji: 状态表情枚举

        Returns:
            bool: 是否成功
        """
        emoji_type = status_emoji.value

        # 如果是相同的表情和消息，跳过（避免重复添加导致多次推送通知）
        if (self.current_message_id == message_id and
            self.current_emoji == emoji_type and
            self.current_reaction_id):
            print(f"[Reaction] 跳过重复表情: {emoji_type}")
            return True

        # 如果有旧表情，先移除
        if self.current_reaction_id and self.current_message_id:
            self._remove_reaction(self.current_message_id, self.current_reaction_id)
            self.current_reaction_id = None

        # 添加新表情
        reaction_id = self._add_reaction(message_id, emoji_type)
        if reaction_id:
            self.current_reaction_id = reaction_id
            self.current_message_id = message_id
            self.current_emoji = emoji_type
            return True

        return False

    def clear_status(self) -> bool:
        """清除当前状态表情

        Returns:
            bool: 是否成功
        """
        if self.current_reaction_id and self.current_message_id:
            success = self._remove_reaction(self.current_message_id, self.current_reaction_id)
            if success:
                self.current_reaction_id = None
                self.current_message_id = None
                self.current_emoji = None
            return success
        return True

    # 便捷方法
    def show_thinking(self, message_id: str) -> bool:
        """显示思考状态"""
        return self.set_status(message_id, StatusEmoji.THINKING)

    def show_typing(self, message_id: str) -> bool:
        """显示输入状态（OpenClaw 风格）"""
        return self.set_status(message_id, StatusEmoji.TYPING)

    def show_tool_execution(self, message_id: str, tool_name: str = None) -> bool:
        """显示工具执行状态

        根据工具类型选择合适的表情
        """
        # 根据工具名称选择表情
        tool_emoji_map = {
            "Read": StatusEmoji.READING,
            "Write": StatusEmoji.WRITING,
            "Edit": StatusEmoji.WRITING,
            "Grep": StatusEmoji.SEARCH,
            "Glob": StatusEmoji.SEARCH,
            "Bash": StatusEmoji.EXECUTE,
        }

        emoji = tool_emoji_map.get(tool_name, StatusEmoji.GEAR)
        return self.set_status(message_id, emoji)

    def show_waiting(self, message_id: str) -> bool:
        """显示等待用户状态"""
        return self.set_status(message_id, StatusEmoji.WAIT)

    def show_plan_mode(self, message_id: str) -> bool:
        """显示计划模式状态"""
        return self.set_status(message_id, StatusEmoji.PLAN)

    def show_completed(self, message_id: str) -> bool:
        """显示完成状态"""
        return self.set_status(message_id, StatusEmoji.DONE)

    def show_error(self, message_id: str) -> bool:
        """显示错误状态"""
        return self.set_status(message_id, StatusEmoji.ERROR)


# 工具名称到表情的映射（用于快速查找）
TOOL_EMOJI_MAP: Dict[str, StatusEmoji] = {
    "Read": StatusEmoji.READING,
    "Write": StatusEmoji.WRITING,
    "Edit": StatusEmoji.WRITING,
    "Grep": StatusEmoji.SEARCH,
    "Glob": StatusEmoji.SEARCH,
    "Bash": StatusEmoji.EXECUTE,
    "AskUserQuestion": StatusEmoji.WAIT,
}
