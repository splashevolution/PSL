#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pvm_trace_visualizer.py -- PSL compilation pipeline trace

Shows every stage of the Paninian System Language compiler pipeline for a
given .pvm source file:

    Stage 0: SOURCE          -- raw PSL source
    Stage 1: SANJNAA TABLE   -- symbol table after first pass
    Stage 2: RAW IR          -- IRNodes before sandhi_pass
    Stage 3: SANDHI IR       -- IRNodes after sandhi_pass (fused pairs marked)
    Stage 4: VALIDATED IR    -- IRNodes after validate_ir (constraints populated)
    Stage 5: ABI BINARY      -- final 32-bit words + byte layout

Diffs between stages are highlighted with >> markers.

Usage:
    python3 -B pvm_trace_visualizer.py <source.pvm> [options]

Options:
    --compact       Omit per-field breakdowns in IR stages
    --no-color      Disable ANSI color output
    --stage N       Show only stage N (0-5)
    --all-pvms      Trace all .pvm files in the current directory

Examples:
    python3 -B pvm_trace_visualizer.py sandhi_core.pvm
    python3 -B pvm_trace_visualizer.py adhikara_core.pvm --stage 3
    python3 -B pvm_trace_visualizer.py --all-pvms --compact
"""

import argparse
import importlib.util
import struct
import sys
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

USE_COLOR = True

def _c(code, text):
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def bold(t):    return _c("1",    t)
def dim(t):     return _c("2",    t)
def green(t):   return _c("32",   t)
def yellow(t):  return _c("33",   t)
def cyan(t):    return _c("36",   t)
def magenta(t): return _c("35",   t)
def red(t):     return _c("31",   t)
def blue(t):    return _c("34",   t)
def white(t):   return _c("37",   t)


# ---------------------------------------------------------------------------
# Compiler loader
# ---------------------------------------------------------------------------

def load_compiler():
    spec = importlib.util.spec_from_file_location(
        "paninian_compiler", ROOT / "src/utils/paninian_compiler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

STAGE_LABELS = [
    "SOURCE",
    "SANJNAA TABLE",
    "RAW IR",
    "SANDHI IR",
    "VALIDATED IR",
    "ABI BINARY",
]

OPCODE_NAMES = {
    0x00: "Lopa",
    0x05: "Write",
    0x06: "Read",
    0xCC: "Store",
    0xAA: "ADHIKARA_OPEN",
    0xBB: "ADHIKARA_CLOSE",
    0xFF: "SANDHI-sentinel",
}

COMP_NAMES = {
    0x0: "explicit",
    0x1: "anuvrtti",
}

FLAG_NAMES = {
    0xF: "standard",
    0xE: "SANDHI-FIRST",
}

COND_NAMES = {
    0x0: "unconditional",
    0x1: "utsarga",
    0x2: "apavada",
}

RING_NAMES = {
    0x0: "Ring₀",
    0x2: "Ring₂",
}


def _opcode_name(op):
    return OPCODE_NAMES.get(op, f"0x{op:02X}")

def _comp_name(comp):
    if comp in COMP_NAMES:
        return COMP_NAMES[comp]
    return f"avrtti×{comp}"

def _field_color(name, value):
    """Color-code a field value by semantic importance."""
    if name == "ring":
        return red(f"Ring₀") if value == 0 else green(f"Ring₂")
    if name == "opcode":
        if value == 0xAA or value == 0xBB:
            return magenta(f"0x{value:02X} ({_opcode_name(value)})")
        if value == 0xFF:
            return yellow(f"0x{value:02X} (sentinel)")
        if value == 0x00:
            return red(f"0x{value:02X} (Lopa)")
        return cyan(f"0x{value:02X} ({_opcode_name(value)})")
    if name == "comp":
        if value == 0x1:
            return yellow(f"0x{value:X} ({_comp_name(value)})")
        if value > 1:
            return yellow(f"0x{value:X} (avrtti×{value})")
        return dim(f"0x{value:X} (explicit)")
    if name == "flags":
        if value == 0xE:
            return bold(magenta(f"0x{value:X} (SANDHI-FIRST)"))
        return dim(f"0x{value:X} (standard)")
    if name == "sandhi_fused":
        return bold(magenta("True")) if value else dim("False")
    if name == "in_adhikara":
        return bold(red("True")) if value else dim("False")
    return str(value)


def _node_summary(node, idx, compact=False, changed_fields=None):
    """Format one IRNode as a single display block."""
    changed_fields = changed_fields or set()

    tgt_str = f"0x{node.target:02X}" if node.target is not None else "⊥"
    op_str  = _opcode_name(node.opcode)
    ring_str = RING_NAMES.get(node.ring, str(node.ring))

    # One-line summary
    marker = bold(yellow(">> ")) if changed_fields else "   "
    word = node.to_word()

    line1 = (
        f"{marker}"
        f"{dim(f'[{idx}]'):4s} "
        f"line {node.source_line:<3d}  "
        f"{_field_color('ring', node.ring):<6s}  "
        f"{_field_color('opcode', node.opcode):<40s}  "
        f"target={cyan(tgt_str):<8s}  "
        f"word={bold(white(f'0x{word:08X}'))}"
    )

    lines = [line1]

    if not compact:
        # Detailed field breakdown
        fields = [
            ("comp",        _comp_name(node.comp),
                            yellow if node.comp != 0 else dim),
            ("flags",       FLAG_NAMES.get(node.flags, f"0x{node.flags:X}"),
                            bold if node.flags == 0xE else dim),
            ("cond",        COND_NAMES.get(node.cond, str(node.cond)),
                            yellow if node.cond != 0 else dim),
            ("sandhi_fused", str(node.sandhi_fused),
                            lambda t: bold(magenta(t)) if node.sandhi_fused else dim(t)),
            ("in_adhikara", str(node.in_adhikara),
                            lambda t: bold(red(t)) if node.in_adhikara else dim(t)),
        ]
        parts = []
        for fname, fval, fcolor in fields:
            marker2 = bold(yellow("*")) if fname in changed_fields else " "
            parts.append(f"  {marker2} {dim(fname+'=')} {fcolor(fval)}")
        if parts:
            lines.append("         " + "  ".join(parts))
        if node.constraints:
            lines.append(f"         {dim('constraints:')} {green(', '.join(node.constraints))}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def _clone_ir(ir_list):
    """Deep-copy an IR list (fields only — constraints and flags)."""
    return [copy.copy(n) for n in ir_list]


def _diff_fields(a, b):
    """Return set of field names that differ between two IRNodes."""
    changed = set()
    for f in ("ring", "comp", "opcode", "target", "cond", "flags",
              "sandhi_fused", "in_adhikara"):
        if getattr(a, f) != getattr(b, f):
            changed.add(f)
    if set(a.constraints) != set(b.constraints):
        changed.add("constraints")
    return changed


def run_pipeline_stages(compiler_mod, source: str):
    """
    Run the full compilation pipeline and return a dict of stages.
    Each stage is either a string, a list of IRNodes, or a list of words.
    Returns None if compilation fails, plus the error.
    """
    C = compiler_mod.PaninianFormalCompiler
    ParibhashaError = compiler_mod.ParibhashaError
    SandhiError = compiler_mod.SandhiError

    stages = {}

    # Stage 0: source
    stages[0] = source

    c = C()

    # Stage 1: Sanjnaa table
    try:
        c._parse_sanjnaa(source)
        stages[1] = dict(c.sanjnaa_table)
    except Exception as e:
        return stages, f"Sanjnaa parse error: {e}"

    # Build raw IR (pre-sandhi, pre-validate)
    ir_list_raw = []
    prev_target = 0x00
    adhikara_depth = 0
    try:
        for line_number, raw_line in enumerate(source.splitlines(), 1):
            stmt = raw_line.split("#", 1)[0].strip()
            if (not stmt or stmt == "{"
                    or stmt.startswith(c.TANTRA_KEYWORD)
                    or stmt.startswith(c.SANJNAA_KEYWORD)):
                continue
            if stmt == "}":
                if adhikara_depth > 0:
                    ir_list_raw.append(compiler_mod.IRNode(
                        ring=0, comp=0, opcode=c.OPCODE_ADHIKARA_CLOSE,
                        target=0x00, cond=0, flags=c.FLAG_IMMEDIATE_LOPA,
                        source_line=line_number, source_text=stmt,
                        constraints=[], region=None,
                    ))
                    adhikara_depth -= 1
                continue
            stmt_ast = c.parse(c.lex(stmt))
            new_nodes = c._build_ir_node(
                stmt_ast, line_number, stmt,
                prev_target=prev_target, adhikara_depth=adhikara_depth
            )
            for node in new_nodes:
                if node.opcode == c.OPCODE_ADHIKARA_OPEN:
                    adhikara_depth += 1
                elif node.comp != c.COMP_ANUVRTTI and node.target is not None:
                    prev_target = node.target
            ir_list_raw.extend(new_nodes)
    except Exception as e:
        return stages, f"IR build error: {e}"

    stages[2] = _clone_ir(ir_list_raw)

    # Stage 3: after sandhi_pass
    ir_list_sandhi = _clone_ir(ir_list_raw)
    try:
        c2 = C()
        c2._parse_sanjnaa(source)
        c2.sandhi_pass(ir_list_sandhi)
        stages[3] = _clone_ir(ir_list_sandhi)
    except SandhiError as e:
        stages[3] = e
        return stages, str(e)
    except Exception as e:
        return stages, f"Sandhi pass error: {e}"

    # Stage 4: after validate_ir
    ir_list_validated = _clone_ir(ir_list_sandhi)
    try:
        c2.validate_ir(ir_list_validated)
        stages[4] = _clone_ir(ir_list_validated)
    except ParibhashaError as e:
        stages[4] = e
        return stages, str(e)
    except Exception as e:
        return stages, f"Validation error: {e}"

    # Stage 5: ABI binary
    try:
        words = c2.emit_from_ir(ir_list_validated)
        stages[5] = words
    except Exception as e:
        return stages, f"Emission error: {e}"

    return stages, None


# ---------------------------------------------------------------------------
# Display functions
# ---------------------------------------------------------------------------

def _banner(title, width=72):
    bar = "─" * width
    print()
    print(bold(cyan(f"┌{bar}┐")))
    pad = (width - len(title)) // 2
    print(bold(cyan("│")) + " " * pad + bold(white(title)) + " " * (width - pad - len(title)) + bold(cyan("│")))
    print(bold(cyan(f"└{bar}┘")))


def _stage_header(n, label, subtitle=""):
    tag = bold(yellow(f"STAGE {n}"))
    print(f"\n{tag}  {bold(label)}")
    if subtitle:
        print(f"       {dim(subtitle)}")
    print(dim("  " + "─" * 68))


def show_stage_0(source):
    _stage_header(0, "SOURCE", "Raw PSL source text")
    for i, line in enumerate(source.splitlines(), 1):
        print(f"  {dim(f'{i:3d}:')} {white(line)}")


def show_stage_1(sanjnaa_table):
    _stage_header(1, "SANJNAA TABLE", "Compile-time symbol table (first pass)")
    if not sanjnaa_table:
        print(f"  {dim('(empty — no सञ्ज्ञा declarations)')}")
    else:
        for name, meta in sanjnaa_table.items():
            addr = meta.get("addr", "?")
            role = meta.get("role", "?")
            print(f"  {cyan(name):<24s}  →  addr={bold(white(f'0x{addr:02X}'))}  role={yellow(role)}")


def show_stage_2(ir_raw, compact=False):
    _stage_header(2, "RAW IR", "IRNodes produced by _build_ir_node() — before any transforms")
    if not ir_raw:
        print(f"  {dim('(empty)')}")
        return
    for i, node in enumerate(ir_raw):
        print(_node_summary(node, i, compact=compact))


def show_stage_3(ir_raw, ir_sandhi, compact=False):
    _stage_header(3, "SANDHI IR",
        "After sandhi_pass(): sentinels consumed, SANDHI-FIRST flags set")

    if isinstance(ir_sandhi, Exception):
        print(f"  {red('SandhiError:')} {ir_sandhi}")
        return

    # Build index map: raw index → sandhi index (sentinels removed)
    # Show removals and changes
    raw_by_line = {n.source_line: n for n in ir_raw}

    removed_lines = set()
    for n in ir_raw:
        if n.opcode == 0xFF:
            removed_lines.add(n.source_line)

    print(f"  {dim(f'Raw nodes: {len(ir_raw)}')}  →  "
          f"{dim(f'Sandhi nodes: {len(ir_sandhi)}')}  "
          f"({yellow(f'{len(ir_raw) - len(ir_sandhi)} sentinel(s) consumed')})")
    print()

    for i, node in enumerate(ir_sandhi):
        raw_node = raw_by_line.get(node.source_line)
        changed = _diff_fields(raw_node, node) if raw_node else set()
        print(_node_summary(node, i, compact=compact, changed_fields=changed))

    if removed_lines:
        print()
        for line in sorted(removed_lines):
            print(f"  {bold(yellow('>>'))}"
                  f" {dim(f'line {line}:')} {yellow('SANDHI sentinel consumed — not emitted to binary')}")


def show_stage_4(ir_sandhi, ir_validated, compact=False):
    _stage_header(4, "VALIDATED IR",
        "After validate_ir(): Paribhāṣā constraints (P1–P4) annotated")

    if isinstance(ir_sandhi, Exception):
        print(f"  {red('(skipped — sandhi pass failed)')}")
        return
    if isinstance(ir_validated, Exception):
        print(f"  {red('ParibhashaError:')} {ir_validated}")
        return

    sandhi_by_line = {n.source_line: n for n in ir_sandhi}

    for i, node in enumerate(ir_validated):
        prev = sandhi_by_line.get(node.source_line)
        changed = _diff_fields(prev, node) if prev else {"constraints"}
        print(_node_summary(node, i, compact=compact, changed_fields=changed))


def show_stage_5(words, compact=False):
    _stage_header(5, "ABI BINARY",
        "Final 32-bit big-endian words → byte layout")

    if not words:
        print(f"  {dim('(empty)')}")
        return

    print(f"  {dim(f'{len(words)} word(s) × 4 bytes = {len(words)*4} bytes total')}")
    print()

    for idx, w in enumerate(words):
        ring   = (w >> 28) & 0xF
        comp   = (w >> 24) & 0xF
        opcode = (w >> 16) & 0xFF
        target = (w >>  8) & 0xFF
        flags  = (w >>  4) & 0xF
        cond   =  w        & 0xF

        b = struct.pack(">I", w)
        byte_str = " ".join(f"{byte:02X}" for byte in b)

        op_label  = _opcode_name(opcode)
        ring_label = RING_NAMES.get(ring, str(ring))

        print(
            f"  {dim(f'[{idx}]')}  "
            f"{bold(white(f'0x{w:08X}'))}  "
            f"bytes=[{cyan(byte_str)}]  "
            f"{_field_color('ring', ring):<8s}  "
            f"{_field_color('opcode', opcode):<42s}  "
            f"tgt={cyan(f'0x{target:02X}')}"
        )

        if not compact:
            comp_label = _comp_name(comp)
            flag_label = FLAG_NAMES.get(flags, f"0x{flags:X}")
            cond_label = COND_NAMES.get(cond, str(cond))
            print(
                f"         {dim('ring=')}  {dim(f'{ring:04b}b')}  "
                f"{dim('comp=')} {dim(f'{comp:04b}b')} ({yellow(comp_label)})  "
                f"{dim('op=')} {dim(f'{opcode:08b}b')}  "
                f"{dim('tgt=')} {dim(f'{target:08b}b')}  "
                f"{dim('flags=')} {dim(f'{flags:04b}b')} ({magenta(flag_label)})  "
                f"{dim('cond=')} {dim(f'{cond:04b}b')} ({yellow(cond_label)})"
            )

    print()
    # Hex dump
    print(f"  {dim('Hex dump (big-endian byte stream):')}")
    all_bytes = b"".join(struct.pack(">I", w) for w in words)
    hex_row = " ".join(f"{b:02X}" for b in all_bytes)
    print(f"  {white(hex_row)}")


def show_pipeline_summary(source, stages, error, filename):
    """Print a compact one-line summary for --all-pvms mode."""
    n_words = len(stages.get(5, [])) if isinstance(stages.get(5), list) else 0
    n_ir    = len(stages.get(4, [])) if isinstance(stages.get(4), list) else 0
    if error:
        status = red("FAIL")
        detail = red(error[:60])
    else:
        status = green("PASS")
        detail = dim(f"{n_ir} IR nodes → {n_words} words")
    print(f"  {status}  {white(filename):<40s}  {detail}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def trace_file(path: Path, args, compiler_mod):
    source = path.read_text(encoding="utf-8")

    if not args.all_pvms:
        _banner(f"PVM IR TRACE — {path.name}")

    stages, error = run_pipeline_stages(compiler_mod, source)

    if args.all_pvms:
        show_pipeline_summary(source, stages, error, path.name)
        return

    only = args.stage

    if only is None or only == 0:
        show_stage_0(stages[0])
    if only is None or only == 1:
        show_stage_1(stages.get(1, {}))
    if only is None or only == 2:
        show_stage_2(stages.get(2, []), compact=args.compact)
    if only is None or only == 3:
        show_stage_3(
            stages.get(2, []),
            stages.get(3, []),
            compact=args.compact
        )
    if only is None or only == 4:
        show_stage_4(
            stages.get(3, []),
            stages.get(4, []),
            compact=args.compact
        )
    if only is None or only == 5:
        show_stage_5(stages.get(5, []), compact=args.compact)

    print()
    if error:
        print(bold(red(f"  ✗ Compilation stopped: {error}")))
    else:
        words = stages.get(5, [])
        ir    = stages.get(4, [])
        sentinels = sum(1 for n in ir
                        if hasattr(n, 'opcode')
                        and n.opcode in (0xAA, 0xBB))
        real_nodes = len(ir) - sentinels
        print(bold(green(
            f"  ✓ {path.name}: "
            f"{real_nodes} IR instruction(s) + {sentinels} sentinel(s) "
            f"→ {len(words)} ABI word(s)"
        )))


def main():
    global USE_COLOR

    parser = argparse.ArgumentParser(
        description="PSL compilation pipeline trace visualizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("source", nargs="?", help=".pvm source file")
    parser.add_argument("--compact",   action="store_true",
                        help="Omit per-field breakdowns")
    parser.add_argument("--no-color",  action="store_true",
                        help="Disable ANSI color output")
    parser.add_argument("--stage",     type=int, choices=range(6),
                        help="Show only stage N (0-5)")
    parser.add_argument("--all-pvms",  action="store_true",
                        help="Trace all .pvm files in current directory")
    args = parser.parse_args()

    if args.no_color:
        USE_COLOR = False

    if not args.source and not args.all_pvms:
        parser.print_help()
        sys.exit(1)

    compiler_mod = load_compiler()

    if args.all_pvms:
        pvms = sorted(ROOT.glob("*.pvm"))
        if not pvms:
            print(red("No .pvm files found in current directory."))
            sys.exit(1)
        _banner("PVM IR TRACE — ALL .pvm FILES")
        print()
        for path in pvms:
            trace_file(path, args, compiler_mod)
        print()
    else:
        path = Path(args.source)
        if not path.exists():
            print(red(f"File not found: {path}"))
            sys.exit(1)
        trace_file(path, args, compiler_mod)


if __name__ == "__main__":
    main()
