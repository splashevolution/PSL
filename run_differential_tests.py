#!/usr/bin/env python3
"""Canonical PSL differential/falsification suite.

This replaces the pre-repair IR-vs-legacy-emitter comparison.

For randomly generated programs from the *currently formalized control subset*
it checks:

  D1  Fresh compiler instances emit identical word streams.
  D2  An independent numeric reference validator accepts every emitted stream.
  D3  Every compiler IR node lowers to the corresponding emitted word.
  D4  Every emitted value is a 32-bit ABI word.

The generator covers:
  * Ring-2 explicit/inherited Write to Siddha and Asiddha
  * Siddha Lopa outside Adhikara
  * scoped Ring-0 Store and inherited Store to Asiddha
  * scoped Asiddha Lopa
  * scoped Store/Store Sandhi pair marking
  * scope open/close and mixed lifecycles

It deliberately excludes Avrtti execution, Utsarga/Apavada conditions, and
claims of Sandhi atomicity because those are not yet part of the repaired Lean
execution theorem.

The reference validator is a separate Python implementation over numeric ABI
words. Agreement is testing evidence, not a formal proof. Lean CI separately
checks a deterministic finite compiler-output corpus.

Usage:
    python run_differential_tests.py [--count 5000] [--seed 42] [--verbose]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src" / "utils"))

from paninian_compiler import PaninianFormalCompiler

OP_LOPA = 0x00
OP_WRITE = 0x05
OP_READ = 0x06
OP_STORE = 0xCC
OP_OPEN = 0xAA
OP_CLOSE = 0xBB
ASIDDHA_BASE = 0x50

ADDRESSES = (0x20, 0x30, 0x40, 0x50, 0x60, 0x70)
SIDDHA = tuple(a for a in ADDRESSES if a < ASIDDHA_BASE)
ASIDDHA = tuple(a for a in ADDRESSES if a >= ASIDDHA_BASE)


def fields(word: int):
    return {
        "ring": (word >> 28) & 0xF,
        "comp": (word >> 24) & 0xF,
        "opcode": (word >> 16) & 0xFF,
        "target": (word >> 8) & 0xFF,
        "flags": (word >> 4) & 0xF,
        "cond": word & 0xF,
    }


def reference_validate(words):
    """Independent executable mirror of the repaired control contract."""
    written = set()
    context = None
    depth = 0

    for word in words:
        f = fields(word)
        op = f["opcode"]

        if op == OP_OPEN:
            depth += 1
            continue

        if op == OP_CLOSE:
            if depth == 0:
                return False
            depth -= 1
            continue

        if op not in (OP_LOPA, OP_WRITE, OP_READ, OP_STORE):
            return False

        if f["comp"] == 1:
            if context is None:
                return False
            target = context
        else:
            target = f["target"]

        if f["ring"] == 0 and target < ASIDDHA_BASE:
            return False

        if f["ring"] == 0 and depth == 0:
            return False

        if op == OP_STORE and (depth == 0 or f["ring"] != 0):
            return False

        if (
            op == OP_LOPA
            and target >= ASIDDHA_BASE
            and (depth == 0 or f["ring"] != 0)
        ):
            return False

        if op == OP_LOPA and target not in written:
            return False

        if op in (OP_WRITE, OP_STORE):
            written.add(target)
        elif op == OP_LOPA:
            written.discard(target)

        if op == OP_LOPA:
            context = None
        elif f["comp"] != 1:
            context = target

    return depth == 0


class SourceBuilder:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.body = []
        self.written = set()
        self.context = None
        self.in_scope = False

    @staticmethod
    def name(addr):
        return f"A{addr:02X}"

    def explicit_write(self, addr):
        indent = "        " if self.in_scope else "    "
        self.body.append(f"{indent}{self.name(addr)} लिखति ।")
        self.written.add(addr)
        self.context = addr

    def inherited_write(self):
        if self.context is None:
            return False
        indent = "        " if self.in_scope else "    "
        self.body.append(f"{indent}लिखति ।")
        self.written.add(self.context)
        return True

    def explicit_lopa(self, addr):
        # Lopa inside scope is auto-promoted to Ring 0, so only Asiddha is
        # legal there. Outside scope only Siddha Lopa is legal.
        if addr not in self.written:
            return False
        if self.in_scope and addr < ASIDDHA_BASE:
            return False
        if not self.in_scope and addr >= ASIDDHA_BASE:
            return False
        indent = "        " if self.in_scope else "    "
        self.body.append(f"{indent}{self.name(addr)} लोपः ।")
        self.written.discard(addr)
        self.context = None
        return True

    def open_scope(self):
        assert not self.in_scope
        self.body.append("    अधिकारः {")
        self.in_scope = True

    def close_scope(self):
        assert self.in_scope
        self.body.append("    }")
        self.in_scope = False

    def explicit_store(self, addr):
        assert self.in_scope and addr >= ASIDDHA_BASE
        self.body.append(f"        {self.name(addr)} स्थापयति ।")
        self.written.add(addr)
        self.context = addr

    def inherited_store(self):
        if not self.in_scope or self.context is None or self.context < ASIDDHA_BASE:
            return False
        self.body.append("        स्थापयति ।")
        self.written.add(self.context)
        return True

    def sandhi_store_pair(self, addr):
        assert self.in_scope and addr >= ASIDDHA_BASE
        self.body.extend(
            [
                f"        {self.name(addr)} स्थापयति ।",
                "        सन्धिः ।",
                f"        {self.name(addr)} स्थापयति ।",
            ]
        )
        self.written.add(addr)
        self.context = addr

    def source(self):
        declarations = [
            f"सञ्ज्ञा {self.name(addr)} = 0x{addr:02X} ।"
            for addr in ADDRESSES
        ]
        assert not self.in_scope
        return "\n".join(
            declarations
            + ["", "तन्त्रशास्त्रम् {"]
            + self.body
            + ["}", ""]
        )


def generate_source(rng: random.Random):
    b = SourceBuilder(rng)

    # Establish at least one explicit top-level write.
    b.explicit_write(rng.choice(ADDRESSES))

    # Additional top-level control operations.
    for _ in range(rng.randint(0, 4)):
        choices = ["write", "inherit"]
        siddha_live = [a for a in b.written if a < ASIDDHA_BASE]
        if siddha_live:
            choices.append("lopa")
        choice = rng.choice(choices)
        if choice == "write":
            b.explicit_write(rng.choice(ADDRESSES))
        elif choice == "inherit":
            b.inherited_write()
        else:
            b.explicit_lopa(rng.choice(siddha_live))

    # Optional privileged scope.
    if rng.random() < 0.85:
        b.open_scope()
        for _ in range(rng.randint(1, 5)):
            choices = ["store", "sandhi"]
            if b.context is not None and b.context >= ASIDDHA_BASE:
                choices.append("inherit_store")
            asiddha_live = [a for a in b.written if a >= ASIDDHA_BASE]
            if asiddha_live:
                choices.append("lopa")
            choice = rng.choice(choices)
            if choice == "store":
                b.explicit_store(rng.choice(ASIDDHA))
            elif choice == "sandhi":
                b.sandhi_store_pair(rng.choice(ASIDDHA))
            elif choice == "inherit_store":
                b.inherited_store()
            else:
                b.explicit_lopa(rng.choice(asiddha_live))
        b.close_scope()

    # Optional post-scope Ring-2 operations. Explicit write always restores
    # context if a prior Lopa cleared it.
    for _ in range(rng.randint(0, 3)):
        choices = ["write"]
        if b.context is not None:
            choices.append("inherit")
        siddha_live = [a for a in b.written if a < ASIDDHA_BASE]
        if siddha_live:
            choices.append("lopa")
        choice = rng.choice(choices)
        if choice == "write":
            b.explicit_write(rng.choice(ADDRESSES))
        elif choice == "inherit":
            b.inherited_write()
        else:
            b.explicit_lopa(rng.choice(siddha_live))

    return b.source()


def check_one(src: str):
    c1 = PaninianFormalCompiler()
    c2 = PaninianFormalCompiler()

    words1 = c1.compile_source(src)
    words2 = c2.compile_source(src)

    failures = []

    if words1 != words2:
        failures.append("D1 compiler output differs across fresh instances")

    if not reference_validate(words1):
        failures.append("D2 independent numeric validator rejected compiler output")

    ir = c1._last_ir
    lowered = [n.to_word() for n in ir]
    if lowered != words1:
        failures.append("D3 IR node lowering differs from emitted word stream")

    if not all(isinstance(w, int) and 0 <= w <= 0xFFFFFFFF for w in words1):
        failures.append("D4 emitted value outside 32-bit ABI range")

    return failures, words1


def fixed_negative_reference_cases():
    return {
        "anuvrtti_without_context": [0x210500F0],
        "close_at_zero": [0x00BB00F0],
        "ring0_siddha_scoped": [0x00AA00F0, 0x000530F0, 0x00BB00F0],
        "store_outside_scope": [0x00CC60F0],
        "ring2_store_in_scope": [0x00AA00F0, 0x20CC60F0, 0x00BB00F0],
        "asiddha_lopa_unwritten": [0x00AA00F0, 0x000060F0, 0x00BB00F0],
        "double_lopa": [0x200530F0, 0x200030F0, 0x200030F0],
        "post_lopa_anuvrtti": [0x200530F0, 0x200030F0, 0x210500F0],
        "unclosed_scope": [0x00AA00F0],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    failures = []
    distinct_streams = set()
    distinct_words = set()

    for i in range(args.count):
        src = generate_source(rng)
        try:
            errs, words = check_one(src)
        except Exception as exc:
            errs = [f"EXCEPTION {type(exc).__name__}: {exc}"]
            words = []

        distinct_streams.add(tuple(words))
        distinct_words.update(words)

        if errs:
            failures.append((i, src, errs))
            if args.verbose:
                print(f"\n--- failing generated program {i} ---")
                print(src)
                for err in errs:
                    print(" ", err)

        if (i + 1) % 500 == 0:
            print(
                f"{i + 1}/{args.count}: failures={len(failures)} "
                f"distinct_streams={len(distinct_streams)} "
                f"distinct_words={len(distinct_words)}"
            )

    negative_failures = []
    for name, words in fixed_negative_reference_cases().items():
        if reference_validate(words):
            negative_failures.append(name)

    print("\nCanonical PSL differential/falsification result")
    print(f"  seed:              {args.seed}")
    print(f"  generated:         {args.count}")
    print(f"  failures:          {len(failures)}")
    print(f"  distinct streams:  {len(distinct_streams)}")
    print(f"  distinct words:    {len(distinct_words)}")
    print(f"  negative failures: {len(negative_failures)}")

    if negative_failures:
        print("  unexpectedly accepted negatives:", ", ".join(negative_failures))

    if failures or negative_failures:
        if failures and not args.verbose:
            idx, src, errs = failures[0]
            print(f"\nFirst failure: generated program {idx}")
            print(src)
            for err in errs:
                print(" ", err)
        raise SystemExit(1)

    print(
        f"[PASS] {args.count}/{args.count} generated programs satisfied D1-D4; "
        f"{len(fixed_negative_reference_cases())} fixed invalid streams rejected."
    )


if __name__ == "__main__":
    main()
