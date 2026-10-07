# PSL

> **Software intent should outlive hardware.**

PSL is an open research project investigating **semantic continuity across changing implementations and hardware generations**.

The central question is deliberately narrow:

> Can a stable semantic contract be realized by materially different systems with machine-checkable evidence, while incorrect or incapable realizations fail closed and unrelated upstream proofs remain reusable?

PSL is not claiming that portable IRs, verified compilers, proof-carrying code, hardware abstraction, multilingual syntax, or legacy-system emulation are new. Those areas have substantial prior art. The research task is to determine whether a useful, formally checkable continuity boundary can be built across hardware evolution without hiding incompatible behavior behind an adapter.

**Research site:** https://splashevolution.github.io/PSL/  
**Status:** open research prototype  
**Formal baseline:** Lean 4 verification + PVM32 realization experiment

## Research direction

The project is moving from a language-surface experiment toward a formal model of semantic continuity:

```text
                 semantic contract
                        │
                 checked meaning
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
       realization A          realization B
        + evidence             + evidence
             │                     │
          checker                 checker
             │                     │
          ACCEPT                  ACCEPT
             │                     │
       device model A         device model B

                 incompatible target
                         │
                         ▼
                       REFUSE
```

A target must not be accepted merely because a driver says it supports an operation. The realization must justify that its **observable behavior** satisfies the semantic contract.

## Three research hypotheses

### 1. Semantic Continuity Hypothesis

A target-neutral semantic contract can remain unchanged across materially different hardware generations while each target-specific realization is checked independently.

### 2. Realization Soundness Hypothesis

A realization that uses the wrong binding, scale, unit, byte order, state transition, privilege mode, or other semantically relevant behavior can be rejected even when its low-level protocol messages are syntactically valid.

### 3. Proof-Reuse Hypothesis

Replacing one hardware realization with another should not require unrelated semantic obligations to be reproved when the semantic contract and observation model are unchanged. New proof obligations should be localized to the changed realization boundary.

These are **research hypotheses, not established claims**.

## First falsification target

The existing capability model is intentionally too weak for the new research direction:

```text
supports(write) = true
```

does not prove that a write realizes the intended meaning.

The first serious experiment should distinguish:

```text
semantic intent:  SetSetpoint(25.0 °C)

correct legacy realization:
  enter configuration mode
  write 250 to the correct register
  receive acknowledgement
  exit configuration mode

dishonest / defective realizations:
  wrong register
  wrong ×10 scaling
  wrong unit
  wrong endianness
  missing configuration transition
  missing acknowledgement
```

A protocol can accept all of those byte sequences. PSL should accept only realizations whose behavior refines the semantic contract.

## Virtual hardware is the primary laboratory

The core research must be reproducible **without proprietary or specialized physical hardware**.

Primary evidence will come from:

- Lean proofs over explicit semantic and device models;
- deterministic software device models;
- QEMU, Renode, or equivalent virtual hardware where useful;
- adversarial realizations and frozen execution traces;
- CI-reproducible experiments.

Physical hardware may later provide additional empirical validation, but it is not required for the core formal claims.

The boundary must remain explicit:

- **formally proved:** properties of the stated mathematical models;
- **simulation-validated:** behavior of virtual devices against those models;
- **not automatically proved:** conformance of an arbitrary physical device to the model.

## Current verified baseline

The current codebase contains two important historical layers.

### Repaired PVM32 semantics

The repaired formal line establishes a canonical model for live written state, context inheritance, authority scope, lifecycle consumption, and selected privileged operations. Lean proves forward-simulation properties for the abstract model.

The finite Python-to-Lean bridge currently checks **65 accepted word streams** containing **22 distinct ABI words**. This is finite conformance evidence, not universal source-to-hardware correctness.

### Semantic-script experiment

`lean/PSL/SemanticKernel.lean` and `lean/PSL/PVM32Driver.lean` established an initial separation between semantic identity and a PVM32 target binding.

That experiment is retained as a useful implementation checkpoint. Its English/Devanagari witness is **not the current research contribution** and does not establish independent source-language elaboration.

The next formal work should strengthen the realization boundary rather than expand the multilingual-surface experiment.

## What PSL is not

PSL is not intended to become:

- an operating system;
- a virtual-machine or emulator project;
- a QEMU or Renode replacement;
- a Sanskrit programming language;
- a multilingual parsing research project;
- another generic compiler infrastructure;
- a protocol gateway such as an OPC-UA/Modbus bridge;
- a claim that boolean capability declarations prove hardware correctness.

Virtual hardware and emulation are **experimental infrastructure**. They are not the identity of the project.

## Research discipline

Every result should distinguish:

1. what is mathematically proved;
2. what is established by finite tests;
3. what is observed in simulation;
4. what remains an assumption;
5. what is not yet connected to physical hardware.

The project should become smaller if evidence does not support a claim.

## Research documents

- [Research charter](docs/RESEARCH_CHARTER.md)
- [Prior art](docs/PRIOR_ART.md)
- [Novelty contract](docs/NOVELTY_CONTRACT.md)
- [Semantic continuity model](docs/SEMANTIC_CONTINUITY.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Evaluation protocol](docs/EVALUATION_PROTOCOL.md)
- [Current semantic architecture](docs/SEMANTIC_ARCHITECTURE.md)
- [Terminology audit](docs/TERMINOLOGY_AUDIT.md)
- [Historical Pāṇinian origin](docs/historical/PANINIAN_ORIGIN.md)

## Running the current formal baseline

```bash
python -m unittest -v tests/test_semantic_contract.py

cd lean
lake build
lake env lean Audit.lean
```

The repository pins the formal toolchain used by CI. Treat CI and the verification ledger as authoritative for the current checked state.

## North star

> **Preserve meaning across implementation change.  
> Require evidence for realization.  
> Refuse incompatible targets.  
> Keep proof boundaries visible.  
> Measure what survives evolution.**

The working ambition is simple to state and difficult to earn:

> **Software intent should outlive hardware.**
