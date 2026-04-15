"""
Coze API 极简同步视频生成模块

功能:
1. 直接调用 Coze Workflow API (同步模式)
2. 解析返回的 JSON 数据
3. 自动下载视频
"""

import os
import time
import json
import urllib.request
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse

from config import (
    COZE_API_KEY,
    COZE_WORKFLOW_ID,
    COZE_API_BASE,
    OUTPUT_DIR
)


class CozeError(Exception):
    pass


def _call_coze_api(payload: dict, timeout: int = 120) -> dict:
    """直接调用同步运行工作流接口"""
    if not COZE_API_KEY:
        raise CozeError("COZE_API_KEY 未配置")
    if not COZE_WORKFLOW_ID:
        raise CozeError("COZE_WORKFLOW_ID 未配置")

    # 工作流同步运行接口
    url = f"{COZE_API_BASE}/workflow/run"
    parsed_url = urlparse(COZE_API_BASE)
    
    headers = {
        "Authorization": f"Bearer {COZE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Host": parsed_url.netloc, 
    }
    
    payload["workflow_id"] = COZE_WORKFLOW_ID
    data = json.dumps(payload).encode("utf-8")

    print(f"  [Coze API] 正在发起视频生成请求 (同步等待模式，预计耗时 30-90s)...")
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        # 视频生成较慢，我们将请求超时设为 120 秒
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response_text = resp.read().decode()
            if resp.status != 200:
                raise CozeError(f"API 请求失败, 状态码: {resp.status}, 响应: {response_text}")
            return json.loads(response_text)
    except HTTPError as e:
        error_body = e.read().decode(errors='ignore')
        raise CozeError(f"调用 Coze API 失败: HTTP Error {e.code}, 响应: {error_body}") from e
    except Exception as e:
        if "time" in str(e).lower() and "out" in str(e).lower():
            raise CozeError(f"请求超时({timeout}秒)，AI 生成视频耗时过长，请检查 Coze 后台任务状态。") from e
        raise CozeError(f"调用 Coze API 失败: {e}") from e


def download_video(video_url: str, save_dir: Path) -> Path:
    """从 URL 下载视频到指定目录"""
    # 过滤掉 URL 参数获取纯净文件名
    filename = Path(video_url.split("?")[0]).name
    if not filename or not filename.endswith(".mp4"):
        filename = f"coze_video_{int(time.time())}.mp4"
        
    save_path = save_dir / filename
    save_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"  [Coze] 正在下载视频 -> {save_path}")
    
    req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp, open(save_path, 'wb') as f:
        f.write(resp.read())
        
    print("  [Coze] 下载完成!")
    return save_path


def generate_video_by_coze(prompt: str, user: str = "python_client") -> Path:
    """
    通过 Coze 同步生成视频的完整流程
    """
    payload = {
        "parameters": {
            "prompt": prompt,
        },
        "ext": {
            "user_id": user
        }
    }
    
    response = _call_coze_api(payload)
    
    if response.get("code") != 0:
        raise CozeError(f"工作流运行失败: {response.get('msg')}")
    
    # 核心：Coze 工作流返回的结果在 data 字段中，且通常是一个 JSON 字符串
    raw_data = response.get("data")
    if not raw_data:
        raise CozeError("API 返回结果中没有 data 数据")
    
    try:
        # 尝试解析 data 里的 JSON
        result = json.loads(raw_data)
    except json.JSONDecodeError:
        # 如果不是 JSON，可能直接就是结果内容（较少见）
        raise CozeError(f"无法解析 data 字段为 JSON: {raw_data}")

    # 寻找视频 URL (兼容 download_url 和 video_url)
    video_url = result.get("download_url") or result.get("video_url")
    
    if not video_url:
        raise CozeError(f"工作流输出中未找到视频链接。当前输出为: {raw_data}。请检查工作流结束节点的变量名是否为 download_url 或 video_url。")
        
    # 保存到临时目录
    temp_dir = OUTPUT_DIR / "_temp" / "coze_videos"
    return download_video(video_url, temp_dir)


# ============ 命令行测试入口 ============
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Coze 视频生成 API 极简测试工具")
    parser.add_argument("prompt", type=str, help="视频生成的提示词")
    args = parser.parse_args()

    try:
        video_file = generate_video_by_coze(args.prompt)
        print(f"\n成功！视频已保存到: {video_file}")
    except CozeError as e:
        print(f"\n出错了: {e}")
