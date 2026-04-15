"""
全局配置文件
使用前请将对应的 API Key 替换为你自己的值
"""

import os
import re
from pathlib import Path

# ============ 项目路径 ============
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
BGM_DIR = ASSETS_DIR / "bgm"
TEMPLATES_DIR = ASSETS_DIR / "templates"

# 旧的扁平目录（兼容单独使用各模块时的默认值）
SCRIPTS_DIR = OUTPUT_DIR / "scripts"
VOICES_DIR = OUTPUT_DIR / "voices"
VIDEOS_DIR = OUTPUT_DIR / "videos"


def get_book_output_dir(book_title: str) -> Path:
    """
    获取某本书的专属输出目录

    输出结构:
      output/被讨厌的勇气/
        ├── script.txt
        ├── voice.mp3
        ├── voice.srt
        ├── frames/
        └── video.mp4
    """
    # 移除危险字符，防止路径遍历
    safe_title = re.sub(r'[\\/:*?"<>|.\s]', '_', book_title).strip('_')
    if not safe_title:
        safe_title = "untitled"
    book_dir = (OUTPUT_DIR / safe_title).resolve()
    # 确保路径在 OUTPUT_DIR 内，防止路径遍历攻击
    if not str(book_dir).startswith(str(OUTPUT_DIR.resolve())):
        raise ValueError(f"非法书名导致路径逃逸: {book_title}")
    book_dir.mkdir(parents=True, exist_ok=True)
    return book_dir

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
# 支持: "edge" | "azure" | "offline" | "clone" (声音克隆)
TTS_PROVIDER = "clone"

# ---- 声音克隆配置(TTS_PROVIDER = "clone" 时生效) ----
# 克隆方案: "gpt_sovits" | "fish_audio"
VOICE_CLONE_ENGINE = "gpt_sovits"

# GPT-SoVITS 配置(本地部署)
# 指定当前使用的语音样本文件夹名称 (assets/voice_sample/ 下的子目录名)
VOICE_SAMPLE_NAME = os.getenv("VOICE_SAMPLE_NAME", "default")

GPT_SOVITS_API_URL = os.getenv("GPT_SOVITS_API_URL", "http://127.0.0.1:9880")
# 动态构建参考音频和文字的路径
GPT_SOVITS_REF_DIR = ASSETS_DIR / "voice_sample" / VOICE_SAMPLE_NAME
GPT_SOVITS_REF_AUDIO = str(GPT_SOVITS_REF_DIR / "sample.wav")
GPT_SOVITS_REF_TEXT_FILE = GPT_SOVITS_REF_DIR / "text.txt"

# 动态读取参考文字内容
def get_gpt_sovits_ref_text():
    if GPT_SOVITS_REF_TEXT_FILE.exists():
        try:
            return GPT_SOVITS_REF_TEXT_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    # 兜底旧配置内容
    return "很多人问我，为什么要读这么多书？其实读书不是为了记住每一个字，而是为了在某个瞬间，能用前人的智慧来对抗生活的平庸。今天我们要拆解的这本书叫《认知觉醒》。作者提到一个核心观点：人与人之间的根本差异，并不在于努力程度，而是在于思维模型。"

GPT_SOVITS_REF_TEXT = get_gpt_sovits_ref_text()

# Fish Audio 配置(在线API)
# 注册: https://fish.audio
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
# 你的声音模型ID(上传样本后在 Fish Audio 控制台获取)
FISH_AUDIO_MODEL_ID = os.getenv("FISH_AUDIO_MODEL_ID", "")

# ---- 数字人配置 ----
# 支持: "" (不使用) | "sadtalker" (本地) | "heygen" (在线API)
DIGITAL_HUMAN_ENGINE = ""

# 你的正面照片路径(用于驱动数字人)
DIGITAL_HUMAN_PHOTO = str(ASSETS_DIR / "avatar" / "photo.png")

# SadTalker 配置(本地部署，需要GPU)
# 部署文档: https://github.com/OpenTalker/SadTalker
SADTALKER_PATH = os.getenv("SADTALKER_PATH", "")

# HeyGen 配置(在线API，付费)
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")

