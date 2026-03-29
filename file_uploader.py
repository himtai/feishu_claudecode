"""
飞书文件上传工具
支持上传图片和文件到飞书
"""
import os
import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import *


class FeishuFileUploader:
    """飞书文件上传器"""

    def __init__(self, client: lark.Client):
        self.client = client

    def upload_image(self, image_path: str) -> str:
        """
        上传图片到飞书
        返回 image_key
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")

            # 使用文件对象而不是字节数据
            with open(image_path, 'rb') as f:
                # 构建请求
                request = CreateImageRequest.builder() \
                    .request_body(CreateImageRequestBody.builder()
                        .image_type("message")
                        .image(f)
                        .build()) \
                    .build()

                # 上传
                response = self.client.im.v1.image.create(request)

            if response.success():
                image_key = response.data.image_key
                print(f"图片上传成功: {image_key}")
                return image_key
            else:
                raise Exception(f"上传失败: {response.msg}")

        except Exception as e:
            print(f"上传图片失败: {e}")
            raise

    def upload_file(self, file_path: str) -> str:
        """
        上传文件到飞书
        返回 file_key
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            file_name = os.path.basename(file_path)

            # 根据扩展名选择正确的 file_type
            ext = os.path.splitext(file_name)[1].lower()
            file_type_map = {
                '.xlsx': 'xlsx',
                '.xls': 'xls',
                '.pdf': 'pdf',
                '.pptx': 'pptx',
                '.docx': 'docx',
            }
            file_type = file_type_map.get(ext, 'stream')

            # 构建请求（使用文件对象而非 bytes，与 upload_image 保持一致）
            with open(file_path, 'rb') as f:
                request = CreateFileRequest.builder() \
                    .request_body(CreateFileRequestBody.builder()
                        .file_type(file_type)
                        .file_name(file_name)
                        .file(f)
                        .build()) \
                    .build()

                # 上传
                response = self.client.im.v1.file.create(request)

            if response.success():
                file_key = response.data.file_key
                print(f"文件上传成功: {file_key}")
                return file_key
            else:
                raise Exception(f"上传失败: {response.msg}")

        except Exception as e:
            print(f"上传文件失败: {e}")
            raise

    def send_image(self, chat_id: str, image_path: str) -> bool:
        """上传并发送图片"""
        try:
            # 上传图片
            image_key = self.upload_image(image_path)

            # 发送消息
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("image")
                    .content(json.dumps({"image_key": image_key}))
                    .build()) \
                .build()

            response = self.client.im.v1.message.create(request)
            return response.success()

        except Exception as e:
            print(f"发送图片失败: {e}")
            return False

    def send_file(self, chat_id: str, file_path: str) -> bool:
        """上传并发送文件"""
        try:
            # 上传文件
            file_key = self.upload_file(file_path)

            # 发送消息
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("file")
                    .content(json.dumps({"file_key": file_key}))
                    .build()) \
                .build()

            response = self.client.im.v1.message.create(request)
            return response.success()

        except Exception as e:
            print(f"发送文件失败: {e}")
            return False
