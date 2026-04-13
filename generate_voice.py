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
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from config import (
    TTS_PROVIDER,
    EDGE_TTS_VOICE,
    EDGE_TTS_STYLE,
    EDGE_TTS_STYLE_DEGREE,
    EDGE_TTS_RATE,
    EDGE_TTS_PITCH,
    EDGE_TTS_SMART_PAUSE,
    EDGE_TTS_MAX_RETRIES,
    EDGE_TTS_RETRY_DELAY,
    HTTP_PROXY,
    HTTPS_PROXY,
    AZURE_TTS_KEY,
    AZURE_TTS_REGION,
    VOICES_DIR,
    get_book_output_dir,
    VOICE_CLONE_ENGINE,
    GPT_SOVITS_API_URL,
    GPT_SOVITS_REF_AUDIO,
    GPT_SOVITS_REF_TEXT,
    FISH_AUDIO_API_KEY,
    FISH_AUDIO_MODEL_ID,
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
# SSML 生成（让声音更自然）
# ============================================================

def _add_smart_pauses(text: str) -> str:
    """
    智能添加停顿标记，让语音有呼吸感

    规则：
    - 句号/问号/感叹号后：较长停顿（500ms）
    - 逗号/顿号后：短停顿（250ms）
    - 分号/冒号后：中等停顿（350ms）
    - 省略号后：思考停顿（600ms）
    - 破折号后：转折停顿（400ms）
    """
    if not EDGE_TTS_SMART_PAUSE:
        return text

    # 用 SSML break 标签替换标点后的空白
    replacements = [
        (r'([。！？!?])\s*', r'\1<break time="500ms"/>'),
        (r'([，,、])\s*', r'\1<break time="250ms"/>'),
        (r'([；;：:])\s*', r'\1<break time="350ms"/>'),
        (r'(……|\.\.\.)\s*', r'\1<break time="600ms"/>'),
        (r'([——\-\-])\s*', r'\1<break time="400ms"/>'),
    ]

    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    return text


def _build_ssml(text: str, voice: str = None) -> str:
    """
    构建 SSML 文档，让 Edge TTS 输出更自然的语音

    SSML 功能：
    - mstts:express-as: 设置说话风格（聊天/叙述/愉快等）
    - prosody: 控制语速、语调
    - break: 自然停顿
    """
    voice = voice or EDGE_TTS_VOICE

    # 添加智能停顿
    text_with_pauses = _add_smart_pauses(text)

    # 转义 XML 特殊字符（但保留已插入的 SSML break 标签）
    # 先用占位符保护 break 标签
    import uuid
    placeholder = f"__BREAK_{uuid.uuid4().hex[:8]}__"
    # 匹配完整的 <break time="..."/> 标签
    break_tags = re.findall(r'<break\s+time="[^"]*"\s*/>', text_with_pauses)
    for i, tag in enumerate(break_tags):
        text_with_pauses = text_with_pauses.replace(tag, f"{placeholder}{i}{placeholder}", 1)
    # 转义所有 XML 特殊字符
    text_with_pauses = text_with_pauses.replace("&", "&amp;")
    text_with_pauses = text_with_pauses.replace("<", "&lt;")
    text_with_pauses = text_with_pauses.replace(">", "&gt;")
    text_with_pauses = text_with_pauses.replace('"', "&quot;")
    text_with_pauses = text_with_pauses.replace("'", "&apos;")
    # 恢复 break 标签
    for i, tag in enumerate(break_tags):
        text_with_pauses = text_with_pauses.replace(f"{placeholder}{i}{placeholder}", tag)

    # 构建 prosody 属性
    prosody_attrs = []
    if EDGE_TTS_RATE and EDGE_TTS_RATE != "+0%":
        prosody_attrs.append(f'rate="{EDGE_TTS_RATE}"')
    if EDGE_TTS_PITCH and EDGE_TTS_PITCH != "+0%":
        prosody_attrs.append(f'pitch="{EDGE_TTS_PITCH}"')
    prosody_str = " ".join(prosody_attrs)

    # 构建内容部分
    content = text_with_pauses

    # 包裹 express-as（说话风格）
    if EDGE_TTS_STYLE:
        style_degree = f' styledegree="{EDGE_TTS_STYLE_DEGREE}"' if EDGE_TTS_STYLE_DEGREE else ""
        content = (
            f'<mstts:express-as style="{EDGE_TTS_STYLE}"{style_degree}>'
            f'{content}'
            f'</mstts:express-as>'
        )

    # 包裹 prosody（语速语调）
    if prosody_str:
        content = f'<prosody {prosody_str}>{content}</prosody>'

    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" '
        f'xml:lang="zh-CN">'
        f'<voice name="{voice}">'
        f'{content}'
        f'</voice>'
        f'</speak>'
    )

    return ssml


