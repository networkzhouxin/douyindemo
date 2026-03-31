"""
BGM 智能匹配模块
根据书籍分类/文案情绪自动选择或生成匹配的背景音乐

三种模式：
1. rule  — 基于规则匹配：书籍分类 → 情绪标签 → 对应 BGM 子目录
2. ai    — AI 分析文案情绪后匹配本地 BGM
3. suno  — 调用 Suno AI 为每本书生成专属原创 BGM
"""

import json
import random
from pathlib import Path

from config import (
    BGM_DIR,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
)

# ============================================================
# 情绪-分类映射表
# BGM 按情绪分子目录存放，例如 assets/bgm/calm/xxx.mp3
# 如果不分子目录，也可以在文件名中包含情绪标签如 calm_piano_01.mp3
# ============================================================

MOOD_CATEGORIES = {
    "calm": {
        "name": "平静舒缓",
        "description": "轻柔的钢琴/吉他，适合深度阅读、心理学、哲学类",
        "keywords": ["钢琴", "轻音乐", "舒缓", "安静"],
    },
    "inspiring": {
        "name": "励志振奋",
        "description": "节奏明快、积极向上，适合成长、效率、商业类",
        "keywords": ["励志", "积极", "振奋", "能量"],
    },
    "emotional": {
        "name": "感性温暖",
        "description": "温暖的弦乐/人声哼唱，适合情感、文学、人生感悟类",
        "keywords": ["温暖", "感动", "深情", "人声"],
    },
    "thoughtful": {
        "name": "沉思深邃",
        "description": "带有留白和空间感，适合思维、哲学、科学类",
        "keywords": ["深沉", "思考", "空灵", "氛围"],
    },
    "energetic": {
        "name": "活力动感",
        "description": "节奏感强，适合书单推荐、快节奏盘点类视频",
        "keywords": ["节奏", "动感", "活泼", "快节奏"],
    },
}

# 书籍分类 → 情绪的默认映射
CATEGORY_TO_MOOD = {
    "心理学": "calm",
    "自我成长": "inspiring",
    "自我管理": "inspiring",
    "学习方法": "inspiring",
    "沟通": "emotional",
    "情感": "emotional",
    "文学": "emotional",
    "小说": "emotional",
    "财富/智慧": "thoughtful",
    "投资/智慧": "thoughtful",
    "商业": "inspiring",
    "历史": "thoughtful",
    "哲学": "thoughtful",
    "科学": "thoughtful",
    "效率": "energetic",
    "书单推荐": "energetic",
}


# ============================================================
# 方案 1：基于规则匹配
# ============================================================

def match_bgm_by_rule(book_category: str) -> Path | None:
    """
    根据书籍分类，按规则匹配 BGM

    匹配优先级：
    1. assets/bgm/{mood}/ 子目录下随机选一首
    2. assets/bgm/ 根目录下文件名包含 mood 关键词的
    3. assets/bgm/ 根目录随机选一首（兜底）
    """
    mood = CATEGORY_TO_MOOD.get(book_category, "calm")
    return _find_bgm_by_mood(mood)


def _find_bgm_by_mood(mood: str) -> Path | None:
    """在 BGM 目录中查找匹配情绪的音乐文件"""
    audio_exts = ("*.mp3", "*.wav", "*.m4a", "*.ogg")

    # 优先级1：子目录
    mood_dir = BGM_DIR / mood
    if mood_dir.exists():
        files = []
        for ext in audio_exts:
            files.extend(mood_dir.glob(ext))
        if files:
            return random.choice(files)

    # 优先级2：文件名包含情绪关键词
    mood_info = MOOD_CATEGORIES.get(mood, {})
    keywords = mood_info.get("keywords", []) + [mood]
    all_files = []
    for ext in audio_exts:
        all_files.extend(BGM_DIR.glob(ext))

    matched = [f for f in all_files if any(kw in f.stem for kw in keywords)]
    if matched:
        return random.choice(matched)

    # 优先级3：随机兜底
    if all_files:
        return random.choice(all_files)

    return None


# ============================================================
# 方案 2：AI 分析文案情绪后匹配
# ============================================================

MOOD_ANALYSIS_PROMPT = """分析以下短视频文案的整体情绪氛围，从下列选项中选择最匹配的一个：

选项：
- calm（平静舒缓）：适合深度阅读、心理学、哲学，配轻柔钢琴/吉他
- inspiring（励志振奋）：适合成长、效率、商业，配节奏明快积极的音乐
- emotional（感性温暖）：适合情感、文学、人生感悟，配温暖弦乐
- thoughtful（沉思深邃）：适合思维、哲学、科学，配空灵有留白的音乐
- energetic（活力动感）：适合书单推荐、快节奏盘点，配节奏感强的音乐

文案内容：
{script}

请只回复一个英文单词（calm/inspiring/emotional/thoughtful/energetic），不要回复其他任何内容。"""


