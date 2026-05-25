# RV32 Sandhi Proof Record -- Sprint 9

## Concept

Sandhi (instruction fusion): two adjacent compatible instructions fuse into an
atomic execution pair. The first word carries FLAGS=0xE (SANDHI-FIRST). The
firmware executes both before advancing. Five compatibility rules (S1-S5) must
all hold; any violation is rejected by the compiler at parse time.

## Source Program

```
# SPRINT 9: Sandhi -- Instruction Fusion
#
# Sandhi (Sanskrit: "junction", "combination") -- when two sounds meet at a
# word boundary they fuse according to phonological rules into a single surface
# form. The fusion is governed by explicit compatibility rules. Not all
# combinations are valid; only those satisfying all rules produce a fused form.
#
# Here: when two instructions meet in the stream and are declared adjacent by
# the Sandhi directive, they fuse into an atomic execution pair if all five
# compatibility rules are satisfied. The first instruction carries FLAGS=0xE
# (SANDHI-FIRST) in its ABI word. The firmware executes the pair atomically.
#
# Sandhi compatibility rules:
#   S1: Both must be write-class (0x05 Write or 0xCC Store)
#   S2: Both must target the same device address
#   S3: First must be explicit (not Anuvrtti-compressed)
#   S4: Both must be in the same ring level
#   S5: No prior Lopa on the shared target
#
# Program structure:
#   1. Write to Vak (Siddha, 0x30) -- standalone, no fusion
#   2. Write to Yantra (Asiddha, 0x60) -- first of Sandhi pair
#      [सन्धिः -- fusion directive]
#   3. Store to Yantra (Asiddha, 0x60) -- second of Sandhi pair (atomic with 2)
#
# Expected ABI words:
#   0x200530F0  -- Write Vak (standalone, FLAGS=0xF)
#   0x200560E0  -- Write Yantra (SANDHI-FIRST, FLAGS=0xE)
#   0x20CC60F0  -- Store Yantra (SANDHI-PAIR second, FLAGS=0xF)
#
# Expected UART:
#   standalone_writes=0x01  sandhi_fusions=0x01
#   VAK_bus=0xFF  YANTRA_write=0xFF  YANTRA_store=0xFF

सञ्ज्ञा यन्त्र = 0x60 ।

तन्त्रशास्त्रम् {
    # Standalone write to Vak -- not fused
    वाचम् लिखति ।

    # Sandhi pair: Write + Store to Yantra (same target, same ring, both write-class)
    यन्त्र लिखति ।
    सन्धिः ।
    यन्त्र स्थापयति ।
}
```

## ABI Words Emitted

```
0x200530F0  Write Vak (standalone, FLAGS=0xF)
0x200560E0  Write Yantra (SANDHI-FIRST, FLAGS=0xE)
0x20CC60F0  Store Yantra (SANDHI-pair second, FLAGS=0xF)
```

## Sandhi Violations Rejected (Part A)

- S1: Non-write fuse (Lopa) -- correctly rejected
- S2: Target mismatch       -- correctly rejected
- S5: Fuse after Lopa       -- correctly rejected

## QEMU UART Output

```text
[RV32 PVM BOOT] Sprint 9 -- Sandhi instruction fusion
[RV32 PVM] word=0x200530F0 op=0x05 target=0x30 flags=0x0F
    WRITE Siddha bus[0x30]=0xFF
[RV32 PVM] word=0x200560E0 op=0x05 target=0x60 flags=0x0E
  SANDHI: fused pair detected
    first:  op=0x05 target=0x60
    second: op=0xCC target=0x60
    WRITE Asiddha write_cache[0x60]=0xFF
    STORE Asiddha store_cache[0x60]=0xFF
  SANDHI: atomic pair executed, sandhi_fusions++
[RV32 PVM SANDHI SUMMARY] standalone_writes=0x01 sandhi_fusions=0x01 VAK_bus=0xFF YANTRA_write=0xFF YANTRA_store=0xFF
```
