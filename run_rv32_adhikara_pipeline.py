#!/usr/bin/env python3
"""
PVM Sprint 10 -- Adhikara Privilege Scope Pipeline

Adhikara (Sanskrit: "authority / jurisdiction") -- a block-level declaration
that sets Ring 0 for all instructions within it, with automatic restoration
to Ring 2 on exit. The scope boundary is a first-class syntactic construct
enforced by the compiler at parse time.

New Paribhasha rule:
  P4: Ring0-outside-scope -- Ring 0 instruction outside an Adhikara block
      is a compile-time error. Use अधिकारः { ... } to declare scope.

New ABI opcodes:
  0xAA -- ADHIKARA_OPEN  (scope-enter sentinel)
  0xBB -- ADHIKARA_CLOSE (scope-exit sentinel)

PART A -- Compiler verification (local, no VM):
  1. adhikara_core.pvm compiles to exactly 5 ABI words:
       0x200530F0  Write Vak   (Ring2, outside scope)
       0x00AA00F0  ADHIKARA_OPEN
       0x00CC60F0  Store Yantra (Ring0, inside scope)
       0x00BB00F0  ADHIKARA_CLOSE
       0x200530F0  Write Vak   (Ring2, restored)
  2. P4 violation rejected (Ring-0 instruction outside scope)
  3. Ring-0 inside scope passes P4
  4. Prior sprint sources (sandhi, sanjnaa, lopa) compile unchanged

PART B -- Firmware proof (QEMU RV32):
  Firmware tracks scope_ring register. ADHIKARA_OPEN sets Ring0,
  ADHIKARA_CLOSE restores Ring2. UART markers:
    ring2_writes=0x02  adhikara_opens=0x01  adhikara_closes=0x01
    ring0_stores=0x01  scope_restored=0x01
    VAK_bus=0xFF  YANTRA_shadow=0xFF

Usage:
    $env:PVM_VM_PASSWORD = "<vm-password>"
    python -B run_rv32_adhikara_pipeline.py
"""

import os
import sys
import importlib.util
import paramiko
from pathlib import Path

PASSWORD = os.environ.get("PVM_VM_PASSWORD")
if not PASSWORD:
    raise SystemExit("Set PVM_VM_PASSWORD before running the Adhikara pipeline.")

ROOT        = Path(__file__).resolve().parent
REMOTE_ROOT = "/home/praveen/pvm_rv32_adhikara"

FILES = [
    ("src/utils/paninian_compiler.py",    "src/utils/paninian_compiler.py"),
    ("src/utils/build_firmware.py",        "src/utils/build_firmware.py"),
    ("src/utils/embed_binary_image.py",    "src/utils/embed_binary_image.py"),
    ("src/rv32/start.S",                   "src/rv32/start.S"),
    ("src/rv32/linker.ld",                 "src/rv32/linker.ld"),
    ("src/rv32/pvm_firmware_adhikara.c",   "src/rv32/pvm_firmware_adhikara.c"),
    ("programs/adhikara_core.pvm",                  "adhikara_core.pvm"),
]

EXPECTED_WORDS = [
    0x200530F0,   # Write Vak (Ring2, outside scope)
    0x00AA00F0,   # ADHIKARA_OPEN
    0x00CC60F0,   # Store Yantra (Ring0, inside scope)
    0x00BB00F0,   # ADHIKARA_CLOSE
    0x200530F0,   # Write Vak (Ring2, restored)
]

EXPECTED_MARKERS = [
    ("Ring2 write count (2)",  "ring2_writes=0x02"),
    ("Adhikara opens (1)",     "adhikara_opens=0x01"),
    ("Adhikara closes (1)",    "adhikara_closes=0x01"),
    ("Ring0 store count (1)",  "ring0_stores=0x01"),
    ("Scope restored (1)",     "scope_restored=0x01"),
    ("Vak bus written",        "VAK_bus=0xFF"),
    ("Yantra shadow written",  "YANTRA_shadow=0xFF"),
]

# -----------------------------------------------------------------------
# P4 violation source
# -----------------------------------------------------------------------

