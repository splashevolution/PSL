# PSL vs C — Tiny Comparative Examples

**Date:** 2026-05-23
**Purpose:** Show concretely what each PSL semantic concept buys structurally,
compared to the equivalent pattern in C. Not benchmarks. Not performance claims.
Structure only.

The question each example answers: *what must the programmer get right manually
in C that PSL enforces structurally?*

---

## Preamble: What "Structural Enforcement" Means

In C, a programmer writes operations in sequence. The compiler checks types
and syntax but not the semantic relationships between operations — whether a
write happened before a read, whether a pointer is still valid, whether a
privilege transition is correctly scoped. Those properties are the programmer's
responsibility, checked at runtime (if at all).

In PSL, several of those semantic relationships are **structurally inexpressible**
if they are invalid. The compiler does not warn — it does not produce binary.
The illegal program has no representation in the ABI.

This distinction matters: a warning can be suppressed. A structural impossibility
cannot.

---

## Example 1 — Paribhāṣā P2: Lopa on Unwritten Target

**Concept:** Lopa (structured erasure) requires that the target was previously
written. Erasing something that was never written is incoherent.

### C
```c
volatile uint8_t *vak = (volatile uint8_t *)0x30;

/* BUG: no prior write; this nullifies a register that was never set.
   The C compiler does not catch this. The hardware executes it silently.
   Whether this is a bug depends on runtime state the compiler cannot see. */
*vak = 0x00;   /* "lopa" — but was 0x30 ever written? unknown */
```

The C programmer must track, by convention, whether a prior write occurred.
Nothing in the language prevents the erasure.

### PSL
```
तन्त्रशास्त्रम् {
    वाचम् लोपः ।        # COMPILE ERROR: P2 Lopa-on-unwritten
}                        # वाचम् (0x30) has not been written
```

```
तन्त्रशास्त्रम् {
    वाचम् लिखति ।       # write 0x30 → W = {0x30}
    वाचम् लोपः ।        # OK: 0x30 ∈ W
}
```

**What PSL buys:** The written-target set `W` is maintained by the compiler.
A Lopa on an address not in `W` is a compile-time error — no binary is produced.
The programmer cannot accidentally erase an unwritten register; the language
structure prevents it.

---

## Example 2 — Paribhāṣā P1: Anuvrtti-at-Start

**Concept:** Anuvrtti (context inheritance) means "inherit the target from the
previous instruction." There must be a previous instruction with an explicit target.

### C
```c
void write_device(volatile uint8_t *addr, uint8_t val);

/* BUG: called before any prior write establishes context.
   In C, functions take explicit arguments — there is no "inherit from caller."
   But in systems code, implicit context is often threaded through globals
   or uninitialized registers. */
void apply_rule(void) {
    write_device(prev_target, 0xFF);  /* where does prev_target come from? */
}
```

In practice, C systems threads context through global variables, function
parameters, or register conventions — all of which are invisible to the
compiler's type checker.

### PSL
```
तन्त्रशास्त्रम् {
    लिखति ।             # COMPILE ERROR: P1 Anuvrtti-at-start
}                        # no prior instruction to inherit from
```

```
तन्त्रशास्त्रम् {
    वाचम् लिखति ।       # explicit: target = 0x30, prev_target = 0x30
    लिखति ।             # OK: inherits 0x30 from above
    लिखति ।             # OK: inherits 0x30 (chain)
}
```

**What PSL buys:** The compiler tracks `prev_target` as a compile-time register.
An Anuvrtti instruction with no prior context is structurally ill-formed — not
a warning, not undefined behaviour, but a named violation (`P1`) with a precise
error message. The chain of inheritance is explicit in the IR (`COMP_ANUVRTTI`
field), not hidden in a calling convention.

---

## Example 3 — Paribhāṣā P3 + P4: Privilege Correctness

**Concept:** Ring₀ (kernel-level) operations must target Asiddha (isolated)
registers only, and must appear inside an explicit privilege scope block.

### C
```c
#define ISOLATED_REG   0x60
#define VISIBLE_REG    0x30
#define KERNEL_OP      __attribute__((section(".privileged")))

/* No structural enforcement of privilege. The compiler will compile this.
   Whether it is correct depends on runtime privilege state. */
volatile uint8_t *isolated = (volatile uint8_t *)ISOLATED_REG;
volatile uint8_t *visible  = (volatile uint8_t *)VISIBLE_REG;

void bad_kernel_write(void) {
    /* Ring 0 on a globally-visible address: P3 violation.
       C does not know this is wrong. */
    *visible = 0xFF;    /* privileged write to shared bus? */
}

void unscoped_kernel_write(void) {
    /* Ring 0 outside any privilege scope: P4 violation.
       No scope declaration, no audit boundary, no structural record. */
    *isolated = 0xFF;
}
```

Enforcing privilege correctness in C requires runtime checks, linker sections,
or OS primitives — all external to the language's type system.

