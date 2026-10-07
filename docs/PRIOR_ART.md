# Prior Art and Claim Boundaries

## Purpose

PSL must not repackage established ideas as novelty. This document records major adjacent research lines and the consequence each has for PSL's claims.

This is a working research map, not an exhaustive literature review.

## Major adjacent work

| Area | Representative work | What it already establishes | Consequence for PSL |
|---|---|---|---|
| Verified compilation | [CompCert](https://compcert.org/man/manual001.html) | Machine-checked semantic preservation from source semantics to assembly behavior; compilation may fail rather than produce code. | "Verified compilation" and "refusal" are not novel. |
| Multi-target verified compilation | [CakeML](https://cakeml.org/) | A proven-correct compiler pipeline targeting multiple machine architectures. | Multiple verified targets are not by themselves a contribution. |
| Proof-carrying code | G. Necula, [Proof-Carrying Code, POPL 1997](https://doi.org/10.1145/263699.263712) | An untrusted producer can provide code plus proof that a consumer checks against a safety policy. | "Untrusted producer + small checker + proof" is established. |
| Translation certification | Krijnen et al., [Translation certification for smart contracts](https://doi.org/10.1016/j.scico.2023.103051) | Translation relations and certificates can check compiler transformations without simply trusting the compiler. | Certificate-based checking of a transformation is not novel. |
| Platform-independent models | [OMG Model Driven Architecture](https://www.omg.org/mda/) | Stable platform-independent models can be mapped to platform-specific realizations as technology evolves. | "Keep intent independent of platform churn" is established motivation. |
| Extensible IR infrastructure | Lattner et al., [MLIR](https://arxiv.org/abs/2002.11054) | Reusable, extensible infrastructure across abstraction levels, application domains, targets, and execution environments. | Another portable/extensible IR is not enough. |
| Multilingual abstract/concrete syntax | [Grammatical Framework](https://www.grammaticalframework.org/doc/gf-refman.html) | One abstract syntax can have independent concrete syntaxes for different languages. | Multiple human-language surfaces are not a defensible novelty claim. |
| Modular metatheory | [Modular Metatheory for Extensible Languages](https://mmel.cs.umn.edu/) | Independently developed language extensions can carry modular proof obligations and compose metatheoretic results. | "Local proofs under extension" is established as a research goal; PSL needs a narrower result. |
| Legacy processor emulation | C. Fidge, [Verifying Emulation of Legacy Mission Computer Systems](https://doi.org/10.1007/978-3-540-45236-2_12) | Formal reasoning about preserving functional/timing behavior when legacy software is retained through emulation on replacement processors. | "Keep old software alive on new hardware" is not novel. |
| Verified device drivers | Zhao et al., [Verifying Device Drivers with Pancake](https://arxiv.org/abs/2501.08249) | Semantics-preserving compilation plus formal verification of a realistic Ethernet driver against device-interface properties. | A verified driver/device pair is not enough. |
| Certified abstraction layers | [DeepSpec / CertiKOS material](https://deepspec.org/event/dsss17/lecture_shao.html) | Compositional certified abstraction layers across low-level systems, kernels, and device-driver reasoning. | A small formal layer between software and hardware is not new by itself. |
| Proof-carrying hardware | Drzevitzky, Kastens, Platzner, [Proof-Carrying Hardware](https://doi.org/10.1155/2010/180242) | Hardware modules can carry proofs checked by a consumer before use. | "Hardware + proof + checker" is established. |
| Hardware-intent IR | Cheng et al., [HINT](https://arxiv.org/abs/2608.07625) | An executable hardware-intent IR can mediate between behavioral specifications and RTL generation. | PSL should not position itself merely as a hardware-intent IR. |

## What remains worth investigating

The surviving PSL research hypothesis is narrower:

> Can a stable semantic contract remain unchanged across materially different hardware/device generations while independent target realizations are checked for behavioral compatibility, incorrect or incapable realizations fail closed, and upstream semantic evidence remains reusable?

This exact combination is **not asserted here as novel**. It is a research hypothesis that must still survive deeper literature review and experimental falsification.

## Important distinctions

### Legacy emulation vs semantic continuity

Legacy emulation commonly preserves an old executable or old-machine behavior by placing an emulator between software and replacement hardware.

PSL's proposed experiment instead freezes the semantic contract and permits each generation to have a different realization:

```text
stable contract
   ├── realization A → legacy model
   ├── realization B → modern model
   └── realization C → refuse
```

The research question is how much semantic evidence survives that substitution and what must be proved locally.

### Protocol correctness vs realization correctness

A low-level request may be well-formed yet semantically wrong.

Examples include:

- correct protocol, wrong register;
- correct register, wrong scale;
- correct bytes, wrong unit;
- correct write, wrong privilege/state;
- correct command, invalid persistence/atomicity assumptions.

PSL's checker must reason about the semantic contract, not merely message syntax.

### Capability declaration vs behavioral proof

A declaration such as:

```text
supports(write) = true
```

is useful for early rejection but is insufficient evidence that the implementation performs the intended write.

The new work must make that distinction formal.

## Literature discipline

Before any PSL result is described as novel:

1. search the closest formal-methods, PL, embedded-systems, hardware-verification, and legacy-modernization literature;
2. state the closest prior result;
3. identify the theorem/property PSL adds;
4. define a falsification experiment;
5. downgrade the claim if the distinction is architectural packaging rather than new evidence.

The repository should prefer a smaller defensible claim over a larger familiar one.
