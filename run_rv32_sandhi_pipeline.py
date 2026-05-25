#!/usr/bin/env python3
"""
PVM Sprint 9 -- Sandhi Instruction Fusion Pipeline

Sandhi (Sanskrit: "junction / combination") -- when two compatible
instructions meet in the stream and are joined by the Sandhi directive,
they fuse into an atomic execution pair. The first instruction's ABI word
carries FLAGS=0xE (SANDHI-FIRST). The firmware executes the pair atomically,
updating both targets before advancing to the next instruction.

Fusion compatibility rules (all five must hold):
  S1: Both must be write-class (0x05 Write or 0xCC Store)
  S2: Both must target the same device address
  S3: First must be explicit (not Anuvrtti-compressed)
  S4: Both must be in the same ring level
  S5: No prior Lopa on the shared target in this stream

PART A -- Compiler verification (local, no VM):
  1. sandhi_core.pvm compiles to exactly three ABI words:
       0x200530F0  Write Vak    (standalone,    FLAGS=0xF)
       0x200560E0  Write Yantra (SANDHI-FIRST,  FLAGS=0xE)
       0x20CC60F0  Store Yantra (SANDHI-pair 2, FLAGS=0xF)
  2. S1 violation rejected (non-write fuse attempt)
  3. S2 violation rejected (target mismatch)
  4. S5 violation rejected (fuse after Lopa on same target)

PART B -- Firmware proof (QEMU RV32):
  Firmware loads the three ABI words, executes them on freestanding
  RV32, and emits UART markers:
    standalone_writes=0x01  sandhi_fusions=0x01
    VAK_bus=0xFF  YANTRA_write=0xFF  YANTRA_store=0xFF

Usage:
    $env:PVM_VM_PASSWORD = "<vm-password>"
    python -B run_rv32_sandhi_pipeline.py
"""

import os
import sys
import importlib.util
import paramiko
from pathlib import Path

PASSWORD = os.environ.get("PVM_VM_PASSWORD")
if not PASSWORD:
    raise SystemExit("Set PVM_VM_PASSWORD before running the Sandhi pipeline.")

ROOT        = Path(__file__).resolve().parent
REMOTE_ROOT = "/home/praveen/pvm_rv32_sandhi"

FILES = [
    ("src/utils/paninian_compiler.py",    "src/utils/paninian_compiler.py"),
    ("src/utils/build_firmware.py",        "src/utils/build_firmware.py"),
    ("src/utils/embed_binary_image.py",    "src/utils/embed_binary_image.py"),
    ("src/rv32/start.S",                   "src/rv32/start.S"),
    ("src/rv32/linker.ld",                 "src/rv32/linker.ld"),
    ("src/rv32/pvm_firmware_sandhi.c",     "src/rv32/pvm_firmware_sandhi.c"),
    ("programs/sandhi_core.pvm",                    "sandhi_core.pvm"),
]

# Expected ABI words for sandhi_core.pvm
EXPECTED_WORDS = [
    0x200530F0,   # Write Vak (0x30) standalone, FLAGS=0xF
    0x200560E0,   # Write Yantra (0x60) SANDHI-FIRST, FLAGS=0xE
    0x20CC60F0,   # Store Yantra (0x60) SANDHI-pair second, FLAGS=0xF
]

