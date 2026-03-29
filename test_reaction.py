"""
测试表情回应功能
"""
import os
import sys
import time
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from reaction_indicator import ReactionIndicator, StatusEmoji

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def main():
    """测试表情回应"""
    if len(sys.argv) < 3:
        print("用法: python3 test_reaction.py <chat_id> <message_id>")
        print("示例: python3 test_reaction.py oc_xxx om_xxx")
        return

    chat_id = sys.argv[1]
    message_id = sys.argv[2]

    # 创建飞书客户端
    client = lark.Client.builder() \
        .app_id(os.getenv("FEISHU_APP_ID")) \
        .app_secret(os.getenv("FEISHU_APP_SECRET")) \
        .build()

    # 创建表情回应指示器
    indicator = ReactionIndicator(client)

    print("🧪 开始测试表情回应功能")
    print(f"📝 Chat ID: {chat_id}")
    print(f"💬 Message ID: {message_id}")
    print()

    # 测试序列
    tests = [
        ("思考中", lambda: indicator.show_thinking(message_id)),
        ("读取文件", lambda: indicator.show_tool_execution(message_id, "Read")),
        ("写入文件", lambda: indicator.show_tool_execution(message_id, "Write")),
        ("搜索", lambda: indicator.show_tool_execution(message_id, "Grep")),
        ("执行命令", lambda: indicator.show_tool_execution(message_id, "Bash")),
        ("等待用户", lambda: indicator.show_waiting(message_id)),
        ("计划模式", lambda: indicator.show_plan_mode(message_id)),
        ("完成", lambda: indicator.show_completed(message_id)),
    ]

    for name, action in tests:
        print(f"⏳ 测试: {name}")
        success = action()
        if success:
            print(f"✅ {name} - 成功")
        else:
            print(f"❌ {name} - 失败")
        time.sleep(2)  # 等待 2 秒，让用户看到效果

    # 清除表情
    print()
    print("🧹 清除表情")
    indicator.clear_status()
    print("✅ 测试完成")

if __name__ == "__main__":
    main()
