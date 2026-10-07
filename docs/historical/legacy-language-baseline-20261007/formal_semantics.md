# Paninian Systems Language — Canonical Formal Semantics

**Verification-repair revision:** 2026-10-07
**Authority:** `lean/PSL/Semantics.lean` is the machine-checked authority for the model described here.
**Scope:** canonical control semantics and abstract execution. This document does **not** claim source-to-RV32 compiler correctness.

The pre-repair document is preserved at
`docs/historical/formal_semantics-pre-verification-repair.md`.

---

## 1. Layers and proof boundary

PSL currently distinguishes these layers:

```text
PSL source
   ↓ Python compiler                     [correspondence still open]
Prakriya IR / 32-bit ABI words
   ↓ canonical control validation        [executable definition]
Lean abstract execution                  [forward simulation proved]
   ↓ canonical RV32 runtime              [refinement still open]
QEMU virt                                [historical execution evidence]
   ↓ physical RISC-V                     [not established]
```

The central repaired Lean result is deliberately narrower than the historical
`compile_sound` claim:

> If the canonical word validator accepts a word stream from a given control
> state, abstract execution of that same word stream from a machine with the
> same control state succeeds and ends with the same final control state.

This is proved by `validateWords_execution`, with corollaries
`validated_ir_executes` and `valid_program_executes`.

---

## 2. ABI word

Each lowered instruction is one 32-bit big-endian word:

```text
31..28   27..24   23..16   15..08   07..04   03..00
RING     COMP      OPCODE    TARGET    FLAGS     COND
```

Current named opcodes:

| Opcode | Operation |
|---:|---|
| `0x00` | Lopa |
| `0x05` | Write |
| `0x06` | Read |
| `0xCC` | Store |
| `0xAA` | Adhikāra OPEN |
| `0xBB` | Adhikāra CLOSE |

`COMP=1` denotes Anuvṛtti. Values greater than 1 are historically used for
Āvṛtti counts, but repetition semantics are not yet part of the repaired formal
execution theorem.

Ring is an **instruction attribute**. It is not a mutable global field of the
canonical machine state.

---

## 3. Address partition

```text
ASIDDHA_BASE = 0x50

Siddha(a)  iff a < 0x50
Asiddha(a) iff a >= 0x50
```

The partition is static.

The repaired control semantics intentionally permits a Ring-2 WRITE whose
resolved target is Asiddha. The visibility/storage consequences of that write
belong to the memory/refinement model and must be specified by the eventual
canonical RV32 runtime.

Ring 0 resolving to a Siddha target is invalid.

---

## 4. Canonical control state

The control state is:

```text
C = <W, K, D>
```

where:

- `W : Addr -> Bool` — whether an address currently has live written state;
- `K : Option Addr` — the current Anuvṛtti target context;
- `D : Nat` — active Adhikāra scope depth.

Initial state:

```text
W(a) = false for every a
K = none
D = 0
```

This replaces the pre-repair model that also stored a mutable global ring.

---

## 5. Target resolution

For word `w` in control state `C`:

```text
resolve(C, w) =
    C.K                 if w.COMP = 1
    some(w.TARGET)      otherwise
```

Therefore an Anuvṛtti instruction is invalid when `K = none`.

An explicit executable instruction establishes new target context unless it is
Lopa.

---

## 6. Adhikāra

OPEN and CLOSE operate on scope depth:

```text
OPEN:  D := D + 1
CLOSE: require D > 0; D := D - 1
```

A CLOSE at depth zero is invalid.

A canonical valid program must finish with `D = 0`.

Adhikāra does not mutate a global ring. Instead, privilege legality requires the
ring attribute carried by each instruction to agree with scope.

---

## 7. Privilege rules

For an executable word whose effective target is `t`:

### P3 — Ring-0 target partition

```text
w.RING = 0  =>  t >= ASIDDHA_BASE
```

### P4 — Ring-0 scope

```text
w.RING = 0  =>  D > 0
```

### Store

Store is always privileged:

```text
w.OPCODE = STORE  =>  D > 0 and w.RING = 0
```

### Asiddha Lopa

```text
w.OPCODE = LOPA and t >= ASIDDHA_BASE
    => D > 0 and w.RING = 0
```

A Ring-2 Lopa of a Siddha address may be legal if P2 is satisfied.

---

## 8. P2 live-written semantics

WRITE and STORE establish live-written state:

```text
WRITE(t) or STORE(t): W[t] := true
```

Lopa requires live-written state:

```text
LOPA(t): require W[t] = true
```

and consumes it:

```text
W[t] := false
```

Thus:

```text
WRITE(t); LOPA(t); LOPA(t)
```

is invalid, while:

```text
WRITE(t); LOPA(t); WRITE(t); LOPA(t)
```

may be valid subject to privilege rules.

This replaces the historical “written at least once earlier” interpretation.

---

## 9. Lopa and Anuvṛtti boundary

Lopa is a hard context boundary:

```text
LOPA(t): K := none
```

Therefore:

```text
explicit operation on t
LOPA(t)
Anuvrtti operation
```

is invalid unless a new explicit instruction appears between the Lopa and the
Anuvṛtti.

This is the canonical resolution of the historical conflict between Sprint 5
and Sprint 13.

---

## 10. Control transition

Ignoring OPEN/CLOSE, a canonical executable transition proceeds conceptually as:

```text
1. reject unknown executable opcode
2. resolve effective target
3. reject Anuvrtti if no context exists
4. enforce P3/P4 and operation-specific privilege rules
5. for Lopa, require W[target] = true
6. update W
7. update K:
      Lopa        -> none
      Anuvrtti    -> preserve current K
      explicit op -> target
8. preserve D
```

The exact executable definition is `controlStep` in
`lean/PSL/Semantics.lean`.

---

## 11. Abstract machine

The repaired abstract machine state is:

```text
MachineState = <control : ControlState, mem : Nat -> Nat>
```

The memory component is intentionally simple:

- WRITE/STORE set the resolved target to `1`;
- Lopa sets the resolved target to `0`;
- other supported control operations leave memory unchanged.

This memory model is sufficient for the present validator-to-execution theorem.
It is **not** yet a faithful Siddha/Asiddha hardware memory model.

`step` first runs `controlStep`. If the control transition fails, execution
fails. If it succeeds, `applyMem` produces the abstract memory update.

---

## 12. Validation and execution

`validateWords` folds `controlStep` over an ABI word stream.

`execute` folds `step` over the same word stream.

`validateIR` lowers an IR list and validates the resulting words from the
initial control state.

`ValidProgram(ir)` means:

```text
there exists cFinal such that
    validateIR(ir) = some cFinal
and cFinal.scopeDepth = 0
```

---

## 13. Machine-checked results

The current Lean module proves:

### Lowering facts

- `lower_preserves_core_fields`
- `lowerAll_length_preserving`

### Control facts

- `open_increments_scope`
- `close_at_zero_fails`
- `step_of_controlStep`

### Forward simulation

- `validateWords_execution`
- `validated_ir_executes`
- `valid_program_executes`

The principal theorem dependencies are checked by `lean/Audit.lean`. CI fails
if they acquire `sorryAx` or the retired PSL project axiom
`p2_runtime_correctness`.

---

## 14. What is not yet formalized

The repaired theorem does not yet model or prove:

1. Python parser/source semantics;
2. Python compiler -> Lean `ValidProgram` correspondence;
3. Āvṛtti repetition behavior;
4. Utsarga/Apavāda conditions;
5. Sandhi atomicity;
6. a complete Siddha/Asiddha visibility model;
7. canonical RV32 firmware refinement;
8. QEMU-to-physical-silicon correspondence.

These are separate proof obligations. They must not be inferred from
`valid_program_executes`.

---

## 15. Sañjñā note

The current Lean definition:

```text
sanjnaaEquiv(ir1, ir2) := lowerAll(ir1) = lowerAll(ir2)
```

makes the present Sañjñā binary-identity theorem definitional. It does not yet
prove that the Python symbol-resolution phase preserves source meaning.

A future source-semantics model must prove symbol resolution independently.

---

## 16. Sandhi note

The compiler still marks a compatible pair with `FLAGS=0xE`. The canonical
example now uses two scoped Ring-0 Stores to the same Asiddha target.

No current Lean theorem establishes atomic execution of that pair. Until an
atomic transition/refinement is formalized, “Sandhi atomicity” is a compiler
intent and historical runtime behavior, not a machine-checked guarantee.

---

## 17. Normative references

For the current revision, use these in order:

1. `lean/PSL/Semantics.lean` — machine-checked abstract/control semantics
2. `src/utils/paninian_compiler.py` — executable compiler implementation
3. `tests/test_semantic_contract.py` and `tests/test_canonical_programs.py`
4. `docs/VERIFICATION_STATUS.md` — claim ledger
5. `docs/SEMANTIC_GAPS.md` — resolved/open inconsistencies

Historical sprint files and firmware are evidence of development history, not
automatically normative for the repaired language.
