"""
飞书 + Claude Agent（长连接模式）
使用 WebSocket 长连接接收飞书消息
无需配置公网 IP 和 webhook
使用持久化 Agent 保持上下文连贯性
"""
import os
import asyncio
import threading
from datetime import datetime
from dotenv import load_dotenv
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.event.callback.model.p2_card_action_trigger import (
    P2CardActionTrigger, P2CardActionTriggerResponse, CallBackToast
)
from claude_agent_sdk import ClaudeAgentOptions
import json
from session_manager import session_manager
from file_downloader import FeishuFileDownloader
from persistent_agent import get_agent_manager
from status_notifier import StatusNotifier
from feishu_client import send_message, send_card

load_dotenv()

# 解决嵌套 Claude Code 会话问题
if 'CLAUDECODE' in os.environ:
    del os.environ['CLAUDECODE']

# 配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
WORK_DIR = os.path.join(os.getcwd(), "workspace")  # 使用 workspace 而不是 feishu_workspace

# 确保工作目录存在
if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR, exist_ok=True)

# 飞书客户端
client = lark.Client.builder() \
    .app_id(FEISHU_APP_ID) \
    .app_secret(FEISHU_APP_SECRET) \
    .build()

# 文件下载器
file_downloader = FeishuFileDownloader(client, download_dir="./downloads")

# 持久化 Agent 管理器
agent_manager = get_agent_manager(WORK_DIR)

# 正在处理的消息（避免重复处理）
processing_messages = set()
processing_messages_lock = threading.Lock()


def mark_message_done(message_id: str):
    """标记消息处理完成"""
    with processing_messages_lock:
        processing_messages.discard(message_id)


def handle_command(client, chat_id: str, command: str):
    """处理特殊命令"""
    if command == '/help':
        send_card(
            client,
            chat_id,
            "📖 帮助",
            "直接发送指令，例如：\n- 读取 README.md\n- 重构 main.py\n- 运行测试\n\n**命令**:\n- `/help` - 显示此帮助\n- `/status` - 查看当前会话状态\n- `/new` - 清除上下文，开始新对话\n- `/cancel` - 取消排队中的消息\n- `/esc` - 打断当前正在执行的任务",
            "blue"
        )
    elif command == '/status':
        # 获取当前会话信息
        agent_session = agent_manager.agents.get(chat_id)
        if agent_session:
            history_count = len(agent_session.conversation_history)
            processing_status = "🟢 空闲" if not agent_session.is_processing else "🔴 处理中"
            queue_info = f"**排队消息**: {agent_session.queue_size} 条" if agent_session.queue_size > 0 else ""
            session_info = f"**会话 ID**: {agent_session.session_id}\n**对话历史**: {history_count} 条消息\n**状态**: {processing_status}\n{queue_info}"
        else:
            session_info = "**状态**: 无活跃会话"

        send_card(
            client,
            chat_id,
            "📊 状态",
            f"**工作目录**: {WORK_DIR}\n**活跃会话**: {len(agent_manager.agents)}\n**连接模式**: WebSocket 长连接\n**上下文窗口**: 1M tokens\n\n{session_info}",
            "grey"
        )
    elif command == '/new':
        agent_manager.clear_agent(chat_id)
        send_card(client, chat_id, "🆕 新对话", "上下文已清除，可以开始新的对话了。", "green")
    elif command == '/cancel':
        agent_session = agent_manager.agents.get(chat_id)
        if agent_session and agent_session.queue_size > 0:
            agent_session.cancel_queue = True
            send_card(client, chat_id, "🚫 取消排队", f"已标记取消，将在当前任务完成后清空排队的 {agent_session.queue_size} 条消息。", "orange")
        else:
            send_message(client, chat_id, "当前没有排队中的消息。")
    elif command == '/esc':
        agent_session = agent_manager.agents.get(chat_id)
        if agent_session and agent_session.current_task and not agent_session.current_task.done():
            agent_session.current_loop.call_soon_threadsafe(agent_session.current_task.cancel)
            if agent_session.current_notifier is not None:
                agent_session.current_notifier._stop_update_timer()
                agent_session.current_notifier = None
            send_card(client, chat_id, "⏹ 已打断", "任务已立即取消。", "red")
        else:
            send_message(client, chat_id, "当前没有正在执行的任务。")
    else:
        send_message(client, chat_id, f"未知命令: {command}\n发送 /help 查看可用命令。")


