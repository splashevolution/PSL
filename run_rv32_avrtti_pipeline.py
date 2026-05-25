#!/usr/bin/env python3
"""
PVM Sprint 3 — Avrtti Bounded Repetition Pipeline

Compiles avrtti_core.pvm, builds freestanding RV32 firmware with the
Avrtti execution engine, runs QEMU system emulation, and asserts that
the rule applied exactly 3 times with no branch prediction required.

Usage:
    $env:PVM_VM_PASSWORD = "<vm-password>"
    python -B run_rv32_avrtti_pipeline.py
"""

import os
import paramiko
from pathlib import Path


PASSWORD = os.environ.get("PVM_VM_PASSWORD")
if not PASSWORD:
    raise SystemExit("Set PVM_VM_PASSWORD before running the Avrtti pipeline.")

ROOT        = Path(__file__).resolve().parent
REMOTE_ROOT = "/home/praveen/pvm_rv32_avrtti"

FILES = [
    ("src/utils/paninian_compiler.py",     "src/utils/paninian_compiler.py"),
    ("src/utils/build_firmware.py",         "src/utils/build_firmware.py"),
    ("src/utils/embed_binary_image.py",     "src/utils/embed_binary_image.py"),
    ("src/rv32/start.S",                    "src/rv32/start.S"),
    ("src/rv32/linker.ld",                  "src/rv32/linker.ld"),
    ("src/rv32/pvm_firmware_avrtti.c",      "src/rv32/pvm_firmware_avrtti.c"),
    ("programs/avrtti_core.pvm",                     "avrtti_core.pvm"),
]


def run(client, command):
    print(f"$ {command}")
    _, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode("utf-8", errors="replace")
    error  = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if error:
        print(error,  end="" if error.endswith("\n") else "\n")
    if status != 0:
        raise RuntimeError(f"Remote command failed (exit {status}): {command}")
    return output


def main():
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

    # Build — use python3 -B to skip stale .pyc on the VM too
    run(
        client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/build_firmware.py avrtti_core.pvm pvm_avrtti.bin",
    )

    run(
        client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/embed_binary_image.py pvm_avrtti.bin src/rv32/pvm_image.h",
    )

    run(
        client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-gcc -march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles -Wall -Wextra -O2 "
        "-T src/rv32/linker.ld src/rv32/start.S src/rv32/pvm_firmware_avrtti.c "
        "-Isrc/rv32 -o pvm_rv32_avrtti.elf && "
        "riscv64-unknown-elf-size pvm_rv32_avrtti.elf && "
        "riscv64-unknown-elf-objdump -h pvm_rv32_avrtti.elf | grep -E '(text|rodata|bss)'",
    )

    print("\n[QEMU] Executing Avrtti firmware under RV32 system emulation...\n")
    execution_output = run(
        client,
        f"cd {REMOTE_ROOT} && "
        "qemu-system-riscv32 -M virt -nographic -bios none -kernel pvm_rv32_avrtti.elf",
    )

    # Save evidence
    evidence_path = ROOT / "evidence" / "2026-05-23-rv32-avrtti-proof.md"
    evidence_path.parent.mkdir(exist_ok=True)
    evidence_path.write_text(
        f"# RV32 Avrtti Proof Record — Sprint 3\n\n"
        f"## Claim Tested\n\n"
        f"Avrtti bounded repetition: a rule marked with count N in the instruction\n"
        f"word executes exactly N times on freestanding RV32 firmware under QEMU\n"
        f"virt system emulation. No branch predictor. No runtime loop variable.\n"
        f"The bound is decoded directly from bits [27:24] of the ABI word.\n\n"
        f"## Execution Output\n\n```text\n{execution_output.strip()}\n```\n",
        encoding="utf-8",
    )
    print(f"\n[Evidence] Saved to {evidence_path}")

    # Assert expected outcomes
    checks = [
        ("Avrtti fired exactly 3 times", "avrtti_cycles=0x03"),
        ("Vak written (Siddha)",          "VAK=0xFF"),
        ("Yantra shadow committed",       "YANTRA_shadow=0xFF"),
        ("Apavada also fired",            "apavada_fired=0x01"),
        ("No rejections",                 "rejected=0x00"),
    ]
    all_passed = True
    print("\n[Verification]")
    for label, marker in checks:
        ok = marker in execution_output
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: '{marker}'")
        if not ok:
            all_passed = False

    if not all_passed:
        raise RuntimeError("Sprint 3 Avrtti proof did not produce all expected outcomes.")

    print(
        "\n[Proof Verified] Paninian Avrtti bounded repetition confirmed — "
        "count decoded from instruction word, executed exactly 3 times, "
        "no branch prediction required."
    )
    client.close()


if __name__ == "__main__":
    main()
