# Paninian System Language — Formal Semantics

**Version:** Post-Sprint-10 / Post-Differential-Testing
**Date:** 2026-05-23
**Status:** Stable — ABI, IRNode structure, Paribhāṣā rules, and Sandhi/Adhikāra semantics frozen.

---

## 0. Preamble

This document gives a mathematical specification of the Paninian System Language (PSL)
compiler semantics. It covers:

1. The **abstract machine** over which PSL programs execute.
2. The **type system** of PSL instruction words.
3. The **legality predicates** (Paribhāṣā, P1–P4).
4. The **Prakriya IR** — the explicit intermediate derivation record.
5. The **Sandhi transform** — IR-level instruction fusion (S1–S5).
6. The **Adhikāra scope** — block-level privilege domains.
7. The **lowering invariants** — correctness conditions on the IR→binary map.

The RV32 firmware proofs (Sprints 1–10) are evidence that the semantics below
are faithfully implemented. They are not the semantics themselves.

---

## 1. Abstract Machine

### 1.1 State Space

The PSL abstract machine state is a 4-tuple:

```
Σ = ⟨B, S, R, PC⟩
```

where:

| Component | Type | Description |
|-----------|------|-------------|
| `B` | `Addr → Byte ∪ {⊥}` | Bus map — globally visible device registers |
| `S` | `Addr → Byte ∪ {⊥}` | Shadow map — isolated (Asiddha) device registers |
| `R` | `{0, 2}` | Current ring level (0 = kernel, 2 = user) |
| `PC` | `ℕ` | Program counter (instruction index) |

Initial state: `Σ₀ = ⟨λa.⊥, λa.⊥, 2, 0⟩`

The symbol `⊥` denotes "not written" — distinct from a written zero byte.

### 1.2 Address Partition

All device addresses are 8-bit values in `[0x00, 0xFF]`. They are partitioned by a single threshold:

```
ASIDDHA_BASE = 0x50

Siddha(a)  ⟺  a < 0x50    -- globally visible bus
Asiddha(a) ⟺  a ≥ 0x50    -- isolated shadow register
```

Siddha addresses map to `B`; Asiddha addresses map to `S`. This partition is
static — it is a property of the address, not of the instruction. A program
cannot move an address between regions.

### 1.3 Ring Levels

```
Ring₀ ≡ 0x0   (kernel / Vrddhi)   -- privileged; Asiddha targets only
Ring₂ ≡ 0x2   (user)              -- default; Siddha targets; Asiddha with restriction
```

Ring level is an instruction-level attribute. It is not a runtime register in the
firmware sense — it is embedded in the ABI word and decoded per instruction.

---

## 2. ABI Word Layout

Every PSL instruction lowers to exactly one 32-bit big-endian word:

```
 31      28 27    24 23      16 15       8 7    4 3    0
 ┌────────┬─────────┬─────────┬─────────┬──────┬──────┐
 │ RING   │  COMP/  │  OPCODE │  TARGET │FLAGS │ COND │
 │  ID    │  COUNT  │ (Kriya) │  (addr) │      │      │
 └────────┴─────────┴─────────┴─────────┴──────┴──────┘
   4 bits   4 bits    8 bits    8 bits   4 bits 4 bits
```

### 2.1 Field Encodings

**RING_ID** (`w[31:28]`):

| Value | Meaning |
|-------|---------|
| `0x0` | Ring₀ — Vrddhi (kernel) |
| `0x2` | Ring₂ — User (default) |

**COMP/COUNT** (`w[27:24]`):

| Value | Meaning |
|-------|---------|
| `0x0` | Explicit — TARGET field carries a literal address |
| `0x1` | Anuvrtti — TARGET field is inherited from previous instruction |
| `n > 1` | Avrtti count — instruction repeats `n` times |

**OPCODE** (`w[23:16]`):

| Value | Sanskrit | Operation |
|-------|----------|-----------|
| `0x00` | लोपः | Lopa — structured erasure |
| `0x05` | लिखति | Write — Ring₂ bus write |
| `0x06` | शृणोति | Read |
| `0xCC` | स्थापयति | Store — Ring₀ shadow write |
| `0xAA` | अधिकारः (open) | Adhikāra scope open sentinel |
| `0xBB` | (close) | Adhikāra scope close sentinel |
| `0xFF` | सन्धिः | Sandhi sentinel (compile-time only; never in binary) |

