#!/usr/bin/env python3
"""
将图片中的金色部分替换为银色
通过HSV色彩空间识别金色区域并转换为银色
"""
import sys
import numpy as np
from PIL import Image

def gold_to_silver(input_path, output_path):
    """
    将图片中的金色替换为银色

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
    """
    # 读取图片
    img = Image.open(input_path)
    img_array = np.array(img)

    # 转换为HSV色彩空间以便更好地识别金色
    img_hsv = Image.fromarray(img_array).convert('HSV')
    hsv_array = np.array(img_hsv, dtype=np.float32)

    # 金色的HSV范围（黄色系，高饱和度，中高亮度）
    # H: 30-60 (黄色到橙黄色)
    # S: 较高饱和度
    # V: 中高亮度
    h, s, v = hsv_array[:,:,0], hsv_array[:,:,1], hsv_array[:,:,2]

    # 识别金色区域（黄色系）
    gold_mask = ((h >= 20) & (h <= 60) & (s >= 30))

    # 将金色区域转换为银色（降低饱和度，保持亮度）
    # 银色是低饱和度的灰色
    hsv_array[:,:,1] = np.where(gold_mask, s * 0.15, s)  # 大幅降低饱和度
    hsv_array[:,:,0] = np.where(gold_mask, 0, h)  # 色调变为中性

    # 转回RGB
    img_hsv_modified = Image.fromarray(hsv_array.astype('uint8'), 'HSV')
    img_rgb = img_hsv_modified.convert('RGB')

    # 保存结果
    img_rgb.save(output_path, quality=95)
    print(f"✓ 金色已替换为银色！输出文件：{output_path}")
    print(f"  图片尺寸: {img.width}x{img.height}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python gold_to_silver.py <输入图片> <输出图片>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    gold_to_silver(input_path, output_path)
