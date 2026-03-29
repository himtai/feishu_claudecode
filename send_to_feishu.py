#!/usr/bin/env python3
"""
飞书图片发送脚本
供 Agent 通过 Bash 工具调用
"""
import sys
import os
from dotenv import load_dotenv
import lark_oapi as lark
from file_uploader import FeishuFileUploader

# 加载环境变量
load_dotenv()

if len(sys.argv) < 3:
    print("用法: python3 send_to_feishu.py <chat_id> <image_path>")
    sys.exit(1)

chat_id = sys.argv[1]
image_path = sys.argv[2]

# 检查文件是否存在
if not os.path.exists(image_path):
    print(f"错误: 文件不存在 - {image_path}")
    sys.exit(1)

# 创建飞书客户端
client = lark.Client.builder() \
    .app_id(os.getenv("FEISHU_APP_ID")) \
    .app_secret(os.getenv("FEISHU_APP_SECRET")) \
    .build()

# 上传并发送
uploader = FeishuFileUploader(client)

# 判断是图片还是文件
if image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
    success = uploader.send_image(chat_id, image_path)
    file_type = "图片"
else:
    success = uploader.send_file(chat_id, image_path)
    file_type = "文件"

if success:
    print(f"✅ {file_type}已发送: {image_path}")
else:
    print(f"❌ {file_type}发送失败")
    sys.exit(1)
