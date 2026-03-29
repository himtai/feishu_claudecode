#!/usr/bin/env python3
import sys
from PIL import Image
from rembg import remove

def replace_background_with_dark(input_path, output_path, bg_color=(0, 0, 0)):
    """
    将图片背景替换为深色

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        bg_color: 背景颜色 RGB 元组，默认黑色 (0, 0, 0)
    """
    # 读取原图
    input_image = Image.open(input_path)

    # 使用 rembg 移除背景，得到透明背景的图片
    output_image = remove(input_image)

    # 创建深色背景
    background = Image.new('RGB', output_image.size, bg_color)

    # 将主体合成到深色背景上
    background.paste(output_image, (0, 0), output_image)

    # 保存结果
    background.save(output_path)
    print(f"✓ 背景替换完成！输出文件：{output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python replace_background.py <输入图片> <输出图片>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    replace_background_with_dark(input_path, output_path)
