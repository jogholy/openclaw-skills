#!/bin/bash
# 测试图片生成

echo "🎨 测试 Seedream 4.5 (最便宜)"
python3 ~/.openclaw/skills/media-generator/scripts/generate.py image \
  "A serene mountain landscape at dawn" \
  --provider xskill \
  --model fal-ai/bytedance/seedream/v4.5/text-to-image

echo ""
echo "🎨 测试 Nano Banana 2 (推荐)"
python3 ~/.openclaw/skills/media-generator/scripts/generate.py image \
  "A cute robot with text 'Hello AI'" \
  --provider xskill \
  --model fal-ai/nano-banana-2
