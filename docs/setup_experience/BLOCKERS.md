# Blockers requiring a human

Status 2026-07-05 night: **ALL BLOCKERS RESOLVED — nothing left for a human.** #2 (UE 5.5) installed and verified; #1 (Xcode 26.6) installed, selected, licensed; Metal compiler verified; #3 (Homebrew) never needed. Setup completed end-to-end — see FINAL_REPORT.md. The rest of this file is kept for the record.

## 1. Full Xcode is not installed (blocks Phase 7 build) — ✔ RESOLVED 2026-07-05 (Xcode 26.6)

- **Symptom:** `xcodebuild -version` → "requires Xcode, but active developer directory '/Library/Developer/CommandLineTools' is a command line tools instance". No `Xcode*.app` exists anywhere on disk (checked `/Applications` and `mdfind`).
- **What you must do:**
  1. Install Xcode 16.x — either from the App Store, or download `Xcode_16.x.xip` from https://developer.apple.com/download/all/ and expand it into `/Applications/Xcode.app`.
  2. Point the system at it and accept the license (needs sudo):
     ```
     sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
     sudo xcodebuild -license accept
     xcodebuild -runFirstLaunch
     xcodebuild -downloadComponent MetalToolchain   # only if Metal Toolchain wasn't selected in the Xcode GUI
     ```
  3. Verify: `xcodebuild -version` prints `Xcode 16.x` (or 26.x).
  4. **If you install Xcode 26 instead of 16** (likely, since this machine runs macOS 26): the tutorial supports it, but you must additionally run (after UE 5.5 is installed):
     ```
     conda activate spear-env
     cd ~/spear-setup/spear
     python tools/install_updated_apple_sdk_json_in_engine/run.py --unreal-engine-dir "/Users/Shared/Epic Games/UE_5.5"
     ```
  5. When installing Xcode, per the tutorial: select **macOS** under *Platform Support* and **Metal Toolchain** under *Other Components*.
- Note: this session cannot use sudo, so even if Xcode.app appeared, the `xcode-select`/license steps would still need you. (`DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` can substitute for `xcode-select` per-command, but license acceptance still needs sudo once.)

## 2. Unreal Engine 5.5 is not installed (blocks Phases 3b, 6, 7, 8) — ✔ RESOLVED 2026-07-05

- **Symptom:** `/Users/Shared/Epic Games/` does not exist; no UnrealEditor binary found on disk.
- **What you must do:**
  1. Install the Epic Games Launcher (https://store.epicgames.com/en-US/download), sign in with an Epic account (GUI login — cannot be automated).
  2. In the launcher: Unreal Engine tab → Library → “+” → install **Unreal Engine 5.5** (default location `/Users/Shared/Epic Games/UE_5.5`). ~50 GB download.
  3. Verify: `ls "/Users/Shared/Epic Games/UE_5.5/Engine"` shows engine folders.
- After both blockers are cleared, resume with the commands in FINAL_REPORT.md (Phases 3b → 6 → 7 → 8).

## 3. (Minor) Homebrew not installed; sudo unavailable in this session

- Homebrew's installer requires sudo to create `/opt/homebrew`. This session's policy denies sudo.
- So far Homebrew is **not needed** for Phases 1–5 (conda + pip cover the toolchain). If a later step demands a brew-only package, it will be added here with the exact `brew install` command for you to run.