# Edge TTS（免费，无需API Key）
EDGE_TTS_VOICE = "zh-CN-YunxiNeural"  # 男声，适合讲书
# 其他可选:
#   zh-CN-YunxiNeural     男声·年轻（支持 narration-relaxed/chat/cheerful 风格）
#   zh-CN-YunjianNeural   男声·沉稳（支持 narration-relaxed/documentary-narration 风格）
#   zh-CN-XiaoxiaoNeural  女声·温柔（支持 chat/cheerful/gentle/narration 等多种风格）
#   zh-CN-XiaoyiNeural    女声·活泼（支持 chat/cheerful 风格）
#   zh-CN-YunyangNeural   男声·新闻（支持 narration-professional 风格）

# 说话风格（让声音更自然，不再像机器朗读）
# 可选: "chat"(聊天) | "narration-relaxed"(轻松叙述) | "cheerful"(愉快)
#       "gentle"(温柔) | "documentary-narration"(纪录片) | ""(不设置)
EDGE_TTS_STYLE = "narration-relaxed"

# 风格强度 (0.01-2.0)，越大风格越明显，建议 0.8-1.5
EDGE_TTS_STYLE_DEGREE = 1.2

# 语速调节 ("-10%" 到 "+10%")，微调即可，太快太慢都不自然
EDGE_TTS_RATE = "+0%"

# 语调调节 ("-5%" 到 "+5%")
EDGE_TTS_PITCH = "+0%"

# 是否启用智能停顿（在标点处自动加自然停顿，让语音有呼吸感）
EDGE_TTS_SMART_PAUSE = True

EDGE_TTS_MAX_RETRIES = 3       # 连接失败时的最大重试次数
EDGE_TTS_RETRY_DELAY = 5       # 重试间隔（秒）

# 网络代理（如果 Edge TTS 连不上微软服务器，可以设置代理）
# 格式: "http://127.0.0.1:7890" 或 "socks5://127.0.0.1:1080"
HTTP_PROXY = os.getenv("HTTP_PROXY", "")
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "")

# Azure TTS
AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY", "")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION", "eastasia")

# ============ 视频合成配置 ============
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 竖屏 9:16
VIDEO_FPS = 30
VIDEO_BG_COLOR = (18, 18, 18)  # 深色背景

# ---- 画面模式 ----
# "cards"  — Pillow 生成的卡片画面(默认，无需外部资源)
# "video"  — 应景视频素材 + 大字幕(最主流的知识类风格)
# "digital_human" — 数字人口播(需要 DIGITAL_HUMAN_ENGINE)
VIDEO_BG_MODE = "coze"

# 新增：Coze API 配置 (当 VIDEO_BG_MODE = "coze" 时生效)
# 国内版: https://www.coze.cn / 国际版: https://www.coze.com
# 1. 注册 Coze，在个人中心创建/获取个人访问令牌 (Personal Access Token)
# 2. 创建一个工作流(Workflow)，发布后获取其 ID
COZE_API_KEY = os.getenv("COZE_API_KEY", "")
COZE_WORKFLOW_ID = os.getenv("COZE_WORKFLOW_ID", "")
COZE_API_BASE = os.getenv("COZE_API_BASE", "https://api.coze.cn/v1")  # 国内版
COZE_API_TIMEOUT = 180  # Coze 视频生成通常需要1-3分钟，设置长一点的超时

# ---- 视频素材配置(VIDEO_BG_MODE = "video" 时生效) ----
# 素材来源优先级: 本地目录 → Pexels API 在线搜索
BG_VIDEOS_DIR = ASSETS_DIR / "bg_videos"

# Pexels API（免费，高质量视频素材，注册即获 Key）
# 注册: https://www.pexels.com/api/
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# 视频素材搜索关键词映射(书籍分类 → 搜索关键词)
# Pexels 用英文搜索效果最好
BG_VIDEO_KEYWORDS = {
    "心理学": ["meditation", "thinking", "peaceful nature"],
    "自我成长": ["sunrise", "running", "mountain climbing"],
    "商业": ["city skyline", "office", "business"],
    "沟通": ["people talking", "coffee meeting", "conversation"],
    "历史": ["ancient architecture", "old books", "museum"],
    "哲学": ["stars", "ocean waves", "foggy forest"],
    "科学": ["space", "laboratory", "technology"],
    "文学": ["rain window", "autumn leaves", "old library"],
    "default": ["book reading", "coffee", "nature calm", "city night"],
}

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