P4_VIOLATION = """तन्त्रशास्त्रम् {
    यन्त्रै स्थापयति ।
}"""

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def load_compiler():
    spec = importlib.util.spec_from_file_location(
        "paninian_compiler", ROOT / "src/utils/paninian_compiler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(client, cmd, desc=None):
    if desc:
        print(f"  [{desc}] $ {cmd[:80]}...")
    else:
        print(f"  $ {cmd[:100]}")
    _stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    rc  = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print("[stderr]", err.rstrip(), file=sys.stderr)
    if rc != 0:
        raise RuntimeError(f"Remote command failed (rc={rc}): {cmd[:80]}")
    return out


# -----------------------------------------------------------------------
# PART A: Local compiler verification
# -----------------------------------------------------------------------

def part_a_compiler_verification():
    print("=" * 60)
    print("PART A: Adhikara Compiler Verification")
    print("=" * 60)

    sc = load_compiler()
    Compiler        = sc.PaninianFormalCompiler
    ParibhashaError = sc.ParibhashaError

    # A1: ABI words
    print("\n[A1] Compiling adhikara_core.pvm ...")
    src   = (ROOT / "programs/adhikara_core.pvm").read_text(encoding="utf-8")
    words = Compiler().compile_source(src)
    descs = [
        "Write Vak   (Ring2, outside scope)",
        "ADHIKARA_OPEN",
        "Store Yantra (Ring0, inside scope)",
        "ADHIKARA_CLOSE",
        "Write Vak   (Ring2, restored)",
    ]

    all_ok = True
    print(f"  Compiled {len(words)} word(s) (expected {len(EXPECTED_WORDS)})")
    for i, (got, want, d) in enumerate(zip(words, EXPECTED_WORDS, descs)):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] Word {i+1}: 0x{got:08X}  {d}")
        if not ok:
            all_ok = False
    if len(words) != len(EXPECTED_WORDS):
        print(f"  [FAIL] count: got {len(words)}, want {len(EXPECTED_WORDS)}")
        all_ok = False
    if not all_ok:
        raise RuntimeError("[A1 FAILED]")
    print("  [OK] All ABI words correct.\n")

    # A2: P4 violation rejection
    print("[A2] P4 violation: Ring-0 outside scope ...")
    try:
        Compiler().compile_source(P4_VIOLATION)
        print("  [FAIL] no error raised")
        raise RuntimeError("[A2 FAILED]")
    except ParibhashaError as e:
        if e.rule_id == "P4":
            print(f"  [PASS] {e.rule_id} ({e.rule_name}): correctly rejected")
        else:
            print(f"  [FAIL] expected P4, got {e.rule_id}")
            raise RuntimeError("[A2 FAILED]")

    # A3: Same Ring-0 instruction inside scope passes
    print("\n[A3] Ring-0 inside scope passes P4 ...")
    inside_src = """तन्त्रशास्त्रम् {
    अधिकारः {
        यन्त्रै स्थापयति ।
    }
}"""
    try:
        w3 = Compiler().compile_source(inside_src)
        print(f"  [PASS] compiled {len(w3)} word(s) without error")
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")
        raise RuntimeError("[A3 FAILED]")

    # A4: Prior sprint binary identity
    print("\n[A4] Binary identity -- prior sprints unchanged ...")
    checks = [
        ("sandhi_core.pvm",  [0x200530F0, 0x200560E0, 0x20CC60F0]),
        ("sanjnaa_core.pvm", None),
        ("lopa_core.pvm",    None),
    ]
    for fname, expected in checks:
        try:
            src2  = (ROOT / fname).read_text(encoding="utf-8")
            words2 = Compiler().compile_source(src2)
            if expected is not None:
                ok = words2 == expected
                print(f"  [{'PASS' if ok else 'FAIL'}] {fname}")
                if not ok:
                    raise RuntimeError(f"[A4 FAILED] {fname}")
            else:
                print(f"  [PASS] {fname}: {len(words2)} words, no error")
        except RuntimeError:
            raise
        except Exception as e:
            print(f"  [FAIL] {fname}: {type(e).__name__}: {e}")
            raise RuntimeError(f"[A4 FAILED] {fname}")

    print("\n[Part A OK] Compiler verification complete.\n")


# -----------------------------------------------------------------------
# PART B: Firmware proof on RV32 QEMU
# -----------------------------------------------------------------------

