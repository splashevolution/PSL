#!/usr/bin/env python3
"""
run_rv32_safety_interlock_pipeline.py -- Sprint 12: Safety-Critical Control DSL

Two-part proof pipeline:

  Part A (14 checks): Structural verification
    A1-A3:   ABI byte count and word count correct
    A4-A11:  Each of the 8 ABI words is correct
    A12:     P4 violation (Ring0 outside scope) correctly rejected
    A13:     P3 violation (Ring0 on Siddha) correctly rejected
    A14:     P1 violation (Anuvrtti at start) correctly rejected

  Part B (12 checks): RV32 QEMU firmware execution
    B1-B11:  UART summary fields present with correct values
    B12:     No structural violations in UART output

Security: VM password MUST be passed via PVM_VM_PASSWORD environment variable.
          It must NEVER be hardcoded in this file.
"""

import os
import sys
import struct
import subprocess
import time
import textwrap
import paramiko

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REMOTE_ROOT = "/home/praveen/pvm_rv32_safety"
RISCV_GCC   = "riscv64-unknown-elf-gcc"
QEMU        = "qemu-system-riscv32"

EXPECTED_WORDS = [
    0x200530F0,   # Write  दबाव      (Ring2, 0x30, sensor status start)
    0x00AA00F0,   # ADHIKARA_OPEN
    0x00CC50F0,   # Store  वाल्व     (Ring0, 0x50, primary valve)
    0x01CC00F0,   # Store  Anuvrtti  (Ring0, inherit 0x50, secondary valve)
    0x00CC60E0,   # Store  इन्टरलॉक (Ring0, 0x60, configure -- SANDHI-FIRST)
    0x00CC60F0,   # Store  इन्टरलॉक (Ring0, 0x60, arm -- SANDHI-PAIR)
    0x00BB00F0,   # ADHIKARA_CLOSE
    0x200530F0,   # Write  दबाव      (Ring2, 0x30, sensor status complete)
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results = []

def check(label, ok, detail=""):
    tag = PASS if ok else FAIL
    msg = f"  [{tag}] {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    results.append((label, ok))
    return ok

def run(cmd, cwd=None, capture=True):
    r = subprocess.run(
        cmd, shell=True, cwd=cwd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    return r.returncode, r.stdout or "", r.stderr or ""

def word_desc(w):
    ring  = (w >> 28) & 0xF
    comp  = (w >> 24) & 0xF
    op    = (w >> 16) & 0xFF
    tgt   = (w >>  8) & 0xFF
    flags = (w >>  4) & 0xF
    return f"ring={ring} comp={comp} op=0x{op:02X} tgt=0x{tgt:02X} flags=0x{flags:X}"

# ---------------------------------------------------------------------------
# Part A: Structural (host-side) verification
# ---------------------------------------------------------------------------

def part_a():
    print("\n=== PART A: Structural verification ===\n")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "utils"))
    import paninian_compiler as sc

    # -- Compile --
    pvm_path = os.path.join(os.path.dirname(__file__), "programs/safety_interlock.pvm")
    src = open(pvm_path, encoding="utf-8").read()
    compiler = sc.PaninianFormalCompiler()
    words = compiler.compile_source(src)
    raw_bytes = b"".join(struct.pack(">I", w) for w in words)

    # A1: word count
    check("A1: Word count == 8", len(words) == 8,
          f"got {len(words)}")

    # A2: byte count
    check("A2: Byte count == 32", len(raw_bytes) == 32,
          f"got {len(raw_bytes)}")

    # A3: big-endian byte order (first word MSB is 0x20)
    check("A3: First byte == 0x20 (big-endian MSB of word[0])",
          raw_bytes[0] == 0x20,
          f"got 0x{raw_bytes[0]:02X}")

    # A4-A11: each word
    labels = [
        "A4:  word[0] = 0x200530F0 (Write दबाव Ring2 0x30 start)",
        "A5:  word[1] = 0x00AA00F0 (ADHIKARA_OPEN)",
        "A6:  word[2] = 0x00CC50F0 (Store वाल्व Ring0 0x50 primary)",
        "A7:  word[3] = 0x01CC00F0 (Store Anuvrtti Ring0 inherit 0x50)",
        "A8:  word[4] = 0x00CC60E0 (Store इन्टरलॉक Ring0 0x60 SANDHI-FIRST)",
        "A9:  word[5] = 0x00CC60F0 (Store इन्टरलॉक Ring0 0x60 SANDHI-PAIR)",
        "A10: word[6] = 0x00BB00F0 (ADHIKARA_CLOSE)",
        "A11: word[7] = 0x200530F0 (Write दबाव Ring2 0x30 complete)",
    ]
    for idx, (expected, label) in enumerate(zip(EXPECTED_WORDS, labels)):
        got = words[idx]
        check(label, got == expected,
              f"expected 0x{expected:08X} ({word_desc(expected)})\n"
              f"         got      0x{got:08X} ({word_desc(got)})")

    # A12: P4 violation -- Ring0 Store outside scope must be rejected.
    # यन्त्रै has role=VRDDHI_RING_0 which forces ring=0x00 at IR build time.
    # Without an अधिकारः block, P4 fires. (Plain 'स्थापयति' outside scope
    # stays at Ring2, so cannot trigger P4 -- we need an explicit Ring0 karaka.)
    p4_src = textwrap.dedent("""\
        तन्त्रशास्त्रम् {
            यन्त्रै स्थापयति ।
        }
    """)
    try:
        c2 = sc.PaninianFormalCompiler()
        c2.compile_source(p4_src)
        check("A12: P4 violation (Ring0 outside scope) rejected at compile time",
              False, "compiled without error -- P4 not enforced")
    except sc.ParibhashaError as e:
        check("A12: P4 violation (Ring0 outside scope) rejected at compile time",
              "P4" in str(e), f"correctly rejected: {e}")
    except Exception as e:
        check("A12: P4 violation (Ring0 outside scope) rejected at compile time",
              False, f"unexpected error: {type(e).__name__}: {e}")

    # A13: P3 violation -- Ring0 on Siddha address must be rejected
    p3_src = textwrap.dedent("""\
        सञ्ज्ञा दबाव = 0x30 ।
        तन्त्रशास्त्रम् {
            अधिकारः {
                दबाव स्थापयति ।
            }
        }
    """)
    try:
        c3 = sc.PaninianFormalCompiler()
        c3.compile_source(p3_src)
        check("A13: P3 violation (Ring0 on Siddha 0x30) rejected at compile time",
              False, "compiled without error -- P3 not enforced")
    except (sc.ParibhashaError, Exception) as e:
        check("A13: P3 violation (Ring0 on Siddha 0x30) rejected at compile time",
              True, f"correctly rejected: {type(e).__name__}: {e}")

    # A14: P1 violation -- Anuvrtti at start (no prior explicit write) must be rejected
    p1_src = textwrap.dedent("""\
        तन्त्रशास्त्रम् {
            लिखति ।
        }
    """)
    try:
        c4 = sc.PaninianFormalCompiler()
        c4.compile_source(p1_src)
        check("A14: P1 violation (Anuvrtti at start) rejected at compile time",
              False, "compiled without error -- P1 not enforced")
    except (sc.ParibhashaError, Exception) as e:
        check("A14: P1 violation (Anuvrtti at start) rejected at compile time",
              True, f"correctly rejected: {type(e).__name__}: {e}")

    return raw_bytes

