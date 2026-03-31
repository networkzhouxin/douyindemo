"""
文案生成模块
调用 AI API 自动生成读书类短视频文案
"""

import json
import os
from datetime import datetime
from pathlib import Path

from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    SCRIPTS_DIR,
    SCRIPT_PROMPT_TEMPLATE,
    BASE_DIR,
)


def load_book_list() -> list[dict]:
    """读取书单数据库"""
    book_list_path = BASE_DIR / "book_list.json"
    with open(book_list_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_book_list(books: list[dict]):
    """保存书单数据库"""
    book_list_path = BASE_DIR / "book_list.json"
    with open(book_list_path, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)


def get_next_pending_book(books: list[dict]) -> dict | None:
    """获取下一本待处理的书"""
    for book in books:
        if book.get("status") == "pending":
            return book
    return None


def build_prompt(book: dict, duration: int = 60) -> str:
    """根据书籍信息构建 Prompt"""
    word_count = duration * 4  # 每秒约4个字
    return SCRIPT_PROMPT_TEMPLATE.format(
        book_title=book["title"],
        book_desc=book["description"],
        duration=duration,
        word_count=word_count,
    )


def generate_with_openai(prompt: str) -> str:
    """使用 OpenAI 兼容接口生成文案"""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "你是一个专业的短视频文案创作者，擅长将书籍内容转化为引人入胜的口播文案。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()


def generate_with_claude(prompt: str) -> str:
    """使用 Claude API 生成文案"""
    import anthropic

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1000,
        system="你是一个专业的短视频文案创作者，擅长将书籍内容转化为引人入胜的口播文案。",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_script(book: dict, duration: int = 60) -> str:
    """
    为指定书籍生成文案

    Args:
        book: 书籍信息字典
        duration: 视频时长（秒）

    Returns:
        生成的文案文本
    """
    prompt = build_prompt(book, duration)

    if LLM_PROVIDER == "claude":
        script = generate_with_claude(prompt)
    else:
        script = generate_with_openai(prompt)

    return script


def save_script(book: dict, script: str) -> Path:
    """
    保存文案到文件

    Returns:
        文案文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = book["title"].replace(" ", "_").replace("/", "_")
    filename = f"{safe_title}_{timestamp}.txt"
    filepath = SCRIPTS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"书名：{book['title']}\n")
        f.write(f"作者：{book['author']}\n")
        f.write(f"分类：{book['category']}\n")
        f.write(f"标签：{', '.join(book['tags'])}\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 40 + "\n\n")
        f.write(script)

    return filepath


def process_next_book(duration: int = 60) -> dict | None:
    """
    处理书单中下一本待处理的书：生成文案并保存

    Returns:
        包含 book, script, filepath 的字典，或 None（无待处理的书）
    """
    books = load_book_list()
    book = get_next_pending_book(books)

    if not book:
        print("书单中没有待处理的书了！")
        return None

    print(f"正在为《{book['title']}》生成文案...")
    script = generate_script(book, duration)
    filepath = save_script(book, script)

    # 更新书单状态
    for b in books:
        if b["id"] == book["id"]:
            b["status"] = "script_done"
            break
    save_book_list(books)

    print(f"文案已保存到：{filepath}")
    print(f"文案字数：{len(script)}")
    return {"book": book, "script": script, "filepath": filepath}


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="读书类短视频文案生成器")
    parser.add_argument("--book", type=str, help="指定书名（不指定则自动取书单中下一本）")
    parser.add_argument("--duration", type=int, default=60, help="视频时长（秒），默认60")
    parser.add_argument("--all", action="store_true", help="批量生成所有待处理书籍的文案")
    args = parser.parse_args()

    if args.all:
        count = 0
        while True:
            result = process_next_book(args.duration)
            if result is None:
                break
            count += 1
            print(f"--- 已完成 {count} 本 ---\n")
        print(f"全部完成！共生成 {count} 篇文案。")
    elif args.book:
        books = load_book_list()
        target = None
        for b in books:
            if b["title"] == args.book:
                target = b
                break
        if target:
            script = generate_script(target, args.duration)
            filepath = save_script(target, script)
            print(f"文案已保存到：{filepath}")
        else:
            print(f"书单中没有找到《{args.book}》")
    else:
        process_next_book(args.duration)
