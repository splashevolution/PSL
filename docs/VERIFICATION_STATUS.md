# PSL Verification Status

This document is the claim ledger for PSL. It separates machine-checked theorems,
executable test evidence, model-level properties, assumptions, and research hypotheses.

A claim may be promoted only when the stronger evidence exists in the repository.

## Evidence labels

- **PROVED** — discharged by the Lean kernel without `sorry` and without depending on an unproved project axiom for the stated claim.
- **AXIOM-DEPENDENT** — theorem is accepted by Lean but transitively depends on a project axiom.
- **TESTED** — supported by executable tests or QEMU runs, not a mathematical proof.
- **MODEL-ONLY** — established only for PSL's abstract machine, not for RV32 hardware semantics.
- **HYPOTHESIS** — research motivation or performance/systems claim that has not yet been established.
- **UNPROVEN** — intended property for which neither a sufficient proof nor sufficient experimental evidence currently exists.

## Current ledger

| Claim | Status | Evidence / limitation |
|---|---|---|
| `IRNode.lower` is a pure deterministic function of an `IRNode` | PROVED, but weak | `L1_lower_deterministic` is reflexivity (`lower n = lower n`). It establishes function equality only in the trivial sense and is not a compiler-determinism theorem. |
| `lowerAll` preserves list length | PROVED | `L2_lower_length_preserving`. |
| Sañjñā-resolved and direct-address programs always compile to identical binaries | UNPROVEN in general | Current Lean theorem assumes `lowerAll ir1 = lowerAll ir2` and returns that assumption. Executable tests cover selected examples. |
| WRITE to an Asiddha target is rejected by the abstract `step` relation | PROVED / MODEL-ONLY | `write_to_asiddha_fails`. This is not an RV32 memory-protection theorem. |
| Explicit Lopa of an unwritten target is rejected by the abstract `step` relation | PROVED / MODEL-ONLY | `lopa_requires_prior_write`, under its stated state hypotheses. |
| OPEN followed by CLOSE restores the prior ring in the abstract machine | PROVED / MODEL-ONLY | `open_close_ring_identity`. |
| Every `paribhasha_ok` IR program executes successfully after lowering | AXIOM-DEPENDENT | `compile_sound` / `compile_sound_statement` depend on `p2_runtime_correctness`. The missing obligation is the forward-simulation relation between compile-time P2 tracking and runtime `MachineState.written`. |
| PSL has a CompCert-equivalent compiler correctness proof | HYPOTHESIS / NOT ESTABLISHED | The repository has a CompCert-inspired structure, but the principal soundness result still depends on a project axiom and does not prove source-to-RV32 semantic preservation. |
| 5000 generated differential cases passed | TESTED | Historical result from `run_differential_tests.py`; this tests implementation agreement over the generated domain, not semantic correctness by itself. |
| RV32 QEMU pipelines emit the expected UART/MMIO markers | TESTED | Firmware pipelines execute under QEMU `virt`. This is execution evidence, not proof of physical-silicon behavior. |
| PSL structurally prevents the documented P1-P4b classes in its compiler model | TESTED + PARTLY MODEL-PROVED | Scope depends on the precise predicates implemented. This claim must not be generalized to arbitrary memory-safety, scheduling, or hardware-isolation properties. |
| Sandhi is atomic at hardware level | UNPROVEN | The compiler marks fused pairs. A hardware-level atomicity theorem/refinement is not currently present. |
| PSL is leaner/faster/more deterministic than conventional systems | HYPOTHESIS | Requires controlled comparative measurements and a defined baseline. |
| Paninian structure makes whole classes of embedded bugs inexpressible | HYPOTHESIS, scoped | Demonstrated only for explicitly encoded legality predicates; it is not established as a general statement about embedded bugs. |
| Results apply to physical RISC-V silicon | UNPROVEN | Current runtime evidence is QEMU-based. |

## Principal open proof obligation

The highest-priority formal gap is:

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
