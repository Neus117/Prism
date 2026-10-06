<div align="center">
  <table>
    <tr>
      <td align="center" width="33%">
        <img src="assets/design/Prism_logo_concept_1.png" width="250" alt="Concept 1"><br>
        <sub>Concept 1</sub>
      </td>
      <td align="center" width="33%">
        <img src="assets/design/Prism_logo_concept_2.png" width="250" alt="Concept 2"><br>
        <sub>Concept 2</sub>
      </td>
      <td align="center" width="33%">
        <img src="assets/design/Prism_logo.jpg" width="250" alt="Final Logo"><br>
        <sub>Final Version</sub>
      </td>
    </tr>
  </table>
</div>

# Prism

> Refract your mix into stems.

[English](README.md) | [简体中文](README_zh.md)

**Prism** is a batch audio/video source separation tool powered by
[HT-Demucs FT](https://github.com/facebookresearch/demucs) 4-stem ONNX models.
It runs entirely on CPU — no CUDA, no GPU required.

---

## Features

- 🎬 **Batch processing** — drop files into `input-video/` and go
- 🧠 **4-stem separation** — drums / bass / other / vocals
- ⚡ **CPU-optimized** — tuned for modern multi-core CPUs
- 🌐 **Bilingual UI** — auto-detects Chinese / English system language
- 📦 **Portable release** — no Python needed; runs out of the box
- 🧹 **Clean uninstaller** — optionally keeps your input/output data

---

## Quick Start (end users)

1. Download **`Prism-portable_vX.Y.Z.zip`** from
   [**Releases**](https://github.com/Neus117/Prism/releases).
2. Extract the archive anywhere (e.g. `D:\Prism`).
3. Put your audio or video files into the `input-video/` folder.
4. Double-click `Prism.exe`.
5. Separated stems are saved to `output/<filename>/`.

To uninstall, run `uninstall.exe` in the same folder. You will be asked
whether to keep your user data.

> **No Python installation and no additional downloads are required** —
> `Prism-portable` already bundles the ONNX models and FFmpeg inside its
> `_internal/` folder.

### Supported formats

- **Video** — `mp4`, `mov`, `mkv`, `avi`, `flv`, `wmv`, `webm`, `m4v`
- **Audio** — `mp3`, `wav`, `flac`, `m4a`, `aac`, `ogg`, `opus`, `wma`, `aiff`

### Note on same-named files

If an audio and a video share the same stem (e.g. `song.mp4` and
`song.mp3`), they will **share the same output folder** `output/song/`,
and only the four `.wav` files from the last processed one are kept.
Avoid placing files with the same name but different extensions
together in `input-video/`.

---

## Running from Source

### 1. Requirements

- **Python 3.10 or 3.11** (3.11 recommended)
- **FFmpeg** — a Windows build of `ffmpeg.exe` (see step 3)
- **HT-Demucs FT ONNX models** — see step 3
- One of:
  - **Anaconda / Miniconda** (recommended for beginners), or
  - **Python's built-in `venv`** (lightweight, no extra install)

### 2. Clone the repository

```bash
git clone https://github.com/Neus117/Prism.git
cd Prism
```

### 3. Provide the models and FFmpeg

Neither the ONNX models nor `ffmpeg.exe` are committed to this repository
(they total several hundred MB). Before running from source you must place
them at the project root:

```
Prism/
├── ffmpeg.exe
├── models/
│   ├── htdemucs_ft_drums_fp16weights.onnx
│   ├── htdemucs_ft_bass_fp16weights.onnx
│   ├── htdemucs_ft_other_fp16weights.onnx
│   └── htdemucs_ft_vocals_fp16weights.onnx
├── src/
└── ...
```

You have **two ways** to obtain them:

**Option A — extract from the `Prism-portable` release (easiest)**

1. Download `Prism-portable_vX.Y.Z.zip` from the
   [**Releases**](https://github.com/Neus117/Prism/releases) page.
2. Extract it to a temporary location.
3. Copy `_internal/models/` and `_internal/ffmpeg.exe` into the source
   project root as shown above.

**Option B — download from the original sources**

- **ONNX models** — published by **[StemSplit](https://stemsplit.io)**
  at
  [huggingface.co/StemSplitio/htdemucs-ft-onnx](https://huggingface.co/StemSplitio/htdemucs-ft-onnx).
  Download the four `htdemucs_ft_*.onnx` files and place them under
  `models/` with the exact filenames listed above.
- **FFmpeg** — any Windows build from
  [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or
  [BtbN](https://github.com/BtbN/FFmpeg-Builds/releases). Place
  `ffmpeg.exe` at the project root.

### 4. Create an environment **inside the project folder**

We strongly recommend creating the virtual environment *inside* the
project directory. This keeps everything self-contained: to fully clean
up, just delete the project folder.

#### Option A — with conda (recommended)

```bash
# Create the environment at ./prism_env (inside the project folder)
conda create -p ./prism_env python=3.11 -y

# Activate it
conda activate ./prism_env
```

> **Note:** using `-p ./prism_env` places the environment inside the
> project folder. Do **not** use `conda create -n prism` — that would put
> it into your global conda envs directory, defeating the purpose.

#### Option B — with Python's built-in venv

```bash
python -m venv .venv
```

Activate it depending on your shell:

| Shell | Command |
|---|---|
| PowerShell | `.\.venv\Scripts\Activate.ps1` |
| CMD | `.venv\Scripts\activate.bat` |
| Git Bash | `source .venv/Scripts/activate` |

> If PowerShell blocks the activation script, run once:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

> Developers / packagers who want to rebuild the `.exe` should
> additionally install:
> ```bash
> pip install -r requirements_build.txt
> ```

### 6. Run it

```bash
python src/batch_process.py
```

Place your media in `input-video/`. Separated stems will appear under
`output/<filename>/`.

---

## Rebuilding the `.exe` (maintainers)

If you want to rebuild the packaged release yourself:

```bash
pip install -r requirements_build.txt
.\build.bat
```

The output will be at `dist/Prism/`, containing:

```
dist/Prism/
├── Prism.exe
├── uninstall.exe
├── _internal/
│   ├── models/
│   ├── ffmpeg.exe
│   └── ...              # Python runtime, DLLs, etc.
├── input-video/
└── output/
```

Zip the whole `Prism/` folder and attach it to a new GitHub Release as
`Prism-portable_vX.Y.Z.zip`.

---

## Environment Variables

| Variable | Values | Effect |
|---|---|---|
| `PRISM_LANG` | `zh`, `en` | Force the UI language (otherwise auto-detected) |

Example (PowerShell):

```powershell
$env:PRISM_LANG = "en"
.\Prism.exe
```

---

## Project Structure

```
Prism/
├── src/
│   ├── batch_process.py        # Batch pipeline (ffmpeg → separate → save)
│   ├── bag_infer.py            # ONNX inference engine
│   └── paths.py                # Dev / frozen path resolution
├── tools/
│   ├── make_icon.py            # Generates assets/prism.ico
│   └── uninstall/
│       └── uninstall.py        # Green uninstaller (source)
├── assets/
│   └── prism.ico               # Application icon
├── models/                     # ONNX models (not committed)
├── ffmpeg.exe                  # FFmpeg binary (not committed)
├── Prism.spec                  # PyInstaller spec — main app
├── uninstall.spec              # PyInstaller spec — uninstaller
├── version_info.txt            # EXE metadata — main app
├── uninstall_version_info.txt  # EXE metadata — uninstaller
├── requirements.txt            # Runtime dependencies
├── requirements_build.txt      # Build-time dependencies
└── build.bat                   # One-click build script
```

---

## License

This project is licensed under the **MIT License** — see
[LICENSE](LICENSE) for details.

### Third-party notices

- **HT-Demucs FT ONNX models** — © StemSplit
  ([stemsplit.io](https://stemsplit.io)). Refer to the
  [original project](https://huggingface.co/StemSplitio/htdemucs-ft-onnx)
  for the exact terms.
- **HT-Demucs / Demucs** — Copyright (c) Meta Platforms, Inc., MIT License.
- **FFmpeg** — a separate project. Depending on the build it may be
  licensed under LGPL or GPL. If you redistribute `ffmpeg.exe` alongside
  Prism, make sure you comply with the license of the specific build you
  ship. See [ffmpeg.org/legal.html](https://ffmpeg.org/legal.html).
- **ONNX Runtime** — MIT License.
- **soundfile / libsndfile** — BSD 3-Clause.

---

## Acknowledgements

**Special thanks to the model author first:**

- **[StemSplit](https://stemsplit.io)** — author of the HT-Demucs FT **ONNX**
  models used by Prism. Original project:
  [huggingface.co/StemSplitio/htdemucs-ft-onnx](https://huggingface.co/StemSplitio/htdemucs-ft-onnx).

And to the projects that made this possible:

- [Demucs](https://github.com/facebookresearch/demucs) by Meta AI Research
- [ONNX Runtime](https://github.com/microsoft/onnxruntime)
- [soundfile](https://github.com/bastibe/python-soundfile)

---

## Contributing

Issues and pull requests are welcome. For major changes, please open an
issue first to discuss what you would like to change.