async def process_message(event_data):
    """处理消息事件（已废弃，使用 MessageHandler 代替）"""
    pass


def handle_message_event(data: P2ImMessageReceiveV1):
    """处理接收消息事件"""
    try:
        message = data.event.message
        sender = data.event.sender

        message_id = message.message_id
        message_type = message.message_type
        chat_id = message.chat_id

        # 避免重复处理
        with processing_messages_lock:
            if message_id in processing_messages:
                return
            processing_messages.add(message_id)

        # 获取用户ID
        user_id = None
        if hasattr(sender, 'sender_id'):
            if hasattr(sender.sender_id, 'user_id'):
                user_id = sender.sender_id.user_id
            elif hasattr(sender.sender_id, 'open_id'):
                user_id = sender.sender_id.open_id
            elif hasattr(sender.sender_id, 'union_id'):
                user_id = sender.sender_id.union_id

        if not user_id:
            user_id = chat_id

        # 处理不同类型的消息
        user_message = ""

        if message_type == 'text':
            # 文本消息
            content = json.loads(message.content)
            user_message = content.get('text', '').strip()

        elif message_type == 'image':
            # 图片消息
            try:
                content = json.loads(message.content)
                image_key = content.get('image_key', '')

                send_message(client, chat_id, "📥 正在下载图片...")

                # 下载图片
                file_path = file_downloader.get_message_resource(
                    message_id, image_key, 'image'
                )

                # 简单确认收到，不强制分析
                user_message = f"[用户发送了图片: {file_path}]"

                # 直接回复确认，不需要 Agent 处理
                send_message(client, chat_id, f"✅ 图片已接收并保存")
                mark_message_done(message_id)
                return

            except Exception as e:
                send_message(client, chat_id, f"❌ 下载图片失败: {e}")
                mark_message_done(message_id)
                return

        elif message_type == 'file':
            # 文件消息
            try:
                content = json.loads(message.content)
                file_key = content.get('file_key', '')
                file_name = content.get('file_name', 'unknown')

                send_message(client, chat_id, f"📥 正在下载文件: {file_name}...")

                # 下载文件
                file_path = file_downloader.get_message_resource(
                    message_id, file_key, 'file'
                )

                # 重命名为原始文件名
                import shutil
                new_path = os.path.join(os.path.dirname(file_path), file_name)
                shutil.move(file_path, new_path)
                file_path = new_path

                # 直接回复确认，不需要 Agent 处理
                send_message(client, chat_id, f"✅ 文件已接收: {file_name}")
                mark_message_done(message_id)
                return

            except Exception as e:
                send_message(client, chat_id, f"❌ 下载文件失败: {e}")
                mark_message_done(message_id)
                return

        elif message_type == 'post':
            # 富文本消息（图片+文字组合）
            try:
                content = json.loads(message.content)

                # 调试：打印消息结构
                print(f"DEBUG: post 消息内容: {json.dumps(content, ensure_ascii=False, indent=2)}")

                # 提取文本内容
                text_parts = []
                image_keys = []

                # 解析 post 消息结构
                post_content = content

                # 如果有 content 字段
                if 'content' in content:
                    post_content = content['content']
                    if isinstance(post_content, str):
                        post_content = json.loads(post_content)

                print(f"DEBUG: post_content 类型: {type(post_content)}")
                print(f"DEBUG: post_content: {post_content}")

                # 递归解析内容
                def parse_post_elements(data):
                    """递归解析 post 消息元素"""
                    if isinstance(data, dict):
                        # 文本元素
                        if data.get('tag') == 'text':
                            text_parts.append(data.get('text', ''))
                        # 图片元素
                        elif data.get('tag') == 'img':
                            image_keys.append(data.get('image_key', ''))
                        # 递归处理子元素
                        for value in data.values():
                            parse_post_elements(value)
                    elif isinstance(data, list):
                        for item in data:
                            parse_post_elements(item)

                parse_post_elements(post_content)

                # 下载所有图片
                downloaded_images = []
                for image_key in image_keys:
                    try:
                        send_message(client, chat_id, f"📥 正在下载图片...")
                        file_path = file_downloader.get_message_resource(
                            message_id, image_key, 'image'
                        )
                        downloaded_images.append(file_path)
                    except Exception as e:
                        print(f"下载图片失败: {e}")

                # 构建消息
                user_text = ' '.join(text_parts).strip()
                if downloaded_images:
                    images_info = '\n'.join([f"- {path}" for path in downloaded_images])
                    user_message = f"{user_text}\n\n[用户发送了 {len(downloaded_images)} 张图片，已保存到:]\n{images_info}"
                else:
                    user_message = user_text if user_text else "[空消息]"

            except Exception as e:
                print(f"解析 post 消息失败: {e}")
                import traceback
                traceback.print_exc()
                send_message(client, chat_id, f"❌ 处理富文本消息失败: {e}")
                mark_message_done(message_id)
                return

        else:
            # 不支持的消息类型
            send_message(client, chat_id, f"暂不支持 {message_type} 类型的消息")
            mark_message_done(message_id)
            return

        if not user_message:
            mark_message_done(message_id)
            return

        print(f"\n📨 [{datetime.now().strftime('%H:%M:%S')}] 收到消息: {user_message[:50]}...")
        print(f"   user_id: {user_id}, chat_id: {chat_id}")

        # 检查是否有等待回答的问题
        pending_session = session_manager.get_pending_question(chat_id)
        if pending_session and pending_session.get('status') == 'waiting':
            print("检测到有等待回答的问题，处理用户回复")

            # 尝试解析用户的选择（数字或选项文本）
            question_data = pending_session.get('question_data', {})
            questions = question_data.get('questions', [])

            if questions:
                question = questions[0]
                options = question.get('options', [])

                # 检查是否是数字选择
                selected_option = None
                if user_message.isdigit():
                    option_index = int(user_message) - 1
                    if 0 <= option_index < len(options):
                        selected_option = options[option_index]
                else:
                    # 尝试匹配选项标签
                    for opt in options:
                        if opt.get('label', '').lower() == user_message.lower():
                            selected_option = opt
                            break

                if selected_option:
                    # 保存答案（会话保持活跃）
                    answer = {
                        question.get('question'): selected_option.get('label')
                    }
                    session_manager.save_answer(chat_id, answer)

                    # 用户选择后，恢复会话并发送用户的选择
                    print(f"用户选择: {selected_option.get('label')}")
                    send_message(client, chat_id, f"✅ 已选择: {selected_option.get('label')}\n继续执行...")

                    # 获取保存的 session_id 和之前的上下文
                    session_id = pending_session.get('session_id', '')
                    previous_response = pending_session.get('previous_response', '')
                    original_prompt = pending_session.get('original_prompt', '')

                    # 用户的选择作为新的 prompt
                    user_choice_prompt = f"我选择：{selected_option.get('label')}"

                    # 构建完整的上下文
                    context = f"原始任务：{original_prompt}\n\n我的回复：\n{previous_response}"

                    # 启动子进程，恢复会话并发送用户选择
                    import subprocess
                    import os as os_module

                    env = os_module.environ.copy()
                    if 'CLAUDECODE' in env:
                        del env['CLAUDECODE']

                    cmd = [
                        'python3', f'{WORK_DIR}/execute_claude.py',
                        str(user_id), str(chat_id),
                        user_choice_prompt,  # 用户的选择
                        session_id,  # 恢复之前的会话
                        "",  # 不使用 user_answer
                        context   # 传递完整上下文
                    ]

                    # 保存子进程日志
                    log_file = open(f'{WORK_DIR}/.sessions/execute_{chat_id}_resume.log', 'w')
                    subprocess.Popen(cmd, cwd=WORK_DIR, env=env, stdout=log_file, stderr=log_file)

                    # 不清除会话，保持活跃
                    mark_message_done(message_id)
                    return
                else:
                    send_message(client, chat_id, f"❌ 无效的选择，请回复选项编号（1-{len(options)}）或选项名称")
                    mark_message_done(message_id)
                    return

        # 检查是否有活跃的会话（用户之前已经选择过，现在继续对话）
        active_session_id = session_manager.get_active_session(chat_id)
        if active_session_id:
            print(f"检测到活跃会话，继续对话: {active_session_id}")

        # 处理命令
        if user_message.startswith('/'):
            handle_command(client, chat_id, user_message)
            mark_message_done(message_id)
        else:
            # 确保参数不为空
            if not user_id or not chat_id:
                print(f"❌ 参数错误: user_id={user_id}, chat_id={chat_id}")
                mark_message_done(message_id)
                return

            # 使用持久化 Agent 处理消息
            print(f"   使用持久化 Agent 处理消息")

            # 获取或创建 Agent 会话
            agent_session = agent_manager.get_or_create_agent(chat_id, user_id)

            # 在后台线程中处理异步任务
            import threading

            def run_async_handler():
                from async_message_handler import process_message_with_agent

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def _run():
                    task = asyncio.ensure_future(
                        process_message_with_agent(
                            agent_session,
                            chat_id,
                            user_id,
                            user_message,
                            client,
                            WORK_DIR,
                            message_id
                        )
                    )
                    agent_session.current_task = task
                    agent_session.current_loop = loop
                    try:
                        await task
                    except asyncio.CancelledError:
                        print(f"[ESC] 任务已被取消: {chat_id}")

                try:
                    loop.run_until_complete(_run())
                finally:
                    agent_session.current_task = None
                    agent_session.current_loop = None
                    mark_message_done(message_id)
                    loop.close()

            thread = threading.Thread(target=run_async_handler, daemon=True)
            thread.start()

    except Exception as e:
        print(f"❌ 处理消息异常: {e}")
        import traceback
        traceback.print_exc()


