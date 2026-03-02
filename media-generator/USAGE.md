# Media Generator 使用指南

## 余额查询 ⭐ NEW

```bash
python3 ~/.openclaw/skills/media-generator/scripts/generate.py balance --provider xskill
```

## 图片生成

```bash
# 最便宜 (16积分/张)
python3 ~/.openclaw/skills/media-generator/scripts/generate.py image \
  "A beautiful sunset" \
  --provider xskill \
  --model fal-ai/bytedance/seedream/v4.5/text-to-image
```

## 视频生成

```bash
# 文生视频 (15积分/秒)
python3 ~/.openclaw/skills/media-generator/scripts/generate.py video \
  "一位女孩在花田中跳舞" \
  --provider xskill \
  --model st-ai/super-seed2 \
  --duration 5
```

## 音频生成 ⭐ NEW

```bash
# 语音合成 (35积分/千字)
python3 ~/.openclaw/skills/media-generator/scripts/generate.py audio \
  "大家好，欢迎收听" \
  --provider xskill \
  --model minimax/t2a \
  --voice female-tianmei
```

## 费用说明

- 图片: 16-60 积分/张
- 视频: 15-60 积分/秒
- 音频: 35 积分/千字 (HD) / 20 积分/千字 (Turbo)