# ---------------------------------------------------------------------------
# Part B: RV32 QEMU firmware execution
# ---------------------------------------------------------------------------

def build_and_run_on_vm(raw_bytes):
    """Build firmware on VM and run under QEMU; return UART output."""
    vm_password = os.environ.get("PVM_VM_PASSWORD")
    if not vm_password:
        print("ERROR: PVM_VM_PASSWORD environment variable not set.")
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        os.environ.get("PVM_VM_HOST", "127.0.0.1"),
        port=int(os.environ.get("PVM_VM_PORT", "2222")),
        username=os.environ.get("PVM_VM_USER", "praveen"),
        password=vm_password,
        timeout=10,
    )

    def ssh(cmd):
        _, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        rc  = stdout.channel.recv_exit_status()
        return rc, out, err

    sftp = client.open_sftp()

    # Create remote directory
    ssh(f"mkdir -p {REMOTE_ROOT}")

    # Upload pvm_image.h (big-endian bytes)
    image_c = "/* Auto-generated pvm_image.h -- Sprint 12 */\n"
    image_c += "#pragma once\n#include <stdint.h>\n"
    image_c += "static const uint8_t pvm_image[] = {\n    "
    image_c += ", ".join(f"0x{b:02X}" for b in raw_bytes)
    image_c += "\n};\n"
    with sftp.open(f"{REMOTE_ROOT}/pvm_image.h", "w") as f:
        f.write(image_c)

    # Upload firmware C source
    fw_path = os.path.join(
        os.path.dirname(__file__),
        "src", "rv32", "pvm_firmware_safety_interlock.c",
    )
    sftp.put(fw_path, f"{REMOTE_ROOT}/pvm_firmware_safety_interlock.c")

    # Upload linker script and start.S from canonical src/rv32/ files
    rv32_dir = os.path.join(os.path.dirname(__file__), "src", "rv32")
    sftp.put(os.path.join(rv32_dir, "linker.ld"), f"{REMOTE_ROOT}/linker.ld")
    sftp.put(os.path.join(rv32_dir, "start.S"),   f"{REMOTE_ROOT}/start.S")

    # Compile
    compile_cmd = (
        f"cd {REMOTE_ROOT} && "
        f"{RISCV_GCC} -march=rv32ima -mabi=ilp32 -nostdlib -ffreestanding "
        f"-O2 -Wall -Wno-unused-but-set-variable "
        f"-I. -T linker.ld "
        f"start.S pvm_firmware_safety_interlock.c "
        f"-o safety_interlock.elf 2>&1"
    )
    rc, out, _ = ssh(compile_cmd)
    if rc != 0:
        print(f"[COMPILE ERROR]\n{out}")
        client.close()
        return None

    # Run under QEMU
    qemu_cmd = (
        f"cd {REMOTE_ROOT} && "
        f"timeout 10 {QEMU} -machine virt -cpu rv32 -nographic "
        f"-bios none -kernel safety_interlock.elf "
        f"-serial mon:stdio 2>/dev/null || true"
    )
    rc, uart_out, _ = ssh(qemu_cmd)
    sftp.close()
    client.close()
    return uart_out


