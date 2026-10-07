# Threat Model

## Goal

The realization boundary must remain correct even when target-specific code is mistaken, incomplete, stale, or actively dishonest.

PSL therefore treats a realization/driver as **untrusted unless its evidence checks**.

## Assets

The properties to protect are:

- semantic meaning of an accepted contract;
- correctness of the binding between semantic identity and target behavior;
- preservation of stated units/domains;
- required state/authority transitions;
- observable postconditions;
- explicit refusal when a target cannot satisfy the contract.

## Adversary / fault model

The initial threat model includes a realization that may:

- claim a capability it does not faithfully implement;
- bind a semantic identity to the wrong register/address/resource;
- apply an incorrect scale factor;
- use the wrong unit;
- encode bytes in the wrong order;
- omit a required mode/authority transition;
- violate operation ordering;
- ignore an acknowledgement or error;
- implement volatile behavior when persistence is required;
- split an operation that the contract requires to be atomic;
- silently emulate or degrade an unavailable capability.

The model includes both malicious and accidental causes. The checker should not depend on intent.

## Trusted computing base

The research goal is to minimize trust to:

- the formal semantics of the semantic contract;
- the formal device model;
- the realization checker / proof kernel;
- the proof assistant kernel and explicitly listed axioms/assumptions.

The realization generator itself should not need to be trusted.

Virtual-device implementations used for experiments are **not automatically part of the formal TCB** unless linked by a separate proof. They provide execution evidence.

## Dishonest-binding attack

Example:

```text
semantic identity: status/setpoint
correct resource:  register 0x20
driver binding:    register 0x21
capability flag:   write = true
```

A boolean capability check accepts the declaration.

The new realization evidence must reject it unless the formal device model proves that 0x21 satisfies the same semantic behavior.

## Wrong-representation attack

Example:

```text
contract:       SetSetpoint(25.0 °C)
device encoding: value = °C × 10
driver writes:  25
```

The protocol may accept the write. The semantic result is 2.5 °C.

The realization should be rejected.

## Incapable target

A read-only target must not be accepted for a persistent setpoint-write contract.

The correct result is:

```text
NO LEGAL REALIZATION
```

not hidden software emulation unless the semantic contract explicitly permits such an implementation and its observable behavior satisfies the same requirements.

## Out of scope initially

The first theory does not attempt to prove:

- electromagnetic or analog properties;
- physical sensor calibration;
- arbitrary hardware timing closure;
- absence of hardware manufacturing defects;
- correctness of QEMU/Renode themselves;
- equivalence between a virtual model and an arbitrary physical device;
- security against a compromised proof-assistant kernel.

Those can become separate research layers only if required.