**TARGET** (`w[15:8]`): 8-bit device address. `0x00` for scope sentinels and Anuvrtti slots.

**FLAGS** (`w[7:4]`):

| Value | Meaning |
|-------|---------|
| `0xF` | Standard (Lopa boundary marker) |
| `0xE` | SANDHI-FIRST — this word is the first of a fused pair |

**COND** (`w[3:0]`):

| Value | Sanskrit | Condition |
|-------|----------|-----------|
| `0x0` | — | Unconditional |
| `0x1` | उत्सर्गः | Utsarga — general rule, lower precedence |
| `0x2` | अपवादः | Apavāda — exception, higher precedence |

### 2.2 Word Construction Function

Given field values, the 32-bit word is:

```
word(ring, comp, op, tgt, flags, cond) =
    (ring  << 28)
  | (comp  << 24)
  | (op    << 16)
  | (tgt   <<  8)
  | ((flags & 0xF) << 4)
  | (cond  & 0xF)
```

This function is total and deterministic. It is the **only** path from IR to binary.

---

## 3. Type System

### 3.1 Karaka (Nominal Argument)

A Karaka is a compile-time binding of a Sanskrit nominal to a device address and a role:

```
Karaka ::= ⟨addr : Addr, role : Role⟩

Role ::= KARMAN          -- standard object; Ring₂
       | APADANA          -- ablative source; Ring₂
       | VRDDHI_RING_0    -- promoted object; Ring₀ forced
```

The `VRDDHI_RING_0` role is the only mechanism by which Ring₀ can appear in a PSL program outside an Adhikāra block via the karaka lexicon (and doing so outside a scope will trigger P4 — see §5.4).

### 3.2 Kriya (Verbal Operation)

```
Kriya ::= Write  (0x05)   -- Ring₂ bus write
        | Read   (0x06)   -- Ring₂ bus read
        | Store  (0xCC)   -- Ring₀ shadow write (requires Adhikāra scope)
        | Lopa   (0x00)   -- structured erasure (requires prior write on same addr)
```

Write-class instructions: `{Write, Store}`. Lopa is not write-class.

### 3.3 Statement Type

A PSL statement is a triple:

```
Stmt ::= ⟨karaka : Karaka ∪ {inherited}, kriya : Kriya, cond : Cond⟩
```

When `karaka = inherited` (Anuvrtti), the target address is resolved from the
most recent preceding statement with an explicit Karaka.

### 3.4 Scope Sentinels

Scope sentinels are not executable instructions. They are compiler-inserted IR nodes
that bracket Adhikāra domains:

```
Sentinel ::= ADHIKARA_OPEN   (opcode 0xAA, target 0x00)
           | ADHIKARA_CLOSE  (opcode 0xBB, target 0x00)
```

Sentinels lower to ABI words but carry no operational semantics in the abstract machine —
they exist solely to inform firmware privilege mode switches.

---

## 4. Prakriya IR

### 4.1 IRNode

The Prakriya intermediate record is a labelled 9-tuple:

```
IRNode ::= ⟨
    ring        : {0, 2},
    comp        : {0x0, 0x1} ∪ [2..15],
    opcode      : Byte,
    target      : Addr ∪ {⊥},
    cond        : {0, 1, 2},
    flags       : {0xF, 0xE},
    source_line : ℕ,
    constraints : List⟨String⟩,
    sandhi_fused : Bool,
    in_adhikara  : Bool
⟩
```

`target = ⊥` is used for Anuvrtti nodes and scope sentinels.

### 4.2 Lowering Map

The lowering map `⟦·⟧ : IRNode → Word₃₂` is:

```
⟦n⟧ = word(
    n.ring,
    n.comp,
    n.opcode,
    n.target ?: 0x00,
    if n.sandhi_fused then 0xE else n.flags,
    n.cond
)
```

where `a ?: b` means "a if defined, else b."

### 4.3 Compilation Pipeline

