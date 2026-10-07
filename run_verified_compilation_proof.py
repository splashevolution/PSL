#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PSL verification-repair harness.

The historical filename is retained for compatibility. This script no longer
claims that Python assertions are formal proofs or that PSL has a
CompCert-equivalent end-to-end correctness theorem.

It runs the current evidence gates:

1. Python compiler semantic-contract + canonical-program tests.
2. Generation of exact compiler-output conformance cases for Lean.
3. Real Lean/Lake typechecking of PSL.Semantics.
4. Lean acceptance of Python-emitted canonical/generated binaries.
5. Lean rejection of adversarial binaries.
6. Principal-theorem axiom audit.

A successful run establishes the current documented verification boundary. It
does NOT establish Python-source -> RV32 semantic preservation, Sandhi
atomicity, physical-silicon behavior, or a general compiler-correctness theorem.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEAN_DIR = ROOT / "lean"
GENERATED = LEAN_DIR / "GeneratedConformance.lean"


def run(label: str, command: list[str], cwd: Path = ROOT) -> None:
    print("\n" + "=" * 78)
    print(f"  {label}")
    print("=" * 78)
    print("$", " ".join(command))
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(
            f"\nFAILED: {label} (exit code {completed.returncode})"
        )


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(
            f"Required tool '{name}' is not available on PATH. "
            "Install/use the pinned Lean toolchain before claiming a full "
            "verification run."
        )


def main() -> None:
    require_tool("lake")

    run(
        "Python semantic contract",
        [sys.executable, "-m", "unittest", "discover", "-v", "-s", "tests"],
    )

    run(
        "Generate compiler -> Lean conformance corpus",
        [
            sys.executable,
            "scripts/generate_lean_conformance.py",
            str(GENERATED),
        ],
    )

    run("Lean formal core", ["lake", "build"], cwd=LEAN_DIR)

    run(
        "Compiler-output conformance in Lean",
        ["lake", "env", "lean", GENERATED.name],
        cwd=LEAN_DIR,
    )

    run(
        "Adversarial rejection conformance in Lean",
        ["lake", "env", "lean", "NegativeConformance.lean"],
        cwd=LEAN_DIR,
    )

    run(
        "Principal theorem dependency audit",
        ["lake", "env", "lean", "Audit.lean"],
        cwd=LEAN_DIR,
    )

    print("\n" + "=" * 78)
    print("  PSL VERIFICATION-REPAIR GATES: PASS")
    print("=" * 78)
    print(
        "Established: compiler regression contract + CI-typechecked Lean "
        "abstract semantics + finite Python-binary/Lean conformance + "
        "adversarial rejection + theorem dependency audit."
    )
    print(
        "Not established: universal Python-source/compiler correctness, "
        "Avrtti/conditional/Sandhi end-to-end semantics, RV32 refinement, "
        "or physical-hardware correctness."
    )


if __name__ == "__main__":
    main()
