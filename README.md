# 读书类抖音账号 — 完整落地方案

## 一、账号定位

### 1. 选择细分方向

| 方向 | 示例 | 特点 |
|------|------|------|
| 书单推荐 | "打工人必读的5本书" | 门槛低，起号快，但同质化严重 |
| 拆书/精华解读 | 每本书浓缩成1-3分钟 | 有深度，粉丝粘性强 |
| 金句/名言 | 书中经典段落+文字动画 | 最适合自动化批量生产 |
| 读书vlog | 记录读书过程/书房 | 需要真人出镜 |
| 故事型 | 把书的内容讲成故事 | 完播率高，但对文案要求高 |
| 特定领域 | 只讲心理学/历史/商业书 | 垂直度高，变现容易 |

**建议新手从「金句/书单推荐」入手**，最适合自动化，门槛最低。

### 2. 账号人设

- **账号名**：简洁好记，带"书/读/阅"等关键词（如：三分钟读书、书虫小张）
- **头像**：书本/阅读相关的简约设计
- **简介**：一句话说清楚你是谁+你能提供什么（如："每天一本好书精华，帮你省下80%的阅读时间"）
- **封面统一模板**：保持视觉一致性

### 3. 目标受众

- 职场人（效率/管理/沟通类书）
- 学生（成长/学习方法类书）
- 女性群体（情感/心理/自我提升类书）

---

## 二、内容制作全流程

一条读书类视频的完整生产链：

```
选书 → 提炼内容/文案 → 生成语音 → 制作背景视频 → 添加字幕 → 配背景音乐 → 合成导出
```

---

## 三、自动化工具链

### 1. 文案自动生成

| 工具 | 说明 | 适用场景 |
|------|------|----------|
| ChatGPT / Claude | 输入书名或核心内容，自动生成拆书文案、金句、书单文案 | 最通用 |
| Kimi (月之暗面) | 支持上传整本书PDF，自动总结 | 长文档处理 |
| 通义千问 | 阿里出品，中文效果好 | 中文文案 |
| Coze (扣子) | 字节旗下，可搭建自动化工作流（Bot） | 搭建自动化流水线 |

**Prompt 示例**：

```
请帮我把《被讨厌的勇气》这本书的核心观点提炼成一段60秒的抖音短视频文案。
要求：
1. 开头3秒要有钩子（引起好奇心）
2. 中间讲2-3个核心观点
3. 结尾有金句总结+引导关注
4. 口语化，像在跟朋友聊天
5. 总字数控制在250字左右
```

### 2. AI 语音生成（TTS）

| 工具 | 特点 | 价格 |
|------|------|------|
| 剪映（内置TTS） | 质量高，多种音色，直接在剪映里用 | 免费 |
| 微软 Azure TTS | 效果最自然，支持SSML控制语气 | 有免费额度 |
| Fish Audio | 开源，可克隆任意声音 | 免费/付费 |
| ChatTTS | 开源，专为对话优化 | 免费 |
| GPT-SoVITS | 开源声音克隆，只需几秒样本 | 免费 |
| 豆包/火山引擎TTS | 字节系，中文质量高 | 有免费额度 |
| Eleven Labs | 英文最好，中文也可 | 付费 |

**推荐**：新手直接用剪映内置TTS。进阶用 Fish Audio 或 GPT-SoVITS 克隆独特声音做差异化。

### 3. 背景视频/画面生成

| 形式 | 工具 | 说明 |
|------|------|------|
| 文字动画 | 剪映、CapCut | 文字逐字出现+翻页效果 |
| 图片轮播 | 剪映、Canva | 书的封面+金句图片 |
| AI生成图片 | Midjourney、Stable Diffusion、通义万相、可灵 | 生成与书内容相关的意境图 |
| AI生成视频 | 可灵AI、Runway、Pika、即梦 | 根据文案生成视频片段 |
| 录屏翻书 | 微信读书/Kindle截屏 | 最简单的方式 |
| 虚拟人/数字人 | HeyGen、D-ID、腾讯智影、硅基流动 | 生成虚拟主播讲书 |

