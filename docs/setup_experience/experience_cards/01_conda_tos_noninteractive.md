# conda 26.x blocks env creation until Anaconda ToS is accepted

- Date / Phase: 2026-07-05 / Phase 1
- Symptom: `conda create -y --name spear-env python=3.11` fails immediately with
  `CondaToSNonInteractiveError: Terms of Service have not been accepted for the following channels: https://repo.anaconda.com/pkgs/main, https://repo.anaconda.com/pkgs/r`
- Root cause: Fresh Miniconda installs (conda ≥25.7, here 26.3.2) require a one-time, per-machine acceptance of the Anaconda repository Terms of Service. In non-interactive shells (CI, agents) the interactive prompt is skipped and the command hard-fails.
- Fix (exact commands):
  ```
  conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
  conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
  ```
  then re-run the original `conda create`.
- Time lost: ~3 minutes.
- How others can avoid this: run the two `conda tos accept` commands right after installing Miniconda, before any `conda create`/`conda install`. Alternative: use conda-forge exclusively (`conda config --add channels conda-forge && conda config --set channel_priority strict`) so the ToS-gated default channels are never consulted, or set `CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes`.
