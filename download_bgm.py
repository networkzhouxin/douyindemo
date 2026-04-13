"""
BGM 自动搜索下载模块
从免费音乐库自动搜索、下载匹配情绪的背景音乐

支持的音乐源：
1. Pixabay Music — 完全免费，无版权，质量高（推荐）
2. Freesound — 学术级免费音效/音乐库
"""

import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

from config import (
    BGM_DIR,
    PIXABAY_API_KEY,
    FREESOUND_API_KEY,
)

# 情绪 → 搜索关键词映射（英文，用于 API 搜索）
MOOD_SEARCH_KEYWORDS = {
    "calm": [
        "calm piano",
        "soft ambient",
        "gentle acoustic",
        "peaceful piano",
        "relaxing background",
    ],
    "inspiring": [
        "inspiring upbeat",
        "motivational",
        "uplifting corporate",
        "positive energy",
        "happy acoustic",
    ],
    "emotional": [
        "emotional strings",
        "warm cinematic",
        "sentimental piano",
        "touching melody",
        "soft emotional",
    ],
    "thoughtful": [
        "ambient atmospheric",
        "deep thinking",
        "minimal piano",
        "contemplative",
        "space ambient",
    ],
    "energetic": [
        "upbeat pop",
        "energetic background",
        "dynamic rhythm",
        "fun happy",
        "bright energetic",
    ],
}


# ============================================================
# Pixabay Music API（推荐，完全免费无版权）
# 注册获取 Key: https://pixabay.com/api/docs/
# ============================================================

def search_pixabay(query: str, mood: str = "", max_results: int = 5) -> list[dict]:
    """
    搜索 Pixabay 音乐

    Returns:
        [{"id": int, "title": str, "url": str, "duration": int, "tags": str}, ...]
    """
    if not PIXABAY_API_KEY:
        print("未配置 PIXABAY_API_KEY，请在 config.py 或环境变量中设置")
        print("免费注册: https://pixabay.com/api/docs/")
        return []

    # Pixabay 目前没有公开稳定的音频 API 端点
    # 其图片/视频 API (/api/, /api/videos/) 不支持音乐搜索
    # 建议直接访问 Pixabay Music 网站手动下载，或使用 Freesound API
    print(f"[Pixabay] 搜索: {query}")
    print(f"  注意: Pixabay 暂无公开音频 API，请手动下载:")
    print(f"  https://pixabay.com/music/search/{urllib.parse.quote(query)}/")
    print(f"  下载后放入 assets/bgm/ 目录即可")
    print(f"  或改用 Freesound API（配置 FREESOUND_API_KEY）自动下载")

    return []


# ============================================================
# Freesound API（免费，需注册）
# 注册获取 Key: https://freesound.org/apiv2/apply/
# ============================================================

def search_freesound(
    query: str,
    min_duration: int = 30,
    max_duration: int = 300,
    max_results: int = 5,
) -> list[dict]:
    """
    搜索 Freesound 音乐

    Returns:
        [{"id": int, "name": str, "duration": float, "preview_url": str, "download_url": str}, ...]
    """
    if not FREESOUND_API_KEY:
        print("未配置 FREESOUND_API_KEY，请在 config.py 或环境变量中设置")
        print("免费注册: https://freesound.org/apiv2/apply/")
        return []

    params = urllib.parse.urlencode({
        "query": query,
        "filter": f"duration:[{min_duration} TO {max_duration}]",
        "fields": "id,name,duration,previews,download",
        "page_size": max_results,
        "sort": "rating_desc",
        "token": FREESOUND_API_KEY,
    })
    url = f"https://freesound.org/apiv2/search/text/?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                print(f"[Freesound] HTTP {resp.status}，搜索失败")
                return []
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                print(f"[Freesound] 返回数据不是有效 JSON")
                return []

        results = []
        for item in data.get("results", []):
            previews = item.get("previews", {})
            preview_url = previews.get("preview-hq-mp3", previews.get("preview-lq-mp3", ""))
            results.append({
                "id": item["id"],
                "name": item["name"],
                "duration": item["duration"],
                "preview_url": preview_url,
                "download_url": item.get("download", ""),
            })

        print(f"[Freesound] 搜索 '{query}'，找到 {len(results)} 个结果")
        return results

    except Exception as e:
        print(f"[Freesound] 搜索失败: {e}")
        return []


def download_from_freesound(
    sound_id: int,
    output_dir: Path,
    filename: str = None,
) -> Path | None:
    """
    从 Freesound 下载音频预览文件（预览文件无需 OAuth 认证）
    """
    if not FREESOUND_API_KEY:
        return None

    # 获取音频详情
    url = f"https://freesound.org/apiv2/sounds/{sound_id}/?token={FREESOUND_API_KEY}&fields=name,previews"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        preview_url = data.get("previews", {}).get("preview-hq-mp3", "")
        if not preview_url:
            print(f"  无法获取音频 {sound_id} 的预览地址")
            return None

        # 下载
        if not filename:
            safe_name = re.sub(r'[^\w\-.]', '_', data.get("name", str(sound_id)))[:50]
            filename = f"{safe_name}.mp3"

        output_path = output_dir / filename

        print(f"  正在下载: {data.get('name', '')} → {output_path.name}")
        # 带超时的下载（urlretrieve 不支持超时，改用 urlopen）
        dl_req = urllib.request.Request(preview_url)
        with urllib.request.urlopen(dl_req, timeout=60) as dl_resp:
            with open(str(output_path), "wb") as out_f:
                out_f.write(dl_resp.read())

        return output_path

    except Exception as e:
        print(f"  下载失败: {e}")
        return None


# ============================================================
# 综合搜索与下载
# ============================================================