def handle_card_action(data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
    """处理卡片按钮点击事件"""
    resp = P2CardActionTriggerResponse()
    toast = CallBackToast()

    try:
        action_value = data.event.action.value
        chat_id = data.event.context.open_chat_id
        user_id = data.event.operator.open_id

        action_type = action_value.get("action") if action_value else None
        print(f"[CardAction] chat_id={chat_id}, action={action_type}, value={action_value}")

        if action_type == "select_option":
            label = action_value.get("label", "")
            session_id = action_value.get("session_id", "")

            toast.type = "success"
            toast.content = f"已选择: {label}"

            # 在新线程中处理选择，不阻塞回调
            def run_selection():
                from async_message_handler import process_message_with_agent
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    agent_session = agent_manager.get_or_create_agent(chat_id, user_id)
                    loop.run_until_complete(
                        process_message_with_agent(
                            agent_session,
                            chat_id,
                            user_id,
                            f"我选择：{label}",
                            client,
                            WORK_DIR,
                            None
                        )
                    )
                finally:
                    loop.close()

            threading.Thread(target=run_selection, daemon=True).start()

        elif action_type == "permission":
            decision = action_value.get("decision", "deny")
            agent_session = agent_manager.agents.get(chat_id)
            if agent_session and agent_session.permission_queue and agent_session.permission_loop:
                asyncio.run_coroutine_threadsafe(
                    agent_session.permission_queue.put(decision),
                    agent_session.permission_loop
                )
                toast.type = "success"
                toast.content = "已确认"
            else:
                toast.type = "info"
                toast.content = "无等待中的权限请求"

    except Exception as e:
        print(f"❌ 处理卡片回调异常: {e}")
        import traceback
        traceback.print_exc()
        toast.type = "error"
        toast.content = "处理失败"

    resp.toast = toast
    return resp


def main():
    """主函数"""
    print("🚀 飞书 Claude Agent 启动（长连接模式）")
    print(f"📁 工作目录: {WORK_DIR}")
    print(f"🔌 使用 WebSocket 长连接")
    print(f"✅ 无需 ngrok，无需公网 IP，无需配置 webhook")
    print(f"✨ 支持交互式选择")
    print("\n正在建立连接...\n")

    try:
        # 启动 Agent 清理任务
        agent_manager.start_cleanup()
        print("✅ Agent 清理任务已启动")

        # 创建事件处理器（使用 builder 模式）
        event_handler = lark.EventDispatcherHandler.builder("", "") \
            .register_p2_im_message_receive_v1(handle_message_event) \
            .register_p2_card_action_trigger(handle_card_action) \
            .build()

        # 注意：飞书的卡片交互事件通过消息回调处理
        # 卡片按钮点击会作为特殊的消息事件返回

        # 创建 WebSocket 客户端
        ws_client = lark.ws.Client(
            FEISHU_APP_ID,
            FEISHU_APP_SECRET,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO
        )

        print("✅ 长连接已建立，等待消息中...\n")

        # 启动连接（阻塞运行）
        ws_client.start()

    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
