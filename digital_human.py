"""
数字人视频生成模块
上传一张正面照片 + 音频，生成口播数字人视频

支持方案:
1. SadTalker  — 开源，本地部署，需要GPU，免费
2. HeyGen     — 在线API，效果最好，付费
3. MuseTalk   — 开源，实时唇形同步，需要GPU

使用方式:
1. 准备一张正面照片(半身/头像，表情自然，光线均匀)
   放到 assets/avatar/photo.png
2. 选择一个方案部署/配置
3. 在 config.py 中设置 DIGITAL_HUMAN_ENGINE
4. 运行时自动生成数字人视频替代卡片画面
"""

import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from config import (
    DIGITAL_HUMAN_ENGINE,
    DIGITAL_HUMAN_PHOTO,
    SADTALKER_PATH,
    HEYGEN_API_KEY,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
)


def is_enabled() -> bool:
    """数字人功能是否启用"""
    return bool(DIGITAL_HUMAN_ENGINE)


def generate_talking_video(
    audio_path: str | Path,
    photo_path: str | Path = None,
    output_path: str | Path = None,
) -> Path | None:
    """
    生成数字人口播视频

    Args:
        audio_path: 语音文件路径
        photo_path: 人物照片路径(不指定则用 config 中的默认照片)
        output_path: 输出视频路径

    Returns:
        生成的视频路径，或 None(失败时)
    """
    audio_path = Path(audio_path)
    photo_path = Path(photo_path or DIGITAL_HUMAN_PHOTO)

    if not photo_path.exists():
        print(f"  [数字人] 照片不存在: {photo_path}")
        print(f"  请将正面照片放到 assets/avatar/photo.png")
        return None

    if output_path is None:
        output_path = audio_path.parent / "talking_head.mp4"
    output_path = Path(output_path)

    if DIGITAL_HUMAN_ENGINE == "sadtalker":
        return _generate_sadtalker(audio_path, photo_path, output_path)
    elif DIGITAL_HUMAN_ENGINE == "heygen":
        return _generate_heygen(audio_path, photo_path, output_path)
    else:
        print(f"  [数字人] 未知引擎: {DIGITAL_HUMAN_ENGINE}")
        return None


# ============================================================
# SadTalker (开源本地部署)
# https://github.com/OpenTalker/SadTalker
# ============================================================

def _generate_sadtalker(
    audio_path: Path,
    photo_path: Path,
    output_path: Path,
) -> Path | None:
    """
    调用 SadTalker 生成数字人视频

    前提: 已克隆并安装 SadTalker
      git clone https://github.com/OpenTalker/SadTalker
      cd SadTalker && pip install -r requirements.txt
      下载预训练模型(见项目README)

    需要: GPU (NVIDIA, 至少4GB显存)
    """
    sadtalker_dir = Path(SADTALKER_PATH)
    if not sadtalker_dir.exists():
        print(f"  [SadTalker] 目录不存在: {sadtalker_dir}")
        print(f"  请先部署 SadTalker: https://github.com/OpenTalker/SadTalker")
        return None

    inference_script = sadtalker_dir / "inference.py"
    if not inference_script.exists():
        print(f"  [SadTalker] 未找到 inference.py")
        return None

    try:
        cmd = [
            "python", str(inference_script),
            "--driven_audio", str(audio_path),
            "--source_image", str(photo_path),
            "--result_dir", str(output_path.parent),
            "--enhancer", "gfpgan",  # 人脸增强
            "--still",  # 只动嘴，头部不大幅运动(更稳定)
            "--preprocess", "crop",  # 自动裁剪人脸区域
        ]

        print(f"  [SadTalker] 正在生成数字人视频...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(sadtalker_dir),
        )

        if result.returncode != 0:
            print(f"  [SadTalker] 生成失败: {result.stderr[:300]}")
            return None

        # SadTalker 输出到 result_dir 下，找到生成的视频
        # 只查找本次生成的新文件（排除已有的 output_path）
        generated = [
            p for p in output_path.parent.glob("*.mp4")
            if p != output_path and p.name != "video.mp4"
        ]
        if generated:
            latest = max(generated, key=lambda p: p.stat().st_mtime)
            # 使用 shutil.move 确保跨文件系统也能工作，且覆盖已有文件
            import shutil
            shutil.move(str(latest), str(output_path))
            print(f"  [SadTalker] 数字人视频已生成: {output_path}")
            return output_path

        print(f"  [SadTalker] 未找到生成的视频文件")
        return None

    except subprocess.TimeoutExpired:
        print(f"  [SadTalker] 生成超时(>5分钟)")
        return None
    except Exception as e:
        print(f"  [SadTalker] 出错: {e}")
        return None


# ============================================================
# HeyGen (在线API，效果最好)
# https://www.heygen.com
# ============================================================