# ============ 风控与安全策略 ============
# 单日最大发布数量（超过则停止发布，等待第二天）
DAILY_PUBLISH_LIMIT = 5

# 发布间隔（秒）：每条视频之间的等待时间，随机取 [最小值, 最大值]
PUBLISH_INTERVAL_MIN = 60
PUBLISH_INTERVAL_MAX = 180

# 操作间隔随机化（模拟人类操作，每步操作之间随机等待）
ACTION_DELAY_MIN = 1.0
ACTION_DELAY_MAX = 3.0

# 每小时休息（发布N条后暂停一段时间）
PUBLISH_BATCH_SIZE = 3           # 每发布N条休息一次
PUBLISH_REST_MIN = 300           # 休息最短（秒）= 5分钟
PUBLISH_REST_MAX = 600           # 休息最长（秒）= 10分钟

# 发布记录文件（记录每日发布数量，用于限流）
PUBLISH_LOG_PATH = BASE_DIR / "publish_log.json"

# 敏感词检测（发布前自动检测标题和文案中的敏感词）
SENSITIVE_WORDS_ENABLED = True
# 自定义敏感词文件（每行一个词，可自行扩充）
SENSITIVE_WORDS_PATH = BASE_DIR / "sensitive_words.txt"

# 跨平台差异化策略
# 多平台发布时，自动对标题做微调（加前缀/后缀/换表述），避免被判重复
CROSS_PLATFORM_VARIATION = True

# ============ BGM 配置 ============
# BGM 来源: "local"(本地匹配) | "download"(自动下载) | "douyin"(发布时用抖音音乐)
BGM_SOURCE = "download"

# Pixabay API（免费注册获取 Key: https://pixabay.com/api/docs/）
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

# Freesound API（免费注册获取 Key: https://freesound.org/apiv2/apply/）
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY", "")

# ============ 书单自动采集配置 ============
# 书单最少保持多少本 pending 状态的书（低于此数量自动补充）
BOOK_LIST_MIN_PENDING = 5

# 每次自动补充多少本
BOOK_LIST_REFILL_COUNT = 10

# 采集来源优先级: "douban"(豆瓣热门) → "ai"(AI推荐) → 都失败则跳过
# 目标分类（采集时会轮流采集这些分类的书）
BOOK_TARGET_CATEGORIES = [
    "心理学", "自我成长", "商业", "沟通",
    "历史", "哲学", "科学", "文学",
]

# ============ 一书多集配置 ============
# 每本书生成多少集视频（每集一个独立选题/角度）
EPISODES_PER_BOOK = 5

# 默认视频时长（秒）
# 书籍蒸馏定位：90秒 = 高信息密度单点蒸馏，兼顾完播率
DEFAULT_DURATION = 90

# ============ 文案 Prompt 模板 ============

# 选题规划 Prompt: 让 AI 为一本书规划多个视频选题
TOPIC_PLAN_PROMPT = """你是"书籍蒸馏"账号的内容策划师。我们的定位是：把一整本书蒸馏成几分钟的精华，帮观众用最短时间吸收一本书最有价值的部分。

请为《{book_title}》这本书规划 {episode_count} 个抖音短视频选题。

书籍简介: {book_desc}

要求:
1. 每个选题要有独立的切入角度，不能重复
2. 选题要有"蒸馏感"——把厚重内容提炼成一个锐利的点
3. 覆盖书中不同的精华内容，不要集中在一个点上
4. 选题类型可以多样化，比如:
   - 核心蒸馏（这本书最值钱的1个观点）
   - 金句蒸馏（书中最扎心的几句话）
   - 方法蒸馏（书中可以直接用的方法/技巧）
   - 故事蒸馏（书中最有趣的故事或案例）
   - 反常识蒸馏（书中违反直觉的观点）
   - 一句话蒸馏（一句话说清这本书讲了什么）
   - 对比型（读这本书前 vs 后的认知差距）
   - 问题解答型（你有没有XXX困惑？这本书给出了答案）

请严格按以下 JSON 格式返回（不要返回其他任何内容）:
[
  {{
    "episode": 1,
    "title": "视频标题（用于抖音发布，要有吸引力，15字以内）",
    "angle": "切入角度的简短描述",
    "type": "选题类型（如: 核心蒸馏/金句蒸馏/方法蒸馏/故事蒸馏/反常识蒸馏等）",
    "key_points": "这集要讲的核心内容（50字以内）"
  }}
]"""