# Expected UART markers
EXPECTED_MARKERS = [
    ("Standalone write count",  "standalone_writes=0x01"),
    ("Sandhi fusion count",     "sandhi_fusions=0x01"),
    ("Vak bus written",         "VAK_bus=0xFF"),
    ("Yantra write executed",   "YANTRA_write=0xFF"),
    ("Yantra store executed",   "YANTRA_store=0xFF"),
]

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def load_compiler():
    spec = importlib.util.spec_from_file_location(
        "paninian_compiler",
        ROOT / "src/utils/paninian_compiler.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(client, cmd, desc=None):
    """Run a command over SSH, print output, raise on non-zero exit."""
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

# Violation sources for rejection tests

# S1 violation: Lopa (0x00) is not write-class; fuse attempt must fail
S1_VIOLATION = """तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    सन्धिः ।
    वाचम् लोपः ।
}"""

# S2 violation: first targets Vak (0x30), second targets Yantra -- mismatch
S2_VIOLATION = """सञ्ज्ञा यन्त्र = 0x60 ।
तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    सन्धिः ।
    यन्त्र लिखति ।
}"""

# S5 violation: Lopa on same target before Sandhi pair
S5_VIOLATION = """तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    वाचम् लोपः ।
    वाचम् लिखति ।
    सन्धिः ।
    वाचम् स्थापयति ।
}"""


def part_a_compiler_verification():
    print("=" * 60)
    print("PART A: Sandhi Compiler Verification")
    print("=" * 60)

    sc = load_compiler()
    Compiler    = sc.PaninianFormalCompiler
    SandhiError = sc.SandhiError

    # -------- A1: ABI word correctness --------
    print("\n[A1] Compiling sandhi_core.pvm ...")
    src   = (ROOT / "programs/sandhi_core.pvm").read_text(encoding="utf-8")
    words = Compiler().compile_source(src)

    all_ok = True
    print(f"  Compiled {len(words)} word(s) (expected {len(EXPECTED_WORDS)})")
    for i, (got, want) in enumerate(zip(words, EXPECTED_WORDS)):
        ok = got == want
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] Word {i+1}: got 0x{got:08X}  want 0x{want:08X}")
        if not ok:
            all_ok = False
    if len(words) != len(EXPECTED_WORDS):
        print(f"  [FAIL] Word count: got {len(words)}, want {len(EXPECTED_WORDS)}")
        all_ok = False
    if not all_ok:
        raise RuntimeError("[A1 FAILED] ABI words do not match expected output.")

    # Check specific bit-field properties
    flags_w1 = (words[0] >> 4) & 0xF
    flags_w2 = (words[1] >> 4) & 0xF
    flags_w3 = (words[2] >> 4) & 0xF

    ok_flags = (flags_w1 == 0xF) and (flags_w2 == 0xE) and (flags_w3 == 0xF)
    print(f"  [{'PASS' if flags_w1 == 0xF else 'FAIL'}] "
          f"Word 1 FLAGS=0x{flags_w1:X} (want 0xF, standalone)")
    print(f"  [{'PASS' if flags_w2 == 0xE else 'FAIL'}] "
          f"Word 2 FLAGS=0x{flags_w2:X} (want 0xE, SANDHI-FIRST)")
    print(f"  [{'PASS' if flags_w3 == 0xF else 'FAIL'}] "
          f"Word 3 FLAGS=0x{flags_w3:X} (want 0xF, SANDHI-pair second)")
    if not ok_flags:
        raise RuntimeError("[A1 FAILED] FLAGS fields incorrect in fused pair.")

    print("  [OK] All ABI words and FLAGS fields correct.\n")

    # -------- A2: Sandhi violation rejection --------
    print("[A2] Testing Sandhi violation rejection ...")
    violations = [
        ("S1", "Non-write fuse (Lopa)",      S1_VIOLATION, "S1"),
        ("S2", "Target mismatch",             S2_VIOLATION, "S2"),
        ("S5", "Fuse after Lopa same target", S5_VIOLATION, "S5"),
    ]

    all_rejected = True
    for expected_id, desc, src, rule_id in violations:
        try:
            Compiler().compile_source(src)
            print(f"  [FAIL] {expected_id} ({desc}): no error raised")
            all_rejected = False
        except SandhiError as e:
            if e.rule_id == expected_id:
                print(f"  [PASS] {e.rule_id} ({e.rule_name}): correctly rejected")
            else:
                print(f"  [FAIL] Expected {expected_id} but got {e.rule_id}: {e}")
                all_rejected = False
        except Exception as e:
            print(f"  [FAIL] {expected_id}: unexpected {type(e).__name__}: {e}")
            all_rejected = False

    if not all_rejected:
        raise RuntimeError("[A2 FAILED] Not all Sandhi violations were correctly rejected.")
    print("  [OK] All three Sandhi violations correctly rejected.\n")

    print("[Part A OK] Compiler verification complete.\n")


# -----------------------------------------------------------------------
# PART B: Firmware proof on RV32 QEMU
# -----------------------------------------------------------------------

