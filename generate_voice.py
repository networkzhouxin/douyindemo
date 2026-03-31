"""
语音合成模块
将文案文本转换为语音文件（MP3）

TTS 方案优先级：
1. Edge TTS（免费，需联网到微软服务器）— 带重试和代理支持
2. Azure TTS（需API Key，质量最好）
3. 离线 pyttsx3（完全离线，不需要网络，音质一般但保证可用）

国内网络连不上微软服务器时：
- 方案A：配置代理（config.py 中设置 HTTP_PROXY）
- 方案B：自动降级到离线 pyttsx3
"""

import asyncio
import os
import re
import time
from datetime import datetime
from pathlib import Path

from config import (
    TTS_PROVIDER,
    EDGE_TTS_VOICE,
    EDGE_TTS_MAX_RETRIES,
    EDGE_TTS_RETRY_DELAY,
    HTTP_PROXY,
    HTTPS_PROXY,
    AZURE_TTS_KEY,
    AZURE_TTS_REGION,
    VOICES_DIR,
)


def clean_text_for_tts(text: str) -> str:
    """清理文案文本，去掉元信息，只保留正文"""
    if "---" in text:
        text = text.split("---", 1)[-1]
    elif "-" * 20 in text:
        parts = text.split("-" * 40)
        if len(parts) > 1:
            text = parts[-1]

    text = text.strip()
    text = re.sub(r"[#*_`]", "", text)
    return text


# ============================================================
# Edge TTS（带重试和代理）
# ============================================================

def _setup_proxy():
    """设置网络代理环境变量（Edge TTS 通过 aiohttp 使用环境变量代理）"""
    if HTTP_PROXY:
        os.environ["HTTP_PROXY"] = HTTP_PROXY
        os.environ["http_proxy"] = HTTP_PROXY
    if HTTPS_PROXY:
        os.environ["HTTPS_PROXY"] = HTTPS_PROXY
        os.environ["https_proxy"] = HTTPS_PROXY


