# PSL Novelty Contract

## Status

PSL has **not yet established a novel research result** in semantic continuity. The current repository contains a verified baseline and a promising research hypothesis.

This document constrains how the project describes itself until stronger evidence exists.

## Claims PSL must not make

PSL must not claim to have invented:

- portable intermediate representations;
- platform-independent models;
- proof-carrying code;
- proof-carrying hardware;
- verified compilation;
- verified device drivers;
- multi-target compilation;
- multilingual abstract/concrete syntax;
- modular proof reuse under language extension;
- legacy emulation;
- hardware abstraction;
- contract-based systems engineering;
- fail-stop compilation/refusal.

It must also not claim that a Sanskrit or Pāṇinian vocabulary is itself a technical contribution.

## Claims that are currently safe

The current repository may accurately say:

- PSL is an **open research prototype**;
- it has a Lean-checked repaired semantic baseline;
- it has an initial semantic-identity / PVM32-binding separation;
- the current boolean capability model is not a realization proof;
- semantic continuity across hardware generations is an **open hypothesis**;
- the planned evaluation will use deterministic virtual hardware and explicit adversarial cases;
- physical-device conformance is outside the present proof boundary.

## Open hypotheses

### Semantic continuity

A semantic contract can remain unchanged while materially different device generations realize it.

### Realization soundness

A checker can reject semantically incorrect realizations even when their low-level requests are syntactically valid.

### Localized proof evolution

Changing a realization/device model can preserve unrelated upstream semantic evidence.

### Fail-closed incompatibility

A target lacking required semantics is rejected instead of silently degraded.

None of these should be described as established until proved and evaluated.

## Required evidence for a stronger claim

A stronger research claim requires at minimum:

1. one formal semantic contract with an explicit observation model;
2. two materially different accepted device models/realizations;
3. one incapable target rejected;
4. adversarial wrong-binding, wrong-scaling, wrong-unit, wrong-order/state cases rejected;
5. a machine-checked soundness statement for the realization checker or relation;
6. measured proof/evidence reuse under hardware substitution;
7. a comparison against a conventional refinement/specification baseline;
8. an updated prior-art review showing what remains distinct.

## Language policy

Use:

- "investigates";
- "hypothesis";
- "prototype";
- "current evidence";
- "formal model";
- "simulation evidence";
- "not yet proved".

Avoid until earned:

- "universal";
- "first";
- "novel" without a cited comparison;
- "hardware independent" without a defined observation/refinement relation;
- "proof of real hardware" when only a virtual model has been verified.

## Pāṇinian origin

The project began with a Pāṇinian-inspired language architecture.

That origin is documented historically, but the current research programme does not assume that Pāṇinian structures are necessary or advantageous. Any future Pāṇinian claim must demonstrate a formal property or measurable proof-engineering advantage against a conventional formulation.

See [Historical Pāṇinian Origin](historical/PANINIAN_ORIGIN.md).

## Kill rule

If the strongest surviving property can already be obtained just as directly with standard transition systems, refinement relations, and existing certification techniques, PSL should say so and narrow its contribution accordingly.