**推荐组合**：
- 入门：剪映文字模板 + 书封面图片
- 进阶：通义万相/可灵生成AI图片 + 文字动画
- 高级：数字人出镜（硅基流动/腾讯智影）

### 4. 字幕自动生成

| 工具 | 说明 |
|------|------|
| 剪映（自动识别字幕） | 一键生成，免费，准确率高 |
| CapCut | 剪映海外版 |
| Whisper (OpenAI) | 开源语音转文字，可本地部署 |

### 5. 背景音乐

| 工具 | 说明 |
|------|------|
| 剪映音乐库 | 内置海量免版权音乐，按氛围筛选 |
| Suno AI | AI作曲，输入描述自动生成音乐 |
| Udio | AI音乐生成 |
| 网易AI作曲 / 天工音乐 | 国内平台 |
| Pixabay Music | 免版权音乐库 |

> 抖音对版权有检测，建议用剪映内置音乐或 AI 生成的原创音乐。

### 6. 视频合成/剪辑

| 工具 | 说明 |
|------|------|
| 剪映（桌面版） | 最推荐，一站式完成所有操作 |
| FFmpeg | 命令行工具，可编程批量合成 |
| MoviePy (Python) | Python视频处理库，适合自动化 |
| Remotion | 用代码(React)生成视频 |

### 7. BGM 智能匹配（bgm_matcher.py）

本项目内置了 BGM 智能匹配模块，支持三种模式：

| 模式 | 说明 | 是否需要 API |
|------|------|-------------|
| rule（规则匹配） | 根据书籍分类自动映射到对应情绪的 BGM | 不需要 |
| ai（AI分析） | 让 AI 分析文案情绪，再匹配对应 BGM | 需要 |
| suno（AI生成） | 生成 Suno AI Prompt，为每本书定制原创 BGM | 手动操作 |
| auto（自动） | 有 API Key 时用 AI 分析，否则降级为规则匹配 | 自适应 |

**情绪分类与 BGM 目录：**

```
assets/bgm/
├── calm/          ← 平静舒缓（心理学、哲学类书）
├── inspiring/     ← 励志振奋（成长、效率、商业类书）
├── emotional/     ← 感性温暖（情感、文学、人生感悟类书）
├── thoughtful/    ← 沉思深邃（思维、哲学、科学类书）
└── energetic/     ← 活力动感（书单推荐、快节奏盘点类）
```

只需将 BGM 文件放进对应情绪子目录，合成视频时会自动匹配。也支持直接把 BGM 放在 `assets/bgm/` 根目录，文件名包含情绪关键词（如 `calm_piano_01.mp3`）即可。

**快捷命令：**
```bash
python bgm_matcher.py setup          # 创建情绪子目录
python bgm_matcher.py guide          # 查看分类指南
python bgm_matcher.py match --book "被讨厌的勇气"   # 测试匹配
python bgm_matcher.py suno --book "认知觉醒"        # 生成 Suno Prompt
```

### 8. 封面/缩略图

| 工具 | 说明 |
|------|------|
| Canva | 海量模板，拖拽设计 |
| 创客贴 | 国内版Canva |
| 剪映 | 可直接做封面 |
| AI生成 | 用Midjourney/通义万相生成 |

---

## 四、自动发布方案

### 方案 A：半自动（推荐新手）

- **抖音创作者服务平台** (creator.douyin.com)：PC端上传视频，支持定时发布，可提前一周批量上传排期

### 方案 B：自动化发布工具

| 工具 | 说明 | 类型 |
|------|------|------|
| social-auto-upload | GitHub开源，支持抖音/视频号/B站等多平台自动上传 | 开源免费 |
| MediaCrawler | 爬虫+发布，支持多平台 | 开源 |
| 蚁小二 | 多平台一键分发 | 付费 |
| 融媒宝 | 多平台一键分发 | 付费 |
| Playwright/Selenium | 自己写脚本控制浏览器自动上传 | 需开发 |

`social-auto-upload` 是目前最靠谱的开源方案，用 Playwright 模拟浏览器操作，支持抖音、快手、视频号、B站、小红书等，支持定时发布和批量上传。

