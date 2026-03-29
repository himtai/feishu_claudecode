"""
飞书自定义工具
为 Claude Agent 提供飞书特定功能
"""


def get_feishu_tools(chat_id: str, uploader):
    """获取飞书自定义工具定义"""
    return [
        {
            "name": "SendImage",
            "description": "发送图片到飞书聊天。当需要展示图表、截图或其他图片时使用。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图片文件的绝对路径"
                    },
                    "description": {
                        "type": "string",
                        "description": "图片的描述（可选）"
                    }
                },
                "required": ["image_path"]
            },
            "handler": lambda params: send_image_handler(chat_id, uploader, params)
        },
        {
            "name": "SendFile",
            "description": "发送文件到飞书聊天。当需要分享日志、配置文件或其他文档时使用。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件的绝对路径"
                    },
                    "description": {
                        "type": "string",
                        "description": "文件的描述（可选）"
                    }
                },
                "required": ["file_path"]
            },
            "handler": lambda params: send_file_handler(chat_id, uploader, params)
        }
    ]


def send_image_handler(chat_id: str, uploader, params: dict) -> dict:
    """处理发送图片"""
    try:
        image_path = params.get("image_path")
        description = params.get("description", "")

        if not image_path:
            return {"success": False, "error": "缺少 image_path 参数"}

        # 发送图片
        success = uploader.send_image(chat_id, image_path)

        if success:
            return {
                "success": True,
                "message": f"图片已发送: {image_path}",
                "description": description
            }
        else:
            return {"success": False, "error": "发送图片失败"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def send_file_handler(chat_id: str, uploader, params: dict) -> dict:
    """处理发送文件"""
    try:
        file_path = params.get("file_path")
        description = params.get("description", "")

        if not file_path:
            return {"success": False, "error": "缺少 file_path 参数"}

        # 发送文件
        success = uploader.send_file(chat_id, file_path)

        if success:
            return {
                "success": True,
                "message": f"文件已发送: {file_path}",
                "description": description
            }
        else:
            return {"success": False, "error": "发送文件失败"}

    except Exception as e:
        return {"success": False, "error": str(e)}
