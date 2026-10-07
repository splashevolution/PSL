# PSL Research Specification

**Revision:** semantic-continuity reset, October 2026  
**Status:** research hypothesis; not yet an established novelty result

## 1. Purpose

PSL studies whether software intent can remain stable while target
implementations and hardware generations change.

The active research boundary is:

```text
SemanticContract
      ↓
Realization + evidence
      ↓
checked relation
      ↓
DeviceModel
```

A realization is accepted only when its evidence establishes the required
observable behavior. A capability declaration alone is insufficient.

## 2. Core objects

The intended formal model will distinguish:

- **SemanticContract** — target-neutral behavioral requirement;
- **Observation** — behavior visible at the semantic boundary;
- **DeviceModel** — target state, transitions, and observations;
- **Realization** — mapping from semantic operation to target operations;
- **RealizationEvidence** — certificate/proof material for that mapping;
- **Checker** — fail-closed validator of realization evidence;
- **Continuity** — relation saying materially different realizations satisfy
  the same contract;
- **Evolution** — relation describing which prior evidence remains valid after
  a controlled change.

The exact Lean definitions remain research work.

## 3. First soundness shape

The target theorem/checker should eventually support a statement resembling:

```text
Check(C, D, R, π) = true
        ⇒
Obs(Execute(D, R(C))) satisfies C
```

The final relation may use trace inclusion, simulation, refinement, or another
precise observational relation depending on nondeterminism and failure
semantics.

## 4. Fail-closed requirement

A target that cannot satisfy the semantic contract must be rejected.

Silent degradation is not permitted unless the contract itself allows the
degraded behavior.

## 5. Adversarial requirement

The first model must distinguish protocol validity from semantic correctness.

Examples that should be rejectable include:

- wrong target resource/register;
- wrong scale or representation;
- wrong unit;
- wrong byte order;
- missing privilege/configuration transition;
- invalid command ordering;
- ignored failure acknowledgement;
- volatile behavior when persistence is required;
- non-atomic behavior when atomicity is required.

## 6. Hardware-generation substitution

A first continuity experiment should hold one contract fixed while testing:

```text
Legacy A      → ACCEPT if faithful
Modern B      → ACCEPT independently
Incapable C   → REFUSE
```

A and B should differ materially in representation or interaction model, not
only in address.

## 7. Proof-reuse measurement

When A is replaced by B, evaluation must report at least:

- semantic-contract changes;
- semantic proof changes;
- upstream certificates invalidated;
- new device-model obligations;
- new realization obligations;
- checker changes;
- proof-check time;
- percentage of prior evidence reused.

## 8. Current compatibility baseline

The existing PVM32 source language, 32-bit ABI, Python compiler, and Lean
control semantics are retained as a verified/repaired historical baseline.

Their legacy identifiers are not the vocabulary of the new research model.

The machine-checked authority for that baseline is
`lean/PSL/Semantics.lean`.

## 9. Scope boundary

PSL is not an operating system, emulator, Sanskrit language project, natural
language parser, or generic compiler framework.

Virtual hardware is test infrastructure.

## 10. Claim discipline

The project may call semantic continuity, realization soundness, fail-closed
compatibility, and localized proof reuse **hypotheses** until they are formally
specified, mechanically checked, experimentally evaluated, and compared with
existing refinement/certification approaches.

See `docs/NOVELTY_CONTRACT.md`.