def auto_download_bgm(
    mood: str = "calm",
    count: int = 3,
    source: str = "freesound",
) -> list[Path]:
    """
    自动搜索并下载指定情绪的 BGM

    Args:
        mood: 情绪类型 (calm/inspiring/emotional/thoughtful/energetic)
        count: 每种关键词下载数量
        source: 音乐源 ("freesound" 目前稳定可用)

    Returns:
        下载成功的文件路径列表
    """
    keywords = MOOD_SEARCH_KEYWORDS.get(mood, MOOD_SEARCH_KEYWORDS["calm"])
    output_dir = BGM_DIR / mood
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []

    for keyword in keywords:
        if source == "freesound":
            results = search_freesound(keyword, max_results=count)
            for item in results:
                # 避免重复下载
                existing = list(output_dir.glob(f"*{item['id']}*"))
                if existing:
                    print(f"  已存在: {existing[0].name}，跳过")
                    downloaded.append(existing[0])
                    continue

                safe_name = re.sub(r'[^\w\-.]', '_', item['name'][:30])
                filename = f"{mood}_{item['id']}_{safe_name}.mp3"
                path = download_from_freesound(item["id"], output_dir, filename)
                if path:
                    downloaded.append(path)
                    time.sleep(0.5)  # 礼貌间隔

        if len(downloaded) >= count:
            break

    print(f"\n[{mood}] 共下载 {len(downloaded)} 首 BGM 到 {output_dir}")
    return downloaded


def auto_download_all_moods(count_per_mood: int = 3, source: str = "freesound"):
    """为所有情绪分类自动下载 BGM"""
    total = 0
    for mood in MOOD_SEARCH_KEYWORDS:
        print(f"\n{'='*50}")
        print(f"正在下载 [{mood}] 类 BGM...")
        print(f"{'='*50}")
        results = auto_download_bgm(mood, count=count_per_mood, source=source)
        total += len(results)

    print(f"\n全部完成！共下载 {total} 首 BGM")


# ============================================================
# 无 API Key 时的备选方案：生成下载指引
# ============================================================

def generate_download_guide(mood: str = None):
    """
    当没有 API Key 时，生成手动下载的详细指引
    包含直接可访问的免费音乐网站链接
    """
    moods = [mood] if mood else list(MOOD_SEARCH_KEYWORDS.keys())

    print("\n" + "=" * 60)
    print("BGM 免费下载指南（无需 API Key）")
    print("=" * 60)

    print("\n以下网站提供完全免费、无版权的音乐，可直接下载：\n")

    sites = [
        {
            "name": "Pixabay Music",
            "url": "https://pixabay.com/music/",
            "desc": "最推荐，高质量免费音乐，无需注册即可下载",
        },
        {
            "name": "Mixkit",
            "url": "https://mixkit.co/free-stock-music/",
            "desc": "免费高质量背景音乐，无需注册",
        },
        {
            "name": "Uppbeat",
            "url": "https://uppbeat.io/",
            "desc": "免费计划每月10首下载",
        },
        {
            "name": "Bensound",
            "url": "https://www.bensound.com/",
            "desc": "经典免费音乐库",
        },
        {
            "name": "Chosic",
            "url": "https://www.chosic.com/free-music/all/",
            "desc": "聚合多个免费音乐源",
        },
    ]

    for site in sites:
        print(f"  {site['name']}")
        print(f"    {site['url']}")
        print(f"    {site['desc']}\n")

    print("-" * 60)
    print("\n按情绪搜索的推荐关键词：\n")

    for m in moods:
        keywords = MOOD_SEARCH_KEYWORDS.get(m, [])
        mood_dir = BGM_DIR / m
        print(f"  [{m}] → 下载后放入 assets/bgm/{m}/")
        for kw in keywords:
            print(f"    搜索: {kw}")
        print()

    print("提示：在 Pixabay Music 搜索上述英文关键词效果最好。")
    print("下载后将 MP3 文件放入对应的 assets/bgm/{mood}/ 目录即可。\n")


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BGM 自动搜索下载工具")
    subparsers = parser.add_subparsers(dest="command")

    # download: 自动下载
    dl_parser = subparsers.add_parser("download", help="自动搜索并下载 BGM")
    dl_parser.add_argument(
        "--mood", choices=list(MOOD_SEARCH_KEYWORDS.keys()),
        help="指定情绪类型（不指定则下载所有）",
    )
    dl_parser.add_argument("--count", type=int, default=3, help="每种情绪下载数量(默认3)")
    dl_parser.add_argument(
        "--source", choices=["freesound"], default="freesound",
        help="音乐源(默认freesound)",
    )

    # guide: 下载指引
    guide_parser = subparsers.add_parser("guide", help="查看免费音乐下载指引（无需API Key）")
    guide_parser.add_argument("--mood", choices=list(MOOD_SEARCH_KEYWORDS.keys()), help="指定情绪类型")

    # search: 仅搜索不下载
    search_parser = subparsers.add_parser("search", help="搜索音乐（仅展示结果）")
    search_parser.add_argument("query", type=str, help="搜索关键词")
    search_parser.add_argument("--source", choices=["freesound"], default="freesound")

    args = parser.parse_args()

    if args.command == "download":
        if args.mood:
            auto_download_bgm(args.mood, count=args.count, source=args.source)
        else:
            auto_download_all_moods(count_per_mood=args.count, source=args.source)

    elif args.command == "guide":
        generate_download_guide(args.mood)

    elif args.command == "search":
        if args.source == "freesound":
            results = search_freesound(args.query)
            for r in results:
                print(f"  [{r['id']}] {r['name']} ({r['duration']:.0f}s)")

    else:
        parser.print_help()
