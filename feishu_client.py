"""
飞书客户端工具
统一的消息发送接口，消除代码重复
"""
import json
import requests
import os
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody


def _get_tenant_access_token():
    """获取 tenant_access_token"""
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": app_id,
        "app_secret": app_secret
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)
        print(f"[DEBUG] Token 响应状态码: {response.status_code}")
        print(f"[DEBUG] Token 响应内容: {response.text[:200]}")
        result = response.json()

        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            print(f"获取 token 失败: {result}")
            return None
    except Exception as e:
        print(f"获取 token 异常: {e}")
        return None


def set_typing_status(client, chat_id: str, user_id: str, status: str = "typing") -> bool:
    """设置输入状态

    Args:
        client: 飞书客户端（未使用，保持接口一致）
        chat_id: 聊天 ID
        user_id: 用户 ID（必需）
        status: 状态，"typing" 表示正在输入，"" 表示清除输入状态

    Returns:
        bool: 是否成功
    """
    try:
        # 获取 access token
        token = _get_tenant_access_token()
        if not token:
            print("[DEBUG] 无法获取 access token")
            return False

        # 构建请求 URL（使用 PATCH 方法）
        url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/input_status"

        print(f"[DEBUG] chat_id: {chat_id}")
        print(f"[DEBUG] user_id: {user_id}")
        print(f"[DEBUG] 请求 URL: {url}")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        # 构建请求体（user_id 和 user_id_type 是必需的）
        data = {
            "user_id": user_id,
            "user_id_type": "open_id",
            "status": status
        }

        print(f"[DEBUG] 请求体: {data}")

        response = requests.patch(url, headers=headers, json=data, timeout=5)
        print(f"[DEBUG] 输入状态响应状态码: {response.status_code}")
        print(f"[DEBUG] 输入状态响应内容: {response.text[:500]}")

        if response.status_code == 404:
            print("[DEBUG] 404 错误 - 可能的原因：")
            print("  1. 机器人不在该会话中")
            print("  2. 应用权限不足")
            return False

        result = response.json()

        if result.get("code") == 0:
            print(f"[DEBUG] 输入状态设置成功: {status if status else 'cleared'}")
            return True
        else:
            print(f"[DEBUG] 输入状态设置失败: code={result.get('code')}, msg={result.get('msg')}")
            return False

    except Exception as e:
        print(f"❌ 设置输入状态异常: {e}")
        return False


def send_message(client, chat_id: str, text: str) -> bool:
    """发送文本消息到飞书"""
    try:
        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()) \
            .build()

        response = client.im.v1.message.create(request)
        return response.success()

    except Exception as e:
        print(f"❌ 发送消息异常: {e}")
        return False


def send_card(client, chat_id: str, title: str, content: str, color: str = "blue") -> bool:
    """发送卡片消息到飞书"""
    try:
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}}
            ]
        }

        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("interactive")
                .content(json.dumps(card))
                .build()) \
            .build()

        response = client.im.v1.message.create(request)
        return response.success()

    except Exception as e:
        print(f"❌ 发送卡片异常: {e}")
        return False


def send_button_card(client, chat_id: str, title: str, content: str, options: list, session_id: str) -> str:
    """发送带按钮的选项卡片，返回消息 ID"""
    try:
        elements = [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": content}
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": opt["label"]},
                        "type": "primary" if i == 0 else "default",
                        "value": {
                            "action": "select_option",
                            "label": opt["label"],
                            "index": opt.get("index", i + 1),
                            "session_id": session_id,
                            "chat_id": chat_id
                        }
                    }
                    for i, opt in enumerate(options)
                ]
            }
        ]

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": elements
        }

        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("interactive")
                .content(json.dumps(card, ensure_ascii=False))
                .build()) \
            .build()

        response = client.im.v1.message.create(request)
        if response.success() and response.data:
            return response.data.message_id
        return None

    except Exception as e:
        print(f"❌ 发送按钮卡片异常: {e}")
        return None


def send_permission_card(client, chat_id: str, tool_name: str, tool_input: dict) -> str:
    """发送工具权限确认卡片（允许 / 总是允许 / 拒绝）"""
    try:
        import json as _json
        input_summary = _json.dumps(tool_input, ensure_ascii=False, indent=2)[:300]
        content = f"**工具**: `{tool_name}`\n\n**参数**:\n```\n{input_summary}\n```"

        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": content}},
            {"tag": "hr"},
            {"tag": "action", "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "✅ 允许"},
                    "type": "primary",
                    "value": {"action": "permission", "decision": "allow", "chat_id": chat_id}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔁 总是允许"},
                    "type": "default",
                    "value": {"action": "permission", "decision": "allow_always", "chat_id": chat_id}
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                    "type": "danger",
                    "value": {"action": "permission", "decision": "deny", "chat_id": chat_id}
                }
            ]}
        ]

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "🔐 需要授权"},
                "template": "orange"
            },
            "elements": elements
        }

        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("interactive")
                .content(_json.dumps(card, ensure_ascii=False))
                .build()) \
            .build()

        response = client.im.v1.message.create(request)
        if response.success() and response.data:
            return response.data.message_id
        return None

    except Exception as e:
        print(f"❌ 发送权限卡片异常: {e}")
        return None
