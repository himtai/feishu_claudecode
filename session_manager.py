"""
会话状态管理
用于保存等待用户交互的 Claude Agent 会话
"""
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any

class SessionManager:
    """管理等待用户交互的会话"""

    def __init__(self, storage_dir: str = ".sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def save_pending_question(
        self,
        chat_id: str,
        user_id: str,
        session_id: str,
        question_data: Dict[str, Any],
        prompt: str,
        previous_response: str = None
    ):
        """保存等待回答的问题"""
        session_file = self.storage_dir / f"{chat_id}.json"

        # 如果已有会话，保留历史记录
        conversation_history = []
        if session_file.exists():
            with open(session_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                conversation_history = existing_data.get('conversation_history', [])

        # 添加当前对话到历史
        conversation_history.append({
            'prompt': prompt,
            'response': previous_response,
            'timestamp': time.time()
        })

        # 只保留最近 5 轮对话
        conversation_history = conversation_history[-5:]

        data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "session_id": session_id,
            "question_data": question_data,
            "original_prompt": prompt,
            "previous_response": previous_response,
            "conversation_history": conversation_history,
            "timestamp": time.time(),
            "status": "waiting"
        }

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"保存会话: {chat_id}, session_id: {session_id}")

    def get_pending_question(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """获取等待回答的问题"""
        session_file = self.storage_dir / f"{chat_id}.json"

        if not session_file.exists():
            return None

        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否超时（30分钟）
        if time.time() - data.get("timestamp", 0) > 1800:
            self.clear_session(chat_id)
            return None

        return data

    def save_answer(self, chat_id: str, answer: Dict[str, str]):
        """保存用户的答案，并标记为已回答但保持会话活跃"""
        session_file = self.storage_dir / f"{chat_id}.json"

        if not session_file.exists():
            return False

        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        data["answer"] = answer
        data["status"] = "active"  # 改为 active 而不是 answered
        data["answer_timestamp"] = time.time()

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    def get_active_session(self, chat_id: str) -> Optional[str]:
        """获取活跃会话的 session_id"""
        session_file = self.storage_dir / f"{chat_id}.json"

        if not session_file.exists():
            return None

        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否超时（30分钟）
        if time.time() - data.get("timestamp", 0) > 1800:
            return None

        status = data.get("status")
        if status in ["active", "answered"]:
            return data.get("session_id")

        return None

    def clear_session(self, chat_id: str):
        """清除会话"""
        session_file = self.storage_dir / f"{chat_id}.json"
        if session_file.exists():
            session_file.unlink()
        print(f"清除会话: {chat_id}")

    def has_pending_question(self, chat_id: str) -> bool:
        """检查是否有等待回答的问题"""
        data = self.get_pending_question(chat_id)
        return data is not None and data.get("status") == "waiting"

    def save_conversation(self, chat_id: str, user_id: str, session_id: str, prompt: str, response: str = None):
        """保存普通对话历史"""
        session_file = self.storage_dir / f"{chat_id}.json"

        # 读取现有会话
        conversation_history = []
        existing_status = "active"
        if session_file.exists():
            with open(session_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                conversation_history = existing_data.get('conversation_history', [])
                existing_status = existing_data.get('status', 'active')

        # 添加当前对话
        conversation_history.append({
            'prompt': prompt,
            'response': response,
            'timestamp': time.time()
        })

        # 只保留最近 5 轮对话
        conversation_history = conversation_history[-5:]

        data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "session_id": session_id,
            "conversation_history": conversation_history,
            "timestamp": time.time(),
            "status": existing_status
        }

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_conversation_history(self, chat_id: str) -> str:
        """获取对话历史的文本摘要"""
        session_file = self.storage_dir / f"{chat_id}.json"

        if not session_file.exists():
            return ""

        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        history = data.get('conversation_history', [])
        if not history:
            return ""

        # 构建历史摘要
        lines = []
        for item in history[-3:]:  # 只取最近 3 轮
            prompt = item.get('prompt', '')
            if prompt:
                lines.append(f"用户: {prompt[:100]}")  # 限制长度
            response = item.get('response', '')
            if response:
                lines.append(f"助手: {response[:100]}")

        return "\n".join(lines) if lines else ""

# 全局会话管理器
session_manager = SessionManager()
