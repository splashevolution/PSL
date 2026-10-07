# Evaluation Protocol

## Principle

PSL's primary experiments must be reproducible without specialized physical hardware.

The evaluation should combine machine-checked formal results with deterministic virtual execution and explicitly adversarial realizations.

## Experiment families

### E1 — Dishonest binding

Contract: one stateful semantic operation.

Target: frozen legacy-style device model.

Compare:

- correct binding;
- wrong address/resource;
- right address with wrong semantic behavior.

Expected result: only behaviorally correct realization is accepted.

### E2 — Representation attacks

Inject independently:

- wrong fixed-point scale;
- wrong unit;
- wrong signedness;
- wrong byte order;
- out-of-range value handling.

Expected result: semantically invalid realizations are rejected even when the protocol is syntactically valid.

### E3 — State/protocol attacks

Inject:

- missing configuration-mode transition;
- invalid operation ordering;
- ignored NACK/error;
- missing persistence step;
- non-atomic realization of an atomic contract.

Expected result: reject whenever the contract's observable requirements are not met.

### E4 — Hardware-generation substitution

Freeze one semantic contract.

Create materially different device models:

**Legacy A**

- narrow words;
- serial-style command protocol;
- fixed-point representation;
- explicit configuration mode.

**Modern B**

- different command/MMIO model;
- wider representation;
- different privilege or persistence semantics.

Expected result: both accepted through independent realizations without modifying the semantic contract.

### E5 — Incapable target

Create a target that lacks a required semantic capability, for example read-only state where persistent write is required.

Expected result: fail closed.

### E6 — Evolution locality

Replace A with B and record which artifacts change.

Required measurements:

- semantic-contract lines changed;
- semantic theorem/proof lines changed;
- upstream certificates invalidated;
- new device-model obligations;
- new realization obligations;
- checker changes;
- proof-check time;
- certificate size;
- percentage of prior evidence reused.

The project should not claim proof locality without publishing these measurements.

## Frozen virtual artifacts

Once a device generation is used as a published baseline, freeze it.

Suggested layout:

```text
experiments/
  devices/
    legacy-a-v1/
    modern-b-v1/
    incapable-c-v1/
  realizations/
    correct/
    adversarial/
  traces/
  manifests/
```

If a model is wrong, create a new version rather than silently rewriting the old artifact.

## Virtual hardware

QEMU, Renode, custom deterministic emulators, or equivalent tools may instantiate device models.

They are evaluation infrastructure, not the PSL contribution.

Where possible, experiments should run in CI with:

- fixed tool versions;
- deterministic seeds;
- captured traces;
- machine-readable expected results.

## Evidence reporting

Every experiment report should state separately:

### Formally proved

Theorems about the formal semantic/device models.

### Simulation validated

Observed virtual-device traces that match expected model behavior.

### Assumed

Properties taken from the device-model construction or external simulator.

### Not established

Physical-device conformance unless separately tested.

## Baseline comparison

At least one later evaluation should implement the same contract/device problem using a conventional transition-system/refinement approach.

PSL only earns a stronger research claim if it demonstrates a concrete advantage such as:

- smaller trusted base;
- stronger fail-closed guarantees;
- clearer/localized evolution obligations;
- greater proof reuse;
- simpler certificate checking.

If no advantage appears, that is a valid negative result.
