"""
文案生成模块
支持一书多集: AI 先规划选题，再为每个选题生成独立文案
"""

import json
import re
from datetime import datetime
from pathlib import Path

from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    SCRIPT_PROMPT_TEMPLATE,
    TOPIC_PLAN_PROMPT,
    EPISODES_PER_BOOK,
    DEFAULT_DURATION,
    BASE_DIR,
    get_book_output_dir,
)


# ============================================================
# 书单管理
# ============================================================

def load_book_list() -> list[dict]:
    book_list_path = BASE_DIR / "book_list.json"
    if not book_list_path.exists():
        return []
    try:
        with open(book_list_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  书单文件读取失败: {e}")
        return []


def save_book_list(books: list[dict]):
    book_list_path = BASE_DIR / "book_list.json"
    # 原子写入：先写临时文件再重命名，防止写入中途崩溃导致数据丢失
    tmp_path = book_list_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)
    tmp_path.replace(book_list_path)


def get_next_pending_book(books: list[dict]) -> dict | None:
    for book in books:
        if book.get("status") == "pending":
            return book
    return None


# ============================================================
# LLM 调用
# ============================================================

def _call_llm(prompt: str, system: str = "", max_tokens: int = 2000) -> str:
    try:
        if LLM_PROVIDER == "claude":
            import anthropic
            client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        else:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.8,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败({LLM_PROVIDER}): {e}") from e


# ============================================================
# 选题规划: 为一本书生成多个视频选题
# ============================================================

def plan_topics(book: dict, episode_count: int = None) -> list[dict]:
    """
    AI 分析一本书，规划多个视频选题

    Returns:
        [{"episode": 1, "title": "...", "angle": "...", "type": "...", "key_points": "..."}, ...]
    """
    episode_count = episode_count or EPISODES_PER_BOOK

    prompt = TOPIC_PLAN_PROMPT.format(
        book_title=book["title"],
        book_desc=book["description"],
        episode_count=episode_count,
    )

    result = _call_llm(
        prompt,
        system="你是一个专业的短视频内容策划师，擅长从书籍中挖掘多个有话题性的选题。",
        max_tokens=3000,
    )

    # 提取 JSON
    json_match = re.search(r'\[.*\]', result, re.DOTALL)
    if json_match:
        try:
            topics = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"AI 返回的 JSON 格式错误: {e}\n原文: {result[:300]}") from e
        if not isinstance(topics, list) or not topics:
            raise ValueError(f"AI 返回的选题为空或格式不正确: {result[:200]}")
        # 确保 episode 编号正确
        for i, topic in enumerate(topics):
            topic["episode"] = i + 1
        return topics

    raise ValueError(f"AI 返回的选题格式无法解析: {result[:200]}")


def save_topic_plan(book: dict, topics: list[dict], output_dir: Path = None) -> Path:
    """保存选题规划到书籍目录"""
    if output_dir is None:
        output_dir = get_book_output_dir(book["title"])

    filepath = output_dir / "topic_plan.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "book_title": book["title"],
            "book_author": book["author"],
            "total_episodes": len(topics),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topics": topics,
        }, f, ensure_ascii=False, indent=2)

    return filepath


def load_topic_plan(book_title: str) -> list[dict] | None:
    """加载已有的选题规划"""
    book_dir = get_book_output_dir(book_title)
    filepath = book_dir / "topic_plan.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("topics", [])
    return None


# ============================================================
# 单集文案生成
# ============================================================

def generate_script(book: dict, duration: int = DEFAULT_DURATION, episode: dict = None) -> str:
    """
    为指定书籍的某一集生成文案

    Args:
        book: 书籍信息
        duration: 视频时长(秒)
        episode: 选题信息(不传则生成通用文案)
    """
    word_count = duration * 4

    if episode:
        prompt = SCRIPT_PROMPT_TEMPLATE.format(
            book_title=book["title"],
            book_desc=book["description"],
            episode_title=episode.get("title", ""),
            episode_angle=episode.get("angle", ""),
            episode_type=episode.get("type", ""),
            episode_key_points=episode.get("key_points", ""),
            duration=duration,
            word_count=word_count,
        )
    else:
        # 兼容旧的单集模式
        prompt = SCRIPT_PROMPT_TEMPLATE.format(
            book_title=book["title"],
            book_desc=book["description"],
            episode_title="核心观点解读",
            episode_angle="提炼全书最核心的2-3个观点",
            episode_type="核心观点",
            episode_key_points=book["description"],
            duration=duration,
            word_count=word_count,
        )

    return _call_llm(
        prompt,
        system="你是一个专业的短视频文案创作者，擅长将书籍内容转化为引人入胜的口播文案。",
        max_tokens=1000,
    )


