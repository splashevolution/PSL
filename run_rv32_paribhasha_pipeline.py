#!/usr/bin/env python3
"""
PVM Sprint 7 -- Paribhasha Compile-Time Constraint Enforcement Pipeline

Paribhasha (meta-rules) proves two complementary facts:

PART A -- Compiler rejection proof (local, no VM):
  The compiler receives three PSL programs, each containing one named
  Paribhasha violation. It must raise ParibhashaError for each, emitting
  zero bytes. The rejection itself is the proof.

  P1: Anuvrtti-at-start   -- compressed instruction with no prior context
  P2: Lopa-on-unwritten   -- erasing a target that was never written
  P3: Vrddhi-on-Siddha    -- Ring 0 privilege on a Siddha target (< 0x50)

PART B -- Valid-program firmware proof (QEMU RV32):
  A program that satisfies all three constraints is compiled and executed
  on freestanding RV32 firmware. The UART output asserts expected state.
  Together, Parts A and B prove that Paribhasha rejects exactly what is
  wrong and permits exactly what is right -- nothing more, nothing less.

Usage:
    $env:PVM_VM_PASSWORD = "<vm-password>"
    python -B run_rv32_paribhasha_pipeline.py
"""

import os
import sys
import importlib.util
import paramiko
from pathlib import Path


PASSWORD = os.environ.get("PVM_VM_PASSWORD")
if not PASSWORD:
    raise SystemExit("Set PVM_VM_PASSWORD before running the Paribhasha pipeline.")

ROOT        = Path(__file__).resolve().parent
REMOTE_ROOT = "/home/praveen/pvm_rv32_paribhasha"

FILES = [
    ("src/utils/paninian_compiler.py",      "src/utils/paninian_compiler.py"),
    ("src/utils/build_firmware.py",          "src/utils/build_firmware.py"),
    ("src/utils/embed_binary_image.py",      "src/utils/embed_binary_image.py"),
    ("src/rv32/start.S",                     "src/rv32/start.S"),
    ("src/rv32/linker.ld",                   "src/rv32/linker.ld"),
    ("src/rv32/pvm_firmware_paribhasha.c",   "src/rv32/pvm_firmware_paribhasha.c"),
    ("programs/paribhasha_valid_core.pvm",            "paribhasha_valid_core.pvm"),
]

# -----------------------------------------------------------------------
# Violation sources — each must be rejected with a named ParibhashaError
# -----------------------------------------------------------------------

P1_VIOLATION = """\
# P1: Anuvrtti-at-start
# First statement has no Karaka -- there is no prior context to inherit.
tantra {
    likh .
}
"""
# Use actual Devanagari for the real test
P1_SRC = """तन्त्रशास्त्रम् {
    लिखति ।
}"""

P2_SRC = """तन्त्रशास्त्रम् {
    वाचम् लोपः ।
}"""

P3_SRC = """तन्त्रशास्त्रम् {
    वाग्यन्त्रैः लिखति ।
}"""

# Expected ABI words for the valid program
EXPECTED_WORDS = [
    0x200530F0,   # Ring 2, Write, Vak (0x30) explicit       -- P1: has prior context (first, but explicit)
    0x210500F0,   # Ring 2, Write, 0x00 Anuvrtti             -- P1: context exists from prev write
    0x200030F0,   # Ring 2, Lopa,  Vak (0x30)                -- P2: Vak was written above
    0x00CC60F0,   # Ring 0, Store, Yantra (0x60) Asiddha     -- P3: 0x60 >= 0x50 (Asiddha)
]


