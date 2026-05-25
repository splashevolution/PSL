#!/usr/bin/env python3
"""
PVM Sprint 4 — Anuvrtti Context Inheritance Pipeline

Compiles anuvritti_core.pvm, builds freestanding RV32 firmware with the
Anuvrtti decoder, runs QEMU system emulation, and asserts that the
compressed instruction inherited its target correctly and produced the
same Siddha bus result as the explicit instruction.

Usage:
    $env:PVM_VM_PASSWORD = "<vm-password>"
    python -B run_rv32_anuvritti_pipeline.py
"""

import os
import paramiko
from pathlib import Path


PASSWORD = os.environ.get("PVM_VM_PASSWORD")
if not PASSWORD:
    raise SystemExit("Set PVM_VM_PASSWORD before running the Anuvrtti pipeline.")

ROOT        = Path(__file__).resolve().parent
REMOTE_ROOT = "/home/praveen/pvm_rv32_anuvritti"

FILES = [
    ("src/utils/paninian_compiler.py",   "src/utils/paninian_compiler.py"),
    ("src/utils/build_firmware.py",       "src/utils/build_firmware.py"),
    ("src/utils/embed_binary_image.py",   "src/utils/embed_binary_image.py"),
    ("src/rv32/start.S",                  "src/rv32/start.S"),
    ("src/rv32/linker.ld",                "src/rv32/linker.ld"),
    ("src/rv32/pvm_firmware_anuvritti.c", "src/rv32/pvm_firmware_anuvritti.c"),
    ("programs/anuvritti_core.pvm",                "anuvritti_core.pvm"),
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

    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/build_firmware.py anuvritti_core.pvm pvm_anuvritti.bin")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "python3 -B src/utils/embed_binary_image.py pvm_anuvritti.bin src/rv32/pvm_image.h")

    run(client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-gcc -march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles -Wall -Wextra -O2 "
        "-T src/rv32/linker.ld src/rv32/start.S src/rv32/pvm_firmware_anuvritti.c "
        "-Isrc/rv32 -o pvm_rv32_anuvritti.elf && "
        "riscv64-unknown-elf-size pvm_rv32_anuvritti.elf && "
        "riscv64-unknown-elf-objdump -h pvm_rv32_anuvritti.elf | grep -E '(text|rodata|bss)'")

    print("\n[QEMU] Executing Anuvrtti firmware under RV32 system emulation...\n")
    execution_output = run(
        client,
        f"cd {REMOTE_ROOT} && "
        "qemu-system-riscv32 -M virt -nographic -bios none -kernel pvm_rv32_anuvritti.elf")

    # Save evidence
    evidence_path = ROOT / "evidence" / "2026-05-23-rv32-anuvritti-proof.md"
    evidence_path.parent.mkdir(exist_ok=True)
    evidence_path.write_text(
        f"# RV32 Anuvrtti Proof Record — Sprint 4\n\n"
        f"## Claim Tested\n\n"
        f"Anuvrtti context inheritance: a PSL instruction with no stated target\n"
        f"compiles to COMPRESSION=0x1 TARGET=0x00. The firmware resolves the\n"
        f"target at decode time from the previous instruction's target register.\n"
        f"Both the explicit and compressed instructions commit to the same Siddha\n"
        f"bus entry under freestanding RV32 QEMU virt system emulation.\n\n"
        f"## Execution Output\n\n```text\n{execution_output.strip()}\n```\n",
        encoding="utf-8",
    )
    print(f"\n[Evidence] Saved to {evidence_path}")

    # Assert expected outcomes
    checks = [
        ("Explicit instruction executed",    "explicit_writes=0x01"),
        ("Anuvrtti inheritance fired",       "inherited_writes=0x01"),
        ("Vak written by both instructions", "VAK=0xFF"),
        ("No rejections",                    "rejected=0x00"),
        ("Anuvrtti target resolved",         "ANUVRTTI: inherited target=0x30"),
    ]
    all_passed = True
    print("\n[Verification]")
    for label, marker in checks:
        ok = marker in execution_output
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: '{marker}'")
        if not ok:
            all_passed = False

    if not all_passed:
        raise RuntimeError("Sprint 4 Anuvrtti proof did not produce all expected outcomes.")

    print(
        "\n[Proof Verified] Paninian Anuvrtti context inheritance confirmed — "
        "compressed instruction inherited target 0x30 from preceding rule, "
        "zero target bits used in ABI word."
    )
    client.close()


if __name__ == "__main__":
    main()
