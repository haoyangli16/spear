# SPEAR exploration guide — capabilities, assets, and the counterfactual-video recipe

Compiled 2026-07-05 from a full survey of the repo (35 examples, the Python API, docs, content) plus a working demo in `counterfactual_demo/`. File references are to `~/spear-setup/spear`.

## 1. What scenes/assets do you have?

**Out of the box (packaged in your SpearSim.app):**
| Scene | Type | What's in it |
|---|---|---|
| `apartment_0000` (default) | **Furnished home interior** | Kitchen + living room; 95 runtime actors; 107 static meshes across 24 categories (sofa, chairs ×3 kinds, tables, cabinet, oven, sink, extractor, fireplace, lamps, curtains, cushions, vases, mirrors, pictures, props…), 191 materials/textures. Actors have stable names like `Meshes/05_chair/Kitchen_Chair_01` — categories are parseable from names (the hypersim example maps them to semantic labels). |
| `debug_0000`, `debug_0001` | Minimal test levels | Basic shapes; good for controlled physics experiments |
| `StarterMap`, `Minimal_Default`, `Advanced_Lighting` | UE starter demos | Small rooms / lighting demos; StarterContent also gives you a **prop library** (SM_Chair, SM_Couch, SM_TableRound, SM_Lamp, SM_Door, SM_Bush, SM_Rock…) you can spawn into any scene |
| `ThirdPersonMap` | Gray-box | Playable character map |
| `VehicleExampleMap`, `VehicleOffroadExampleMap` | **Outdoor** | Paved track + offroad terrain, 2 drivable cars |

**Verdict for your use case:** the strength is **indoor/home**. Outdoor is limited to the two vehicle maps.

**Getting more scenes:**
- **Kujiale library** — SPEAR's flagship dataset (historically ~300 photorealistic apartment interiors). Not in the repo; fetched via `tools/download_content_from_perforce.py` (needs Perforce access from the SPEAR team) and built into mountable `.pak` files with `tools/build_paks_kujiale.py`. Load at runtime with `--pak-files` or the `SpMountPak` console command.
- **Epic sample worlds** (CitySample = the Matrix city, ElectricDreams jungle, Hillside…) — free on Fab/Epic Launcher; SPEAR attaches to them via the `control_*_sample` examples (requires opening them in the UE editor with SPEAR plugins; see `docs/running_our_example_applications.md:40-43`).
- **Your own assets** — `docs/importing_and_exporting_assets.md` + `pipeline/import_external_content.py`.

## 2. The interaction API (all from Python, over RPC)

Everything runs in a deterministic frame loop — `with instance.begin_frame(): <act>` / `with instance.end_frame(): <observe>` executes in ONE engine frame; `instance.step(num_frames=N)` advances time. That determinism is exactly what counterfactual comparison needs.

| You want | API (game.unreal_service unless noted) |
|---|---|
| List all objects | `find_actors_as_dict()` → stable-name → actor map |
| Find objects | `find_actors_by_name/tag/class(...)` |
| Read pose | `actor.K2_GetActorLocation()/K2_GetActorRotation()` (⚠ returns **lowercase** `x,y,z` keys; setters take uppercase) |
| Change pose | `actor.K2_SetActorLocationAndRotation(NewLocation={"X":…}, NewRotation={"Pitch":…})` — call `SetMobility(NewMobility="Movable")` on its mesh component first if it's static scenery |
| Remove object | `destroy_actor(actor=…)` (or `SetActorHiddenInGame` to hide non-destructively) |
| Add object | `spawn_actor(uclass="AStaticMeshActor", location=…, spawn_parameters={"SpawnCollisionHandlingOverride":"AlwaysSpawn"})` + `SetStaticMesh(NewMesh=load_object(uclass="UStaticMesh", name="/Game/StarterContent/Props/SM_Chair.SM_Chair"))` |
| Physics | `component.AddForce(...)` (see `examples/control_simple_agent`); Chaos physics reacts automatically |
| Actions/input | `enhanced_input_service.inject_input_for_actor(...)` — drive the car, walk the character (`examples/control_car`, `control_character`) |
| Any UE function/property | `actor.AnyBlueprintCallableOrCppUFunction(...)`, `actor.get_properties()`, `set_property_value_for_object(...)` — the whole engine reflection system is exposed |
| RGB / depth / normals / segmentation | spawn `/SpContent/Blueprints/BP_CameraSensor` → 17 capture components (`final_tone_curve_hdr_` RGB, `sp_depth_meters_` metric depth, `world_normal_`, `sp_object_ids_*` instance segmentation, roughness/metallic/diffuse…) → `component.read_pixels()` → numpy |
| Semantic/instance masks | `segmentation_service` (see `examples/render_image_hypersim` — 17 passes + semantic labels derived from actor names) |
| Camera paths | `navigation_service.get_random_points(...)` on the nav mesh (`examples/render_image_dataset/generate_camera_poses.py`), or `pipeline/generate_free_space_camera_paths.py` |

