"""
全局配置文件
使用前请将对应的 API Key 替换为你自己的值
"""

import os
from pathlib import Path

# ============ 项目路径 ============
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
SCRIPTS_DIR = OUTPUT_DIR / "scripts"
VOICES_DIR = OUTPUT_DIR / "voices"
VIDEOS_DIR = OUTPUT_DIR / "videos"
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
BGM_DIR = ASSETS_DIR / "bgm"
TEMPLATES_DIR = ASSETS_DIR / "templates"

# 确保输出目录存在
for d in [SCRIPTS_DIR, VOICES_DIR, VIDEOS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============ AI 文案生成配置 ============
# 支持: "openai" (兼容ChatGPT/通义千问等) | "claude"
LLM_PROVIDER = "openai"

# OpenAI 兼容接口配置（也适用于通义千问、Kimi、DeepSeek等）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Claude 配置
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "your-claude-api-key-here")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6-20250514")

# ============ TTS 语音合成配置 ============
# 支持: "edge" (微软Edge免费TTS) | "azure" | "volcengine" (火山引擎/豆包)
TTS_PROVIDER = "edge"

# Edge TTS（免费，无需API Key）
EDGE_TTS_VOICE = "zh-CN-YunxiNeural"  # 男声，适合讲书
# 其他可选: zh-CN-XiaoxiaoNeural(女声), zh-CN-YunjianNeural(男声沉稳)

# Azure TTS
AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY", "")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION", "eastasia")

# ============ 视频合成配置 ============
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 竖屏 9:16
VIDEO_FPS = 30
VIDEO_BG_COLOR = (18, 18, 18)  # 深色背景

# 字幕样式
SUBTITLE_FONT_SIZE = 48
SUBTITLE_FONT_COLOR = "white"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 2

# 标题样式
TITLE_FONT_SIZE = 64
TITLE_FONT_COLOR = "yellow"

# ============ 发布配置 ============
# 抖音 Cookie 文件路径（首次需要手动登录获取）
DOUYIN_COOKIE_PATH = BASE_DIR / "douyin_cookie.json"

# 发布时间设置（24小时制）
PUBLISH_TIMES = ["07:30", "12:00", "20:30"]

# ============ 文案 Prompt 模板 ============
SCRIPT_PROMPT_TEMPLATE = """请帮我把《{book_title}》这本书的核心观点提炼成一段{duration}秒的抖音短视频文案。

书籍简介：{book_desc}

要求：
1. 开头3秒要有强烈的钩子（引起好奇心，可以用反问/悬念/颠覆认知的方式）
2. 中间讲2-3个核心观点，每个观点用生动的例子或比喻辅助说明
3. 结尾有金句总结 + 引导关注（如"关注我，每天带你读一本好书"）
4. 口语化，像在跟朋友聊天，避免书面语
5. 总字数控制在{word_count}字左右（按照每秒4个字的语速）
6. 不要出现"大家好"等开场白，直接进入主题

请只输出文案正文，不要输出标题或其他说明。"""
