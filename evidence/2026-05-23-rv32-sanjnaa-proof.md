# RV32 Sanjnaa Proof Record — Sprint 6

## Claim Tested

Sanjnaa compile-time symbol resolution: symbolic names declared via
सञ्ज्ञा compile to byte-for-byte identical ABI words as built-in Karaka
terms. The symbol table is erased before the binary is emitted.
Zero runtime overhead. Proven on freestanding RV32 QEMU virt emulation.

## Expected ABI Words

```
0x200530F0
0x200550F0
0x200030F0
0x210500F0
```

## Execution Output

```text
[RV32 PVM BOOT] Sprint 6 — Sanjnaa compile-time symbol resolution
[RV32 PVM] word=0x200530F0 op=0x05 target=0x30
  SIDDHA global=0xFF (Sanjnaa symbol resolved to 0x30)
[RV32 PVM] word=0x200550F0 op=0x05 target=0x50
  ASIDDHA shadow=0xFF (Sanjnaa symbol resolved to 0x50)
[RV32 PVM] word=0x200030F0 op=0x00 target=0x30
  LOPA: bus[0x30] erased -> 0x00, boundary set
[RV32 PVM] word=0x210500F0 op=0x05 target=0x00
  LOPA BOUNDARY: Anuvrtti inheritance blocked
[RV32 PVM SANJNAA SUMMARY] sanjnaa_writes=0x02 lopa_erasures=0x01 blocked_inheritances=0x01 VAK_after_lopa=0x00 SROTRA_shadow=0xFF rejected=0x00
```
