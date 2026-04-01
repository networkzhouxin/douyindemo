"""
主流程脚本
一书多集全自动流水线:
  书单采集 -> 选题规划(N个角度) -> 逐集生成(文案/语音/视频) -> 自动发布
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from config import BASE_DIR, BGM_SOURCE, EPISODES_PER_BOOK, get_book_output_dir
from generate_script import (
    generate_all_episodes,
    get_pending_episodes,
    load_book_list,
    save_book_list,
    get_next_pending_book,
    plan_topics,
    save_topic_plan,
    load_topic_plan,
)
from generate_voice import generate_voice
from generate_video import generate_video


def _ensure_books():
    """确保书单有足够的待处理书籍"""
    try:
        from book_crawler import ensure_enough_books
        ensure_enough_books()
    except Exception as e:
        print(f"  书单自动补充失败: {e}")


def pipeline_episode(
    book: dict,
    episode: dict,
    ep_dir: Path,
    script: str,
    duration: int = 60,
    publish: bool = False,
) -> dict:
    """
    单集流水线: 文案 -> 语音 -> 视频 -> (发布)

    Args:
        book: 书籍信息
        episode: 选题信息
        ep_dir: 本集输出目录
        script: 已生成的文案
        duration: 视频时长
        publish: 是否自动发布
    """
    title = book["title"]
    author = book["author"]
    tags = book.get("tags", [])
    ep_num = episode.get("episode", 1)
    ep_title = episode.get("title", "")

    # 检查是否已有视频
    if (ep_dir / "video.mp4").exists():
        print(f"  EP{ep_num:02d} 视频已存在，跳过")
        return {"episode": ep_num, "video_path": str(ep_dir / "video.mp4"), "skipped": True}

    # ===== 语音 =====
    print(f"  EP{ep_num:02d} 生成语音...")
    voice_result = generate_voice(
        text=script,
        book_title=title,
        with_subtitles=True,
        output_dir=ep_dir,
    )

    # ===== 视频 =====
    print(f"  EP{ep_num:02d} 合成视频...")
    video_path = generate_video(
        voice_path=voice_result["voice_path"],
        subtitle_path=voice_result["subtitle_path"],
        book_title=title,
        book_author=author,
        book=book,
        script=script,
    )

    print(f"  EP{ep_num:02d} 完成 -> {video_path}")

    # ===== 发布(可选，带风控) =====
    if publish:
        from auto_publish import upload_video
        from safety import pre_publish_check, random_publish_interval

        desc = f"《{title}》{ep_title}"
        all_tags = ["读书", "好书推荐"] + tags
        use_douyin_music = BGM_SOURCE == "douyin"

        # 风控: 发布前检查
        passed, msg = pre_publish_check(desc, script)
        if not passed:
            print(f"  EP{ep_num:02d} [风控] 跳过发布: {msg}")
        else:
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
                print(f"  EP{ep_num:02d} 发布成功!")
            else:
                print(f"  EP{ep_num:02d} 发布失败，请手动上传")

    return {
        "episode": ep_num,
        "title": ep_title,
        "video_path": str(video_path),
        "voice_path": str(voice_result["voice_path"]),
    }


def pipeline_book(
    book: dict,
    episode_count: int = None,
    duration: int = 60,
    publish: bool = False,
) -> list[dict]:
    """
    一本书的完整流水线(多集)

    流程:
    1. 规划选题(N个角度)
    2. 逐集生成文案
    3. 逐集生成语音+视频
    """
    episode_count = episode_count or EPISODES_PER_BOOK
    title = book["title"]

    print(f"\n{'#'*60}")
    print(f"  《{title}》 - 计划生成 {episode_count} 集")
    print(f"{'#'*60}")

    # Step 1+2: 规划选题 + 生成文案
    print(f"\n[选题+文案]")
    episodes = generate_all_episodes(book, episode_count, duration)

    # Step 3: 逐集生成语音+视频
    results = []
    for ep_data in episodes:
        episode = ep_data["episode"]
        script = ep_data["script"]
        ep_dir = ep_data["output_dir"]
        ep_num = episode.get("episode", 1)

        print(f"\n[EP{ep_num:02d}/{episode_count}] {episode.get('title', '')}")

        try:
            result = pipeline_episode(book, episode, ep_dir, script, duration, publish)
            results.append(result)
        except Exception as e:
            print(f"  EP{ep_num:02d} 出错: {e}")
            results.append({"episode": ep_num, "error": str(e)})
            continue

    # 保存报告
    book_dir = get_book_output_dir(title)
    report_path = book_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "book": title,
            "total_episodes": episode_count,
            "completed": sum(1 for r in results if "error" not in r and not r.get("skipped")),
            "skipped": sum(1 for r in results if r.get("skipped")),
            "errors": sum(1 for r in results if "error" in r),
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    completed = sum(1 for r in results if "error" not in r)
    print(f"\n《{title}》完成! {completed}/{episode_count} 集")

    return results


def pipeline_auto(
    book_count: int = 1,
    episode_count: int = None,
    duration: int = 60,
    publish: bool = False,
):
    """
    全自动模式: 自动采集书单 -> 一书多集全流程
    """
    episode_count = episode_count or EPISODES_PER_BOOK

    print("=" * 60)
    print(f"全自动模式: {book_count} 本书 x {episode_count} 集/本 = {book_count * episode_count} 条视频")
    print("=" * 60)

    all_results = []
    for i in range(book_count):
        _ensure_books()

        books = load_book_list()
        book = get_next_pending_book(books)
        if not book:
            print("书单已空，结束")
            break

        results = pipeline_book(book, episode_count, duration, publish)
        all_results.append({"book": book["title"], "results": results})

        # 更新状态
        for b in books:
            if b["id"] == book["id"]:
                b["status"] = "done"
        save_book_list(books)

        print(f"\n>>> 已完成 {i+1}/{book_count} 本 <<<")

    # 总报告
    total_videos = sum(
        sum(1 for r in item["results"] if "error" not in r)
        for item in all_results
    )
    print(f"\n{'='*60}")
    print(f"全部完成! {len(all_results)} 本书，共 {total_videos} 条视频")
    print(f"{'='*60}")

    return all_results


def reset_book_status():
    books = load_book_list()
    for book in books:
        book["status"] = "pending"
    save_book_list(books)
    print(f"已重置 {len(books)} 本书的状态为 pending")


# ============ 命令行入口 ============
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="读书类抖音短视频 - 一书多集自动化生产线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py auto                          # 1本书 x 5集 = 5条视频
  python main.py auto --books 3                # 3本书 x 5集 = 15条视频
  python main.py auto --books 2 --episodes 8   # 2本书 x 8集 = 16条视频
  python main.py auto --books 1 --publish      # 生成并自动发布
  python main.py book "被讨厌的勇气"            # 指定一本书生成全部集数
  python main.py book "被讨厌的勇气" --episodes 10  # 指定生成10集
  python main.py plan "认知觉醒"                # 只看选题规划，不生成视频
  python main.py fill                           # 只补充书单
  python main.py stats                          # 查看统计
  python main.py reset                          # 重置书单状态
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # auto: 全自动模式
    auto_parser = subparsers.add_parser("auto", help="全自动(采集+规划+生成+发布)")
    auto_parser.add_argument("--books", type=int, default=1, help="处理几本书(默认1)")
    auto_parser.add_argument("--episodes", type=int, default=None, help=f"每本书几集(默认{EPISODES_PER_BOOK})")
    auto_parser.add_argument("--duration", type=int, default=60, help="视频时长(秒)")
    auto_parser.add_argument("--publish", action="store_true", help="自动发布")

    # book: 指定一本书
    book_parser = subparsers.add_parser("book", help="为指定书生成全部集数")
    book_parser.add_argument("title", type=str, help="书名")
    book_parser.add_argument("--episodes", type=int, default=None, help="集数")
    book_parser.add_argument("--duration", type=int, default=60, help="视频时长(秒)")
    book_parser.add_argument("--publish", action="store_true", help="自动发布")

    # plan: 只看选题规划
    plan_parser = subparsers.add_parser("plan", help="查看/生成选题规划(不生成视频)")
    plan_parser.add_argument("title", type=str, help="书名")
    plan_parser.add_argument("--episodes", type=int, default=None, help="规划几个选题")

    # fill: 补充书单
    fill_parser = subparsers.add_parser("fill", help="自动补充书单")
    fill_parser.add_argument("--count", type=int, default=10, help="补充数量")
    fill_parser.add_argument("--source", choices=["douban", "ai", "auto"], default="auto")
    fill_parser.add_argument("--category", type=str, help="指定分类")

    # stats: 统计
    subparsers.add_parser("stats", help="查看书单和产出统计")

    # reset
    subparsers.add_parser("reset", help="重置书单状态")

    args = parser.parse_args()

    if args.command == "auto":
        pipeline_auto(
            book_count=args.books,
            episode_count=args.episodes,
            duration=args.duration,
            publish=args.publish,
        )

    elif args.command == "book":
        books = load_book_list()
        target = next((b for b in books if b["title"] == args.title), None)
        if not target:
            # 如果书单里没有，创建一个临时条目
            target = {
                "id": 0,
                "title": args.title,
                "author": "未知",
                "category": "",
                "description": f"《{args.title}》",
                "tags": [],
            }
            print(f"书单中没有《{args.title}》，使用简要信息生成")
        pipeline_book(target, args.episodes, args.duration, args.publish)

    elif args.command == "plan":
        books = load_book_list()
        target = next((b for b in books if b["title"] == args.title), None)
        if not target:
            target = {"title": args.title, "description": f"《{args.title}》", "author": "未知", "category": ""}
        # 先检查已有规划
        existing = load_topic_plan(args.title)
        if existing:
            print(f"\n《{args.title}》已有选题规划:")
            for t in existing:
                print(f"  EP{t['episode']:02d} [{t.get('type','')}] {t['title']}")
                print(f"        {t.get('angle', '')}")
            print(f"\n(重新规划请先删除 output/{args.title}/topic_plan.json)")
        else:
            topics = plan_topics(target, args.episodes)
            save_topic_plan(target, topics)
            print(f"\n《{args.title}》选题规划({len(topics)} 集):")
            for t in topics:
                print(f"  EP{t['episode']:02d} [{t.get('type','')}] {t['title']}")
                print(f"        {t.get('angle', '')}")
                print(f"        要点: {t.get('key_points', '')}")

    elif args.command == "fill":
        from book_crawler import auto_fill_books
        cats = [args.category] if args.category else None
        auto_fill_books(target_count=args.count, categories=cats, source=args.source)

    elif args.command == "stats":
        from book_crawler import show_book_stats
        show_book_stats()

        # 额外显示产出统计
        import os
        output_dir = BASE_DIR / "output"
        if output_dir.exists():
            video_count = 0
            book_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
            for bd in book_dirs:
                ep_dirs = [d for d in bd.iterdir() if d.is_dir() and d.name.startswith("ep")]
                for ep in ep_dirs:
                    if (ep / "video.mp4").exists():
                        video_count += 1
            print(f"\n  产出统计:")
            print(f"    已处理书籍: {len(book_dirs)} 本")
            print(f"    已生成视频: {video_count} 条")

        # 发布统计
        from safety import show_publish_stats
        show_publish_stats()

    elif args.command == "reset":
        reset_book_status()

    else:
        parser.print_help()
