# Setup experience & exploration docs (fork-maintained)

This directory documents a complete, real-world SPEAR setup and capability exploration performed on
**2026-07-05** on a MacBook Pro (Apple M5 Pro, 48 GB RAM, macOS 26.5.1, Xcode 26.6, Unreal Engine 5.5),
following the official [getting_started.md](../getting_started.md) tutorial end-to-end. All 9 tutorial
phases passed. We maintain these docs in this fork so teammates can replicate the setup without
rediscovering the same pitfalls, and can quickly understand what SPEAR can do.

**New to the codebase? Read [`CODE_MAP.md`](../../CODE_MAP.md) at the repo root first.**

## Reading order

| Doc | Read it when… |
|---|---|
| [`SETUP_PLAYBOOK.md`](SETUP_PLAYBOOK.md) | **you are setting up SPEAR on a new machine** — the golden path: optimal install order, real durations per step, verification commands, every trap pre-empted |
| [`EXPLORATION_GUIDE.md`](EXPLORATION_GUIDE.md) | **you want to know what SPEAR can do** — scenes/assets inventory, the Python interaction API, RGB/depth/segmentation capture, video recording, and the counterfactual-data recipe |
| [`experience_cards/`](experience_cards/) | you hit an error — one card per problem we solved (symptom → root cause → exact fix) |
| [`FINAL_REPORT.md`](FINAL_REPORT.md) | you want the phase-by-phase acceptance evidence of the original setup |
| [`PROGRESS.md`](PROGRESS.md) / [`BLOCKERS.md`](BLOCKERS.md) | historical record of the run (timestamped log; human-blocker resolutions) |

## The four pitfalls, in one breath

1. **conda ≥ 25.7 blocks scripted `conda create`** until you run `conda tos accept` for the two default channels (card 01).
2. **The 174-submodule clone can die once with `early EOF`** — just re-run it; and use `set -o pipefail` if you pipe git output through `tee` (card 02).
3. **Command Line Tools ≠ Xcode.** CLT builds all the C++ deps fine, but the Unreal Editor hard-requires full Xcode for the Metal shader compiler — install Xcode *before* the 50 GB engine download, not after (card 03).
4. **`tools/run_executable.py` upstream bug** (as of 2026-07-05): stale `INITIALIZE_GAME_WORLD_SERVICE` config key crashes the tool; fixed in this fork by renaming to `WORLD_REGISTRY_SERVICE` (card 04).

## Hands-on companion

[`examples/counterfactual_demo/`](../../examples/counterfactual_demo/) is a working example built during this
exploration: it launches the packaged `SpearSim.app`, discovers all 95 actors in `apartment_0000`, then
captures RGB + metric depth under four conditions — baseline, move+rotate a chair, remove a vase,
add a new chair — and writes per-condition images, raw depth arrays, and diff-vs-baseline heatmaps.

Note on paths: `FINAL_REPORT.md`, `PROGRESS.md`, and `BLOCKERS.md` are verbatim records from the original
run and reference that machine's workspace (`~/spear-setup/...`). The playbook and exploration guide are
written to be machine-independent.
