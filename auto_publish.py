"""
自动发布模块
使用 Playwright 自动上传视频到抖音创作者平台

内置风控策略:
- 发布前敏感词检测
- 每日发布上限
- 操作间隔随机化(模拟人类)
- 连续发布后自动休息
- 跨平台标题差异化
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path

from config import (
    DOUYIN_COOKIE_PATH,
    VIDEOS_DIR,
    ACTION_DELAY_MIN,
    ACTION_DELAY_MAX,
)


async def save_cookies(page, cookie_path: Path = DOUYIN_COOKIE_PATH):
    """保存浏览器 Cookie"""
    cookies = await page.context.cookies()
    with open(cookie_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"Cookie 已保存到 {cookie_path}")


async def load_cookies(context, cookie_path: Path = DOUYIN_COOKIE_PATH):
    """加载已保存的 Cookie"""
    if not cookie_path.exists():
        return False
    try:
        with open(cookie_path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        return True
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Cookie 文件损坏: {e}，请重新登录")
        return False


async def login_douyin(playwright):
    """
    手动登录抖音创作者平台（首次使用时调用）
    会打开浏览器让你扫码登录，登录后自动保存 Cookie
    """
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto("https://creator.douyin.com/")
    print("请在浏览器中扫码登录抖音...")
    print("登录成功后，按回车键继续...")

    # 等待用户登录（检测到用户信息元素说明登录成功）
    try:
        await page.wait_for_selector(
            'div[class*="avatar"], div[class*="user-info"]',
            timeout=120000,  # 2分钟超时
        )
        print("检测到登录成功！")
    except Exception:
        input("自动检测失败，请确认已登录后按回车...")

    await save_cookies(page)
    await browser.close()
    print("登录完成，Cookie 已保存，后续发布无需再次登录。")


async def add_douyin_music(page, music_keyword: str = "读书"):
    """
    在抖音发布页面添加平台音乐

    上传视频后，在发布页面点击"选择音乐"，搜索并添加抖音平台上的音乐。
    这样可以直接使用抖音的正版音乐库，零版权风险，还能蹭热门音乐流量。

    Args:
        page: Playwright page 对象
        music_keyword: 搜索关键词（如"读书"、"轻音乐"、"钢琴"）
    """
    try:
        # 查找并点击"选择音乐"或"配乐"按钮（逐个尝试选择器）
        music_btn = None
        for selector in [
            'text="选择音乐"', 'text="配乐"', 'text="添加音乐"',
            'button:has-text("音乐")', 'div:has-text("选择配乐")',
            '[class*="music"]', '[class*="audio"]',
        ]:
            music_btn = await page.query_selector(selector)
            if music_btn:
                break

        if not music_btn:
            print("  未找到音乐选择按钮，跳过（可能页面已改版）")
            return False

        await music_btn.click()
        time.sleep(2)

        # 在搜索框输入关键词
        search_input = None
        for selector in [
            'input[placeholder*="搜索"]', 'input[placeholder*="音乐"]',
            'input[type="text"][class*="search"]',
        ]:
            search_input = await page.query_selector(selector)
            if search_input:
                break
        if search_input:
            await search_input.fill(music_keyword)
            await page.keyboard.press("Enter")
            time.sleep(2)

        # 选择第一首音乐（通常是热门/推荐的）
        use_btn = None
        for selector in [
            'text="使用"', 'button:has-text("使用")',
            'text="添加"', 'button:has-text("添加")',
        ]:
            use_btn = await page.query_selector(selector)
            if use_btn:
                break
        if use_btn:
            await use_btn.click()
            time.sleep(1)
            print(f"  已添加抖音平台音乐（搜索: {music_keyword}）")
            return True

        # 如果没找到"使用"按钮，尝试点击音乐列表第一项
        first_music = None
        for selector in [
            '[class*="music-item"]:first-child',
            '[class*="audio-item"]:first-child',
        ]:
            first_music = await page.query_selector(selector)
            if first_music:
                break
        if first_music:
            await first_music.click()
            time.sleep(1)
            print(f"  已选择抖音平台音乐（搜索: {music_keyword}）")
            return True

        print("  未能自动选择音乐，请稍后手动添加")
        return False

    except Exception as e:
        print(f"  添加音乐失败: {e}，跳过")
        return False


# 书籍蒸馏类视频常用的音乐搜索关键词
DOUYIN_MUSIC_KEYWORDS = {
    "calm": ["轻音乐", "钢琴曲", "安静读书", "舒缓纯音乐"],
    "inspiring": ["励志背景音乐", "正能量", "热血", "奋斗"],
    "emotional": ["感人音乐", "温暖", "治愈", "深情"],
    "thoughtful": ["沉思", "空灵", "氛围感", "冥想音乐"],
    "energetic": ["节奏感", "活力", "卡点音乐", "热门BGM"],
    "default": ["知识分享", "轻音乐", "纯音乐背景", "读书BGM"],
}


def get_douyin_music_keyword(book: dict = None, mood: str = None) -> str:
    """根据书籍信息或情绪获取抖音音乐搜索关键词"""
    import random

    if mood and mood in DOUYIN_MUSIC_KEYWORDS:
        return random.choice(DOUYIN_MUSIC_KEYWORDS[mood])

    if book:
        category = book.get("category", "")
        from bgm_matcher import CATEGORY_TO_MOOD
        mood = CATEGORY_TO_MOOD.get(category, "default")
        keywords = DOUYIN_MUSIC_KEYWORDS.get(mood, DOUYIN_MUSIC_KEYWORDS["default"])
        return random.choice(keywords)

    return random.choice(DOUYIN_MUSIC_KEYWORDS["default"])


async def upload_video(
    video_path: str | Path,
    title: str,
    tags: list[str] = None,
    publish_time: str = None,
    headless: bool = False,
    use_douyin_music: bool = False,
    music_keyword: str = None,
    book: dict = None,
):
    """
    上传视频到抖音创作者平台

    Args:
        video_path: 视频文件路径
        title: 视频标题/描述
        tags: 标签列表，如 ["读书", "好书推荐"]
        publish_time: 定时发布时间，格式 "2024-01-01 20:00"，None 表示立即发布
        headless: 是否无头模式运行
        use_douyin_music: 是否使用抖音平台音乐（而非视频自带的BGM）
        music_keyword: 抖音音乐搜索关键词（不指定则根据书籍自动选择）
        book: 书籍信息（用于自动选择音乐关键词）
    """
    from playwright.async_api import async_playwright
    from safety import pre_publish_check, record_publish, random_delay

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # === 风控: 发布前检查 ===
    passed, msg = pre_publish_check(title)
    if not passed:
        print(f"  [风控] 发布被拦截: {msg}")
        return False
    print(f"  [风控] 检查通过 ({msg})")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()

        # 加载 Cookie
        cookie_loaded = await load_cookies(context)
        if not cookie_loaded:
            print("未找到 Cookie，请先运行 login 命令登录")
            await browser.close()
            return False

        page = await context.new_page()

        try:
            # 1. 进入发布页面
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            await page.wait_for_load_state("networkidle")
            random_delay()  # 随机等待，模拟人类

            # 2. 检查是否需要重新登录
            if "login" in page.url.lower():
                print("Cookie 已过期，请重新登录")
                await browser.close()
                return False

            # 3. 上传视频文件
            upload_input = await page.wait_for_selector(
                'input[type="file"]', timeout=15000
            )
            await upload_input.set_input_files(str(video_path))
            print(f"正在上传: {video_path.name}")

            try:
                await page.wait_for_selector(
                    'text="重新上传"',
                    timeout=300000,
                )
                print("上传完成！")
            except Exception:
                # 检查是否有上传错误提示
                error_el = await page.query_selector('[class*="error"], [class*="fail"]')
                if error_el:
                    error_text = await error_el.text_content()
                    print(f"上传失败: {error_text}")
                    return False
                print("上传超时，但未检测到错误，继续尝试发布...")
            random_delay()

            # 4. 填写标题/描述
            title_editor = await page.wait_for_selector(
                'div[class*="editor"], div[contenteditable="true"]',
                timeout=10000,
            )
            await title_editor.click()
            random_delay(0.5, 1.0)
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")

            # 输入标题（随机打字速度，模拟人类）
            desc_text = title
            if tags:
                tag_text = " ".join(f"#{tag}" for tag in tags)
                desc_text = f"{title} {tag_text}"
            type_delay = random.randint(30, 80)  # 每字 30-80ms
            await title_editor.type(desc_text, delay=type_delay)

            random_delay()

            # 5. 添加抖音平台音乐（可选）
            if use_douyin_music:
                keyword = music_keyword or get_douyin_music_keyword(book=book)
                print(f"正在添加抖音音乐（关键词: {keyword}）...")
                await add_douyin_music(page, keyword)
                random_delay()

            # 6. 定时发布（可选）
            if publish_time:
                schedule_radio = await page.query_selector('text="定时发布"')
                if schedule_radio:
                    await schedule_radio.click()
                    random_delay()
                    time_input = await page.query_selector(
                        'input[placeholder*="选择日期"]'
                    )
                    if time_input:
                        await time_input.fill(publish_time)

            # 7. 点击发布
            random_delay(1.5, 3.0)
            publish_btn = await page.wait_for_selector(
                'button:has-text("发布")', timeout=10000
            )
            await publish_btn.click()
            print(f"视频已发布: {title}")

            # === 风控: 记录发布 ===
            record_publish(title, str(video_path))

            # 等待发布完成（检测页面跳转或成功提示）
            try:
                await page.wait_for_url("**/manage**", timeout=10000)
            except Exception:
                # 可能没有跳转，等待一段时间确保操作完成
                import asyncio as _asyncio
                await _asyncio.sleep(3)

            await save_cookies(page)
            return True

        except Exception as e:
            print(f"发布失败: {e}")
            # 截图保存错误现场
            error_screenshot = VIDEOS_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=str(error_screenshot))
            print(f"错误截图已保存: {error_screenshot}")
            return False

        finally:
            await browser.close()


async def batch_upload(
    video_list: list[dict],
):
    """
    批量上传视频（内置风控: 随机间隔 + 每日上限 + 定期休息）

    Args:
        video_list: [{"path": "xxx.mp4", "title": "xxx", "tags": [...], "publish_time": "xxx"}, ...]
    """
    from safety import (
        can_publish, random_publish_interval, should_rest, take_rest,
    )

    total = len(video_list)
    published = 0

    for i, video_info in enumerate(video_list, 1):
        # 检查每日上限
        ok, msg = can_publish()
        if not ok:
            print(f"\n  [风控] {msg}")
            break

        print(f"\n--- 正在发布第 {i}/{total} 个视频 ---")
        success = await upload_video(
            video_path=video_info["path"],
            title=video_info["title"],
            tags=video_info.get("tags"),
            publish_time=video_info.get("publish_time"),
        )
        if success:
            published += 1
            print(f"第 {i} 个发布成功")
        else:
            print(f"第 {i} 个发布失败，跳过")

        if i < total:
            # 检查是否需要休息
            if should_rest(published):
                take_rest()
            else:
                random_publish_interval()

    print(f"\n批量发布完成！共 {total} 个，请到抖音创作者平台确认。")


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="抖音自动发布工具")
    subparsers = parser.add_subparsers(dest="command")

    # login 子命令
    subparsers.add_parser("login", help="登录抖音（首次使用）")

    # upload 子命令
    upload_parser = subparsers.add_parser("upload", help="上传视频")
    upload_parser.add_argument("--video", type=str, required=True, help="视频文件路径")
    upload_parser.add_argument("--title", type=str, required=True, help="视频标题")
    upload_parser.add_argument("--tags", type=str, nargs="+", help="标签列表")
    upload_parser.add_argument("--time", type=str, help="定时发布时间 (如 2024-01-01 20:00)")
    upload_parser.add_argument("--headless", action="store_true", help="无头模式")
    upload_parser.add_argument(
        "--douyin-music", action="store_true",
        help="使用抖音平台音乐（不使用视频自带BGM）",
    )
    upload_parser.add_argument(
        "--music-keyword", type=str,
        help="抖音音乐搜索关键词（如: 轻音乐、读书BGM）",
    )

    args = parser.parse_args()

    if args.command == "login":
        from playwright.async_api import async_playwright

        async def _login():
            async with async_playwright() as p:
                await login_douyin(p)

        asyncio.run(_login())

    elif args.command == "upload":
        asyncio.run(
            upload_video(
                video_path=args.video,
                title=args.title,
                tags=args.tags,
                publish_time=args.time,
                headless=args.headless,
                use_douyin_music=args.douyin_music,
                music_keyword=args.music_keyword,
            )
        )
    else:
        parser.print_help()