# 单集文案 Prompt
SCRIPT_PROMPT_TEMPLATE = """你是"书籍蒸馏"账号的文案创作者。我们的风格是：用最精炼的语言把一本书的精华蒸馏出来，让观众几分钟就能吸收一本书最有价值的部分。

请帮我为《{book_title}》这本书写一段{duration}秒的抖音短视频文案。

书籍简介: {book_desc}

本集选题: {episode_title}
切入角度: {episode_angle}
选题类型: {episode_type}
核心内容: {episode_key_points}

要求:
1. 开头3秒要有强烈的钩子（引起好奇心，可以用反问/悬念/颠覆认知的方式）
2. 紧扣本集选题展开，不要泛泛而谈
3. 结尾有强有力的金句总结
4. 口语化，像在跟朋友聊天，避免书面语5. 总字数控制在{word_count}字左右（按照每秒4个字的语速）
6. 不要出现"大家好"等开场白，直接进入主题
7. 体现"蒸馏"感：信息密度高，每句话都有干货，没有废话

请只输出文案正文，不要输出标题或其他说明。"""


# ============ 启动配置校验 ============

def validate_config() -> list[str]:
    """
    校验关键配置项，返回警告信息列表。
    在 main.py 启动时调用，提前发现配置问题。
    """
    warnings = []

    # LLM API Key 校验
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY in ("your-api-key-here", ""):
        warnings.append("OPENAI_API_KEY 未配置，文案生成将失败。请设置环境变量或编辑 config.py")
    if LLM_PROVIDER == "claude" and CLAUDE_API_KEY in ("your-claude-api-key-here", ""):
        warnings.append("CLAUDE_API_KEY 未配置，文案生成将失败。请设置环境变量或编辑 config.py")

    # TTS 配置校验
    if TTS_PROVIDER == "azure" and not AZURE_TTS_KEY:
        warnings.append("TTS_PROVIDER='azure' 但 AZURE_TTS_KEY 未配置，将无法生成语音")
    if TTS_PROVIDER == "clone":
        if VOICE_CLONE_ENGINE == "fish_audio" and (not FISH_AUDIO_API_KEY or not FISH_AUDIO_MODEL_ID):
            warnings.append("声音克隆使用 fish_audio 但 API Key 或 Model ID 未配置")
        if VOICE_CLONE_ENGINE == "gpt_sovits" and not Path(GPT_SOVITS_REF_AUDIO).exists():
            warnings.append(f"GPT-SoVITS 参考音频不存在: {GPT_SOVITS_REF_AUDIO}")

    # Edge TTS 风格强度范围
    if not (0.01 <= EDGE_TTS_STYLE_DEGREE <= 2.0):
        warnings.append(f"EDGE_TTS_STYLE_DEGREE={EDGE_TTS_STYLE_DEGREE} 超出范围(0.01-2.0)")

    # BGM 配置校验
    if BGM_SOURCE == "download" and not PIXABAY_API_KEY and not FREESOUND_API_KEY:
        warnings.append("BGM_SOURCE='download' 但 PIXABAY_API_KEY 和 FREESOUND_API_KEY 均未配置")

    # 视频背景模式校验
    if VIDEO_BG_MODE == "video":
        has_local = BG_VIDEOS_DIR.exists() and any(BG_VIDEOS_DIR.rglob("*.mp4"))
        if not has_local and not PEXELS_API_KEY:
            warnings.append(
                "VIDEO_BG_MODE='video' 但无本地素材且 PEXELS_API_KEY 未配置。"
                "将降级为卡片模式。配置方法: https://www.pexels.com/api/ 免费注册"
            )
    if VIDEO_BG_MODE == "digital_human" and not DIGITAL_HUMAN_ENGINE:
        warnings.append("VIDEO_BG_MODE='digital_human' 但 DIGITAL_HUMAN_ENGINE 未配置")

    # FFmpeg 校验
    import shutil
    if not shutil.which("ffmpeg"):
        warnings.append("FFmpeg 未找到，视频合成将失败。请安装 FFmpeg 并加入 PATH")

    return warnings
