"""
语音合成模块
将文案文本转换为语音文件（MP3）
默认使用 Edge TTS（免费，无需API Key）
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path

from config import (
    TTS_PROVIDER,
    EDGE_TTS_VOICE,
    AZURE_TTS_KEY,
    AZURE_TTS_REGION,
    VOICES_DIR,
)


def clean_text_for_tts(text: str) -> str:
    """清理文案文本，去掉元信息，只保留正文"""
    # 如果文案文件包含头部信息，去掉分隔线之前的内容
    if "---" in text:
        text = text.split("---", 1)[-1]
    elif "-" * 20 in text:
        parts = text.split("-" * 40)
        if len(parts) > 1:
            text = parts[-1]

    # 去掉多余的空行和空格
    text = text.strip()
    # 去掉 Markdown 格式符号
    text = re.sub(r"[#*_`]", "", text)
    return text


async def generate_voice_edge(text: str, output_path: Path, voice: str = None):
    """使用 Edge TTS 生成语音（免费）"""
    import edge_tts

    voice = voice or EDGE_TTS_VOICE
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


async def generate_voice_edge_with_subtitles(
    text: str, output_path: Path, subtitle_path: Path, voice: str = None
):
    """
    使用 Edge TTS 生成语音，同时生成字幕文件（SRT格式）
    这样可以实现精确的逐字/逐句字幕同步
    """
    import edge_tts

    voice = voice or EDGE_TTS_VOICE
    communicate = edge_tts.Communicate(text, voice)
    srt_content = []
    audio_chunks = []
    idx = 1

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start_ms = chunk["offset"] // 10000  # 转换为毫秒
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


def _ms_to_srt_time(ms: int) -> str:
    """毫秒转SRT时间格式 HH:MM:SS,mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def generate_voice_azure(text: str, output_path: Path):
    """使用 Azure TTS 生成语音（需要API Key）"""
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


def generate_voice(
    text: str,
    book_title: str = "untitled",
    with_subtitles: bool = True,
) -> dict:
    """
    生成语音文件

    Args:
        text: 文案文本
        book_title: 书名（用于文件命名）
        with_subtitles: 是否同时生成字幕文件

    Returns:
        {"voice_path": Path, "subtitle_path": Path | None}
    """
    text = clean_text_for_tts(text)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = book_title.replace(" ", "_").replace("/", "_")

    voice_path = VOICES_DIR / f"{safe_title}_{timestamp}.mp3"
    subtitle_path = VOICES_DIR / f"{safe_title}_{timestamp}.srt" if with_subtitles else None

    if TTS_PROVIDER == "azure":
        generate_voice_azure(text, voice_path)
        return {"voice_path": voice_path, "subtitle_path": None}
    else:
        # 默认使用 Edge TTS
        if with_subtitles:
            asyncio.run(
                generate_voice_edge_with_subtitles(
                    text, voice_path, subtitle_path
                )
            )
        else:
            asyncio.run(generate_voice_edge(text, voice_path))

        return {"voice_path": voice_path, "subtitle_path": subtitle_path}


def list_available_voices():
    """列出所有可用的中文语音"""
    import edge_tts

    async def _list():
        voices = await edge_tts.list_voices()
        cn_voices = [v for v in voices if v["Locale"].startswith("zh-")]
        for v in cn_voices:
            print(f"  {v['ShortName']:30s} | {v['Gender']:6s} | {v['Locale']}")
        return cn_voices

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
    args = parser.parse_args()

    if args.list_voices:
        print("可用的中文语音：")
        list_available_voices()
    elif args.text:
        result = generate_voice(args.text, with_subtitles=not args.no_subtitle)
        print(f"语音文件：{result['voice_path']}")
        if result["subtitle_path"]:
            print(f"字幕文件：{result['subtitle_path']}")
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
        title = Path(args.file).stem
        result = generate_voice(text, book_title=title, with_subtitles=not args.no_subtitle)
        print(f"语音文件：{result['voice_path']}")
        if result["subtitle_path"]:
            print(f"字幕文件：{result['subtitle_path']}")
    else:
        print("请使用 --text 或 --file 指定要合成的内容，或用 --list-voices 查看可用语音")
