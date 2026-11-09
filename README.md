# Mixed beam sampling fanout Linux validation

Public SGLang contribution candidate `sgl-mixed-beam-sampling-fanout`.
Exact upstream base: `3825fcd3978ea549a6b41417be21f6973c98e50e`.
Frozen patch SHA-256: `946f6bcf491003a3bfdd71ac42c372ffccd9dd4789bb96e907e0b060c686f784`.

Runs unchanged upstream `pre-commit run --all-files` on standard Ubuntu 24.04 / Python 3.12. The full candidate check has a 35 minute timeout. On candidate failure, a pristine worktree of the same base runs the same complete command with its own 35 minute timeout. A baseline failure never converts a failed candidate into a passing result.

This package is dispatched independently on its own branch. The workflow is installed remotely as `.github/workflows/sglang-rerank.yml`; its concurrency group includes the branch ref. It uses no artifact/cache actions, paid runner class, model downloads, or publication. Raw evidence is compressed into the job log with SHA-256. The job has a 90 minute limit.

Tool preparation follows this exact base: Rust 1.92 with clippy/rustfmt, Rust 1.90 with clippy/rustfmt, and nightly rustfmt for the explicit gateway hook. The Ollama base adds a Python standard-library sidebar-sort hook; it does not add a Node hook.

Local preparation only applied this exact patch to a temporary repository containing changed base files, then computed final file hashes. No full checkout, dependency installation, or product change was performed locally. The product patch remains under the upstream Apache-2.0 license.
