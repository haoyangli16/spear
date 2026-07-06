# SPEAR Setup — Progress Log

Mission: fully autonomous SPEAR simulator setup per https://github.com/spear-sim/spear/blob/main/docs/getting_started.md (macOS path).
Workspace: `~/spear-setup/`

## Current status (updated 2026-07-05, night — ✅ MISSION COMPLETE, ALL PHASES PASS)

- **Every phase (0–8) passed its acceptance test.** SPEAR is fully set up: `SpearSim.app` built (2.1 GB), launch-tested on two scenes, Python↔sim RPC connection verified working.
- No open blockers. One upstream repo bug was found and patched locally in `tools/run_executable.py` (experience_cards/04) — worth reporting to https://github.com/spear-sim/spear/issues.
- See FINAL_REPORT.md for the full evidence table and day-to-day usage commands.

## Phase 0 — Preflight audit (2026-07-05) — DONE

| Prerequisite | Status | Detail |
|---|---|---|
| macOS | OK | macOS 26.5.1 (build 25F80) |
| Chip | OK | Apple M5 Pro, arm64, 18 cores (6 Super + 12 Performance) |
| RAM | OK | 48 GB |
| Free disk | OK | 780 GiB free at start (need ≥150 GB); 773 GiB free after setup |
| git | OK | system git 2.50.1; spear-env git 2.55.0 |
| Xcode (full) | **MISSING** | Only Command Line Tools (clang 21.0.0); no Xcode*.app on disk. Human blocker for Phase 7. CLT was sufficient for Phases 4–5. |
| Unreal Engine 5.5 | **MISSING** | `/Users/Shared/Epic Games/` absent; no UnrealEditor anywhere. Human blocker for Phases 3b, 6, 7, 8. |
| Homebrew | MISSING | Needs sudo to install; **not needed** for any completed phase. |
| Miniconda | OK (installed) | Miniconda3 arm64 → `~/miniconda3`, conda 26.3.2 |
| sudo | UNAVAILABLE | Session policy denies sudo. |

## Phase log (all timestamps 2026-07-05, local)

- Phase 0 audit complete. Workspace `~/spear-setup/{logs,experience_cards}` created.
- Phase 1: Miniconda installed silently (logs/phase1_miniconda_install.log).
  - FAILURE+FIX: `conda create` → CondaToSNonInteractiveError; fixed via `conda tos accept` × 2 channels (experience_cards/01). 
  - DONE. Acceptance PASSED: Python 3.11.15, cmake 4.3.4, git 2.55.0 inside spear-env (logs/phase1_conda_env.log).
- Phase 2: clone with submodules.
  - FAILURE: attempt 1 died mid-transfer (`early EOF`); git auto-removed partial dir. Note: `| tee` masked git's exit code (experience_cards/02).
  - DONE on attempt 2 (logs/phase2_clone_attempt2.log). Acceptance PASSED: 174 submodules, 0 uninitialized.
  - Read docs/getting_started.md from clone; plan matches; noted Xcode-26 extra step for resume path.
- Phase 3a: `pip install -e python` → spear-sim 1.0.0 (logs/phase3a_pip_install_spear.log).
  - DONE. Acceptance PASSED: `import spear` → `~/spear-setup/spear/python/spear/__init__.py`.
- Phase 3b: **BLOCKED** (no UE). Not attempted — tool requires `--unreal-engine-dir`.
- Phase 4: `python tools/build_third_party_libs.py` (logs/phase4_third_party_libs.log).
  - DONE, exit 0. Built with Apple clang 21 from Command Line Tools (full Xcode not required for this step).
  - Acceptance PASSED: boost → `third_party/boost/stage/lib/libboost_*.a`; rpclib → `third_party/rpclib/BUILD/Mac/librpc.a`; yaml-cpp → `third_party/yaml-cpp/BUILD/Mac/libyaml-cpp.a`.
- Phase 5: `python tools/install_python_extension.py` (logs/phase5_install_python_extension.log).
  - DONE, exit 0. Acceptance PASSED: `import spear_ext` OK; native API (Client, DataBundle, PackedArray, …) present.
  - Extra smoke test: all spear submodules (`spear.instance`, `spear.services`, `spear.unreal_object`, `spear.utils`) import with zero failures.
- Phase 6, 7, 8: **BLOCKED** (need UE; 7 also needs Xcode). See BLOCKERS.md + FINAL_REPORT.md resume section.
- FINAL_REPORT.md written.
- (evening) Harry installed UE 5.5 → confirmed at `/Users/Shared/Epic Games/UE_5.5`. Blocker #2 RESOLVED.
- (evening) UE first launch: "requires Xcode to compile shaders for Metal" dialog → new experience_cards/03; gave Harry exact Xcode install + xcode-select/license steps. Xcode download in progress. Blocker #1 remains OPEN until `xcodebuild -version` succeeds.
- (evening) Docs pass: README.md added to workspace; PROGRESS/BLOCKERS/FINAL_REPORT updated to current state.
- (late evening) Harry installed Xcode 26.6 (build 17F113) + opened UE editor successfully. Verified: `xcodebuild -version` OK, `xcode-select -p` → /Applications/Xcode.app, Metal compiler present.
- (late evening) Phase 3b DONE, exit 0 (logs/phase3b_editor_env.log). Acceptance PASSED: UE editor Python (`Engine/Binaries/ThirdParty/Python3/Mac/bin/python3`) imports spear from the editable install.
- (late evening) Xcode-26 patch: `install_updated_apple_sdk_json_in_engine/run.py` exit 0; original backed up to `Engine/Config/Apple/Apple_SDK.json.bak` (logs/phase3b_apple_sdk_json.log).
- (late evening) Phase 6 DONE, exit 0 (logs/phase6_copy_engine_content.log). Acceptance PASSED: 7 content packs copied into `cpp/unreal_projects/SpearSim/Content/` (StarterContent, ThirdPerson, Vehicles, Mannequins, …).
- (late evening) Phase 7 STARTED: full UAT build running in background (logs/phase7_uat.log).
- (night) Phase 7 DONE: `BUILD SUCCESSFUL`, AutomationTool exit 0, BuildCookRun 326.6 s (M5 Pro — far faster than the 1–3 h estimate). Acceptance PASSED: `cpp/unreal_projects/SpearSim/Standalone-Development/Mac/SpearSim.app` exists (2.1 GB), 9 maps cooked (apartment_0000, debug_0000/0001, 6 UE debug scenes).
- (night) Phase 8 FAILURE: `run_executable.py` crashed instantly — `AttributeError: INITIALIZE_GAME_WORLD_SERVICE` (upstream schema-drift bug; the key was renamed to WORLD_REGISTRY_SERVICE everywhere except this script). Patched lines 58–60 of tools/run_executable.py (experience_cards/04).
- (night) Phase 8 DONE after fix. Acceptance PASSED twice: debug_0000 launched (PID 18412), alive 90 s, SIGTERM'd cleanly, zero crash reports in ~/Library/Logs/DiagnosticReports; bonus apartment_0000 launched (PID 18518), alive 60 s, terminated cleanly. Launch logs additionally show spear.Instance connected its spear_ext RPC Client to the sim and shut down gracefully — the full Python↔simulator loop works.
- (night) MISSION COMPLETE. FINAL_REPORT.md updated to final state.
