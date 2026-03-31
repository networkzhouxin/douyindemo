"""
主流程脚本
串联所有模块：文案生成 → 语音合成 → 视频合成 → 自动发布
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from config import BASE_DIR, BGM_SOURCE
from generate_script import (
    generate_script,
    load_book_list,
    save_book_list,
    save_script,
    get_next_pending_book,
)
from generate_voice import generate_voice, clean_text_for_tts
from generate_video import generate_video


def pipeline_single(book: dict, duration: int = 60, publish: bool = False):
    """
    单本书的完整流水线

    Args:
        book: 书籍信息
        duration: 视频时长（秒）
        publish: 是否自动发布
    """
    title = book["title"]
    author = book["author"]
    tags = book.get("tags", [])

    # ===== Step 1: 生成文案 =====
    print(f"\n{'='*50}")
    print(f"[1/3] 正在为《{title}》生成文案...")
    print(f"{'='*50}")
    script = generate_script(book, duration)
    script_path = save_script(book, script)
    print(f"文案已保存: {script_path}")
    print(f"文案字数: {len(script)}")
    print(f"预览: {script[:100]}...")

    # ===== Step 2: 生成语音 =====
    print(f"\n{'='*50}")
    print(f"[2/3] 正在生成语音...")
    print(f"{'='*50}")
    voice_result = generate_voice(
        text=script,
        book_title=title,
        with_subtitles=True,
    )
    print(f"语音文件: {voice_result['voice_path']}")
    if voice_result["subtitle_path"]:
        print(f"字幕文件: {voice_result['subtitle_path']}")

    # ===== Step 3: 合成视频 =====
    print(f"\n{'='*50}")
    print(f"[3/3] 正在合成视频...")
    print(f"{'='*50}")
    video_path = generate_video(
        voice_path=voice_result["voice_path"],
        subtitle_path=voice_result["subtitle_path"],
        book_title=title,
        book_author=author,
        book=book,
        script=script,
    )
    print(f"视频已生成: {video_path}")

    # ===== Step 4: 自动发布（可选） =====
    if publish:
        print(f"\n{'='*50}")
        print(f"[发布] 正在发布到抖音...")
        print(f"{'='*50}")
        from auto_publish import upload_video

        desc = f"《{title}》读书分享"
        all_tags = ["读书", "好书推荐", "书单"] + tags

        # 如果 BGM 来源设置为 douyin，发布时使用抖音平台音乐
        use_douyin_music = BGM_SOURCE == "douyin"

        success = asyncio.run(
            upload_video(
                video_path=video_path,
                title=desc,
                tags=all_tags,
                use_douyin_music=use_douyin_music,
                book=book,
            )
        )
        if success:
            print("发布成功！")
        else:
            print("发布失败，请手动上传")

    return {
        "book": title,
        "script_path": str(script_path),
        "voice_path": str(voice_result["voice_path"]),
        "subtitle_path": str(voice_result["subtitle_path"]) if voice_result["subtitle_path"] else None,
        "video_path": str(video_path),
    }


def pipeline_batch(count: int = 0, duration: int = 60, publish: bool = False):
    """
    批量处理书单

    Args:
        count: 处理数量，0 表示全部
        duration: 视频时长
        publish: 是否自动发布
    """
    books = load_book_list()
    results = []
    processed = 0

    for book in books:
        if book.get("status") != "pending":
            continue
        if count > 0 and processed >= count:
            break

        try:
            result = pipeline_single(book, duration, publish)
            results.append(result)

            # 更新状态
            book["status"] = "done"
            save_book_list(books)
            processed += 1

            print(f"\n>>> 已完成 {processed} 本 <<<\n")

        except Exception as e:
            print(f"\n处理《{book['title']}》时出错: {e}")
            book["status"] = "error"
            save_book_list(books)
            continue

    # 保存执行报告
    if results:
        report_path = BASE_DIR / "output" / "last_run_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n执行报告已保存: {report_path}")

    print(f"\n全部完成！共处理 {processed} 本书。")
    return results


def reset_book_status():
    """重置所有书籍状态为 pending"""
    books = load_book_list()
    for book in books:
        book["status"] = "pending"
    save_book_list(books)
    print(f"已重置 {len(books)} 本书的状态为 pending")


# ============ 命令行入口 ============
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="读书类抖音短视频自动化生产线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py next                    # 处理书单中下一本书
  python main.py batch --count 3         # 批量处理3本
  python main.py batch --all             # 处理所有待处理的书
  python main.py next --publish          # 处理并自动发布
  python main.py batch --all --publish   # 全部处理并发布
  python main.py reset                   # 重置书单状态
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # next: 处理下一本
    next_parser = subparsers.add_parser("next", help="处理书单中下一本待处理的书")
    next_parser.add_argument("--duration", type=int, default=60, help="视频时长(秒)")
    next_parser.add_argument("--publish", action="store_true", help="生成后自动发布")

    # batch: 批量处理
    batch_parser = subparsers.add_parser("batch", help="批量处理书单")
    batch_parser.add_argument("--count", type=int, default=0, help="处理数量(0=全部)")
    batch_parser.add_argument("--all", action="store_true", help="处理所有待处理的书")
    batch_parser.add_argument("--duration", type=int, default=60, help="视频时长(秒)")
    batch_parser.add_argument("--publish", action="store_true", help="生成后自动发布")

    # reset: 重置状态
    subparsers.add_parser("reset", help="重置所有书籍状态为pending")

    args = parser.parse_args()

    if args.command == "next":
        books = load_book_list()
        book = get_next_pending_book(books)
        if book:
            pipeline_single(book, args.duration, args.publish)
            # 更新状态
            for b in books:
                if b["id"] == book["id"]:
                    b["status"] = "done"
            save_book_list(books)
        else:
            print("书单中没有待处理的书了！使用 'python main.py reset' 重置状态。")

    elif args.command == "batch":
        count = 0 if args.all else args.count
        if count == 0 and not args.all:
            print("请指定 --count 或 --all")
            sys.exit(1)
        pipeline_batch(count, args.duration, args.publish)

    elif args.command == "reset":
        reset_book_status()

    else:
        parser.print_help()