def _apply_pauses_as_spaces(text: str) -> str:
    """
    通过在标点后插入短句分隔来模拟停顿
    Edge TTS 会在自然断句处自动加入停顿，
    我们通过调整文本格式来强化这个效果
    """
    if not EDGE_TTS_SMART_PAUSE:
        return text

    # 在句末标点后加换行（Edge TTS 会在换行处自然停顿）
    text = re.sub(r'([。！？!?])\s*', r'\1\n', text)
    # 省略号后加停顿
    text = re.sub(r'(……|\.\.\.)\s*', r'\1\n', text)
    # 清理多余换行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ============================================================
# Edge TTS（带 SSML + 重试 + 代理）
# ============================================================

def _setup_proxy():
    """设置网络代理环境变量"""
    if HTTP_PROXY:
        os.environ["HTTP_PROXY"] = HTTP_PROXY
        os.environ["http_proxy"] = HTTP_PROXY
    if HTTPS_PROXY:
        os.environ["HTTPS_PROXY"] = HTTPS_PROXY
        os.environ["https_proxy"] = HTTPS_PROXY


async def generate_voice_edge(text: str, output_path: Path, voice: str = None):
    """使用 Edge TTS 生成自然语音（带重试）"""
    import edge_tts

    _setup_proxy()
    voice = voice or EDGE_TTS_VOICE
    tts_text = _apply_pauses_as_spaces(text)

    last_error = None
    for attempt in range(1, EDGE_TTS_MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(
                tts_text,
                voice,
                rate=EDGE_TTS_RATE,
                pitch=EDGE_TTS_PITCH,
            )
            await communicate.save(str(output_path))
            return
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
    """使用 Edge TTS 生成自然语音 + SRT 字幕（带重试）"""
    import edge_tts

    _setup_proxy()
    voice = voice or EDGE_TTS_VOICE

    tts_text = _apply_pauses_as_spaces(text)

    last_error = None
    for attempt in range(1, EDGE_TTS_MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(
                tts_text,
                voice,
                rate=EDGE_TTS_RATE,
                pitch=EDGE_TTS_PITCH,
            )
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

            # 保存音频（原子写入：先写临时文件再重命名）
            tmp_audio = output_path.with_suffix(".tmp")
            with open(tmp_audio, "wb") as f:
                for chunk in audio_chunks:
                    f.write(chunk)
            tmp_audio.replace(output_path)

            # 保存字幕（原子写入）
            tmp_srt = subtitle_path.with_suffix(".tmp")
            with open(tmp_srt, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_content))
            tmp_srt.replace(subtitle_path)

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
# 声音克隆: GPT-SoVITS (本地部署)
# ============================================================

def generate_voice_gpt_sovits(text: str, output_path: Path):
    """
    使用 GPT-SoVITS 克隆声音生成语音

    前提: 已在本地部署 GPT-SoVITS 并启动 API 服务
    部署: https://github.com/RVC-Boss/GPT-SoVITS
    启动: python api.py (默认端口 9880)

    录音要求:
    - 10-30秒清晰人声(无背景噪音)
    - WAV格式, 16kHz+, 单声道
    - 放到 assets/voice_sample/sample.wav
    """
    import urllib.request
    import urllib.parse

    ref_audio = Path(GPT_SOVITS_REF_AUDIO)
    if not ref_audio.exists():
        raise FileNotFoundError(
            f"参考音频不存在: {ref_audio}\n"
            f"请录制10-30秒人声样本放到 assets/voice_sample/sample.wav"
        )

    params = urllib.parse.urlencode({
        "refer_wav_path": str(ref_audio),
        "prompt_text": GPT_SOVITS_REF_TEXT,
        "prompt_language": "zh",
        "text": text,
        "text_language": "zh",
    })
    url = f"{GPT_SOVITS_API_URL}?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio_data = resp.read()

        # 1. 先保存原始音频
        raw_path = output_path.with_suffix(".raw.wav")
        with open(raw_path, "wb") as f:
            f.write(audio_data)

        # 2. 使用 FFmpeg 自动切除末尾和开头的静音 (静音阈值 -50dB，持续 0.5s 以上视为静音)
        # silenceremove=start_periods=1:start_threshold=-50dB:stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB
        import subprocess
        import shutil

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_path),
            "-af", "silenceremove=start_periods=1:start_threshold=-50dB:stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB",
            str(output_path)
        ]
        
        # 检查 ffmpeg 是否可用
        if shutil.which("ffmpeg"):
            result = subprocess.run(ffmpeg_cmd, capture_output=True)
            if result.returncode != 0:
                err_msg = result.stderr.decode("utf-8", errors="replace")
                print(f"  [警告] FFmpeg 切除静音失败: {err_msg}")
                # 失败则回退到原始音频
                shutil.copy(raw_path, output_path)
        else:
            # 没有 ffmpeg 则直接重命名
            raw_path.replace(output_path)

        # 清理临时文件
        if raw_path.exists():
            raw_path.unlink()

        print(f"  [GPT-SoVITS] 声音克隆完成 (已自动切除末尾静音)")
    except Exception as e:
        raise RuntimeError(
            f"GPT-SoVITS 调用失败: {e}\n"
            f"请确认 GPT-SoVITS API 已启动: {GPT_SOVITS_API_URL}"
        ) from e


