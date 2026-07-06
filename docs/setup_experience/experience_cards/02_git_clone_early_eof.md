# git clone --recurse-submodules dies with "early EOF" on large repos

- Date / Phase: 2026-07-05 / Phase 2
- Symptom:
  ```
  fetch-pack: unexpected disconnect while reading sideband packet
  fatal: early EOF
  fatal: fetch-pack: invalid index-pack output
  ```
  after ~400 MB of a multi-GB transfer. git deletes the partial clone directory on failure, so a naive "check the dir exists" test can also mislead.
- Root cause: transient network disconnect mid-transfer (the spear repo + 174 submodules, boost alone is ~150 subrepos and the main pack is >1.5 GB). Nothing wrong with the machine or the command.
- Fix (exact commands): simply re-run the identical clone; it succeeded on attempt 2:
  ```
  git clone https://github.com/spear-sim/spear ~/spear-setup/spear --recurse-submodules
  ```
  If it fails repeatedly, fall back to a resumable strategy: clone without submodules first, then `git submodule update --init --recursive --jobs 4` (which resumes per-submodule instead of restarting everything).
- Time lost: ~15 minutes (one full re-download).
- How others can avoid this:
  1. Expect this on flaky networks/VPNs; retry once before diagnosing.
  2. If scripting: `git clone ... | tee log; echo $?` reports **tee's** exit code, not git's — attempt 1 looked "successful" (exit 0) until the log was read. Use `set -o pipefail` (zsh/bash) so the pipeline propagates git's failure.
  3. Verify with `git submodule status --recursive | grep -c '^-'` == 0 rather than trusting exit codes alone.