### PSL
```
# P3 violation — Ring₀ on Siddha (globally-visible) target
तन्त्रशास्त्रम् {
    अधिकारः {
        वाग्यन्थ्रैः लिखति ।  # COMPILE ERROR: P3 Vrddhi-on-Siddha
    }                          # 0x30 < 0x50: Siddha target, Ring₀ invalid
}

# P4 violation — Ring₀ outside scope
तन्त्रशास्त्रम् {
    यन्त्रम् स्थापयति ।       # COMPILE ERROR: P4 Ring0-outside-scope
}                              # Ring₀ Store with no enclosing अधिकारः block
```

```
# Correct — both P3 and P4 satisfied
तन्त्रशास्त्रम् {
    वाचम् लिखति ।             # Ring₂, Siddha target: OK
    अधिकारः {
        यन्त्र स्थापयति ।     # Ring₀ promoted, Asiddha target: OK
    }
    वाचम् लिखति ।             # Ring₂ restored: OK
}
```

**What PSL buys:** Two structural guarantees enforced simultaneously:

- *P3*: The address space partition (Siddha/Asiddha) is a compile-time type
  distinction. Ring₀ on a Siddha address is a category error — not a runtime
  fault, not a memory protection violation, but a compile-time structural
  impossibility.

- *P4*: Privileged operations require an explicit lexical scope declaration
  (`अधिकारः { }`). There is no way to emit a Ring₀ instruction outside a
  scope in valid PSL. Every Ring₀ operation in the binary is auditable by
  finding the enclosing scope in the source.

---

## Example 4 — Sandhi: Atomic Pair Declaration

**Concept:** Sandhi (instruction fusion) declares that two instructions must
execute as an atomic pair. The compiler enforces five compatibility rules at
compile time.

### C
```c
volatile uint8_t *yantra = (volatile uint8_t *)0x60;

/* Intent: write then store atomically.
   C has no atomic compound write primitive for MMIO.
   Solutions are runtime: lock, memory barrier, or platform-specific pragma. */
__sync_synchronize();   /* memory barrier — runtime, not structural */
*yantra = 0xFF;         /* write */
*yantra = 0xFF;         /* store (same address, different semantics?) */
__sync_synchronize();

/* What the compiler does NOT check:
   - that both operations target the same address (S2)
   - that neither is a Lopa (S1)
   - that both are in the same privilege ring (S4)
   - that the target was not previously erased (S5)
   The programmer asserts these properties by convention. */
```

### PSL
```
# S2 violation — different targets
तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    सन्धिः ।
    यन्त्र स्थापयति ।    # COMPILE ERROR: S2 target mismatch (0x30 ≠ 0x60)
}

# S1 violation — Lopa is not write-class
तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    वाचम् लोपः ।
    सन्धिः ।
    वाचम् लिखति ।        # COMPILE ERROR: S1 (Lopa before sentinel is not write-class)
}
```

```
# Correct Sandhi
तन्त्रशास्त्रम् {
    वाचम् लिखति ।         # standalone (not fused)
    यन्त्र लिखति ।        # first of pair — FLAGS=0xE in binary
    सन्धिः ।
    यन्त्र स्थापयति ।     # second of pair — atomic with above
}
```

ABI output:
```
0x200530F0  -- Write Vak    (standalone,    FLAGS=0xF)
0x200560E0  -- Write Yantra (SANDHI-FIRST,  FLAGS=0xE) ← fused
0x20CC60F0  -- Store Yantra (SANDHI-PAIR,   FLAGS=0xF) ← atomic with above
```

**What PSL buys:** The five Sandhi rules (S1–S5) are compile-time checks, not
runtime contracts. A declared fusion that violates any rule produces a named
`SandhiError` with the specific rule, the two source lines, and the detail.
The programmer cannot accidentally declare an incoherent atomic pair — the
declaration itself is the check.

The `FLAGS=0xE` bit in the binary is a structural consequence of the source
declaration, not a pragma or annotation. It is always present on a first-of-pair
word, always absent otherwise. No runtime code chooses it.

---

## Example 5 — Anuvrtti: Inheritance Chain vs Repetition

**Concept:** The difference between Anuvrtti (inherit-and-extend) and Avrtti
(bounded repetition) — two distinct compression strategies that look similar
in C but have different binary encodings and semantic contracts.

### C
```c
volatile uint8_t *vak = (volatile uint8_t *)0x30;

/* Repetition (Avrtti): same instruction N times */
for (int i = 0; i < 3; i++) *vak = 0xFF;

/* Inheritance chain (Anuvrtti): implicit carry of context */
void write_vak(void)   { *vak = 0xFF; }
void write_again(void) { write_vak(); }  /* "inherits" by calling same fn */
void and_again(void)   { write_vak(); }
```

In C, both patterns look like function calls or loops. The distinction between
"repeat with same target" and "inherit target from context" is invisible to the
compiler — both produce the same machine code.

