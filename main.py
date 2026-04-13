"""
主流程脚本
一书多集全自动流水线:
  书单采集 -> 选题规划(N个角度) -> 逐集生成(文案/语音/视频) -> 自动发布
"""

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path

# ============ 提前解析动态参数 ============
# 必须在导入 config 之前拦截参数，以确保环境变量生效
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--voice-sample", type=str, help="指定使用的语音样本文件夹名称 (assets/voice_sample/ 下)")
_args, _ = _parser.parse_known_args()
if _args.voice_sample:
    os.environ["VOICE_SAMPLE_NAME"] = _args.voice_sample

from config import BASE_DIR, BGM_SOURCE, DEFAULT_DURATION, EPISODES_PER_BOOK, get_book_output_dir, validate_config
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
    duration: int = DEFAULT_DURATION,
    publish: bool = False,
    only_voice: bool = False,
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
        only_voice: 是否只生成语音(跳过视频合成)
    """
    title = book["title"]
    author = book["author"]
    tags = book.get("tags", [])
    ep_num = episode.get("episode", 1)
    ep_title = episode.get("title", "")

    # 检查是否已有视频
    if not only_voice and (ep_dir / "video.mp4").exists():
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

    if only_voice:
        print(f"  EP{ep_num:02d} [已开启仅生成语音] 跳过视频合成")
        return {
            "episode": ep_num,
            "title": ep_title,
            "voice_path": str(voice_result["voice_path"]),
            "video_skipped": True
        }

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
        all_tags = ["书籍蒸馏", "读书", "好书推荐"] + tags
        use_douyin_music = BGM_SOURCE == "douyin"

        # 风控: 发布前检查
        passed, msg = pre_publish_check(desc, script)
        if not passed:
            print(f"  EP{ep_num:02d} [风控] 跳过发布: {msg}")
        else:
            try:
                # 兼容已有事件循环（如在 Jupyter 等环境中调用）
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        success = pool.submit(
                            asyncio.run,
                            upload_video(
                                video_path=video_path,
                                title=desc,
                                tags=all_tags,
                                use_douyin_music=use_douyin_music,
                                book=book,
                            )
                        ).result()
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
            except Exception as e:
                print(f"  EP{ep_num:02d} 发布出错: {e}")

    return {
        "episode": ep_num,
        "title": ep_title,
        "video_path": str(video_path),
        "voice_path": str(voice_result["voice_path"]),
    }


def pipeline_book(
    book: dict,
    episode_count: int = None,
    duration: int = DEFAULT_DURATION,
    publish: bool = False,
    only_voice: bool = False,
    read_only: bool = False,
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
    print(f"  《{title}》 - 计划生成 {1 if read_only else episode_count} 集")
    print(f"{'#'*60}")

    if read_only:
        print(f"\n[纯读模式] 跳过选题规划和 AI 文案生成，直接朗读原文...")
        episodes = [
            {
                "episode": 1,
                "title": title,
                "script": book.get("description", f"《{title}》"),
                "output_dir": get_book_output_dir(title) / "ep01_原文朗读"
            }
        ]
        # 确保输出目录存在
        episodes[0]["output_dir"].mkdir(parents=True, exist_ok=True)
    else:
        # Step 1+2: 规划选题 + 生成文案
        print(f"\n[选题+文案]")
        episodes = generate_all_episodes(book, episode_count, duration)

    # Step 3: 逐集生成语音+视频
    results = []
    for ep_data in episodes:
        episode = ep_data["episode"]
        script = ep_data["script"]
        ep_dir = ep_data["output_dir"]
        # 对于 read_only 模式，我们构造的 episode 字典里可能没有完整字段，做一下兼容
        if isinstance(episode, int):
            ep_num = episode
            episode_dict = {"episode": ep_num, "title": ep_data.get("title", title)}
        else:
            ep_num = episode.get("episode", 1)
            episode_dict = episode

        print(f"\n[EP{ep_num:02d}/{len(episodes)}] {episode_dict.get('title', '')}")

        try:
            result = pipeline_episode(book, episode_dict, ep_dir, script, duration, publish, only_voice)
            results.append(result)
        except Exception as e:
            print(f"  EP{ep_num:02d} 出错: {e}")
            results.append({"episode": ep_num, "error": str(e)})
            continue

    # 保存报告
    completed = sum(1 for r in results if "error" not in r and not r.get("skipped"))
    skipped = sum(1 for r in results if r.get("skipped"))
    errors = sum(1 for r in results if "error" in r)
    try:
        book_dir = get_book_output_dir(title)
        report_path = book_dir / "report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "book": title,
                "total_episodes": len(episodes),
                "completed": completed,
                "skipped": skipped,
                "errors": errors,
                "results": results,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  报告保存失败: {e}")

    print(f"\n《{title}》完成! {completed}/{len(episodes)} 集(跳过{skipped},失败{errors})")

    return results


def pipeline_auto(
    book_count: int = 1,
    episode_count: int = None,
    duration: int = DEFAULT_DURATION,
    publish: bool = False,
    only_voice: bool = False,
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

        results = pipeline_book(book, episode_count, duration, publish, only_voice)
        all_results.append({"book": book["title"], "results": results})

        # 更新状态
        for b in books:
            if b["id"] == book["id"]:
                b["status"] = "done"
        try:
            save_book_list(books)
        except Exception as e:
            print(f"  书单状态保存失败: {e}")

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
        description="书籍蒸馏 - 一书多集自动化生产线（把一本书蒸馏成精华短视频）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py auto                          # 1本书 x 5集 = 5条视频
  python main.py auto --books 3                # 3本书 x 5集 = 15条视频
  python main.py auto --books 2 --episodes 8   # 2本书 x 8集 = 16条视频
  python main.py auto --books 1 --publish      # 生成并自动发布
  python main.py auto --voice-sample calm      # 指定声音样本
  python main.py book "被讨厌的勇气"            # 指定一本书生成全部集数
  python main.py book "被讨厌的勇气" --only-voice   # 只生成语音不合成视频
  python main.py book "被讨厌的勇气" --episodes 10  # 指定生成10集
  python main.py plan "认知觉醒"                # 只看选题规划，不生成视频
  python main.py fill                           # 只补充书单
  python main.py stats                          # 查看统计
  python main.py reset                          # 重置书单状态
        """
    )

    # 提取公共参数的函数
    def add_shared_args(p):
        p.add_argument("--voice-sample", type=str, help="指定使用的语音样本文件夹名称 (assets/voice_sample/ 下)")
        p.add_argument("--only-voice", action="store_true", help="仅生成文案和语音，跳过视频合成和发布")

    subparsers = parser.add_subparsers(dest="command")

    # auto: 全自动模式
    auto_parser = subparsers.add_parser("auto", help="全自动(采集+规划+生成+发布)")
    auto_parser.add_argument("--books", type=int, default=1, help="处理几本书(默认1)")
    auto_parser.add_argument("--episodes", type=int, default=None, help=f"每本书几集(默认{EPISODES_PER_BOOK})")
    auto_parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help=f"视频时长(秒，默认{DEFAULT_DURATION})")
    auto_parser.add_argument("--publish", action="store_true", help="自动发布")
    add_shared_args(auto_parser)

    # book: 指定一本书
    book_parser = subparsers.add_parser("book", help="为指定书生成全部集数")
    book_parser.add_argument("title", type=str, help="书名")
    book_parser.add_argument("--author", type=str, default="未知", help="作者 (当书单中没有此书时有效)")
    book_parser.add_argument("--desc", type=str, default="", help="书籍简介 (当书单中没有此书时有效，提供简介能让AI写出更准确的文案)")
    book_parser.add_argument("--episodes", type=int, default=None, help="集数")
    book_parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help=f"视频时长(秒，默认{DEFAULT_DURATION})")
    book_parser.add_argument("--publish", action="store_true", help="自动发布")
    book_parser.add_argument("--read-only", action="store_true", help="纯读模式：跳过AI文案生成，直接朗读原文(通过 --desc 传入内容)")
    add_shared_args(book_parser)

    # plan: 只看选题规划
    plan_parser = subparsers.add_parser("plan", help="查看/生成选题规划(不生成视频)")
    plan_parser.add_argument("title", type=str, help="书名")
    plan_parser.add_argument("--episodes", type=int, default=None, help="规划几个选题")
    add_shared_args(plan_parser)

    # fill: 补充书单
    fill_parser = subparsers.add_parser("fill", help="自动补充书单")
    fill_parser.add_argument("--count", type=int, default=10, help="补充数量")
    fill_parser.add_argument("--source", choices=["douban", "ai", "auto"], default="auto")
    fill_parser.add_argument("--category", type=str, help="指定分类")
    add_shared_args(fill_parser)

    # stats: 统计
    stats_parser = subparsers.add_parser("stats", help="查看书单和产出统计")
    add_shared_args(stats_parser)

    # reset
    reset_parser = subparsers.add_parser("reset", help="重置书单状态")
    add_shared_args(reset_parser)

    # 兜底解析全局参数
    parser.add_argument("--voice-sample", type=str, help="指定使用的语音样本文件夹名称")
    parser.add_argument("--only-voice", action="store_true", help="仅生成语音")

    args = parser.parse_args()

    # 启动配置校验
    config_warnings = validate_config()
    if config_warnings:
        print("\n[配置警告]")
        for w in config_warnings:
            print(f"  ⚠ {w}")
        print()

    # 如果在子解析器中没有获取到，尝试从主解析器获取
    only_voice = getattr(args, "only_voice", False)
    publish = getattr(args, "publish", False) and not only_voice

    if args.command == "auto":
        pipeline_auto(
            book_count=args.books,
            episode_count=args.episodes,
            duration=args.duration,
            publish=publish,
            only_voice=only_voice,
        )

    elif args.command == "book":
        if not args.title.strip():
            print("错误: 书名不能为空")
            sys.exit(1)
        books = load_book_list()
        target = next((b for b in books if b["title"] == args.title), None)
        
        is_read_only = getattr(args, "read_only", False)
        # 如果是纯读模式，强制开启 only_voice (不生成视频)
        final_only_voice = only_voice or is_read_only
        
        if not target:
            desc = args.desc
            author = args.author
            
            # 如果没有提供描述，尝试使用 AI 自动查询该书的信息
            if not desc:
                print(f"书单中没有《{args.title}》，正在使用 AI 自动查询书籍信息...")
                try:
                    from book_crawler import BOOK_RECOMMEND_PROMPT, _call_openai, _call_claude
                    from config import LLM_PROVIDER
                    
                    if is_read_only:
                        query_prompt = f"请提供《{args.title}》的作者和完整的原文内容（不要任何解析，只要原文）。\n请严格按以下 JSON 格式返回：\n{{\"author\": \"作者\", \"description\": \"完整的原文内容\"}}"
                    else:
                        query_prompt = f"请提供《{args.title}》这本书的作者和一句话核心简介（50-100字，包含核心观点）。如果这是一首著名的诗词（如《清平乐·六盘山》），请提供作者和该诗词的核心赏析或创作背景。\n请严格按以下 JSON 格式返回：\n{{\"author\": \"作者\", \"description\": \"简介\"}}"
                    
                    if LLM_PROVIDER == "claude":
                        result = _call_claude(query_prompt)
                    else:
                        result = _call_openai(query_prompt)
                        
                    import re
                    json_match = re.search(r'\{.*\}', result, re.DOTALL)
                    if json_match:
                        info = json.loads(json_match.group())
                        if author == "未知":
                            author = info.get("author", "未知")
                        desc = info.get("description", f"《{args.title}》")
                        print(f"  -> 查询成功: 作者: {author}")
                except Exception as e:
                    print(f"  -> AI 查询失败 ({e})，将使用默认简要信息。")
                    desc = f"《{args.title}》"
            else:
                desc = args.desc if args.desc else f"《{args.title}》"

            target = {
                "id": 0,
                "title": args.title,
                "author": author,
                "category": "",
                "description": desc,
                "tags": [],
            }
            print(f"将使用以下信息生成: (作者: {target['author']}, 简介: {desc[:30]}...)")
        pipeline_book(target, args.episodes, args.duration, publish, final_only_voice, is_read_only)

    elif args.command == "plan":
        if not args.title.strip():
            print("错误: 书名不能为空")
            sys.exit(1)
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
