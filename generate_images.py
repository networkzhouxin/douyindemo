"""
画面生成模块
使用 Pillow 生成视频所需的各种画面素材(无需外部 API)

生成内容:
1. 渐变/主题色背景图(根据书籍分类自动选配色)
2. 书籍封面卡片(书名+作者+装饰)
3. 金句/要点卡片(从文案中提取关键段落)
4. 片头/片尾画面
5. 装饰元素(分割线、图标等)
"""

import math
import random
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import VIDEO_WIDTH, VIDEO_HEIGHT, FONTS_DIR, TEMPLATES_DIR, get_book_output_dir

# ============================================================
# 配色方案(按书籍分类/情绪)
# ============================================================

COLOR_THEMES = {
    "calm": {
        "name": "静谧蓝",
        "bg_gradient": [(20, 30, 48), (36, 59, 85)],        # 深蓝渐变
        "accent": (100, 180, 255),                            # 亮蓝
        "text_primary": (240, 240, 245),                      # 近白
        "text_secondary": (160, 175, 200),                    # 灰蓝
        "card_bg": (30, 42, 65, 220),                         # 半透明深蓝
        "highlight": (255, 200, 80),                          # 金色高亮
    },
    "inspiring": {
        "name": "活力橙",
        "bg_gradient": [(25, 20, 20), (60, 30, 15)],         # 深棕渐变
        "accent": (255, 160, 50),                              # 橙色
        "text_primary": (255, 250, 240),
        "text_secondary": (200, 180, 150),
        "card_bg": (50, 35, 20, 220),
        "highlight": (255, 120, 30),
    },
    "emotional": {
        "name": "温暖粉",
        "bg_gradient": [(35, 20, 28), (60, 25, 40)],         # 深紫红渐变
        "accent": (255, 130, 150),                             # 粉色
        "text_primary": (255, 245, 248),
        "text_secondary": (200, 170, 180),
        "card_bg": (50, 25, 35, 220),
        "highlight": (255, 180, 120),
    },
    "thoughtful": {
        "name": "深邃绿",
        "bg_gradient": [(15, 25, 20), (25, 50, 40)],         # 深绿渐变
        "accent": (80, 200, 160),                              # 青绿
        "text_primary": (235, 245, 240),
        "text_secondary": (150, 185, 170),
        "card_bg": (20, 38, 30, 220),
        "highlight": (120, 230, 180),
    },
    "energetic": {
        "name": "电光紫",
        "bg_gradient": [(20, 15, 35), (40, 20, 60)],         # 深紫渐变
        "accent": (180, 100, 255),                             # 紫色
        "text_primary": (245, 240, 255),
        "text_secondary": (180, 165, 210),
        "card_bg": (35, 25, 55, 220),
        "highlight": (255, 150, 200),
    },
}

# 书籍分类 -> 配色
CATEGORY_TO_THEME = {
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
}


def get_theme(category: str = "", mood: str = "") -> dict:
    """根据分类或情绪获取配色方案"""
    if mood and mood in COLOR_THEMES:
        return COLOR_THEMES[mood]
    theme_key = CATEGORY_TO_THEME.get(category, "calm")
    return COLOR_THEMES[theme_key]


# ============================================================
# 字体工具
# ============================================================

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """获取中文字体"""
    # 优先项目字体
    for ext in ("*.ttf", "*.otf"):
        for f in FONTS_DIR.glob(ext):
            return ImageFont.truetype(str(f), size)

    # Windows 系统字体
    font_paths = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)

    return ImageFont.load_default()


# ============================================================
# 背景图生成
# ============================================================

def create_gradient_bg(
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    color_top: tuple = (20, 30, 48),
    color_bottom: tuple = (36, 59, 85),
) -> Image.Image:
    """生成垂直渐变背景"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return img


def add_particles(img: Image.Image, color: tuple, count: int = 30) -> Image.Image:
    """添加装饰光点/粒子效果"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for _ in range(count):
        x = random.randint(0, img.width)
        y = random.randint(0, img.height)
        size = random.randint(1, 4)
        alpha = random.randint(30, 120)
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(*color[:3], alpha),
        )

    img_rgba = img.convert("RGBA")
    return Image.alpha_composite(img_rgba, overlay).convert("RGB")


