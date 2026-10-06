# -*- mode: python ; coding: utf-8 -*-
"""
Prism —— HT-Demucs FT 4-stem ONNX 打包配置
------------------------------------------------
把混音折射成音轨。
"""
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH)


# =========================================================
# 1) 自动收集第三方库
# =========================================================
ort_datas, ort_binaries, ort_hidden = collect_all("onnxruntime")
sf_datas,  sf_binaries,  sf_hidden  = collect_all("soundfile")

datas         = list(ort_datas) + list(sf_datas)
binaries      = list(ort_binaries) + list(sf_binaries)
hiddenimports = list(ort_hidden) + list(sf_hidden) + [
    "onnxruntime.capi._pybind_state",
    "ctypes",
    "ctypes.wintypes",
    "_ctypes",
]


# =========================================================
# 2) 项目自带资源
# =========================================================
datas += [
    (str(ROOT / "models"),     "models"),
    (str(ROOT / "ffmpeg.exe"), "."),
]


# =========================================================
# 3) 收集关键系统 DLL（免装 VC++ Redistributable）
# =========================================================
def collect_critical_dlls() -> list[tuple[str, str]]:
    candidates: list[Path] = []
    for prefix in {sys.base_prefix, sys.prefix}:
        if not prefix:
            continue
        candidates.append(Path(prefix) / "DLLs")
        candidates.append(Path(prefix) / "Library" / "bin")
        candidates.append(Path(prefix))

    for sp in Path(sys.prefix).glob("Lib/site-packages"):
        candidates.append(sp / "onnxruntime" / "capi")

    sysroot = os.environ.get("SystemRoot", r"C:\Windows")
    candidates.append(Path(sysroot) / "System32")

    wanted = [
        "libffi-*.dll",
        "ffi-*.dll",             # conda 命名
        "ffi.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "msvcp140.dll",
        "msvcp140_1.dll",
        "concrt140.dll",
    ]

    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for cand in candidates:
        if not cand.exists():
            continue
        for pat in wanted:
            for f in cand.glob(pat):
                if f.name in seen:
                    continue
                seen.add(f.name)
                found.append((str(f), "."))
                print(f"[spec] + DLL  {f}")
    return found


binaries += collect_critical_dlls()


# =========================================================
# 3b) 项目根目录里手动准备的 DLL 兜底
# =========================================================
for dll in ["ffi-8.dll", "ffi-7.dll", "ffi.dll",
            "vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"]:
    p = ROOT / dll
    if p.exists():
        binaries.append((str(p), "."))
        print(f"[spec] + 手动 DLL  {p}")


# =========================================================
# 4) 图标（存在才用，避免构建报错）
# =========================================================
_icon_path = ROOT / "assets" / "prism.ico"
ICON = str(_icon_path) if _icon_path.exists() else None
if ICON:
    print(f"[spec] + 图标  {ICON}")
else:
    print("[spec] - 未找到 assets\\prism.ico，将使用默认图标")


# =========================================================
# 5) Analysis / PYZ / EXE / COLLECT
# =========================================================
a = Analysis(
    [str(ROOT / "src" / "batch_process.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "tkinter", "PIL", "IPython",
        "pandas", "scipy", "pytest",
        "PyQt5", "PyQt6", "PySide2", "PySide6",
        "jupyter", "notebook",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Prism",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=str(ROOT / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Prism",
)