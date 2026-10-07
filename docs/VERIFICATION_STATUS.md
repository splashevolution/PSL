# PSL Verification Status

This is the authoritative claim ledger for the repaired PSL research prototype.
It separates machine-checked theorems, executable test evidence, historical
results, open refinements, and research hypotheses.

## Evidence labels

- **PROVED / MODEL-ONLY** — discharged by the Lean kernel in CI for PSL's abstract model.
- **TESTED** — supported by executable tests or QEMU runs; not a mathematical proof.
- **HISTORICAL** — evidence from an older sprint whose semantics may differ from the current contract.
- **UNPROVEN** — intended property without a sufficient proof.
- **HYPOTHESIS** — research or comparative claim requiring new evidence.
- **REMOVED / INCORRECT** — historical claim or theorem found to conflict with the current implementation/specification.

## Current ledger

| Claim | Status | Evidence / limitation |
|---|---|---|
| The current Lean module typechecks | PROVED / MODEL-ONLY | CI runs `lake build` against pinned Lean 4.34.1 with `PSL.Semantics` as the default target. |
| Lowering preserves ring/comp/opcode/cond | PROVED / MODEL-ONLY | `lower_preserves_core_fields`. |
| Lowering preserves instruction count | PROVED / MODEL-ONLY | `lowerAll_length_preserving`. |
| Sañjñā-equivalent IRs have identical lowered binaries | PROVED, but definitional/weak | `sanjnaa_equiv_is_binary_identity`; `sanjnaaEquiv` is currently defined as lowered-binary equality, so this does not yet prove symbol-resolution correctness. |
| Ring-2 WRITE to Asiddha is rejected | REMOVED / INCORRECT | Canonical PSL permits Ring-2 WRITE to Asiddha. Historical Sprint 9 examples/firmware already relied on this behavior. |
| Lopa consumes live-written state | TESTED + MODELLED | Python semantic-contract tests cover double-Lopa rejection and re-establishment after a new write; Lean `controlStep` uses the same lifecycle. |
| Lopa clears inheritance context | TESTED + MODELLED | Canonical repair decision. Python tests reject post-Lopa Anuvṛtti without new explicit context; Lean `controlStep` sets `contextTarget := none`. |
| Store requires Adhikāra and Ring 0 | TESTED + MODELLED | Python validator and Lean `controlStep` enforce both conditions. |
| Asiddha Lopa requires Adhikāra and Ring 0 | TESTED + MODELLED | Python validator and Lean `controlStep` enforce both conditions. |
| Successful canonical word validation implies successful abstract execution with the same final control state | PROVED / MODEL-ONLY | `validateWords_execution`, axiom-free. |
| Successful validation of lowered IR implies successful abstract execution | PROVED / MODEL-ONLY | `validated_ir_executes`, axiom-free. |
| A `ValidProgram` executes and ends with closed Adhikāra scope | PROVED / MODEL-ONLY | `valid_program_executes`, axiom-free. |
| The principal repaired theorems depend on no PSL project axiom or `sorryAx` | CI-AUDITED | `lean/Audit.lean` prints theorem dependencies; current output lists only Lean's standard `propext`. CI fails on `sorryAx` or reintroduction of `p2_runtime_correctness`. |\n| Current Python compiler outputs are accepted by Lean for the canonical finite corpus | TESTED CROSS-LANGUAGE | CI compiles 8 checked-in programs plus 57 deterministic generated variants, feeds 65 emitted word streams to Lean, and round-trips 22 distinct ABI words through `decodeABIWord`. This is finite conformance, not a universal compiler theorem. |\n| Canonical adversarial ABI streams are rejected by Lean | TESTED / MODEL-ONLY | `lean/NegativeConformance.lean` checks missing context, unmatched CLOSE, privilege/region violations, Store scope/ring errors, P2 double-Lopa, Lopa context boundary, and unclosed scope. |
| Python compiler acceptance implies Lean `ValidProgram` | UNPROVEN | This is the next major compiler/formal correspondence obligation. |
| Āvṛtti semantics are preserved end-to-end | UNPROVEN | Count encoding exists historically; current repaired formal machine does not yet model repetition. |
| Utsarga/Apavāda semantics are preserved end-to-end | UNPROVEN | Historical firmware evidence exists; current repaired formal model does not yet model conditional behavior. |
| Sandhi executes atomically | UNPROVEN | Historical compiler/firmware mark or simulate fused pairs, but current formal model does not prove atomicity. |
| Lean abstract semantics refine a canonical RV32 implementation | UNPROVEN | Historical RV32 firmware evolved across sprints and is not a single proved refinement target. |
| QEMU observations establish physical-silicon behavior | UNPROVEN | No physical RISC-V refinement/evidence is established. |
| PSL has a CompCert-equivalent compiler-correctness proof | NOT ESTABLISHED | The current theorem is a validator-to-abstract-execution forward simulation, not source-to-RV32 semantic preservation. |
| 5000 generated differential cases passed | HISTORICAL / TESTED | Useful regression evidence for the historical generated domain; not a proof of current semantics. |
| Historical RV32/QEMU pipelines emitted expected UART/MMIO markers | HISTORICAL / TESTED | Valid execution evidence for those sprint implementations, not proof of the repaired canonical model. |
| PSL is leaner/faster/more deterministic than conventional systems | HYPOTHESIS | Requires a defined baseline and controlled measurement. |
| Pāṇinian structure makes broad classes of embedded bugs inexpressible | HYPOTHESIS, scoped | Defensible only for the exact legality predicates encoded and verified. |

## Retired proof path

The historical formal file introduced:

```lean
axiom p2_runtime_correctness ...
```

and used it in a purported `compile_sound` proof. The first genuine CI-backed
Lean build also exposed type errors in that proof development.

The repaired model removes both the project axiom and the unverified theorem
path. P2/live-written behavior and inheritance context are now explicit pieces
of the canonical control transition. The new theorem proves forward simulation
from that executable validator transition to the abstract execution transition.

This is a stronger trust story, but a narrower claim than end-to-end compiler correctness.

## Canonical abstraction boundaries

```text
PSL source
   ↓  [Python compiler -> Lean correspondence: OPEN]
validated/lowered ABI words
   ↓  [validateWords_execution: PROVED]
Lean abstract execution
   ↓  [canonical RV32 refinement: OPEN]
RV32 implementation
   ↓  [QEMU execution evidence]
QEMU virt
   ↓  [physical-hardware refinement/evidence: OPEN]
RISC-V silicon
```

Additional semantic dimensions still need explicit models before they can enter
the end-to-end theorem:

```text
Āvṛtti repetition
Utsarga / Apavāda conditions
Sandhi atomicity
memory visibility / Siddha-Asiddha storage refinement
```

## Repair gate before further feature development

1. Keep Lean CI and theorem-dependency audit green.
2. Establish Python compiler → Lean `ValidProgram` correspondence for the canonical subset.
3. Repair or classify historical example programs that contradict the canonical contract.
4. Synchronize `formal_semantics.md`, `SPEC.md`, and the paper with the repaired model.
5. Add generated/adversarial tests for the canonical validator, not only happy-path examples.
6. Model Āvṛtti, conditions, and Sandhi separately with falsification tests before extending the main theorem.
7. Select one canonical RV32 runtime and prove/test its refinement to the Lean machine.
8. Only then reconsider an end-to-end compiler-soundness claim.

Claims should be promoted only when the stronger evidence is present and reproducible.
