"""
书单自动采集模块
自动从多个来源获取热门/优质书籍，填充 book_list.json

来源：
1. 豆瓣热门榜 — 爬取豆瓣读书的热门/高分书单
2. AI 推荐 — 用 LLM 按分类批量推荐适合做短视频的书
3. 自动补充 — 书单快用完时自动触发采集

全自动：main.py 运行时会自动检测书单余量，不够就自动补充
"""

import json
import random
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from config import (
    BASE_DIR,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    BOOK_LIST_MIN_PENDING,
    BOOK_LIST_REFILL_COUNT,
    BOOK_TARGET_CATEGORIES,
)


def load_book_list() -> list[dict]:
    path = BASE_DIR / "book_list.json"
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  书单文件读取失败: {e}")
        return []


def save_book_list(books: list[dict]):
    path = BASE_DIR / "book_list.json"
    # 原子写入：先写临时文件再重命名
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def get_existing_titles(books: list[dict]) -> set[str]:
    """获取已有书名集合（用于去重）"""
    return {b["title"] for b in books}


def get_next_id(books: list[dict]) -> int:
    if not books:
        return 1
    return max(b.get("id", 0) for b in books) + 1


def count_pending(books: list[dict]) -> int:
    return sum(1 for b in books if b.get("status") == "pending")


# ============================================================
# 来源 1：豆瓣读书
# ============================================================

DOUBAN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://book.douban.com/",
}

# 豆瓣分类标签对应的 URL tag
DOUBAN_CATEGORY_TAGS = {
    "心理学": "心理学",
    "自我成长": "个人管理",
    "商业": "商业",
    "沟通": "管理",
    "历史": "历史",
    "哲学": "哲学",
    "科学": "科学",
    "文学": "文学",
    "小说": "小说",
    "经济": "经济学",
    "社会": "社会学",
    "科普": "科普",
}