```
source : String
    │
    ▼  _parse_sanjnaa(source)
sanjnaa_table : Map⟨Name, Karaka⟩
    │
    ▼  per line: _build_ir_node(stmt_ast, adhikara_depth)
ir_list : List⟨IRNode⟩          (raw, unvalidated)
    │
    ▼  sandhi_pass(ir_list)      (§6)
ir_list : List⟨IRNode⟩          (sentinels removed, fused pairs marked)
    │
    ▼  validate_ir(ir_list)      (§5)
ir_list : List⟨IRNode⟩          (constraints populated, or ParibhashaError raised)
    │
    ▼  check_lowering_invariants(ir_list)   (§7)
ir_list : List⟨IRNode⟩          (L1/L2 asserted)
    │
    ▼  emit_from_ir(ir_list)
words : List⟨Word₃₂⟩
```

Each stage is a pure function over the IR list. No stage may produce binary directly
from the AST; the IR is the only intermediate form.

### 4.4 Written-Target Tracking

The IR pipeline maintains a set `W ⊆ Addr` of written targets, updated during
`validate_ir`. The invariant is:

```
After processing node n:
    if n.opcode ∈ {0x05, 0xCC}
       ∧ n.comp ≠ COMP_ANUVRTTI
       ∧ n.target ≠ ⊥
    then W := W ∪ {n.target}

    if n.opcode = 0x00
       ∧ n.comp ≠ COMP_ANUVRTTI
       ∧ n.target ≠ ⊥
    then W := W \ {n.target}
```

Explicit Lopa therefore **consumes** the live-written state for its target.
A second explicit Lopa requires an intervening Write/Store. Anuvrtti Lopa is
treated as a chained operation whose effective target is resolved from runtime
context; its precise source/runtime refinement remains an open formal obligation.

---

## 5. Paribhāṣā — Legality Predicates (P1–P4)

Paribhāṣā rules are checked during `validate_ir`. A violation raises
`ParibhashaError(rule_id, rule_name, line, text, detail)` and terminates
compilation. No binary is emitted on violation.

### 5.1 P1 — Anuvrtti-at-start

```
P1(ir_list) ⟺
    ∀ n ∈ ir_list :
        (n is the first non-sentinel node) ⟹ n.comp ≠ COMP_ANUVRTTI
```

**Rationale:** Anuvrtti resolves target from context. There is no prior context
at the start of the instruction stream. An Anuvrtti-first program is structurally
ill-formed — the target is undefined.

**Effect:** `ParibhashaError("P1", "Anuvrtti-at-start", ...)`

### 5.2 P2 — Lopa-on-unwritten

```
P2(ir_list) ⟺
    ∀ n ∈ ir_list :
        (n.opcode = 0x00 ∧ n.target ≠ ⊥)
        ⟹ n.target ∈ W_{before n}
```

where `W_{before n}` is the written-target set immediately before processing `n`.

**Rationale:** Lopa is structured erasure — it nullifies a prior write. Erasing
something that was never written has no semantic content and is structurally
incoherent.

**Effect:** `ParibhashaError("P2", "Lopa-on-unwritten", ...)`

### 5.3 P3 — Vrddhi-on-Siddha

```
P3(ir_list) ⟺
    ∀ n ∈ ir_list :
        (n.ring = 0 ∧ n.target ≠ ⊥)
        ⟹ Asiddha(n.target)
```

**Rationale:** Ring₀ (Vrddhi) authority is meaningful only for Asiddha (isolated)
targets. Ring₀ on a Siddha (globally visible) bus target conflates kernel authority
with user-visible state — a semantic category error.

**Effect:** `ParibhashaError("P3", "Vrddhi-on-Siddha", ...)`

### 5.4 P4 — Ring0-outside-scope

```
P4(ir_list) ⟺
    ∀ n ∈ ir_list :
        n.ring = 0
        ⟹ adhikara_depth_{before n} > 0
```

where `adhikara_depth` is incremented by `ADHIKARA_OPEN` sentinels and decremented
by `ADHIKARA_CLOSE` sentinels as they are encountered during `validate_ir`.

**Rationale:** Privileged operations must be explicitly scoped. Unscoped Ring₀
instructions cannot be audited or bounded — they are structurally invisible to
any scope-aware analysis.

**Effect:** `ParibhashaError("P4", "Ring0-outside-scope", ...)`

