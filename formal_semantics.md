# PSL Formal Semantics — Active Research Boundary

## Authority

The active research direction is specified conceptually in
`docs/SEMANTIC_CONTINUITY.md`.

The existing machine-checked implementation authority remains
`lean/PSL/Semantics.lean`, but that module describes the repaired **legacy
PVM32 control model**, not the final semantic-continuity theory.

## Current proved baseline

The central repaired theorem has the following shape:

> if canonical validation of a PVM32 word stream succeeds from a control
> state, abstract execution of that same stream from a machine with the same
> control state succeeds and ends with the same final control state.

The repository also checks a finite Python-to-Lean corpus.

This does not establish:

- universal source-compiler correctness;
- realization correctness for arbitrary device bindings;
- hardware-generation continuity;
- virtual-to-physical device equivalence.

## Emerging semantic-continuity layer

The next formal model should define:

```text
SemanticContract
Observation
DeviceModel
Realization
RealizationEvidence
Checker
```

and a soundness statement resembling:

```text
Check(C, D, R, π) = true
        ⇒
observable behavior of Execute(D, R(C))
satisfies C
```

The exact observational/refinement relation is intentionally still open.

## Compatibility terminology

The existing PVM32 Lean model contains historical ABI identifiers. They are
preserved to maintain proof and execution lineage, not because they define the
new research vocabulary.

See `docs/TERMINOLOGY_AUDIT.md`.

## Archived prior document

The previous detailed language/ABI semantics document is preserved at:

`docs/historical/legacy-language-baseline-20261007/formal_semantics.md`.
