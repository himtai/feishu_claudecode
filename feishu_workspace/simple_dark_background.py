#!/usr/bin/env python3
"""
简单的深色背景替换工具
不需要 AI 模型，使用图像处理技术
"""
import sys
from PIL import Image, ImageDraw, ImageFilter

def add_dark_background(input_path, output_path, bg_color=(20, 20, 25), padding=50):
    """
    为图片添加深色背景

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        bg_color: 背景颜色 RGB 元组，默认深灰色
        padding: 边距像素
    """
    # 读取原图
    img = Image.open(input_path)

    # 转换为 RGBA（如果不是的话）
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # 创建新的深色背景图片（比原图大一些，留出边距）
    new_width = img.width + padding * 2
    new_height = img.height + padding * 2
    background = Image.new('RGB', (new_width, new_height), bg_color)

    # 将原图居中粘贴到深色背景上
    # 如果原图有透明通道，使用它作为 mask
    background.paste(img, (padding, padding), img if img.mode == 'RGBA' else None)

    # 保存结果
    background.save(output_path, quality=95)
    print(f"✓ 深色背景添加完成！输出文件：{output_path}")
    print(f"  原始尺寸: {img.width}x{img.height}")
    print(f"  新尺寸: {new_width}x{new_height}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python simple_dark_background.py <输入图片> <输出图片>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    add_dark_background(input_path, output_path)
