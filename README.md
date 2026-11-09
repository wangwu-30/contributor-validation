# Offline random input token accounting Linux validation

Public SGLang contribution candidate `sgl-offline-random-input-token-accounting`.
Exact upstream base: `76dafba55a5e3e155368474fe9ffcdc71db27749`.
Frozen patch SHA-256: `eb6ce6fb3187548395fff9bb28914bb3db8b2091fcdcf94e82df4f3c108bd363`.

Runs unchanged upstream `pre-commit run --all-files` on standard Ubuntu 24.04 / Python 3.12. The full candidate check has a 35 minute timeout. On candidate failure, a pristine worktree of the same base runs the same complete command with its own 35 minute timeout. A baseline failure never converts a failed candidate into a passing result.

This package is dispatched independently on its own branch. The workflow is installed remotely as `.github/workflows/sglang-rerank.yml`; its concurrency group includes the branch ref. It uses no artifact/cache actions, paid runner class, model downloads, or publication. Raw evidence is compressed into the job log with SHA-256. The job has a 90 minute limit.

Tool preparation follows this exact base: Rust 1.92 with clippy/rustfmt, Rust 1.90 with clippy/rustfmt, and nightly rustfmt for the explicit gateway hook. The Ollama base adds a Python standard-library sidebar-sort hook; it does not add a Node hook.

Local preparation only applied this exact patch to a temporary repository containing changed base files, then computed final file hashes. No full checkout, dependency installation, or product change was performed locally. The product patch remains under the upstream Apache-2.0 license.
