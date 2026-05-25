#!/usr/bin/env python3
"""
run_rv32_boot_sequencer_pipeline.py -- Sprint 11: Secure MMIO Boot Sequencer

Two-part proof:

  Part A (local): Compiler structural verification
    A1. boot_sequencer.pvm compiles to exactly 7 words
    A2. Word 0: Write Ring2 status bus (0x200530F0)
    A3. Word 1: ADHIKARA_OPEN sentinel (0x00AA00F0)
    A4. Word 2: Store Ring0 clock_ctrl (0x00CC50F0) -- inside scope
    A5. Word 3: Store Ring0 sec_lock SANDHI-FIRST (0x00CC60E0)
    A6. Word 4: Store Ring0 sec_lock SANDHI-PAIR (0x00CC60F0)
    A7. Word 5: ADHIKARA_CLOSE sentinel (0x00BB00F0)
    A8. Word 6: Write Ring2 status bus confirm (0x200530F0)

    Structural guarantee checks:
    A9.  BUG-1 proof: no Ring0 instruction appears outside scope in binary
    A10. BUG-2 proof: no Ring0 instruction targets Siddha addr (< 0x50) in binary
    A11. BUG-3 proof: security lock pair carries FLAGS=0xE (Sandhi atomic marker)

    Rejection checks (compiler must refuse these):
    A12. Unscoped Ring0 store (P4 violation) -- rejected
    A13. Ring0 on Siddha target (P3 violation) -- rejected
    A14. Sandhi on different targets (S2 violation) -- rejected

  Part B (VM): Firmware execution proof
    B1.  UART contains "[RV32 PVM BOOT]"
    B2.  UART contains "ADHIKARA_OPEN"
    B3.  UART contains "ADHIKARA_CLOSE"
    B4.  UART contains "SANDHI-FIRST"
    B5.  UART contains "SANDHI-PAIR"
    B6.  UART contains "status_writes=0x02"
    B7.  UART contains "clock_stores=0x01"
    B8.  UART contains "lock_stores=0x02"
    B9.  UART contains "sandhi_pairs=0x01"
    B10. UART contains "BUG1_prevented=0x01"
    B11. UART contains "BUG2_prevented=0x01"
    B12. UART contains "BUG3_atomic=0x01"

Usage:
    $env:PVM_VM_PASSWORD = "..."
    python -B run_rv32_boot_sequencer_pipeline.py
"""

import importlib.util
import os
import struct
import sys
import paramiko
from pathlib import Path

ROOT   = Path(__file__).resolve().parent
SRC_RV = ROOT / "src" / "rv32"
PVM    = ROOT / "programs/boot_sequencer.pvm"

PASS_COUNT = 0
FAIL_COUNT = 0

