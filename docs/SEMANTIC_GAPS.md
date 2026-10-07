# PSL Semantic Gaps Under Repair

This document records semantic contradictions discovered by cross-checking the
compiler, historical firmware, example programs, specification, and a real
CI-backed Lean build.

Resolved entries are retained because they explain why the repaired semantics
differ from some historical sprint artifacts.

## G1 — Ring-2 WRITE to Asiddha — RESOLVED

### Conflict

Historical Lean rejected OP_WRITE when the target was `>= ASIDDHA_BASE`.

The canonical Sprint 9 program and firmware explicitly allowed Ring-2 WRITE to
Yantra at `0x60` (Asiddha), using the region's non-global/shadow behavior.

### Decision

**Ring-2 WRITE to Asiddha remains legal.**

Address visibility/storage behavior belongs to the Siddha/Asiddha memory model;
WRITE is not rejected solely because the address is Asiddha.

### Repair

- Python semantic-contract test locks this behavior.
- Repaired Lean `controlStep` does not impose the historical
  `WRITE -> Siddha-only` rule.
- The old `write_to_asiddha_fails` theorem is retired as incorrect for the
  canonical language.

A future RV32 refinement must specify exactly where Ring-2 Asiddha writes are
stored and what observers can see them.

---

## G2 — P2 written-state lifetime after Lopa — RESOLVED

### Conflict

Historical Python validation approximately meant:

> this address was written at least once earlier.

Historical runtime code instead cleared `written[target]` after Lopa.

The old `p2_runtime_correctness` axiom therefore attempted to relate two
different state machines.

### Decision

**P2 uses live-written semantics.**

Lopa consumes the live-written state. Another Lopa of that target requires a
new intervening WRITE/STORE.

### Repair

- Python validator discards the target from its live-written state after Lopa.
- A subsequent WRITE/STORE re-establishes live-written state.
- Lean `controlStep` follows the same lifecycle.
- Regression tests cover double-Lopa rejection and write-after-Lopa recovery.
- The old `p2_runtime_correctness` project axiom has been removed.

---

## G3 — Lean source was not actually typechecked — RESOLVED

### Conflict

The historical executable “verified compilation” harness checked that theorem
names and strings occurred in `Semantics.lean`. It did not run a real Lean
build.

When the repair branch first made `PSL.Semantics` an actual Lake target, the
historical file failed with multiple Lean errors.

### Repair

- Lean is pinned with `lean-toolchain`.
- `PSL.Semantics` is the default Lake target.
- GitHub Actions runs `lake build`.
- The formal core was rebuilt rather than forcing the broken proof through.
- Current CI typechecks the repaired module successfully.
- `lean/Audit.lean` prints dependencies of the principal theorems and CI fails
  on `sorryAx` or reintroduction of `p2_runtime_correctness`.

---

## G4 — Meaning of Lopa for Anuvṛtti context — RESOLVED

### Conflict

Sprint 5 defined Lopa as an inheritance boundary: it clears `prev_target`, so
the next target-less instruction cannot inherit through the erased context.

Sprint 13 later emitted:

```text
explicit Lopa key
Anuvṛtti Lopa
```

and its firmware preserved/updated `prev_target` across Lopa so the second
erasure could inherit the same address.

Those meanings are incompatible.

### Decision

**Lopa is a hard context boundary.**

After Lopa, there is no live Anuvṛtti target until a new explicit instruction
establishes one.

This choice matches the earlier structural meaning of Lopa and makes the
boundary enforceable by the compiler rather than firmware convention.

### Repair

- Python validator tracks a live `context_target`.
- Lopa clears it.
- Anuvṛtti with no live context is a P1-class compile error.
- Lean `ControlState.contextTarget` and `controlStep` use the same rule.
- Regression tests cover post-Lopa Anuvṛtti rejection.

### Historical impact

Sprint 13's inherited-Lopa example and firmware are now **historical artifacts**,
not canonical semantics. The key-lifecycle example must be rewritten before it
can be used as current evidence.

---

## G5 — Ring represented twice — RESOLVED AT ABSTRACT MODEL

### Conflict

`formal_semantics.md` historically stated that ring is an instruction-level
ABI attribute, but the old Lean `MachineState` also stored a mutable global
ring changed by OPEN/CLOSE.

