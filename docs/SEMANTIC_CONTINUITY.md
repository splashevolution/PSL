# Semantic Continuity: Research Model

## Goal

Define precisely what it would mean for **software intent to outlive hardware**.

The phrase is motivation, not a theorem. The purpose of this document is to turn it into falsifiable formal obligations.

## Core objects

Let:

- (C) be a semantic contract;
- (D) be a device model;
- (R) be a target-specific realization;
- (pi) be realization evidence;
- (Obs) be the observation function or relation exposed at the semantic boundary.

The contract denotes a set of allowed observable behaviors:

```text
⟦C⟧ = allowed observable traces / outcomes
```

A realization maps semantic operations to device interactions.

A checker should establish a statement of the shape:

```text
Check(C, D, R, π) = true
        ⇒
Obs(Execute(D, R(C))) satisfies ⟦C⟧
```

The exact direction may become refinement, trace inclusion, simulation, or another relation once nondeterminism and failure behavior are specified.

## Why observable behavior

Different device generations may legitimately differ in:

- instruction sequences;
- register layout;
- packet format;
- timing below an allowed bound;
- internal state representation;
- word width;
- implementation language;
- memory layout.

Semantic continuity should therefore be stated over **observable behavior**, not binary identity or identical internal states.

This follows the same broad discipline used by verified compiler work such as CompCert, while applying it to a different proposed boundary.

## Minimum contract vocabulary

The first contract language should remain small.

Candidate fields include:

- operation identity;
- input domain and units;
- preconditions;
- postconditions;
- observable effects;
- allowed failures;
- authority / mode requirements;
- atomicity requirements;
- persistence requirements;
- optional timing constraints.

Not every field belongs in version 1. The goal is the minimum model needed to distinguish a correct realization from realistic semantically wrong ones.

## First example

Semantic contract:

```text
SetSetpoint(25.0 °C)
```

Legacy device model:

```text
representation: signed 16-bit integer
scale:          0.1 °C
target:         register 0x20
precondition:   configuration mode
completion:     ACK
persistence:    required
```

A correct realization might be:

```text
enter-config
write 250 -> 0x20
observe ACK
exit-config
```

Semantically wrong realizations include:

```text
write 25 -> 0x20        # wrong scale
write 250 -> 0x21       # wrong binding
write Fahrenheit value  # wrong unit
write without config    # wrong state transition
ignore NACK             # wrong completion semantics
```

A protocol implementation may consider several of these requests syntactically legal. A semantic-continuity checker should not.

## Hardware-generation substitution

The first continuity experiment should use one frozen contract and at least three target models.

```text
                         same contract
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          Legacy A        Modern B       Incapable C
          ACCEPT          ACCEPT           REFUSE
```

A and B should differ materially, not merely by register number.

Possible differences:

- serial command protocol vs MMIO-like interface;
- fixed-point vs floating-point representation;
- explicit configuration mode vs direct operation;
- different privilege model;
- different persistence mechanism.

## Proof-reuse hypothesis

Let (E_C) be upstream evidence about contract (C).

When target (D_1) is replaced with (D_2), the desired result is:

```text
C unchanged
E_C unchanged
new D2 model required
new R2 required
new realization evidence π2 required
```

A stronger theory should characterize exactly which upstream artifacts remain valid and why.

This must be measured, not asserted.

## Device-model boundary

Formal verification can prove a theorem about (D). It does not automatically prove that a physical device conforms to (D).

The initial research therefore uses deterministic virtual device models.

Later physical testing, if performed, creates a separate obligation:

```text
physical device  ≈  formal DeviceModel
```

That relationship is empirical unless stronger implementation evidence is available.

## Open theorem targets

The exact Lean statements remain to be designed, but the research should converge toward properties resembling:

**Checker soundness**

If the checker accepts realization evidence, the realized device behavior refines the contract.

**Fail-closed incapability**

If a target cannot satisfy a required observable property, no valid realization certificate exists under the stated model.

**Hardware substitution**

Two different accepted realizations can satisfy the same semantic contract.

**Evolution locality**

Replacing a target realization preserves all upstream obligations that depend only on the unchanged contract and observation model.

## Current gap

The existing PSL `DriverContract.supports : Capability → Bool` is only a capability declaration.

It does not prove that:

- a semantic identity is bound to the correct target resource;
- scaling/units are correct;
- required device-state transitions occur;
- observable postconditions hold.

That gap is the intended starting point of the new research.