def add_vignette(img: Image.Image, strength: float = 0.6) -> Image.Image:
    """添加暗角效果，让画面更有电影质感"""
    width, height = img.size
    vignette = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(vignette)

    cx, cy = width // 2, height // 2
    max_dist = math.sqrt(cx**2 + cy**2)

    for y in range(0, height, 2):
        for x in range(0, width, 2):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            ratio = dist / max_dist
            brightness = int(255 * (1 - ratio * strength))
            brightness = max(0, min(255, brightness))
            draw.rectangle([x, y, x + 1, y + 1], fill=brightness)

    vignette = vignette.resize((width, height), Image.LANCZOS)

    img_rgba = img.convert("RGBA")
    result = Image.new("RGBA", (width, height))
    for y in range(height):
        for x in range(width):
            r, g, b, a = img_rgba.getpixel((x, y))
            v = vignette.getpixel((x, y)) / 255.0
            result.putpixel((x, y), (int(r * v), int(g * v), int(b * v), a))

    return result.convert("RGB")


def create_themed_bg(theme: dict) -> Image.Image:
    """根据主题创建精美背景"""
    colors = theme["bg_gradient"]
    img = create_gradient_bg(
        color_top=colors[0],
        color_bottom=colors[1],
    )
    img = add_particles(img, theme["accent"], count=40)
    return img


# ============================================================
# 卡片生成
# ============================================================

