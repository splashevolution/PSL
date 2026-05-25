# RV32 Anuvrtti Proof Record — Sprint 4

## Claim Tested

Anuvrtti context inheritance: a PSL instruction with no stated target
compiles to COMPRESSION=0x1 TARGET=0x00. The firmware resolves the
target at decode time from the previous instruction's target register.
Both the explicit and compressed instructions commit to the same Siddha
bus entry under freestanding RV32 QEMU virt system emulation.

## Execution Output

```text
[RV32 PVM BOOT] Sprint 4 — Anuvrtti context inheritance firmware
[RV32 PVM] word=0x200530F0 comp=0x00 target=0x30
  EXPLICIT: target=0x30 recorded as Anuvrtti context
  SIDDHA global=0xFF
[RV32 PVM] word=0x210500F0 comp=0x01 target=0x00
  ANUVRTTI: inherited target=0x30 from previous instruction
  SIDDHA global=0xFF
[RV32 PVM ANUVRTTI SUMMARY] explicit_writes=0x01 inherited_writes=0x01 VAK=0xFF rejected=0x00
```
