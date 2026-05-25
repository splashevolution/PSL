# Sprint 12 Proof Record — Safety-Critical Control DSL

**Date:** 2026-05-23  
**Sprint:** 12  
**Title:** Safety-Critical Control DSL — Pressure-Relief Valve Safety Interlock  
**Result:** 26/26 PASS

---

## Scenario

A pressure management safety controller must sequence actuator operations
in a structurally correct order. Four bug classes are prevented at compile
time by PSL's structural type system — they cannot be expressed in valid PSL
source, so no binary containing them can be produced.

**Address map:**
| Address | Region   | Ring | Device              |
|---------|----------|------|---------------------|
| 0x30    | Siddha   | 2    | Pressure sensor bus |
| 0x50    | Asiddha  | 0    | Valve actuator      |
| 0x60    | Asiddha  | 0    | Safety interlock    |

---

## PSL Source (safety_interlock.pvm)

```
सञ्ज्ञा दबाव = 0x30 ।
सञ्ज्ञा वाल्व = 0x50 ।
सञ्ज्ञा इन्टरलॉक = 0x60 ।

तन्त्रशास्त्रम् {
    दबाव लिखति ।              # Signal: starting (Ring2, Siddha)
    अधिकारः {
        वाल्व स्थापयति ।      # Primary valve open (Ring0, Asiddha)
        स्थापयति ।             # Secondary valve — Anuvrtti (inherit 0x50)
        इन्टरलॉक स्थापयति ।  # Interlock configure (SANDHI-FIRST)
        सन्धिः ।
        इन्टरलॉक स्थापयति ।  # Interlock arm (atomic with above)
    }
    दबाव लिखति ।              # Signal: complete (Ring2, Siddha)
}
```

---

## ABI Output (8 words, 32 bytes, big-endian)

| Index | Word       | Meaning                                      |
|-------|------------|----------------------------------------------|
| 0     | 0x200530F0 | Write दबाव  Ring2 0x30 (sensor status start) |
| 1     | 0x00AA00F0 | ADHIKARA_OPEN                                |
| 2     | 0x00CC50F0 | Store वाल्व Ring0 0x50 (primary valve)       |
| 3     | 0x01CC00F0 | Store Anuvrtti Ring0 inherit 0x50 (COMP=1)   |
| 4     | 0x00CC60E0 | Store इन्टरलॉक Ring0 0x60 (SANDHI-FIRST)    |
| 5     | 0x00CC60F0 | Store इन्टरलॉक Ring0 0x60 (SANDHI-PAIR)     |
| 6     | 0x00BB00F0 | ADHIKARA_CLOSE                               |
| 7     | 0x200530F0 | Write दबाव  Ring2 0x30 (sensor status done)  |

---

## Bug Classes Prevented Structurally

| Bug   | Rule | Description                                  | Evidence                        |
|-------|------|----------------------------------------------|---------------------------------|
| BUG-1 | P4   | Ring0 valve write outside privilege scope    | P4 compile error confirmed A12  |
| BUG-2 | P3   | Ring0 write to shared sensor bus (Siddha)    | P3 compile error confirmed A13  |
| BUG-3 | S1-5 | Non-atomic configure-then-arm interlock      | FLAGS=0xE in binary, A8         |
| BUG-4 | P1   | Anuvrtti with no prior explicit write        | P1 compile error confirmed A14  |

New in Sprint 12 vs Sprint 11: BUG-4 (P1 / Anuvrtti chain) is an additional
structural guarantee demonstrated here. Anuvrtti inside an Adhikāra scope
(word[3]: COMP=1, Ring0, TARGET=0x00) proves the inheritance chain is
structurally provable — the compiler tracks `prev_target` at compile time,
not at runtime.

---

## Part A Results (14/14)

- A1-A3: ABI byte/word counts and byte order correct
- A4-A11: All 8 ABI words match expected encoding exactly
- A12: P4 violation (Ring0 outside scope) — `ParibhashaError [P4]` ✓
- A13: P3 violation (Ring0 on Siddha 0x30) — `ParibhashaError [P3]` ✓
- A14: P1 violation (Anuvrtti at start) — `ParibhashaError [P1]` ✓

---

## Part B Results (12/12) — RV32 QEMU Firmware

UART summary line:
```
[RV32 PVM SAFETY INTERLOCK SUMMARY] sensor_writes=0x02 scope_opens=0x01
valve_stores=0x01 anuvrtti_stores=0x01 interlock_stores=0x02
sandhi_pairs=0x01 scope_closes=0x01 BUG1_prevented=0x01
BUG2_prevented=0x01 BUG3_atomic=0x01 BUG4_chain=0x01
```

All 12 UART markers confirmed on freestanding RV32 QEMU hardware.

---

## What Sprint 12 Adds Over Sprint 11

Sprint 11 demonstrated P3, P4, and Sandhi (BUG-1, BUG-2, BUG-3) in a boot
sequencer scenario. Sprint 12 adds:

1. **P1 / Anuvrtti chain (BUG-4):** An Anuvrtti instruction inside a
   privileged scope (COMP=1, Ring0) proves that the inheritance chain
   is structurally provable. The compiler tracks `prev_target` at compile
   time; the firmware confirms `BUG4_chain=0x01` — every Anuvrtti word
   in the binary has a provable explicit-write ancestor.

2. **Domain transfer:** The same three structural mechanisms (P4 scope,
   P3 address partition, Sandhi atomicity) apply unchanged to a different
   real-world domain — safety-critical actuator control — without any
   compiler changes. PSL's structural guarantees are domain-agnostic.

---

*Pipeline: run_rv32_safety_interlock_pipeline.py — 26/26 PASS*
