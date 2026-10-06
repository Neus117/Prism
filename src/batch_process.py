import os
import sys
import subprocess
from pathlib import Path

import bag_infer

# [打包改动] 用 paths 模块统一解析路径：
#   app_dir()      —— 用户可见的工作目录（exe 同级 / 开发时的项目根）
#   resource_dir() —— 只读资源目录（_internal / 开发时的项目根）
from paths import app_dir, resource_dir

BASE_DIR         = app_dir()
INPUT_MEDIA_DIR  = BASE_DIR / "input-video"   # 视频和音频都放这里
OUTPUT_DIR       = BASE_DIR / "output"
TEMP_AUDIO_DIR   = BASE_DIR / "temp_audio"

# [打包改动] ffmpeg 跟随打包资源目录；不再硬编码绝对路径
FFMPEG_PATH = str(resource_dir() / "ffmpeg.exe")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".aiff"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

OVERWRITE_EXISTING = False


def check_ffmpeg():
    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-version"],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="ignore",
        )
        print(f"✅ FFmpeg 已就绪: {result.stdout.splitlines()[0]}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"❌ 错误：无法找到或运行 FFmpeg，请检查路径: {FFMPEG_PATH}")
        return False


def process_media(media_path: Path):
    media_name = media_path.stem
    suffix = media_path.suffix.lower()
    is_video = suffix in VIDEO_EXTENSIONS
    kind = "视频" if is_video else "音频"

    print(f"\n{'='*50}")
    print(f"🎬 开始处理{kind}: {media_path.name}")

    media_output_dir = OUTPUT_DIR / media_name
    media_output_dir.mkdir(parents=True, exist_ok=True)

    if not OVERWRITE_EXISTING:
        existing_stems = list(media_output_dir.glob("*.wav"))
        if len(existing_stems) >= 4:
            print(f"⏭️  跳过：{media_name} 的分离结果已存在。")
            return

    # 中间文件统一用无损 WAV，避免二次压缩损失
    temp_audio_path = TEMP_AUDIO_DIR / f"{media_name}_temp.wav"
    if is_video:
        print(f"  🎵 正在提取音频并重采样至 44.1kHz 双声道 WAV...")
    else:
        print(f"  🎵 正在重采样至 44.1kHz 双声道 WAV...")

    ffmpeg_cmd = [
        FFMPEG_PATH, "-y",
        "-i", str(media_path),
        "-vn",                      # 视频去视频流；音频文件此参数无害
        "-ar", "44100",
        "-ac", "2",
        "-c:a", "pcm_s16le",        # 16-bit PCM WAV
        str(temp_audio_path),
    ]

    try:
        subprocess.run(
            ffmpeg_cmd, check=True, capture_output=True,
            text=True, encoding="utf-8", errors="ignore",
        )
    except subprocess.CalledProcessError as e:
        print(f"  ❌ FFmpeg 处理失败: {e.stderr}")
        return

    if not temp_audio_path.exists() or temp_audio_path.stat().st_size == 0:
        print("  ❌ 提取的音频文件为空，跳过。")
        return

    print(f"  🧠 正在运行 HT-Demucs FT 分离...")
    try:
        stems = bag_infer.separate_all(str(temp_audio_path))
    except Exception as e:
        print(f"  ❌ 分离失败: {str(e)}")
        if temp_audio_path.exists():
            temp_audio_path.unlink()
        return

    print(f"  💾 正在保存分离后的音轨...")
    import soundfile as sf
    for stem_name, audio_data in stems.items():
        out_file_name = f"{media_name}_{stem_name}.wav"
        out_file_path = media_output_dir / out_file_name
        sf.write(str(out_file_path), audio_data.T, bag_infer.SAMPLE_RATE)
        print(f"    ✓ 已保存: {out_file_name}")

    if temp_audio_path.exists():
        temp_audio_path.unlink()

    print(f"✅ 完成: {media_name}")


def main():
    print("🚀 批量视频/音频人声分离工具启动 (CPU)...")
    print(f"📂 工作目录: {BASE_DIR}")

    INPUT_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    if not check_ffmpeg():
        # 打包后如果用户没按回车就闪退，会看不到错误，这里等一下
        if getattr(sys, "frozen", False):
            input("\n按回车退出...")
        return

    media_files = sorted(
        [f for f in INPUT_MEDIA_DIR.iterdir()
         if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )

    if not media_files:
        print(f"⚠️  在 {INPUT_MEDIA_DIR} 中没有找到可处理的视频或音频文件。")
        if getattr(sys, "frozen", False):
            input("\n按回车退出...")
        return

    print(f"📂 发现 {len(media_files)} 个媒体文件，开始批量处理...")

    for media_file in media_files:
        try:
            process_media(media_file)
        except KeyboardInterrupt:
            print("\n🛑 用户中断操作。")
            break
        except Exception as e:
            print(f"\n❌ 处理 {media_file.name} 时发生未知错误: {str(e)}")
            continue

    print("\n🎉 所有任务处理完毕！")
    if getattr(sys, "frozen", False):
        input("\n按回车退出...")


if __name__ == "__main__":
    main()