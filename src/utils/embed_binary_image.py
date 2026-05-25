#!/usr/bin/env python3
"""Convert a compiled PVM binary image into a freestanding C header."""

import sys
from pathlib import Path


def write_header(binary_path, header_path):
    payload = Path(binary_path).read_bytes()
    if not payload or len(payload) % 4 != 0:
        raise ValueError("PVM firmware image must contain complete 32-bit words.")

    byte_rows = []
    for start in range(0, len(payload), 12):
        chunk = payload[start:start + 12]
        byte_rows.append("    " + ", ".join(f"0x{byte:02X}" for byte in chunk) + ",")

    header = "\n".join(
        [
            "#ifndef PVM_IMAGE_H",
            "#define PVM_IMAGE_H",
            "",
            "#include <stdint.h>",
            "",
            "static const uint8_t pvm_image[] = {",
            *byte_rows,
            "};",
            "",
            f"#define PVM_IMAGE_SIZE {len(payload)}u",
            f"#define PVM_IMAGE_WORDS {len(payload) // 4}u",
            "",
            "#endif",
            "",
        ]
    )
    Path(header_path).write_text(header, encoding="ascii")
    print(
        f"[Firmware Embed] Embedded {len(payload) // 4} ABI words "
        f"from {binary_path} -> {header_path}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 embed_binary_image.py <image.bin> <output.h>")
        sys.exit(1)
    write_header(sys.argv[1], sys.argv[2])
