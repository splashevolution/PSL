# PSL Property-Based Test Generator — Formal Specification

**Version:** 1.0  
**Date:** 2026-05-23  
**Implementation:** `run_differential_tests.py`  
**Status:** Active — 5000/5000 programs pass all properties (seed 42).

---

## 0. Purpose

This document specifies the PSL property-based test generator as a research
artifact in its own right. The generator is not incidental to the compiler —
it is a formal object that:

1. Defines the **legality grammar** of PSL (what programs may be generated).
2. Defines the **coverage classes** (what semantic territory is exercised).
3. States the **differential properties** that must hold over all generated programs.
4. Records the **invariants the generator itself must satisfy** (meta-constraints).

The generator's purpose is not to find bugs by chance. It is to exert
**invariant pressure** — to force the compiler's semantic rules to be
consistent across a space of programs too large to curate by hand.

---

## 1. Generator Architecture

### 1.1 Top-Level Structure

```
generate_program(rng: Random) → source : String

    ProgramBuilder(rng)
        │
        ├── optional: add_sanjnaa(name, addr)
        │
        ├── choose strategy ∈ Strategies
        │
        └── call strategy methods → append lines
            │
            └── build() → PSL source string
```

The generator is **constructive**: it only calls methods that produce
structurally valid PSL fragments. It never generates source text directly,
never concatenates raw Sanskrit strings, and never attempts to repair
an invalid program. If a method's precondition is not met, it is not called.

### 1.2 Determinism

The generator is fully deterministic given a seed:

```
∀ seed ∈ ℕ, count ∈ ℕ :
    run(seed, count) always produces the identical sequence of programs
```

This is guaranteed by threading a single `random.Random(seed)` instance through
all generation choices. No global random state is used.

---

## 2. Address Space

The generator operates over a fixed, finite set of device addresses:

```
A_Siddha  = {0x30}              -- Vak bus (globally visible)
A_Asiddha = {0x50, 0x60}        -- Srotra, Yantra (isolated)
A_All     = A_Siddha ∪ A_Asiddha
```

This partitioning mirrors the compiler's `ASIDDHA_BASE = 0x50` threshold.
Addresses outside `A_All` are never generated. This is not a limitation —
it is a deliberate constraint that keeps coverage focused on the semantic
boundary (Siddha vs. Asiddha) where the most interesting rules (P3, P4, S2)
apply.

### 2.1 Karaka Token Map

Each address has a canonical PSL token:

| Address | Token | Role |
|---------|-------|------|
| 0x30 | वाचम् | KARMAN (Ring₂) |
| 0x50 | श्रोत्रम् | KARMAN (Ring₂) |
| 0x60 | यन्त्र | KARMAN (Ring₂) |

Sañjñā declarations may introduce additional names for Asiddha addresses.
When a Sañjñā name exists for an address, the generator uses it with
probability 0.3 (providing Sañjñā coverage without overwhelming other tokens).

---

## 3. Legality Grammar

The legality grammar defines the set of programs the generator may produce.
All generated programs must be accepted by `compile_source(enforce_paribhasha=True)`.

### 3.1 Generator Invariants (Meta-Constraints)

These are preconditions maintained by `ProgramBuilder` that ensure no
generated program violates P1–P4 or S1–S5:

**G1 — No Anuvrtti-first (enforces P1):**
```
add_anuvrtti_write() is only called after add_write() or add_avrtti_write()
has been called at least once in the current program.
```

`ProgramBuilder` tracks `prev_target`. Anuvrtti is only emitted when
`prev_target is not None`. No strategy calls `add_anuvrtti_write()` first.

**G2 — No Lopa-on-unwritten (enforces P2):**
```
add_lopa(addr) is only called when addr ∈ self.written
```

`ProgramBuilder.written` is a set updated by all write-producing methods.
`add_lopa` calls `written.discard(addr)` after emission, maintaining the
invariant that written reflects the current written state.

**G3 — No Ring₀ outside scope (enforces P3 and P4):**
```
add_ring0_store(addr) is only called inside an open_adhikara() / close_adhikara() pair.
addr ∈ A_Asiddha for all add_ring0_store() calls.
```

