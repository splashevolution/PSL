#!/usr/bin/env python3
"""Generate Lean conformance checks from canonical PSL compiler output.

The generated corpus includes the checked-in canonical programs plus a
deterministic family of sources from the currently formalized subset.

This is finite cross-language conformance evidence, not a universal proof that
the Python compiler implements the Lean semantics for every PSL source.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "utils"))

from paninian_compiler import PaninianFormalCompiler

CANONICAL_PROGRAMS = (
    "lopa_core.pvm",
    "sandhi_core.pvm",
    "paribhasha_valid_core.pvm",
    "key_lifecycle.pvm",
    "anuvritti_core.pvm",
    "adhikara_core.pvm",
    "boot_sequencer.pvm",
    "safety_interlock.pvm",
)


def lean_nat_list(words):
    return "[" + ", ".join(f"0x{w:08X}" for w in words) + "]"


def lean_ir_node(node):
    target = (
        "none"
        if node.target is None
        else f"some (fin256 0x{node.target:02X})"
    )
    return (
        "{ ring := fin16 0x%X, comp := fin16 0x%X, "
        "opcode := fin256 0x%02X, target := %s, "
        "cond := fin16 0x%X, flags := fin16 0x%X, "
        "in_adhikara := %s, sandhi_fused := %s }"
        % (
            node.ring,
            node.comp,
            node.opcode,
            target,
            node.cond,
            node.flags,
            "true" if node.in_adhikara else "false",
            "true" if node.sandhi_fused else "false",
        )
    )


def lean_ir_list(ir):
    if not ir:
        return "[]"
    body = ",\n    ".join(lean_ir_node(node) for node in ir)
    return "[\n    " + body + "\n  ]"


def lean_ident(label):
    safe = "".join(ch if ch.isalnum() else "_" for ch in label)
    return "pythonIR_" + safe


def emit_ir_certificate(lines, label, compiler, words):
    ir = compiler._last_ir
    name = lean_ident(label)
    lines.extend(
        [
            f"def {name} : List IRNode :=",
            f"  {lean_ir_list(ir)}",
            "",
            f"example : validateIRClosed {name} = true := by",
            "  native_decide",
            "",
            f"example : (lowerAll {name}).map ABIWord.toNat = {lean_nat_list(words)} := by",
            "  native_decide",
            "",
            f"example : validateEncodedClosed {lean_nat_list(words)} = true := by",
            "  native_decide",
            "",
        ]
    )


def generated_sources():
    """Yield deterministic valid sources from the proved control subset."""
    case = 0

    # Siddha lifecycle: explicit write, optional inherited writes, optional Lopa.
    for addr in (0x20, 0x30, 0x40):
        for inherited_count in (0, 1, 2):
            for do_lopa in (False, True):
                name = f"S{addr:02X}"
                body = [f"    {name} लिखति ।"]
                body.extend("    लिखति ।" for _ in range(inherited_count))
                if do_lopa:
                    body.append(f"    {name} लोपः ।")
                source = (
                    f"सञ्ज्ञा {name} = 0x{addr:02X} ।\n"
                    "तन्त्रशास्त्रम् {\n"
                    + "\n".join(body)
                    + "\n}\n"
                )
                yield f"generated_siddha_{case:03d}", source
                case += 1

    # Ring-2 Asiddha WRITE remains legal; no privileged operation involved.
    for addr in (0x50, 0x60, 0x70):
        for inherited_count in (0, 1, 2):
            name = f"A{addr:02X}"
            body = [f"    {name} लिखति ।"]
            body.extend("    लिखति ।" for _ in range(inherited_count))
            source = (
                f"सञ्ज्ञा {name} = 0x{addr:02X} ।\n"
                "तन्त्रशास्त्रम् {\n"
                + "\n".join(body)
                + "\n}\n"
            )
            yield f"generated_asiddha_write_{case:03d}", source
            case += 1

    # Scoped Store lifecycle with optional inherited Store and explicit Lopa.
    for addr in (0x50, 0x60, 0x70):
        for inherited_count in (0, 1, 2):
            for do_lopa in (False, True):
                name = f"P{addr:02X}"
                body = [f"        {name} स्थापयति ।"]
                body.extend("        स्थापयति ।" for _ in range(inherited_count))
                if do_lopa:
                    body.append(f"        {name} लोपः ।")
                source = (
                    f"सञ्ज्ञा {name} = 0x{addr:02X} ।\n"
                    "तन्त्रशास्त्रम् {\n"
                    "    अधिकारः {\n"
                    + "\n".join(body)
                    + "\n    }\n}\n"
                )
                yield f"generated_scoped_{case:03d}", source
                case += 1

    # Mixed status + privileged state + optional Sandhi + Lopa.
    for target in (0x50, 0x60, 0x70):
        for use_inherited in (False, True):
            for use_sandhi in (False, True):
                name = f"M{target:02X}"
                scoped = [f"        {name} स्थापयति ।"]
                if use_inherited:
                    scoped.append("        स्थापयति ।")
                if use_sandhi:
                    scoped.extend(
                        [
                            f"        {name} स्थापयति ।",
                            "        सन्धिः ।",
                            f"        {name} स्थापयति ।",
                        ]
                    )
                scoped.append(f"        {name} लोपः ।")
                source = (
                    f"सञ्ज्ञा STATUS = 0x20 ।\n"
                    f"सञ्ज्ञा {name} = 0x{target:02X} ।\n"
                    "तन्त्रशास्त्रम् {\n"
                    "    STATUS लिखति ।\n"
                    "    अधिकारः {\n"
                    + "\n".join(scoped)
                    + "\n    }\n"
                    "    STATUS लिखति ।\n"
                    "}\n"
                )
                yield f"generated_mixed_{case:03d}", source
                case += 1


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "lean" / "GeneratedConformance.lean"

    lines = [
        "import PSL.Semantics",
        "",
        "/-",
        "  AUTO-GENERATED by scripts/generate_lean_conformance.py.",
        "  Finite compiler/Lean conformance evidence; not a universal compiler proof.",
        "-/",
        "",
    ]

    all_words = set()
    emitted_programs = 0

    # Checked-in canonical examples. Export Python's final IR as a Lean value,
    # prove that Lean accepts it as a closed program, and independently check
    # that Lean lowering produces the exact numeric words emitted by Python.
    for name in CANONICAL_PROGRAMS:
        source = (ROOT / "programs" / name).read_text(encoding="utf-8")
        compiler = PaninianFormalCompiler()
        words = compiler.compile_source(source)
        all_words.update(words)
        emitted_programs += 1
        lines.append(f"-- {name}")
        emit_ir_certificate(lines, name, compiler, words)

    # Generated source corpus. Deduplicate identical binaries so Lean work is
    # proportional to semantic variety rather than template count.
    seen_word_streams = set()
    generated_count = 0
    for label, source in generated_sources():
        compiler = PaninianFormalCompiler()
        words = compiler.compile_source(source)
        key = tuple(words)
        if key in seen_word_streams:
            continue
        seen_word_streams.add(key)
        all_words.update(words)
        generated_count += 1
        emitted_programs += 1
        lines.append(f"-- {label}")
        emit_ir_certificate(lines, label, compiler, words)

    # Every distinct ABI word observed from Python must round-trip through the
    # Lean numeric decoder.
    for word in sorted(all_words):
        lines.extend(
            [
                f"example : ABIWord.toNat (decodeABIWord 0x{word:08X}) = 0x{word:08X} := by",
                "  native_decide",
                "",
            ]
        )

    output.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"generated {output}: {emitted_programs} accepted word streams "
        f"({len(CANONICAL_PROGRAMS)} checked-in + {generated_count} generated), "
        f"{len(all_words)} distinct ABI words, "
        f"{emitted_programs} Python-IR certificates"
    )


if __name__ == "__main__":
    main()
