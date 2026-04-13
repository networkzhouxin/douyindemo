# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

书籍蒸馏 - 抖音全自动内容生产线 (Book Distillation - Douyin Auto-Production Pipeline)

账号定位："书籍蒸馏"——把任意一本书的精华蒸馏成几分钟的短视频，帮观众用最短时间吸收最有价值的内容。

核心理念：一本书拆成多集，每集90秒蒸馏一个精华点（核心观点/金句/方法论/故事/反常识等）。

**Book Collection → Topic Planning (1 book, multiple episodes) → AI Script → TTS Voice → Video Synthesis → Auto-Publish**

## Quick Start Commands

```bash
# Full auto mode: 1 book x 5 episodes = 5 videos (each 90s)
python main.py auto

# N books x M episodes
python main.py auto --books 3 --episodes 8

# Specific book
python main.py book "被讨厌的勇气" --episodes 10

# Custom duration (default 90s)
python main.py auto --duration 120

# View topic plan only
python main.py plan "认知觉醒"

# View stats
python main.py stats

# Auto-publish after generation
python main.py auto --books 1 --publish

# Video background: setup & preview
python bg_video.py setup
python bg_video.py search "peaceful nature" --count 5
```

## Module Commands

```bash
# Script generation
python generate_script.py --book "书名" --episodes 5

# Voice synthesis
python generate_voice.py --text "文案" --list-voices

# Video synthesis
python generate_video.py --voice xxx.mp3 --subtitle xxx.srt --title "书名"

# Background video material
python bg_video.py setup                     # Create directory structure
python bg_video.py search "calm piano"       # Search Pexels
python bg_video.py download --category 心理学  # Batch download by category

# BGM matching
python bgm_matcher.py match --book "书名"

# Auto-publish (first time requires login)
python auto_publish.py login
python auto_publish.py upload --video xxx.mp4 --title "标题" --tags 书籍蒸馏 好书推荐
```

## Architecture

```
main.py (入口)
├── book_crawler.py      # 书单采集 (豆瓣 + AI 推荐)
├── generate_script.py   # 选题规划 + AI 文案 (一书多集蒸馏)
├── generate_voice.py    # TTS 语音 (Edge/Azure/离线/声音克隆)
├── generate_images.py   # 画面帧生成 (Pillow, 5 套配色, cards 模式)
├── bg_video.py          # 视频素材获取 (本地 + Pexels API, video 模式)
├── generate_video.py    # 视频合成 (MoviePy, 3种画面模式)
├── digital_human.py     # 数字人 (SadTalker/HeyGen)
├── bgm_matcher.py       # BGM 智能匹配
├── auto_publish.py      # 自动发布 (Playwright)
└── safety.py            # 风控 (敏感词/限流)
```

## Configuration

All configuration in `config.py`:

- **LLM**: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` (supports OpenAI/Claude/通义千问/DeepSeek/Kimi)
- **TTS**: `TTS_PROVIDER` = "edge" | "azure" | "offline" | "clone"
- **Voice Clone**: `VOICE_CLONE_ENGINE` = "gpt_sovits" | "fish_audio"
- **Video BG Mode**: `VIDEO_BG_MODE` = "video" (default) | "cards" | "digital_human"
- **Video Material**: `PEXELS_API_KEY` (free), `BG_VIDEOS_DIR`, `BG_VIDEO_KEYWORDS`
- **Video**: `VIDEO_WIDTH=1080`, `VIDEO_HEIGHT=1920` (竖屏 9:16)
- **Duration**: `DEFAULT_DURATION=90` (每集90秒，约360字)
- **Episodes**: `EPISODES_PER_BOOK=5` (每本书蒸馏5个角度)
- **Publish**: `DAILY_PUBLISH_LIMIT=5`, `PUBLISH_INTERVAL_*` (random delay)
- **Safety**: `SENSITIVE_WORDS_ENABLED=True`
- **Startup Validation**: `validate_config()` checks API keys, FFmpeg, TTS config, video mode on startup

## Video Background Modes

Three modes, switch via `VIDEO_BG_MODE` in `config.py`:

| Mode | Description | Best For |
|------|-------------|----------|
| `"video"` (default) | 应景视频素材 + 半透明暗层 + 大字幕 | 最主流知识类风格 |
| `"cards"` | Pillow 生成卡片画面 | 无外部资源时兜底 |
| `"digital_human"` | 数字人口播 | 需要 GPU 或付费 API |

Video mode fallback: `video` → `cards` (if no material available)

Material sources: local `assets/bg_videos/` → Pexels API (auto-download & cache)

## Output Structure

```
output/被讨厌的勇气/
├── topic_plan.json          # 选题规划 (蒸馏角度)
├── ep01_你为什么总在意别人的看法/
│   ├── script.txt           # 文案
│   ├── voice.mp3            # 语音
│   ├── voice.srt            # 字幕
│   ├── bg_cache/            # 视频素材缓存 (video 模式)
│   ├── frames/              # 画面帧 (cards 模式)
│   └── video.mp4            # 最终视频 (90s)
└── report.json              # 生成报告
```

## Key Notes

1. **Environment**: Requires FFmpeg, Playwright (for auto-publish), Python 3.10+
2. **LLM API**: Set via env vars (`OPENAI_API_KEY`, `OPENAI_BASE_URL`) or edit `config.py`
3. **Video Mode**: Default `"video"` — set `PEXELS_API_KEY` for auto material, or put MP4s in `assets/bg_videos/`
4. **Edge TTS**: If connection fails (common in China), set proxy or use `TTS_PROVIDER="offline"`
5. **Voice Clone**: Record 10-30s sample → `assets/voice_sample/sample.wav`, set `TTS_PROVIDER="clone"`
6. **Auto-publish**: Douyin UI changes frequently; selectors in `auto_publish.py` may need updates
7. **Brand**: All prompts, tags, slogans use "书籍蒸馏" branding — maintain consistency when modifying
