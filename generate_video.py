"""
视频合成模块
使用 MoviePy 将语音、字幕、背景、音乐合成为最终视频
"""

import random
from datetime import datetime
from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
    concatenate_videoclips,
)

from config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    VIDEO_BG_COLOR,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_FONT_COLOR,
    SUBTITLE_STROKE_COLOR,
    SUBTITLE_STROKE_WIDTH,
    TITLE_FONT_SIZE,
    TITLE_FONT_COLOR,
    VIDEOS_DIR,
    BGM_DIR,
    FONTS_DIR,
)


def parse_srt(srt_path: Path) -> list[dict]:
    """
    解析 SRT 字幕文件

    Returns:
        [{"start": float_seconds, "end": float_seconds, "text": str}, ...]
    """
    subtitles = []
    content = srt_path.read_text(encoding="utf-8")
    blocks = content.strip().split("\n\n")

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            time_line = lines[1]
            text = " ".join(lines[2:])

            start_str, end_str = time_line.split(" --> ")
            start = _srt_time_to_seconds(start_str.strip())
            end = _srt_time_to_seconds(end_str.strip())

            subtitles.append({"start": start, "end": end, "text": text})

    return subtitles


def _srt_time_to_seconds(time_str: str) -> float:
    """SRT时间格式转秒数"""
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def group_subtitles(subtitles: list[dict], max_chars: int = 15) -> list[dict]:
    """
    将逐字字幕合并为逐句字幕（每组最多 max_chars 个字）
    使字幕更易阅读
    """
    if not subtitles:
        return []

    grouped = []
    current_text = ""
    current_start = subtitles[0]["start"]

    for sub in subtitles:
        if len(current_text) + len(sub["text"]) > max_chars:
            if current_text:
                grouped.append({
                    "start": current_start,
                    "end": sub["start"],
                    "text": current_text,
                })
            current_text = sub["text"]
            current_start = sub["start"]
        else:
            current_text += sub["text"]

    # 最后一组
    if current_text:
        grouped.append({
            "start": current_start,
            "end": subtitles[-1]["end"],
            "text": current_text,
        })

    return grouped


def find_font() -> str:
    """查找可用的中文字体"""
    # 优先使用项目内的字体
    for font_file in FONTS_DIR.glob("*.ttf"):
        return str(font_file)
    for font_file in FONTS_DIR.glob("*.otf"):
        return str(font_file)

    # Windows 系统字体
    system_fonts = [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
    ]
    for f in system_fonts:
        if Path(f).exists():
            return f

    return "Arial"  # fallback


def find_bgm(book: dict = None, script: str = None) -> Path | None:
    """
    智能匹配背景音乐

    优先使用 bgm_matcher 智能匹配，失败则随机选择
    """
    try:
        from bgm_matcher import match_bgm
        result = match_bgm(book=book, script=script, mode="auto")
        if result:
            return result
    except ImportError:
        pass

    # 兜底：随机选择
    bgm_files = list(BGM_DIR.glob("*.mp3")) + list(BGM_DIR.glob("*.wav"))
    if bgm_files:
        return random.choice(bgm_files)
    return None


