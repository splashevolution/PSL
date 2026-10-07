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

## Active formal milestone — RED-3

RED-1 established that two distinct target bindings for the same semantic script both pass the capability-plus-lowering gate.

GREEN-1 adds the minimum missing formal boundary: a generic \`DeviceModel(Resource)\` that independently states what each target resource denotes, plus an executable \`checkBinding\` relation. The PVM32 witness accepts the reference binding and rejects the RED-1 adversarial binding without putting a physical address into the target-neutral semantic script.

See \`docs/research/RED1_DISHONEST_BINDING.md\` and \`docs/research/GREEN1_DEVICE_BINDING_CHECK.md\`.

This closes only binding correctness relative to a stated device model. Representation, units, protocol state, persistence, failure handling, and physical-device conformance remain open.

RED-2 now freezes the GREEN-1-correct resource binding and mutates only the target payload. A machine-checked witness shows that both raw values pass the GREEN-1 binding checker because representation is outside its model.

See \`docs/research/RED2_REPRESENTATION_BLINDNESS.md\`.

This established the next narrow gap: **binding correctness is not representation correctness**.

GREEN-2 adds a generic target-specific \`RepresentationModel(SemanticValue, Raw)\` plus an executable representation checker. The target-neutral witness states 25 °C; the PVM32 model independently defines Celsius as fixed-point ×10, so raw 250 is derived at the target boundary rather than embedded in the semantic value.

The composed GREEN-2 gate accepts the reference candidate and rejects the RED-2 wrong-scale candidate while preserving the GREEN-1 resource check.

See \`docs/research/GREEN2_REPRESENTATION_CHECK.md\`.

RED-3 now freezes the GREEN-2-correct resource and raw payload and mutates only the surrounding protocol trace. A machine-checked witness shows that both executions pass GREEN-2 because protocol/state behavior is outside its model.

See \`docs/research/RED3_PROTOCOL_BLINDNESS.md\`.

This establishes the next narrow gap: **binding correctness plus representation correctness is not protocol/state correctness**.

Persistence, timing, and physical-device conformance remain open.

The motivating case is:

Example:

```text
contract: SetSetpoint(25.0 °C)

correct:
  configuration-mode
  encode 25.0 as 250
  correct resource
  ACK observed

incorrect:
  write 250 to the correct resource
  but omit required configuration/state transitions
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
