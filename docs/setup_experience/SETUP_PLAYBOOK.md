# The fluent SPEAR-on-macOS setup playbook (read this first)

Distilled from a complete real setup on 2026-07-05 (MacBook Pro M5 Pro, 48 GB RAM, macOS 26.5.1, Xcode 26.6, UE 5.5). Following this order avoids every mistake we hit. Companion to the official tutorial — follow that for the commands, this for the traps: https://github.com/spear-sim/spear/blob/main/docs/getting_started.md

## Rule #1: start the two giant, human-gated downloads FIRST

The long poles are **Xcode (~15 GB)** and **Unreal Engine 5.5 (~50 GB)**, and both need GUI logins no script can do. Kick both off before anything else; everything below runs in parallel while they download.

1. **Xcode** — App Store → "Xcode" → install. Open it once: accept license, select *macOS* platform support and **Metal Toolchain** (Other Components). Then:
   ```bash
   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
   sudo xcodebuild -license accept
   xcodebuild -runFirstLaunch
   xcodebuild -version        # must print Xcode 16.x or 26.x
   ```
   ⚠️ Command Line Tools are NOT enough — clang/cmake will happily build all the C++ deps, then the Unreal Editor refuses to start ("requires Xcode to compile shaders for Metal"). Card 03.
2. **Unreal Engine 5.5** — Epic Games Launcher → sign in → Unreal Engine → Library → install 5.5 to the default `/Users/Shared/Epic Games/UE_5.5`; tick *Editor symbols for debugging*.
   ⚠️ That path contains a space. **Quote it in every command**, ideally `UE_DIR="/Users/Shared/Epic Games/UE_5.5"` once.

## Rule #2: two one-time tweaks nobody tells you about

- **Fresh conda (≥25.7) blocks `conda create` in scripts** with `CondaToSNonInteractiveError`. Immediately after installing Miniconda run (card 01):
  ```bash
  conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
  conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
  ```
- **Xcode 26 users**: UE 5.5 doesn't officially support it; after UE is installed run SPEAR's patch once (it backs up the original):
  ```bash
  python tools/install_updated_apple_sdk_json_in_engine/run.py --unreal-engine-dir "$UE_DIR"
  ```

## The golden path (with real durations on an M5 Pro)

| # | Step | Command (in `spear-env` unless noted) | Took | Verify with |
|---|---|---|---|---|
| 1 | Miniconda (if needed) | arm64 installer, `bash Miniconda3-*.sh -b -p ~/miniconda3` | ~2 min | `conda --version` |
| 2 | ToS accept | see Rule #2 | seconds | no error on next step |
| 3 | Env + tooling | `conda create -y -n spear-env python=3.11 && conda activate spear-env && conda install -y -c conda-forge git && pip install cmake` | ~4 min | `python --version` → 3.11.x |
| 4 | Clone | `git clone https://github.com/spear-sim/spear ~/spear-setup/spear --recurse-submodules` | ~20 min | `git submodule status --recursive \| grep -c '^-'` → **0** |
| 5 | spear pkg | `cd ~/spear-setup/spear && pip install -e python` | ~2 min | `python -c "import spear"` |
| 6 | Editor-env pkg (needs UE) | `python tools/install_python_package_in_editor_env.py --unreal-engine-dir "$UE_DIR"` | ~1 min | UE's `Engine/Binaries/ThirdParty/Python3/Mac/bin/python3 -c "import spear"` |
| 7 | Third-party libs | `python tools/build_third_party_libs.py` | ~8 min | `libboost_*.a`, `librpc.a`, `libyaml-cpp.a` exist |
| 8 | spear_ext | `python tools/install_python_extension.py` | ~3 min | `python -c "import spear_ext"` |
| 9 | Engine content (needs UE) | `python tools/copy_engine_content.py --unreal-engine-dir "$UE_DIR"` | ~1 min | 7 packs in `cpp/unreal_projects/SpearSim/Content/` |
| 10 | Standalone build (needs UE+Xcode) | `python tools/run_uat.py --unreal-engine-dir "$UE_DIR" -build -cook -stage -package -archive -pak` | **~6 min** (budget 1–3 h on older Macs) | `Standalone-Development/Mac/SpearSim.app` exists |
| 11 | Launch test | `python tools/run_executable.py --map /Game/SPEAR/Scenes/debug_0000/Maps/debug_0000` | ~2 min | process stays alive; no crash report |

## Known traps, in the order you'd hit them

1. **Clone dies with `early EOF`** mid-transfer (174 submodules, >1.5 GB pack): just re-run the identical command; use `git submodule update --init --recursive --jobs 4` as the resumable fallback. If scripting, `set -o pipefail` — `git ... | tee log` otherwise reports tee's exit code and hides the failure. (Card 02)
2. **First run of freshly installed binaries can stall ~2 min** (Gatekeeper scanning). Don't diagnose; run it again.
3. **UE editor won't start without full Xcode** — see Rule #1. (Card 03)
4. **`run_executable.py` crashes with `AttributeError: INITIALIZE_GAME_WORLD_SERVICE`** (repo state as of 2026-07-05): stale config key in the tool script; the service is `WORLD_REGISTRY_SERVICE` now. Two-line fix at lines 58–60, or workaround `--skip-override-game-paused`. Check whether upstream fixed it before patching. (Card 04)
5. **General yacs `AttributeError: SOME_KEY` in any tools/ script** = schema drift, not your setup. Grep the repo for the key; align the script with `python/spear/config/default_config.*.yaml` and the C++ `Config::get` call sites.

## Sanity envelope

- Disk: repo+builds ≈ 8 GB, Miniconda ≈ 2 GB, UE ≈ 50 GB, Xcode ≈ 15 GB → have ~150 GB free.
- No Homebrew required anywhere on this path.
- No sudo required except the two `xcodebuild`/`xcode-select` one-timers.
- Everything else is fully scriptable/non-interactive — an agent (or CI) can do steps 1–5, 7–8 with zero human input, and 6, 9–11 once UE+Xcode exist.