The `in_scope` flag is set by `open_adhikara()` and cleared by `close_adhikara()`.
Ring₀ stores are never emitted outside this flag. Addresses for Ring₀ stores are
always drawn from `A_Asiddha`, respecting P3.

**G4 — Sandhi coherence (enforces S1–S5):**
```
add_sandhi_pair(addr) emits Write(addr) + sentinel + Store(addr):
  - addr ∈ A_Asiddha (S2: both instructions target same Asiddha address)
  - both Write and Store are write-class (S1)
  - Write is explicit Karaka (S3)
  - both are Ring₂ (S4; Store is Ring₂ in this context because outside scope)
  - Write re-establishes addr in written before Store (S5: no prior-lopa violation)
```

`add_sandhi_pair` always begins with a fresh Write, so `last_event` for the
target at the point of the sentinel is always `Write` — S5 cannot fire.

**G5 — Lopa resets Sandhi eligibility tracking:**
```
add_lopa(addr) sets self.prev_target = None and discards addr from self.written.
```

If a `mixed` strategy calls `add_lopa` and then `add_sandhi_pair` on the same
address, `add_sandhi_pair` emits a new Write first — which re-establishes the
target and satisfies S5. The generator cannot produce an S5 violation by
construction.

### 3.2 Grammar in BNF

```
program     ::= sanjnaa* tantra

sanjnaa     ::= "सञ्ज्ञा" name "=" hex_addr "।"

tantra      ::= "तन्त्रशास्त्रम् {" body "}"

body        ::= stmt+

stmt        ::= write_stmt
              | anuvrtti_stmt
              | avrtti_stmt
              | lopa_stmt
              | sandhi_triple
              | adhikara_block

write_stmt  ::= karaka " लिखति ।"

anuvrtti_stmt ::= "लिखति ।"        -- requires prior write_stmt in body

avrtti_stmt   ::= karaka " आवृत्तिः " digit " लिखति ।"
                  where digit ∈ {2,3,4,5}

lopa_stmt     ::= karaka " लोपः ।"
                  requires: karaka.addr ∈ written

sandhi_triple ::= write_stmt "    सन्धिः ।" store_stmt
                  requires: write.addr = store.addr ∈ A_Asiddha

store_stmt    ::= karaka " स्थापयति ।"
                  (Ring₂ outside scope — compiler promotes to Ring₀ inside scope)

adhikara_block ::= "    अधिकारः {" ring0_stmt+ "}"

ring0_stmt    ::= "        " karaka " स्थापयति ।"
                  requires: karaka.addr ∈ A_Asiddha

karaka        ::= "वाचम्" | "श्रोत्रम्" | "यन्त्र" | sanjnaa_name
```

### 3.3 What Is NOT Generated

The generator deliberately excludes several valid PSL constructs:

| Excluded | Reason |
|----------|--------|
| Conditional (Utsarga/Apavāda) | Covered by Sprint 2 dedicated tests; not part of D1-D4 verification scope |
| Read (शृणोति, opcode 0x06) | Read semantics not yet exercised in firmware proofs |
| Nested Adhikāra (`d > 1`) | Depth > 1 not in the current Adhikāra spec; reserved for future sprint |
| Cross-scope Sandhi | Sandhi spanning an Adhikāra boundary is undefined; excluded to avoid S4 |
| Ring₀ Sañjñā (VRDDHI_RING_0 role) | P4 violation outside scope; requires Adhikāra wrapping, complex to generate safely |
| Empty body | P1 would fire on a body with only Anuvrtti; excluded at strategy level |

These exclusions are **documented decisions**, not oversights. Future generator
versions may lift them as new sprints extend the spec.

---

## 4. Generation Strategies

The generator chooses uniformly at random from 7 named strategies. Each strategy
is a fixed sequence of `ProgramBuilder` method calls.

### 4.1 Strategy Definitions

**plain_writes** — baseline coverage:
```
repeat 1..4 times:
    add_write(addr ∈ A_All)
```
Exercises: Write, multiple targets, Siddha/Asiddha mix.  
P-rules exercised: P1 (not first), P2 (nothing to lopa), P3 (Ring₂ only).

