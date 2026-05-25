# RV32 Adhikara Proof Record -- Sprint 10

## Concept

Adhikara (privilege scope): a block-level declaration sets Ring 0 for
all instructions within it, with automatic restoration to Ring 2 on exit.
P4 Paribhasha rule: Ring-0 instruction outside an Adhikara block is a
compile-time error.

## Source Program

```
# SPRINT 10: Adhikāra -- Privilege Scope Domains
#
# Adhikāra (Sanskrit: "authority / jurisdiction") -- a header rule in the
# Aṣṭādhyāyī that governs all sūtras within its domain. Its authority
# extends until explicitly closed or superseded. Here: a block-level
# declaration that sets Ring 0 for all instructions within it, with
# automatic restoration to Ring 2 on exit.
#
# ABI words emitted by this program:
#
#   0x200530F0  -- Write Vak (Ring 2, outside scope, standalone)
#   0x0000AAF0  -- ADHIKARA_OPEN  (scope-open sentinel)
#   0x0000CC60F0  -- Store Yantra (Ring 0, inside scope -- valid by P4)
#   0x0000BBF0  -- ADHIKARA_CLOSE (scope-close sentinel)
#   0x200530F0  -- Write Vak (Ring 2, outside scope, restored)
#
# Note: inside the अधिकारः block, Ring 0 is in effect for all instructions.
# The compiler validates that Ring-0 instructions appear only inside such blocks.
# Outside the block, Ring 2 is restored automatically.
#
# P4 violation (rejected at compile time):
#   तन्त्रशास्त्रम् {
#       यन्त्रम् स्थापयति ।   <-- Ring 0 Store outside Adhikara block -> P4
#   }
#
# Expected UART:
#   ring2_writes=0x02  adhikara_opens=0x01  adhikara_closes=0x01
#   ring0_stores=0x01  scope_restored=0x01

सञ्ज्ञा यन्त्र = 0x60 ।

तन्त्रशास्त्रम् {
    # Ring 2 -- outside scope
    वाचम् लिखति ।

    # Enter privileged scope
    अधिकारः {
        # Ring 0 in effect here
        यन्त्र स्थापयति ।
    }

    # Ring 2 restored -- outside scope again
    वाचम् लिखति ।
}
```

## ABI Words Emitted

```
0x200530F0  Write Vak (Ring2, outside scope)
0x00AA00F0  ADHIKARA_OPEN
0x00CC60F0  Store Yantra (Ring0, inside scope)
0x00BB00F0  ADHIKARA_CLOSE
0x200530F0  Write Vak (Ring2, restored)
```

## P4 Violation Rejected (Part A)

- Ring-0 instruction outside Adhikara block -- correctly rejected

## QEMU UART Output

```text
[RV32 PVM BOOT] Sprint 10 -- Adhikara privilege scope
[RV32 PVM] word=0x200530F0 op=0x05 scope=Ring2
    WRITE Ring2 bus[0x30]=0xFF
[RV32 PVM] word=0x00AA00F0 op=0xAA scope=Ring2
  ADHIKARA_OPEN: scope_ring -> Ring0
[RV32 PVM] word=0x00CC60F0 op=0xCC scope=Ring0
    STORE Ring0 shadow[0x60]=0xFF
[RV32 PVM] word=0x00BB00F0 op=0xBB scope=Ring0
  ADHIKARA_CLOSE: scope_ring -> Ring2
[RV32 PVM] word=0x200530F0 op=0x05 scope=Ring2
    WRITE Ring2 bus[0x30]=0xFF
[RV32 PVM ADHIKARA SUMMARY] ring2_writes=0x02 adhikara_opens=0x01 adhikara_closes=0x01 ring0_stores=0x01 scope_restored=0x01 VAK_bus=0xFF YANTRA_shadow=0xFF
```