def analyze_mood_with_ai(script: str) -> str:
    """让 AI 分析文案情绪，返回情绪标签"""
    prompt = MOOD_ANALYSIS_PROMPT.format(script=script[:500])

    try:
        if LLM_PROVIDER == "claude":
            mood = _analyze_with_claude(prompt)
        else:
            mood = _analyze_with_openai(prompt)

        mood = mood.strip().lower()
        if mood in MOOD_CATEGORIES:
            return mood
    except Exception as e:
        print(f"AI 情绪分析失败: {e}，使用默认情绪 calm")

    return "calm"


def _analyze_with_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=10,
    )
    return response.choices[0].message.content.strip()


def _analyze_with_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def match_bgm_by_ai(script: str) -> tuple[Path | None, str]:
    """
    用 AI 分析文案情绪，然后匹配本地 BGM

    Returns:
        (bgm_path, mood)
    """
    mood = analyze_mood_with_ai(script)
    print(f"AI 情绪分析结果: {mood} ({MOOD_CATEGORIES[mood]['name']})")
    bgm_path = _find_bgm_by_mood(mood)
    return bgm_path, mood


# ============================================================
# 方案 3：Suno AI 生成原创 BGM
# ============================================================

SUNO_MUSIC_PROMPT_TEMPLATE = """为一个读书类短视频生成背景音乐。

书名：《{book_title}》
分类：{category}
文案情绪：{mood_desc}

要求：
- 纯音乐，无人声
- 时长约 {duration} 秒
- 风格：{style}
- 节奏适中，不抢语音的主体地位
- 适合作为口播短视频的背景音乐"""


def generate_bgm_prompt(book: dict, mood: str = None) -> str:
    """为 Suno AI 生成音乐描述 Prompt"""
    if mood is None:
        mood = CATEGORY_TO_MOOD.get(book.get("category", ""), "calm")

    mood_info = MOOD_CATEGORIES.get(mood, MOOD_CATEGORIES["calm"])

    style_map = {
        "calm": "轻柔钢琴曲，带有少量弦乐点缀",
        "inspiring": "明快的吉他弹奏配合轻鼓点",
        "emotional": "温暖的小提琴旋律，带有钢琴伴奏",
        "thoughtful": "空灵的环境音乐，带有电子氛围感",
        "energetic": "轻快的电子节拍，带有律动感",
    }

    return SUNO_MUSIC_PROMPT_TEMPLATE.format(
        book_title=book.get("title", ""),
        category=book.get("category", ""),
        mood_desc=mood_info["name"],
        duration=60,
        style=style_map.get(mood, style_map["calm"]),
    )


def generate_bgm_with_suno(book: dict, mood: str = None) -> str:
    """
    调用 Suno AI 生成背景音乐（需要 Suno API 或手动操作）

    由于 Suno 目前没有公开稳定的 API，这里生成 Prompt 供手动使用。
    如果有 API 访问权限，可以扩展此函数。

    Returns:
        生成的 Suno Prompt 文本
    """
    prompt = generate_bgm_prompt(book, mood)
    print("=" * 50)
    print("请将以下 Prompt 粘贴到 Suno AI (suno.com) 生成音乐：")
    print("=" * 50)
    print(prompt)
    print("=" * 50)
    print(f"\n生成后将 MP3 文件保存到: {BGM_DIR}/")
    return prompt


# ============================================================
# 统一入口
# ============================================================

def match_bgm(
    book: dict = None,
    script: str = None,
    mode: str = "auto",
) -> Path | None:
    """
    智能匹配 BGM 的统一入口

    Args:
        book: 书籍信息（用于规则匹配）
        script: 文案文本（用于 AI 情绪分析）
        mode: 匹配模式
            - "rule": 仅按分类规则匹配
            - "ai": 用 AI 分析文案情绪后匹配
            - "suno": 生成 Suno Prompt（需手动生成音乐）
            - "auto": 优先 AI 分析，无 API Key 时降级为规则匹配

    Returns:
        匹配到的 BGM 文件路径，或 None
    """
    if mode == "rule" and book:
        category = book.get("category", "")
        bgm = match_bgm_by_rule(category)
        if bgm:
            print(f"[规则匹配] BGM: {bgm.name}")
        else:
            print("[规则匹配] 未找到匹配的 BGM 文件")
        return bgm

    elif mode == "ai" and script:
        bgm, mood = match_bgm_by_ai(script)
        if bgm:
            print(f"[AI匹配] 情绪={mood}, BGM: {bgm.name}")
        else:
            print(f"[AI匹配] 情绪={mood}, 但未找到匹配的 BGM 文件")
        return bgm

    elif mode == "suno" and book:
        generate_bgm_with_suno(book)
        return None

    elif mode == "auto":
        # 自动模式：AI分析 → 规则匹配 → 自动下载
        mood = None
        has_api_key = (
            OPENAI_API_KEY != "your-api-key-here"
            or CLAUDE_API_KEY != "your-claude-api-key-here"
        )

        # Step 1: 尝试 AI 情绪分析
        if script and has_api_key:
            bgm, mood = match_bgm_by_ai(script)
            if bgm:
                print(f"[自动-AI匹配] 情绪={mood}, BGM: {bgm.name}")
                return bgm
            print(f"[自动-AI匹配] 情绪={mood}, 本地无匹配文件")

        # Step 2: 尝试规则匹配
        if book:
            category = book.get("category", "")
            if not mood:
                mood = CATEGORY_TO_MOOD.get(category, "calm")
            bgm = match_bgm_by_rule(category)
            if bgm:
                print(f"[自动-规则匹配] BGM: {bgm.name}")
                return bgm

        # Step 3: 本地无 BGM → 自动下载
        if not mood:
            mood = "calm"
        print(f"[自动下载] 本地无 BGM，尝试自动下载 {mood} 类音乐...")
        try:
            from download_bgm import auto_download_bgm
            downloaded = auto_download_bgm(mood=mood, count=2)
            if downloaded:
                print(f"[自动下载] 下载成功，使用: {downloaded[0].name}")
                return downloaded[0]
        except Exception as e:
            print(f"[自动下载] 下载失败: {e}")

        # Step 4: 最终兜底
        bgm = _find_bgm_by_mood("calm")
        if bgm:
            return bgm

        print("[提示] 未找到任何 BGM。运行 'python download_bgm.py guide' 查看免费音乐下载指南")
        return None

    return None


