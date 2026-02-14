#!/usr/bin/env python3
"""
OCR 工具 - 读取图片中的文字
基于 RapidOCR (ONNX Runtime)，支持中英文混合识别
用途：读取券商持仓截图、交易记录等
"""
import argparse
import json
import sys

def ocr_image(image_path, min_score=0.5):
    """OCR 识别图片文字"""
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    result, elapse = ocr(image_path)
    
    if not result:
        return []
    
    lines = []
    for box, text, score in result:
        if score >= min_score:
            # box 是四个角的坐标 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            y_center = (box[0][1] + box[2][1]) / 2
            x_center = (box[0][0] + box[2][0]) / 2
            lines.append({
                'text': text,
                'score': round(score, 3),
                'x': round(x_center),
                'y': round(y_center),
            })
    
    # 按 y 坐标排序（从上到下），同行按 x 排序
    lines.sort(key=lambda l: (l['y'] // 20, l['x']))
    return lines

def main():
    parser = argparse.ArgumentParser(description="OCR 图片文字识别")
    parser.add_argument("image", help="图片路径")
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    lines = ocr_image(args.image, args.min_score)
    
    if args.json:
        print(json.dumps(lines, ensure_ascii=False, indent=2))
    else:
        for l in lines:
            print(f"[{l['score']:.3f}] {l['text']}")

if __name__ == "__main__":
    main()
