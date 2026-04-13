"""
视频合成模块
使用 MoviePy 将画面帧、语音、字幕、音乐合成为最终视频

画面效果：
- 分段画面切换（片头→多个内容卡片→片尾），不再是一张静态图
- 每段画面有渐变/主题色背景 + 书籍卡片 + 金句卡片
- 画面之间有淡入淡出转场
- 字幕实时同步显示
"""

import random
from datetime import datetime
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_audioclips,
    concatenate_videoclips,
)

from config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    VIDEO_BG_MODE,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_FONT_COLOR,
    SUBTITLE_STROKE_COLOR,
    SUBTITLE_STROKE_WIDTH,
    VIDEOS_DIR,
    BGM_DIR,
    FONTS_DIR,
    get_book_output_dir,
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
    """将逐字字幕合并为逐句字幕"""
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

    if current_text:
        grouped.append({
            "start": current_start,
            "end": subtitles[-1]["end"],
            "text": current_text,
        })

    return grouped


def find_font() -> str:
    """查找可用的中文字体"""
    for font_file in FONTS_DIR.glob("*.ttf"):
        return str(font_file)
    for font_file in FONTS_DIR.glob("*.otf"):
        return str(font_file)

    system_fonts = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for f in system_fonts:
        if Path(f).exists():
            return f

    return "Arial"