def setup_bgm_dirs():
    """创建 BGM 情绪子目录结构"""
    for mood in MOOD_CATEGORIES:
        mood_dir = BGM_DIR / mood
        mood_dir.mkdir(parents=True, exist_ok=True)
    print("已创建 BGM 目录结构：")
    for mood, info in MOOD_CATEGORIES.items():
        print(f"  assets/bgm/{mood}/  ← {info['name']}：{info['description']}")
    print("\n请将对应情绪的 BGM 文件放入对应目录即可。")


def print_mood_guide():
    """打印情绪-分类对照表，帮助用户理解如何存放 BGM"""
    print("\n" + "=" * 60)
    print("BGM 情绪分类指南")
    print("=" * 60)

    for mood, info in MOOD_CATEGORIES.items():
        print(f"\n📁 assets/bgm/{mood}/")
        print(f"   {info['name']} — {info['description']}")

        # 找出映射到这个 mood 的书籍分类
        categories = [cat for cat, m in CATEGORY_TO_MOOD.items() if m == mood]
        if categories:
            print(f"   适用书籍分类：{', '.join(categories)}")

    print(f"\n💡 提示：也可以将 BGM 直接放在 assets/bgm/ 根目录，")
    print(f"   文件名中包含情绪关键词即可自动匹配（如 calm_piano_01.mp3）")
    print()


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BGM 智能匹配工具")
    subparsers = parser.add_subparsers(dest="command")

    # setup: 创建目录结构
    subparsers.add_parser("setup", help="创建 BGM 情绪分类目录")

    # guide: 查看分类指南
    subparsers.add_parser("guide", help="查看情绪-分类对照指南")

    # match: 为指定书匹配 BGM
    match_parser = subparsers.add_parser("match", help="为书籍匹配 BGM")
    match_parser.add_argument("--book", type=str, help="书名")
    match_parser.add_argument("--category", type=str, help="书籍分类")
    match_parser.add_argument("--script-file", type=str, help="文案文件路径")
    match_parser.add_argument(
        "--mode", choices=["rule", "ai", "suno", "auto"], default="auto",
        help="匹配模式",
    )

    # suno: 生成 Suno Prompt
    suno_parser = subparsers.add_parser("suno", help="为书籍生成 Suno AI 音乐 Prompt")
    suno_parser.add_argument("--book", type=str, required=True, help="书名")

    args = parser.parse_args()

    if args.command == "setup":
        setup_bgm_dirs()

    elif args.command == "guide":
        print_mood_guide()

    elif args.command == "match":
        book_info = None
        script_text = None

        if args.book or args.category:
            if args.book:
                books = json.loads(
                    (Path(__file__).parent / "book_list.json").read_text(encoding="utf-8")
                )
                book_info = next((b for b in books if b["title"] == args.book), None)
                if not book_info:
                    book_info = {"title": args.book, "category": args.category or ""}
            else:
                book_info = {"title": "", "category": args.category}

        if args.script_file:
            script_text = Path(args.script_file).read_text(encoding="utf-8")

        result = match_bgm(book=book_info, script=script_text, mode=args.mode)
        if result:
            print(f"\n最终匹配 BGM: {result}")
        else:
            print("\n未找到匹配的 BGM 文件，请先添加音乐到 assets/bgm/ 目录")

    elif args.command == "suno":
        books = json.loads(
            (Path(__file__).parent / "book_list.json").read_text(encoding="utf-8")
        )
        book_info = next((b for b in books if b["title"] == args.book), None)
        if book_info:
            generate_bgm_with_suno(book_info)
        else:
            print(f"书单中没有找到《{args.book}》")

    else:
        parser.print_help()
