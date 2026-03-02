#!/usr/bin/env python3
"""通用音视频生成工具"""
import requests
import json
import time
import sys
import argparse
from pathlib import Path

class MediaGenerator:
    def __init__(self, provider_config):
        self.api_key = provider_config["apiKey"]
        self.base_url = provider_config["baseUrl"]
    
    def create_task(self, model, params):
        url = f"{self.base_url}/api/v3/tasks/create"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {"model": model, "params": params}
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        if result.get("code") != 200:
            raise Exception(f"创建任务失败: {result}")
        
        return result["data"]["task_id"], result["data"].get("price", 0)
    
    def query_task(self, task_id):
        url = f"{self.base_url}/api/v3/tasks/query"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        response = requests.post(url, json={"task_id": task_id}, headers=headers)
        result = response.json()
        
        if result.get("code") != 200:
            raise Exception(f"查询失败: {result}")
        
        return result["data"]
    
    def get_balance(self):
        """查询余额"""
        # 通过创建一个测试任务来获取余额信息
        url = f"{self.base_url}/api/v3/tasks/create"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "fal-ai/bytedance/seedream/v4.5/text-to-image",
            "params": {"prompt": "test", "num_images": 1}
        }
        
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        if result.get("code") == 200:
            balance = result["data"].get("balance", 0)
            task_id = result["data"]["task_id"]
            
            # 取消任务
            try:
                requests.post(f"{self.base_url}/api/v3/tasks/cancel",
                            json={"task_id": task_id}, headers=headers, timeout=5)
            except:
                pass
            
            return balance
        
        return None
    
    def wait_for_completion(self, task_id, max_wait=300):
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            data = self.query_task(task_id)
            status = data["status"]
            
            if status == "completed":
                return data["output"]
            elif status == "failed":
                error = data.get("output", {}).get("error", "Unknown")
                raise Exception(f"生成失败: {error}")
            
            time.sleep(5)
        
        raise Exception("任务超时")

def load_config():
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    return config["skills"]["entries"]["media-generator"]

def generate_image(generator, prompt, model, num_images=1):
    params = {"prompt": prompt, "num_images": num_images}
    task_id, price = generator.create_task(model, params)
    print(f"✅ 任务创建: {task_id}, 费用: {price}")
    
    output = generator.wait_for_completion(task_id)
    images = output["images"]
    
    for i, img in enumerate(images):
        url = img["url"] if isinstance(img, dict) else img
        print(f"图片 {i+1}: {url}")
    
    return images

def generate_video(generator, prompt, model, duration=5, ratio="16:9", image_files=None, video_files=None):
    params = {"prompt": prompt, "duration": duration, "ratio": ratio}
    
    if image_files or video_files:
        params["functionMode"] = "omni_reference"
        if image_files:
            params["image_files"] = image_files
        if video_files:
            params["video_files"] = video_files
    
    task_id, price = generator.create_task(model, params)
    print(f"✅ 任务创建: {task_id}, 费用: {price}")
    
    output = generator.wait_for_completion(task_id, max_wait=120)
    video_url = output.get("video") or output.get("videos", [{}])[0].get("url")
    
    print(f"🎬 视频: {video_url}")
    return video_url

def generate_audio(generator, text, model, voice_id="female-tianmei"):
    params = {"text": text, "voice_id": voice_id}
    task_id, price = generator.create_task(model, params)
    print(f"✅ 任务创建: {task_id}, 费用: {price}")
    
    output = generator.wait_for_completion(task_id)
    audio_url = output.get("audio") or output.get("audio_url")
    
    print(f"🎵 音频: {audio_url}")
    return audio_url

def show_balance(generator):
    balance = generator.get_balance()
    if balance is None:
        print("❌ 无法获取余额")
        return
    
    print(f"\n💰 当前余额: {balance} 积分 (¥{balance/100:.2f})")
    print(f"\n📊 可生成数量估算:")
    print(f"  图片 (Seedream 4.5, 16积分/张): ~{balance//16} 张")
    print(f"  图片 (Nano Banana 2, 32积分/张): ~{balance//32} 张")
    print(f"  视频 (Seedance 2.0 Fast, 15积分/秒): ~{balance//15} 秒 (~{balance//75} 个5秒视频)")
    print(f"  音频 (海螺 HD, 35积分/千字): ~{balance//35} 千字 (~{balance//350} 万字)")

def main():
    parser = argparse.ArgumentParser(description="音视频生成工具")
    parser.add_argument("type", choices=["image", "video", "audio", "balance"])
    parser.add_argument("prompt", nargs="?", help="提示词")
    parser.add_argument("--provider", default="xskill")
    parser.add_argument("--model", help="模型ID")
    parser.add_argument("--num", type=int, default=1)
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--ratio", default="16:9")
    parser.add_argument("--voice", default="female-tianmei")
    parser.add_argument("--image-files", nargs="+")
    parser.add_argument("--video-files", nargs="+")
    
    args = parser.parse_args()
    
    config = load_config()
    provider_config = config["providers"][args.provider]
    generator = MediaGenerator(provider_config)
    
    if args.type == "balance":
        show_balance(generator)
    elif args.type == "image":
        if not args.model:
            parser.error("--model is required for image generation")
        generate_image(generator, args.prompt, args.model, args.num)
    elif args.type == "video":
        if not args.model:
            parser.error("--model is required for video generation")
        generate_video(generator, args.prompt, args.model, args.duration, args.ratio, args.image_files, args.video_files)
    elif args.type == "audio":
        if not args.model:
            parser.error("--model is required for audio generation")
        generate_audio(generator, args.prompt, args.model, args.voice)

if __name__ == "__main__":
    main()
