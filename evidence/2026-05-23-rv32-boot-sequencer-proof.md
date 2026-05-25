# RV32 Boot Sequencer Proof Record — Sprint 11

**Date:** 2026-05-23  
**Result:** PASS 26/26 (14 compiler + 12 firmware)

## Scenario

Privilege-separated peripheral initialization — a boot ROM initialises
three hardware peripherals with structural correctness guarantees:

1. Boot status register (0x30, Siddha, Ring₂) — shared status bus
2. Clock control register (0x50, Asiddha, Ring₀) — isolated, privileged
3. Security lock register (0x60, Asiddha, Ring₀) — isolated, Sandhi-fused

## Bug Classes Structurally Prevented

| Bug | Rule | Prevention |
|-----|------|------------|
| BUG-1: Unscoped Ring₀ write | P4 | Ring₀ without अधिकारः cannot compile |
| BUG-2: Ring₀ on shared bus | P3 | Ring₀ on addr < 0x50 cannot compile |
| BUG-3: Non-atomic configure-then-lock | Sandhi | FLAGS=0xE enforces atomic pair |

## Source Program (boot_sequencer.pvm)

```
सञ्ज्ञा घड़ी = 0x50 ।
सञ्ज्ञा सुरक्षा = 0x60 ।

तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    अधिकारः {
        घड़ी स्थापयति ।
        सुरक्षा स्थापयति ।
        सन्धिः ।
        सुरक्षा स्थापयति ।
    }
    वाचम् लिखति ।
}
```

## ABI Words Emitted (7 words, 28 bytes)

```
0x200530F0  Write  boot_status  Ring₂  Siddha   standalone
0x00AA00F0  ADHIKARA_OPEN
0x00CC50F0  Store  clock_ctrl   Ring₀  Asiddha  inside scope
0x00CC60E0  Store  sec_lock     Ring₀  Asiddha  SANDHI-FIRST (FLAGS=0xE)
0x00CC60F0  Store  sec_lock     Ring₀  Asiddha  SANDHI-PAIR  (atomic)
0x00BB00F0  ADHIKARA_CLOSE
0x200530F0  Write  boot_status  Ring₂  Siddha   confirm
```

## Hex dump

```
20 05 30 F0 00 AA 00 F0 00 CC 50 F0 00 CC 60 E0 00 CC 60 F0 00 BB 00 F0 20 05 30 F0
```

## UART Summary (freestanding RV32 QEMU)

```
[RV32 PVM BOOT SEQUENCER SUMMARY]
status_writes=0x02 scope_opens=0x01 clock_stores=0x01
lock_stores=0x02 sandhi_pairs=0x01 scope_closes=0x01
BUG1_prevented=0x01 BUG2_prevented=0x01 BUG3_atomic=0x01
```