### 方案 C：完全自动化流水线（进阶）

用 Python 串起整个流程：

```
Cron定时触发
  → 脚本从书单数据库取下一本书
  → 调用 Claude/GPT API 生成文案
  → 调用 TTS API 生成语音
  → 调用 AI 生图 API 生成背景图
  → FFmpeg/MoviePy 合成视频
  → 调用 social-auto-upload 自动发布
```

---

## 五、执行节奏

### 第一周：准备阶段
- [ ] 注册抖音号，完善资料
- [ ] 确定细分方向（建议金句/书单）
- [ ] 用 Canva 设计头像、封面模板
- [ ] 安装剪映桌面版
- [ ] 注册 Claude/ChatGPT 用于生成文案

### 第二周：手动跑通流程
- [ ] 手动做3-5条视频，跑通全流程
- [ ] 每条视频记录耗时，找出瓶颈
- [ ] 测试不同风格（纯文字/图片/数字人）看数据

### 第三-四周：半自动化
- [ ] 用 AI 批量生成一周的文案
- [ ] 用剪映模板批量套用
- [ ] 用创作者平台定时发布

### 第二个月起：全面自动化
- [ ] 搭建 Python 自动化脚本
- [ ] 部署 social-auto-upload
- [ ] 建立书单数据库，持续补充内容

---

## 六、发布策略

- **频率**：每天 1-2 条（坚持比数量重要）
- **时间**：早7-9点、中午12-13点、晚20-22点
- **标签**：#读书 #好书推荐 #书单 + 书名相关标签
- **前5条视频**：不要急着追数据，先找到节奏
- **互动**：前期每条评论都回复

---

## 七、变现路径

1. **抖音橱窗带货**（卖书）— 1000粉即可开通
2. **知识付费**（付费读书社群/课程）
3. **直播带货**（讲书+卖书）
4. **广告接单**（出版社/知识类APP投放）
5. **引流私域**（微信读书社群）

---

## 八、项目结构

```
douyindemo/
├── README.md              # 本文档
├── config.py              # 全局配置（API密钥、路径等）
├── book_list.json         # 书单数据库
├── generate_script.py     # AI文案生成
├── generate_voice.py      # TTS语音合成
├── generate_video.py      # 视频合成（MoviePy）
├── bgm_matcher.py         # BGM智能匹配（规则/AI情绪分析/Suno）
├── download_bgm.py        # BGM自动搜索下载（Freesound等）
├── auto_publish.py        # 自动发布到抖音（支持抖音平台音乐）
├── main.py                # 主流程：串联所有步骤
├── output/                # 输出目录
│   ├── scripts/           # 生成的文案
│   ├── voices/            # 生成的语音
│   └── videos/            # 合成的视频
├── assets/                # 静态资源
│   ├── fonts/             # 字体文件
│   ├── bgm/               # 背景音乐（按情绪分子目录）
│   │   ├── calm/          # 平静舒缓
│   │   ├── inspiring/     # 励志振奋
│   │   ├── emotional/     # 感性温暖
│   │   ├── thoughtful/    # 沉思深邃
│   │   └── energetic/     # 活力动感
│   └── templates/         # 视频模板/背景图
└── requirements.txt       # Python依赖
```

---

## 九、环境准备与安装

### 1. 前置要求

- Python 3.10+
- FFmpeg（视频合成必需）
- 一个 AI API Key（OpenAI / 通义千问 / DeepSeek / Claude 任选其一）

### 2. 安装 FFmpeg

**Windows**（推荐用 winget 或 scoop）：
```bash
# winget
winget install Gyan.FFmpeg

# 或 scoop
scoop install ffmpeg
```

安装后验证：
```bash
ffmpeg -version
```

### 3. 安装 Python 依赖

```bash
cd douyindemo
pip install -r requirements.txt
```

### 4. 安装 Playwright 浏览器（自动发布需要）

```bash
playwright install chromium
```

### 5. 配置 API Key

有两种方式，任选其一：

**方式 A：环境变量（推荐）**

