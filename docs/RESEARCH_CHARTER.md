# PSL Research Charter

## Purpose

PSL investigates **semantic continuity across implementation and hardware evolution**.

The project asks whether software intent can be represented by a stable semantic contract whose target-specific realizations can be checked independently, with incorrect or incapable targets rejected and unrelated semantic evidence preserved.

This charter governs new research work. Historical code may contain earlier terminology or experiments that are not current research claims.

## Primary research questions

1. Can a semantic contract remain invariant while hardware/device realizations change materially?
2. Can realization correctness be established by evidence stronger than a driver-declared capability flag?
3. Can incompatible realizations fail closed rather than being silently emulated or degraded?
4. Can proof obligations caused by hardware substitution remain local to the realization boundary?
5. How much previously established evidence survives controlled evolution?

## Working objects

The intended theory will distinguish at least:

- **SemanticContract** — target-neutral observable requirements;
- **Observation** — the behavior visible at the semantic boundary;
- **DeviceModel** — formal state and transition model of a target;
- **Realization** — mapping from semantic operations to target operations;
- **RealizationEvidence** — proof/certificate material connecting a realization to the contract;
- **Checker** — small fail-closed verifier of that evidence;
- **Continuity relation** — condition under which different realizations satisfy the same contract;
- **Evolution relation** — condition under which old evidence remains valid after a controlled change.

Names may change as the theory becomes precise.

## Scope

PSL includes:

- formal semantics;
- refinement / realization relations;
- proof-producing or certificate-checking experiments;
- fail-closed compatibility;
- proof-reuse measurements;
- deterministic virtual-device evaluation;
- adversarial realizations.

## Explicit non-goals

PSL is not an operating system, hypervisor, emulator, generic hardware-abstraction layer, Sanskrit language, natural-language parser, or replacement for established compiler infrastructures.

QEMU, Renode, VirtualBox, or similar tools may be used as **test infrastructure**, but virtual-hardware engineering belongs outside the core PSL research contribution.

## Reproducibility constraint

Core PSL experiments should be runnable without specialized physical equipment.

A preferred research artifact should reduce to:

```text
git clone
  ↓
Lean + Python
  ↓
deterministic model / virtual hardware
  ↓
proofs + traces + adversarial failures
```

Physical devices may later test model-to-device conformance, but they are optional validation rather than a prerequisite.

## Evidence taxonomy

PSL must label evidence accurately.

**Theorem evidence** supports a property of the formal model under stated assumptions.

**Finite test evidence** supports covered cases only.

**Simulation evidence** shows behavior of the selected virtual implementation.

**Physical evidence**, if later collected, supports an empirical device/model relationship.

No category automatically implies another.

## Success criteria

A meaningful first result should show one frozen semantic contract with:

- two materially different accepted realizations;
- one incapable realization that is mechanically refused;
- several syntactically valid but semantically wrong realizations that are rejected;
- no semantic-contract change between accepted hardware generations;
- measurable reuse of upstream proof/evidence.

## Kill criteria

The central hypothesis weakens materially if:

- correct and incorrect bindings cannot be distinguished without trusting the driver;
- adding a new target forces target details into the semantic contract;
- replacing a target requires global reproving of unrelated semantics;
- the checker becomes as complex/trusted as the realization itself;
- simulation-specific assumptions leak into the semantic theory;
- the approach provides no measurable benefit over ordinary refinement/specification techniques.

A negative result is acceptable. The project must not preserve a claim merely because it is attractive.
