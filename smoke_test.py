#!/usr/bin/env python3
"""Execute every course notebook and report failures.

Each notebook is copied into its own temp subdirectory and executed there.
nbconvert sets the kernel's working directory to wherever the notebook file
lives, so this keeps committed outputs untouched and stops side-effect writes
(the figures/ PNGs in module 07, SQLite files in module 10) from leaking into
the source tree. Every notebook is self-contained and loads its data from a
URL, so the copy is safe.

Before executing anything, a static check verifies that every notebook's
saved state is a clean top-to-bottom run: code cells numbered 1..N with no
unexecuted cells and no saved error outputs. This catches the "committed a
notebook without re-running it" mistake without executing a thing.

The full suite runs in about three minutes, so there is no reason to skip it
before a push that touches notebooks.

Usage:
    python smoke_test.py                  # static check, then execute everything
    python smoke_test.py 07 11_2          # only paths containing a pattern
    python smoke_test.py --counts         # static check only, no execution
    python smoke_test.py --list           # show what would run, don't run
    python smoke_test.py --timeout 600    # per-notebook timeout in seconds

Exit status is non-zero if the static check or any notebook fails.
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent
VENV_DIR = ROOT / "venv"

EXCLUDE_DIR_PARTS = {"venv", ".ipynb_checkpoints", "_site"}


def venv_warning():
    """None if running from ./venv (or if no ./venv exists, as in CI);
    otherwise a banner to print.

    Jupyter picks a kernel via sys.prefix, which is set by which python ran
    this script, not by whether `source venv/bin/activate` was typed.
    (Checking sys.executable directly doesn't work: venv/bin/python3 is a
    symlink to the system interpreter, so resolving it collapses both paths
    to the same file. sys.prefix is what venvs actually redirect via
    pyvenv.cfg, so it's the correct signal.) If this process isn't running
    with ./venv's prefix, notebooks execute against whatever kernel is
    registered elsewhere on the machine, which can be missing or have
    outdated packages. Failures from that mismatch look exactly like real
    notebook bugs, so flag it loudly rather than let it masquerade as one.
    """
    if not VENV_DIR.exists():
        return None  # CI installs into its own interpreter; nothing to compare
    try:
        running = pathlib.Path(sys.prefix).resolve()
        expected = VENV_DIR.resolve()
    except OSError:
        return None
    if running == expected:
        return None
    return (
        "\n"
        "############################################################\n"
        "#  WARNING: not running from this project's venv.\n"
        f"#  Expected prefix: {expected}\n"
        f"#  Actual prefix:   {running}\n"
        "#  Run `source venv/bin/activate` first. Otherwise notebooks\n"
        "#  execute against whatever Jupyter kernel is registered\n"
        "#  elsewhere, and failures below may be environment artifacts,\n"
        "#  not real bugs.\n"
        "############################################################\n"
    )


def collect(patterns):
    nbs = []
    for p in sorted(ROOT.rglob("*.ipynb")):
        rel = p.relative_to(ROOT)
        if EXCLUDE_DIR_PARTS & set(rel.parts):
            continue
        if patterns and not any(pat in str(rel) for pat in patterns):
            continue
        nbs.append(rel)
    return nbs


def check_saved_state(nbs):
    """Verify each notebook's committed state is a clean 1..N run.

    Returns a list of problem strings (empty means all clean). Applies to
    every notebook, exercises included: the exercises ship fully executed
    with solution cells, so they must be clean runs too.
    """
    problems = []
    for rel in nbs:
        nb = json.loads((ROOT / rel).read_text())
        code = [c for c in nb["cells"] if c["cell_type"] == "code"]
        counts = [c.get("execution_count") for c in code]
        if counts != list(range(1, len(code) + 1)):
            nulls = sum(1 for c in counts if c is None)
            detail = f"{nulls} unexecuted cell(s)" if nulls else f"counts {counts[:6]}..."
            problems.append(f"{rel}: not a clean 1..N run ({detail})")
        for i, c in enumerate(code):
            for o in c.get("outputs", []):
                if o.get("output_type") == "error":
                    problems.append(
                        f"{rel}: saved error output in code cell {i} ({o.get('ename')})"
                    )
    return problems


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("patterns", nargs="*",
                    help="only check notebooks whose path contains one of these substrings")
    ap.add_argument("--list", action="store_true",
                    help="list notebooks that would run, then exit")
    ap.add_argument("--counts", action="store_true",
                    help="run only the static saved-state check, no execution")
    ap.add_argument("--timeout", type=int, default=600,
                    help="per-notebook timeout in seconds (default 600)")
    args = ap.parse_args()

    nbs = collect(args.patterns)
    if not nbs:
        print("No notebooks matched.")
        return 1
    if args.list:
        for nb in nbs:
            print(nb)
        print(f"\n{len(nbs)} notebooks")
        return 0

    problems = check_saved_state(nbs)
    if problems:
        print(f"Static check: {len(problems)} problem(s) in saved notebook state:")
        for p in problems:
            print(f"  {p}")
        print("\nRe-run the notebook top to bottom and commit, e.g.:")
        print("  jupyter nbconvert --to notebook --execute --inplace <notebook>")
    else:
        print(f"Static check: all {len(nbs)} notebooks have clean saved state.")
    if args.counts:
        return 1 if problems else 0

    warning = venv_warning()
    if warning:
        print(warning)

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, nb in enumerate(nbs, 1):
            print(f"[{i}/{len(nbs)}] {nb} ... ", end="", flush=True)
            start = time.time()
            try:
                work_dir = pathlib.Path(tmp) / str(nb).replace("/", "__")
                work_dir.mkdir()
                nb_copy = work_dir / nb.name
                shutil.copy(ROOT / nb, nb_copy)
                proc = subprocess.run(
                    [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
                     "--execute", str(nb_copy), "--output-dir", str(work_dir),
                     "--ExecutePreprocessor.timeout", str(args.timeout)],
                    capture_output=True, text=True, timeout=args.timeout + 60,
                )
                ok = proc.returncode == 0
                err = proc.stderr
            except subprocess.TimeoutExpired:
                ok, err = False, f"hard timeout after {args.timeout}s"
            elapsed = time.time() - start
            if ok:
                print(f"ok ({elapsed:.0f}s)")
            else:
                print(f"FAIL ({elapsed:.0f}s)")
                tail = "\n".join(line for line in err.splitlines() if line.strip())[-2000:]
                failures.append((nb, tail))

    print(f"\n{len(nbs) - len(failures)}/{len(nbs)} notebooks passed.")
    for nb, tail in failures:
        print(f"\n=== FAILED: {nb} ===\n{tail}")
    if failures and warning:
        print(warning)
    return 1 if (failures or problems) else 0


if __name__ == "__main__":
    sys.exit(main())