```bash
# OpenAI
export OPENAI_API_KEY="sk-xxxxxxxx"

# 如果用国内模型，额外设置 BASE_URL 和 MODEL
# 通义千问
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export OPENAI_MODEL="qwen-plus"

# DeepSeek
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_MODEL="deepseek-chat"

# Kimi
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
export OPENAI_MODEL="moonshot-v1-8k"

# 如果用 Claude
export CLAUDE_API_KEY="sk-ant-xxxxxxxx"
```

**方式 B：直接编辑 config.py**

打开 `config.py`，找到对应的配置项修改即可。

### 6. （可选）配置语音角色

默认使用 `zh-CN-YunxiNeural`（男声），可在 `config.py` 中修改 `EDGE_TTS_VOICE`。

查看所有可用中文语音：
```bash
python generate_voice.py --list-voices
```

常用语音：
| 语音ID | 性别 | 风格 |
|--------|------|------|
| zh-CN-YunxiNeural | 男 | 年轻，适合讲书 |
| zh-CN-YunjianNeural | 男 | 沉稳，适合深度解读 |
| zh-CN-XiaoxiaoNeural | 女 | 温柔，适合情感类书籍 |
| zh-CN-XiaoyiNeural | 女 | 活泼，适合书单推荐 |

### 7. 背景音乐（三种方案，无需手动下载）

在 `config.py` 中设置 `BGM_SOURCE` 选择方案：

```python
BGM_SOURCE = "download"   # 方案A: 自动下载免费音乐（默认）
BGM_SOURCE = "douyin"     # 方案B: 发布时直接用抖音平台音乐（最省事）
BGM_SOURCE = "local"      # 方案C: 使用本地 assets/bgm/ 中的音乐
```

**方案 A：自动下载（推荐）**

从 Freesound 等免费音乐库按情绪自动搜索下载，零手动操作：

```bash
# 需要先配置 Freesound API Key（免费注册）
export FREESOUND_API_KEY="your-key"

# 一键下载所有情绪分类的 BGM
python download_bgm.py download

# 只下载指定情绪
python download_bgm.py download --mood calm --count 5
```

注册 Freesound API Key（免费）: https://freesound.org/apiv2/apply/

没有 API Key 也没关系，运行主流程时如果检测到本地无 BGM 会自动尝试下载。

**方案 B：使用抖音平台音乐（最省事，零版权风险）**

视频生成时不加 BGM，在发布环节自动从抖音音乐库搜索添加。好处：
- 完全零版权风险（抖音已购买授权）
- 可以蹭热门音乐的流量
- 抖音会根据音乐推荐流量

```bash
# 发布时自动添加抖音音乐
python auto_publish.py upload --video xxx.mp4 --title "xxx" --douyin-music

# 指定音乐搜索关键词
python auto_publish.py upload --video xxx.mp4 --title "xxx" --douyin-music --music-keyword "轻音乐"
```

**方案 C：本地音乐**

手动放 MP3 到 `assets/bgm/` 即可。没有 API Key 时可以查看免费下载指南：
```bash
python download_bgm.py guide
```

### 8. （可选）添加自定义字体

将 `.ttf` 或 `.otf` 字体文件放入 `assets/fonts/` 目录，会自动优先使用。

不放的话默认使用系统字体（微软雅黑）。

---

## 十、使用方式

### 核心命令

```bash
# 处理书单中下一本书（自动执行：文案→语音→视频）
python main.py next

# 批量处理 3 本
python main.py batch --count 3

# 处理书单中所有待处理的书
python main.py batch --all

# 指定视频时长为 90 秒（默认 60 秒）
python main.py next --duration 90

# 生成后自动发布到抖音
python main.py next --publish

# 批量生成并发布
python main.py batch --all --publish

# 重置所有书籍状态为 pending（重新开始）
python main.py reset
```

### 单独使用各模块

**单独生成文案：**
```bash
# 自动取书单中下一本
python generate_script.py

# 指定书名
python generate_script.py --book "被讨厌的勇气"

# 批量生成所有文案
python generate_script.py --all

# 指定时长（影响字数）
python generate_script.py --duration 90
```