def draw_rounded_rect(
    draw: ImageDraw.Draw,
    xy: tuple,
    radius: int,
    fill: tuple,
):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = xy
    # 使用 Pillow 内置的圆角矩形(需要 Pillow 8.2+)
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def create_book_cover_card(
    book_title: str,
    book_author: str,
    theme: dict,
    width: int = 700,
    height: int = 500,
) -> Image.Image:
    """
    生成书籍封面卡片
    精美的卡片设计，包含书名、作者、装饰线条
    """
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # 卡片背景(圆角半透明)
    draw_rounded_rect(draw, (0, 0, width, height), radius=30, fill=theme["card_bg"])

    # 顶部装饰线
    accent = theme["accent"]
    draw.rectangle([60, 50, width - 60, 54], fill=accent)

    # 书名图标(书本符号)
    icon_font = get_font(40)
    draw.text((width // 2 - 15, 70), "📖", font=icon_font, anchor="mt")

    # 书名
    title_font = get_font(52, bold=True)
    title_text = f"《{book_title}》"
    # 自动换行
    max_chars = 10
    if len(title_text) > max_chars:
        mid = len(title_text) // 2
        title_text = title_text[:mid] + "\n" + title_text[mid:]

    bbox = draw.multiline_textbbox((0, 0), title_text, font=title_font)
    text_w = bbox[2] - bbox[0]
    draw.multiline_text(
        ((width - text_w) // 2, 140),
        title_text,
        font=title_font,
        fill=theme["text_primary"],
        align="center",
    )

    # 分隔线
    line_y = 280
    line_w = 120
    draw.rectangle(
        [(width - line_w) // 2, line_y, (width + line_w) // 2, line_y + 3],
        fill=theme["accent"],
    )

    # 作者
    author_font = get_font(32)
    draw.text(
        (width // 2, 310),
        f"作者:{book_author}",
        font=author_font,
        fill=theme["text_secondary"],
        anchor="mt",
    )

    # 底部装饰标语
    slogan_font = get_font(24)
    draw.text(
        (width // 2, height - 60),
        "每天一本好书 - 遇见更好的自己",
        font=slogan_font,
        fill=(*theme["accent"][:3], 150),
        anchor="mt",
    )

    # 底部装饰线
    draw.rectangle([60, height - 40, width - 60, height - 36], fill=accent)

    return card


def create_quote_card(
    quote_text: str,
    theme: dict,
    index: int = 0,
    width: int = 860,
    height: int = 400,
) -> Image.Image:
    """
    生成金句/要点卡片
    每个核心观点做成一张卡片
    """
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # 卡片背景
    draw_rounded_rect(draw, (0, 0, width, height), radius=25, fill=theme["card_bg"])

    # 左侧装饰竖线
    draw.rectangle([30, 40, 36, height - 40], fill=theme["accent"])

    # 序号圆圈
    num_font = get_font(28, bold=True)
    cx, cy = 70, 60
    draw.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=theme["accent"])
    draw.text((cx, cy), str(index + 1), font=num_font, fill=(30, 30, 30), anchor="mm")

    # 引号装饰
    quote_font = get_font(60)
    draw.text((110, 30), "\u201C", font=quote_font, fill=(*theme["accent"][:3], 100))

    # 正文(自动换行)
    body_font = get_font(36)
    wrapped = textwrap.fill(quote_text, width=16)
    draw.multiline_text(
        (70, 100),
        wrapped,
        font=body_font,
        fill=theme["text_primary"],
        spacing=16,
    )

    return card


def create_opening_frame(
    book_title: str,
    book_author: str,
    category: str = "",
    hook_text: str = "",
    theme: dict = None,
) -> Image.Image:
    """
    生成片头画面
    包含: 背景 + 大号书名 + 钩子文案
    """
    if theme is None:
        theme = get_theme(category)

    img = create_themed_bg(theme)
    img_rgba = img.convert("RGBA")

    # 半透明遮罩(让文字更清晰)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 80))
    img_rgba = Image.alpha_composite(img_rgba, overlay)

    draw = ImageDraw.Draw(img_rgba)

    # 顶部分类标签
    if category:
        tag_font = get_font(28)
        tag_text = f"# {category}"
        bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
        tw = bbox[2] - bbox[0]
        tag_x = (VIDEO_WIDTH - tw) // 2
        # 标签背景
        draw_rounded_rect(
            draw,
            (tag_x - 20, 180, tag_x + tw + 20, 225),
            radius=12,
            fill=(*theme["accent"][:3], 80),
        )
        draw.text(
            (VIDEO_WIDTH // 2, 190),
            tag_text,
            font=tag_font,
            fill=theme["accent"],
            anchor="mt",
        )

    # 书名(大号)
    title_font = get_font(72, bold=True)
    title_text = f"《{book_title}》"
    draw.text(
        (VIDEO_WIDTH // 2, 400),
        title_text,
        font=title_font,
        fill=theme["highlight"],
        anchor="mt",
    )

    # 作者
    author_font = get_font(36)
    draw.text(
        (VIDEO_WIDTH // 2, 500),
        book_author,
        font=author_font,
        fill=theme["text_secondary"],
        anchor="mt",
    )

    # 装饰分割线
    line_w = 200
    draw.rectangle(
        [(VIDEO_WIDTH - line_w) // 2, 560, (VIDEO_WIDTH + line_w) // 2, 563],
        fill=theme["accent"],
    )

    # 钩子文案(如果有)
    if hook_text:
        hook_font = get_font(42)
        wrapped = textwrap.fill(hook_text, width=18)
        draw.multiline_text(
            (VIDEO_WIDTH // 2, 650),
            wrapped,
            font=hook_font,
            fill=theme["text_primary"],
            anchor="mt",
            align="center",
            spacing=14,
        )

    # 封面卡片
    cover_card = create_book_cover_card(book_title, book_author, theme)
    card_x = (VIDEO_WIDTH - cover_card.width) // 2
    img_rgba.paste(cover_card, (card_x, 900), cover_card)

    # 底部提示
    tip_font = get_font(26)
    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT - 120),
        "👆 滑动继续听",
        font=tip_font,
        fill=theme["text_secondary"],
        anchor="mt",
    )

    return img_rgba.convert("RGB")


def create_content_frame(
    segment_text: str,
    segment_index: int,
    total_segments: int,
    book_title: str,
    theme: dict = None,
    category: str = "",
) -> Image.Image:
    """
    生成内容段落画面
    每个核心观点/段落对应一张卡片画面
    """
    if theme is None:
        theme = get_theme(category)

    img = create_themed_bg(theme)
    img_rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(img_rgba)

    # 顶部书名(小号)
    header_font = get_font(30)
    draw.text(
        (VIDEO_WIDTH // 2, 80),
        f"《{book_title}》",
        font=header_font,
        fill=theme["text_secondary"],
        anchor="mt",
    )

    # 进度指示器
    progress_text = f"{segment_index + 1} / {total_segments}"
    draw.text(
        (VIDEO_WIDTH // 2, 130),
        progress_text,
        font=get_font(24),
        fill=(*theme["accent"][:3], 150),
        anchor="mt",
    )

    # 进度条
    bar_w = 300
    bar_h = 4
    bar_x = (VIDEO_WIDTH - bar_w) // 2
    bar_y = 165
    draw.rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        fill=(*theme["text_secondary"][:3], 60),
    )
    filled_w = int(bar_w * (segment_index + 1) / total_segments)
    draw.rectangle(
        [bar_x, bar_y, bar_x + filled_w, bar_y + bar_h],
        fill=theme["accent"],
    )

    # 核心要点卡片(居中显示)
    quote_card = create_quote_card(segment_text, theme, index=segment_index)
    card_x = (VIDEO_WIDTH - quote_card.width) // 2
    img_rgba.paste(quote_card, (card_x, 350), quote_card)

    # 底部装饰文字
    footer_font = get_font(24)
    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT - 200),
        "关注我 - 每天带你读一本好书",
        font=footer_font,
        fill=(*theme["text_secondary"][:3], 120),
        anchor="mt",
    )

    return img_rgba.convert("RGB")


def create_ending_frame(
    book_title: str,
    theme: dict = None,
    category: str = "",
) -> Image.Image:
    """生成片尾画面"""
    if theme is None:
        theme = get_theme(category)

    img = create_themed_bg(theme)
    img_rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(img_rgba)

    # 大号感谢文字
    thanks_font = get_font(56, bold=True)
    draw.text(
        (VIDEO_WIDTH // 2, 500),
        "感谢观看",
        font=thanks_font,
        fill=theme["text_primary"],
        anchor="mt",
    )

    # 书名
    title_font = get_font(36)
    draw.text(
        (VIDEO_WIDTH // 2, 600),
        f"《{book_title}》",
        font=title_font,
        fill=theme["highlight"],
        anchor="mt",
    )

    # 装饰线
    line_w = 160
    draw.rectangle(
        [(VIDEO_WIDTH - line_w) // 2, 670, (VIDEO_WIDTH + line_w) // 2, 673],
        fill=theme["accent"],
    )

    # CTA
    cta_font = get_font(40, bold=True)
    draw.text(
        (VIDEO_WIDTH // 2, 760),
        "点赞 + 关注",
        font=cta_font,
        fill=theme["accent"],
        anchor="mt",
    )

    sub_font = get_font(30)
    draw.text(
        (VIDEO_WIDTH // 2, 830),
        "每天带你读一本好书",
        font=sub_font,
        fill=theme["text_secondary"],
        anchor="mt",
    )

    # 装饰图标
    icon_font = get_font(80)
    draw.text((VIDEO_WIDTH // 2, 1000), "📚", font=icon_font, anchor="mt")

    return img_rgba.convert("RGB")


# ============================================================
# 文案分段工具
# ============================================================

def split_script_to_segments(script: str) -> list[str]:
    """
    将文案拆分成多个段落/观点
    用于生成不同的画面卡片

    规则:
    1. 优先按句号/问号/感叹号分段
    2. 合并太短的段落
    3. 拆分太长的段落
    """
    # 按标点分句
    sentences = re.split(r'([。！？!?])', script)
    # 重新组合(标点粘回前一句)
    merged = []
    for i in range(0, len(sentences) - 1, 2):
        s = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
        s = s.strip()
        if s:
            merged.append(s)
    # 最后一个(可能没有标点)
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        merged.append(sentences[-1].strip())

    # 合并太短的句子(< 15字合并到下一句)
    segments = []
    buffer = ""
    for s in merged:
        buffer += s
        if len(buffer) >= 20:
            segments.append(buffer)
            buffer = ""
    if buffer:
        if segments:
            segments[-1] += buffer
        else:
            segments.append(buffer)

    # 拆分太长的段落(> 60字拆开)
    final = []
    for seg in segments:
        if len(seg) > 60:
            mid = len(seg) // 2
            # 找附近的逗号断开
            comma_pos = seg.find("，", mid - 10)
            if comma_pos == -1:
                comma_pos = mid
            final.append(seg[:comma_pos + 1].strip())
            final.append(seg[comma_pos + 1:].strip())
        else:
            final.append(seg)

    return [s for s in final if s]


def generate_all_frames(
    book_title: str,
    book_author: str,
    category: str,
    script: str,
    output_dir: Path = None,
) -> list[Path]:
    """
    为一条视频生成全部画面帧图片

    Returns:
        生成的图片文件路径列表(按顺序:片头 -> 内容段落 -> 片尾)
    """
    if output_dir is None:
        output_dir = get_book_output_dir(book_title) / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)

    theme = get_theme(category)
    segments = split_script_to_segments(script)

    frames = []

    # 提取钩子(文案第一句)
    hook = segments[0] if segments else ""

    # 1. 片头
    opening = create_opening_frame(
        book_title, book_author, category, hook_text=hook, theme=theme
    )
    path = output_dir / "00_opening.png"
    opening.save(str(path))
    frames.append(path)

    # 2. 内容段落
    for i, seg in enumerate(segments):
        content = create_content_frame(
            segment_text=seg,
            segment_index=i,
            total_segments=len(segments),
            book_title=book_title,
            theme=theme,
        )
        path = output_dir / f"{i+1:02d}_content.png"
        content.save(str(path))
        frames.append(path)

    # 3. 片尾
    ending = create_ending_frame(book_title, theme=theme)
    path = output_dir / f"{len(segments)+1:02d}_ending.png"
    ending.save(str(path))
    frames.append(path)

    print(f"已生成 {len(frames)} 张画面(片头1 + 内容{len(segments)} + 片尾1)")
    return frames


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="视频画面生成工具")
    parser.add_argument("--title", type=str, required=True, help="书名")
    parser.add_argument("--author", type=str, default="", help="作者")
    parser.add_argument("--category", type=str, default="心理学", help="分类")
    parser.add_argument("--script", type=str, help="文案文本(直接输入)")
    parser.add_argument("--script-file", type=str, help="文案文件路径")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    parser.add_argument(
        "--preview", action="store_true", help="只生成片头预览"
    )
    args = parser.parse_args()

    script_text = args.script or ""
    if args.script_file:
        script_text = Path(args.script_file).read_text(encoding="utf-8")

    if args.preview:
        theme = get_theme(args.category)
        img = create_opening_frame(
            args.title, args.author, args.category, theme=theme
        )
        out = Path(args.output_dir or ".") / "preview_opening.png"
        img.save(str(out))
        print(f"预览已保存: {out}")
    else:
        if not script_text:
            print("请提供文案:--script 或 --script-file")
        else:
            out_dir = Path(args.output_dir) if args.output_dir else None
            frames = generate_all_frames(
                args.title, args.author, args.category, script_text, out_dir
            )
            for f in frames:
                print(f"  {f}")