async def generate_voice_edge(text: str, output_path: Path, voice: str = None):
    """使用 Edge TTS 生成语音（带重试）"""
    import edge_tts

    _setup_proxy()
    voice = voice or EDGE_TTS_VOICE

    last_error = None
    for attempt in range(1, EDGE_TTS_MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            return  # 成功
        except Exception as e:
            last_error = e
            if attempt < EDGE_TTS_MAX_RETRIES:
                print(f"  Edge TTS 第 {attempt} 次失败: {e}")
                print(f"  {EDGE_TTS_RETRY_DELAY} 秒后重试...")
                await asyncio.sleep(EDGE_TTS_RETRY_DELAY)
            else:
                raise last_error


async def generate_voice_edge_with_subtitles(
    text: str, output_path: Path, subtitle_path: Path, voice: str = None
):
    """使用 Edge TTS 生成语音 + SRT 字幕（带重试）"""
    import edge_tts

    _setup_proxy()
    voice = voice or EDGE_TTS_VOICE

    last_error = None
    for attempt in range(1, EDGE_TTS_MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(text, voice)
            srt_content = []
            audio_chunks = []
            idx = 1

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start_ms = chunk["offset"] // 10000
                    duration_ms = chunk["duration"] // 10000
                    end_ms = start_ms + duration_ms
                    word = chunk["text"]

                    start_time = _ms_to_srt_time(start_ms)
                    end_time = _ms_to_srt_time(end_ms)
                    srt_content.append(f"{idx}\n{start_time} --> {end_time}\n{word}\n")
                    idx += 1

            # 保存音频
            with open(output_path, "wb") as f:
                for chunk in audio_chunks:
                    f.write(chunk)

            # 保存字幕
            with open(subtitle_path, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_content))

            return  # 成功
        except Exception as e:
            last_error = e
            if attempt < EDGE_TTS_MAX_RETRIES:
                print(f"  Edge TTS 第 {attempt} 次失败: {e}")
                print(f"  {EDGE_TTS_RETRY_DELAY} 秒后重试...")
                await asyncio.sleep(EDGE_TTS_RETRY_DELAY)
            else:
                raise last_error


def _ms_to_srt_time(ms: int) -> str:
    """毫秒转SRT时间格式"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


# ============================================================
# Azure TTS
# ============================================================

def generate_voice_azure(text: str, output_path: Path):
    """使用 Azure TTS 生成语音"""
    import azure.cognitiveservices.speech as speechsdk

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_TTS_KEY, region=AZURE_TTS_REGION
    )
    speech_config.speech_synthesis_voice_name = "zh-CN-YunxiNeural"
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )

    result = synthesizer.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(f"Azure TTS 失败: {result.reason}")


# ============================================================
# 离线 TTS（pyttsx3，完全不需要网络）
# ============================================================

def generate_voice_offline(text: str, output_path: Path):
    """
    使用 pyttsx3 离线生成语音

    优点：完全离线，不需要网络
    缺点：音质一般，依赖系统自带的语音引擎
    Windows 上使用 SAPI5，自带中文语音
    """
    import pyttsx3

    engine = pyttsx3.init()

    # 设置中文语音（Windows SAPI5）
    voices = engine.getProperty("voices")
    zh_voice = None
    for v in voices:
        if "chinese" in v.name.lower() or "zh" in v.id.lower():
            zh_voice = v
            break

    if zh_voice:
        engine.setProperty("voice", zh_voice.id)

    engine.setProperty("rate", 170)    # 语速
    engine.setProperty("volume", 0.9)  # 音量

    # pyttsx3 直接保存为 wav/mp3
    # 先保存为 wav，如果需要 mp3 再转换
    wav_path = output_path.with_suffix(".wav")
    engine.save_to_file(text, str(wav_path))
    engine.runAndWait()

    # 如果需要 mp3 格式，尝试用 ffmpeg 转换
    if output_path.suffix.lower() == ".mp3":
        try:
            import subprocess
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), "-q:a", "2", str(output_path)],
                capture_output=True, check=True,
            )
            wav_path.unlink()  # 删除 wav
        except (FileNotFoundError, subprocess.CalledProcessError):
            # ffmpeg 不可用，直接用 wav
            if wav_path.exists():
                wav_path.rename(output_path)

    print(f"  [离线TTS] 语音已生成（音质有限，建议配置代理后使用 Edge TTS）")


def generate_offline_subtitle(text: str, subtitle_path: Path, chars_per_second: float = 4.0):
    """
    为离线 TTS 生成估算的字幕文件
    按每秒 chars_per_second 个字估算时间
    """
    # 按标点分句
    sentences = re.split(r'([。！？!?，,；;：:、])', text)
    merged = []
    for i in range(0, len(sentences) - 1, 2):
        s = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
        s = s.strip()
        if s:
            merged.append(s)
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        merged.append(sentences[-1].strip())

    srt_lines = []
    current_time = 0.0
    for idx, sentence in enumerate(merged, 1):
        duration = len(sentence) / chars_per_second
        start = _ms_to_srt_time(int(current_time * 1000))
        end = _ms_to_srt_time(int((current_time + duration) * 1000))
        srt_lines.append(f"{idx}\n{start} --> {end}\n{sentence}\n")
        current_time += duration

    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))


# ============================================================
# 统一入口
# ============================================================

def generate_voice(
    text: str,
    book_title: str = "untitled",
    with_subtitles: bool = True,
) -> dict:
    """
    生成语音文件（统一入口）

    优先级：
    1. 按 TTS_PROVIDER 配置的方案生成
    2. Edge TTS 失败时自动降级到离线 pyttsx3

    Returns:
        {"voice_path": Path, "subtitle_path": Path | None}
    """
    text = clean_text_for_tts(text)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = book_title.replace(" ", "_").replace("/", "_")

    voice_path = VOICES_DIR / f"{safe_title}_{timestamp}.mp3"
    subtitle_path = VOICES_DIR / f"{safe_title}_{timestamp}.srt" if with_subtitles else None

    # Azure TTS
    if TTS_PROVIDER == "azure":
        if not AZURE_TTS_KEY:
            print("  Azure TTS Key 未配置，降级到 Edge TTS")
        else:
            generate_voice_azure(text, voice_path)
            return {"voice_path": voice_path, "subtitle_path": None}

    # 离线 TTS（直接使用，不尝试网络）
    if TTS_PROVIDER == "offline":
        generate_voice_offline(text, voice_path)
        if with_subtitles and subtitle_path:
            generate_offline_subtitle(text, subtitle_path)
        return {"voice_path": voice_path, "subtitle_path": subtitle_path}

    # Edge TTS（默认，带重试 + 失败自动降级到离线）
    try:
        if with_subtitles and subtitle_path:
            asyncio.run(
                generate_voice_edge_with_subtitles(text, voice_path, subtitle_path)
            )
        else:
            asyncio.run(generate_voice_edge(text, voice_path))

        return {"voice_path": voice_path, "subtitle_path": subtitle_path}

    except Exception as e:
        print(f"\n  Edge TTS 最终失败: {e}")
        print(f"  可能原因：国内网络无法连接微软服务器")
        print(f"  解决方案：")
        print(f"    1. 配置代理: 在 config.py 中设置 HTTP_PROXY/HTTPS_PROXY")
        print(f"       或设置环境变量: export HTTPS_PROXY=http://127.0.0.1:7890")
        print(f"    2. 使用离线TTS: 在 config.py 中设置 TTS_PROVIDER = 'offline'")
        print(f"\n  正在自动降级到离线 TTS...")

        try:
            generate_voice_offline(text, voice_path)
            if with_subtitles and subtitle_path:
                generate_offline_subtitle(text, subtitle_path)
            return {"voice_path": voice_path, "subtitle_path": subtitle_path}
        except Exception as e2:
            print(f"  离线 TTS 也失败了: {e2}")
            print(f"  请安装 pyttsx3: pip install pyttsx3")
            raise RuntimeError(
                f"所有 TTS 方案均失败。Edge TTS: {e} | 离线: {e2}\n"
                f"请配置代理或安装 pyttsx3"
            ) from e2


def list_available_voices():
    """列出所有可用的中文语音"""
    import edge_tts

    async def _list():
        voices = await edge_tts.list_voices()
        cn_voices = [v for v in voices if v["Locale"].startswith("zh-")]
        for v in cn_voices:
            print(f"  {v['ShortName']:30s} | {v['Gender']:6s} | {v['Locale']}")
        return cn_voices

    _setup_proxy()
    return asyncio.run(_list())


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="语音合成工具")
    parser.add_argument("--text", type=str, help="直接输入要合成的文本")
    parser.add_argument("--file", type=str, help="从文案文件读取文本")
    parser.add_argument("--voice", type=str, help="指定语音角色")
    parser.add_argument("--list-voices", action="store_true", help="列出所有可用的中文语音")
    parser.add_argument("--no-subtitle", action="store_true", help="不生成字幕文件")
    parser.add_argument(
        "--provider", choices=["edge", "azure", "offline"],
        help="指定TTS方案（覆盖config配置）",
    )
    args = parser.parse_args()

    if args.list_voices:
        print("可用的中文语音：")
        list_available_voices()
    elif args.text or args.file:
        if args.file:
            text = Path(args.file).read_text(encoding="utf-8")
            title = Path(args.file).stem
        else:
            text = args.text
            title = "test"

        result = generate_voice(text, book_title=title, with_subtitles=not args.no_subtitle)
        print(f"语音文件：{result['voice_path']}")
        if result["subtitle_path"]:
            print(f"字幕文件：{result['subtitle_path']}")
    else:
        print("请使用 --text 或 --file 指定要合成的内容，或用 --list-voices 查看可用语音")