**单独生成语音：**
```bash
# 从文案文件生成语音
python generate_voice.py --file output/scripts/被讨厌的勇气_20260331.txt

# 直接输入文本
python generate_voice.py --text "你有没有想过，为什么你总是在意别人的看法？"

# 不生成字幕
python generate_voice.py --file xxx.txt --no-subtitle

# 查看所有可用语音
python generate_voice.py --list-voices
```

**单独合成视频：**
```bash
python generate_video.py \
  --voice output/voices/被讨厌的勇气_20260331.mp3 \
  --subtitle output/voices/被讨厌的勇气_20260331.srt \
  --title "被讨厌的勇气" \
  --author "岸见一郎" \
  --bgm assets/bgm/light_piano.mp3 \
  --bgm-volume 0.2
```

**单独发布到抖音：**
```bash
# 首次使用：登录抖音（扫码，只需一次）
python auto_publish.py login

# 上传视频
python auto_publish.py upload \
  --video output/videos/被讨厌的勇气_20260331.mp4 \
  --title "看完这本书，我才明白为什么你总是活得那么累" \
  --tags 读书 好书推荐 心理学

# 定时发布
python auto_publish.py upload \
  --video output/videos/xxx.mp4 \
  --title "xxx" \
  --time "2026-04-01 20:30"
```

### 管理书单

编辑 `book_list.json` 即可添加新书，格式：

```json
{
  "id": 11,
  "title": "书名",
  "author": "作者",
  "category": "分类",
  "description": "一句话简介（AI会基于此生成文案）",
  "tags": ["标签1", "标签2"],
  "status": "pending"
}
```

status 字段说明：
- `pending` — 待处理
- `script_done` — 文案已生成
- `done` — 全流程完成
- `error` — 处理出错

---

## 十一、完整工作流示意

```
┌─────────────────────────────────────────────────────┐
│                  python main.py next                │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │  1. 从 book_list.json   │
          │     取下一本 pending 书  │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  2. generate_script.py  │
          │  调用 AI API 生成文案    │
          │  → output/scripts/*.txt │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  3. generate_voice.py   │
          │  Edge TTS 生成语音+字幕  │
          │  → output/voices/*.mp3  │
          │  → output/voices/*.srt  │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  4. bgm_matcher.py      │
          │  智能匹配背景音乐        │
          │  (规则/AI情绪/Suno生成)  │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  5. generate_video.py   │
          │  MoviePy 合成视频        │
          │  语音+字幕+书名+BGM     │
          │  → output/videos/*.mp4  │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  6. auto_publish.py     │
          │  (可选) Playwright      │
          │  自动发布到抖音          │
          └─────────────────────────┘
```

---

## 十二、常见问题

### Q: 没有 API Key 怎么办？
可以先手动写文案，只用语音合成+视频合成模块。Edge TTS 完全免费，不需要任何 Key。

### Q: 视频没有背景音乐？
在 `assets/bgm/` 目录放入 MP3 文件即可。没有的话视频只有语音，也能用。

### Q: 字幕位置/大小不对？
编辑 `config.py` 中的 `SUBTITLE_FONT_SIZE`、`TITLE_FONT_SIZE` 等参数调整。

### Q: 如何更换 AI 模型？
编辑 `config.py`，修改 `LLM_PROVIDER`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。支持所有 OpenAI 兼容接口的模型。

### Q: 抖音发布失败？
1. 先确认 Cookie 没过期：重新运行 `python auto_publish.py login`
2. 查看 `output/videos/` 下的错误截图排查问题
3. 抖音页面改版可能导致选择器失效，需要更新 `auto_publish.py` 中的选择器

### Q: 如何提升视频质量？
1. 在 `assets/templates/` 放入背景图片（后续版本支持）
2. 用 AI 生成配图（Midjourney / 通义万相）替换纯色背景
3. 使用更好的字体（推荐：思源黑体、阿里巴巴普惠体）
4. 在 `config.py` 中调整 `VIDEO_FPS` 和编码参数