def ok(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  [PASS] {msg}")

def fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"  [FAIL] {msg}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

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
# Part A: Local compiler verification
# ---------------------------------------------------------------------------

def run_part_a(compiler_mod):
    section("PART A: Compiler Structural Verification")

    C               = compiler_mod.PaninianFormalCompiler
    ParibhashaError = compiler_mod.ParibhashaError
    SandhiError     = compiler_mod.SandhiError

    src = PVM.read_text(encoding="utf-8")
    c   = C()

    # Compile the boot sequencer
    try:
        words = c.compile_source(src)
    except Exception as e:
        fail(f"boot_sequencer.pvm failed to compile: {e}")
        return None

    # Expected ABI
    EXPECTED = [
        0x200530F0,  # Write Ring2 status bus (standalone)
        0x00AA00F0,  # ADHIKARA_OPEN
        0x00CC50F0,  # Store Ring0 clock_ctrl
        0x00CC60E0,  # Store Ring0 sec_lock SANDHI-FIRST
        0x00CC60F0,  # Store Ring0 sec_lock SANDHI-PAIR
        0x00BB00F0,  # ADHIKARA_CLOSE
        0x200530F0,  # Write Ring2 status bus (confirm)
    ]

    # A1: word count
    if len(words) == 7:
        ok(f"A1: Compiles to exactly 7 words ({len(words)})")
    else:
        fail(f"A1: Expected 7 words, got {len(words)}: {[hex(w) for w in words]}")
        return None

    # A2-A8: individual word checks
    labels = [
        ("A2", "Write Ring2 status bus standalone"),
        ("A3", "ADHIKARA_OPEN sentinel"),
        ("A4", "Store Ring0 clock_ctrl (inside scope)"),
        ("A5", "Store Ring0 sec_lock SANDHI-FIRST"),
        ("A6", "Store Ring0 sec_lock SANDHI-PAIR"),
        ("A7", "ADHIKARA_CLOSE sentinel"),
        ("A8", "Write Ring2 status bus confirm"),
    ]
    for i, (check_id, label) in enumerate(labels):
        if words[i] == EXPECTED[i]:
            ok(f"{check_id}: word[{i}]={hex(words[i])} -- {label}")
        else:
            fail(f"{check_id}: word[{i}]={hex(words[i])} expected {hex(EXPECTED[i])} -- {label}")

    # ---- Structural guarantee checks ----

    # A9: BUG-1 proof -- scan binary for Ring0 outside scope
    in_scope = False
    bug1_violation = False
    for w in words:
        op   = (w >> 16) & 0xFF
        ring = (w >> 28) & 0xF
        if op == 0xAA:
            in_scope = True
        elif op == 0xBB:
            in_scope = False
        elif ring == 0x0 and op not in (0xAA, 0xBB) and not in_scope:
            bug1_violation = True

    if not bug1_violation:
        ok("A9:  BUG-1 proof: binary contains zero Ring0 instructions outside scope")
    else:
        fail("A9:  BUG-1 proof: Ring0 instruction found outside scope in binary")

    # A10: BUG-2 proof -- scan binary for Ring0 on Siddha target
    bug2_violation = False
    for w in words:
        op     = (w >> 16) & 0xFF
        ring   = (w >> 28) & 0xF
        target = (w >>  8) & 0xFF
        if ring == 0x0 and op not in (0xAA, 0xBB) and target < 0x50 and target != 0x00:
            bug2_violation = True

    if not bug2_violation:
        ok("A10: BUG-2 proof: binary contains zero Ring0 instructions on Siddha targets")
    else:
        fail("A10: BUG-2 proof: Ring0 on Siddha target found in binary")

    # A11: BUG-3 proof -- FLAGS=0xE present on security lock pair
    sandhi_first_count = sum(1 for w in words if ((w >> 4) & 0xF) == 0xE)
    if sandhi_first_count == 1:
        ok(f"A11: BUG-3 proof: FLAGS=0xE (SANDHI-FIRST) present exactly once "
           f"on security lock store")
    else:
        fail(f"A11: BUG-3 proof: expected 1 SANDHI-FIRST word, got {sandhi_first_count}")

    # ---- Rejection checks ----

    # A12: BUG-1 violation program -- Ring0 (VRDDHI_RING_0 karaka) without Adhikara scope
    # यन्त्रै has role=VRDDHI_RING_0, which forces ring=0x00 at IR build time.
    # Without an अधिकारः block, P4 fires.
    bug1_prog = """तन्त्रशास्त्रम् {
    यन्त्रै स्थापयति ।
}"""
    try:
        C().compile_source(bug1_prog)
        fail("A12: P4 unscoped Ring0 store was NOT rejected (compiler failure)")
    except ParibhashaError as e:
        if "P4" in str(e):
            ok(f"A12: P4 unscoped Ring0 store correctly rejected: {e.rule_name}")
        else:
            fail(f"A12: Wrong rule triggered: {e}")
    except Exception as e:
        fail(f"A12: Unexpected error: {e}")

    # A13: BUG-2 violation program -- Ring0 on Siddha target inside scope
    bug2_prog = """तन्त्रशास्त्रम् {
    अधिकारः {
        वाग्यन्थ्रैः लिखति ।
    }
}"""
    try:
        C().compile_source(bug2_prog)
        fail("A13: P3 Ring0-on-Siddha was NOT rejected (compiler failure)")
    except ParibhashaError as e:
        if "P3" in str(e):
            ok(f"A13: P3 Ring0-on-Siddha correctly rejected: {e.rule_name}")
        else:
            fail(f"A13: Wrong rule triggered: {e}")
    except Exception as e:
        fail(f"A13: Unexpected error: {e}")

    # A14: S2 violation -- Sandhi on different targets
    s2_prog = """सञ्ज्ञा घड़ी = 0x50 ।
सञ्ज्ञा सुरक्षा = 0x60 ।
तन्त्रशास्त्रम् {
    अधिकारः {
        घड़ी स्थापयति ।
        सन्धिः ।
        सुरक्षा स्थापयति ।
    }
}"""
    try:
        C().compile_source(s2_prog)
        fail("A14: S2 cross-target Sandhi was NOT rejected (compiler failure)")
    except SandhiError as e:
        if "S2" in str(e):
            ok(f"A14: S2 cross-target Sandhi correctly rejected: {e.rule_name}")
        else:
            fail(f"A14: Wrong rule triggered: {e}")
    except Exception as e:
        fail(f"A14: Unexpected error: {e}")

    return words

# ---------------------------------------------------------------------------
# Part B: VM firmware proof
# ---------------------------------------------------------------------------

REMOTE_ROOT = "/home/praveen/pvm_rv32_boot"

def _ssh_run(client, cmd, desc=""):
    _in, stdout, stderr = client.exec_command(cmd, timeout=120)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    combined = out + err
    if desc:
        print(f"  [ssh:{desc}] exit={stdout.channel.recv_exit_status()}")
    return combined


def build_and_run_on_vm(words, vm_password):
    section("PART B: RV32 QEMU Firmware Execution")

    if not words:
        fail("B0: No words to embed -- Part A failed")
        return ""

    # Build pvm_image.h content
    header_lines = [
        "/* AUTO-GENERATED -- boot_sequencer.pvm */",
        "#pragma once",
        "#include <stdint.h>",
        "static const uint8_t pvm_image[] = {",
    ]
    byte_data = b"".join(struct.pack(">I", w) for w in words)
    hex_bytes = [f"0x{b:02X}" for b in byte_data]
    for i in range(0, len(hex_bytes), 8):
        header_lines.append("    " + ", ".join(hex_bytes[i:i+8]) + ",")
    header_lines.append("};")
    header_content = "\n".join(header_lines) + "\n"

    # Connect via paramiko (same pattern as all other pipelines)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        os.environ.get("PVM_VM_HOST", "127.0.0.1"),
        port=int(os.environ.get("PVM_VM_PORT", "2222")),
        username=os.environ.get("PVM_VM_USER", "praveen"),
        password=vm_password,
        timeout=10,
    )

    # Set up remote directory
    _ssh_run(client, f"mkdir -p {REMOTE_ROOT}/src/rv32", "mkdir")

    # Upload files via SFTP
    sftp = client.open_sftp()
    print("\n  [SFTP] Uploading files ...")

    # pvm_image.h (generated from compiled words)
    with sftp.open(f"{REMOTE_ROOT}/src/rv32/pvm_image.h", "w") as f:
        f.write(header_content)
    print("  [SFTP] pvm_image.h")

    # firmware C source
    fw_src = (SRC_RV / "pvm_firmware_boot_sequencer.c").read_text(encoding="utf-8")
    with sftp.open(f"{REMOTE_ROOT}/src/rv32/pvm_firmware_boot_sequencer.c", "w") as f:
        f.write(fw_src)
    print("  [SFTP] pvm_firmware_boot_sequencer.c")

    # Shared files from the standard rv32 directory
    for fname in ("start.S", "linker.ld"):
        sftp.put(str(SRC_RV / fname), f"{REMOTE_ROOT}/src/rv32/{fname}")
        print(f"  [SFTP] {fname}")

    sftp.close()

    # Compile
    print("\n  [Build] Compiling boot_sequencer firmware ...")
    gcc_cmd = (
        f"cd {REMOTE_ROOT}/src/rv32 && "
        "riscv64-unknown-elf-gcc "
        "-march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles "
        "-Wall -Wextra -O2 "
        "-T linker.ld "
        "start.S pvm_firmware_boot_sequencer.c "
        "-Isrc/rv32 "
        "-o boot_sequencer.elf 2>&1"
    )
    # Note: -I needs to be relative to cwd, fix:
    gcc_cmd = (
        f"cd {REMOTE_ROOT}/src/rv32 && "
        "riscv64-unknown-elf-gcc "
        "-march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles "
        "-Wall -Wextra -O2 "
        "-T linker.ld "
        "start.S pvm_firmware_boot_sequencer.c "
        "-I. "
        "-o boot_sequencer.elf 2>&1"
    )
    gcc_out = _ssh_run(client, gcc_cmd, "gcc")
    if gcc_out.strip():
        print(f"  [gcc output] {gcc_out.strip()}")

    # Execute on QEMU
    print("\n  [QEMU] Executing on freestanding RV32 ...\n")
    qemu_cmd = (
        f"cd {REMOTE_ROOT}/src/rv32 && "
        "timeout 15 qemu-system-riscv32 -M virt -nographic -bios none "
        "-kernel boot_sequencer.elf 2>/dev/null || true"
    )
    uart = _ssh_run(client, qemu_cmd, "qemu")

    client.close()

    print("  --- UART output ---")
    for line in uart.splitlines():
        print(f"  {line}")
    print("  --- end UART ---\n")
    return uart

