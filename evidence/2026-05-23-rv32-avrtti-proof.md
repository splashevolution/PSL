# RV32 Avrtti Proof Record — Sprint 3

## Claim Tested

Avrtti bounded repetition: a rule marked with count N in the instruction
word executes exactly N times on freestanding RV32 firmware under QEMU
virt system emulation. No branch predictor. No runtime loop variable.
The bound is decoded directly from bits [27:24] of the ABI word.

## Execution Output

```text
[RV32 PVM BOOT] Sprint 3 — Avrtti bounded repetition firmware
[RV32 PVM] Srotra preloaded with 0xA5
[RV32 PVM] word=0x230530F0 count=03 repeat=03
  AVRTTI: applying rule 03 times (bound from instruction word)
    [cycle 01] target=0x30
      SIDDHA global=0xFF
    [cycle 02] target=0x30
      SIDDHA global=0xFF
    [cycle 03] target=0x30
      SIDDHA global=0xFF
[RV32 PVM] word=0x00CC60F2 count=00 repeat=01
    [cycle 01] target=0x60
      ASIDDHA shadow=0xFF global=0x00
[RV32 PVM AVRTTI SUMMARY] avrtti_cycles=0x03 VAK=0xFF YANTRA_shadow=0xFF apavada_fired=0x01 rejected=0x00
```
