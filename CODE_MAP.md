# SPEAR code map

A guided map of this repository for new contributors. (Fork-maintained; based on a full code survey on
2026-07-05. See [`docs/setup_experience/`](docs/setup_experience/) for setup instructions and
[`docs/setup_experience/EXPLORATION_GUIDE.md`](docs/setup_experience/EXPLORATION_GUIDE.md) for a
capability-oriented tour.)

## The big picture — how a Python script controls Unreal

```
your script                      python/spear (pip pkg)             inside the Unreal process
┌────────────────┐   calls   ┌──────────────────────────┐  msgpack-rpc  ┌─────────────────────────────┐
│ examples/*.py  │ ────────► │ spear.Instance            │ ────────────► │ SpServices plugin           │
│                │           │  ├ unreal_service         │  port 30000   │  ├ RpcService (rpclib srv)  │
│                │           │  ├ rendering_service      │  + shared     │  ├ EngineService (frames)   │
│                │           │  ├ navigation_service ... │    memory     │  ├ UnrealService (reflection)│
│                │           │  └ spear_ext (C++ client) │               │  └ ... more services        │
└────────────────┘           └──────────────────────────┘               └─────────────────────────────┘
```

- **Frame model:** work is scheduled into engine frames. `with instance.begin_frame():` executes at the
  start of one frame (actions), `with instance.end_frame():` at the end of the same frame (observations),
  `instance.step(num_frames=N)` advances time. Deterministic by default (fixed 1/30 s delta time).
- **Reflection everywhere:** any `UFUNCTION`/`UPROPERTY` in the engine is callable/settable from Python —
  `actor.K2_SetActorLocationAndRotation(...)`, `actor.get_properties()`, etc. There is no hand-written
  binding per feature; `UnrealService` resolves names at runtime.
- **Config system:** a single yacs tree (defaults in `python/spear/config/*.yaml`) is passed to the app at
  launch; C++ reads it via `Config::get<T>("SP_SERVICES....")` (SpCore). Python tools override keys before
  launch — e.g. `SP_SERVICES.INITIALIZE_ENGINE_SERVICE.GAME_DEFAULT_MAP`.

## Directory guide

### Python side

| Path | What it is |
|---|---|
| `python/spear/` | The `spear` pip package (client API). `instance.py` = process lifecycle + frame loop; `unreal_object.py` = Python proxies for UE objects (method calls → RPC); `config/` = yacs default config trees (`default_config.spear.yaml`, `.sp_services.yaml`, `.sp_core.yaml`). |
| `python/spear/services/` | One client class per in-engine service. Key ones: `unreal_service.py` (find/spawn/destroy actors, call functions, get/set properties — the main object API), `engine_service.py` (frame begin/end sync), `rendering_service.py` (viewport alignment), `navigation_service.py` (nav-mesh sampling), `enhanced_input_service.py` + `input_service.py` (inject keyboard/gamepad/input-actions), `segmentation_service.py` (object-ID ↔ actor maps), `sp_func_service.py` (calls into `SpFunc`s like `read_pixels`), `async_loading_service.py`, `world_registry_service.py`. |
| `python_ext/` | `spear_ext`, the compiled C++ extension (built by `tools/install_python_extension.py`): msgpack-rpc `Client`, `Future` (async calls), `DataBundle`/`PackedArray`/`SharedMemoryView` (zero-copy numpy transport). |

### C++ side (`cpp/`)

