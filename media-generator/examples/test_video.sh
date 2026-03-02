#!/bin/bash
# 测试视频生成

echo "🎬 测试 Seedance 2.0 文生视频"
python3 ~/.openclaw/skills/media-generator/scripts/generate.py video \
  "一位穿着红色裙子的女孩在花田中旋转跳舞，阳光洒落，花瓣飘散" \
  --provider xskill \
  --model st-ai/super-seed2 \
  --duration 5 \
  --ratio 16:9