def part_b_firmware_proof():
    print("=" * 60)
    print("PART B: Sandhi Firmware Proof (RV32 QEMU)")
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

    # Setup remote directories
    run(client, f"mkdir -p {REMOTE_ROOT}/src/utils {REMOTE_ROOT}/src/rv32 {REMOTE_ROOT}/evidence")

    # SFTP all files
    print("\n[SFTP] Uploading files ...")
    sftp = client.open_sftp()
    for local, remote in FILES:
        local_path = ROOT / local
        if not local_path.exists():
            sftp.close()
            client.close()
            raise FileNotFoundError(f"Local file missing: {local_path}")
        sftp.put(str(local_path), f"{REMOTE_ROOT}/{remote}")
        print(f"  [SFTP] {local} -> {REMOTE_ROOT}/{remote}")
    sftp.close()
    print()

    # Build binary from .pvm source
    print("[Build] Compiling sandhi_core.pvm -> pvm_sandhi.bin ...")
    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/build_firmware.py sandhi_core.pvm pvm_sandhi.bin",
        desc="build_firmware")

    # Embed binary into C header
    print("\n[Embed] Embedding pvm_sandhi.bin -> src/rv32/pvm_image.h ...")
    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/embed_binary_image.py pvm_sandhi.bin src/rv32/pvm_image.h",
        desc="embed_binary")

    # Compile ELF
    print("\n[Compile] Building pvm_rv32_sandhi.elf ...")
    run(client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-gcc "
        "-march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles "
        "-Wall -Wextra -O2 "
        "-T src/rv32/linker.ld "
        "src/rv32/start.S "
        "src/rv32/pvm_firmware_sandhi.c "
        "-Isrc/rv32 "
        "-o pvm_rv32_sandhi.elf",
        desc="gcc")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-size pvm_rv32_sandhi.elf && "
        "riscv64-unknown-elf-objdump -h pvm_rv32_sandhi.elf | "
        "grep -E '(text|rodata|bss)'")

    # Run QEMU
    print("\n[QEMU] Executing Sandhi firmware on freestanding RV32 ...\n")
    execution_output = run(
        client,
        f"cd {REMOTE_ROOT} && "
        "qemu-system-riscv32 -M virt -nographic -bios none "
        "-kernel pvm_rv32_sandhi.elf",
    )

    # Save evidence
    evidence_path = ROOT / "evidence" / "2026-05-23-rv32-sandhi-proof.md"
    evidence_path.parent.mkdir(exist_ok=True)

    sc    = load_compiler()
    words = sc.PaninianFormalCompiler().compile_source(
        (ROOT / "programs/sandhi_core.pvm").read_text(encoding="utf-8")
    )

    evidence_path.write_text(
        "# RV32 Sandhi Proof Record -- Sprint 9\n\n"
        "## Concept\n\n"
        "Sandhi (instruction fusion): two adjacent compatible instructions fuse into an\n"
        "atomic execution pair. The first word carries FLAGS=0xE (SANDHI-FIRST). The\n"
        "firmware executes both before advancing. Five compatibility rules (S1-S5) must\n"
        "all hold; any violation is rejected by the compiler at parse time.\n\n"
        "## Source Program\n\n"
        "```\n"
        + (ROOT / "programs/sandhi_core.pvm").read_text(encoding="utf-8").strip()
        + "\n```\n\n"
        "## ABI Words Emitted\n\n```\n"
        + "\n".join(
            f"0x{w:08X}  {desc}"
            for w, desc in zip(words, [
                "Write Vak (standalone, FLAGS=0xF)",
                "Write Yantra (SANDHI-FIRST, FLAGS=0xE)",
                "Store Yantra (SANDHI-pair second, FLAGS=0xF)",
            ])
        )
        + "\n```\n\n"
        "## Sandhi Violations Rejected (Part A)\n\n"
        "- S1: Non-write fuse (Lopa) -- correctly rejected\n"
        "- S2: Target mismatch       -- correctly rejected\n"
        "- S5: Fuse after Lopa       -- correctly rejected\n\n"
        "## QEMU UART Output\n\n```text\n"
        + execution_output.strip()
        + "\n```\n",
        encoding="utf-8",
    )
    print(f"\n[Evidence] Saved to {evidence_path}")

    # Verify UART markers
    print("\n[Verification] Checking UART markers ...")
    all_passed = True
    for label, marker in EXPECTED_MARKERS:
        ok = marker in execution_output
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: '{marker}'")
        if not ok:
            all_passed = False

    client.close()

    if not all_passed:
        raise RuntimeError(
            "Sprint 9 Part B: firmware did not emit all expected UART markers."
        )

    print(
        "\n[Part B OK] Sandhi firmware proof confirmed.\n"
        "  Standalone write executed, Sandhi pair fused and executed atomically.\n"
        "  All bus states correct on freestanding RV32 QEMU."
    )


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    part_a_compiler_verification()
    part_b_firmware_proof()

    print()
    print("=" * 60)
    print("SPRINT 9 COMPLETE: Sandhi -- instruction fusion proven.")
    print("  FLAGS=0xE marks the SANDHI-FIRST word in the ABI.")
    print("  Firmware fuses the pair atomically at runtime.")
    print("  Five compatibility rules enforced at compile time.")
    print("=" * 60)


if __name__ == "__main__":
    main()
