"""
飞书文件下载工具
支持从飞书下载图片和文件
"""
import os
import json
import requests
import lark_oapi as lark
from lark_oapi.api.im.v1 import *


class FeishuFileDownloader:
    """飞书文件下载器"""

    def __init__(self, client: lark.Client, download_dir: str = "./downloads"):
        self.client = client
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)

    def download_image(self, image_key: str, filename: str = None) -> str:
        """
        下载图片
        返回本地文件路径
        """
        try:
            # 获取图片内容
            request = GetImageRequest.builder() \
                .image_key(image_key) \
                .build()

            response = self.client.im.v1.image.get(request)

            if not response.success():
                raise Exception(f"获取图片失败: {response.msg}")

            # 保存文件
            if not filename:
                filename = f"{image_key}.png"

            file_path = os.path.join(self.download_dir, filename)
            # 转换为绝对路径
            file_path = os.path.abspath(file_path)

            with open(file_path, 'wb') as f:
                f.write(response.data)

            print(f"图片下载成功: {file_path}")
            return file_path

        except Exception as e:
            print(f"下载图片失败: {e}")
            raise

    def download_file(self, file_key: str, filename: str = None) -> str:
        """
        下载文件
        返回本地文件路径
        """
        try:
            # 获取文件内容
            request = GetFileRequest.builder() \
                .file_key(file_key) \
                .build()

            response = self.client.im.v1.file.get(request)

            if not response.success():
                raise Exception(f"获取文件失败: {response.msg}")

            # 保存文件
            if not filename:
                filename = file_key

            file_path = os.path.join(self.download_dir, filename)
            # 转换为绝对路径
            file_path = os.path.abspath(file_path)

            with open(file_path, 'wb') as f:
                f.write(response.data)

            print(f"文件下载成功: {file_path}")
            return file_path

        except Exception as e:
            print(f"下载文件失败: {e}")
            raise

    def get_message_resource(self, message_id: str, file_key: str, resource_type: str) -> str:
        """
        获取消息中的资源（图片或文件）
        resource_type: 'image' 或 'file'
        返回本地文件路径
        """
        try:
            # 获取资源
            request = GetMessageResourceRequest.builder() \
                .message_id(message_id) \
                .file_key(file_key) \
                .type(resource_type) \
                .build()

            response = self.client.im.v1.message_resource.get(request)

            if not response.success():
                raise Exception(f"获取资源失败: {response.msg}")

            # 保存文件
            filename = f"{file_key}_{resource_type}"
            file_path = os.path.join(self.download_dir, filename)
            # 转换为绝对路径
            file_path = os.path.abspath(file_path)

            # 处理不同类型的响应数据
            file_data = response.file
            if hasattr(file_data, 'read'):
                # 如果是 BytesIO 或文件对象
                file_data = file_data.read()
            elif not isinstance(file_data, bytes):
                # 如果不是 bytes，尝试转换
                file_data = bytes(file_data)

            with open(file_path, 'wb') as f:
                f.write(file_data)

            print(f"资源下载成功: {file_path}")
            return file_path

        except Exception as e:
            print(f"下载资源失败: {e}")
            import traceback
            traceback.print_exc()
            raise
