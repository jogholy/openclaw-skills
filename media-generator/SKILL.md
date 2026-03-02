# Media Generator Skill

通用音视频生成工具，支持多平台、多模型。

## 使用场景

当用户请求生成图片、视频或音频时激活此 skill。

## 配置要求

需要在 `~/.openclaw/openclaw.json` 中配置 API Key：

```json
{
  "skills": {
    "entries": {
      "media-generator": {
        "providers": {
          "xskill": {
            "apiKey": "sk-your-api-key",
            "baseUrl": "https://api.xskill.ai"
          }
        }
      }
    }
  }
}
```

## 快速使用

```bash
# 生成图片
python ~/.openclaw/skills/media-generator/scripts/generate.py image \
  "A beautiful sunset over mountains" \
  --provider xskill \
  --model fal-ai/bytedance/seedream/v4.5/text-to-image
```

## 推荐模型

### 图片生成
- `fal-ai/bytedance/seedream/v4.5/text-to-image` - 16积分/张，最便宜
- `fal-ai/nano-banana-2` - 32积分/张，速度快，支持文字渲染
- `fal-ai/nano-banana-pro` - 60积分/张，高质量

### 视频生成（待实现）
- `st-ai/super-seed2` - Seedance 2.0

### 音频生成（待实现）
- `minimax/hailuo-tts` - 海螺语音合成
