# PSL Property-Based Generator — Compatibility Baseline

## Status

The deterministic property-based generator is retained as regression evidence
for the repaired legacy PVM32 compiler.

It is **not** the specification of the new semantic-continuity research model.

## Current purpose

The generator continues to provide:

- deterministic source generation from a fixed seed;
- broad exercise of the legacy compiler's accepted control subset;
- differential comparison against expected compiler/runtime invariants;
- additional inputs for the finite Python-to-Lean conformance bridge.

The current CI also runs a fixed 1,000-case differential falsification pass
with seed 42.

## Claim boundary

Passing generated cases shows behavior over the generated corpus.

It does not establish:

- universal compiler correctness;
- correctness of arbitrary device bindings;
- semantic continuity across hardware generations;
- physical-hardware conformance.

## Terminology

The generator and its source language contain historical compatibility tokens.
Those tokens are frozen test inputs and should not be used as vocabulary in
new semantic-continuity code.

The detailed previous generator specification is preserved at:

`docs/historical/legacy-language-baseline-20261007/property_based_generator_spec.md`.

## Future evaluation

New property-based work should target realization evidence rather than source
syntax. Useful generated mutations include:

- wrong resource binding;
- wrong scale;
- wrong unit;
- wrong byte order;
- missing state transition;
- invalid ordering;
- missing persistence;
- false capability declaration.

See `docs/EVALUATION_PROTOCOL.md`.
