"""
Bag inference for the full HT-Demucs FT 4-stem ONNX ensemble.
纯 CPU 极致优化版，专为 i7-12800HX 调优。
"""
from __future__ import annotations

import argparse
import sys
import time
import os
import gc
import locale
from pathlib import Path

import numpy as np
import onnxruntime as ort
import soundfile as sf

# [打包改动] 从 paths 模块取得资源目录，兼容开发 / PyInstaller 冻结环境
from paths import resource_dir

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

SAMPLE_RATE = 44100
SEGMENT_S = 7.8
N_SAMPLES = int(SEGMENT_S * SAMPLE_RATE)
N_CHANNELS = 2
SOURCES = ["drums", "bass", "other", "vocals"]

# [打包改动] 原来 HERE 指向脚本目录；现在指向资源根目录
#   - 开发时：  <项目根>
#   - 打包后：  <exe>\ 同级 _internal\
HERE = resource_dir()

DEFAULT_ONNX_FILES = {
    "drums":  HERE / "models" / "htdemucs_ft_drums_fp16weights.onnx",
    "bass":   HERE / "models" / "htdemucs_ft_bass_fp16weights.onnx",
    "other":  HERE / "models" / "htdemucs_ft_other_fp16weights.onnx",
    "vocals": HERE / "models" / "htdemucs_ft_vocals_fp16weights.onnx",
}

# i7-12800HX: 16 物理核 (8P+8E), 24 线程
INTRA_OP_THREADS = 12
INTER_OP_THREADS = 1


# =========================================================
# 轻量 i18n：检测系统语言，零依赖，可按需扩展
#   环境变量 PRISM_LANG=zh 或 en 可强制覆盖
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
        "input":          "  输入:    {n:,} 采样点 ({sec:.1f}s)",
        "chunks":         "  分块:    {n}",
        "mode":           "  模式:    顺序单模型 (CPU 优化, 线程={threads})",
        "load_model":     "\n  ── [{stem}] 加载模型 (provider=CPUExecutionProvider)...",
        "loaded":         "  ✓ [{stem}] 加载完成，开始推理...",
        "chunk_progress": "    [{stem}] 分块 {i}/{n}: {t:.1f}s",
        "done_stem":      "  ✓ [{stem}] 完成，已释放 session",
        "total":          "\n  总计:    {sec:.2f}s (RTF {rtf:.2f})",
        "provider":       "  提供者:  CPU",
        "loading_file":   "正在加载 {path} ...",
        "wrote":          "  已写出 {path}",
    },
    "en": {
        "input":          "  Input:   {n:,} samples ({sec:.1f}s)",
        "chunks":         "  Chunks:  {n}",
        "mode":           "  Mode:    Sequential single-model (CPU optimized, threads={threads})",
        "load_model":     "\n  ── [{stem}] Loading model (provider=CPUExecutionProvider)...",
        "loaded":         "  ✓ [{stem}] Loaded, starting inference...",
        "chunk_progress": "    [{stem}] chunk {i}/{n}: {t:.1f}s",
        "done_stem":      "  ✓ [{stem}] Done, session released",
        "total":          "\n  Total:   {sec:.2f}s (RTF {rtf:.2f})",
        "provider":       "  Provider: CPU",
        "loading_file":   "Loading {path} ...",
        "wrote":          "  wrote {path}",
    },
}


def t(key: str, **kw) -> str:
    s = _T[_LANG].get(key) or _T["en"].get(key) or key
    return s.format(**kw) if kw else s


def _make_transition_window(segment: int, overlap_frac: float = 0.25) -> np.ndarray:
    transition = int(segment * overlap_frac)
    window = np.ones(segment, dtype=np.float32)
    fade = np.linspace(0, 1, transition, dtype=np.float32)
    window[:transition] = fade
    window[-transition:] = fade[::-1]
    return window


