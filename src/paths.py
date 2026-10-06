"""集中处理开发环境 / PyInstaller 冻结环境的路径差异。"""
from __future__ import annotations
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """
    用户可见的工作目录：
      - 打包后：exe 所在文件夹（input-video / output / temp_audio 都放这里）
      - 开发时：项目根目录（src 的上一级）
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """
    只读资源目录（模型 / ffmpeg）：
      - 打包后：PyInstaller 解包出来的 _internal 目录
      - 开发时：项目根目录
    两种情况下，其下都有 models\\ 和 ffmpeg.exe。
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent.parent