"""
持久化 Claude Agent 管理器
为每个用户维护一个长期运行的 Claude Agent 会话
"""
import asyncio
from typing import Dict, Optional
from claude_agent_sdk import query, ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny
import time
from collections import deque


class PersistentAgentManager:
    """持久化 Agent 管理器"""

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.agents: Dict[str, 'AgentSession'] = {}  # chat_id -> AgentSession
        self.cleanup_task = None

    def get_or_create_agent(self, chat_id: str, user_id: str) -> 'AgentSession':
        """获取或创建 Agent 会话"""
        if chat_id not in self.agents:
            print(f"创建新的 Agent 会话: {chat_id}")
            self.agents[chat_id] = AgentSession(chat_id, user_id, self.work_dir)
        else:
            self.agents[chat_id].last_active = time.time()
        return self.agents[chat_id]

    def clear_agent(self, chat_id: str):
        """清除指定的 Agent 会话"""
        if chat_id in self.agents:
            agent = self.agents[chat_id]
            # 立即取消正在运行的 asyncio 任务
            if agent.current_task is not None and agent.current_loop is not None:
                if not agent.current_task.done():
                    agent.current_loop.call_soon_threadsafe(agent.current_task.cancel)
            # 停止状态通知器的后台更新线程，避免旧卡片时间继续跳动
            if agent.current_notifier is not None:
                agent.current_notifier._stop_update_timer()
                agent.current_notifier = None
            print(f"清除 Agent 会话: {chat_id}")
            del self.agents[chat_id]

    async def cleanup_inactive_agents(self):
        """清理不活跃的 Agent（超过30分钟）"""
        while True:
            await asyncio.sleep(300)
            current_time = time.time()
            inactive_chats = [
                chat_id for chat_id, agent in self.agents.items()
                if current_time - agent.last_active > 1800
            ]
            for chat_id in inactive_chats:
                print(f"清理不活跃会话: {chat_id}")
                del self.agents[chat_id]

    def start_cleanup(self):
        """启动清理任务（在后台线程中）"""
        if self.cleanup_task is None:
            import threading

            def run_cleanup():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.cleanup_inactive_agents())

            thread = threading.Thread(target=run_cleanup, daemon=True)
            thread.start()
            print("清理任务已在后台线程启动")


