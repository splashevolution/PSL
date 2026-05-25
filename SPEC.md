# SPEC.md: The Paninian Systems Language & Virtual Machine Specification

### 1. The Morphological Grammar Model

The Paninian Systems Language (PSL) maps the structural rules of the *Aṣṭādhyāyī* directly to compile-time resource allocations and data-flow semantics.

* **कारकाणि (Kārakas - Data-Flow Relations):**
* **अपादानम् (Apādāna - Source):** Marked by the ablative case suffix (`-आत्`). Maps to the source register or memory read address.
* **कर्मन् (Karman - Destination):** Marked by the accusative case suffix (`-म्` / `-म`). Maps to the destination register or memory write target.
* **करणम् (Karaṇa - Instrument):** Marked by the instrumental case suffix (`-एण` / `-ऐः`). Maps to the specific hardware bus, peripheral resource, or DMA channel.
* **अधिकरणम् (Adhikaraṇa - Context/Location):** Marked by the locative case suffix (`-ए`). Maps to the active base memory segment, memory bank, or execution context.


* **अनुवृत्तिः (Anuvṛtti - State Compression):** If an instruction omits a *Karman* (destination) or *Apādāna* (source), the compiler automatically copies the missing parameter from the immediate preceding instruction in the Abstract Syntax Tree (AST), compressing code footprint.
* **वृद्धिः (Vṛddhi - Privilege Escalation):** If a target word undergoes structural expansion to the highest phonetic tier (suffix `-ऐ`), it triggers hardware-level Ring 0 privilege clearance.

---

### 2. The Fixed 32-Bit Bytecode Specification

Every operation compiled from PSL emits a rigid, predictable 32-bit instruction word layout to eliminate decoding drift.

```
+---------+---------+-----------------+-----------------+-----------------+
| 31 - 28 | 27 - 24 |     23 - 16     |     15 - 08     |     07 - 00     |
+---------+---------+-----------------+-----------------+-----------------+
| RING_ID | COMPRES |   OPCODE (KRIYĀ)|   TARGET (REG)  |   FLAGS (LOPA)  |
+---------+---------+-----------------+-----------------+-----------------+
```

* **Bits - PRIVILEGE_RING:** `0x0` = Ring 0 (Vṛddhi), `0x2` = Ring 2 (Standard User).
* **Bits - COMPRESSION_MASK:** `0x1` = Anuvṛtti compression active (inherit context), `0x0` = Explicit.
* **Bits - KRIYĀ_OPCODE:** The system primitive action (`0x00` = Lopa, `0x05` = Write, `0x06` = Read, `0xCC` = Store).
* **Bits - HARDWARE_TARGET:** The specific virtual hardware or memory register address.
* **Bits - LIFECYCLE_FLAGS:** Execution and cleanup boundary markers (e.g., `0x0F` = Immediate Tasya Lopaḥ erasure).
* **Binary Image Encoding:** Firmware images serialize each instruction as one big-endian 32-bit word. `build_firmware.py` emits this format and `pvm_hal.c` consumes it directly.

---

### 3. The PSL Deterministic Visibility Model

The current PSL reference model evaluates visibility and privilege constraints deterministically from instruction structure. Task scheduling and hardware-level enforcement are not yet implemented.

* **Virtual Device Namespace:** Fake pointer addresses are replaced by a rigid, isolated Virtual Device Table:
* `0x30` -> `VDEV_VĀK` (System Character/Serial Output Stream)
* `0x50` -> `VDEV_ŚROTRA` (System Audio/Sensor Input Stream)
* `0x60` -> `VDEV_YANTRA` (Core Direct Memory Access Execution Rail)


* **Siddha-Asiddha Boundary Gate:** Registers `< 0x50` are **Siddha (Globally Manifest)**; writes commit immediately to the visible reference-model bus. Registers `>= 0x50` are **Asiddha (Invisible/Shadow)**; modifications are isolated inside the reference model's shadow cache. Hardware/MMIO enforcement is a later implementation milestone.

### 4. RV32 System-Emulated Firmware Proof

The verified RV32 target embeds the compiled PSL image into freestanding firmware and executes it under the QEMU `virt` machine with `-bios none`. The linker places code and mutable state in emulated RAM beginning at `0x80000000`. Firmware trace output is emitted through a volatile write to the `virt` machine UART MMIO address `0x10000000`.

This proof establishes system-emulated MMIO output and RAM-backed decoder state. It does not yet establish execution on physical silicon or an HDL gate-array implementation.
