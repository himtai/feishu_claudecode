#!/usr/bin/env python3
"""
发送图片到飞书的简单脚本
"""
import os
import sys
import json
from dotenv import load_dotenv
import lark_oapi as lark
from lark_oapi.api.im.v1 import *

load_dotenv()

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

def send_image_to_chat(chat_id: str, image_path: str):
    """发送图片到飞书聊天"""
    try:
        # 创建客户端
        client = lark.Client.builder() \
            .app_id(FEISHU_APP_ID) \
            .app_secret(FEISHU_APP_SECRET) \
            .build()

        # 上传图片
        with open(image_path, 'rb') as f:
            request = CreateImageRequest.builder() \
                .request_body(CreateImageRequestBody.builder()
                    .image_type("message")
                    .image(f)
                    .build()) \
                .build()

            response = client.im.v1.image.create(request)

        if not response.success():
            print(f"上传图片失败: {response.msg}")
            return False

        image_key = response.data.image_key
        print(f"图片上传成功: {image_key}")

        # 发送消息
        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("image")
                .content(json.dumps({"image_key": image_key}))
                .build()) \
            .build()

        response = client.im.v1.message.create(request)

        if response.success():
            print(f"✓ 图片发送成功！")
            return True
        else:
            print(f"发送消息失败: {response.msg}")
            return False

    except Exception as e:
        print(f"发送图片失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python send_image.py <chat_id> <image_path>")
        sys.exit(1)

    chat_id = sys.argv[1]
    image_path = sys.argv[2]

    send_image_to_chat(chat_id, image_path)
