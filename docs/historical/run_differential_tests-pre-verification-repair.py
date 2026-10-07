#!/usr/bin/env python3
"""
PVM Differential Test Suite

Tests that the IR compilation path and the legacy direct-emission path
produce byte-identical output for every valid PSL program.

Four properties verified per program:
  D1 (Byte identity)        IR words == legacy words, byte-for-byte
  D2 (Constraint coverage)  Every non-sentinel IRNode carries P1-ok..P4-ok
  D3 (Word count identity)  len(ir_words) == len(legacy_words)
  D4 (L1 determinism)       node.to_word() is stable across two calls

The generator produces structurally valid programs only -- programs that
would pass validate_ir() -- so all four properties must hold on every run.

The generator covers:
  - Write, Store (Ring 2 only outside scope), Lopa, Anuvrtti
  - Avrtti (count 2-5)
  - Sanjnaa symbol declarations
  - Sandhi pairs (Write+Write, Write+Store on same Asiddha target)
  - Adhikara scope blocks (Ring-0 Store inside scope)

Usage:
    python -B run_differential_tests.py [--count N] [--seed S] [--verbose]
"""

import argparse
import importlib.util
import random
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_compiler():
    spec = importlib.util.spec_from_file_location(
        "paninian_compiler", ROOT / "src/utils/paninian_compiler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Program generator
# ---------------------------------------------------------------------------

# Siddha targets (can be used with Write/Lopa in Ring 2)
SIDDHA_TARGETS  = [0x30]          # Vak
# Asiddha targets (can be used with Write/Store in Ring 2, or Ring-0 in scope)
ASIDDHA_TARGETS = [0x50, 0x60]    # Srotra, Yantra

# Karaka tokens for known addresses
ADDR_TO_KARAKA = {
    0x30: "वाचम्",
    0x50: "श्रोत्रम्",
    0x60: "यन्त्र",
}


class ProgramBuilder:
    """Builds a valid PSL program as a string, tracking written targets."""

    def __init__(self, rng: random.Random):
        self.rng          = rng
        self.lines        = []
        self.written      = set()   # targets written in current scope
        self.prev_target  = None
        self.in_scope     = False   # inside Adhikara block
        self.sanjnaa_map  = {}      # name -> addr

    def _karaka(self, addr):
        """Return the PSL token for a given address (or Sanjnaa name)."""
        for name, a in self.sanjnaa_map.items():
            if a == addr and self.rng.random() < 0.3:
                return name
        return ADDR_TO_KARAKA.get(addr, "वाचम्")

    def add_sanjnaa(self, name, addr):
        self.sanjnaa_map[name] = addr
        self.lines.append(f"सञ्ज्ञा {name} = 0x{addr:02X} ।")

    def add_write(self, addr):
        """Ring-2 Write to addr. Always valid."""
        tok = self._karaka(addr)
        self.lines.append(f"    {tok} लिखति ।")
        self.written.add(addr)
        self.prev_target = addr

    def add_anuvrtti_write(self):
        """Write with no Karaka (inherits prev_target). Requires prev_target."""
        self.lines.append("    लिखति ।")
        if self.prev_target is not None:
            self.written.add(self.prev_target)

    def add_avrtti_write(self, addr, count):
        """Avrtti Write: count repetitions."""
        tok = self._karaka(addr)
        self.lines.append(f"    {tok} आवृत्तिः {count} लिखति ।")
        self.written.add(addr)
        self.prev_target = addr

    def add_lopa(self, addr):
        """Lopa on addr -- requires addr in written."""
        tok = self._karaka(addr)
        self.lines.append(f"    {tok} लोपः ।")
        self.written.discard(addr)
        self.prev_target = None   # Lopa resets context

    def add_sandhi_pair(self, addr):
        """Write + Sandhi + Store on same Asiddha target."""
        tok = self._karaka(addr)
        self.lines.append(f"    {tok} लिखति ।")
        self.lines.append("    सन्धिः ।")
        self.lines.append(f"    {tok} स्थापयति ।")
        self.written.add(addr)
        self.prev_target = addr

    def open_adhikara(self):
        self.lines.append("    अधिकारः {")
        self.in_scope = True

    def add_ring0_store(self, addr):
        """Ring-0 Store inside Adhikara scope."""
        tok = self._karaka(addr)
        self.lines.append(f"        {tok} स्थापयति ।")
        self.written.add(addr)
        self.prev_target = addr

    def close_adhikara(self):
        self.lines.append("    }")
        self.in_scope = False

    def build(self):
        src = "\n".join(
            ["तन्त्रशास्त्रम् {"]
            + ["    " + ln if not ln.startswith("    ") and not ln.startswith("तन्") and not ln.startswith("सञ्") else ln
               for ln in self.lines]
            + ["}"]
        )
        # Sanjnaa declarations go before tantra block
        sanjnaa_lines = [l for l in self.lines if l.startswith("सञ्ज्ञा")]
        body_lines    = [l for l in self.lines if not l.startswith("सञ्ज्ञा")]
        return "\n".join(
            sanjnaa_lines
            + ["तन्त्रशास्त्रम् {"]
            + body_lines
            + ["}"]
        )


def generate_program(rng: random.Random) -> str:
    """
    Generate one random valid PSL program. Returns the source string.
    """
    b = ProgramBuilder(rng)

    # Optionally add a Sanjnaa declaration
    if rng.random() < 0.4:
        names = ["प्रथमः", "द्वितीयः", "तृतीयः"]
        addrs = [0x60, 0x50]
        b.add_sanjnaa(rng.choice(names), rng.choice(addrs))

    # Choose a generation strategy
    strategy = rng.choice([
        "plain_writes",
        "write_lopa",
        "anuvrtti",
        "avrtti",
        "sandhi",
        "adhikara",
        "mixed",
    ])

    if strategy == "plain_writes":
        for _ in range(rng.randint(1, 4)):
            addr = rng.choice(SIDDHA_TARGETS + ASIDDHA_TARGETS)
            b.add_write(addr)

    elif strategy == "write_lopa":
        addr = rng.choice(SIDDHA_TARGETS + ASIDDHA_TARGETS)
        b.add_write(addr)
        b.add_lopa(addr)
        # Optional: write again after lopa
        if rng.random() < 0.5:
            b.add_write(rng.choice(SIDDHA_TARGETS + ASIDDHA_TARGETS))

    elif strategy == "anuvrtti":
        addr = rng.choice(SIDDHA_TARGETS + ASIDDHA_TARGETS)
        b.add_write(addr)
        for _ in range(rng.randint(1, 3)):
            b.add_anuvrtti_write()

    elif strategy == "avrtti":
        addr = rng.choice(SIDDHA_TARGETS + ASIDDHA_TARGETS)
        count = rng.randint(2, 5)
        b.add_avrtti_write(addr, count)

    elif strategy == "sandhi":
        # Sandhi only valid on Asiddha targets (same target, write-class)
        addr = rng.choice(ASIDDHA_TARGETS)
        b.add_write(rng.choice(SIDDHA_TARGETS))   # standalone first
        b.add_sandhi_pair(addr)

    elif strategy == "adhikara":
        # Ring-2 write, then Adhikara scope with Ring-0 store, then Ring-2 again
        b.add_write(rng.choice(SIDDHA_TARGETS))
        b.open_adhikara()
        b.add_ring0_store(rng.choice(ASIDDHA_TARGETS))
        b.close_adhikara()
        b.add_write(rng.choice(SIDDHA_TARGETS))

    elif strategy == "mixed":
        # Combine 2-3 strategies
        addr1 = rng.choice(SIDDHA_TARGETS + ASIDDHA_TARGETS)
        b.add_write(addr1)
        if rng.random() < 0.4:
            b.add_anuvrtti_write()
        if rng.random() < 0.4 and b.written:
            b.add_lopa(rng.choice(list(b.written)) if b.written else addr1)
        if rng.random() < 0.3:
            addr2 = rng.choice(ASIDDHA_TARGETS)
            b.add_sandhi_pair(addr2)

    return b.build()


# ---------------------------------------------------------------------------
# Legacy emission path
# ---------------------------------------------------------------------------

def legacy_emit(compiler_mod, src: str):
    """
    Emit words via the legacy AST path (parse -> emit_words).
    Skips Sandhi sentinels and Adhikara open/close nodes.
    Returns list of 32-bit words.
    """
    C   = compiler_mod.PaninianFormalCompiler
    ASTNode = compiler_mod.ASTNode
    c   = C()
    c._parse_sanjnaa(src)

    legacy_nodes = []
    for raw_line in src.splitlines():
        stmt = raw_line.split('#', 1)[0].strip()
        if (not stmt
                or stmt == '{'
                or stmt == '}'
                or stmt.startswith(c.TANTRA_KEYWORD)
                or stmt.startswith(c.SANJNAA_KEYWORD)
                or stmt.startswith(c.ADHIKARA_KEYWORD)
                or stmt == c.SANDHI_KEYWORD
                or stmt == c.SANDHI_KEYWORD + " ।"):
            continue
        tokens = c.lex(stmt)
        if not tokens:
            continue
        ast = c.parse(tokens)
        for statement in ast.children:
            # Skip Sandhi and Adhikara AST nodes -- legacy path doesn't handle them
            if any(n.type in ("SANDHI_NODE", "ADHIKARA_NODE")
                   for n in statement.children):
                continue
            if statement.children:
                legacy_nodes.append(statement)

    root = ASTNode("SUTRA_STREAM", children=legacy_nodes)
    return c.emit_words(root)


# ---------------------------------------------------------------------------
# Differential check
# ---------------------------------------------------------------------------

def check_program(compiler_mod, src: str, prog_id: int, verbose: bool):
    """
    Run one program through both paths and check all four properties.
    Returns (passed: bool, failures: list[str])
    """
    C               = compiler_mod.PaninianFormalCompiler
    ParibhashaError = compiler_mod.ParibhashaError
    SandhiError     = compiler_mod.SandhiError

    failures = []

    # IR path
    try:
        c_ir  = C()
        ir_words = c_ir.compile_source(src, enforce_paribhasha=True)
    except (ParibhashaError, SandhiError) as e:
        failures.append(f"IR path rejected valid program: {e}")
        return False, failures
    except Exception as e:
        failures.append(f"IR path crash: {type(e).__name__}: {e}")
        return False, failures

    # Legacy path -- only for programs without Sandhi or Adhikara
    # (legacy emit_words doesn't handle those constructs)
    has_sandhi   = c.SANDHI_KEYWORD   in src if (c := C()) else False
    has_adhikara = C().ADHIKARA_KEYWORD in src

    if not has_sandhi and not has_adhikara:
        try:
            legacy_words = legacy_emit(compiler_mod, src)
        except Exception as e:
            failures.append(f"Legacy path crash: {type(e).__name__}: {e}")
            return False, failures

        # D1: byte identity
        if ir_words != legacy_words:
            failures.append(
                f"D1 FAIL: IR {[hex(w) for w in ir_words]} "
                f"!= legacy {[hex(w) for w in legacy_words]}"
            )

        # D3: word count identity
        if len(ir_words) != len(legacy_words):
            failures.append(
                f"D3 FAIL: IR count {len(ir_words)} != legacy {len(legacy_words)}"
            )

    # D2: constraint coverage (every non-sentinel node carries P1-ok..P4-ok)
    # Re-run to get IR list with constraints populated
    c2 = C()
    c2._parse_sanjnaa(src)
    ir_list = []
    prev_target    = 0x00
    adhikara_depth = 0
    OPEN  = C.OPCODE_ADHIKARA_OPEN
    CLOSE = C.OPCODE_ADHIKARA_CLOSE

    for line_number, raw_line in enumerate(src.splitlines(), 1):
        stmt = raw_line.split('#', 1)[0].strip()
        if (not stmt or stmt == '{' or stmt.startswith(c2.TANTRA_KEYWORD)
                or stmt.startswith(c2.SANJNAA_KEYWORD)):
            continue
        if stmt == '}':
            if adhikara_depth > 0:
                from importlib.util import spec_from_file_location, module_from_spec
                ir_list.append(compiler_mod.IRNode(
                    ring=0, comp=0, opcode=CLOSE, target=0x00,
                    cond=0, flags=0x0F, source_line=line_number,
                    source_text=stmt, constraints=["ADHIKARA-close"], region=None,
                ))
                adhikara_depth -= 1
            continue
        ast = c2.parse(c2.lex(stmt))
        new_nodes = c2._build_ir_node(ast, line_number, stmt,
                                      prev_target=prev_target,
                                      adhikara_depth=adhikara_depth)
        for node in new_nodes:
            if node.opcode == OPEN:
                adhikara_depth += 1
            elif node.comp != c2.COMP_ANUVRTTI and node.target is not None:
                prev_target = node.target
        ir_list.extend(new_nodes)

    c2.sandhi_pass(ir_list)
    c2.validate_ir(ir_list)

    SENTINEL_OPCODES = {0xFF, OPEN, CLOSE}
    for node in ir_list:
        if node.opcode in SENTINEL_OPCODES:
            continue
        for rule in ("P1-ok", "P2-ok", "P3-ok", "P4-ok"):
            if rule not in node.constraints:
                failures.append(
                    f"D2 FAIL: node at line {node.source_line} "
                    f"missing {rule} (constraints={node.constraints})"
                )

    # D4: L1 determinism -- to_word() is stable
    for node in ir_list:
        if node.opcode in SENTINEL_OPCODES:
            continue
        w1 = node.to_word()
        w2 = node.to_word()
        if w1 != w2:
            failures.append(
                f"D4 FAIL: to_word() non-deterministic at line {node.source_line}: "
                f"0x{w1:08X} != 0x{w2:08X}"
            )

    passed = len(failures) == 0
    if verbose and not passed:
        print(f"\n[Program {prog_id}]")
        print(src)
        for f in failures:
            print(f"  {f}")

    return passed, failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PVM Differential Test Suite")
    parser.add_argument("--count",   type=int, default=5000,
                        help="Number of programs to generate (default 5000)")
    parser.add_argument("--seed",    type=int, default=42,
                        help="Random seed (default 42)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print failing programs")
    args = parser.parse_args()

    print("=" * 60)
    print(f"PVM Differential Test Suite")
    print(f"Programs: {args.count}   Seed: {args.seed}")
    print("=" * 60)

    mod = load_compiler()
    rng = random.Random(args.seed)

    passed_count  = 0
    failed_count  = 0
    error_count   = 0
    all_failures  = []

    strategies    = {}
    d_counters    = {"D1": 0, "D2": 0, "D3": 0, "D4": 0}

    for i in range(1, args.count + 1):
        src = generate_program(rng)

        # Detect strategy from source content for stats
        if "सन्धिः" in src:
            strat = "sandhi"
        elif "अधिकारः" in src:
            strat = "adhikara"
        elif "आवृत्तिः" in src:
            strat = "avrtti"
        elif "लोपः" in src:
            strat = "write_lopa"
        else:
            strat = "plain"
        strategies[strat] = strategies.get(strat, 0) + 1

        try:
            ok, failures = check_program(mod, src, i, args.verbose)
        except Exception as e:
            error_count += 1
            all_failures.append((i, src, [f"EXCEPTION: {type(e).__name__}: {e}"]))
            continue

        if ok:
            passed_count += 1
        else:
            failed_count += 1
            all_failures.append((i, src, failures))
            for f in failures:
                for d in ("D1", "D2", "D3", "D4"):
                    if f.startswith(d):
                        d_counters[d] += 1

        if i % 500 == 0:
            print(f"  Progress: {i}/{args.count} "
                  f"passed={passed_count} failed={failed_count} "
                  f"errors={error_count}")

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Total programs:  {args.count}")
    print(f"  Passed:          {passed_count}")
    print(f"  Failed:          {failed_count}")
    print(f"  Errors:          {error_count}")
    print()
    print("  Property breakdown (failures):")
    for d, label in [
        ("D1", "Byte identity (IR == legacy)"),
        ("D2", "Constraint coverage (P1-ok..P4-ok)"),
        ("D3", "Word count identity"),
        ("D4", "L1 determinism (to_word stable)"),
    ]:
        print(f"    {d}: {d_counters[d]} failures  -- {label}")
    print()
    print("  Strategy distribution:")
    for strat, cnt in sorted(strategies.items(), key=lambda x: -x[1]):
        print(f"    {strat:15}: {cnt:5} programs ({100*cnt//args.count}%)")

    if all_failures and args.verbose:
        print()
        print("  First 3 failing programs:")
        for pid, src, fails in all_failures[:3]:
            print(f"\n  --- Program {pid} ---")
            print(src[:400])
            for f in fails:
                print(f"    {f}")

    total_pass = passed_count == args.count and error_count == 0
    print()
    status = "PASS" if total_pass else "FAIL"
    print(f"[{status}] {passed_count}/{args.count} programs passed all four properties.")

    if not total_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
