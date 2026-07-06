# Unreal Editor first launch fails: "requires Xcode to compile shaders for Metal"

- Date / Phase: 2026-07-05 / between Phase 2 and Phase 3b (first launch of freshly installed UE 5.5 on macOS)
- Symptom: opening the Unreal Editor shows a dialog:
  > "Unreal Engine requires Xcode to compile shaders for Metal. To continue, install Xcode and open it to accept the license agreement. If you install Xcode to any location other than Applications/Xcode, also run the xcode-select command-line tool to specify its location."
- Root cause: macOS Command Line Tools (CLT) alone are NOT enough for the Unreal Engine. The Metal shader compiler ships only inside the full Xcode.app. A machine can build all of SPEAR's third-party C++ libraries and the spear_ext extension with just CLT (clang is included), which makes it easy to believe the toolchain is complete — but UE itself needs full Xcode.
- Fix (exact steps):
  1. Install Xcode from the Mac App Store (~15 GB; on macOS 26 this is Xcode 26.x, which SPEAR supports with one extra step, see below).
  2. Open Xcode once; accept the license; when choosing components select **macOS** platform support and **Metal Toolchain** (Other Components).
  3. In a terminal:
     ```
     sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
     sudo xcodebuild -license accept
     xcodebuild -runFirstLaunch
     xcodebuild -downloadComponent MetalToolchain   # only if Metal Toolchain wasn't selected in the GUI
     ```
  4. Verify with `xcodebuild -version`.
  5. **Xcode 26 only:** UE 5.5 doesn't officially support Xcode 26; SPEAR provides a patch tool that must be run once after UE is installed:
     ```
     conda activate spear-env
     cd ~/spear-setup/spear
     python tools/install_updated_apple_sdk_json_in_engine/run.py --unreal-engine-dir "/Users/Shared/Epic Games/UE_5.5"
     ```
- Time lost: none in this run (predicted in the preflight audit before UE was installed), but on a fresh machine this is typically discovered only at UE first launch — after a 50 GB engine download.
- How others can avoid this: install full Xcode BEFORE (or in parallel with) the Unreal Engine download. Don't assume CLT is sufficient just because `clang`/`cmake` builds succeed — check `xcodebuild -version` early; if it errors with "requires Xcode", the editor and any `run_uat.py` build will fail later.
