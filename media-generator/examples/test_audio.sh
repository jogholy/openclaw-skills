#!/bin/bash
# 测试音频生成

echo "🎵 测试海螺语音合成"
python3 ~/.openclaw/skills/media-generator/scripts/generate.py audio \
  "各位听众朋友们，大家好！今天我们来聊聊人工智能，非常有趣的话题。" \
  --provider xskill \
  --model minimax/t2a \
  --voice female-tianmei