| Path | What it is |
|---|---|
| `cpp/unreal_plugins/SpCore` | Foundations: the `Config::` system (reads the yacs tree), stable-name components (human-readable actor names like `Meshes/05_chair/Kitchen_Chair_01`), logging, std/UE interop utils. |
| `cpp/unreal_plugins/SpServices` | The in-engine RPC server and every service the Python clients talk to: `RpcService` (rpclib server, port 30000), `EngineService` (frame work queues), `UnrealService` (reflection), `InitializeEngineService` (map/benchmarking/pak overrides at boot), `WorldRegistryService` (game-paused control, world bookkeeping), `InputService`/`EnhancedInputService`, `NavigationService`, `RenderingService`, `SegmentationService`, ... |
| `cpp/unreal_plugins/SpUnrealTypes` | Engine subclasses SPEAR needs: `SpSceneCaptureComponent2D` (the camera-pass workhorse behind `read_pixels()`), `SpMoviePipelineDeferredPass` (+ExtraPass0-3, custom MRQ passes with per-pass show flags/cvars), `SpLevelSequenceDirector` (streams level instances during cinematics), `SpGameMode`, `SpPlayerController`, `SpDebugManager`, etc. |
| `cpp/unreal_plugins/SpContent` | Content-only plugin shipped in the executable: **`BP_CameraSensor`** (17 capture components: RGB, `sp_depth_meters_`, `world_normal_`, `sp_object_ids_*` segmentation, roughness/metallic/diffuse/lighting-only, …), `BP_MultiViewCameraSensor_13/_33` (3-cam arc / 3×3 grid rigs), `BP_Axes`, `BP_SpGameMode`, `MPPC_*` Movie-Render-Queue configs, and the `PPM_*` post-process materials that implement the depth/normal passes. |
| `cpp/unreal_plugins/SpModuleRules` | Shared UnrealBuildTool build rules for all plugins. |
| `cpp/unreal_projects/SpearSim` | The Unreal project. `Content/SPEAR/Scenes/` = shipped scenes (`apartment_0000` furnished home + `debug_0000/0001`); other `Content/*` dirs are engine-template content copied in by `tools/copy_engine_content.py`. Build outputs land in `Standalone-Development/` (or `Standalone-Shipping/`). |
| `third_party/` | Submodules built by `tools/build_third_party_libs.py`: boost, rpclib (the RPC transport), yaml-cpp (C++ side of the config system). |

### Tooling and content workflows

| Path | What it is |
|---|---|
| `tools/` | User-facing CLI. Setup: `build_third_party_libs.py`, `install_python_extension.py`, `install_python_package_in_editor_env.py`, `copy_engine_content.py`, `install_updated_apple_sdk_json_in_engine/` (Xcode 26 fix). Build/run: `run_uat.py` (build+cook+package the executable), `run_executable.py` (launch standalone with a chosen `--map`), `run_editor.py` / `run_editor_script.py` / `run_editor_tasks/` (drive the editor), `run_editor_mrq_job.py` (offline movie rendering), `build_pak.py` / `build_paks_kujiale.py` (package extra scenes as mountable `.pak`s), `run_mcp_server.py` (expose the sim as an MCP server for natural-language control), `sign_executable_mac.py` / `_windows.py`. |
| `examples/` | 35 runnable programs, the best documentation of the API. Start with `getting_started` (spawn/get/set/call), then `render_image` (camera capture), `render_image_dataset` (RGB+depth+normals over sampled poses), `render_image_hypersim` (all 17 passes + segmentation), `render_image_multi_view` (multi-camera → mp4 video), `control_simple_agent`/`control_car`/`control_character` (forces & action injection), `movie_render_queue` (MRQ from Python), **`counterfactual_demo` (this fork — intervention → paired RGB/depth → diffs)**. The `control_*_sample` examples need separately-downloaded Epic sample projects + the editor; `import_*` need external datasets. |
| `editor/` | Python scripts that run **inside** the Unreal editor (via `tools/run_editor_script.py`) to generate the SpContent assets (`create_asset_bp_camera_sensor.py`, `create_asset_mppc_default_configs.py`, …) and to modify scenes (nav-mesh bounds, stable-name components). |
| `pipeline/` | Derives data from existing scenes (not scene generation): export geometry/metadata, collision geometry, kinematic trees, MuJoCo scene conversion (`generate_mujoco_scene.py`), and the `generate_free_space_*` family (navigable-space graphs → camera paths → images/videos). |
| `docs/` | Official tutorials (`getting_started.md`, `running_our_example_applications.md`, `controlling_with_natural_language.md`, `importing_and_exporting_assets.md`) + **`setup_experience/`** (this fork: setup playbook, exploration guide, troubleshooting cards). |

## Where to start, by goal

- **Set up a new machine** → `docs/setup_experience/SETUP_PLAYBOOK.md`
- **Learn the API** → run `examples/getting_started`, then read `python/spear/services/unreal_service.py`
- **Capture RGB/depth/segmentation** → `examples/render_image_dataset`, `examples/render_image_hypersim`
- **Record video** → `examples/render_image_multi_view` (frame loop) or `examples/movie_render_queue` (offline EXR)
- **Counterfactual data** → `examples/counterfactual_demo` + `docs/setup_experience/EXPLORATION_GUIDE.md` §4
- **Add scenes/assets** → `docs/importing_and_exporting_assets.md`, `tools/build_pak.py`
- **Understand a service end-to-end** → pick the client in `python/spear/services/`, find its C++ twin in `cpp/unreal_plugins/SpServices/Source/SpServices/`
