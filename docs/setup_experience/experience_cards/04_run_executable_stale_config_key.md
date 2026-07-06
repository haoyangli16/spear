# tools/run_executable.py crashes: AttributeError INITIALIZE_GAME_WORLD_SERVICE

- Date / Phase: 2026-07-05 / Phase 8 (end-to-end launch test)
- Symptom: `python tools/run_executable.py --map /Game/SPEAR/Scenes/debug_0000/Maps/debug_0000` exits immediately with
  ```
  File ".../tools/run_executable.py", line 59, in <module>
    config.SP_SERVICES.INITIALIZE_GAME_WORLD_SERVICE.OVERIDE_GAME_PAUSED = True
  AttributeError: INITIALIZE_GAME_WORLD_SERVICE
  ```
  The SpearSim process never launches.
- Root cause: main-branch drift in the spear repo. The tool script still writes to `SP_SERVICES.INITIALIZE_GAME_WORLD_SERVICE.{OVERIDE_GAME_PAUSED, GAME_PAUSED}` (note the `OVERIDE` typo), but that service was renamed: the yacs schema (`python/spear/config/default_config.sp_services.yaml`) and the C++ consumer (`cpp/unreal_plugins/SpServices/Source/SpServices/WorldRegistryService.h:178`) both use `SP_SERVICES.WORLD_REGISTRY_SERVICE.{OVERRIDE_GAME_PAUSED, GAME_PAUSED}`. `INITIALIZE_GAME_WORLD_SERVICE` appears nowhere else in the repo. yacs raises AttributeError on unknown keys, so the script dies before launching anything.
- Fix (exact edit in `tools/run_executable.py`, lines 58–60):
  ```python
  if not args.skip_override_game_paused:
      config.SP_SERVICES.WORLD_REGISTRY_SERVICE.OVERRIDE_GAME_PAUSED = True
      config.SP_SERVICES.WORLD_REGISTRY_SERVICE.GAME_PAUSED = False
  ```
  Workaround without editing code: pass `--skip-override-game-paused` (the game world then starts paused, per the config defaults, but the executable launches).
- Time lost: ~10 minutes.
- How others can avoid this: if a `tools/*.py` script throws `AttributeError: <SOME_KEY>` from yacs, it's a schema-drift bug, not your setup. Grep the repo for the key: if it only appears in the failing script, find the renamed section in `python/spear/config/default_config.*.yaml` (confirm against the C++ `Config::get` call sites) and update the script. Consider filing/checking an upstream issue at https://github.com/spear-sim/spear/issues.