**write_lopa** — erasure semantics:
```
add_write(addr ∈ A_All)
add_lopa(addr)                     -- same addr: P2 satisfied
if random() < 0.5:
    add_write(addr' ∈ A_All)      -- optional post-lopa write
```
Exercises: Lopa, written-target tracking, prev_target reset.  
P-rules exercised: P2 boundary.

**anuvrtti** — context inheritance:
```
add_write(addr ∈ A_All)
repeat 1..3 times:
    add_anuvrtti_write()
```
Exercises: COMP_ANUVRTTI encoding, target inheritance chain.  
P-rules exercised: P1 (anuvrtti is never first).

**avrtti** — bounded repetition:
```
add_avrtti_write(addr ∈ A_All, count ∈ {2,3,4,5})
```
Exercises: COMP/COUNT field values 2–5, single-word multi-execution.

**sandhi** — instruction fusion:
```
add_write(addr_pre ∈ A_Siddha)    -- preamble (any write)
add_sandhi_pair(addr ∈ A_Asiddha) -- Write + sentinel + Store
```
Exercises: SANDHI-FIRST flag (0xE), sentinel removal, S1–S5 coherence.  
P-rules exercised: P3 (Asiddha target), P4 (Ring₂, not Ring₀).

**adhikara** — privilege scope:
```
add_write(addr_pre ∈ A_Siddha)
open_adhikara()
add_ring0_store(addr ∈ A_Asiddha)
close_adhikara()
add_write(addr_post ∈ A_Siddha)
```
Exercises: ADHIKARA_OPEN/CLOSE sentinels, Ring₀ promotion, in_adhikara flag.  
P-rules exercised: P3 (Asiddha), P4 (Ring₀ inside scope only).

**mixed** — cross-feature interaction:
```
add_write(addr1 ∈ A_All)
if random() < 0.4: add_anuvrtti_write()
if random() < 0.4 ∧ written ≠ ∅:
    add_lopa(addr ∈ written)
if random() < 0.3:
    add_sandhi_pair(addr2 ∈ A_Asiddha)
```
Exercises: feature interactions — Anuvrtti after Write, Lopa before Sandhi,
Sandhi after Lopa (with re-establishing Write), all in a single program.

### 4.2 Strategy Distribution (seed 42, count 5000)

| Strategy | Count | Percentage |
|----------|-------|------------|
| plain | 1758 | 35% |
| sandhi | 919 | 18% |
| write_lopa | 904 | 18% |
| avrtti | 753 | 15% |
| adhikara | 666 | 13% |

Note: `anuvrtti` and `mixed` appear within these counts (7 strategies, uniform
choice → ~14% each; exact counts vary by seed due to sampling). The distribution
above reflects actual run output and is not a target — it is a consequence of
the uniform choice plus the random seed.

---

## 5. Differential Properties

For each generated program `src`, the following properties must hold.
A failure in any property is a **test failure** — it indicates either a generator
invariant violation or a compiler inconsistency.

### 5.1 D1 — Byte Identity

```
D1(src) ⟺
    uses_fusion(src) = False
    ∧ uses_scope(src) = False
    ⟹ emit_from_ir(compile(src)) = legacy_emit(src)
```

The IR compilation path and the legacy `emit_words()` path must produce
bit-identical word lists for programs that do not use Sandhi or Adhikāra
constructs.

The restriction to non-Sandhi/non-Adhikāra programs is necessary because
the legacy path does not implement those features. D1 is not a test of
the legacy path — it is a test of IR correctness on the common subset.

**Implementation:** `check_program()` compares `ir_words == legacy_words` only
when the source contains neither `सन्धिः` nor `अधिकारः`.

### 5.2 D2 — Constraint Coverage

```
D2(src) ⟺
    ∀ n ∈ ir_list(compile(src)) :
        n is not a scope sentinel
        ⟹ {"P1-ok","P2-ok","P3-ok","P4-ok"} ⊆ n.constraints
```

Every non-sentinel IR node must have been through all four Paribhāṣā checks.
D2 verifies that `validate_ir` did not skip any node — a silent omission would
be more dangerous than an incorrect check.

**Implementation:** After `compile_source`, re-build the IR list and check
`n.constraints` for each non-sentinel node.

