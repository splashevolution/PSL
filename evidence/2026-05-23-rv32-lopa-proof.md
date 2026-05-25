# RV32 Lopa Proof Record — Sprint 5

## Claim Tested

Lopa structured erasure: an explicit Lopa instruction zeroes a Siddha
bus entry and resets the Anuvrtti carry register, preventing any
subsequent inheritance from crossing the erasure boundary. Proven on
freestanding RV32 firmware under QEMU virt system emulation.

## Execution Output

```text
[RV32 PVM BOOT] Sprint 5 — Lopa structured erasure firmware
[RV32 PVM] word=0x200530F0 comp=0x00 op=0x05 target=0x30
  EXPLICIT: target=0x30 recorded, Lopa boundary cleared
  SIDDHA global=0xFF
[RV32 PVM] word=0x200030F0 comp=0x00 op=0x00 target=0x30
  LOPA: bus[0x30] erased -> 0x00
  LOPA BOUNDARY SET: Anuvrtti inheritance reset
[RV32 PVM] word=0x210500F0 comp=0x01 op=0x05 target=0x00
  LOPA BOUNDARY: Anuvrtti inheritance blocked — no valid context after erasure
[RV32 PVM LOPA SUMMARY] lopa_erasures=0x01 blocked_inheritances=0x01 VAK_after_lopa=0x00 explicit_writes=0x01 rejected=0x00
```