def run_part_b(uart):
    checks = [
        ("B1",  "[RV32 PVM BOOT]",        "Boot banner present"),
        ("B2",  "ADHIKARA_OPEN",           "Privileged scope entered"),
        ("B3",  "ADHIKARA_CLOSE",          "Privileged scope exited"),
        ("B4",  "SANDHI-FIRST",            "Atomic pair declared (FLAGS=0xE detected)"),
        ("B5",  "SANDHI-PAIR",             "Atomic pair second instruction executed"),
        ("B6",  "status_writes=0x02",      "Two status bus writes (start + confirm)"),
        ("B7",  "clock_stores=0x01",       "Clock register configured once"),
        ("B8",  "lock_stores=0x02",        "Security lock written twice (write + lock)"),
        ("B9",  "sandhi_pairs=0x01",       "One Sandhi atomic pair completed"),
        ("B10", "BUG1_prevented=0x01",     "BUG-1 structural guarantee confirmed"),
        ("B11", "BUG2_prevented=0x01",     "BUG-2 structural guarantee confirmed"),
        ("B12", "BUG3_atomic=0x01",        "BUG-3 atomic pair marker confirmed"),
    ]
    for check_id, marker, description in checks:
        if marker in uart:
            ok(f"{check_id}: {description}")
        else:
            fail(f"{check_id}: '{marker}' not found -- {description}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  PVM Sprint 11 -- Secure MMIO Boot Sequencer Pipeline")
    print("  boot_sequencer.pvm")
    print("=" * 60)

    compiler_mod = load_compiler()

    # Part A
    words = run_part_a(compiler_mod)

    # Part B
    vm_password = os.environ.get("PVM_VM_PASSWORD", "")
    if not vm_password:
        print("\n  [SKIP] PVM_VM_PASSWORD not set -- skipping Part B (VM execution)")
        print("         Set $env:PVM_VM_PASSWORD and re-run for full proof.")
    else:
        uart = build_and_run_on_vm(words, vm_password)
        run_part_b(uart)

    # Final result
    total = PASS_COUNT + FAIL_COUNT
    print(f"\n{'='*60}")
    if FAIL_COUNT == 0:
        print(f"  [PASS] {PASS_COUNT}/{total} checks passed.")
    else:
        print(f"  [FAIL] {PASS_COUNT}/{total} passed, {FAIL_COUNT} failed.")
    print("=" * 60)
    sys.exit(0 if FAIL_COUNT == 0 else 1)

if __name__ == "__main__":
    main()