## 3. Video recording — two tiers

1. **Frame-loop capture → mp4** (`examples/render_image_multi_view`): read_pixels every frame while moving the camera, then encode with the ffmpeg bundled in `imageio_ffmpeg` (no install needed). Works with depth/any pass — this is your workhorse for counterfactual video pairs, because you control every frame deterministically.
2. **Movie Render Queue** (`examples/movie_render_queue`, `tools/run_editor_mrq_job.py`): offline cinematic-quality rendering to 16-bit EXR sequences with depth-in-meters, normals, world position, object IDs, lighting-only passes, 7× supersampling. Driven from Python via `UMoviePipelineQueueEngineSubsystem`. Output lands in `Saved/MovieRenders/`.

## 4. The counterfactual recipe (proven working in `counterfactual_demo/`)

`~/spear-setup/counterfactual_demo/run.py` did exactly your workflow today against apartment_0000:
factual capture → **move+rotate** `Kitchen_Chair_01` (+60cm, +45°) → **remove** `Vase_01` → **add** a StarterContent chair → per-condition RGB + depth PNG + raw depth `.npy` + diff-vs-before heatmaps + contact sheet. See `output/`.

To extend it to **videos**: wrap each condition in a `for frame in range(N):` loop (move the camera or let physics run via `instance.step()`), save per-frame PNGs, encode like `render_image_multi_view` does. Because the frame loop is deterministic (fixed 1/30s delta time is SPEAR's default), the factual and counterfactual rollouts stay frame-aligned — only your intervention differs.

Determinism tips for clean pairs: keep `OVERRIDE_BENCHMARKING`/fixed delta time on (default), give 3+ settle frames after each scene edit (TAA/Lumen accumulate temporally), and expect small residual diff noise from animated foliage/sky outside windows.

## 5. Which stock examples to try next (all work with your packaged app)

| Example | Shows you |
|---|---|
| `getting_started` | The core spawn/get/set/call programming model |
| `render_image_dataset` | RGB+depth+normals over 50 nav-mesh camera poses (dataset generation) |
| `render_image_hypersim` | All 17 passes + full semantic/instance segmentation |
| `render_image_multi_view` | 9-camera rig + mp4 encoding (video) |
| `control_simple_agent` | Force-driven physics agent |
| `control_car` / `control_character` | Action injection (throttle/steer, walk/jump) |
| `movie_render_queue` | Offline EXR movie rendering |
| `sample_nav_mesh` | Free-space sampling |

Setup per example: copy `user_config.yaml.example` → `user_config.yaml`, set `GAME_EXECUTABLE` to `~/spear-setup/spear/cpp/unreal_projects/SpearSim/Standalone-Development/Mac/SpearSim.app` (the examples' `.example` files point at a Shipping path). One-time: `pip install -e "python[examples]"` (done).

## 6. Bonus: natural-language control

`tools/run_mcp_server.py` + `docs/controlling_with_natural_language.md` expose the whole API as an MCP server — i.e., Claude can drive the simulator conversationally ("move the sofa 1 m left and render the depth map"). Worth wiring up if you iterate on interventions interactively.

## Gotchas discovered while building the demo

- Getter structs return **lowercase** keys (`{'x':…}`), setter args take **uppercase** (`{"X":…}`) — see `counterfactual_demo/run.py`.
- Scene furniture is Static mobility; `SetMobility(NewMobility="Movable")` before moving it.
- `cv2.imshow`-based examples block on a GUI window — fine interactively, strip for batch runs.
- Diff-vs-baseline shows faint global noise from temporal AA and animated exterior; not a bug, tune settle frames if it matters.
