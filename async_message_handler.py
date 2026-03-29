"""
异步消息处理器
使用持久化 Agent 处理飞书消息
支持消息队列
"""
import asyncio
import os
from claude_agent_sdk import ClaudeAgentOptions
from status_notifier import StatusNotifier


async def process_message_with_agent(
    agent_session,
    chat_id: str,
    user_id: str,
    user_message: str,
    client,
    work_dir: str,
    user_message_id: str = None  # 新增：用户消息 ID（用于表情回应）
):
    """使用持久化 Agent 处理消息"""
    from feishu_client import send_card, send_message, set_typing_status

    # 检查是否正在处理
    if agent_session.is_processing:
        # 添加到队列
        agent_session.queue_size += 1
        queue_position = agent_session.queue_size

        send_card(
            client,
            chat_id,
            "⏳ 消息已排队",
            f"当前有任务正在执行中\n\n**排队位置**: 第 {queue_position} 位\n**提示**: 发送 /cancel 可取消排队",
            "orange"
        )

        # 等待前面的任务完成
        while agent_session.is_processing:
            await asyncio.sleep(1)
            # 检查是否取消队列
            if agent_session.cancel_queue:
                agent_session.queue_size -= 1
                if agent_session.queue_size <= 0:
                    agent_session.cancel_queue = False
                send_message(client, chat_id, "✅ 已取消排队")
                return

        agent_session.queue_size -= 1
        send_message(client, chat_id, "✅ 轮到你了，开始处理...")

    try:
        agent_session.is_processing = True

        # 设置输入状态为"正在输入"（暂时禁用，API 返回 404）
        # set_typing_status(client, chat_id, user_id, "typing")

        # 创建状态通知器（传入用户消息 ID 用于表情回应）
        notifier = StatusNotifier(client, chat_id, user_message_id)
        agent_session.current_notifier = notifier  # 保存引用，以便 /new 时停止
        notifier.notify_thinking()

        print(f"  准备发送消息到 Agent")
        print(f"  消息内容: {user_message[:100]}...")
        print(f"  消息长度: {len(user_message)} 字符")

        # 在消息中添加系统提示，告诉 Agent 如何发送图片
        system_hint = f"\n\n[系统提示：如需发送图片或文件给用户，使用命令: python3 send_to_feishu.py {chat_id} <文件路径>]"
        user_message_with_hint = user_message + system_hint

        # 定义状态回调函数
        def status_callback(event_type, data):
            """处理 Agent 状态事件"""
            print(f"[DEBUG] status_callback 被调用: event_type={event_type}")
            if event_type == 'thinking_text':
                # 流式显示思考内容
                text = data.get('text', '')
                print(f"[DEBUG] 思考内容: {text[:50]}...")
                notifier.notify_thinking_text(text)
            elif event_type == 'tool_use':
                tool_name = data.get('tool_name', '')
                tool_input = data.get('tool_input', {})
                print(f"[DEBUG] 调用 notifier.notify_tool_use: {tool_name}")
                notifier.notify_tool_use(tool_name, tool_input)
            elif event_type == 'token_usage':
                input_tokens = data.get('input_tokens', 0)
                output_tokens = data.get('output_tokens', 0)
                notifier.update_token_usage(input_tokens, output_tokens)

        # 读取记忆文件作为 system_prompt
        memory_file = os.path.join(os.path.dirname(work_dir), "CLAUDE.md")
        system_prompt = None
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            print(f"  已加载记忆文件: {memory_file} ({len(system_prompt)} 字符)")

        # 配置选项
        options = ClaudeAgentOptions(
            cwd=work_dir,
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion"],
            permission_mode="default",  # default 模式：自动执行
            continue_conversation=True,
            resume=agent_session.session_id,  # 使用持久化的 session_id
            system_prompt=system_prompt,
        )

        print(f"  发送消息到 Agent，session_id: {agent_session.session_id}")
        print(f"  对话历史: {len(agent_session.conversation_history)} 条")

        # 发送消息（带状态回调）
        print(f"  开始调用 agent_session.send_message")
        try:
            result = await agent_session.send_message(user_message_with_hint, options, status_callback, feishu_client=client)
        except Exception as e:
            if "signature" in str(e):
                print(f"[FIX] 检测到 signature 错误，重置会话并重试")
                agent_session.session_id = None
                agent_session.conversation_history = []
                # 重新构建不带 resume 的 options
                retry_options = ClaudeAgentOptions(
                    cwd=work_dir,
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion"],
                    permission_mode="default",
                    continue_conversation=False,
                    betas=['context-1m-2025-08-07'],
                    system_prompt=system_prompt,
                )
                result = await agent_session.send_message(user_message_with_hint, retry_options, status_callback, feishu_client=client)
            else:
                raise
        print(f"  send_message 返回: {result}")

        result_text = result['result']
        tool_calls = result['tool_calls']
        print(f"  结果文本长度: {len(result_text) if result_text else 0}")
        print(f"  工具调用: {tool_calls}")

        # 静默丢弃旧任务通知，不发给用户
        if result_text and result_text.strip().startswith('旧任务通知'):
            print(f"[SKIP] 检测到旧任务通知，静默丢弃，不发给用户")
            return True

        # 发送结果
        print(f"  准备发送结果，result_text 是否为空: {not result_text}")
        if result_text:
            print(f"  result_text 长度: {len(result_text)}")

            # 检测是否包含编号选项，如有则发按钮卡片
            import re
            option_pattern = re.compile(r'^\s*(?:\*{1,2})?(\d+)[.)、](?:\*{1,2})?\s*(.+)$', re.MULTILINE)
            option_matches = option_pattern.findall(result_text)
            print(f"  [DEBUG] result_text 前200字: {repr(result_text[:200])}")
            print(f"  [DEBUG] option_matches: {option_matches}")
            if len(option_matches) >= 2:
                print(f"  检测到 {len(option_matches)} 个编号选项，发送按钮卡片")
                from feishu_client import send_button_card
                options_list = [
                    {"label": m[1].strip(), "index": int(m[0])}
                    for m in option_matches
                ]
                send_button_card(client, chat_id, "请选择", result_text, options_list, agent_session.session_id or "")
                notifier.notify_completed()
                return True

            # 备用检测：加粗标题单独成行（如 **Python**），作为选项按钮
            bold_header_pattern = re.compile(r'^\*\*([^*\n]+)\*\*\s*$', re.MULTILINE)
            bold_matches = [m for m in bold_header_pattern.findall(result_text) if not m.strip().endswith(('：', ':'))]
            print(f"  [DEBUG] bold_matches: {bold_matches}")
            if len(bold_matches) >= 2:
                print(f"  检测到 {len(bold_matches)} 个加粗标题选项，发送按钮卡片")
                from feishu_client import send_button_card
                options_list = [
                    {"label": m.strip(), "index": i + 1}
                    for i, m in enumerate(bold_matches)
                ]
                send_button_card(client, chat_id, "请选择", result_text, options_list, agent_session.session_id or "")
                notifier.notify_completed()
                return True

            # 检测是否需要发送图片
            import re
            image_pattern = r'(/[^\s]+\.(?:png|jpg|jpeg|gif|webp))'
            image_matches = re.findall(image_pattern, result_text)

            if image_matches:
                print(f"  检测到图片路径: {image_matches}")
                notifier.notify_tool_use("send_image", {"paths": image_matches})
                from file_uploader import FeishuFileUploader
                uploader = FeishuFileUploader(client)
                for img_path in image_matches:
                    if os.path.exists(img_path):
                        print(f"  发送图片: {img_path}")
                        uploader.send_image(chat_id, img_path)
                notifier.notify_completed()
                return True

            if len(result_text) > 2000:
                print(f"  分段发送")
                chunks = [result_text[i:i+2000] for i in range(0, len(result_text), 2000)]
                for i, chunk in enumerate(chunks):
                    send_message(client, chat_id, f"[{i+1}/{len(chunks)}]\n{chunk}")
                    await asyncio.sleep(0.5)
            else:
                print(f"  发送卡片")
                send_card(
                    client,
                    chat_id,
                    "✅ 完成",
                    result_text + (f"\n\n**工具**: {', '.join(tool_calls)}" if tool_calls else ""),
                    "green"
                )
                print(f"  卡片已发送")

        # 通知完成
        print(f"  通知完成")
        notifier.notify_completed()

        # 清除输入状态（暂时禁用，API 返回 404）
        # set_typing_status(client, chat_id, user_id, status="")

        # 保存到项目记忆，让终端能看到
        try:
            memory_file = os.path.expanduser("~/.claude/projects/-mnt-f-claude-code/memory/feishu_recent.md")
            os.makedirs(os.path.dirname(memory_file), exist_ok=True)

            with open(memory_file, 'a', encoding='utf-8') as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n## 飞书对话 [{timestamp}]\n")
                f.write(f"**用户**: {user_message[:200]}\n")
                if result_text:
                    f.write(f"**助手**: {result_text[:200]}\n")
                f.write("\n---\n")
        except Exception as e:
            print(f"保存记忆失败: {e}")

        return True

    except Exception as e:
        print(f"处理消息失败: {e}")
        import traceback
        traceback.print_exc()

        send_card(client, chat_id, "❌ 错误", str(e), "red")

        # 清除输入状态（暂时禁用，API 返回 404）
        # set_typing_status(client, chat_id, user_id, status="")

        return False

    finally:
        agent_session.is_processing = False

