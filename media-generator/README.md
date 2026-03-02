# Media Generator Skill

AI 音视频生成工具，支持图片、视频、音频生成。

## 功能

- ✅ 图片生成（文生图、图像编辑）
- ✅ 视频生成（文生视频、图生视频、全能模式）
- ✅ 音频生成（语音合成）
- ✅ 余额查询和数量估算

## 依赖

### API Key 获取

本 skill 需要 xskill.ai 平台的 API Key：

1. 访问 https://www.xskill.ai/
2. 注册/登录账号
3. 进入 API Key 页面：https://www.xskill.ai/#/v2/api-keys
4. 创建新的 API Key
5. 充值积分（支持支付宝/微信）

### 配置

在 `~/.openclaw/openclaw.json` 中添加：

```json
{
  "skills": {
    "entries": {
      "media-generator": {
        "providers": {
          "xskill": {
            "apiKey": "sk-your-api-key-here",
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
# 查询余额
python3 ~/.openclaw/skills/media-generator/scripts/generate.py balance

# 生成图片 (16积分/张)
python3 ~/.openclaw/skills/media-generator/scripts/generate.py image \
  "A beautiful cat" \
  --model fal-ai/bytedance/seedream/v4.5/text-to-image

# 生成视频 (15积分/秒)
python3 ~/.openclaw/skills/media-generator/scripts/generate.py video \
  "跳舞的女孩" \
  --model st-ai/super-seed2 \
  --duration 5

# 生成音频 (35积分/千字)
python3 ~/.openclaw/skills/media-generator/scripts/generate.py audio \
  "你好世界" \
  --model minimax/t2a
```

## 费用说明

- 图片：16-60 积分/张
- 视频：15-60 积分/秒
- 音频：35 积分/千字 (HD) / 20 积分/千字 (Turbo)

详见 `USAGE.md` 和 `models.json`
