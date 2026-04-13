"""
视频素材获取模块
为"书籍蒸馏"视频提供应景的背景视频画面

素材来源优先级:
1. 本地素材库 (assets/bg_videos/) — 按分类/情绪分子目录
2. Pexels API  — 免费高质量视频素材，根据书籍分类自动搜索

使用方式:
  视频素材 + 大字幕 = 最主流的知识类短视频风格
"""

import json
import random
import re
import urllib.request
import urllib.parse
from pathlib import Path

from config import (
    BG_VIDEOS_DIR,
    PEXELS_API_KEY,
    BG_VIDEO_KEYWORDS,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
)


# ============================================================
# 本地素材库
# ============================================================

def find_local_videos(category: str = "", mood: str = "", count: int = 5) -> list[Path]:
    """
    从本地素材库查找视频

    目录结构:
      assets/bg_videos/
      ├── 心理学/         ← 按分类
      ├── calm/           ← 按情绪
      ├── nature/         ← 按场景
      └── *.mp4           ← 通用素材
    """
    video_exts = ("*.mp4", "*.mov", "*.avi", "*.mkv")

    if not BG_VIDEOS_DIR.exists():
        BG_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        return []

    found = []

    # 优先级1: 按分类查找
    if category:
        cat_dir = BG_VIDEOS_DIR / category
        if cat_dir.exists():
            for ext in video_exts:
                found.extend(cat_dir.glob(ext))

    # 优先级2: 按情绪查找
    if mood and not found:
        mood_dir = BG_VIDEOS_DIR / mood
        if mood_dir.exists():
            for ext in video_exts:
                found.extend(mood_dir.glob(ext))

    # 优先级3: 根目录通用素材
    if not found:
        for ext in video_exts:
            found.extend(BG_VIDEOS_DIR.glob(ext))

    # 优先级4: 所有子目录
    if not found:
        for ext in video_exts:
            found.extend(BG_VIDEOS_DIR.rglob(ext))

    if found:
        random.shuffle(found)
        return found[:count]
    return []


# ============================================================
# Pexels API（免费高质量视频素材）
# ============================================================

