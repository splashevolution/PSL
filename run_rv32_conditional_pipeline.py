#!/usr/bin/env python3
"""
PVM Sprint 2 — Utsarga/Apavada Conditional Execution Pipeline

Transfers Sprint 2 source files to the Lubuntu VM, builds the freestanding
RV32 firmware with the conditional evaluator, runs QEMU system emulation,
and asserts the expected Paninian precedence output.

Usage:
    $env:PVM_VM_PASSWORD = "<vm-password>"
    python -B run_rv32_conditional_pipeline.py
"""

import os
import paramiko
from pathlib import Path


PASSWORD = os.environ.get("PVM_VM_PASSWORD")
if not PASSWORD:
    raise SystemExit("Set PVM_VM_PASSWORD before running the conditional pipeline.")

ROOT        = Path(__file__).resolve().parent
REMOTE_ROOT = "/home/praveen/pvm_rv32_conditional"

FILES = [
    ("src/utils/paninian_compiler.py",       "src/utils/paninian_compiler.py"),
    ("src/utils/build_firmware.py",           "src/utils/build_firmware.py"),
    ("src/utils/embed_binary_image.py",       "src/utils/embed_binary_image.py"),
    ("src/rv32/start.S",                      "src/rv32/start.S"),
    ("src/rv32/linker.ld",                    "src/rv32/linker.ld"),
    ("src/rv32/pvm_firmware_conditional.c",   "src/rv32/pvm_firmware_conditional.c"),
    ("programs/conditional_core.pvm",                  "conditional_core.pvm"),
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

    # 1. Create remote directory tree
    run(client, f"mkdir -p {REMOTE_ROOT}/src/utils {REMOTE_ROOT}/src/rv32 {REMOTE_ROOT}/evidence")

    # 2. Transfer source files
    sftp = client.open_sftp()
    for local, remote in FILES:
        local_path = ROOT / local
        if not local_path.exists():
            raise FileNotFoundError(f"Local file missing: {local_path}")
        sftp.put(str(local_path), f"{REMOTE_ROOT}/{remote}")
        print(f"  [SFTP] {local} -> {REMOTE_ROOT}/{remote}")
    sftp.close()

    # 3. Compile PSL source -> binary image
    run(
        client,
        f"cd {REMOTE_ROOT} && "
        "python3 src/utils/build_firmware.py conditional_core.pvm pvm_conditional.bin",
    )

    # 4. Embed binary image into firmware header
    run(
        client,
        f"cd {REMOTE_ROOT} && "
        "python3 src/utils/embed_binary_image.py pvm_conditional.bin src/rv32/pvm_image.h",
    )

    # 5. Compile RV32 ELF using the conditional firmware
    run(
        client,
        f"cd {REMOTE_ROOT} && "
        "riscv64-unknown-elf-gcc -march=rv32imac -mabi=ilp32 -mcmodel=medany "
        "-ffreestanding -fno-builtin -nostdlib -nostartfiles -Wall -Wextra -O2 "
        "-T src/rv32/linker.ld src/rv32/start.S src/rv32/pvm_firmware_conditional.c "
        "-Isrc/rv32 -o pvm_rv32_conditional.elf && "
        "riscv64-unknown-elf-size pvm_rv32_conditional.elf && "
        "riscv64-unknown-elf-objdump -h pvm_rv32_conditional.elf | grep -E '(text|rodata|bss)'",
    )

    # 6. Run QEMU system emulation
    print("\n[QEMU] Executing conditional firmware under RV32 system emulation...\n")
    execution_output = run(
        client,
        f"cd {REMOTE_ROOT} && "
        "qemu-system-riscv32 -M virt -nographic -bios none -kernel pvm_rv32_conditional.elf",
    )

    # 7. Save evidence
    evidence_path = ROOT / "evidence" / "2026-05-23-rv32-conditional-proof.md"
    evidence_path.parent.mkdir(exist_ok=True)
    evidence_path.write_text(
        f"# RV32 Conditional Proof Record — Sprint 2\n\n"
        f"## Claim Tested\n\n"
        f"Utsarga/Apavada conditional rule application compiles from PSL source,\n"
        f"embeds into freestanding RV32 firmware, and produces observable Paninian\n"
        f"precedence behaviour via UART MMIO under QEMU virt system emulation.\n\n"
        f"## Execution Output\n\n```text\n{execution_output.strip()}\n```\n",
        encoding="utf-8",
    )
    print(f"\n[Evidence] Saved to {evidence_path}")

    # 8. Assert expected outcomes
    checks = [
        ("Apavada fires",        "APAVADA FIRED"),
        ("Utsarga skipped",      "UTSARGA SKIPPED"),
        ("Yantra shadow written","YANTRA_shadow=0xFF"),
        ("Vak not written",      "VAK=0x00"),
    ]
    all_passed = True
    print("\n[Verification]")
    for label, marker in checks:
        ok = marker in execution_output
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}: '{marker}'")
        if not ok:
            all_passed = False

    if not all_passed:
        raise RuntimeError("Sprint 2 conditional proof did not produce all expected outcomes.")

    print(
        "\n[Proof Verified] Paninian Utsarga/Apavada precedence confirmed on "
        "freestanding RV32 system emulation."
    )
    client.close()


if __name__ == "__main__":
    main()