def fetch_douban_hot(category: str = "", count: int = 20) -> list[dict]:
    """
    从豆瓣获取热门书籍

    使用豆瓣的公开 API 端点（无需登录/API Key）
    """
    tag = DOUBAN_CATEGORY_TAGS.get(category, category)
    params = urllib.parse.urlencode({
        "tag": tag,
        "type": "T",  # T=热门
        "start": 0,
        "count": count,
    })
    url = f"https://book.douban.com/j/search_tags?type=book&tag={urllib.parse.quote(tag)}"

    # 使用豆瓣 tag 搜索 API
    search_url = f"https://book.douban.com/j/search?{params}"

    books = []
    try:
        req = urllib.request.Request(search_url, headers=DOUBAN_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                print(f"  [豆瓣] HTTP {resp.status}，请求失败")
                return []
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        for item in data.get("books", []):
            title = item.get("title", "").strip()
            if not title:
                continue

            # 提取作者（可能有多个）
            author_info = item.get("author_info", "")
            if not author_info:
                # 从 publisher 等字段尝试提取
                author_info = ""

            books.append({
                "title": title,
                "author": author_info or "未知",
                "category": category,
                "description": item.get("abstract", "") or f"豆瓣评分 {item.get('rating', {}).get('value', 'N/A')}",
                "tags": [category] if category else [],
                "douban_url": item.get("url", ""),
                "rating": item.get("rating", {}).get("value", ""),
            })

        print(f"  [豆瓣] 分类「{category}」获取到 {len(books)} 本书")

    except Exception as e:
        print(f"  [豆瓣] 获取失败: {e}")

    return books


def fetch_douban_top250(start: int = 0, count: int = 25) -> list[dict]:
    """从豆瓣 Top 250 获取高分书籍"""
    url = f"https://book.douban.com/top250?start={start}"

    books = []
    try:
        req = urllib.request.Request(url, headers=DOUBAN_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                print(f"  [豆瓣Top250] HTTP {resp.status}，请求失败")
                return []
            html = resp.read().decode("utf-8", errors="replace")

        # 简单正则提取（避免依赖 BeautifulSoup）
        titles = re.findall(r'<a href="https://book.douban.com/subject/\d+/"[^>]*title="([^"]+)"', html)
        ratings = re.findall(r'<span class="rating_nums">([\d.]+)</span>', html)
        infos = re.findall(r'<p class="pl">(.*?)</p>', html)

        for i, title in enumerate(titles[:count]):
            author = ""
            if i < len(infos):
                parts = infos[i].split("/")
                if parts:
                    author = parts[0].strip()

            rating = ratings[i] if i < len(ratings) else ""
            books.append({
                "title": title.strip(),
                "author": author,
                "category": "",
                "description": f"豆瓣 Top250，评分 {rating or 'N/A'}",
                "tags": ["豆瓣Top250"],
                "rating": rating,
            })

        print(f"  [豆瓣Top250] 获取到 {len(books)} 本书")

    except Exception as e:
        print(f"  [豆瓣Top250] 获取失败: {e}")

    return books


# ============================================================
# 来源 2：AI 推荐
# ============================================================

BOOK_RECOMMEND_PROMPT = """我运营一个叫"书籍蒸馏"的抖音账号，定位是把一本书的精华蒸馏成几分钟短视频。

请推荐 {count} 本适合做"书籍蒸馏"内容的{category}类书籍。

要求：
1. 选择信息密度高、有核心金句、能被高效提炼的书
2. 优先选近10年出版的、知名度较高的书
3. 每本书的简介要包含可以被"蒸馏"的核心观点或方法论
4. 避免过于学术或小众的书，要让普通人也能快速吸收

请严格按以下 JSON 格式返回（不要返回其他任何内容）：
[
  {{
    "title": "书名",
    "author": "作者",
    "description": "一句话核心介绍（50-100字，要包含书的核心观点和亮点）",
    "tags": ["标签1", "标签2"]
  }}
]"""


def recommend_books_with_ai(category: str, count: int = 10) -> list[dict]:
    """用 AI 推荐适合做短视频的书籍"""
    prompt = BOOK_RECOMMEND_PROMPT.format(category=category, count=count)

    try:
        if LLM_PROVIDER == "claude":
            result = _call_claude(prompt)
        else:
            result = _call_openai(prompt)

        # 提取 JSON
        json_match = re.search(r'\[.*\]', result, re.DOTALL)
        if json_match:
            try:
                books = json.loads(json_match.group())
            except json.JSONDecodeError as e:
                print(f"  [AI推荐] JSON 解析失败: {e}")
                return []
            if not isinstance(books, list):
                return []
            for book in books:
                book["category"] = category
                if "tags" not in book:
                    book["tags"] = [category]
                elif category not in book["tags"]:
                    book["tags"].insert(0, category)

            print(f"  [AI推荐] 分类「{category}」推荐了 {len(books)} 本书")
            return books

    except Exception as e:
        print(f"  [AI推荐] 失败: {e}")

    return []


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=3000,
    )
    return response.choices[0].message.content.strip()


def _call_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ============================================================
# 自动补充书单
# ============================================================

def auto_fill_books(
    target_count: int = None,
    categories: list[str] = None,
    source: str = "auto",
) -> int:
    """
    自动补充书单

    Args:
        target_count: 要补充多少本（默认用 config 中的 BOOK_LIST_REFILL_COUNT）
        categories: 目标分类（默认用 config 中的 BOOK_TARGET_CATEGORIES）
        source: 来源 "douban" | "ai" | "auto"（auto=先豆瓣后AI）

    Returns:
        实际新增的书籍数量
    """
    target_count = target_count or BOOK_LIST_REFILL_COUNT
    categories = categories or BOOK_TARGET_CATEGORIES

    books = load_book_list()
    existing_titles = get_existing_titles(books)
    next_id = get_next_id(books)

    new_books = []
    category_cycle = categories.copy()
    random.shuffle(category_cycle)

    for category in category_cycle:
        if len(new_books) >= target_count:
            break

        remaining = target_count - len(new_books)
        candidates = []

        # 尝试豆瓣
        if source in ("douban", "auto"):
            candidates = fetch_douban_hot(category, count=remaining + 5)
            time.sleep(1)  # 请求间隔，避免被封

        # 豆瓣不够则用 AI 补充
        if len(candidates) < remaining and source in ("ai", "auto"):
            ai_books = recommend_books_with_ai(category, count=remaining)
            candidates.extend(ai_books)

        # 去重并添加
        for candidate in candidates:
            if len(new_books) >= target_count:
                break
            title = candidate.get("title", "").strip()
            if not title or title in existing_titles:
                continue

            new_book = {
                "id": next_id,
                "title": title,
                "author": candidate.get("author", "未知"),
                "category": candidate.get("category", category),
                "description": candidate.get("description", ""),
                "tags": candidate.get("tags", [category]),
                "status": "pending",
            }
            new_books.append(new_book)
            existing_titles.add(title)
            next_id += 1

    if new_books:
        books.extend(new_books)
        save_book_list(books)
        print(f"\n书单已更新：新增 {len(new_books)} 本，总计 {len(books)} 本")
        for b in new_books:
            print(f"  + 《{b['title']}》 [{b['category']}]")
    else:
        print("未找到新书可添加")

    return len(new_books)


def ensure_enough_books() -> bool:
    """
    检查并确保有足够的待处理书籍。
    这个函数会在 main.py 的流水线中自动调用，
    确保永远有足够的待处理书籍。

    Returns:
        True 表示书单充足
    """
    books = load_book_list()
    pending = count_pending(books)

    if pending >= BOOK_LIST_MIN_PENDING:
        return True

    print(f"\n书单余量不足（剩余 {pending} 本，最少需要 {BOOK_LIST_MIN_PENDING} 本）")
    print("正在自动补充书单...\n")

    added = auto_fill_books()

    # 如果还是没有待处理的书，尝试将已完成的书重置为 pending，实现循环
    if pending + added == 0:
        done_count = sum(1 for b in books if b.get("status") == "done")
        if done_count > 0:
            print(f"无法获取新书，但发现 {done_count} 本已完成的书籍，正在重置状态以进行循环处理...")
            for b in books:
                if b.get("status") == "done":
                    b["status"] = "pending"
            save_book_list(books)
            return True
        else:
            print("警告: 既无法获取新书，也没有已完成的书籍可以重置。")
            return False

    return True



def show_book_stats():
    """显示书单统计信息"""
    books = load_book_list()
    total = len(books)
    pending = sum(1 for b in books if b.get("status") == "pending")
    done = sum(1 for b in books if b.get("status") == "done")
    script_done = sum(1 for b in books if b.get("status") == "script_done")
    error = sum(1 for b in books if b.get("status") == "error")

    print(f"\n{'='*40}")
    print(f"书单统计")
    print(f"{'='*40}")
    print(f"  总计:     {total} 本")
    print(f"  待处理:   {pending} 本")
    print(f"  文案完成: {script_done} 本")
    print(f"  已完成:   {done} 本")
    print(f"  出错:     {error} 本")

    # 按分类统计
    categories = {}
    for b in books:
        cat = b.get("category", "未分类")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n  按分类:")
    for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {cnt} 本")
    print()


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="书单自动采集工具")
    subparsers = parser.add_subparsers(dest="command")

    # fill: 自动补充
    fill_parser = subparsers.add_parser("fill", help="自动补充书单")
    fill_parser.add_argument("--count", type=int, default=10, help="补充数量")
    fill_parser.add_argument(
        "--source", choices=["douban", "ai", "auto"], default="auto",
        help="来源(默认auto)",
    )
    fill_parser.add_argument("--category", type=str, help="指定分类")

    # douban: 从豆瓣获取
    douban_parser = subparsers.add_parser("douban", help="从豆瓣获取热门书")
    douban_parser.add_argument("--category", type=str, default="心理学", help="分类")
    douban_parser.add_argument("--top250", action="store_true", help="获取Top250")
    douban_parser.add_argument("--count", type=int, default=20, help="数量")

    # ai: AI推荐
    ai_parser = subparsers.add_parser("ai", help="用AI推荐书籍")
    ai_parser.add_argument("--category", type=str, default="心理学", help="分类")
    ai_parser.add_argument("--count", type=int, default=10, help="数量")

    # stats: 查看统计
    subparsers.add_parser("stats", help="查看书单统计")

    # clear-done: 清除已完成的书
    subparsers.add_parser("clear-done", help="清除已完成的书（保留pending和error）")

    args = parser.parse_args()

    if args.command == "fill":
        cats = [args.category] if args.category else None
        auto_fill_books(target_count=args.count, categories=cats, source=args.source)

    elif args.command == "douban":
        if args.top250:
            results = fetch_douban_top250(count=args.count)
        else:
            results = fetch_douban_hot(args.category, count=args.count)
        for r in results:
            print(f"  《{r['title']}》 {r.get('author', '')} — {r.get('description', '')[:50]}")

    elif args.command == "ai":
        results = recommend_books_with_ai(args.category, count=args.count)
        for r in results:
            print(f"  《{r['title']}》 {r.get('author', '')} — {r.get('description', '')[:50]}")

    elif args.command == "stats":
        show_book_stats()

    elif args.command == "clear-done":
        books = load_book_list()
        before = len(books)
        books = [b for b in books if b.get("status") in ("pending", "error")]
        save_book_list(books)
        print(f"已清除 {before - len(books)} 本已完成的书，剩余 {len(books)} 本")

    else:
        parser.print_help()