def part_b_firmware_proof():
    print("=" * 60)
    print("PART B: Adhikara Firmware Proof (RV32 QEMU)")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        os.environ.get("PVM_VM_HOST", "127.0.0.1"),
        port=int(os.environ.get("PVM_VM_PORT", "2222")),
        username=os.environ.get("PVM_VM_USER", "praveen"),
        password=PASSWORD,
        timeout=10,
    )

    run(client, f"mkdir -p {REMOTE_ROOT}/src/utils {REMOTE_ROOT}/src/rv32 {REMOTE_ROOT}/evidence")

    print("\n[SFTP] Uploading files ...")
    sftp = client.open_sftp()
    for local, remote in FILES:
        lp = ROOT / local
        if not lp.exists():
            sftp.close(); client.close()
            raise FileNotFoundError(f"Missing: {lp}")
        sftp.put(str(lp), f"{REMOTE_ROOT}/{remote}")
        print(f"  [SFTP] {local}")
    sftp.close()
    print()

    print("[Build] adhikara_core.pvm -> pvm_adhikara.bin ...")
    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/build_firmware.py adhikara_core.pvm pvm_adhikara.bin",
        desc="build_firmware")

    print("\n[Embed] pvm_adhikara.bin -> src/rv32/pvm_image.h ...")
    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/embed_binary_image.py pvm_adhikara.bin src/rv32/pvm_image.h",
        desc="embed_binary")

    print("\n[Compile] Building pvm_rv32_adhikara.elf ...")
    run(client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-gcc "
        "-march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles "
        "-Wall -Wextra -O2 "
        "-T src/rv32/linker.ld "
        "src/rv32/start.S "
        "src/rv32/pvm_firmware_adhikara.c "
        "-Isrc/rv32 "
        "-o pvm_rv32_adhikara.elf",
        desc="gcc")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-size pvm_rv32_adhikara.elf && "
        "riscv64-unknown-elf-objdump -h pvm_rv32_adhikara.elf | "
        "grep -E '(text|rodata|bss)'")

    print("\n[QEMU] Executing Adhikara firmware on freestanding RV32 ...\n")
    execution_output = run(
        client,
        f"cd {REMOTE_ROOT} && "
        "qemu-system-riscv32 -M virt -nographic -bios none "
        "-kernel pvm_rv32_adhikara.elf",
    )

    # Save evidence
    evidence_path = ROOT / "evidence" / "2026-05-23-rv32-adhikara-proof.md"
    evidence_path.parent.mkdir(exist_ok=True)

    sc    = load_compiler()
    words = sc.PaninianFormalCompiler().compile_source(
        (ROOT / "programs/adhikara_core.pvm").read_text(encoding="utf-8")
    )

    evidence_path.write_text(
        "# RV32 Adhikara Proof Record -- Sprint 10\n\n"
        "## Concept\n\n"
        "Adhikara (privilege scope): a block-level declaration sets Ring 0 for\n"
        "all instructions within it, with automatic restoration to Ring 2 on exit.\n"
        "P4 Paribhasha rule: Ring-0 instruction outside an Adhikara block is a\n"
        "compile-time error.\n\n"
        "## Source Program\n\n"
        "```\n"
        + (ROOT / "programs/adhikara_core.pvm").read_text(encoding="utf-8").strip()
        + "\n```\n\n"
        "## ABI Words Emitted\n\n```\n"
        + "\n".join(
            f"0x{w:08X}  {d}"
            for w, d in zip(words, [
                "Write Vak (Ring2, outside scope)",
                "ADHIKARA_OPEN",
                "Store Yantra (Ring0, inside scope)",
                "ADHIKARA_CLOSE",
                "Write Vak (Ring2, restored)",
            ])
        )
        + "\n```\n\n"
        "## P4 Violation Rejected (Part A)\n\n"
        "- Ring-0 instruction outside Adhikara block -- correctly rejected\n\n"
        "## QEMU UART Output\n\n```text\n"
        + execution_output.strip()
        + "\n```\n",
        encoding="utf-8",
    )
    print(f"\n[Evidence] Saved to {evidence_path}")

    print("\n[Verification] Checking UART markers ...")
    all_passed = True
    for label, marker in EXPECTED_MARKERS:
        ok = marker in execution_output
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: '{marker}'")
        if not ok:
            all_passed = False

    client.close()

    if not all_passed:
        raise RuntimeError("Sprint 10 Part B: firmware did not emit all expected markers.")

    print(
        "\n[Part B OK] Adhikara firmware proof confirmed.\n"
        "  Scope opened, Ring-0 Store executed inside, Ring2 restored on close."
    )


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    part_a_compiler_verification()
    part_b_firmware_proof()

    print()
    print("=" * 60)
    print("SPRINT 10 COMPLETE: Adhikara -- privilege scope proven.")
    print("  ADHIKARA_OPEN/CLOSE bracket Ring-0 domains in the ABI.")
    print("  P4 rejects Ring-0 instructions outside declared scope.")
    print("  Firmware tracks scope_ring register, restores on exit.")
    print("=" * 60)


if __name__ == "__main__":
    main()