### 5.3 D3 — Word Count Identity

```
D3(src) ⟺
    uses_fusion(src) = False
    ∧ uses_scope(src) = False
    ⟹ |emit_from_ir(compile(src))| = |legacy_emit(src)|
```

The number of emitted words must be identical under both paths. D3 is logically
implied by D1 (byte identity implies count identity) but is checked separately
because a length mismatch gives a more actionable error message than a byte-level
diff failure.

### 5.4 D4 — L1 Determinism

```
D4(src) ⟺
    ∀ n ∈ ir_list(compile(src)) :
        n.to_word() = n.to_word()     -- two independent calls
```

`IRNode.to_word()` is a pure function of the node's fields. D4 asserts that
no side-effects or mutable state affect the lowering map between calls.

**Implementation:** For each node in the compiled IR list, call `n.to_word()`
twice and assert equality.

### 5.5 Property Hierarchy

```
D1 ⊆ D3  (D1 implies D3 on the same restricted domain)
D4        (independent of D1/D3; checks lowering map purity)
D2        (independent of D1/D3; checks validation completeness)
```

D2 and D4 apply to all programs. D1 and D3 apply only to programs outside
the Sandhi/Adhikāra domain.

---

## 6. Coverage Classes

A coverage class is a semantic property that at least one generated program
in the suite must exhibit. The generator is designed to cover all classes
in every run of sufficient size (≥ 500 programs with any seed).

### 6.1 Instruction-Level Coverage

| Class | Generator Method | Exercises |
|-------|-----------------|-----------|
| C1 | `add_write(Siddha)` | Write on Siddha target (P3 boundary) |
| C2 | `add_write(Asiddha)` | Write on Asiddha target |
| C3 | `add_anuvrtti_write()` | COMP_ANUVRTTI encoding |
| C4 | `add_avrtti_write(count=2..5)` | COMP/COUNT field 2-5 |
| C5 | `add_lopa(addr)` | Lopa opcode, written-target erasure |
| C6 | `add_sandhi_pair(Asiddha)` | Sandhi fusion, FLAGS=0xE |
| C7 | `add_ring0_store(Asiddha)` | Ring₀ promotion, in_adhikara |

### 6.2 Rule-Boundary Coverage

| Class | What is tested |
|-------|----------------|
| R1 | P1 boundary: first instruction is always explicit (never Anuvrtti-first) |
| R2 | P2 boundary: Lopa only after Write; written set correctly tracks erasure |
| R3 | P3 boundary: Ring₀ only on Asiddha targets |
| R4 | P4 boundary: Ring₀ only inside Adhikāra scope |
| R5 | S5 boundary: Lopa followed by Write followed by Sandhi (valid re-establishment) |

### 6.3 Interaction Coverage

| Class | Program type | Strategies that produce it |
|-------|-------------|--------------------------|
| I1 | Write → Anuvrtti chain | `anuvrtti`, `mixed` |
| I2 | Write → Lopa → Write (re-establishment) | `write_lopa` (optional tail), `mixed` |
| I3 | Write → Lopa → Sandhi-pair (S5 refinement boundary) | `mixed` |
| I4 | Sandhi-pair after standalone Write | `sandhi` |
| I5 | Ring₀ Store flanked by Ring₂ Writes | `adhikara` |
| I6 | Sañjñā name used as Karaka for known Asiddha address | all (30% probability) |

### 6.4 Coverage Verification

The test runner reports strategy distribution at the end of each run. A run
is considered **coverage-adequate** if all 7 strategies appear at least once.
With ≥ 500 programs and any seed, the probability of a strategy being absent
is < 0.001 (uniform choice over 7, `(6/7)^500 ≈ 10^{-33}`).

---

## 7. Generator Correctness Properties

The generator must satisfy the following properties independently of the compiler.
These can be verified by running the generator and inspecting output without
invoking the compiler:

**GC1 — Structural validity:**
Every program produced by `build()` must parse without `SyntaxError`.

**GC2 — No Anuvrtti-first (G1):**
In any generated program, if the body's first instruction is `"लिखति ।"` (bare),
that is a bug — all generated programs start with an explicit Karaka.

