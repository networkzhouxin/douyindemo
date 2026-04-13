"""
风控与安全模块
- 敏感词检测: 发布前自动扫描标题/文案
- 发布限流: 每日上限、随机间隔、定期休息
- 跨平台差异化: 自动微调标题避免重复判定
- 发布日志: 记录发布历史，防止超限
"""

import json
import random
import re
import time
from datetime import datetime, date
from pathlib import Path

from config import (
    DAILY_PUBLISH_LIMIT,
    PUBLISH_INTERVAL_MIN,
    PUBLISH_INTERVAL_MAX,
    ACTION_DELAY_MIN,
    ACTION_DELAY_MAX,
    PUBLISH_BATCH_SIZE,
    PUBLISH_REST_MIN,
    PUBLISH_REST_MAX,
    PUBLISH_LOG_PATH,
    SENSITIVE_WORDS_ENABLED,
    SENSITIVE_WORDS_PATH,
    CROSS_PLATFORM_VARIATION,
)


# ============================================================
# 敏感词检测
# ============================================================

_sensitive_words_cache: list[str] | None = None


def _load_sensitive_words() -> list[str]:
    """加载敏感词库"""
    global _sensitive_words_cache
    if _sensitive_words_cache is not None:
        return _sensitive_words_cache

    words = []
    if SENSITIVE_WORDS_PATH.exists():
        with open(SENSITIVE_WORDS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    words.append(line)

    _sensitive_words_cache = words
    return words


_sensitive_pattern_cache = None


def check_sensitive_words(text: str) -> list[str]:
    """
    检测文本中的敏感词

    使用正则预编译模式提高检测效率（O(n) 而非 O(n*m)）

    Returns:
        命中的敏感词列表（空列表表示安全）
    """
    if not SENSITIVE_WORDS_ENABLED:
        return []

    words = _load_sensitive_words()
    if not words:
        return []

    # 预编译正则（缓存），将所有敏感词合并为一个大的交替匹配模式
    global _sensitive_pattern_cache
    if _sensitive_pattern_cache is None:
        escaped = [re.escape(w) for w in words]
        _sensitive_pattern_cache = re.compile("|".join(escaped))

    matches = _sensitive_pattern_cache.findall(text)
    return list(set(matches))


def check_content_safe(title: str, script: str = "") -> tuple[bool, list[str]]:
    """
    综合检测标题和文案是否安全

    Returns:
        (is_safe, found_words)
    """
    text = f"{title} {script}"
    found = check_sensitive_words(text)

    if found:
        print(f"  [风控] 检测到敏感词: {', '.join(found)}")
        return False, found

    return True, []


# ============================================================
# 发布限流
# ============================================================

def _load_publish_log() -> dict:
    """加载发布日志"""
    if PUBLISH_LOG_PATH.exists():
        try:
            with open(PUBLISH_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [风控] 发布日志读取失败: {e}，使用空日志")
    return {"daily": {}, "total": 0}


def _save_publish_log(log: dict):
    # 原子写入：先写临时文件再重命名，防止进程崩溃导致日志损坏
    tmp_path = PUBLISH_LOG_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    tmp_path.replace(PUBLISH_LOG_PATH)


def get_today_publish_count() -> int:
    """获取今日已发布数量"""
    log = _load_publish_log()
    today = date.today().isoformat()
    return log.get("daily", {}).get(today, 0)


def can_publish() -> tuple[bool, str]:
    """
    检查是否可以继续发布

    Returns:
        (can_publish, reason)
    """
    today_count = get_today_publish_count()
    if today_count >= DAILY_PUBLISH_LIMIT:
        return False, f"今日已发布 {today_count} 条，达到上限 {DAILY_PUBLISH_LIMIT} 条，明天再发"
    return True, f"今日已发布 {today_count}/{DAILY_PUBLISH_LIMIT}"


def record_publish(title: str, video_path: str = ""):
    """记录一次发布"""
    log = _load_publish_log()
    today = date.today().isoformat()

    if "daily" not in log:
        log["daily"] = {}
    log["daily"][today] = log["daily"].get(today, 0) + 1
    log["total"] = log.get("total", 0) + 1

    # 记录详细历史
    if "history" not in log:
        log["history"] = []
    log["history"].append({
        "title": title,
        "video": video_path,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    # 只保留最近100条历史
    log["history"] = log["history"][-100:]

    _save_publish_log(log)


def random_delay(min_s: float = None, max_s: float = None):
    """随机等待一段时间（模拟人类操作间隔）"""
    min_s = min_s or ACTION_DELAY_MIN
    max_s = max_s or ACTION_DELAY_MAX
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)
    return delay


def random_publish_interval():
    """发布间隔：随机等待"""
    delay = random.uniform(PUBLISH_INTERVAL_MIN, PUBLISH_INTERVAL_MAX)
    print(f"  [风控] 等待 {delay:.0f} 秒后发布下一条...")
    time.sleep(delay)
    return delay


def should_rest(published_count: int) -> bool:
    """判断是否需要休息"""
    return PUBLISH_BATCH_SIZE > 0 and published_count > 0 and published_count % PUBLISH_BATCH_SIZE == 0


def take_rest():
    """执行休息"""
    rest = random.uniform(PUBLISH_REST_MIN, PUBLISH_REST_MAX)
    print(f"  [风控] 已连续发布 {PUBLISH_BATCH_SIZE} 条，休息 {rest/60:.1f} 分钟...")
    time.sleep(rest)


# ============================================================
# 跨平台差异化
# ============================================================

# 标题前缀池（随机选一个加在前面）
_TITLE_PREFIXES = [
    "", "", "",  # 高概率不加前缀
    "必看 ",
    "推荐 ",
    "分享 ",
]

# 标题后缀池
_TITLE_SUFFIXES = [
    "", "", "",
    " 值得一看",
    " 强烈推荐",
    " 建议收藏",
]

# 同义替换对
_SYNONYMS = [
    ("推荐", "安利"),
    ("值得一看", "不容错过"),
    ("必读", "一定要看"),
    ("分享", "推荐"),
    ("精华", "干货"),
    ("核心观点", "关键洞察"),
]


def vary_title(title: str, platform: str = "douyin") -> str:
    """
    对标题做微调，用于跨平台差异化

    Args:
        title: 原始标题
        platform: 目标平台（不同平台用不同策略）

    Returns:
        微调后的标题
    """
    if not CROSS_PLATFORM_VARIATION:
        return title

    varied = title

    # 随机同义替换（只替换一对，且检查替换后不会与原标题相同）
    if random.random() < 0.3:
        random.shuffle(_SYNONYMS)
        for old, new in _SYNONYMS:
            if old in varied and new not in varied:
                varied = varied.replace(old, new, 1)
                break

    # 平台特定调整
    if platform == "xiaohongshu":
        # 小红书偏好 emoji 和感叹号
        if not any(c in varied for c in "!！"):
            varied += "！"
    elif platform == "bilibili":
        # B站偏好中括号标签
        if not varied.startswith("【"):
            prefix = random.choice(["【书籍蒸馏】", "【蒸馏精华】", "【好书蒸馏】", ""])
            varied = prefix + varied
    elif platform == "douyin":
        # 抖音保持简洁
        pass

    return varied


def vary_tags(tags: list[str], platform: str = "douyin") -> list[str]:
    """对标签做差异化"""
    if not CROSS_PLATFORM_VARIATION:
        return tags

    varied = tags.copy()

    # 各平台额外标签
    platform_tags = {
        "douyin": ["书籍蒸馏", "BookTok"],
        "xiaohongshu": ["书籍蒸馏", "读书笔记", "精华提炼"],
        "bilibili": ["书籍蒸馏", "知识区", "学习"],
        "weixin": ["书籍蒸馏", "书评", "精华提炼"],
    }

    extra = platform_tags.get(platform, [])
    if extra:
        varied.append(random.choice(extra))

    return varied


# ============================================================
# 发布前综合检查
# ============================================================

def pre_publish_check(title: str, script: str = "") -> tuple[bool, str]:
    """
    发布前综合安全检查

    Returns:
        (passed, message)
    """
    # 1. 检查每日限额
    ok, msg = can_publish()
    if not ok:
        return False, msg

    # 2. 敏感词检测
    is_safe, found = check_content_safe(title, script)
    if not is_safe:
        return False, f"内容包含敏感词: {', '.join(found)}，请修改后再发布"

    # 3. 标题长度检查（抖音限制）
    if len(title) > 55:
        return False, f"标题过长({len(title)}字)，抖音限制55字以内"

    return True, msg


def show_publish_stats():
    """显示发布统计"""
    log = _load_publish_log()
    today = date.today().isoformat()
    today_count = log.get("daily", {}).get(today, 0)

    print(f"\n{'='*40}")
    print(f"发布统计")
    print(f"{'='*40}")
    print(f"  今日已发布: {today_count}/{DAILY_PUBLISH_LIMIT}")
    print(f"  累计发布:   {log.get('total', 0)} 条")

    # 最近发布
    history = log.get("history", [])
    if history:
        print(f"\n  最近发布:")
        for h in history[-5:]:
            print(f"    [{h.get('time', '')}] {h.get('title', '')}")
    print()