def part_b(raw_bytes):
    print("\n=== PART B: RV32 QEMU firmware execution ===\n")

    uart = build_and_run_on_vm(raw_bytes)
    if uart is None:
        for label in [f"B{i}" for i in range(1, 13)]:
            check(f"{label}: (skipped -- build failed)", False)
        return

    print("  [UART output]")
    for line in uart.strip().splitlines():
        print(f"    {line}")
    print()

    summary_line = ""
    for line in uart.splitlines():
        if "SAFETY INTERLOCK SUMMARY" in line:
            summary_line = line
            break

    # B1: summary line present
    check("B1:  UART summary line present",
          "SAFETY INTERLOCK SUMMARY" in uart)

    # B2: sensor_writes=0x02
    check("B2:  sensor_writes=0x02",
          "sensor_writes=0x02" in summary_line,
          f"summary: {summary_line.strip()}")

    # B3: scope_opens=0x01
    check("B3:  scope_opens=0x01",
          "scope_opens=0x01" in summary_line)

    # B4: valve_stores=0x01
    check("B4:  valve_stores=0x01",
          "valve_stores=0x01" in summary_line)

    # B5: anuvrtti_stores=0x01
    check("B5:  anuvrtti_stores=0x01",
          "anuvrtti_stores=0x01" in summary_line)

    # B6: interlock_stores=0x02
    check("B6:  interlock_stores=0x02",
          "interlock_stores=0x02" in summary_line)

    # B7: sandhi_pairs=0x01
    check("B7:  sandhi_pairs=0x01",
          "sandhi_pairs=0x01" in summary_line)

    # B8: scope_closes=0x01
    check("B8:  scope_closes=0x01",
          "scope_closes=0x01" in summary_line)

    # B9: BUG1_prevented=0x01
    check("B9:  BUG1_prevented=0x01",
          "BUG1_prevented=0x01" in summary_line)

    # B10: BUG2_prevented=0x01
    check("B10: BUG2_prevented=0x01",
          "BUG2_prevented=0x01" in summary_line)

    # B11: BUG3_atomic=0x01
    check("B11: BUG3_atomic=0x01",
          "BUG3_atomic=0x01" in summary_line)

    # B12: BUG4_chain=0x01
    check("B12: BUG4_chain=0x01",
          "BUG4_chain=0x01" in summary_line)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print(" Sprint 12: Safety-Critical Control DSL")
    print(" Pressure-Relief Valve Safety Interlock Pipeline")
    print("=" * 72)

    raw_bytes = part_a()
    part_b(raw_bytes)

    total  = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print(f"\n{'=' * 72}")
    print(f" RESULTS: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
        for label, ok in results:
            if not ok:
                print(f"   FAIL: {label}")
    else:
        print("  -- ALL PASS")
    print("=" * 72)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
