# RV32 Paribhasha Proof Record -- Sprint 7

## Claim Tested

Paribhasha compile-time meta-rule enforcement:
  (A) Three named violations are correctly rejected by the compiler.
  (B) A valid program satisfying all constraints compiles and executes.

## P1: Anuvrtti-at-start  [compiler rejected]
## P2: Lopa-on-unwritten  [compiler rejected]
## P3: Vrddhi-on-Siddha   [compiler rejected]

## Expected ABI Words (valid program)

```
0x200530F0
0x210500F0
0x200030F0
0x00CC60F0
```

## Execution Output

```text
[RV32 PVM BOOT] Sprint 7 -- Paribhasha valid-program proof
[RV32 PVM] word=0x200530F0 ring=0x02 op=0x05 target=0x30
  WRITE Siddha bus[0x30]=0xFF
[RV32 PVM] word=0x210500F0 ring=0x02 op=0x05 target=0x00
  ANUVRTTI: inherited target=0x30
  WRITE Siddha bus[0x30]=0xFF
[RV32 PVM] word=0x200030F0 ring=0x02 op=0x00 target=0x30
  LOPA: bus[0x30] erased -> 0x00, boundary set
[RV32 PVM] word=0x00CC60F0 ring=0x00 op=0xCC target=0x60
  STORE Ring0 Asiddha shadow[0x60]=0xFF (P3 satisfied: target >= 0x50)
[RV32 PVM PARIBHASHA SUMMARY] siddha_writes=0x02 anuvrtti_inherited=0x01 lopa_erasures=0x01 asiddha_stores=0x01 VAK_after_lopa=0x00 YANTRA_shadow=0xFF
```