def _load_single_session(onnx_path: Path) -> ort.InferenceSession:
    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = INTRA_OP_THREADS
    sess_options.inter_op_num_threads = INTER_OP_THREADS
    sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_options.enable_mem_pattern = True

    return ort.InferenceSession(
        str(onnx_path),
        sess_options=sess_options,
        providers=["CPUExecutionProvider"],
    )


def separate(mix: np.ndarray, sample_rate: int,
             onnx_files: dict[str, Path] | None = None,
             verbose: bool = True) -> dict[str, np.ndarray]:
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"Bound to {SAMPLE_RATE} Hz; got {sample_rate}.")
    if mix.ndim != 2 or mix.shape[0] != N_CHANNELS:
        raise ValueError(f"Expected (2, samples) input, got {mix.shape}")

    files = onnx_files or DEFAULT_ONNX_FILES

    for stem, path in files.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing {stem} model at {path}.")

    total_len = mix.shape[1]
    overlap = N_SAMPLES // 4
    stride = N_SAMPLES - overlap
    n_chunks = max(1, (total_len + stride - 1) // stride)

    if verbose:
        print(t("input", n=total_len, sec=total_len / sample_rate))
        print(t("chunks", n=n_chunks))
        print(t("mode", threads=INTRA_OP_THREADS))

    window = _make_transition_window(N_SAMPLES)
    out = {stem: np.zeros((N_CHANNELS, total_len), dtype=np.float32) for stem in SOURCES}

    t0 = time.perf_counter()

    for stem in SOURCES:
        target_row = SOURCES.index(stem)
        if verbose:
            print(t("load_model", stem=stem))

        session = _load_single_session(files[stem])

        if verbose:
            print(t("loaded", stem=stem))

        stem_t0 = time.perf_counter()
        for i in range(n_chunks):
            start = i * stride
            end = min(start + N_SAMPLES, total_len)
            chunk = mix[:, start:end]
            if chunk.shape[1] < N_SAMPLES:
                chunk = np.pad(chunk,
                               ((0, 0), (0, N_SAMPLES - chunk.shape[1])),
                               mode="constant")
            x = chunk[np.newaxis, ...].astype(np.float32)
            chunk_len = end - start
            w = window[:chunk_len]

            stems_out = session.run(["stems"], {"mix": x})[0][0]
            out[stem][:, start:end] += stems_out[target_row, :, :chunk_len] * w

            if verbose:
                print(t("chunk_progress",
                        stem=stem, i=i + 1, n=n_chunks,
                        t=time.perf_counter() - stem_t0))

        del session
        gc.collect()
        if verbose:
            print(t("done_stem", stem=stem))

    weight = np.zeros(total_len, dtype=np.float32)
    for i in range(n_chunks):
        start = i * stride
        end = min(start + N_SAMPLES, total_len)
        w = window[:end - start]
        weight[start:end] += w
    weight = np.maximum(weight, 1e-8)

    for stem in SOURCES:
        out[stem] /= weight

    if verbose:
        elapsed = time.perf_counter() - t0
        rtf = elapsed / (total_len / sample_rate)
        print(t("total", sec=elapsed, rtf=rtf))
        print(t("provider"))

    return out


def separate_all(input_path: str, **kwargs) -> dict[str, np.ndarray]:
    audio, sr = sf.read(input_path, dtype="float32", always_2d=True)
    audio = audio.T
    if audio.shape[0] == 1:
        audio = np.tile(audio, (2, 1))
    elif audio.shape[0] > 2:
        audio = audio[:2]
    return separate(audio, sr, **kwargs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(t("loading_file", path=args.input))
    audio, sr = sf.read(str(args.input), dtype="float32", always_2d=True)
    audio = audio.T
    if audio.shape[0] == 1:
        audio = np.tile(audio, (2, 1))
    elif audio.shape[0] > 2:
        audio = audio[:2]

    stems = separate(audio, sr)

    for stem, audio_out in stems.items():
        out_path = args.out_dir / f"{stem}.wav"
        sf.write(str(out_path), audio_out.T, sr)
        print(t("wrote", path=out_path))


if __name__ == "__main__":
    main()