def find_bgm(book: dict = None, script: str = None) -> Path | None:
    """智能匹配背景音乐"""
    try:
        from bgm_matcher import match_bgm
        result = match_bgm(book=book, script=script, mode="auto")
        if result:
            return result
    except ImportError:
        pass

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
    合成最终视频（带画面帧切换）

    自动生成画面帧（背景+书籍卡片+金句卡片），分段切换，
    配合字幕同步、背景音乐，输出完整的短视频。

    Args:
        voice_path: 语音文件路径
        subtitle_path: SRT字幕文件路径
        book_title: 书名
        book_author: 作者
        bgm_path: 背景音乐路径（不指定则自动匹配）
        bgm_volume: 背景音乐音量（0-1）
        book: 书籍信息字典
        script: 文案文本
    """
    voice_path = Path(voice_path)
    if not voice_path.exists():
        raise FileNotFoundError(f"语音文件不存在: {voice_path}")
    font = find_font()
    category = book.get("category", "") if book else ""

    # 1. 加载语音
    voice_clip = AudioFileClip(str(voice_path))
    duration = voice_clip.duration

    # 跟踪所有需要释放的资源
    clips_to_close = [voice_clip]
    video = None

    try:
        # 2. 根据 VIDEO_BG_MODE 选择画面方案
        _bg_ready = False

        # 方案A: 数字人
        if VIDEO_BG_MODE == "digital_human":
            try:
                from digital_human import is_enabled as dh_enabled, generate_talking_video
                if dh_enabled():
                    print("  正在生成数字人视频...")
                    dh_video = generate_talking_video(
                        audio_path=voice_path,
                        output_path=voice_path.parent / "talking_head.mp4",
                    )
                    if dh_video and dh_video.exists():
                        from moviepy import VideoFileClip, ColorClip
                        dh_clip = VideoFileClip(str(dh_video)).resized((VIDEO_WIDTH, VIDEO_HEIGHT))
                        clips_to_close.append(dh_clip)
                        if dh_clip.duration >= duration:
                            dh_clip = dh_clip.subclipped(0, duration)
                        elif dh_clip.duration < duration:
                            pad = ColorClip(
                                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                                color=(18, 18, 18),
                                duration=duration - dh_clip.duration,
                            )
                            dh_clip = concatenate_videoclips([dh_clip, pad])
                        layers = [dh_clip]
                        print("  数字人视频已生成，使用数字人画面")
                        _bg_ready = True
            except ImportError:
                print("  数字人模块不可用，降级为其他模式")

        # 方案B: 应景视频素材 + 大字幕（最主流知识类风格）
        if not _bg_ready and VIDEO_BG_MODE in ("video", "digital_human"):
            bg_clip = _build_video_background(category, duration, voice_path.parent)
            if bg_clip is not None:
                clips_to_close.append(bg_clip)
                # 添加半透明暗层，让字幕更清晰
                from moviepy import ColorClip
                dark_overlay = (
                    ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0))
                    .with_duration(duration)
                    .with_opacity(0.35)
                )
                layers = [bg_clip, dark_overlay]
                print("  使用视频素材背景")
                _bg_ready = True

        # 方案C: 卡片画面（兜底）
        if not _bg_ready:
            frame_paths = _generate_frames(book_title, book_author, category, script, voice_path.parent)
            bg_video = _build_frame_sequence(frame_paths, duration)
            layers = [bg_video]

        # 4. 添加字幕层
        if subtitle_path:
            subtitle_path = Path(subtitle_path)
            if subtitle_path.exists():
                raw_subs = parse_srt(subtitle_path)
                # 视频背景模式下字幕更大、每行更多字(因为是主要阅读内容)
                is_video_bg = _bg_ready and VIDEO_BG_MODE == "video"
                max_chars = 12 if is_video_bg else 15
                subs = group_subtitles(raw_subs, max_chars=max_chars)

                # 视频背景模式：字幕更大更醒目，居中偏下
                sub_font_size = int(SUBTITLE_FONT_SIZE * 1.3) if is_video_bg else SUBTITLE_FONT_SIZE
                sub_stroke_width = SUBTITLE_STROKE_WIDTH + 1 if is_video_bg else SUBTITLE_STROKE_WIDTH
                sub_y_pos = int(VIDEO_HEIGHT * 0.55) if is_video_bg else int(VIDEO_HEIGHT * 0.65)

                for sub in subs:
                    sub_clip = (
                        TextClip(
                            text=sub["text"],
                            font_size=sub_font_size,
                            color=SUBTITLE_FONT_COLOR,
                            font=font,
                            stroke_color=SUBTITLE_STROKE_COLOR,
                            stroke_width=sub_stroke_width,
                            size=(VIDEO_WIDTH - 120, None),
                            method="caption",
                            text_align="center",
                        )
                        .with_start(sub["start"])
                        .with_end(sub["end"])
                        .with_position(("center", sub_y_pos))
                    )
                    layers.append(sub_clip)

        # 5. 合成视频
        video = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

        # 6. 音频混合（语音 + BGM）
        audio_tracks = [voice_clip]

        if bgm_path is None:
            bgm_path = find_bgm(book=book, script=script)

        if bgm_path and Path(bgm_path).exists():
            bgm_clip = AudioFileClip(str(bgm_path))
            clips_to_close.append(bgm_clip)
            if bgm_clip.duration < duration:
                loops = int(duration / bgm_clip.duration) + 1
                bgm_clip = concatenate_audioclips([bgm_clip] * loops).subclipped(0, duration)
            else:
                bgm_clip = bgm_clip.subclipped(0, duration)

            bgm_clip = bgm_clip.with_volume_scaled(bgm_volume)
            bgm_clip = bgm_clip.audio_fadein(2).audio_fadeout(3)
            audio_tracks.append(bgm_clip)

        final_audio = CompositeAudioClip(audio_tracks)
        video = video.with_audio(final_audio)

        # 7. 导出（保存到语音文件所在目录，即当前集的目录）
        output_dir = voice_path.parent
        output_path = output_dir / "video.mp4"

        video.write_videofile(
            str(output_path),
            fps=VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium",
            logger="bar",
        )

        return output_path

    finally:
        # 确保所有资源都被释放，即使发生异常
        for clip in clips_to_close:
            try:
                clip.close()
            except Exception:
                pass
        if video is not None:
            try:
                video.close()
            except Exception:
                pass


def _generate_frames(
    book_title: str,
    book_author: str,
    category: str,
    script: str,
    output_dir: Path = None,
) -> list[Path]:
    """
    生成视频画面帧

    优先使用 generate_images 模块生成精美画面；
    如果该模块不可用（如缺少 Pillow），则回退到纯色帧。
    """
    try:
        from generate_images import generate_all_frames
        if script:
            frames_dir = (output_dir / "frames") if output_dir else None
            return generate_all_frames(
                book_title, book_author, category, script, frames_dir
            )
    except ImportError:
        print("generate_images 模块不可用，使用纯色背景")
    except Exception as e:
        print(f"画面生成出错: {e}，使用纯色背景")

    return []


def _build_frame_sequence(
    frame_paths: list[Path],
    total_duration: float,
    crossfade: float = 0.8,
) -> CompositeVideoClip | ImageClip:
    """
    将多张画面帧图片组合成视频序列，带淡入淡出转场

    Args:
        frame_paths: 图片路径列表
        total_duration: 总时长
        crossfade: 转场时长（秒）
    """
    from config import VIDEO_BG_COLOR

    if not frame_paths:
        # 无帧图片，使用纯色背景
        from moviepy import ColorClip
        return ColorClip(
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
            color=VIDEO_BG_COLOR,
            duration=total_duration,
        )

    n = len(frame_paths)

    if n == 1:
        return (
            ImageClip(str(frame_paths[0]))
            .resized((VIDEO_WIDTH, VIDEO_HEIGHT))
            .with_duration(total_duration)
        )

    # 计算每帧时长（考虑交叉淡化的重叠）
    # 有效时长 = sum(帧时长) - (n-1)*crossfade = total_duration
    # 帧时长 = (total_duration + (n-1)*crossfade) / n
    frame_duration = (total_duration + (n - 1) * crossfade) / n
    frame_duration = max(frame_duration, crossfade + 0.5)  # 至少比转场长

    clips = []
    for path in frame_paths:
        clip = (
            ImageClip(str(path))
            .resized((VIDEO_WIDTH, VIDEO_HEIGHT))
            .with_duration(frame_duration)
        )
        clips.append(clip)

    # 使用 crossfadein/crossfadeout 实现转场
    video = concatenate_videoclips(clips, method="compose", padding=-crossfade)

    # 裁剪到精确时长
    if video.duration > total_duration:
        video = video.subclipped(0, total_duration)

    return video


def _build_video_background(
    category: str,
    total_duration: float,
    cache_dir: Path = None,
) -> CompositeVideoClip | None:
    """
    构建视频素材背景

    从本地或 Pexels 获取视频素材，拼接/循环到指定时长，
    裁剪为竖屏 9:16。
    """
    try:
        from bg_video import get_bg_videos
    except ImportError:
        print("  bg_video 模块不可用")
        return None

    from moviepy import VideoFileClip, ColorClip

    video_paths = get_bg_videos(
        category=category,
        count=5,
        cache_dir=cache_dir / "bg_cache" if cache_dir else None,
    )

    if not video_paths:
        return None

    clips = []
    accumulated = 0.0

    for vpath in video_paths:
        if accumulated >= total_duration:
            break
        try:
            clip = VideoFileClip(str(vpath))
            # 裁剪为竖屏 9:16（居中裁剪）
            clip = _crop_to_portrait(clip)
            clip = clip.resized((VIDEO_WIDTH, VIDEO_HEIGHT))
            clips.append(clip)
            accumulated += clip.duration
        except Exception as e:
            print(f"  [素材] 加载失败 {vpath.name}: {e}")
            continue

    if not clips:
        return None

    # 如果素材不够长，循环拼接
    if accumulated < total_duration:
        while accumulated < total_duration:
            for clip in list(clips):
                if accumulated >= total_duration:
                    break
                clips.append(clip)
                accumulated += clip.duration

    # 拼接所有素材
    from moviepy import concatenate_videoclips
    combined = concatenate_videoclips(clips, method="compose")

    # 裁剪到精确时长
    if combined.duration > total_duration:
        combined = combined.subclipped(0, total_duration)

    return combined


def _crop_to_portrait(clip):
    """将视频裁剪为竖屏 9:16（居中裁剪）"""
    w, h = clip.size
    target_ratio = 9 / 16  # 竖屏

    current_ratio = w / h
    if abs(current_ratio - target_ratio) < 0.05:
        return clip  # 已经接近竖屏

    if current_ratio > target_ratio:
        # 视频太宽(横屏)，裁掉两边
        new_w = int(h * target_ratio)
        x_center = w // 2
        x1 = x_center - new_w // 2
        return clip.cropped(x1=x1, x2=x1 + new_w)
    else:
        # 视频太高，裁掉上下
        new_h = int(w / target_ratio)
        y_center = h // 2
        y1 = y_center - new_h // 2
        return clip.cropped(y1=y1, y2=y1 + new_h)


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="视频合成工具")
    parser.add_argument("--voice", type=str, required=True, help="语音文件路径")
    parser.add_argument("--subtitle", type=str, help="SRT字幕文件路径")
    parser.add_argument("--title", type=str, default="", help="书名")
    parser.add_argument("--author", type=str, default="", help="作者")
    parser.add_argument("--category", type=str, default="", help="书籍分类")
    parser.add_argument("--script", type=str, help="文案文本（用于生成画面）")
    parser.add_argument("--script-file", type=str, help="文案文件路径")
    parser.add_argument("--bgm", type=str, help="背景音乐路径")
    parser.add_argument("--bgm-volume", type=float, default=0.15, help="背景音乐音量(0-1)")
    args = parser.parse_args()

    script_text = args.script
    if args.script_file:
        script_text = Path(args.script_file).read_text(encoding="utf-8")

    book_info = None
    if args.category:
        book_info = {"category": args.category}

    output = generate_video(
        voice_path=args.voice,
        subtitle_path=args.subtitle,
        book_title=args.title,
        book_author=args.author,
        bgm_path=args.bgm,
        bgm_volume=args.bgm_volume,
        book=book_info,
        script=script_text,
    )
    print(f"视频已生成：{output}")
