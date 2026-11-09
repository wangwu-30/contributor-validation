#!/usr/bin/env python3
"""Run the exact candidate all-files check, then pristine-base comparison on failure.

Use Ubuntu 24.04 / Python 3.12 with requirements-precommit.txt installed.
The workflow must use timeout-minutes: 90 and always export evidence/.
No product dependencies, model downloads, publication, or hook skips are used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

BASE = 'd910efa03a864131dd81fab022bab8c7739daed9'
PATCH_SHA = 'f6e894838f400268a93aa1891388e6924554572bbd29952068f0a9cc28ad02d7'
CONFIG_SHA = 'bc5fad26a3713d59d28398dd5b7cfcb4296d305c154b76ba0ac34af6e1518632'
FILES = {
    "python/sglang/srt/entrypoints/ollama/serving.py": "05883e38f6029e7656d00c9aee0bb4debc2afeda430e1ce6fdfaca0ed25009dc",
    "test/registered/unit/entrypoints/ollama/test_sampling_options.py": "a5ec6782ea67ae552d714366832257cb03b00168ae7901b1c97756f2ebb16209"
}
ACTIVE = None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def stop_group(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    # A parent can exit while build/compiler grandchildren remain alive.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def interrupted(signum, _frame):
    stop_group(ACTIVE)
    raise SystemExit(128 + signum)


def run(command, cwd, evidence, name, timeout=120, check=True):
    global ACTIVE
    began = time.time()
    print("Starting " + name, flush=True)
    timed_out = False
    with (evidence / (name + ".stdout")).open("wb") as out, (evidence / (name + ".stderr")).open("wb") as err:
        ACTIVE = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err,
                                  env=os.environ.copy(), start_new_session=True)
        try:
            code = ACTIVE.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_group(ACTIVE)
            code = ACTIVE.returncode
        finally:
            # Ensure no orphan workers survive a failed or successful hook.
            stop_group(ACTIVE)
            ACTIVE = None
    result = {"argv": command, "cwd": str(cwd), "start_epoch": began,
              "end_epoch": time.time(), "returncode": code, "timed_out": timed_out}
    save(evidence / (name + ".json"), result)
    print(f"Finished {name}: returncode={code}, timed_out={timed_out}", flush=True)
    if check and (code != 0 or timed_out):
        raise RuntimeError("Command failed; inspect " + name + ".{json,stdout,stderr}")
    return result


def git_value(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()


def verify_tree(source, candidate=False):
    if git_value(source, "rev-parse", "HEAD") != BASE:
        raise RuntimeError("Incorrect source base")
    if sha(source / ".pre-commit-config.yaml") != CONFIG_SHA:
        raise RuntimeError("Incorrect pre-commit config")
    if candidate:
        actual = {path: sha(source / path) for path in FILES}
        if actual != FILES:
            raise RuntimeError("Candidate file hashes do not match frozen patch")
        return actual
    if git_value(source, "status", "--porcelain"):
        raise RuntimeError("Base checkout is not pristine")
    return {}


def state(source, evidence, prefix):
    for suffix, args in [
        ("status", ["status", "--porcelain=v1", "--untracked-files=all"]),
        ("diff", ["diff", "--binary"]),
        ("staged-diff", ["diff", "--cached", "--binary"]),
        ("head-diff", ["diff", "HEAD", "--binary"]),
        ("tracked-files", ["ls-files"]),
    ]:
        run(["git", *args], source, evidence, prefix + "-" + suffix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="source/checkout")
    parser.add_argument("--patch", default="product.patch")
    parser.add_argument("--evidence", default="evidence")
    args = parser.parse_args()
    source, patch, evidence = (Path(x).resolve() for x in (args.source, args.patch, args.evidence))
    evidence.mkdir(parents=True, exist_ok=True)
    if (evidence / "result.json").exists():
        raise RuntimeError("Refusing to overwrite previous result evidence")
    result = {"base": BASE, "patch_sha256": PATCH_SHA, "status": "infrastructure_error"}
    try:
        if platform.system() != "Linux" or sys.version_info[:2] != (3, 12):
            raise RuntimeError("Requires Linux Python 3.12")
        if os.environ.get("SKIP"):
            raise RuntimeError("SKIP is forbidden")
        os.environ.pop("SKIP", None)
        if sha(patch) != PATCH_SHA:
            raise RuntimeError("Incorrect frozen patch SHA256")
        verify_tree(source)
        save(evidence / "environment.json", {
            "python": sys.version, "platform": platform.platform(),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "pre_commit_home": os.environ.get("PRE_COMMIT_HOME"),
            "cargo_target_dir": os.environ.get("CARGO_TARGET_DIR"),
            "skip": None,
        })
        for name, command in [
            ("os-release", ["cat", "/etc/os-release"]),
            ("disk", ["df", "-h"]),
            ("git-version", ["git", "--version"]),
            ("python-version", [sys.executable, "--version"]),
            ("pip-freeze", [sys.executable, "-m", "pip", "freeze", "--all"]),
            ("pip-check", [sys.executable, "-m", "pip", "check"]),
            ("precommit-version", [sys.executable, "-m", "pre_commit", "--version"]),
            ("rustup-show", ["rustup", "show"]),
            ("rustup-toolchains", ["rustup", "toolchain", "list"]),
            ("system-packages", ["dpkg-query", "-W"]),
        ]:
            run(command, source, evidence, name)
        run(["git", "switch", "-c", "validation/rerank-candidate"], source, evidence, "candidate-branch")
        run(["git", "apply", "--check", str(patch)], source, evidence, "patch-check")
        run(["git", "apply", str(patch)], source, evidence, "patch-apply")
        result["verified_candidate_files"] = verify_tree(source, candidate=True)
        run(["git", "add", "--", *FILES], source, evidence, "candidate-add")
        (evidence / "pre-commit-config.yaml").write_bytes((source / ".pre-commit-config.yaml").read_bytes())
        state(source, evidence, "candidate-before")
        command = [sys.executable, "-m", "pre_commit", "run", "--all-files"]
        candidate = run(command, source, evidence, "candidate-precommit", timeout=35 * 60, check=False)
        result["candidate"] = candidate
        state(source, evidence, "candidate-after")
        result["source_changed_by_hooks"] = any(
            (evidence / ("candidate-before-" + suffix)).read_bytes()
            != (evidence / ("candidate-after-" + suffix)).read_bytes()
            for suffix in ("status.stdout", "head-diff.stdout")
        )
        if candidate["returncode"] == 0 and not candidate["timed_out"] and not result["source_changed_by_hooks"]:
            verify_tree(source, candidate=True)
            result["status"] = "candidate_passed"
            return 0
        # A new worktree shares Git objects only; candidate worktree edits cannot
        # leak into this pristine, explicitly named baseline branch.
        baseline = source.parent / "baseline"
        run(["git", "worktree", "add", "-b", "validation/rerank-baseline", str(baseline), BASE],
            source, evidence, "baseline-create", timeout=300)
        verify_tree(baseline)
        state(baseline, evidence, "baseline-before")
        result["baseline"] = run(command, baseline, evidence, "baseline-precommit", timeout=35 * 60, check=False)
        state(baseline, evidence, "baseline-after")
        result["status"] = "candidate_failed_baseline_comparison_recorded"
        result["interpretation"] = "Candidate did not pass. Compare raw hook outputs and diffs; baseline failure never converts candidate failure into success."
        return 1
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        save(evidence / "result.json", result)
        print(json.dumps(result, indent=2), flush=True)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
                summary.write("### SGLang rerank Linux result\n\n```json\n" + json.dumps(result, indent=2) + "\n```\n")


if __name__ == "__main__":
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    sys.exit(main())
