# 书籍蒸馏 - 抖音全自动内容生产线

把任意一本书的精华蒸馏成几分钟短视频，帮观众用最短时间吸收最有价值的内容。

**书单采集 → 选题规划(一书多集蒸馏) → AI文案 → TTS语音 → 画面合成 → 视频导出 → 自动发布**

---

## 目录

- [项目能力概览](#一项目能力概览)
- [快速开始](#二快速开始)
- [项目结构](#三项目结构)
- [核心命令](#四核心命令)
- [各模块详细说明](#五各模块详细说明)
- [配置参考](#六配置参考)
- [风控与安全策略](#七风控与安全策略)
- [已知局限与建议](#八已知局限与建议)
- [账号运营指南](#九账号运营指南)
- [常见问题](#十常见问题)
- [外部工具参考](#十一外部工具参考)

---

## 一、项目能力概览

| 环节 | 能力 | 依赖 |
|------|------|------|
| 书单采集 | 豆瓣热门榜爬取 + AI 智能推荐，自动去重补充 | 网络 / LLM API |
| 选题规划 | AI 为每本书拆解 5-10 个蒸馏角度的视频选题 | LLM API |
| 文案生成 | 按选题逐集生成高信息密度口播文案，支持 OpenAI/Claude/国内模型 | LLM API |
| 语音合成 | Edge TTS(免费) + 说话风格/智能停顿，失败自动降级离线 | 网络(可离线) |
| 声音克隆 | 录10-30秒样本，后续所有视频用你自己的声音(GPT-SoVITS/Fish Audio) | 本地GPU 或 API |
| 视频画面 | 3种模式: 应景视频素材+字幕(推荐) / 卡片画面 / 数字人口播 | Pexels API(免费) 或本地素材 |
| BGM匹配 | 按书籍分类自动匹配情绪/自动下载/支持抖音平台音乐 | 可选 API |
| 视频合成 | MoviePy 合成竖屏视频(1080x1920)，语音+字幕+画面+BGM | FFmpeg |
| 自动发布 | Playwright 模拟浏览器发布到抖音，支持定时发布 | Playwright |
| 风控安全 | 敏感词检测、每日限额、操作随机化、跨平台差异化 | 无 |

### 一书多集蒸馏示例

一本《被讨厌的勇气》自动蒸馏出：

| 集数 | 类型 | 选题 |
|------|------|------|
| EP01 | 反常识蒸馏 | 你为什么总在意别人的看法? |
| EP02 | 核心蒸馏 | 所有的烦恼都来自人际关系 |
| EP03 | 方法蒸馏 | 课题分离: 学会分清什么是你的事 |
| EP04 | 金句蒸馏 | 这本书里最扎心的5句话 |
| EP05 | 一句话蒸馏 | 90秒说清这本书讲了什么 |

### 输出目录结构

```
output/
├── 被讨厌的勇气/
│   ├── topic_plan.json               # 蒸馏选题规划
│   ├── ep01_你为什么总在意别人的看法/
│   │   ├── script.txt                # 文案
│   │   ├── voice.mp3                 # 语音
│   │   ├── voice.srt                 # 字幕
│   │   ├── bg_cache/                 # 视频素材缓存 (video模式)
│   │   ├── frames/                   # 画面帧 (cards模式)
│   │   └── video.mp4                 # 最终视频 (90s)
│   ├── ep02_所有的烦恼都来自人际关系/
│   │   └── ...
│   └── report.json                   # 生成报告
├── 认知觉醒/
│   └── ...
```

---

## 二、快速开始

### 1. 环境要求

- Python 3.10+
- FFmpeg
- 一个 LLM API Key(OpenAI / 通义千问 / DeepSeek / Kimi / Claude 任选)

### 2. 安装

```bash
# 克隆项目
cd douyindemo

# 安装依赖
pip install -r requirements.txt

# 安装浏览器引擎(自动发布需要，可选)
playwright install chromium
```

### 3. 安装 FFmpeg

```bash
# Windows (winget)
winget install Gyan.FFmpeg

# Windows (scoop)
scoop install ffmpeg

# 验证
ffmpeg -version
```

### 4. 配置 API Key

```bash
# 方式A: 环境变量(推荐)
# OpenAI
export OPENAI_API_KEY="sk-xxxxxxxx"

# 通义千问
export OPENAI_API_KEY="sk-xxxxxxxx"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export OPENAI_MODEL="qwen-plus"

# DeepSeek
export OPENAI_API_KEY="sk-xxxxxxxx"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_MODEL="deepseek-chat"

# Kimi
export OPENAI_API_KEY="sk-xxxxxxxx"
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
export OPENAI_MODEL="moonshot-v1-8k"

# 方式B: 直接编辑 config.py 中对应字段
```

### 5. 运行

```bash
# 全自动: 1本书 x 5集 = 5条视频 (每集90秒)
python main.py auto

# 3本书 x 5集 = 15条视频
python main.py auto --books 3

# 2本书 x 8集 = 16条视频
python main.py auto --books 2 --episodes 8

# 自定义时长
python main.py auto --duration 120
```

启动时会自动校验配置（API Key、FFmpeg 等），有问题会提前警告。

---

## 三、项目结构

```
douyindemo/
├── config.py              # 全局配置(API密钥/视频参数/风控/声音克隆/数字人等)
├── main.py                # 主入口: 全自动蒸馏流水线
│
├── book_list.json         # 书单数据库(自动维护)
├── book_crawler.py        # 书单采集(豆瓣+AI推荐)
│
├── generate_script.py     # 选题规划 + AI文案生成(一书多集蒸馏)
├── generate_voice.py      # TTS语音合成(Edge/Azure/离线/声音克隆)
├── generate_images.py     # 画面帧生成(Pillow，5套主题配色，cards模式)
├── bg_video.py            # 视频素材获取(本地+Pexels API，video模式)
├── generate_video.py      # 视频合成(MoviePy，3种画面模式)
├── digital_human.py       # 数字人视频(SadTalker/HeyGen)
│
├── bgm_matcher.py         # BGM智能匹配(规则/AI情绪/Suno)
├── download_bgm.py        # BGM自动下载(Freesound)
│
├── auto_publish.py        # 自动发布到抖音(Playwright)
├── safety.py              # 风控模块(敏感词/限流/差异化)
├── sensitive_words.txt    # 敏感词库(可自行扩充)
│
├── requirements.txt       # Python依赖
├── output/                # 产出(按书籍/集数分目录)
└── assets/
    ├── fonts/             # 自定义字体
    ├── bgm/               # 背景音乐(按情绪分子目录)
    ├── bg_videos/         # 视频素材(按分类/情绪分子目录，video模式用)
    │   ├── 心理学/        # 按书籍分类
    │   ├── calm/          # 按情绪
    │   └── *.mp4          # 通用素材
    ├── templates/         # 视频模板
    ├── voice_sample/      # 你的声音样本(声音克隆用)
    │   └── sample.wav     # 10-30秒清晰人声
    └── avatar/            # 你的照片(数字人用)
        └── photo.png      # 正面半身照
```

---

## 四、核心命令

### 全自动模式

```bash
python main.py auto                          # 1本书 x 5集 = 5条视频
python main.py auto --books 3                # 3本书 x 5集 = 15条视频
python main.py auto --books 2 --episodes 8   # 2本书 x 8集 = 16条视频
python main.py auto --duration 120           # 每集120秒(深度蒸馏)
python main.py auto --books 1 --publish      # 生成并自动发布
python main.py auto --voice-sample calm      # 指定使用特定的声音样本
python main.py auto --only-voice             # 仅生成文案和语音，不合成视频
```

### 指定一本书

```bash
python main.py book "被讨厌的勇气"               # 默认5集
python main.py book "被讨厌的勇气" --episodes 10  # 10集
python main.py book "被讨厌的勇气" --voice-sample energetic # 指定声音
python main.py book "被讨厌的勇气" --only-voice   # 快速测试声音效果
```

### 只看选题规划(不生成视频)

```bash
python main.py plan "认知觉醒"
```

### 书单管理

```bash
python main.py fill                      # 自动补充10本
python main.py fill --count 20           # 补充20本
python main.py fill --category "心理学"   # 只补指定分类
python main.py fill --source ai          # 只用AI推荐
python main.py stats                     # 查看统计
python main.py reset                     # 重置书单状态
```

### 单独使用各模块

```bash
# 文案
python generate_script.py --book "被讨厌的勇气" --episodes 5

# 语音
python generate_voice.py --file output/xxx/ep01/script.txt
python generate_voice.py --text "测试一段文字"
python generate_voice.py --list-voices

# 视频
python generate_video.py --voice xxx.mp3 --subtitle xxx.srt --title "书名"

# 视频素材(video模式)
python bg_video.py setup                              # 创建素材目录
python bg_video.py search "peaceful nature"            # 搜索 Pexels
python bg_video.py download --category 心理学           # 按分类批量下载

# BGM
python bgm_matcher.py guide                          # 查看分类指南
python bgm_matcher.py match --book "被讨厌的勇气"     # 测试匹配
python download_bgm.py download                       # 下载所有分类BGM
python download_bgm.py guide                          # 免费音乐下载指南

# 发布
python auto_publish.py login                          # 首次登录(扫码)
python auto_publish.py upload --video xxx.mp4 --title "xxx" --tags 书籍蒸馏 好书推荐
python auto_publish.py upload --video xxx.mp4 --title "xxx" --douyin-music
```

---

## 五、各模块详细说明

### 5.1 书单采集 (book_crawler.py)

| 来源 | 说明 | 需要API |
|------|------|---------|
| 豆瓣热门 | 按分类爬取豆瓣读书热门榜，提取书名/作者/简介/评分 | 不需要 |
| AI推荐 | LLM 按分类推荐适合做"蒸馏"内容的书（信息密度高、有核心方法论） | 需要 |
| 自动补充 | 书单 pending 数量低于阈值(默认5)时自动触发采集 | - |

支持的分类: 心理学、自我成长、商业、沟通、历史、哲学、科学、文学(可在 config.py 中修改)。

### 5.2 文案生成 (generate_script.py)

**一书多集蒸馏流程:**

1. AI 分析书籍，规划 N 个蒸馏角度(核心蒸馏/金句蒸馏/方法蒸馏/故事蒸馏/反常识蒸馏...)
2. 选题保存为 `topic_plan.json`，支持断点续跑
3. 逐集生成文案，每集紧扣选题展开，高信息密度，不会内容重复

**支持的 LLM:**

| 模型 | 配置方式 |
|------|---------|
| OpenAI GPT-4o/GPT-4 | `OPENAI_BASE_URL` 默认值 |
| 通义千问 | `OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1` |
| DeepSeek | `OPENAI_BASE_URL=https://api.deepseek.com/v1` |
| Kimi | `OPENAI_BASE_URL=https://api.moonshot.cn/v1` |
| Claude | `LLM_PROVIDER="claude"` + `CLAUDE_API_KEY` |

所有兼容 OpenAI 接口的模型都可以直接接入。

### 5.3 语音合成 (generate_voice.py)

**四重保障(自动降级):**

```
声音克隆(可选) --未启用或失败--> Edge TTS(免费) --失败--> 重试3次 --仍失败--> 离线pyttsx3
```

**Edge TTS 自然度优化:**

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `EDGE_TTS_VOICE` | 语音角色 | `zh-CN-YunxiNeural`(男) |
| `EDGE_TTS_STYLE` | 说话风格 | `narration-relaxed`(轻松叙述) |
| `EDGE_TTS_RATE` | 语速微调 | `+0%` |
| `EDGE_TTS_SMART_PAUSE` | 智能停顿 | `True` |

**推荐搭配:**

| 内容类型 | 语音 | 风格 |
|---------|------|------|
| 核心蒸馏/方法蒸馏 | YunxiNeural | narration-relaxed |
| 深度蒸馏/哲学类 | YunjianNeural | documentary-narration |
| 情感/文学蒸馏 | XiaoxiaoNeural | gentle |
| 快节奏书单盘点 | XiaoyiNeural | cheerful |

**国内网络连不上微软服务器时:**

```bash
# 方案A: 配置代理
export HTTPS_PROXY=http://127.0.0.1:7890

# 方案B: 直接用离线TTS
# config.py 中设置 TTS_PROVIDER = "offline"
```

### 5.4 声音克隆 (generate_voice.py 内置)

录一段 10-30 秒人声样本，后续所有视频都用你自己的声音，辨识度拉满。

**两种方案:**

| 方案 | 效果 | 成本 | 需要GPU | 说明 |
|------|------|------|---------|------|
| GPT-SoVITS | 几乎以假乱真 | 免费 | 是(4GB+) | 开源，本地部署，几秒样本即可克隆 |
| Fish Audio | 好 | 有免费额度 | 否 | 在线API，上传样本即用，最简单 |

**使用步骤:**

```bash
# 1. 录音: 10-30秒清晰人声，无背景噪音，WAV格式
#    放到 assets/voice_sample/default/sample.wav
#    同时在该目录下新建 text.txt，填入这10秒录音的原话。

# 2. 选择方案，编辑 config.py:
TTS_PROVIDER = "clone"
VOICE_CLONE_ENGINE = "gpt_sovits"
VOICE_SAMPLE_NAME = "default"  # 使用 default 文件夹的样本
```

> **💡 高级技巧：语音样本池（一键换声音）**
> 
> 你可以根据不同类型的书，准备不同情绪的语音样本（如：严肃、活力、治愈）。
> 
> 1. 在 `assets/voice_sample/` 下建立多个子目录：
>    - `assets/voice_sample/energetic/sample.wav` + `text.txt`
>    - `assets/voice_sample/calm/sample.wav` + `text.txt`
> 2. 运行时直接通过参数指定使用哪个声音，无需修改代码：
> ```bash
> python main.py book "认知觉醒" --voice-sample energetic
> python main.py auto --voice-sample calm
> ```
> 
> 3. **调试模式**：如果你只想快速听听配音效果而不关心画面，可以加上 `--only-voice`：
> ```bash
> python main.py auto --voice-sample hm --only-voice
> ```

**录音要求:**
- 安静环境，无背景噪音、回声
- 说话自然，语速适中(不要刻意播音腔)
- WAV 格式，16kHz 以上，单声道
- 时长 10-30 秒(内容随意，可以读一段书)

> **💡 炼丹秘籍：用于训练 GPT-SoVITS 的素材文案推荐**
> 
> 为了让 AI 学习到你最自然、多样的语调，建议分批录制以下 4 种风格的素材（总长 5-10 分钟）：
> 
> 1. **基础沉稳（适合知识分享）**：
>    “很多人问我，为什么要读这么多书？其实读书不是为了记住每一个字，而是为了在某个瞬间，能用前人的智慧来对抗生活的平庸。今天我们要拆解的这本书叫《认知觉醒》。作者提到一个核心观点：人与人之间的根本差异，并不在于努力程度，而是在于思维模型。”
> 
> 2. **高能钩子（适合视频开头，语速稍快）**：
>    “别再用战术上的勤奋，来掩盖战略上的懒惰了！你是不是也经常觉得自己很忙，但一年到头发现什么都没留下？听着，这可能不是你的能力问题，而是你的底层逻辑出错了。今天我只用三分钟，把这本书里最扎心的五个真相拆穿。”
> 
> 3. **深度共情（低沉缓慢，有温度）**：
>    “其实，我们每个人的一生，都在寻找一种叫‘课题分离’的能力。就像《被讨厌的勇气》里说的那样，别人的评价，那是别人的课题，而你如何看待自己，才是你的课题。学会放下那些不属于你的负担，你会发现世界其实很简单。”
> 
> 4. **自然生活（像聊天一样，增加真实感）**：
>    “哎，说实话啊，我以前也觉得读书挺枯燥的。翻两页就想玩手机，对吧？后来我发现，其实是因为我没找对方法。你就把书里的作者，想象成一个顶级大佬坐在你对面，正跟你喝茶聊天呢。他把这辈子的避坑指南都告诉你了。”

**GPT-SoVITS 部署:**
```bash
git clone https://github.com/RVC-Boss/GPT-SoVITS
cd GPT-SoVITS
pip install -r requirements.txt
# 下载预训练模型(见项目README)
python api.py  # 启动API服务(默认端口9880)
```

> 声音克隆失败时会自动降级到 Edge TTS，不影响整体流程。

### 5.5 视频画面 — 三种模式

通过 `config.py` 中的 `VIDEO_BG_MODE` 切换画面模式:

```python
VIDEO_BG_MODE = "video"           # 应景视频素材 + 大字幕（默认，推荐）
VIDEO_BG_MODE = "cards"           # Pillow 卡片画面（无需外部资源）
VIDEO_BG_MODE = "digital_human"   # 数字人口播（需要 GPU 或付费 API）
```

**三种模式对比:**

| 模式 | 画面效果 | 外部依赖 | 适合场景 |
|------|---------|---------|---------|
| `video` | 应景视频+暗层+大字幕，最主流知识类风格 | Pexels API(免费) 或本地素材 | **推荐日常使用** |
| `cards` | Pillow 卡片画面，质感有限 | 无 | 无网络/无素材时兜底 |
| `digital_human` | 数字人口播，最有真人感 | GPU 或付费API | 有条件时效果最好 |

#### video 模式（默认推荐）

应景视频素材 + 半透明暗层(35%) + 大号字幕，是抖音知识类最主流的画面风格。

**素材来源(自动降级):**

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 本地素材 `assets/bg_videos/` | 按分类放竖屏 MP4 |
| 2 | Pexels API | 免费注册，按分类自动搜索下载并缓存 |
| 3 | 降级为 cards 模式 | 无素材时兜底 |

**快速上手:**

```bash
# 1. 免费注册 Pexels API Key: https://www.pexels.com/api/
# 2. 配置
export PEXELS_API_KEY="你的key"
# 3. 直接跑（自动按书籍分类搜索应景素材）
python main.py auto
```

**手动准备素材:**

```bash
# 创建目录结构
python bg_video.py setup

# 把竖屏视频放进去即可
assets/bg_videos/心理学/meditation_01.mp4
assets/bg_videos/商业/city_skyline.mp4
assets/bg_videos/通用素材.mp4
```

自动根据书籍分类匹配关键词搜索(如心理学→meditation, thinking)，横屏素材自动居中裁剪为竖屏，不够长自动循环拼接。

#### cards 模式

基于 Pillow 自动生成，无需外部 API:

- 5 套主题配色(根据书籍分类自动选择)
- 渐变背景 + 装饰光点 + 暗角效果
- 书籍封面卡片 + 金句/观点卡片
- 片头 + 片尾("书籍蒸馏"品牌CTA)
- 画面之间淡入淡出转场

| 配色 | 适用分类 | 风格 |
|------|---------|------|
| 静谧蓝 | 心理学、哲学 | 深蓝渐变+金色高亮 |
| 活力橙 | 成长、商业 | 深棕渐变+橙色强调 |
| 温暖粉 | 情感、文学 | 紫红渐变+粉色 |
| 深邃绿 | 投资、科学 | 深绿渐变+青绿 |
| 电光紫 | 书单、盘点 | 深紫渐变+亮紫 |

> cards 模式的画面质感有限。如果追求更高质量但不想用 video 模式，建议用本项目生成文案+语音后，手动导入剪映制作视频。

### 5.6 数字人 (digital_human.py)

上传一张正面照片，自动生成"真人"口播视频，画面中有一个"人"在说话。启用后自动替代卡片画面，视频质感显著提升。

**方案对比:**

| 方案 | 效果 | 成本 | GPU | 部署难度 |
|------|------|------|-----|---------|
| SadTalker | 好(嘴型+头部微动) | 免费 | 需要4GB+ | 中 |
| MuseTalk | 较好(实时唇形同步) | 免费 | 需要6GB+ | 中 |
| HeyGen | 最好(最逼真) | 付费 | 不需要 | 无需部署 |
| 腾讯智影 | 好 | 有免费额度 | 不需要 | 无需部署 |
| 硅基流动 | 好 | 有免费额度 | 不需要 | 无需部署 |

**使用步骤:**

```bash
# 1. 准备照片: 正面半身照，表情自然，光线均匀
#    放到 assets/avatar/photo.png

# 2. 检查照片是否符合要求
python digital_human.py check

# 3. 编辑 config.py:
DIGITAL_HUMAN_ENGINE = "sadtalker"
SADTALKER_PATH = "/path/to/SadTalker"

# 4. 查看完整部署指引
python digital_human.py guide

# 5. 运行(自动用数字人画面替代卡片)
python main.py auto
```

**照片要求:**
- 正面或微侧(15度以内)
- 半身照或头肩照，人脸占画面 30%+
- 光线均匀，无强烈阴影
- 背景简洁(纯色或虚化最佳)
- 嘴巴自然闭合
- 分辨率 512x512 以上

> 没有 GPU 或不想部署? 推荐直接用**腾讯智影**或**硅基流动**的在线免费额度，手动生成数字人视频后放到对应 ep 目录即可。

### 5.7 BGM (bgm_matcher.py + download_bgm.py)

三种方案:

| 方案 | 配置 | 说明 |
|------|------|------|
| 自动下载 | `BGM_SOURCE="download"` | 从 Freesound 按情绪下载(需API Key) |
| 抖音音乐 | `BGM_SOURCE="douyin"` | 发布时自动添加抖音平台音乐(零版权风险) |
| 本地文件 | `BGM_SOURCE="local"` | 手动放 MP3 到 `assets/bgm/` |

BGM 按情绪分 5 个子目录(calm/inspiring/emotional/thoughtful/energetic)，根据书籍分类自动匹配。

### 5.8 自动发布 (auto_publish.py)

基于 Playwright 控制浏览器，模拟人工操作:

1. 首次需扫码登录: `python auto_publish.py login`
2. Cookie 自动保存，后续无需重复登录
3. 支持: 定时发布、抖音平台音乐、批量上传
4. 内置风控(见第七章)

> **注意:** 抖音网页版经常改版，选择器可能失效，需要根据实际页面调试 `auto_publish.py` 中的 CSS 选择器。建议首次使用时设置 `headless=False` 观察运行情况。

---

## 六、配置参考

所有配置集中在 `config.py`，主要分组:

| 分组 | 关键配置 | 说明 |
|------|---------|------|
| AI文案 | `LLM_PROVIDER` `OPENAI_API_KEY` `OPENAI_BASE_URL` | LLM选择和密钥 |
| 语音 | `TTS_PROVIDER` `EDGE_TTS_VOICE` `EDGE_TTS_STYLE` | TTS引擎和风格 |
| 画面模式 | `VIDEO_BG_MODE` | `"video"`(默认) / `"cards"` / `"digital_human"` |
| 视频素材 | `PEXELS_API_KEY` `BG_VIDEOS_DIR` `BG_VIDEO_KEYWORDS` | video模式的素材来源和关键词映射 |
| 视频 | `VIDEO_WIDTH` `VIDEO_HEIGHT` `VIDEO_FPS` | 视频尺寸帧率 |
| 时长 | `DEFAULT_DURATION=90` | 每集90秒(约360字) |
| 集数 | `EPISODES_PER_BOOK=5` | 每本书蒸馏5个角度 |
| 字幕 | `SUBTITLE_FONT_SIZE` `SUBTITLE_FONT_COLOR` | 字幕样式(video模式自动放大1.3倍) |
| BGM | `BGM_SOURCE` | 背景音乐来源 |
| 发布 | `PUBLISH_TIMES` `DAILY_PUBLISH_LIMIT` | 发布时间和限额 |
| 风控 | `PUBLISH_INTERVAL_*` `SENSITIVE_WORDS_ENABLED` | 安全策略 |
| 书单 | `BOOK_LIST_MIN_PENDING` `BOOK_TARGET_CATEGORIES` | 书单采集 |
| 校验 | `validate_config()` | 启动时自动校验API Key/FFmpeg/画面模式等 |

---

## 七、风控与安全策略

### 7.1 敏感词检测

发布前自动扫描标题和文案，命中敏感词则拦截发布。使用预编译正则匹配，性能高效。

- 词库文件: `sensitive_words.txt`(每行一个词，支持自行扩充)
- 覆盖: 政治/违法/虚假宣传/侵权/引流/低俗等
- 配置: `SENSITIVE_WORDS_ENABLED = True`

### 7.2 发布限流

| 策略 | 配置 | 默认值 |
|------|------|--------|
| 每日上限 | `DAILY_PUBLISH_LIMIT` | 5条/天 |
| 发布间隔 | `PUBLISH_INTERVAL_MIN/MAX` | 60-180秒随机 |
| 操作延迟 | `ACTION_DELAY_MIN/MAX` | 1-3秒随机(每步操作) |
| 打字速度 | 代码内随机 | 30-80ms/字 |
| 批量休息 | `PUBLISH_BATCH_SIZE` / `PUBLISH_REST_*` | 每3条休息5-10分钟 |

### 7.3 跨平台差异化

多平台分发时自动对标题做微调(同义替换、平台特定标签)，避免被判重复内容。

配置: `CROSS_PLATFORM_VARIATION = True`

### 7.4 发布日志

每次发布自动记录到 `publish_log.json`（原子写入，防崩溃丢失），包含每日计数和发布历史。

查看统计: `python main.py stats`

### 7.5 安全使用建议

- 单日发布不超过 5 条(新号建议 1-2 条)
- 不要在固定时间发布，利用项目的随机间隔功能
- 定期更新 `sensitive_words.txt`，关注抖音创作者服务中心的规则变化
- 多账号运营需要 IP 隔离(本项目未内置，建议配合易媒助手等工具)

---

## 八、已知局限与建议

### 当前局限

| 环节 | 局限 | 影响 |
|------|------|------|
| 画面质量 | video 模式依赖素材质量；cards 模式卡片质感有限 | video 模式已大幅改善，cards 模式竞争力偏低 |
| TTS音质 | Edge TTS 听3秒能辨别是AI，与真人配音有差距 | 建议尽早切换声音克隆 |
| 视频素材 | Pexels 素材不一定完美匹配书籍内容 | 可手动补充精准素材到 assets/bg_videos/ |
| 自动发布 | 选择器基于推测，抖音改版后需手动调试 | 首次使用大概率需要适配 |
| 豆瓣爬取 | 可能被反爬拦截 | 降级到AI推荐即可 |
| 文案质量 | 依赖AI模型水平，没有质量评估机制 | 个别文案可能平庸 |
| 数据反馈 | 没有抓取发布后的播放/点赞数据 | 无法自动优化内容方向 |

### 推荐使用方式

**阶段一: 快速起步(推荐)**

1. 配置 LLM API Key + Pexels API Key(都免费)
2. `python main.py auto` 全自动生成(video 模式 + Edge TTS)
3. 手动发布到抖音，观察数据
4. 跑通 5-10 条后，确认哪些蒸馏角度数据好

**阶段二: 提升辨识度**

- 录制声音样本，启用声音克隆(`TTS_PROVIDER="clone"`)
- 积累本地精品素材到 `assets/bg_videos/`，替代 Pexels 通用素材
- 调通自动发布(`auto_publish.py`)

**阶段三: 全自动+数据驱动**

- 全流程自动化(文案→语音→视频→发布)
- 加入数据回收(爬取播放量/点赞)
- 根据数据自动调整蒸馏方向和风格

### 视频质量提升路径

| 优先级 | 方案 | 配置方式 | 效果提升 |
|--------|------|---------|---------|
| 1 | **启用 video 模式** | `VIDEO_BG_MODE="video"` + `PEXELS_API_KEY` | 很大 — 应景画面+字幕，最主流知识类风格 |
| 2 | 启用声音克隆 | `TTS_PROVIDER="clone"` + 录 30 秒人声 | 大 — 声音有辨识度，不再是千篇一律的AI腔 |
| 3 | 启用数字人 | `DIGITAL_HUMAN_ENGINE="sadtalker"` + 一张照片 | 很大 — 有"人"在画面里，完播率显著提升 |
| 4 | 手动用剪映制作 | 本项目生成文案+语音，导入剪映做画面 | 很大 — 画面质量最高 |
| 5 | 用更好的 LLM | GPT-4o / Claude | 中 — 文案质量明显优于免费模型 |

---

## 九、账号运营指南

### 9.1 "书籍蒸馏"账号定位

**核心理念:** 把一本书的精华蒸馏成几分钟短视频，让观众用最短时间吸收最有价值的内容。

**差异化优势:**
- "蒸馏"这个概念比"拆书/读书推荐"更有辨识度
- 暗示高信息密度——每句话都有干货，没有废话
- 适用于任意书籍，不限品类
- 一书多集蒸馏不同角度，粉丝追更性强

**内容风格:**
- 开头即钩子，3秒抓住注意力
- 每集只攻一个点，讲透讲深
- 信息密度高，节奏紧凑
- 口语化，像朋友聊天，不像老师讲课
- 结尾金句收尾 + "关注书籍蒸馏"

### 9.2 发布策略

- **频率:** 每天 1-2 条(坚持比数量重要)
- **时间:** 早 7-9 点、中午 12-13 点、晚 20-22 点
- **标签:** `#书籍蒸馏` `#好书推荐` `#读书` + 书名相关标签
- **前5条:** 不追数据，找节奏
- **互动:** 前期每条评论都回复

### 9.3 变现路径

1. **抖音橱窗带货**(卖书) - 1000粉即可开通，最直接
2. **知识付费**(蒸馏书单社群/精读课程)
3. **直播带货**(现场蒸馏一本书+卖书)
4. **广告接单**(出版社/知识类APP)
5. **引流私域**(微信读书社群)

### 9.4 执行节奏

| 阶段 | 时间 | 目标 |
|------|------|------|
| 准备 | 第1周 | 注册账号、配置工具、设计封面模板 |
| 手动验证 | 第2周 | 手动做5条视频，跑通流程，看数据 |
| 半自动 | 第3-4周 | AI批量生成文案，剪映制作视频，定时发布 |
| 全自动 | 第2月起 | 全流程自动化，持续优化 |

---

## 十、常见问题

### Q: 没有 API Key 怎么办?
可以跳过文案生成，手动写文案后只用语音+视频模块。Edge TTS 完全免费。

### Q: Edge TTS 连不上?
国内网络可能无法直连微软服务器。两种解决方案:
```bash
# 方案A: 配代理
export HTTPS_PROXY=http://127.0.0.1:7890

# 方案B: 用离线TTS(config.py)
TTS_PROVIDER = "offline"
```

### Q: 视频质量不够好?
首先确认已切换到 video 模式(`VIDEO_BG_MODE="video"`)，配合 Pexels API 自动获取应景素材，效果远好于默认卡片。
如果还不满意，建议用本项目生成文案+语音，手动导入剪映制作视频。

### Q: video 模式怎么配置?
```bash
# 1. 免费注册: https://www.pexels.com/api/
# 2. 设置环境变量或编辑 config.py
export PEXELS_API_KEY="你的key"
# 3. 确认 config.py 中 VIDEO_BG_MODE = "video" (默认已是)
# 4. 直接运行，自动按分类搜索下载应景素材
python main.py auto
```
也可以手动放竖屏 MP4 到 `assets/bg_videos/` 目录，会优先使用本地素材。

### Q: 没有 Pexels API Key，video 模式能用吗?
可以手动放视频素材到 `assets/bg_videos/` 目录。如果既没有 API Key 也没有本地素材，会自动降级为 cards 卡片模式。

### Q: 抖音发布失败?
1. Cookie 过期: 重新运行 `python auto_publish.py login`
2. 页面改版: 需要更新 `auto_publish.py` 中的 CSS 选择器
3. 查看错误截图排查

### Q: 如何换AI模型?
编辑 `config.py` 中的 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`，支持所有兼容 OpenAI 接口的模型。

### Q: 一本书蒸馏几集合适?
热门书 5-8 集，内容特别丰富的可以 10 集。在 `config.py` 中设置 `EPISODES_PER_BOOK`，或命令行 `--episodes N`。

### Q: 每集多长合适?
默认 90 秒(约360字)，适合单点蒸馏。深度方法论/故事型可以 `--duration 120`。不建议超过 3 分钟，会影响完播率，也不符合"蒸馏"的精炼调性。

### Q: 如何增加新的书籍分类?
编辑 `config.py` 中的 `BOOK_TARGET_CATEGORIES` 列表即可。

### Q: 声音克隆需要什么条件?
- **Fish Audio(最简单):** 只需注册账号、上传声音样本，拿到 API Key 和模型 ID 填入 config.py 即可，无需 GPU
- **GPT-SoVITS(效果最好):** 需要 NVIDIA GPU(4GB+显存)，本地部署后启动 API 服务

### Q: 没有 GPU 能用数字人吗?
可以。腾讯智影和硅基流动都有在线免费额度，无需 GPU。在网页上操作: 上传照片 + 粘贴文案/上传音频 → 生成视频 → 下载放到对应 ep 目录即可。

### Q: 声音克隆和数字人可以同时用吗?
可以，这是效果最好的组合: 用你的声音 + 你的形象，生成的视频最接近真人出镜。在 config.py 中同时设置:
```python
TTS_PROVIDER = "clone"           # 声音克隆
DIGITAL_HUMAN_ENGINE = "sadtalker"  # 数字人
```

### Q: 录音有什么要求?
- 安静环境，无空调/风扇/电脑散热等背景噪音
- 正常说话，不要刻意播音腔
- 10-30 秒即可，内容随意(读一段书最自然)
- WAV 格式，用手机录音转 WAV 也行

### Q: 启动时提示配置警告?
`main.py` 启动时会自动调用 `validate_config()` 校验 API Key、FFmpeg、TTS 配置等。根据提示修复即可，不影响已配置正确的模块。

---

## 十一、外部工具参考

本项目覆盖了核心生产流程，以下外部工具可配合使用:

### 视频素材与制作

| 工具 | 用途 | 价格 |
|------|------|------|
| Pexels | 高质量免费视频素材(本项目 video 模式已集成) | 免费 API |
| Pixabay | 免费视频/图片素材 | 免费 |
| Mixkit | 免费视频素材 | 免费 |
| 剪映桌面版 | 视频剪辑+TTS+模板，手动制作质量最好 | 免费 |
| 腾讯智影 | 数字人出镜 | 有免费额度 |
| 硅基流动 | 数字人API | 有免费额度 |

### 多平台分发

| 工具 | 说明 | 价格 |
|------|------|------|
| 新榜小豆芽 | 50+平台一键分发，操作简单 | 免费版可用 |
| 蚁小二 | 60+平台，多账号管理 | 付费 |
| 易媒助手 | 防风控，IP隔离，多账号安全 | 付费 |

### 声音克隆(提升TTS质量)

| 工具 | 说明 |
|------|------|
| Fish Audio | 开源声音克隆，几秒样本即可 |
| GPT-SoVITS | 开源，需本地部署 |
| ChatTTS | 开源，专为对话优化 |

---

## 完整工作流

```
┌──────────────────────────────────────────────────────────┐
│          python main.py auto --books 2 --episodes 5      │
└───────────────────────────┬──────────────────────────────┘
                            │
               ┌────────────▼────────────┐
               │  book_crawler.py        │
               │  检查书单 -> 自动补充    │
               └────────────┬────────────┘
                            │
               ┌────────────▼────────────┐
               │  generate_script.py     │
               │  AI 规划5个蒸馏角度      │
               │  逐集生成高密度文案      │
               └────────────┬────────────┘
                            │
                ┌───────────▼───────────┐
                │  每集独立处理(90s):    │
                │                       │
                │  generate_voice.py    │
                │  语音(Edge TTS        │
                │   或声音克隆)         │
                │         |             │
                │  画面(按 VIDEO_BG_MODE │
                │  自动选择):           │
                │  ├ video: bg_video.py │
                │  │ 应景视频+暗层+大字幕│
                │  ├ cards: 卡片画面    │
                │  └ digital_human: 口播│
                │         |             │
                │  bgm_matcher.py       │
                │  智能匹配BGM          │
                │         |             │
                │  generate_video.py    │
                │  合成最终视频          │
                └───────────┬───────────┘
                            │
               ┌────────────▼────────────┐
               │  safety.py              │
               │  敏感词检测 + 限流检查   │
               └────────────┬────────────┘
                            │
               ┌────────────▼────────────┐
               │  auto_publish.py        │
               │  (可选) 自动发布到抖音   │
               │  随机间隔 + 定期休息     │
               └────────────┬────────────┘
                            │
                    循环下一本书...
```