### 5.5 Paribhāṣā Interaction Order

Rules are checked in the order P1 → P2 → P3 → P4 per node. The first violation
terminates. This ordering is not arbitrary: P1 must precede P2 because an
Anuvrtti-first node may have `target = ⊥`, making P2's target check undefined.

---

## 6. Sandhi — IR-Level Instruction Fusion

### 6.1 Operational Semantics

Sandhi (fusion) is a compile-time IR transform, not a runtime optimization.
It produces a pair of instructions that the abstract machine treats atomically:
the first word's FLAGS field is set to `0xE` (SANDHI-FIRST), signalling to
the firmware that the next instruction must execute in the same atomic step.

The **Sandhi sentinel** (opcode `0xFF`) is a compiler directive inserted by
the parser when `सन्धिः` appears in source. It is never emitted to binary.

### 6.2 Sandhi Pass Algorithm

```
sandhi_pass(ir_list):
    sentinels ← [i | ir_list[i].opcode = 0xFF]
    for i in reversed(sentinels):
        assert i > 0 ∧ i < |ir_list| - 1  else raise S0
        node_a ← ir_list[i - 1]
        node_b ← ir_list[i + 1]
        check S1(node_a, node_b)
        check S2(node_a, node_b)
        check S3(node_a, node_b)
        check S4(node_a, node_b)
        check S5(node_a, i, ir_list)
        node_a.sandhi_fused ← True
        remove ir_list[i]   -- sentinel consumed
    return ir_list
```

Sentinels are processed in reverse index order so that index stability is
maintained (removing a sentinel does not shift earlier sentinels).

### 6.3 Sandhi Legality Rules (S0–S5)

**S0 — Boundary:**
```
S0: i = 0 ∨ i ≥ |ir_list| - 1
```
The sentinel has no valid instruction pair. A Sandhi directive must be flanked
by exactly one instruction on each side within the current block.

**S1 — Write-class requirement:**
```
S1: node_a.opcode ∉ {0x05, 0xCC} ∨ node_b.opcode ∉ {0x05, 0xCC}
```
Sandhi fuses only write-class instructions. Lopa (opcode 0x00) cannot be fused —
erasure is not a write and has no meaningful atomic pairing with a store.

**S2 — Target identity:**
```
S2: node_a.target ≠ node_b.target ∨ node_a.target = ⊥
```
Both instructions must target the same device address. Fusing cross-target
instructions would conflate two independent operations — they have no common
semantic object to fuse on.

**S3 — Explicit first:**
```
S3: node_a.comp = COMP_ANUVRTTI
```
The first instruction of a fused pair must carry an explicit Karaka. Anuvrtti
inherits from context; within a fused pair the context is the pair itself,
creating a self-referential target resolution.

**S4 — Ring identity:**
```
S4: node_a.ring ≠ node_b.ring
```
Both instructions must execute at the same privilege level. A cross-ring fusion
would require the abstract machine to switch privilege mid-atomic-step, which
is undefined in the abstract machine model.

**S5 — Coherence after erasure (refined):**

Let `prior(i) = ir_list[0 .. i]` (the prefix up to and including `node_a`).
Define:

```
last_event(addr, prefix) =
    the opcode of the rightmost node n in prefix
    such that n.target = addr ∧ n.opcode ∈ {0x00, 0x05, 0xCC}
    or ⊥ if no such node exists
```

Then:

```
S5: last_event(node_a.target, prior(i)) = 0x00
    -- i.e., the most recent event on the target is a Lopa,
    -- with no Write or Store occurring after it (in prior(i))
```

