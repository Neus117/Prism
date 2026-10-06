"""
Uninstall Prism
-----------------------------
绿色卸载：删除本程序所在文件夹，可选择保留 input-video / output 用户数据。
"""
from __future__ import annotations

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path


DETACHED_PROCESS = 0x00000008


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _pause() -> None:
    try:
        input("\n按回车退出...")
    except EOFError:
        pass


def _ask(prompt: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        raw = input(f"{prompt} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    return raw in ("y", "yes")


def _count_files(d: Path) -> int:
    if not d.exists():
        return 0
    return sum(1 for p in d.rglob("*") if p.is_file())


def _write_bat(target: Path, keep_data: bool) -> Path:
    bat = Path(tempfile.gettempdir()) / "prism_uninstall.bat"
    t   = str(target)
    tmp = tempfile.gettempdir()

    L: list[str] = [
        "@echo off",
        f'cd /d "{tmp}"',
        "ping 127.0.0.1 -n 4 >nul",
        "",
        "rem --- program files ---",
        f'if exist "{t}\\_internal"  rmdir /s /q "{t}\\_internal"',
        f'if exist "{t}\\models"     rmdir /s /q "{t}\\models"',
        f'for %%F in ("{t}\\*.exe") do del /f /q "%%F"',
        f'if exist "{t}\\temp_audio" rmdir /s /q "{t}\\temp_audio"',
        "",
    ]

    if not keep_data:
        L += [
            "rem --- user data ---",
            f'if exist "{t}\\input-video" rmdir /s /q "{t}\\input-video"',
            f'if exist "{t}\\output"      rmdir /s /q "{t}\\output"',
            "",
            "rem --- top folder ---",
            f'rmdir "{t}" 2>nul',
            "",
        ]

    L += [
        'start "" /b cmd /c del /f /q "%~f0"',
        "exit /b 0",
    ]

    bat.write_text("\r\n".join(L), encoding="ascii")
    return bat


def main() -> int:
    target = _app_dir()

    print("=" * 60)
    print("  Prism 卸载程序")
    print("=" * 60)
    print(f"  安装目录：{target}")
    print()

    if not (target / "Prism.exe").exists():
        print("  ⚠️  未在目标目录中找到 Prism.exe。")
        print("      这似乎不是 Prism 的安装目录。")
        if not _ask("仍要继续删除？", default=False):
            print("  已取消。")
            _pause()
            return 1
        print()

    in_dir  = target / "input-video"
    out_dir = target / "output"
    has_user_data = in_dir.exists() or out_dir.exists()

    keep_data = False
    if has_user_data:
        print("  检测到用户数据：")
        if in_dir.exists():
            print(f"    • input-video\\  ({_count_files(in_dir)} 个文件)")
        if out_dir.exists():
            print(f"    • output\\       ({_count_files(out_dir)} 个文件)")
        print()
        print("  是否保留这些用户数据？")
        print("    保留 → 只删除程序文件，你的素材和分离结果会留下")
        print("    删除 → 连同用户数据一起清空，不可恢复")
        keep_data = _ask("保留用户数据？", default=True)
        print()

    print("  即将执行：")
    print("    ✓ 删除 Prism.exe、uninstall.exe、_internal、models")
    if keep_data:
        print("    ✓ 保留 input-video\\ 与 output\\")
    else:
        print("    ✗ 连同 input-video\\ 与 output\\ 一起删除，不可恢复")
    print()
    if not _ask("确认卸载？", default=False):
        print("  已取消。")
        _pause()
        return 0

    bat = _write_bat(target, keep_data)
    print(f"\n  正在启动卸载脚本：{bat}")
    print("  本窗口将在 2 秒内关闭，随后在后台完成删除。")
    print("  （如果删除未生效，请稍等 5 秒后手动检查安装目录）")

    os.chdir(tempfile.gettempdir())

    subprocess.Popen(
        ["cmd", "/c", str(bat)],
        cwd=tempfile.gettempdir(),
        close_fds=True,
        creationflags=DETACHED_PROCESS,
    )
    time.sleep(2.0)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        _pause()
        sys.exit(1)