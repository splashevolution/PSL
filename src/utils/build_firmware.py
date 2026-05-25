#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
# Force internal path recognition to prevent modular resolution drops
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from paninian_compiler import PaninianFormalCompiler

def build_firmware_target(source_path, output_target="pvm_launch.bin"):
    if not os.path.exists(source_path):
        print(f"[Error] Target file missing: {source_path}")
        sys.exit(1)
        
    with open(source_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    compiler = PaninianFormalCompiler()
    instruction_words = compiler.compile_source(raw_content)
    compiled_bytecode = compiler.emit_binary_words(instruction_words)

    with open(output_target, 'wb') as f:
        f.write(compiled_bytecode)

    print(
        f"[Firmware Pipeline Linked] Compiled {len(instruction_words)} "
        f"fixed-width instructions: {source_path} -> {output_target}"
    )
    for word in instruction_words:
        print(f"  ABI_EMIT 0x{word:08X}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 build_firmware.py <source.pvm> [output.bin]")
        sys.exit(1)
    build_firmware_target(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "pvm_launch.bin")