def search_pexels_videos(
    query: str,
    count: int = 5,
    orientation: str = "portrait",
    min_duration: int = 10,
) -> list[dict]:
    """
    搜索 Pexels 视频素材

    Args:
        query: 搜索关键词(英文效果最好)
        count: 返回数量
        orientation: "portrait"(竖屏) | "landscape"(横屏)
        min_duration: 最短时长(秒)

    Returns:
        [{"id": int, "url": str, "download_url": str, "duration": int, "width": int, "height": int}, ...]
    """
    if not PEXELS_API_KEY:
        return []

    params = urllib.parse.urlencode({
        "query": query,
        "per_page": count,
        "orientation": orientation,
        "size": "medium",
    })
    url = f"https://api.pexels.com/videos/search?{params}"

    try:
        req = urllib.request.Request(url, headers={
            "Authorization": PEXELS_API_KEY,
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for video in data.get("videos", []):
            if video.get("duration", 0) < min_duration:
                continue

            # 选择最佳质量的视频文件(竖屏优先)
            best_file = _pick_best_video_file(video.get("video_files", []))
            if not best_file:
                continue

            results.append({
                "id": video["id"],
                "url": video.get("url", ""),
                "download_url": best_file["link"],
                "duration": video["duration"],
                "width": best_file.get("width", 0),
                "height": best_file.get("height", 0),
            })

        return results

    except Exception as e:
        print(f"  [Pexels] 搜索失败: {e}")
        return []


def _pick_best_video_file(video_files: list[dict]) -> dict | None:
    """从视频文件列表中选择最合适的版本"""
    if not video_files:
        return None

    # 按分辨率排序，优先选 720p-1080p 的(太高浪费带宽，太低画质差)
    candidates = []
    for f in video_files:
        h = f.get("height", 0)
        w = f.get("width", 0)
        if f.get("file_type") == "video/mp4":
            candidates.append(f)

    if not candidates:
        candidates = video_files

    # 优先竖屏(height > width)
    portrait = [f for f in candidates if f.get("height", 0) > f.get("width", 0)]
    if portrait:
        candidates = portrait

    # 选分辨率适中的
    def score(f):
        h = f.get("height", 0)
        # 720p-1080p 得分最高
        if 720 <= h <= 1080:
            return 100 - abs(h - 1080)
        return h

    candidates.sort(key=score, reverse=True)
    return candidates[0] if candidates else None


def download_pexels_video(video_info: dict, output_dir: Path) -> Path | None:
    """下载 Pexels 视频到本地"""
    download_url = video_info.get("download_url")
    if not download_url:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"pexels_{video_info['id']}.mp4"
    output_path = output_dir / filename

    # 已下载过则跳过
    if output_path.exists():
        return output_path

    try:
        print(f"  [Pexels] 下载素材: {video_info['id']} ({video_info['duration']}s)")
        req = urllib.request.Request(download_url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(str(output_path), "wb") as f:
                f.write(resp.read())
        return output_path
    except Exception as e:
        print(f"  [Pexels] 下载失败: {e}")
        # 清理不完整的文件
        if output_path.exists():
            output_path.unlink()
        return None


# ============================================================
# 统一入口
# ============================================================

def get_bg_videos(
    category: str = "",
    book_title: str = "",
    count: int = 3,
    cache_dir: Path = None,
) -> list[Path]:
    """
    获取背景视频素材(统一入口)

    优先级: 本地素材 → Pexels API 下载

    Args:
        category: 书籍分类
        book_title: 书名(用于缓存目录)
        count: 需要多少段素材
        cache_dir: 下载缓存目录(默认 assets/bg_videos/{category}/)

    Returns:
        视频文件路径列表
    """
    # 获取情绪标签
    from bgm_matcher import CATEGORY_TO_MOOD
    mood = CATEGORY_TO_MOOD.get(category, "calm")

    # Step 1: 本地素材
    local = find_local_videos(category=category, mood=mood, count=count)
    if len(local) >= count:
        print(f"  [素材] 使用本地素材: {len(local)} 段")
        return local[:count]

    # Step 2: Pexels API 在线搜索
    if PEXELS_API_KEY:
        keywords = BG_VIDEO_KEYWORDS.get(category, BG_VIDEO_KEYWORDS["default"])
        keyword = random.choice(keywords)

        print(f"  [素材] Pexels 搜索: {keyword}")
        results = search_pexels_videos(keyword, count=count * 2)

        if results:
            if cache_dir is None:
                cache_dir = BG_VIDEOS_DIR / (category or "default")

            downloaded = list(local)  # 加上已有的本地素材
            for video_info in results:
                if len(downloaded) >= count:
                    break
                path = download_pexels_video(video_info, cache_dir)
                if path:
                    downloaded.append(path)

            if downloaded:
                print(f"  [素材] 共获取 {len(downloaded)} 段视频素材")
                return downloaded[:count]

    # Step 3: 还是没有素材，给出提示
    if not local:
        print(f"  [素材] 无可用视频素材")
        print(f"    方案1: 配置 PEXELS_API_KEY (免费注册 https://www.pexels.com/api/)")
        print(f"    方案2: 手动放视频到 assets/bg_videos/ 目录")
        print(f"    降级为卡片模式...")

    return local


# ============================================================
# 工具函数
# ============================================================

def setup_bg_video_dirs():
    """创建视频素材目录结构"""
    BG_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    for category in BG_VIDEO_KEYWORDS:
        if category != "default":
            (BG_VIDEOS_DIR / category).mkdir(exist_ok=True)

    print("已创建视频素材目录结构:")
    for category in BG_VIDEO_KEYWORDS:
        if category != "default":
            print(f"  assets/bg_videos/{category}/")
    print(f"  assets/bg_videos/              ← 通用素材")
    print(f"\n放入竖屏(9:16)的 MP4 视频素材即可。")
    print(f"推荐来源: Pexels (pexels.com), Pixabay, Mixkit")


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="视频素材获取工具")
    subparsers = parser.add_subparsers(dest="command")

    # setup: 创建目录
    subparsers.add_parser("setup", help="创建素材目录结构")

    # search: 搜索 Pexels
    search_parser = subparsers.add_parser("search", help="搜索 Pexels 视频素材")
    search_parser.add_argument("query", type=str, help="搜索关键词(英文)")
    search_parser.add_argument("--count", type=int, default=5, help="数量")

    # download: 按分类批量下载
    dl_parser = subparsers.add_parser("download", help="按书籍分类批量下载素材")
    dl_parser.add_argument("--category", type=str, help="书籍分类")
    dl_parser.add_argument("--count", type=int, default=3, help="每分类下载数量")

    args = parser.parse_args()

    if args.command == "setup":
        setup_bg_video_dirs()

    elif args.command == "search":
        results = search_pexels_videos(args.query, count=args.count)
        for r in results:
            print(f"  [{r['id']}] {r['duration']}s {r['width']}x{r['height']} {r['url']}")

    elif args.command == "download":
        categories = [args.category] if args.category else list(BG_VIDEO_KEYWORDS.keys())
        for cat in categories:
            if cat == "default":
                continue
            print(f"\n--- {cat} ---")
            get_bg_videos(category=cat, count=args.count)

    else:
        parser.print_help()
