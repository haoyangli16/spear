# SPEAR Setup — Final Report ✅ (completed 2026-07-05)

**Result: the SPEAR simulator is fully installed, built, and launch-tested on this machine. All 9 phases PASS. No open blockers.**

Machine: MacBook Pro, Apple M5 Pro (18 cores), 48 GB RAM, macOS 26.5.1, arm64.
Toolchain: Xcode 26.6 (17F113), Unreal Engine 5.5 at `/Users/Shared/Epic Games/UE_5.5` (path has a space — always quote it), Miniconda (conda 26.3.2) with env `spear-env` (Python 3.11.15).

## Phase-by-phase status

| Phase | Status | Acceptance evidence |
|---|---|---|
| 0 — Preflight audit | **PASS** | Full table in PROGRESS.md. Initially missing: Xcode, UE 5.5 (both installed by Harry same day), Homebrew (never needed). |
| 1 — Conda env + tooling | **PASS** | In spear-env: Python 3.11.15, cmake 4.3.4, git 2.55.0. |
| 2 — Clone + submodules | **PASS** | 174 submodules, 0 uninitialized. |
| 3a — spear package (conda env) | **PASS** | `import spear` → editable install. |
| 3b — spear package (UE editor env) | **PASS** | Exit 0; UE's bundled python3 imports spear. Xcode-26 `Apple_SDK.json` patch applied (backup: `Engine/Config/Apple/Apple_SDK.json.bak`). |
| 4 — Third-party C++ libs | **PASS** | boost/rpclib/yaml-cpp static libs built (CLT clang 21 sufficed). |
| 5 — spear_ext extension | **PASS** | `import spear_ext` OK; native RPC API present. |
| 6 — Copy engine content | **PASS** | 7 content packs copied into `cpp/unreal_projects/SpearSim/Content/`. |
| 7 — SpearSim standalone build | **PASS** | `BUILD SUCCESSFUL`, exit 0, BuildCookRun 326.6 s. `Standalone-Development/Mac/SpearSim.app` = 2.1 GB, 9 maps cooked. Log: `logs/phase7_uat.log`. |
| 8 — Launch test | **PASS** (after 1 fix) | debug_0000: launched, alive 90 s, clean SIGTERM, no crash reports. apartment_0000: alive 60 s, clean. Logs show spear.Instance ↔ sim RPC client connect/disconnect working. |

## The one bug found (patched locally — consider filing upstream)

`tools/run_executable.py` crashed with `AttributeError: INITIALIZE_GAME_WORLD_SERVICE` — the script references a config service that was renamed to `WORLD_REGISTRY_SERVICE` everywhere else in the repo (yacs schema + C++ consumer). Patched lines 58–60 to use the new key (and its `OVERRIDE` spelling). Details + workaround: `experience_cards/04_run_executable_stale_config_key.md`. This is an upstream `main`-branch bug worth reporting to https://github.com/spear-sim/spear/issues. Note: the local patch will show as a modified file in `git status`; keep it until upstream fixes the script.

## How to use SPEAR from here

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate spear-env
cd ~/spear-setup/spear

# interactive: double-click SpearSim.app, or:
python tools/run_executable.py --map /Game/SPEAR/Scenes/apartment_0000/Maps/apartment_0000

# other packaged maps: debug_0000, debug_0001, StarterMap, ThirdPersonMap, VehicleExampleMap, ...
# in-app: press ~ and `Open MapName`

# rebuild after C++ changes (see docs/getting_started.md "Helpful RunUAT options"):
python tools/run_uat.py --unreal-engine-dir "/Users/Shared/Epic Games/UE_5.5" -build -cook -stage -package -archive -pak

# next tutorial: docs/running_our_example_applications.md (programmatic Python control)
```

## Replicating this setup on another Mac

Read `experience_cards/00_fluent_setup_playbook.md` — the distilled golden path with install ordering, real per-step durations, verification commands, and all traps pre-empted.

## Problems hit and solved (details in experience_cards/)

1. **01** — conda 26.x refuses `conda create` until `conda tos accept` (non-interactive shells hard-fail).
2. **02** — 174-submodule clone died once with `early EOF`; plain retry fixed it; `| tee` masks git's exit code without `pipefail`.
3. **03** — UE first launch requires full Xcode for the Metal shader compiler; CLT is not enough (discovered pre-emptively in the audit; hit for real at first editor launch).
4. **04** — `run_executable.py` stale config key (see above).

## Where things are

- Repo: `~/spear-setup/spear` (main branch; one local patch in tools/run_executable.py)
- Executable: `~/spear-setup/spear/cpp/unreal_projects/SpearSim/Standalone-Development/Mac/SpearSim.app`
- Env: `conda activate spear-env` · Logs: `~/spear-setup/logs/` · Overview: `~/spear-setup/README.md`
