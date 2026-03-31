"""
自动发布模块
使用 Playwright 自动上传视频到抖音创作者平台
"""

import json
import time
from datetime import datetime
from pathlib import Path

from config import DOUYIN_COOKIE_PATH, VIDEOS_DIR


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
    with open(cookie_path, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    await context.add_cookies(cookies)
    return True


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


async def upload_video(
    video_path: str | Path,
    title: str,
    tags: list[str] = None,
    publish_time: str = None,
    headless: bool = False,
):
    """
    上传视频到抖音创作者平台

    Args:
        video_path: 视频文件路径
        title: 视频标题/描述
        tags: 标签列表，如 ["读书", "好书推荐"]
        publish_time: 定时发布时间，格式 "2024-01-01 20:00"，None 表示立即发布
        headless: 是否无头模式运行
    """
    from playwright.async_api import async_playwright

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

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
            time.sleep(2)

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

            # 等待上传完成（进度条消失或出现"重新上传"按钮）
            await page.wait_for_selector(
                'text="重新上传"',
                timeout=300000,  # 5分钟超时，大文件需要更长时间
            )
            print("上传完成！")

            # 4. 填写标题/描述
            # 清空默认标题，输入自定义标题
            title_editor = await page.wait_for_selector(
                'div[class*="editor"], div[contenteditable="true"]',
                timeout=10000,
            )
            await title_editor.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")

            # 输入标题
            desc_text = title
            if tags:
                tag_text = " ".join(f"#{tag}" for tag in tags)
                desc_text = f"{title} {tag_text}"
            await title_editor.type(desc_text, delay=50)

            time.sleep(1)

            # 5. 定时发布（可选）
            if publish_time:
                # 点击定时发布选项
                schedule_radio = await page.query_selector('text="定时发布"')
                if schedule_radio:
                    await schedule_radio.click()
                    time.sleep(1)
                    # 输入时间（具体选择器需根据实际页面调整）
                    time_input = await page.query_selector(
                        'input[placeholder*="选择日期"]'
                    )
                    if time_input:
                        await time_input.fill(publish_time)

            # 6. 点击发布
            time.sleep(2)
            publish_btn = await page.wait_for_selector(
                'button:has-text("发布")', timeout=10000
            )
            await publish_btn.click()
            print(f"视频已发布: {title}")

            # 等待发布完成
            time.sleep(3)

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
    interval_seconds: int = 60,
):
    """
    批量上传视频

    Args:
        video_list: [{"path": "xxx.mp4", "title": "xxx", "tags": [...], "publish_time": "xxx"}, ...]
        interval_seconds: 每个视频之间的间隔（秒），避免被风控
    """
    total = len(video_list)
    for i, video_info in enumerate(video_list, 1):
        print(f"\n--- 正在发布第 {i}/{total} 个视频 ---")
        success = await upload_video(
            video_path=video_info["path"],
            title=video_info["title"],
            tags=video_info.get("tags"),
            publish_time=video_info.get("publish_time"),
        )
        if success:
            print(f"第 {i} 个发布成功")
        else:
            print(f"第 {i} 个发布失败，跳过")

        if i < total:
            print(f"等待 {interval_seconds} 秒后继续...")
            time.sleep(interval_seconds)

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
            )
        )
    else:
        parser.print_help()
