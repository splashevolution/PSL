# Terminology Audit

**Date:** 2026-10-07  
**Purpose:** separate the active semantic-continuity research vocabulary from historical Pāṇinian / Sanskrit prototype terminology.

## Policy

PSL no longer treats Pāṇinian terminology, Sanskrit syntax, or multilingual surfaces as part of its current novelty claim.

The active research vocabulary is deliberately neutral:

- semantic contract;
- observation;
- device model;
- realization;
- realization evidence / certificate;
- checker;
- refinement / continuity;
- fail-closed incompatibility;
- evolution-local proof reuse.

Historical terminology is preserved only where removing it would damage provenance, invalidate a verified compatibility baseline, or create high-risk churn with no research value.

## Classification

### A. Historical — preserve as provenance

These artifacts document the earlier research line and should remain available, preferably under explicit historical paths:

- Pāṇinian/Sanskrit case studies and rendered documents;
- pre-verification-repair specifications and manuscripts;
- historical sprint evidence;
- historical QEMU/RV32 pipeline records;
- old comparative examples;
- the original Pāṇinian project rationale.

Historical material may use its original terminology without implying a current claim.

### B. Compatibility baseline — preserve identifiers, do not extend

The repaired PVM32/Python/Lean baseline contains identifiers whose names are tied to the original ABI and proof history, including examples such as:

- `OP_LOPA`;
- `Region.Siddha` / `Region.Asiddha`;
- `in_adhikara`;
- `sandhi_fused`;
- `sanjnaaEquiv`;
- the Python `PaninianFormalCompiler` and related exception names;
- current `.pvm` source tokens and filenames.

These names are **frozen compatibility vocabulary**, not active research terminology.

They should not be copied into new semantic-continuity modules. Renaming them solely for aesthetics would create broad proof/test churn while adding no scientific value.

When the new semantic-continuity model supersedes this baseline, compatibility identifiers can be retired behind an archival boundary.

### C. Active-path cleanup — remove now

The following were not required for the repaired baseline and were removed from the active research path:

- the explicit English/Devanagari `SurfaceForm` witness;
- the cross-surface equivalence theorem;
- source-language examples in the PVM32 realization module;
- comments presenting relation kinds as Pāṇinian concepts;
- active public documentation centered on Pāṇini or Sanskrit.

## Naming rule for new work

New modules should use ordinary systems/formal-methods terminology unless a non-standard term earns its place through a precise mathematical definition and a demonstrated advantage.

For example:

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

should be preferred over historical terminology.

## Pāṇinian material

Pāṇini may return to the active research line only if a controlled comparison demonstrates a concrete formal or proof-engineering advantage.

Until then, the project origin is documented at:

`docs/historical/PANINIAN_ORIGIN.md`

## Audit invariant

A future pull request should be questioned if it introduces new Sanskrit/Pāṇinian names into active semantic-continuity code without an accompanying technical justification.