def _generate_heygen(
    audio_path: Path,
    photo_path: Path,
    output_path: Path,
) -> Path | None:
    """
    调用 HeyGen API 生成数字人视频

    注意: HeyGen 是付费服务，但效果最好
    注册: https://www.heygen.com
    """
    if not HEYGEN_API_KEY:
        print("  [HeyGen] 未配置 HEYGEN_API_KEY")
        return None

    # HeyGen 的完整 API 调用流程较复杂(需要先上传素材、创建项目等)
    # 这里提供基本框架，实际使用需根据 HeyGen 最新 API 文档调整

    print(f"  [HeyGen] HeyGen API 集成需要根据最新文档适配")
    print(f"  建议直接在 HeyGen 网页版操作:")
    print(f"    1. 上传照片创建数字人形象")
    print(f"    2. 上传音频或粘贴文案")
    print(f"    3. 生成并下载视频")
    print(f"    4. 将视频放到对应的 ep 目录下")
    return None


# ============================================================
# 工具函数
# ============================================================

def check_photo(photo_path: str | Path = None) -> dict:
    """
    检查照片是否适合用于数字人生成

    Returns:
        {"ok": bool, "message": str, "suggestions": [str]}
    """
    photo_path = Path(photo_path or DIGITAL_HUMAN_PHOTO)

    if not photo_path.exists():
        return {
            "ok": False,
            "message": f"照片不存在: {photo_path}",
            "suggestions": [
                "请准备一张正面照片放到 assets/avatar/photo.png",
                "要求: 正面、光线均匀、背景简洁、表情自然",
                "推荐: 半身照或头肩照，分辨率 512x512 以上",
            ],
        }

    try:
        from PIL import Image
        img = Image.open(str(photo_path))
        img.verify()  # 验证图片文件完整性
        # verify() 后需要重新打开获取尺寸
        img = Image.open(str(photo_path))
        w, h = img.size

        suggestions = []
        ok = True

        if w < 256 or h < 256:
            suggestions.append(f"分辨率偏低({w}x{h})，建议至少 512x512")
            ok = False

        if img.mode != "RGB":
            suggestions.append(f"颜色模式为 {img.mode}，建议转为 RGB")

        if w / h > 2 or h / w > 2:
            suggestions.append("宽高比过大，建议接近 1:1 或 3:4")
            ok = False

        if not suggestions:
            suggestions.append("照片基本符合要求")

        return {
            "ok": ok,
            "message": f"照片尺寸: {w}x{h}, 格式: {img.format}",
            "suggestions": suggestions,
        }

    except ImportError:
        return {"ok": True, "message": "Pillow 未安装，跳过检查", "suggestions": []}
    except Exception as e:
        return {"ok": False, "message": f"读取照片失败: {e}", "suggestions": []}


def print_setup_guide():
    """打印数字人方案对比和部署指引"""
    print("""
============================================================
  数字人方案对比
============================================================

  方案        | 效果  | 成本    | 部署难度 | 需要GPU
  ------------|-------|---------|----------|--------
  SadTalker   | 好    | 免费    | 中       | 是(4GB+)
  MuseTalk    | 较好  | 免费    | 中       | 是(6GB+)
  HeyGen      | 最好  | 付费    | 无需部署 | 否
  腾讯智影    | 好    | 有免费额度 | 无需部署 | 否
  硅基流动    | 好    | 有免费额度 | 无需部署 | 否

------------------------------------------------------------
  推荐:
  - 有GPU -> SadTalker(免费，效果好)
  - 无GPU，少量使用 -> 腾讯智影/硅基流动(免费额度)
  - 追求最佳效果 -> HeyGen(付费)
------------------------------------------------------------

  SadTalker 部署步骤:
  1. git clone https://github.com/OpenTalker/SadTalker
  2. cd SadTalker && pip install -r requirements.txt
  3. 下载预训练模型(见项目README)
  4. 在 config.py 中设置:
     DIGITAL_HUMAN_ENGINE = "sadtalker"
     SADTALKER_PATH = "/path/to/SadTalker"

  照片要求:
  - 正面半身照或头肩照
  - 表情自然，嘴巴闭合
  - 光线均匀，背景简洁
  - 分辨率 512x512 以上
  - 放到 assets/avatar/photo.png

  录音要求(声音克隆):
  - 10-30秒清晰人声
  - 安静环境，无背景噪音
  - WAV格式，16kHz以上
  - 放到 assets/voice_sample/sample.wav
""")


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数字人视频生成工具")
    subparsers = parser.add_subparsers(dest="command")

    # guide: 查看方案对比
    subparsers.add_parser("guide", help="查看数字人方案对比和部署指引")

    # check: 检查照片
    check_parser = subparsers.add_parser("check", help="检查照片是否符合要求")
    check_parser.add_argument("--photo", type=str, help="照片路径")

    # generate: 生成数字人视频
    gen_parser = subparsers.add_parser("generate", help="生成数字人视频")
    gen_parser.add_argument("--audio", type=str, required=True, help="音频文件路径")
    gen_parser.add_argument("--photo", type=str, help="照片路径")
    gen_parser.add_argument("--output", type=str, help="输出视频路径")

    args = parser.parse_args()

    if args.command == "guide":
        print_setup_guide()
    elif args.command == "check":
        result = check_photo(args.photo)
        print(f"\n  {result['message']}")
        for s in result["suggestions"]:
            print(f"  - {s}")
    elif args.command == "generate":
        if not is_enabled():
            print("数字人未启用，请在 config.py 中设置 DIGITAL_HUMAN_ENGINE")
        else:
            result = generate_talking_video(args.audio, args.photo, args.output)
            if result:
                print(f"生成完成: {result}")
    else:
        parser.print_help()