This created two privilege authorities and contributed to a false theorem that
OPEN then CLOSE restored an arbitrary previous ring. CLOSE actually selected
Ring 2 in that model.

### Decision

**Ring is an instruction attribute. Adhikāra is tracked as lexical/runtime scope depth.**

### Repair

The canonical Lean state now contains:

```text
ControlState
  written
  contextTarget
  scopeDepth
```

and each ABI word carries its own ring. Store and Asiddha-Lopa legality requires
both the correct ring bit and active Adhikāra scope.

`formal_semantics.md` still needs synchronization and should be treated as a
historical design document until that rewrite is complete.

---

## G6 — Multiple RV32 firmware semantics — OPEN

The repository contains firmware produced at different sprints. Their behavior
is not uniform:

- earlier firmware models only subsets of the language;
- Lopa/context behavior changed;
- privilege and region checks differ;
- Sandhi implementations stage/commit state differently.

Therefore “the RV32 firmware implements PSL” is too broad.

### Required repair

1. Select or create **one canonical RV32 runtime**.
2. Give it the same control state as the Lean model.
3. Add a portable reference interpreter test vector shared by Python/Lean/RV32.
4. Compare every canonical word-stream transition against the reference.
5. Only then attempt an RV32 refinement theorem/argument.

Historical sprint firmware should remain for provenance, but not serve as
simultaneous authorities.

---

## G7 — Historical examples cross semantic eras — RESOLVED

Some files in `programs/` encode assumptions that later rules invalidate.

Known examples include:

- `key_lifecycle.pvm`: inherited Lopa after Lopa conflicts with G4.
- `lopa_core.pvm`: demonstrates post-Lopa Anuvṛtti at runtime; the repaired
  compiler now rejects this structurally.
- `paribhasha_valid_core.pvm`: contains a privileged Store outside Adhikāra,
  which became illegal after P4.
- `sandhi_core.pvm`: its historical pair predates the later privileged-Store
  contract.

### Repair

The pre-repair text of all four conflicting examples is preserved under
`programs/historical/`.

The active examples were rewritten to the canonical contract:

- active `lopa_core.pvm` stops at the Lopa boundary;
- active `sandhi_core.pvm` uses a scoped same-ring Store/Store pair;
- active `paribhasha_valid_core.pvm` scopes its privileged Store;
- active `key_lifecycle.pvm` removes the inherited Lopa through the boundary.

`tests/test_canonical_programs.py` locks exact ABI output for the four repaired
programs and confirms the other current scoped examples compile.

---

## Current repair order

1. Keep feature development frozen.
2. Keep Python semantic-contract and Lean verification CI green.
3. Repair/classify stale `.pvm` examples.
4. Synchronize `formal_semantics.md`, `SPEC.md`, and paper claims.
5. Prove Python compiler → Lean `ValidProgram` correspondence for the canonical subset.
6. Add formal semantics for Āvṛtti, Utsarga/Apavāda, and Sandhi.
7. Select one canonical RV32 runtime and establish refinement evidence.
8. Only then consider an end-to-end compiler-correctness claim.

A green proof obtained by changing only Lean is not sufficient. Compiler,
formal model, executable runtime, examples, and documentation must describe
the same language.


---

## G8 — Python compiler to Lean semantics — PARTIALLY CLOSED

A universal source/compiler correspondence is still open because the Python
parser/compiler has not been formalized in Lean.

However, the repair branch now has a concrete cross-language gate:

1. Python compiles the checked-in canonical programs.
2. A deterministic generator produces additional sources from the currently
   formalized subset.
3. Their exact numeric 32-bit binaries are emitted into an auto-generated Lean
   file.
4. Lean independently decodes those words with `decodeABIWord`.
5. Lean requires `validateEncodedClosed ... = true` for every accepted stream.
6. Every distinct emitted ABI word is required to round-trip through the Lean
   numeric decoder.
7. Separate adversarial numeric streams are required to evaluate to rejection.

Current passing corpus:

- 8 checked-in canonical programs;
- 57 deterministic generated variants;
- 65 accepted word streams total;
- 22 distinct ABI words;
- fixed negative cases for context, scope, privilege, P2, and Lopa boundaries.

This is strong finite conformance evidence, **not** a proof for all Python source
programs. The remaining research obligation is a formal source/IR
correspondence or a proof-producing compiler/certificate design.