def generate_video(
    voice_path: str | Path,
    subtitle_path: str | Path | None = None,
    book_title: str = "",
    book_author: str = "",
    bgm_path: str | Path | None = None,
    bgm_volume: float = 0.15,
    book: dict = None,
    script: str = None,
) -> Path:
    """
    合成最终视频

    Args:
        voice_path: 语音文件路径
        subtitle_path: SRT字幕文件路径（可选）
        book_title: 书名（显示在视频顶部）
        book_author: 作者（显示在书名下方）
        bgm_path: 背景音乐路径（不指定则自动智能匹配）
        bgm_volume: 背景音乐音量（0-1）
        book: 书籍信息字典（用于智能匹配 BGM）
        script: 文案文本（用于 AI 分析情绪匹配 BGM）

    Returns:
        输出视频文件路径
    """
    voice_path = Path(voice_path)
    font = find_font()

    # 1. 加载语音，确定视频时长
    voice_clip = AudioFileClip(str(voice_path))
    duration = voice_clip.duration

    # 2. 创建背景
    bg_clip = ColorClip(
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        color=VIDEO_BG_COLOR,
        duration=duration,
    )

    layers = [bg_clip]

    # 3. 添加书名标题
    if book_title:
        title_text = f"《{book_title}》"
        title_clip = (
            TextClip(
                text=title_text,
                font_size=TITLE_FONT_SIZE,
                color=TITLE_FONT_COLOR,
                font=font,
                size=(VIDEO_WIDTH - 100, None),
                method="caption",
                text_align="center",
            )
            .with_duration(duration)
            .with_position(("center", 200))
        )
        layers.append(title_clip)

    if book_author:
        author_clip = (
            TextClip(
                text=f"作者：{book_author}",
                font_size=36,
                color="gray",
                font=font,
                text_align="center",
            )
            .with_duration(duration)
            .with_position(("center", 290))
        )
        layers.append(author_clip)

    # 4. 添加字幕
    if subtitle_path:
        subtitle_path = Path(subtitle_path)
        if subtitle_path.exists():
            raw_subs = parse_srt(subtitle_path)
            subs = group_subtitles(raw_subs, max_chars=15)

            for sub in subs:
                sub_clip = (
                    TextClip(
                        text=sub["text"],
                        font_size=SUBTITLE_FONT_SIZE,
                        color=SUBTITLE_FONT_COLOR,
                        font=font,
                        stroke_color=SUBTITLE_STROKE_COLOR,
                        stroke_width=SUBTITLE_STROKE_WIDTH,
                        size=(VIDEO_WIDTH - 120, None),
                        method="caption",
                        text_align="center",
                    )
                    .with_start(sub["start"])
                    .with_end(sub["end"])
                    .with_position(("center", VIDEO_HEIGHT // 2))
                )
                layers.append(sub_clip)

    # 5. 合成视频
    video = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # 6. 混合音频（语音 + 背景音乐）
    audio_tracks = [voice_clip]

    if bgm_path is None:
        bgm_path = find_bgm(book=book, script=script)

    if bgm_path and Path(bgm_path).exists():
        bgm_clip = AudioFileClip(str(bgm_path))
        # 循环背景音乐以匹配视频时长
        if bgm_clip.duration < duration:
            loops_needed = int(duration / bgm_clip.duration) + 1
            bgm_clip = concatenate_videoclips(
                [bgm_clip] * loops_needed
            ).subclipped(0, duration)
        else:
            bgm_clip = bgm_clip.subclipped(0, duration)

        bgm_clip = bgm_clip.with_volume_scaled(bgm_volume)
        # 添加淡入淡出
        bgm_clip = bgm_clip.audio_fadein(2).audio_fadeout(3)
        audio_tracks.append(bgm_clip)

    final_audio = CompositeAudioClip(audio_tracks)
    video = video.with_audio(final_audio)

    # 7. 导出
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = book_title.replace(" ", "_").replace("/", "_") if book_title else "video"
    output_path = VIDEOS_DIR / f"{safe_title}_{timestamp}.mp4"

    video.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        logger="bar",
    )

    # 清理
    voice_clip.close()
    video.close()

    return output_path


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="视频合成工具")
    parser.add_argument("--voice", type=str, required=True, help="语音文件路径")
    parser.add_argument("--subtitle", type=str, help="SRT字幕文件路径")
    parser.add_argument("--title", type=str, default="", help="书名")
    parser.add_argument("--author", type=str, default="", help="作者")
    parser.add_argument("--bgm", type=str, help="背景音乐路径")
    parser.add_argument("--bgm-volume", type=float, default=0.15, help="背景音乐音量(0-1)")
    args = parser.parse_args()

    output = generate_video(
        voice_path=args.voice,
        subtitle_path=args.subtitle,
        book_title=args.title,
        book_author=args.author,
        bgm_path=args.bgm,
        bgm_volume=args.bgm_volume,
    )
    print(f"视频已生成：{output}")
