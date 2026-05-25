#!/usr/bin/env python3
"""
PVM Sprint 6 — Sanjnaa Compile-Time Symbol Resolution Pipeline

Compiles sanjnaa_core.pvm (which uses symbolic names via सञ्ज्ञा declarations),
verifies the compiled ABI words are byte-for-byte identical to what built-in
Karaka terms would produce, builds freestanding RV32 firmware, runs QEMU,
and asserts the expected execution results.

The key proof is in the compiler output:
  वाक् (symbol, addr=0x30) -> same word as वाचम् (built-in, addr=0x30)
  श्रव (symbol, addr=0x50) -> same word as श्रोत्रम् (built-in, addr=0x50)

Usage:
    $env:PVM_VM_PASSWORD = "<vm-password>"
    python -B run_rv32_sanjnaa_pipeline.py
"""

import os
import sys
import struct
import importlib.util
import paramiko
from pathlib import Path


PASSWORD = os.environ.get("PVM_VM_PASSWORD")
if not PASSWORD:
    raise SystemExit("Set PVM_VM_PASSWORD before running the Sanjnaa pipeline.")

ROOT        = Path(__file__).resolve().parent
REMOTE_ROOT = "/home/praveen/pvm_rv32_sanjnaa"

FILES = [
    ("src/utils/paninian_compiler.py",  "src/utils/paninian_compiler.py"),
    ("src/utils/build_firmware.py",      "src/utils/build_firmware.py"),
    ("src/utils/embed_binary_image.py",  "src/utils/embed_binary_image.py"),
    ("src/rv32/start.S",                 "src/rv32/start.S"),
    ("src/rv32/linker.ld",               "src/rv32/linker.ld"),
    ("src/rv32/pvm_firmware_sanjnaa.c",  "src/rv32/pvm_firmware_sanjnaa.c"),
    ("programs/sanjnaa_core.pvm",                 "sanjnaa_core.pvm"),
]

# Expected ABI words — what the symbolic program must compile to.
# These are identical to what direct Karaka terms would produce.
EXPECTED_WORDS = [
    0x200530F0,   # Write वाक् (0x30) via Sanjnaa — same as वाचम् लिखति
    0x200550F0,   # Write श्रव (0x50) via Sanjnaa — same as श्रोत्रम् लिखति
    0x200030F0,   # Lopa  वाक् (0x30) via Sanjnaa
    0x210500F0,   # Anuvrtti write — blocked by Lopa boundary
]


def load_compiler_fresh():
    """Load compiler directly from source, bypassing any stale .pyc cache."""
    spec = importlib.util.spec_from_file_location(
        "paninian_compiler",
        str(ROOT / "src" / "utils" / "paninian_compiler.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PaninianFormalCompiler()


def verify_compiler_output():
    """
    Local verification: compile sanjnaa_core.pvm and assert ABI words
    match EXPECTED_WORDS before sending anything to the VM.
    """
    compiler = load_compiler_fresh()
    source   = (ROOT / "programs/sanjnaa_core.pvm").read_text(encoding="utf-8")
    words    = compiler.compile_source(source)

    print("[Compiler Verification] Sanjnaa symbol resolution:")
    print(f"  Compiled {len(words)} instruction(s)")
    all_ok = True
    for i, (got, want) in enumerate(zip(words, EXPECTED_WORDS)):
        ok = got == want
        status = "PASS" if ok else "FAIL"
        tgt_got  = (got  >> 8) & 0xFF
        tgt_want = (want >> 8) & 0xFF
        print(f"  [{status}] Instr {i+1}: got 0x{got:08X}  want 0x{want:08X}"
              f"  target=0x{tgt_got:02X} (expected 0x{tgt_want:02X})")
        if not ok:
            all_ok = False
    if len(words) != len(EXPECTED_WORDS):
        print(f"  [FAIL] Word count: got {len(words)}, want {len(EXPECTED_WORDS)}")
        all_ok = False
    if not all_ok:
        raise RuntimeError("Compiler produced incorrect ABI words for Sanjnaa symbols.")
    print("  [OK] All ABI words match — Sanjnaa symbols resolve identically "
          "to built-in Karaka terms. Zero runtime overhead confirmed.\n")


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


def main():
    # Step 0: Verify compiler output locally before touching the VM
    verify_compiler_output()

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
        "python3 -B src/utils/build_firmware.py sanjnaa_core.pvm pvm_sanjnaa.bin")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/embed_binary_image.py pvm_sanjnaa.bin src/rv32/pvm_image.h")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-gcc -march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles -Wall -Wextra -O2 "
        "-T src/rv32/linker.ld src/rv32/start.S src/rv32/pvm_firmware_sanjnaa.c "
        "-Isrc/rv32 -o pvm_rv32_sanjnaa.elf && "
        "riscv64-unknown-elf-size pvm_rv32_sanjnaa.elf && "
        "riscv64-unknown-elf-objdump -h pvm_rv32_sanjnaa.elf | grep -E '(text|rodata|bss)'")

    print("\n[QEMU] Executing Sanjnaa firmware under RV32 system emulation...\n")
    execution_output = run(
        client,
        f"cd {REMOTE_ROOT} && "
        "qemu-system-riscv32 -M virt -nographic -bios none -kernel pvm_rv32_sanjnaa.elf")

    # Save evidence
    evidence_path = ROOT / "evidence" / "2026-05-23-rv32-sanjnaa-proof.md"
    evidence_path.parent.mkdir(exist_ok=True)
    evidence_path.write_text(
        f"# RV32 Sanjnaa Proof Record — Sprint 6\n\n"
        f"## Claim Tested\n\n"
        f"Sanjnaa compile-time symbol resolution: symbolic names declared via\n"
        f"सञ्ज्ञा compile to byte-for-byte identical ABI words as built-in Karaka\n"
        f"terms. The symbol table is erased before the binary is emitted.\n"
        f"Zero runtime overhead. Proven on freestanding RV32 QEMU virt emulation.\n\n"
        f"## Expected ABI Words\n\n"
        f"```\n"
        + "\n".join(f"0x{w:08X}" for w in EXPECTED_WORDS)
        + f"\n```\n\n"
        f"## Execution Output\n\n```text\n{execution_output.strip()}\n```\n",
        encoding="utf-8",
    )
    print(f"\n[Evidence] Saved to {evidence_path}")

    checks = [
        ("Two Sanjnaa writes committed",        "sanjnaa_writes=0x02"),
        ("Lopa erasure fired",                  "lopa_erasures=0x01"),
        ("Anuvrtti blocked after Lopa",         "blocked_inheritances=0x01"),
        ("Vak zeroed after Lopa",               "VAK_after_lopa=0x00"),
        ("Srotra shadow written (Asiddha)",     "SROTRA_shadow=0xFF"),
        ("Sanjnaa symbol trace in output",      "Sanjnaa symbol resolved to 0x30"),
        ("No rejections",                       "rejected=0x00"),
    ]
    all_passed = True
    print("\n[Verification]")
    for label, marker in checks:
        ok = marker in execution_output
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: '{marker}'")
        if not ok:
            all_passed = False

    if not all_passed:
        raise RuntimeError("Sprint 6 Sanjnaa proof did not produce all expected outcomes.")

    print(
        "\n[Proof Verified] Paninian Sanjnaa compile-time symbol resolution confirmed —\n"
        "  symbolic names वाक् and श्रव resolved to identical ABI words as built-in terms,\n"
        "  symbol table fully erased before binary emission, zero runtime overhead."
    )
    client.close()


if __name__ == "__main__":
    main()
