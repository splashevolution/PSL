# Prakriya IR Proof Record -- Sprint 8

## Claim Tested

The Prakriya (Semantic IR) layer sits between parsing and binary
emission. Every instruction is resolved into an IRNode before any
binary is produced. The IR is transparent: binary output is
byte-for-byte identical to the legacy direct-emit path.

## IR Output (paribhasha_valid_core.pvm)

```
[paribhasha_valid_core Prakriya] 4 instruction(s):
  line17   ring=Ring2  op=0x05  target=0x30       comp=0x0  cond=0x0  word=0x200530F0 [SIDDHA]  {P1-ok P2-ok P3-ok}
  line20   ring=Ring2  op=0x05  target=inherited  comp=0x1  cond=0x0  word=0x210500F0  {P1-ok P2-ok P3-ok}
  line23   ring=Ring2  op=0x00  target=0x30       comp=0x0  cond=0x0  word=0x200030F0 [SIDDHA]  {P1-ok P2-ok P3-ok}
  line26   ring=Ring0  op=0xCC  target=0x60       comp=0x0  cond=0x0  word=0x00CC60F0 [ASIDDHA]  {P1-ok P2-ok P3-ok}
```

## Proofs

- PROOF 1: Binary identity across 5 sprint sources: PASS
- PROOF 2: IR inspection -- all semantic properties visible: PASS
- PROOF 3: Paribhasha caught at validate_ir(): PASS (P1, P2, P3)
- PROOF 4: Region field (SIDDHA/ASIDDHA) correctly resolved: PASS
- PROOF 5: Constraint tracking -- P1-ok P2-ok P3-ok per node: PASS
