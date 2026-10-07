# PSL Realization Examples

These examples describe the **current semantic-continuity research problem**.
They are not source-language syntax examples.

## Example 1 — Correct legacy realization

Semantic contract:

```text
SetSetpoint(25.0 °C)
persistent = true
requires configuration mode
completion requires ACK
```

Legacy device model:

```text
resource: 0x20
representation: signed integer × 10
```

Candidate realization:

```text
enter-config
write 250 -> 0x20
observe ACK
exit-config
```

Expected result: **ACCEPT**, provided the realization evidence establishes the
required state transitions and observation.

## Example 2 — Wrong scale

Candidate:

```text
enter-config
write 25 -> 0x20
observe ACK
exit-config
```

The protocol request may be valid, but the resulting semantic value is
2.5 °C rather than 25.0 °C.

Expected result: **REJECT**.

## Example 3 — Wrong binding

Candidate:

```text
enter-config
write 250 -> 0x21
observe ACK
exit-config
```

A boolean `supports(write)` declaration cannot distinguish this from the
correct resource mapping.

Expected result: **REJECT unless the device model proves 0x21 has the required
behavior**.

## Example 4 — Different hardware generation

Modern device model:

```text
named parameter: setpoint
representation: float32 °C
no configuration-mode transition
persistent commit is implicit
```

A different realization may still satisfy the same semantic contract.

Expected result: **ACCEPT independently** without changing the contract.

## Example 5 — Incapable target

Device C can read temperature but cannot persistently modify a setpoint.

Expected result:

```text
NO LEGAL REALIZATION
```

The system must not silently claim compatibility.

## What these examples test

The central distinction is:

> protocol correctness is not realization correctness.

The formal work must define the observation/refinement relation that makes
those judgments mechanically meaningful.

The older C-vs-Sanskrit language examples are preserved at:

`docs/historical/legacy-language-baseline-20261007/comparative_examples.md`.