# ============================================================
# 声音克隆: Fish Audio (在线API)
# ============================================================

def generate_voice_fish_audio(text: str, output_path: Path):
    """
    使用 Fish Audio 在线API克隆声音

    步骤:
    1. 注册 https://fish.audio
    2. 上传你的声音样本，创建声音模型
    3. 获取 API Key 和模型 ID，填入 config.py
    """
    import urllib.request

    if not FISH_AUDIO_API_KEY:
        raise ValueError("未配置 FISH_AUDIO_API_KEY，请在 config.py 或环境变量中设置")
    if not FISH_AUDIO_MODEL_ID:
        raise ValueError("未配置 FISH_AUDIO_MODEL_ID，请先在 Fish Audio 上传声音样本创建模型")

    url = "https://api.fish.audio/v1/tts"
    payload = json.dumps({
        "text": text,
        "reference_id": FISH_AUDIO_MODEL_ID,
        "format": "mp3",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio_data = resp.read()

        # 原子写入
        tmp_path = output_path.with_suffix(".tmp")
        with open(tmp_path, "wb") as f:
            f.write(audio_data)
        tmp_path.replace(output_path)

        print(f"  [Fish Audio] 声音克隆完成")
    except Exception as e:
        raise RuntimeError(f"Fish Audio 调用失败: {e}") from e


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
    try:
        engine.runAndWait()
    except Exception as e:
        raise RuntimeError(f"离线 TTS 引擎执行失败: {e}") from e

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
    output_dir: Path = None,
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

    if output_dir is None:
        output_dir = get_book_output_dir(book_title)
    output_dir.mkdir(parents=True, exist_ok=True)

    voice_path = output_dir / "voice.mp3"
    subtitle_path = output_dir / "voice.srt" if with_subtitles else None

    # 声音克隆
    if TTS_PROVIDER == "clone":
        try:
            if VOICE_CLONE_ENGINE == "fish_audio":
                generate_voice_fish_audio(text, voice_path)
            else:
                generate_voice_gpt_sovits(text, voice_path)
            # 声音克隆没有逐字时间戳，用估算字幕
            if with_subtitles and subtitle_path:
                generate_offline_subtitle(text, subtitle_path)
            return {"voice_path": voice_path, "subtitle_path": subtitle_path}
        except Exception as e:
            print(f"  声音克隆失败: {e}")
            print(f"  降级到 Edge TTS...")

    # Azure TTS
    if TTS_PROVIDER == "azure":
        if not AZURE_TTS_KEY:
            print("  Azure TTS Key 未配置，降级到 Edge TTS")
        else:
            generate_voice_azure(text, voice_path)
            return {"voice_path": voice_path, "subtitle_path": None}

    # 离线 TTS
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
    try:
        return asyncio.run(_list())
    except Exception as e:
        print(f"  获取语音列表失败: {e}")
        print(f"  可能是网络问题，请检查代理设置或网络连接")
        return []


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
