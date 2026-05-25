# RV32 Conditional Proof Record — Sprint 2

## Claim Tested

Utsarga/Apavada conditional rule application compiles from PSL source,
embeds into freestanding RV32 firmware, and produces observable Paninian
precedence behaviour via UART MMIO under QEMU virt system emulation.

## Execution Output

```text
[RV32 PVM BOOT] Sprint 2 — Utsarga/Apavada conditional firmware
[RV32 PVM] Srotra preloaded with 0xA5 (input signal present)
[RV32 PVM] word=0x200530F1 target=0x30 cond=0x01
  UTSARGA SKIPPED — Apavada takes precedence (Srotra signal present)
[RV32 PVM] word=0x00CC60F2 target=0x60 cond=0x02
  APAVADA FIRED — Ring 0 store to Yantra shadow committed
  ASIDDHA shadow=0xFF global=0x00
[RV32 PVM CONDITIONAL SUMMARY] VAK=0x00 YANTRA_shadow=0xFF utsarga_skipped=0x01 apavada_fired=0x01 rejected=0x00
```
