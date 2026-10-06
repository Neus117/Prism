import os
import sys
import locale
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


# =========================================================
# 轻量 i18n：检测系统语言，零依赖，可按需扩展
# =========================================================
def _detect_lang() -> str:
    env = os.environ.get("PRISM_LANG", "").strip().lower()
    if env.startswith("zh"):
        return "zh"
    if env.startswith("en"):
        return "en"
    try:
        code = (locale.getdefaultlocale()[0] or "en").lower()
    except Exception:
        code = "en"
    return "zh" if code.startswith("zh") else "en"


_LANG = _detect_lang()

_T = {
    "zh": {
        "banner_title":   "Prism —— 批量音频/视频分轨工具 (CPU)",
        "working_dir":    "📂 工作目录: {path}",
        "ffmpeg_ok":      "✅ FFmpeg 已就绪: {ver}",
        "ffmpeg_missing": "❌ 错误：无法找到或运行 FFmpeg，请检查路径: {path}",
        "start_media":    "\n🎬 开始处理{kind}: {name}",
        "kind_video":     "视频",
        "kind_audio":     "音频",
        "skipped":        "⏭️  跳过：{name} 的分离结果已存在。",
        "extract_audio":  "  🎵 正在提取音频并重采样至 44.1kHz 双声道 WAV...",
        "resample":       "  🎵 正在重采样至 44.1kHz 双声道 WAV...",
        "ffmpeg_fail":    "  ❌ FFmpeg 处理失败: {err}",
        "empty_audio":    "  ❌ 提取的音频文件为空，跳过。",
        "separating":     "  🧠 正在运行 HT-Demucs FT 分离...",
        "separate_fail":  "  ❌ 分离失败: {err}",
        "saving":         "  💾 正在保存分离后的音轨...",
        "saved_one":      "    ✓ 已保存: {name}",
        "done_media":     "✅ 完成: {name}",
        "no_media":       "⚠️  在 {path} 中没有找到可处理的视频或音频文件。",
        "found_media":    "📂 发现 {n} 个媒体文件，开始批量处理...",
        "interrupted":    "\n🛑 用户中断操作。",
        "unknown_error":  "\n❌ 处理 {name} 时发生未知错误: {err}",
        "all_done":       "\n🎉 所有任务处理完毕！",
        "press_enter":    "\n按回车退出...",
    },
    "en": {
        "banner_title":   "Prism — Batch Audio/Video Source Separation Tool (CPU)",
        "working_dir":    "📂 Working directory: {path}",
        "ffmpeg_ok":      "✅ FFmpeg ready: {ver}",
        "ffmpeg_missing": "❌ Error: FFmpeg not found or failed to run. Check path: {path}",
        "start_media":    "\n🎬 Processing {kind}: {name}",
        "kind_video":     "video",
        "kind_audio":     "audio",
        "skipped":        "⏭️  Skipped: separation results for {name} already exist.",
        "extract_audio":  "  🎵 Extracting audio and resampling to 44.1kHz stereo WAV...",
        "resample":       "  🎵 Resampling to 44.1kHz stereo WAV...",
        "ffmpeg_fail":    "  ❌ FFmpeg failed: {err}",
        "empty_audio":    "  ❌ Extracted audio is empty, skipping.",
        "separating":     "  🧠 Running HT-Demucs FT separation...",
        "separate_fail":  "  ❌ Separation failed: {err}",
        "saving":         "  💾 Saving separated stems...",
        "saved_one":      "    ✓ Saved: {name}",
        "done_media":     "✅ Done: {name}",
        "no_media":       "⚠️  No media files found in {path}.",
        "found_media":    "📂 Found {n} media file(s), starting batch processing...",
        "interrupted":    "\n🛑 User interrupted.",
        "unknown_error":  "\n❌ Unknown error while processing {name}: {err}",
        "all_done":       "\n🎉 All tasks completed!",
        "press_enter":    "\nPress Enter to exit...",
    },
}


def t(key: str, **kw) -> str:
    s = _T[_LANG].get(key) or _T["en"].get(key) or key
    return s.format(**kw) if kw else s


def check_ffmpeg():
    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-version"],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="ignore",
        )
        print(t("ffmpeg_ok", ver=result.stdout.splitlines()[0]))
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(t("ffmpeg_missing", path=FFMPEG_PATH))
        return False


def process_media(media_path: Path):
    media_name = media_path.stem
    suffix = media_path.suffix.lower()
    is_video = suffix in VIDEO_EXTENSIONS
    kind = t("kind_video") if is_video else t("kind_audio")

    print("=" * 60)
    print(t("start_media", kind=kind, name=media_path.name))

    media_output_dir = OUTPUT_DIR / media_name
    media_output_dir.mkdir(parents=True, exist_ok=True)

    if not OVERWRITE_EXISTING:
        existing_stems = list(media_output_dir.glob("*.wav"))
        if len(existing_stems) >= 4:
            print(t("skipped", name=media_name))
            return

    # 中间文件统一用无损 WAV，避免二次压缩损失
    temp_audio_path = TEMP_AUDIO_DIR / f"{media_name}_temp.wav"
    print(t("extract_audio") if is_video else t("resample"))

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
        print(t("ffmpeg_fail", err=e.stderr))
        return

    if not temp_audio_path.exists() or temp_audio_path.stat().st_size == 0:
        print(t("empty_audio"))
        return

    print(t("separating"))
    try:
        stems = bag_infer.separate_all(str(temp_audio_path))
    except Exception as e:
        print(t("separate_fail", err=str(e)))
        if temp_audio_path.exists():
            temp_audio_path.unlink()
        return

    print(t("saving"))
    import soundfile as sf
    for stem_name, audio_data in stems.items():
        out_file_name = f"{media_name}_{stem_name}.wav"
        out_file_path = media_output_dir / out_file_name
        sf.write(str(out_file_path), audio_data.T, bag_infer.SAMPLE_RATE)
        print(t("saved_one", name=out_file_name))

    if temp_audio_path.exists():
        temp_audio_path.unlink()

    print(t("done_media", name=media_name))


def main():
    print("=" * 60)
    print("🚀 " + t("banner_title"))
    print("=" * 60)
    print(t("working_dir", path=BASE_DIR))

    INPUT_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    if not check_ffmpeg():
        # 打包后如果用户没按回车就闪退，会看不到错误，这里等一下
        if getattr(sys, "frozen", False):
            input(t("press_enter"))
        return

    media_files = sorted(
        [f for f in INPUT_MEDIA_DIR.iterdir()
         if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )

    if not media_files:
        print(t("no_media", path=INPUT_MEDIA_DIR))
        if getattr(sys, "frozen", False):
            input(t("press_enter"))
        return

    print(t("found_media", n=len(media_files)))

    for media_file in media_files:
        try:
            process_media(media_file)
        except KeyboardInterrupt:
            print(t("interrupted"))
            break
        except Exception as e:
            print(t("unknown_error", name=media_file.name, err=str(e)))
            continue

    print(t("all_done"))
    if getattr(sys, "frozen", False):
        input(t("press_enter"))


if __name__ == "__main__":
    main()