def save_script(book: dict, script: str, output_dir: Path = None, episode: dict = None) -> Path:
    """保存文案到对应目录"""
    if output_dir is None:
        output_dir = get_book_output_dir(book["title"])

    filepath = output_dir / "script.txt"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"书名: {book['title']}\n")
        f.write(f"作者: {book['author']}\n")
        f.write(f"分类: {book['category']}\n")
        if episode:
            f.write(f"第 {episode.get('episode', '?')} 集: {episode.get('title', '')}\n")
            f.write(f"选题类型: {episode.get('type', '')}\n")
            f.write(f"切入角度: {episode.get('angle', '')}\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 40 + "\n\n")
        f.write(script)

    return filepath


# ============================================================
# 一书多集: 批量生成
# ============================================================

def generate_all_episodes(
    book: dict,
    episode_count: int = None,
    duration: int = DEFAULT_DURATION,
) -> list[dict]:
    """
    为一本书生成全部集数的文案

    流程: 规划选题 -> 逐集生成文案 -> 保存

    Returns:
        [{"episode": dict, "script": str, "output_dir": Path}, ...]
    """
    episode_count = episode_count or EPISODES_PER_BOOK
    if episode_count <= 0:
        raise ValueError(f"集数必须为正整数，收到: {episode_count}")
    book_dir = get_book_output_dir(book["title"])

    # Step 1: 规划选题(或加载已有规划)
    topics = load_topic_plan(book["title"])
    if topics and len(topics) >= episode_count:
        print(f"  使用已有选题规划({len(topics)} 个选题)")
    else:
        print(f"  正在为《{book['title']}》规划 {episode_count} 个选题...")
        topics = plan_topics(book, episode_count)
        save_topic_plan(book, topics, book_dir)
        print(f"  选题规划完成:")
        for t in topics:
            print(f"    EP{t['episode']:02d} [{t.get('type','')}] {t['title']}")

    # Step 2: 逐集生成文案
    results = []
    for topic in topics[:episode_count]:
        ep_num = topic["episode"]
        safe_title = re.sub(r'[\\/:*?"<>|]', '', topic.get("title", ""))[:20]
        ep_dir = book_dir / f"ep{ep_num:02d}_{safe_title}"
        ep_dir.mkdir(parents=True, exist_ok=True)

        # 检查是否已有文案
        script_file = ep_dir / "script.txt"
        if script_file.exists():
            print(f"  EP{ep_num:02d} 文案已存在，跳过")
            script = script_file.read_text(encoding="utf-8")
            # 提取正文(去掉头部信息)
            if "-" * 40 in script:
                script = script.split("-" * 40, 1)[-1].strip()
            results.append({"episode": topic, "script": script, "output_dir": ep_dir})
            continue

        print(f"  EP{ep_num:02d} 正在生成文案: {topic['title']}...")
        script = generate_script(book, duration, episode=topic)
        save_script(book, script, output_dir=ep_dir, episode=topic)
        print(f"    字数: {len(script)}")

        results.append({"episode": topic, "script": script, "output_dir": ep_dir})

    return results


def get_pending_episodes(book: dict) -> list[dict]:
    """
    获取一本书中尚未生成视频的集数

    通过检查每集目录下是否存在 video.mp4 来判断
    """
    book_dir = get_book_output_dir(book["title"])

    # 加载选题规划
    topics = load_topic_plan(book["title"])
    if not topics:
        return []

    pending = []
    for topic in topics:
        ep_num = topic["episode"]
        safe_title = re.sub(r'[\\/:*?"<>|]', '', topic.get("title", ""))[:20]
        ep_dir = book_dir / f"ep{ep_num:02d}_{safe_title}"

        if not (ep_dir / "video.mp4").exists():
            pending.append({**topic, "_output_dir": ep_dir})

    return pending


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="书籍蒸馏 - 短视频文案生成器")
    parser.add_argument("--book", type=str, help="指定书名")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help=f"视频时长(秒，默认{DEFAULT_DURATION})")
    parser.add_argument("--episodes", type=int, help=f"生成集数(默认{EPISODES_PER_BOOK})")
    parser.add_argument("--plan-only", action="store_true", help="只生成选题规划，不生成文案")
    args = parser.parse_args()

    if args.book:
        books = load_book_list()
        target = next((b for b in books if b["title"] == args.book), None)
        if not target:
            print(f"书单中没有找到《{args.book}》")
        elif args.plan_only:
            topics = plan_topics(target, args.episodes)
            for t in topics:
                print(f"  EP{t['episode']:02d} [{t.get('type','')}] {t['title']}")
                print(f"         {t.get('angle', '')}")
        else:
            results = generate_all_episodes(target, args.episodes, args.duration)
            print(f"\n完成! 共生成 {len(results)} 集文案")
    else:
        books = load_book_list()
        book = get_next_pending_book(books)
        if book:
            results = generate_all_episodes(book, args.episodes, args.duration)
            print(f"\n完成! 共生成 {len(results)} 集文案")
        else:
            print("书单中没有待处理的书了!")