**Rationale (S5 refinement):** The original formulation ("any prior Lopa on
the same target") was overly conservative. A Write after a Lopa re-establishes
the target as a valid write recipient — the Lopa's erasure is superseded. Sandhi
on a re-established target is coherent. S5 fires only when the Lopa is the
*most recent* event on the target — meaning the target is currently in the
erased state at the point of fusion.

Note: `node_a` itself is included in `prior(i)` because `node_a` is always a
write-class instruction (guaranteed by S1) and may itself be the re-establishing
write. This is the corrected semantics discovered through differential testing.

**S5 Effect:** `SandhiError("S5", "Sandhi-after-lopa", ...)`

---

## 7. Adhikāra — Privilege Scope Semantics

### 7.1 Scope Structure

Adhikāra is a lexically scoped privilege domain. In source:

```
अधिकारः {
    <Ring₀-capable instructions>
}
```

The compiler tracks nesting depth `d : ℕ` (initially 0). On encountering
`अधिकारः {`, `d` is incremented and an `ADHIKARA_OPEN` sentinel is emitted.
On encountering `}` when `d > 0`, `d` is decremented and an `ADHIKARA_CLOSE`
sentinel is emitted. The outer tantra block's closing `}` is not an Adhikāra close.

### 7.2 Ring Promotion

Inside an Adhikāra block, a Store instruction (`स्थापयति`, opcode 0xCC) emitted
at default Ring₂ is automatically promoted to Ring₀:

```
if d > 0 ∧ n.opcode = 0xCC ∧ n.ring = Ring₂ then n.ring := Ring₀
```

This promotion happens during `_build_ir_node`, before `validate_ir`. The
`in_adhikara` field of the IRNode is set to `True` for all nodes built with `d > 0`.

### 7.3 Scope Sentinel ABI Encoding

```
ADHIKARA_OPEN  → word(ring=0, comp=0, op=0xAA, tgt=0x00, flags=0xF, cond=0)
               = 0x00AA00F0

ADHIKARA_CLOSE → word(ring=0, comp=0, op=0xBB, tgt=0x00, flags=0xF, cond=0)
               = 0x00BB00F0
```

These words are emitted to the binary image. The firmware decodes them and adjusts
its `scope_ring` register accordingly — they are not no-ops.

### 7.4 Scope × Paribhāṣā Interaction

P4 consults `adhikara_depth` as maintained by `validate_ir` (which re-derives
depth by scanning sentinels). This is independent of the `in_adhikara` field
set during IR construction. The two must agree — a disagreement is an L2 violation.

---

## 8. Lowering Invariants

### 8.1 L1 — Deterministic Lowering

```
L1: ∀ n ∈ ir_list : ⟦n⟧₁ = ⟦n⟧₂
```

where `⟦n⟧₁` and `⟦n⟧₂` are two independent evaluations of the lowering map.

L1 asserts that `IRNode.to_word()` is a pure function — it depends only on the
node's fields, none of which are mutable after `sandhi_pass` sets `sandhi_fused`.
Differential property D4 verifies L1 across 5000 generated programs.

### 8.2 L2 — No Post-Transform Violations

```
L2(P1): ∀ n ∈ ir_list :
    (n is the first non-sentinel node) ⟹ n.comp ≠ COMP_ANUVRTTI

L2(P3): ∀ n ∈ ir_list :
    n.ring = 0 ∧ n.target ≠ ⊥ ⟹ Asiddha(n.target)
```

L2 checks that `sandhi_pass` did not introduce violations. Since `sandhi_pass`
only sets `sandhi_fused = True` and removes sentinel nodes — it does not change
`ring`, `comp`, or `target` fields — L2 is vacuously satisfied post-`validate_ir`.
The assertion is retained as a defence against future transform passes.

### 8.3 Word Range

```
∀ n ∈ ir_list : 0 ≤ ⟦n⟧ ≤ 0xFFFFFFFF
```

This is guaranteed by construction: all fields are bounded before packing.

---

## 9. Differential Validation Properties

The following four properties were verified across 5000 randomly-generated valid
PSL programs (seed 42, `run_differential_tests.py`):

| ID | Property | Formal Statement |
|----|----------|-----------------|
| D1 | Byte identity | `emit_from_ir(compile(src)) = legacy_emit(src)` for all non-Sandhi/non-Adhikāra programs |
| D2 | Constraint coverage | `∀ n ∈ ir_list : {"P1-ok","P2-ok","P3-ok","P4-ok"} ⊆ n.constraints` for all non-sentinel nodes |
| D3 | Word count identity | `|emit_from_ir(compile(src))| = |legacy_emit(src)|` |
| D4 | L1 determinism | `n.to_word() = n.to_word()` (two independent calls) |

**Result (2026-05-23):** D1=0, D2=0, D3=0, D4=0 failures. 5000/5000 PASS.

D1 and D3 apply only to programs that do not use Sandhi or Adhikāra constructs,
since the legacy `emit_words()` path does not handle those. The IR path is the
canonical path for all programs; legacy is retained only for differential comparison.

---

## 10. Exception Hierarchy

### 10.1 ParibhashaError

```
ParibhashaError(
    rule_id   : {"P1", "P2", "P3", "P4"},
    rule_name : String,
    line_number : ℕ,
    line_text   : String,
    detail      : String
)
```

Raised by `validate_ir`. Terminates compilation. No binary is produced.

### 10.2 SandhiError

```
SandhiError(
    rule_id  : {"S0", "S1", "S2", "S3", "S4", "S5"},
    rule_name : String,
    line_a   : ℕ,
    line_b   : ℕ,
    detail   : String
)
```

Raised by `sandhi_pass`. Terminates compilation. No binary is produced.

---

## 11. Stability Declarations

The following are **frozen** as of this document. Changes require a versioned
amendment with rationale:

- **ABI word layout** (§2) — field positions and widths.
- **IRNode field set** (§4.1) — no new fields without a sprint justification.
- **Paribhāṣā rules P1–P4** (§5) — rule semantics and ordering.
- **Sandhi rules S0–S5** (§6.3) — including the S5 refinement.
- **Adhikāra promotion rule** (§7.2) — Store-at-Ring₂ inside scope → Ring₀.
- **Lowering map** (§4.2) — `word()` construction function.
- **Compilation pipeline order** (§4.3) — parse → IR → sandhi → validate → lower.

The following are **open** for future sprints:

- New Karaka roles (§3.1) — provided P3 is not violated.
- New Kriya opcodes (§3.2) — provided the opcode space is not exhausted.
- New Paribhāṣā rules P5+ — must not contradict P1–P4.
- New Sandhi rules S6+ — must not contradict S1–S5.
- New scope types beyond Adhikāra — must respect the scope depth model (§7.1).
- Property-based test generator extensions — must not generate P1–P4 violations.

---

## Appendix A — Known PSL Program Instances

### A.1 sandhi_core.pvm (Sprint 9 proof)

```
सञ्ज्ञा यन्त्र = 0x60 ।
तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    यन्त्र लिखति ।
    सन्धिः ।
    यन्त्र स्थापयति ।
}
```

IR: `[Write(0x30), Write(0x60), Sandhi-sentinel, Store(0x60)]`
After sandhi_pass: `[Write(0x30), Write*(0x60)[SANDHI-FIRST], Store(0x60)]`
Binary: `[0x200530F0, 0x200560E0, 0x20CC60F0]`

### A.2 adhikara_core.pvm (Sprint 10 proof)

```
सञ्ज्ञा यन्त्र = 0x60 ।
तन्त्रशास्त्रम् {
    वाचम् लिखति ।
    अधिकारः {
        यन्त्र स्थापयति ।
    }
    वाचम् लिखति ।
}
```

IR: `[Write(0x30), OPEN, Store(0x60)@Ring₀, CLOSE, Write(0x30)]`
Binary: `[0x200530F0, 0x00AA00F0, 0x00CC60F0, 0x00BB00F0, 0x200530F0]`

### A.3 S5 boundary case (discovered via differential testing)

Valid (lopa then write then sandhi):
```
तन्त्रशास्त्रम् {
    यन्त्र लिखति ।     # write 0x60 → W = {0x60}
    यन्त्र लोपः ।      # lopa 0x60  → last_event(0x60) = Lopa
    यन्त्र लिखति ।     # write 0x60 → last_event(0x60) = Write (re-established)
    सन्धिः ।           # sentinel
    यन्त्र स्थापयति ।  # store 0x60
}
```
S5 does not fire: `last_event(0x60, prior) = Write` (node_a itself).

Invalid (lopa then sandhi, no re-write):
```
तन्त्रशास्त्रम् {
    यन्त्र लिखति ।     # write 0x60
    यन्त्र लोपः ।      # lopa 0x60
    सन्धिः ।           # sentinel
    यन्त्र स्थापयति ।  # store 0x60
}
```
S1 fires first (node_a is Lopa, not write-class). S5 would also fire, but S1 takes precedence.

---

*End of formal semantics document.*