def load_compiler():
    spec = importlib.util.spec_from_file_location(
        "paninian_compiler",
        str(ROOT / "src" / "utils" / "paninian_compiler.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(client, command):
    print(f"$ {command}")
    _, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode("utf-8", errors="replace")
    error  = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if output: print(output, end="" if output.endswith("\n") else "\n")
    if error:  print(error,  end="" if error.endswith("\n") else "\n")
    if status != 0:
        raise RuntimeError(f"Remote command failed (exit {status}): {command}")
    return output


# -----------------------------------------------------------------------
# PART A: Compiler rejection proof
# -----------------------------------------------------------------------

def part_a_rejection_proof():
    print("=" * 60)
    print("PART A: Paribhasha Compiler Rejection Proof")
    print("=" * 60)

    sc = load_compiler()
    PaninianFormalCompiler = sc.PaninianFormalCompiler
    ParibhashaError        = sc.ParibhashaError

    violations = [
        ("P1", "Anuvrtti-at-start",  P1_SRC),
        ("P2", "Lopa-on-unwritten",  P2_SRC),
        ("P3", "Vrddhi-on-Siddha",   P3_SRC),
    ]

    all_ok = True
    for expected_id, expected_name, src in violations:
        try:
            PaninianFormalCompiler().compile_source(src)
            print(f"  [FAIL] {expected_id} ({expected_name}): no error raised")
            all_ok = False
        except ParibhashaError as e:
            if e.rule_id == expected_id:
                print(f"  [PASS] {e.rule_id} ({e.rule_name}): correctly rejected")
            else:
                print(f"  [FAIL] Expected {expected_id} but got {e.rule_id}: {e}")
                all_ok = False
        except Exception as e:
            print(f"  [FAIL] {expected_id}: unexpected {type(e).__name__}: {e}")
            all_ok = False

    if not all_ok:
        raise RuntimeError("Part A failed: not all Paribhasha violations were correctly rejected.")

    print("\n[Part A OK] All three violations correctly rejected by compiler.\n")


# -----------------------------------------------------------------------
# PART B: Valid-program compiler verification + QEMU execution
# -----------------------------------------------------------------------

def part_b_valid_program_proof():
    print("=" * 60)
    print("PART B: Valid-Program Firmware Proof (RV32 QEMU)")
    print("=" * 60)

    # Step B1: Verify compiler output locally
    sc        = load_compiler()
    compiler  = sc.PaninianFormalCompiler()
    valid_src = (ROOT / "programs/paribhasha_valid_core.pvm").read_text(encoding="utf-8")
    words     = compiler.compile_source(valid_src)

    print("[Compiler Verification] Valid program:")
    print(f"  Compiled {len(words)} instruction(s)")
    all_ok = True
    for i, (got, want) in enumerate(zip(words, EXPECTED_WORDS)):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] Instr {i+1}: "
              f"got 0x{got:08X}  want 0x{want:08X}")
        if not ok:
            all_ok = False
    if len(words) != len(EXPECTED_WORDS):
        print(f"  [FAIL] Word count: got {len(words)}, want {len(EXPECTED_WORDS)}")
        all_ok = False
    if not all_ok:
        raise RuntimeError("Compiler produced wrong ABI words for valid program.")
    print("  [OK] All ABI words correct.\n")

    # Step B2: SSH to VM and run QEMU
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

    sftp = client.open_sftp()
    for local, remote in FILES:
        local_path = ROOT / local
        if not local_path.exists():
            raise FileNotFoundError(f"Local file missing: {local_path}")
        sftp.put(str(local_path), f"{REMOTE_ROOT}/{remote}")
        print(f"  [SFTP] {local} -> {REMOTE_ROOT}/{remote}")
    sftp.close()

    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/build_firmware.py paribhasha_valid_core.pvm pvm_paribhasha.bin")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/embed_binary_image.py pvm_paribhasha.bin src/rv32/pvm_image.h")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-gcc -march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles -Wall -Wextra -O2 "
        "-T src/rv32/linker.ld src/rv32/start.S src/rv32/pvm_firmware_paribhasha.c "
        "-Isrc/rv32 -o pvm_rv32_paribhasha.elf && "
        "riscv64-unknown-elf-size pvm_rv32_paribhasha.elf && "
        "riscv64-unknown-elf-objdump -h pvm_rv32_paribhasha.elf | grep -E '(text|rodata|bss)'")

    print("\n[QEMU] Executing Paribhasha valid-program firmware...\n")
    execution_output = run(
        client,
        f"cd {REMOTE_ROOT} && "
        "qemu-system-riscv32 -M virt -nographic -bios none -kernel pvm_rv32_paribhasha.elf")

    # Save evidence
    evidence_path = ROOT / "evidence" / "2026-05-23-rv32-paribhasha-proof.md"
    evidence_path.parent.mkdir(exist_ok=True)
    evidence_path.write_text(
        "# RV32 Paribhasha Proof Record -- Sprint 7\n\n"
        "## Claim Tested\n\n"
        "Paribhasha compile-time meta-rule enforcement:\n"
        "  (A) Three named violations are correctly rejected by the compiler.\n"
        "  (B) A valid program satisfying all constraints compiles and executes.\n\n"
        "## P1: Anuvrtti-at-start  [compiler rejected]\n"
        "## P2: Lopa-on-unwritten  [compiler rejected]\n"
        "## P3: Vrddhi-on-Siddha   [compiler rejected]\n\n"
        "## Expected ABI Words (valid program)\n\n```\n"
        + "\n".join(f"0x{w:08X}" for w in EXPECTED_WORDS)
        + "\n```\n\n"
        "## Execution Output\n\n```text\n"
        + execution_output.strip()
        + "\n```\n",
        encoding="utf-8",
    )
    print(f"\n[Evidence] Saved to {evidence_path}")

    checks = [
        ("Two Siddha writes (explicit + Anuvrtti)",  "siddha_writes=0x02"),
        ("Anuvrtti inherited once",                   "anuvrtti_inherited=0x01"),
        ("Lopa fired once",                           "lopa_erasures=0x01"),
        ("Asiddha Ring-0 store fired",                "asiddha_stores=0x01"),
        ("Vak zeroed after Lopa",                     "VAK_after_lopa=0x00"),
        ("Yantra shadow written",                     "YANTRA_shadow=0xFF"),
    ]
    all_passed = True
    print("\n[Verification]")
    for label, marker in checks:
        ok = marker in execution_output
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: '{marker}'")
        if not ok:
            all_passed = False

    client.close()

    if not all_passed:
        raise RuntimeError("Sprint 7 Part B: valid-program proof did not produce all expected outcomes.")

    print(
        "\n[Part B OK] Paribhasha valid-program firmware proof confirmed.\n"
        "  All three constraints satisfied. Firmware executed correctly on RV32 QEMU."
    )


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    part_a_rejection_proof()
    part_b_valid_program_proof()

    print("\n" + "=" * 60)
    print("SPRINT 7 COMPLETE: Paribhasha -- meta-rules proven.")
    print("  The compiler rejects exactly what is wrong.")
    print("  The firmware proves exactly what is permitted.")
    print("=" * 60)


if __name__ == "__main__":
    main()
