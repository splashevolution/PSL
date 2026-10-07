# PSL — Project Manifest

**Direction:** semantic continuity across hardware generations  
**Status:** open research prototype

## Research question

PSL investigates whether a stable semantic contract can survive materially
different target implementations while each realization is checked
independently, incompatible targets fail closed, and unrelated upstream proof
evidence remains reusable.

The project is no longer developed as a Sanskrit or Pāṇinian programming
language experiment.

## Active research documents

The current research contract is defined by:

- `docs/RESEARCH_CHARTER.md`
- `docs/PRIOR_ART.md`
- `docs/NOVELTY_CONTRACT.md`
- `docs/SEMANTIC_CONTINUITY.md`
- `docs/THREAT_MODEL.md`
- `docs/EVALUATION_PROTOCOL.md`
- `docs/TERMINOLOGY_AUDIT.md`

## Formal baseline

The repository retains a repaired PVM32 compiler/Lean baseline because it
provides useful checked implementation history.

Important files:

- `lean/PSL/Semantics.lean` — repaired legacy PVM32 abstract/control semantics;
- `lean/PSL/SemanticKernel.lean` — small language-neutral semantic checkpoint;
- `lean/PSL/PVM32Driver.lean` — Realization 0 / compatibility adapter;
- `tests/` — current Python regression and adversarial tests;
- `scripts/generate_lean_conformance.py` — finite Python-to-Lean conformance corpus.

Historical identifiers in the PVM32 compiler and ABI are compatibility names,
not current research vocabulary. See `docs/TERMINOLOGY_AUDIT.md`.

## Evidence boundary

The project distinguishes:

1. Lean theorems about stated formal models;
2. finite compiler/regression evidence;
3. virtual-hardware execution evidence;
4. future physical-device conformance evidence.

No category automatically proves another.

## Current research sequence

The next formal line is expected to introduce neutral objects such as:

```text
SemanticContract
Observation
DeviceModel
Realization
RealizationEvidence
RealizationChecker
Continuity
Evolution
```

The first falsification target is a syntactically valid but semantically wrong
target realization: wrong binding, scale, unit, byte order, state transition,
or failure handling must be rejectable without trusting the realization
generator.

## Virtual hardware

PSL's core research should be reproducible without specialized equipment.
QEMU, Renode, or small deterministic emulators may be used as external
evaluation infrastructure.

Operating-system and general virtual-hardware engineering are outside PSL's
research scope.

## Historical material

Earlier Pāṇinian/Sanskrit work is retained under explicit historical paths for
provenance. It should not be read as the current novelty claim.

Start with `docs/historical/PANINIAN_ORIGIN.md`.
