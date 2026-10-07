# PSL Semantic Gaps Under Repair

This document records semantic contradictions discovered by the first real CI-backed
Lean typecheck and cross-check against the compiler and RV32 firmware.

These are **design decisions to resolve**, not proof obligations to paper over.

## G1 — Ring-2 WRITE to Asiddha is inconsistent across layers

### Compiler / examples
The canonical Sprint 9 program emits:

```text
0x200560E0  Write Yantra (target 0x60, Ring 2)
```

Yantra (0x60) is in the Asiddha region (>= 0x50).

The Python compiler accepts this program.

### Sprint 9 RV32 firmware
`pvm_firmware_sandhi.c` explicitly supports WRITE to both regions:

- Siddha target -> `siddha_global_bus`
- Asiddha target -> `asiddha_write_cache`

### Lean abstract machine (pre-repair)
The `step` relation rejects OP_WRITE when `target >= ASIDDHA_BASE`.

### Consequence
The previous compiler-soundness argument attempted to derive a
`write_siddha` precondition that is not supplied by the compiler predicates.
The intended compiler-soundness theorem is therefore not currently provable
without first choosing and documenting the intended WRITE semantics.

### Decision required
Choose one canonical rule and make compiler, spec, Lean model, and firmware agree:

A. Ring-2 WRITE may target Asiddha but goes to a non-global/shadow write cache; or
B. Ring-2 WRITE is Siddha-only and Sprint 9/compiler behavior must change.

Current implementation evidence favors **A**, but no repair should silently
make this choice without updating all layers together.

---

## G2 — P2 written-state lifetime is inconsistent after Lopa

### Python compiler
`validate_ir` adds explicit WRITE/STORE targets to `written_targets` but
does not remove a target after Lopa.

Therefore P2 currently means approximately:

> "this address has been written at least once earlier in the stream."

### Runtime
The latest lifecycle runtime clears `written[target]` when Lopa executes.
A second explicit Lopa without an intervening write is rejected at runtime.

### Earlier Lean model
The Lean `p2_ok` model erased an address from its written set after Lopa,
matching the runtime rather than the Python compiler.

### Consequence
The old `p2_runtime_correctness` axiom attempted to bridge two state machines
that do not implement the same invariant.

### Decision required
Choose one meaning:

A. **Live-written semantics**: Lopa consumes the written state. A second
   explicit Lopa requires another WRITE/STORE first.
B. **Ever-written semantics**: once written, an address remains P2-eligible
   even after Lopa; runtime must stop rejecting the second explicit Lopa.

The lifecycle/erasure interpretation and runtime behavior favor **A**, but this
must be adopted explicitly and regression-tested.

---

## G3 — Lean file was not previously typechecked by the verification harness

The historical executable harness checked for theorem names as text. It did not
run `lake build`.

The repair branch adds a pinned Lean toolchain and CI that names
`PSL.Semantics` as the default target. That first real build exposed multiple
type errors in the formal source.

Until CI is green, no Lean declaration in this repository should be described
as a currently machine-checked result of this revision.

---

## Repair order

1. Keep feature development frozen.
2. Resolve G1 and G2 as language-spec decisions.
3. Make compiler + executable reference model agree with those decisions.
4. Add regression tests for both boundary cases.
5. Rebuild a minimal Lean model that typechecks.
6. Prove local safety properties.
7. Define an explicit source/runtime simulation relation.
8. Attempt compiler soundness only after the simulation relation exists.
9. Only then investigate RV32 refinement.

A green proof obtained by changing only the Lean model is **not** sufficient.
All executable and specification layers must agree on the same semantics.
