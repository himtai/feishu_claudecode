import os
import sys
import asyncio
import json
import time
from dotenv import load_dotenv
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from claude_agent_sdk import query, ClaudeAgentOptions
from session_manager import session_manager
from status_notifier import StatusNotifier
from file_uploader import FeishuFileUploader

load_dotenv()

# 解决嵌套问题
if 'CLAUDECODE' in os.environ:
    del os.environ['CLAUDECODE']

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
WORK_DIR = os.getcwd()

client = lark.Client.builder() \
    .app_id(FEISHU_APP_ID) \
    .app_secret(FEISHU_APP_SECRET) \
    .build()

user_sessions = {}


def send_message(chat_id: str, text: str):
    """发送消息"""
    try:
        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()) \
            .build()
        client.im.v1.message.create(request)
    except Exception as e:
        print(f"发送消息失败: {e}")


def send_card(chat_id: str, title: str, content: str, color: str = "blue"):
    """发送卡片"""
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
        client.im.v1.message.create(request)
    except Exception as e:
        print(f"发送卡片失败: {e}")


def send_interactive_question(chat_id: str, question_data: dict):
    """发送交互式问题卡片（带按钮）"""
    try:
        questions = question_data.get('questions', [])
        if not questions:
            send_message(chat_id, "需要你的选择，但问题格式错误")
            return

        # 只处理第一个问题（简化版）
        question = questions[0]
        question_text = question.get('question', '请选择')
        options = question.get('options', [])

        # 构建卡片元素
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{question_text}**"
                }
            },
            {"tag": "hr"}
        ]

        # 添加选项按钮
        actions = []
        for idx, option in enumerate(options):
            label = option.get('label', f'选项{idx+1}')
            description = option.get('description', '')

            # 添加选项说明
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{label}**\n{description}"
                }
            })

            # 添加按钮
            actions.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": label
                },
                "value": json.dumps({
                    "question": question_text,
                    "answer": label,
                    "option_index": idx
                }),
                "type": "primary" if idx == 0 else "default"
            })

        elements.append({
            "tag": "action",
            "actions": actions
        })

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "🤔 需要你的选择"},
                "template": "blue"
            },
            "elements": elements
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
        print(f"发送交互式卡片: {response.success()}")

    except Exception as e:
        print(f"发送交互式卡片失败: {e}")
        import traceback
        traceback.print_exc()