### PSL
```
# Avrtti — bounded repetition: ONE word, COMP field = 3
तन्त्रशास्त्रम् {
    वाचम् आवृत्तिः ३ लिखति ।  # word: 0x230530F0 (COMP=3)
}
# Binary: ONE instruction word. Firmware executes it 3 times.

# Anuvrtti — inheritance chain: THREE words, COMP field = 1
तन्त्रशास्त्रम् {
    वाचम् लिखति ।   # word: 0x200530F0 (explicit, COMP=0)
    लिखति ।          # word: 0x210030F0 (anuvrtti, COMP=1, TARGET=0x00)
    लिखति ।          # word: 0x210030F0 (anuvrtti, COMP=1, TARGET=0x00)
}
# Binary: THREE instruction words. Each fires once.
```

The difference is encoded in the `COMP/COUNT` field:

| Pattern | COMP field | Words in binary | Firmware behaviour |
|---------|-----------|-----------------|-------------------|
| Avrtti ×3 | `0x3` | 1 word | Execute same instruction 3× |
| Anuvrtti ×2 | `0x1` | 3 words | Execute 3 distinct instructions, target inherited |

**What PSL buys:** Two semantically distinct compression strategies have
distinct ABI encodings. A reviewer inspecting the binary can distinguish them
without runtime tracing. The encoding is not an optimization hint — it is a
semantic declaration that changes what the firmware does.

---

## Example 6 — Sañjñā: Compile-Time Named Abstraction

**Concept:** Sañjñā binds a Sanskrit name to a device address at compile time.
All uses of the name in source resolve to the same address. The name does not
exist in the binary.

### C
```c
/* Option A: #define — no type, no scope, no error on misuse */
#define YANTRA_REG  0x60
*((volatile uint8_t *)YANTRA_REG) = 0xFF;

/* Option B: const — typed, but address is embedded by the linker,
   not resolved by the compiler at the instruction level */
const uint32_t YANTRA_ADDR = 0x60;
*((volatile uint8_t *)YANTRA_ADDR) = 0xFF;

/* Option C: enum — integer only, no pointer semantics */
enum { YANTRA = 0x60 };
```

None of these guarantee that the name `YANTRA` and the literal `0x60` are
interchangeable in the emitted binary — the compiler may or may not fold them
depending on optimization level.

### PSL
```
सञ्ज्ञा यन्त्र = 0x60 ।

तन्त्रशास्त्रम् {
    यन्त्र लिखति ।   # resolves to 0x60 at compile time
    यन्त्र लोपः ।    # resolves to 0x60 at compile time
}
```

Emits: `[0x200560F0, 0x200060F0]` — identical to using `0x60` directly.

**Verified by firmware proof (Sprint 6):** The pipeline compiles both the
Sañjñā version and the direct-address version and asserts byte identity.
The firmware cannot distinguish them. The name exists only in the source.

**What PSL buys:** The Sañjñā table is resolved in the compiler's first pass,
before any IR is built. There is no runtime indirection, no symbol table in the
binary, no address-of-name operation. The abstraction cost is exactly zero —
provably, because the pipeline verifies binary identity.

---

## Summary: What Each Concept Enforces

| PSL Concept | C equivalent burden | PSL structural guarantee |
|-------------|--------------------|-----------------------------|
| P1 Anuvrtti-at-start | Manual: track whether prior write exists | Compiler: `prev_target` is a compile-time register; Anuvrtti-first is structurally ill-formed |
| P2 Lopa-on-unwritten | Manual: track written state per address | Compiler: `W` (written-target set) is maintained; Lopa on `addr ∉ W` is rejected |
| P3 Vrddhi-on-Siddha | Manual: check address range before Ring₀ write | Compiler: Siddha/Asiddha is a type distinction; Ring₀ on Siddha is a category error |
| P4 Ring0-outside-scope | Manual: ensure privilege mode is set; typically OS-enforced | Compiler: Ring₀ requires lexical `अधिकारः` block; no ring promotion without it |
| Sandhi S1–S5 | Manual: assert atomicity contracts by convention | Compiler: five compatibility rules checked per declared fusion; named error per rule |
| Sañjñā | Manual: `#define` or `const`; correctness by convention | Compiler: two-pass resolution; binary identity provable per sprint |
| Avrtti vs Anuvrtti | Indistinguishable in C binary; compiler choice | ABI-distinct COMP encodings; firmware behaviour differs; human-readable in binary |

---

## What This Is Not Claiming

**Not claiming:** PSL is faster than C. Performance is not the point.

**Not claiming:** PSL is more expressive than C. C can express anything.

**Not claiming:** These properties cannot be enforced in C with tools. They can —
with external static analysers, Frama-C, or MISRA rules. But those are external
to the language, added after the fact, and optional.

**Claiming:** In PSL, these properties are enforced by the structure of the
language itself. They are not optional. They cannot be suppressed. The compiler
either produces binary satisfying all of them, or it produces no binary at all.

That is the structural argument. The RV32 firmware proofs are evidence that
the compiler's guarantees transfer to real hardware execution. They are not
the argument itself.

---

*End of comparative examples.*