class AgentSession:
    """单个 Agent 会话"""

    def __init__(self, chat_id: str, user_id: str, work_dir: str):
        self.chat_id = chat_id
        self.user_id = user_id
        self.work_dir = work_dir
        self.session_id: Optional[str] = None
        self.conversation_history = []
        self.last_active = time.time()
        self.is_processing = False
        self.message_queue = deque()
        self.queue_size = 0
        self.cancel_queue = False
        self.escape_requested = False
        self.permission_queue: Optional[asyncio.Queue] = None
        self.permission_loop = None
        self.current_notifier = None  # 当前活跃的状态通知器
        self.current_task = None   # 当前 asyncio Task
        self.current_loop = None   # 当前 asyncio 事件循环

    def get_queue_position(self) -> int:
        return self.queue_size

    def is_busy(self) -> bool:
        return self.is_processing or len(self.message_queue) > 0

    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': time.time()
        })

    def get_context_summary(self) -> str:
        if not self.conversation_history:
            return ""
        recent = self.conversation_history[-20:]
        lines = []
        for item in recent:
            role = "用户" if item['role'] == 'user' else "助手"
            lines.append(f"{role}: {item['content'][:300]}")
        return "\n".join(lines)

    async def send_message(self, prompt: str, options: ClaudeAgentOptions, status_callback=None, feishu_client=None):
        """发送消息到 Agent"""
        self.is_processing = True
        self.last_active = time.time()
        self.add_to_history('user', prompt)
        print(f"[DEBUG] send_message 被调用, feishu_client={'有' if feishu_client else '无'}")

        try:
            result_text = ""
            tool_calls = []

            async def process_messages(message_iter, sdk_client=None):
                nonlocal result_text
                async for message in message_iter:
                    msg_type = type(message).__name__
                    print(f"[DEBUG] 收到消息类型: {msg_type}")

                    if self.escape_requested:
                        print("[ESC] 用户请求打断")
                        self.escape_requested = False
                        if sdk_client:
                            await sdk_client.interrupt()
                        break

                    if msg_type == 'SystemMessage':
                        if hasattr(message, 'data') and isinstance(message.data, dict):
                            if message.data.get('subtype') == 'init':
                                self.session_id = message.data.get('session_id')
                                print(f"  会话 ID: {self.session_id}")

                    if msg_type == 'ToolUseMessage':
                        if hasattr(message, 'tool_name'):
                            tool_name = message.tool_name
                            tool_calls.append(tool_name)
                            if status_callback:
                                tool_input = getattr(message, 'tool_input', {})
                                status_callback('tool_use', {'tool_name': tool_name, 'tool_input': tool_input})

                    if msg_type == 'ResultMessage':
                        print(f"[DEBUG] ResultMessage")
                        if hasattr(message, 'usage') and message.usage:
                            if isinstance(message.usage, dict):
                                input_tokens = message.usage.get('input_tokens', 0)
                                output_tokens = message.usage.get('output_tokens', 0)
                            else:
                                input_tokens = getattr(message.usage, 'input_tokens', 0)
                                output_tokens = getattr(message.usage, 'output_tokens', 0)
                            print(f"[DEBUG] Token 使用: input={input_tokens}, output={output_tokens}")
                            if status_callback and (input_tokens > 0 or output_tokens > 0):
                                status_callback('token_usage', {'input_tokens': input_tokens, 'output_tokens': output_tokens})
                        if hasattr(message, 'result') and message.result:
                            result_text = message.result

                    if msg_type == 'AssistantMessage':
                        if hasattr(message, 'content') and message.content:
                            for block in message.content:
                                block_type = type(block).__name__
                                if block_type == 'TextBlock' and hasattr(block, 'text'):
                                    text_content = block.text
                                    result_text += text_content
                                    print(f"[DEBUG] TextBlock: {text_content[:100]}...")
                                    if status_callback and text_content.strip():
                                        status_callback('thinking_text', {'text': text_content})
                                elif block_type == 'ToolUseBlock':
                                    tool_name = block.name if hasattr(block, 'name') else 'Unknown'
                                    tool_input = block.input if hasattr(block, 'input') else {}
                                    tool_calls.append(tool_name)
                                    if status_callback:
                                        status_callback('tool_use', {'tool_name': tool_name, 'tool_input': tool_input})

            if feishu_client:
                print(f"[Permission] 使用 ClaudeSDKClient 路径")
                from dataclasses import replace as dc_replace
                from feishu_client import send_permission_card

                async def can_use_tool(tool_name: str, tool_input: dict, ctx):
                    # 只拦截 Bash，其他工具自动允许
                    if tool_name != "Bash":
                        return PermissionResultAllow()
                    self.permission_queue = asyncio.Queue()
                    self.permission_loop = asyncio.get_event_loop()
                    send_permission_card(feishu_client, self.chat_id, tool_name, tool_input)
                    print(f"[Permission] 等待用户决定: {tool_name}")
                    try:
                        decision = await asyncio.wait_for(self.permission_queue.get(), timeout=120)
                    except asyncio.TimeoutError:
                        decision = "deny"
                    print(f"[Permission] 用户决定: {decision}")
                    if decision in ("allow", "allow_always"):
                        return PermissionResultAllow()
                    else:
                        return PermissionResultDeny(message="用户拒绝", interrupt=True)

                sdk_options = dc_replace(options, can_use_tool=can_use_tool)

                async def prompt_stream():
                    yield {
                        "type": "user",
                        "message": {"role": "user", "content": prompt},
                        "parent_tool_use_id": None,
                        "session_id": self.session_id or "default",
                    }

                async with ClaudeSDKClient(sdk_options) as sdk_client:
                    await sdk_client.query(prompt_stream())
                    await process_messages(sdk_client.receive_response(), sdk_client)
            else:
                await process_messages(query(prompt=prompt, options=options))

            if result_text:
                self.add_to_history('assistant', result_text)

            return {
                'result': result_text,
                'tool_calls': tool_calls,
                'session_id': self.session_id
            }

        finally:
            self.is_processing = False
            self.last_active = time.time()


# 全局管理器实例
agent_manager: Optional[PersistentAgentManager] = None


def get_agent_manager(work_dir: str) -> PersistentAgentManager:
    """获取全局 Agent 管理器"""
    global agent_manager
    if agent_manager is None:
        agent_manager = PersistentAgentManager(work_dir)
    return agent_manager