async def execute_claude(user_id: str, chat_id: str, prompt: str, resume_session_id: str = None, user_answer: dict = None, previous_context: str = None):
    """执行 Claude Agent"""
    try:
        print(f"执行任务: {prompt}")

        # 创建状态通知器
        notifier = StatusNotifier(client, chat_id)

        # 发送初始状态（无论是否恢复会话）
        if not resume_session_id and not previous_context:
            send_card(chat_id, "🤖 开始执行", f"**任务**: {prompt}", "blue")

        # 始终显示 thinking 状态
        notifier.notify_thinking()

        # 添加系统提示，鼓励 Claude 在需要时询问用户
        system_prompt = """
你正在飞书机器人环境中运行，可以与用户交互。

重要规则：
- 当用户的请求中包含"先问我"、"询问我"、"让我选择"等词语时，在回复中列出清晰的编号选项
- 当遇到多个可行方案且用户没有明确指定时，列出编号选项让用户选择
- 用户会通过回复选项编号来选择
- 如果用户已经做出选择，请根据选择继续执行任务
"""

        # 构造完整的 prompt
        full_prompt = prompt

        # 如果有之前的上下文（用户做了选择），添加到 prompt 中
        if previous_context:
            full_prompt = f"{previous_context}\n\n{prompt}"
            print(f"包含之前的上下文")

        # 如果用户明确要求询问，在 prompt 中强调
        if any(keyword in prompt for keyword in ['先问', '询问', '让我选', '问我']):
            full_prompt = f"{full_prompt}\n\n重要：请在回复中列出清晰的编号选项（如 1. 选项A  2. 选项B），让用户选择。"

        options = ClaudeAgentOptions(
            cwd=WORK_DIR,
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion"],
            permission_mode="plan",
            system_prompt=system_prompt,
            continue_conversation=True,  # 关键：继续对话而不是开始新会话
            resume=resume_session_id  # 恢复会话
        )

        result_text = ""
        tool_calls = []
        got_response = False
        current_session_id = resume_session_id

        async for message in query(prompt=full_prompt, options=options):
            got_response = True

            # 获取消息类型
            msg_type = type(message).__name__

            # 处理 SystemMessage - 获取 session_id
            if msg_type == 'SystemMessage':
                if hasattr(message, 'data') and isinstance(message.data, dict):
                    if message.data.get('subtype') == 'init':
                        current_session_id = message.data.get('session_id')
                        print(f"Session ID: {current_session_id}")
                        print(f"Resume session ID: {resume_session_id}")
                        print(f"Continue conversation: True")
                continue

            # 检测 AskUserQuestion 工具调用
            if msg_type == 'ToolUseMessage':
                if hasattr(message, 'tool_name') and message.tool_name == 'AskUserQuestion':
                    print("检测到 AskUserQuestion")

                    # 提取问题数据
                    tool_input = message.tool_input if hasattr(message, 'tool_input') else {}

                    # 通知等待用户回答
                    questions = tool_input.get('questions', [])
                    question_text = questions[0].get('question', '请选择') if questions else '请选择'
                    notifier.notify_waiting_user(question_text)

                    # 保存会话状态
                    session_manager.save_pending_question(
                        chat_id=chat_id,
                        user_id=user_id,
                        session_id=current_session_id,
                        question_data=tool_input,
                        prompt=prompt
                    )

                    # 发送交互式卡片到飞书
                    send_interactive_question(chat_id, tool_input)

                    print("等待用户选择...")
                    return  # 暂停执行，等待用户回答

                # 其他工具调用 - 发送状态通知
                if hasattr(message, 'tool_name'):
                    tool_name = message.tool_name
                    tool_input = message.tool_input if hasattr(message, 'tool_input') else {}
                    tool_calls.append(f"🔧 {tool_name}")
                    print(f"  工具: {tool_name}")

                    # 发送工具执行状态
                    notifier.notify_tool_use(tool_name, tool_input)

            # 处理 AssistantMessage - 提取文本内容
            elif msg_type == 'AssistantMessage':
                if hasattr(message, 'content') and message.content:
                    for block in message.content:
                        block_type = type(block).__name__
                        if block_type == 'TextBlock' and hasattr(block, 'text'):
                            result_text += block.text

            # 处理 ResultMessage - 最终结果
            elif msg_type == 'ResultMessage':
                if hasattr(message, 'result') and message.result:
                    result_text = message.result
                if hasattr(message, 'usage') and message.usage:
                    input_tokens = message.usage.get('input_tokens', 0)
                    output_tokens = message.usage.get('output_tokens', 0)
                    notifier.update_token_usage(input_tokens, output_tokens)

        # 如果没有收到响应，发送默认消息
        if not got_response or not result_text:
            result_text = "收到你的消息了！我是 Claude Agent，可以帮你执行各种任务。"

        # 发送结果
        print(f"准备发送结果，长度: {len(result_text)}")

        # 检测结果中是否包含选项列表（即使没有调用 AskUserQuestion）
        if result_text and not resume_session_id:
            # 检测是否包含编号选项（如 "1. xxx" 或 "1) xxx"）
            import re
            option_pattern = r'^\s*(\d+)[.、)]\s*(.+)$'
            lines = result_text.split('\n')
            detected_options = []

            for line in lines:
                match = re.match(option_pattern, line.strip())
                if match:
                    option_num = match.group(1)
                    option_text = match.group(2).strip()
                    detected_options.append({
                        'number': option_num,
                        'label': option_text,
                        'description': ''
                    })

            # 如果检测到至少2个选项，保存为待回答的问题
            if len(detected_options) >= 2:
                print(f"检测到 {len(detected_options)} 个选项，保存会话等待用户选择")

                # 构造问题数据
                question_data = {
                    'questions': [{
                        'question': '请选择',
                        'options': detected_options,
                        'multiSelect': False
                    }]
                }

                # 保存会话，包含之前的对话内容作为上下文
                session_manager.save_pending_question(
                    chat_id=chat_id,
                    user_id=user_id,
                    session_id=current_session_id,
                    question_data=question_data,
                    prompt=prompt,
                    previous_response=result_text  # 保存 Claude 的回复作为上下文
                )

                # 先发 Claude 的回复文字，再发带按钮的交互卡片
                send_card(chat_id, "💬 Claude", result_text, "blue")
                send_interactive_question(chat_id, question_data)
                notifier.notify_completed()
                return  # 不再走下面的普通结果发送

        # 如果是恢复会话，也要更新 session_id（保持会话活跃）
        elif resume_session_id and current_session_id:
            # 更新会话状态，保持活跃
            existing_session = session_manager.get_pending_question(chat_id)
            if existing_session:
                existing_session['session_id'] = current_session_id
                existing_session['status'] = 'active'
                existing_session['timestamp'] = time.time()
                session_file = session_manager.storage_dir / f"{chat_id}.json"
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_session, f, ensure_ascii=False, indent=2)

        if result_text:
            if len(result_text) > 2000:
                chunks = [result_text[i:i+2000] for i in range(0, len(result_text), 2000)]
                for i, chunk in enumerate(chunks):
                    print(f"发送分段 {i+1}/{len(chunks)}")
                    send_message(chat_id, f"[{i+1}/{len(chunks)}]\n{chunk}")
                    await asyncio.sleep(0.5)
            else:
                print(f"发送卡片消息")
                send_card(
                    chat_id,
                    "✅ 完成",
                    result_text + (f"\n\n**工具**: {', '.join(tool_calls)}" if tool_calls else ""),
                    "green"
                )
        else:
            print("发送默认完成消息")
            send_message(chat_id, "✅ 任务完成")

        # 通知完成
        notifier.notify_completed()

        # 保存对话历史（无论是否有 session_id）
        if current_session_id:
            session_manager.save_conversation(
                chat_id=chat_id,
                user_id=user_id,
                session_id=current_session_id,
                prompt=prompt,
                response=result_text[:500] if result_text else ""  # 只保存前500字符
            )
        else:
            # 即使没有 session_id，也保存对话
            print("警告：没有 session_id，但仍保存对话历史")
            session_manager.save_conversation(
                chat_id=chat_id,
                user_id=user_id,
                session_id="unknown",
                prompt=prompt,
                response=result_text[:500] if result_text else ""
            )

        print("任务完成")

    except Exception as e:
        print(f"执行出错: {e}")
        # 通知错误
        try:
            notifier = StatusNotifier(client, chat_id)
            notifier.notify_error(str(e))
        except:
            pass
        send_card(chat_id, "❌ 错误", str(e), "red")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python3 execute_claude.py <user_id> <chat_id> <prompt> [resume_session_id] [answer_json] [previous_context]")
        sys.exit(1)

    user_id = sys.argv[1]
    chat_id = sys.argv[2]
    prompt = sys.argv[3]
    resume_session_id = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
    user_answer = json.loads(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] else None
    previous_context = sys.argv[6] if len(sys.argv) > 6 else None

    # 设置超时时间（5分钟）
    try:
        asyncio.run(asyncio.wait_for(
            execute_claude(user_id, chat_id, prompt, resume_session_id, user_answer, previous_context),
            timeout=300  # 5分钟超时
        ))
    except asyncio.TimeoutError:
        print("执行超时")
        # 发送超时消息到飞书
        load_dotenv()
        client = lark.Client.builder() \
            .app_id(os.getenv("FEISHU_APP_ID")) \
            .app_secret(os.getenv("FEISHU_APP_SECRET")) \
            .build()
        send_card(chat_id, "⏱️ 超时", "任务执行超过5分钟，已自动停止", "red")