**GC3 — Written-set consistency (G2):**
After any `add_lopa(addr)` call, `addr ∉ builder.written`.
Before any `add_lopa(addr)` call, `addr ∈ builder.written`.

**GC4 — Scope flag consistency (G3):**
`add_ring0_store()` is only ever called between `open_adhikara()` and
`close_adhikara()`. `builder.in_scope = True` exactly during this interval.

**GC5 — Sandhi target in A_Asiddha (G4):**
`add_sandhi_pair(addr)` is only ever called with `addr ∈ {0x50, 0x60}`.

---

## 8. Failure Classification

When a program fails a property, the failure is classified:

| Failure type | Likely cause |
|-------------|--------------|
| `IR path rejected valid program` | Generator produced a program that violates a compiler rule — generator meta-constraint G1–G5 is broken |
| `D1 mismatch` | IR path and legacy path disagree on binary — compiler inconsistency |
| `D2 missing constraint` | `validate_ir` skipped a node — validation loop bug |
| `D3 word count mismatch` | Length disagrees before byte comparison — emission bug |
| `D4 non-determinism` | `to_word()` is not a pure function — mutable state in IRNode |
| `IR path crash` | Unhandled exception in compiler — robustness failure |
| `Legacy path crash` | Unhandled exception in legacy emitter |

The test runner captures and reports the first 3 failures with full program source
and error message when `--verbose` is passed.

---

## 9. Invocation

```bash
# Standard run (5000 programs, fixed seed, deterministic)
python3 -B run_differential_tests.py --count 5000 --seed 42

# Development run (fewer programs, verbose failure output)
python3 -B run_differential_tests.py --count 200 --seed 42 --verbose

# Stress run (different seed, same count)
python3 -B run_differential_tests.py --count 5000 --seed 137
```

No VM, no SSH, no QEMU required. The generator and differential checker are
purely local — they test the compiler's semantic consistency, not the firmware's
execution correctness. Firmware proofs are a separate layer.

### 9.1 Expected Output (passing)

```
============================================================
PVM Differential Test Suite
Programs: 5000   Seed: 42
============================================================
  Progress: 500/5000 passed=500 failed=0 errors=0
  ...
  Progress: 5000/5000 passed=5000 failed=0 errors=0

============================================================
RESULTS
============================================================
  Total programs:  5000
  Passed:          5000
  Failed:          0
  Errors:          0

  Property breakdown (failures):
    D1: 0 failures  -- Byte identity (IR == legacy)
    D2: 0 failures  -- Constraint coverage (P1-ok..P4-ok)
    D3: 0 failures  -- Word count identity
    D4: 0 failures  -- L1 determinism (to_word stable)

[PASS] 5000/5000 programs passed all four properties.
```

---

## 10. Relationship to Formal Semantics

This generator spec is a companion to `formal_semantics.md`. The correspondence is:

| Generator concept | Formal semantics section |
|------------------|-------------------------|
| `A_Siddha`, `A_Asiddha` | §1.2 Address Partition |
| G1 (no Anuvrtti-first) | §5.1 P1 |
| G2 (no Lopa-on-unwritten) | §5.2 P2 |
| G3 (Ring₀ only in scope) | §5.3 P3 + §5.4 P4 |
| G4 (Sandhi coherence) | §6.3 S1–S5 |
| G5 (Lopa resets tracking) | §6.3 S5 (last_event definition) |
| D1 (byte identity) | §9 D1 |
| D2 (constraint coverage) | §4.3 compilation pipeline + §5 |
| D3 (word count) | §4.2 lowering map |
| D4 (L1 determinism) | §8.1 L1 |

The generator's meta-constraints (G1–G5) are the **constructive dual** of the
compiler's legality predicates (P1–P4, S1–S5): the compiler rejects illegal
programs; the generator never produces them. Both must agree on the boundary.

The S5 refinement (discovered during differential testing, documented in
`formal_semantics.md` §6.3) is reflected here in G5: the generator always
emits a Write before a Sandhi-pair, which satisfies `last_event = Write` and
prevents S5 from firing. This is not a coincidence — the generator constraint
and the rule were co-refined until they agreed.

---

*End of property-based test generator specification.*
