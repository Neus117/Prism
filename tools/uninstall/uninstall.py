"""
Uninstall Prism
-----------------------------
绿色卸载：删除本程序所在文件夹，可选择保留 input-video / output 用户数据。
"""
from __future__ import annotations

import os
import sys
import time
import locale
import tempfile
import subprocess
from pathlib import Path


DETACHED_PROCESS = 0x00000008


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
        "title":          "Prism 卸载程序",
        "install_dir":    "  安装目录：{path}",
        "no_exe":         "  ⚠️  未在目标目录中找到 Prism.exe。",
        "no_exe_hint":    "      这似乎不是 Prism 的安装目录。",
        "ask_continue":   "仍要继续删除？",
        "cancelled":      "  已取消。",
        "user_data":      "  检测到用户数据：",
        "files_n":        "  ({n} 个文件)",
        "ask_keep":       "是否保留这些用户数据？",
        "keep_hint":      "    保留 → 只删除程序文件，你的素材和分离结果会留下",
        "del_hint":       "    删除 → 连同用户数据一起清空，不可恢复",
        "ask_keep_short": "保留用户数据？",
        "about_to":       "  即将执行：",
        "del_prog":       "    ✓ 删除 Prism.exe、uninstall.exe、_internal、models",
        "keep_data":      "    ✓ 保留 input-video\\ 与 output\\",
        "del_data":       "    ✗ 连同 input-video\\ 与 output\\ 一起删除，不可恢复",
        "ask_confirm":    "确认卸载？",
        "launching":      "\n  正在启动卸载脚本：{path}",
        "closing":        "  本窗口将在 2 秒内关闭，随后在后台完成删除。",
        "closing_hint":   "  （如果删除未生效，请稍等 5 秒后手动检查安装目录）",
        "press_enter":    "\n按回车退出...",
    },
    "en": {
        "title":          "Prism Uninstaller",
        "install_dir":    "  Install directory: {path}",
        "no_exe":         "  ⚠️  Prism.exe was not found in the target directory.",
        "no_exe_hint":    "      This does not appear to be the Prism install directory.",
        "ask_continue":   "Continue anyway?",
        "cancelled":      "  Cancelled.",
        "user_data":      "  User data detected:",
        "files_n":        "  ({n} files)",
        "ask_keep":       "Keep these user data?",
        "keep_hint":      "    Keep   → only remove program files; your source media",
        "keep_hint2":     "             and separated results will remain",
        "del_hint":       "    Delete → remove everything including user data",
        "del_hint2":      "             (irreversible)",
        "ask_keep_short": "Keep user data?",
        "about_to":       "  About to perform:",
        "del_prog":       "    ✓ Remove: Prism.exe, uninstall.exe, _internal, models",
        "keep_data":      "    ✓ Keep:   input-video\\ and output\\",
        "del_data":       "    ✗ Also:   input-video\\ and output\\ (irreversible)",
        "ask_confirm":    "Confirm uninstall?",
        "launching":      "\n  Launching uninstall script: {path}",
        "closing":        "  This window will close in ~2s; deletion continues in the background.",
        "closing_hint":   "  (If deletion does not take effect, wait 5s and check the folder.)",
        "press_enter":    "\nPress Enter to exit...",
    },
}


def t(key: str, **kw) -> str:
    s = _T[_LANG].get(key) or _T["en"].get(key) or key
    return s.format(**kw) if kw else s


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _pause() -> None:
    try:
        input(t("press_enter"))
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
    t_  = str(target)
    tmp = tempfile.gettempdir()

    L: list[str] = [
        "@echo off",
        f'cd /d "{tmp}"',
        "ping 127.0.0.1 -n 4 >nul",
        "",
        "rem --- program files ---",
        f'if exist "{t_}\\_internal"  rmdir /s /q "{t_}\\_internal"',
        f'if exist "{t_}\\models"     rmdir /s /q "{t_}\\models"',
        f'for %%F in ("{t_}\\*.exe") do del /f /q "%%F"',
        f'if exist "{t_}\\temp_audio" rmdir /s /q "{t_}\\temp_audio"',
        "",
    ]

    if not keep_data:
        L += [
            "rem --- user data ---",
            f'if exist "{t_}\\input-video" rmdir /s /q "{t_}\\input-video"',
            f'if exist "{t_}\\output"      rmdir /s /q "{t_}\\output"',
            "",
            "rem --- top folder ---",
            f'rmdir "{t_}" 2>nul',
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
    print("  " + t("title"))
    print("=" * 60)
    print(t("install_dir", path=target))
    print()

    if not (target / "Prism.exe").exists():
        print(t("no_exe"))
        print(t("no_exe_hint"))
        if not _ask(t("ask_continue"), default=False):
            print(t("cancelled"))
            _pause()
            return 1
        print()

    in_dir  = target / "input-video"
    out_dir = target / "output"
    has_user_data = in_dir.exists() or out_dir.exists()

    keep_data = False
    if has_user_data:
        print(t("user_data"))
        if in_dir.exists():
            print(f"    • input-video\\  " + t("files_n", n=_count_files(in_dir)))
        if out_dir.exists():
            print(f"    • output\\       " + t("files_n", n=_count_files(out_dir)))
        print()
        print(t("ask_keep"))
        print(t("keep_hint"))
        if _LANG == "en":
            print(t("keep_hint2"))
        print(t("del_hint"))
        if _LANG == "en":
            print(t("del_hint2"))
        keep_data = _ask(t("ask_keep_short"), default=True)
        print()

    print(t("about_to"))
    print(t("del_prog"))
    if keep_data:
        print(t("keep_data"))
    else:
        print(t("del_data"))
    print()
    if not _ask(t("ask_confirm"), default=False):
        print(t("cancelled"))
        _pause()
        return 0

    bat = _write_bat(target, keep_data)
    print(t("launching", path=bat))
    print(t("closing"))
    print(t("closing_hint"))

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