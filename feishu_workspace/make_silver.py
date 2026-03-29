#!/usr/bin/env python3
"""
将图片中的盔甲变成银色
使用色调调整和亮度处理
"""
import sys
from PIL import Image, ImageEnhance, ImageFilter

def make_armor_silver(input_path, output_path, padding=50):
    """
    将图片转换为银色调

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        padding: 边距像素
    """
    # 读取原图
    img = Image.open(input_path)

    # 转换为 RGB
    if img.mode != 'RGB':
        if img.mode == 'RGBA':
            # 保留透明通道
            alpha = img.split()[3]
            img = img.convert('RGB')
        else:
            img = img.convert('RGB')
    else:
        alpha = None

    # 降低饱和度，使颜色变灰（银色效果）
    converter = ImageEnhance.Color(img)
    img = converter.enhance(0.3)  # 降低饱和度到30%

    # 增加亮度，使其更像银色
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.2)  # 增加20%亮度

    # 增加对比度，使金属质感更强
    contrast = ImageEnhance.Contrast(img)
    img = contrast.enhance(1.3)  # 增加30%对比度

    # 轻微锐化，增强金属边缘
    img = img.filter(ImageFilter.SHARPEN)

    # 如果有透明通道，恢复它
    if alpha:
        img = img.convert('RGBA')
        img.putalpha(alpha)

    # 创建深色背景
    new_width = img.width + padding * 2
    new_height = img.height + padding * 2
    background = Image.new('RGB', (new_width, new_height), (20, 20, 25))

    # 将处理后的图片居中粘贴到深色背景上
    if img.mode == 'RGBA':
        background.paste(img, (padding, padding), img)
    else:
        background.paste(img, (padding, padding))

    # 保存结果
    background.save(output_path, quality=95)
    print(f"✓ 银色盔甲处理完成！输出文件：{output_path}")
    print(f"  原始尺寸: {img.width}x{img.height}")
    print(f"  新尺寸: {new_width}x{new_height}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python make_silver.py <输入图片> <输出图片>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    make_armor_silver(input_path, output_path)
