# PSL Verification Status

This document is the claim ledger for PSL. It separates machine-checked theorems,
executable test evidence, model-level properties, assumptions, and research hypotheses.

A claim may be promoted only when the stronger evidence exists in the repository.

## Evidence labels

- **PROVED** — discharged by the Lean kernel in a CI-backed `lake build`, without `sorry` and without depending on an unproved project axiom for the stated claim.
- **AXIOM-DEPENDENT** — theorem is accepted by Lean but transitively depends on a project axiom.
- **TESTED** — supported by executable tests or QEMU runs, not a mathematical proof.
- **MODEL-ONLY** — established only for PSL's abstract machine, not for RV32 hardware semantics.
- **HYPOTHESIS** — research motivation or performance/systems claim that has not yet been established.
- **UNPROVEN** — intended property for which neither a sufficient proof nor sufficient experimental evidence currently exists.

## Current ledger

| Claim | Status | Evidence / limitation |
|---|---|---|
| `IRNode.lower` is a pure deterministic function of an `IRNode` | UNVERIFIED IN CURRENT REVISION | The historical declaration was reflexive and the first real CI-backed Lean build currently fails before the formal file can be accepted as a whole. |
| `lowerAll` preserves list length | UNVERIFIED IN CURRENT REVISION | Intended local theorem; current repair CI must first typecheck the formal module. |
| Sañjñā-resolved and direct-address programs always compile to identical binaries | UNPROVEN in general | Current Lean theorem assumes `lowerAll ir1 = lowerAll ir2` and returns that assumption. Executable tests cover selected examples. |
| WRITE to an Asiddha target is rejected by the abstract `step` relation | SEMANTIC CONFLICT | The pre-repair Lean model rejects it, while Sprint 9 firmware and canonical examples allow a Ring-2 WRITE to Asiddha via a write cache. See `docs/SEMANTIC_GAPS.md` G1. |
| Explicit Lopa of an unwritten target is rejected by the abstract `step` relation | SEMANTIC CONFLICT / UNVERIFIED | Runtime clears written-state after Lopa; the Python compiler historically did not. See `docs/SEMANTIC_GAPS.md` G2. |
| OPEN followed by CLOSE restores the prior ring in the abstract machine | UNVERIFIED IN CURRENT REVISION | Intended model property; current repair CI must first typecheck the formal module. |
| Every `paribhasha_ok` IR program executes successfully after lowering | WITHDRAWN / UNPROVEN | The old theorem and `p2_runtime_correctness` axiom were removed from the repair branch. The goal is not currently valid until G1/G2 semantics are reconciled. |
| PSL has a CompCert-equivalent compiler correctness proof | HYPOTHESIS / NOT ESTABLISHED | The repository has a CompCert-inspired structure, but the principal soundness result still depends on a project axiom and does not prove source-to-RV32 semantic preservation. |
| 5000 generated differential cases passed | TESTED | Historical result from `run_differential_tests.py`; this tests implementation agreement over the generated domain, not semantic correctness by itself. |
| RV32 QEMU pipelines emit the expected UART/MMIO markers | TESTED | Firmware pipelines execute under QEMU `virt`. This is execution evidence, not proof of physical-silicon behavior. |
| PSL structurally prevents the documented P1-P4b classes in its compiler model | TESTED + PARTLY MODEL-PROVED | Scope depends on the precise predicates implemented. This claim must not be generalized to arbitrary memory-safety, scheduling, or hardware-isolation properties. |
| Sandhi is atomic at hardware level | UNPROVEN | The compiler marks fused pairs. A hardware-level atomicity theorem/refinement is not currently present. |
| PSL is leaner/faster/more deterministic than conventional systems | HYPOTHESIS | Requires controlled comparative measurements and a defined baseline. |
| Paninian structure makes whole classes of embedded bugs inexpressible | HYPOTHESIS, scoped | Demonstrated only for explicitly encoded legality predicates; it is not established as a general statement about embedded bugs. |
| Results apply to physical RISC-V silicon | UNPROVEN | Current runtime evidence is QEMU-based. |

## Current blocking obligations

The first priority is semantic agreement across compiler, specification, executable runtime, and Lean. Two concrete contradictions are documented in `docs/SEMANTIC_GAPS.md`. After those are resolved, the principal formal gap remains:

```text
compile-time p2_ok
        +
execution of the lowered prefix
        =>
runtime MachineState.written agrees with the compile-time written set
```

The current Lean development introduces this bridge as:

```lean
axiom p2_runtime_correctness ...
```

Until that axiom is eliminated (or the main theorem is explicitly weakened), the
repository must describe `compile_sound` as **axiom-dependent**.

## Abstraction boundaries

PSL currently contains several distinct layers. Evidence at one layer must not be
silently promoted to another.

```text
PSL source / compiler predicates
          ↓
Prakriya IR
          ↓
Lean abstract machine
          ↓  [refinement not yet proved]
RV32 firmware implementation
          ↓
QEMU virt execution
          ↓  [physical-hardware evidence not yet present]
RISC-V silicon
```

Future work should attach an explicit refinement obligation to each downward arrow.

## Repair gate

Before adding language features, PSL should satisfy all of the following:

1. No principal theorem depends on `p2_runtime_correctness` or another undocumented project axiom.
2. The compiler-soundness theorem states exactly which source semantics are preserved.
3. Sañjñā identity is proved from symbol-resolution semantics rather than assumed binary equality.
4. Sandhi semantics are represented in the formal machine before claiming atomicity.
5. Property tests include invalid/adversarial programs and mutation tests, not only valid generated programs.
6. README, STATUS, paper, and evidence use the labels in this ledger consistently.
7. RV32 claims are separated from abstract-machine claims until a refinement argument exists.

This file is intentionally conservative. Claims should move upward only when their
supporting proof or experiment is present and reproducible.
