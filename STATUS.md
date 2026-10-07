# PSL — Current Status

**Date:** 2026-10-07  
**Research direction:** semantic continuity across implementation and hardware evolution

## Current position

PSL has completed a public repositioning away from a Pāṇinian/Sanskrit
language claim.

The active research question is now:

> Can a stable semantic contract survive materially different hardware
> generations while target realizations are independently checked,
> incompatible targets fail closed, and unrelated upstream proof evidence
> remains reusable?

This is a research hypothesis, not yet a proved contribution.

## Verified baseline retained

The repaired baseline currently provides:

- a pinned Lean 4 build in CI;
- an axiom-free validator-to-abstract-execution forward simulation for the
  repaired PVM32 control model;
- Python regression tests for the corresponding compiler contract;
- finite Python-to-Lean conformance over 65 accepted word streams and
  22 distinct ABI words;
- fixed adversarial ABI streams that Lean must reject;
- a separated semantic-identity / PVM32 binding checkpoint.

These results remain intentionally narrower than universal compiler or
hardware-correctness claims.

## Retired active direction

The following are no longer active research goals:

- Sanskrit programming syntax;
- English/Devanagari surface equivalence;
- Pāṇinian terminology as a novelty argument;
- expanding the historical PVM32 DSL as the main research product.

The explicit cross-surface witness has been removed from the active Lean
semantic kernel.

## Preserved compatibility baseline

The Python compiler, canonical `.pvm` examples, PVM32 ABI, and repaired Lean
semantics still contain historical names. They are frozen compatibility
vocabulary used to preserve verification lineage.

They should not be copied into new semantic-continuity modules.

See `docs/TERMINOLOGY_AUDIT.md`.

## Next formal milestone

The next research milestone should establish a RED case where the current
system cannot distinguish a declared capability from a semantically correct
realization.

Example:

```text
contract: SetSetpoint(25.0 °C)

correct:
  configuration-mode
  encode 25.0 as 250
  correct resource
  ACK observed

incorrect:
  write 25
  wrong resource
  wrong unit
  missing state transition
```

The new theory should reject incorrect realizations because of behavior, not
because they fail low-level syntax.

## Evaluation constraint

Core experiments must be reproducible without specialized physical hardware.

Lean plus deterministic device models, QEMU, Renode, or equivalent virtual
infrastructure are sufficient for the primary research phase.

## Historical status record

The previous long-form sprint/status document is preserved at:

`docs/historical/legacy-language-baseline-20261007/STATUS.md`

Its old PASS/proof wording is historical evidence only.
