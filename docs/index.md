---
layout: default
title: Paninian Systems Language
description: A proof-relevant semantic script for meaning that outlives syntax and hardware.
---

# Paninian Systems Language

## Meaning should outlive syntax. Software intent should outlive hardware.

PSL is a research project exploring whether one semantic derivation can survive changes in **human notation, compiler stacks, and hardware generations**.

The central idea is simple:

```text
surface expression
      ↓
semantic elaboration
      ↓
Paninian Semantic Script / Prakriyā
      ↓
Lean-checked legality
      ↓
capability-declaring driver
      ↓
target realization
```

A surface decides how meaning is expressed.

A driver decides how meaning is realized.

Neither should be allowed to silently change what the program means.

---

## This is not “Sanskrit programming”

Pāṇini matters to PSL because of the **structure of derivation**:

- **Sañjñā** — semantic identity
- **Kāraka** — relationships
- **Kriyā** — actions
- **Anuvṛtti** — controlled context inheritance
- **Adhikāra** — authority scope
- **Lopa** — consumption and context termination
- **Utsarga / Apavāda** — default and exception
- **Paribhāṣā** — rules about legal rule application
- **Sandhi** — lawful composition
- **Prakriyā** — the derivation itself

The experiment fails if these concepts amount to Sanskrit labels on conventional compiler machinery.

---

## One meaning, plural surfaces

The current semantic-kernel experiment contains a small formal witness:

```text
English:
    write status

Devanagari:
    स्थितिः लिखति ।
```

Both denote the same explicit semantic script.

The PVM32 driver then owns the target-specific binding:

```text
SemanticId(1001)
       ↓
PVM32 binding
       ↓
0x20
       ↓
0x200520F0
```

The semantic identity itself is neither the English word, the Devanagari word, nor the PVM address.

That witness is intentionally small. It does **not** prove universal natural-language understanding or universal portability.

---

## The larger aim

PSL is testing whether a semantic program can outlive the machine it was first realized on.

A future script should be able to meet different targets through independently written drivers:

```text
                  SemanticScript
                 /      |       \
                /       |        \
           modern CPU  GPU     legacy device
              driver  driver      driver
                │       │           │
             LLVM     MLIR      old protocol
                                    │
                                  QEMU
```

The legacy target should know nothing about PSL.

If a target cannot satisfy the requested semantics, PSL should refuse the realization rather than silently pretending compatibility.

---

## What is actually established

PSL has a repaired formal core under active verification. The current work distinguishes:

- compiler tests;
- finite Python-to-Lean conformance evidence;
- Lean theorems about the canonical abstract machine;
- historical QEMU execution evidence;
- still-open source-to-runtime and hardware-refinement boundaries.

The project deliberately does **not** equate one evidence type with another.

Current development lines:

- [Verification repair](https://github.com/splashevolution/paninian-systems-language/tree/repair/verification-contract)
- [Semantic script kernel](https://github.com/splashevolution/paninian-systems-language/tree/feature/semantic-script-kernel)
- [Verification ledger](https://github.com/splashevolution/paninian-systems-language/blob/repair/verification-contract/docs/VERIFICATION_STATUS.md)
- [Known semantic gaps](https://github.com/splashevolution/paninian-systems-language/blob/repair/verification-contract/docs/SEMANTIC_GAPS.md)
- [Semantic architecture](https://github.com/splashevolution/paninian-systems-language/blob/feature/semantic-script-kernel/docs/SEMANTIC_ARCHITECTURE.md)

---

## The novelty hypothesis

PSL does not claim to have invented:

- portable IRs;
- multiple program projections;
- heterogeneous backends;
- verified compilers;
- proof-carrying code;
- stable semantic identifiers.

The research hypothesis is the **combined trust boundary**:

> Can plural surfaces independently elaborate into one proof-relevant semantic derivation, while independently developed drivers realize that derivation under machine-checkable capability and preservation obligations?

That claim still has to earn its evidence.

---

## Kill criteria

The universal-script idea should be narrowed or abandoned if:

- independent frontends cannot converge without sharing hidden target assumptions;
- a genuinely different second driver forces hardware detail into the semantic kernel;
- an incapable or dishonest driver cannot be rejected;
- legacy and modern targets cannot share one semantic program;
- proof obligations grow globally instead of locally;
- the practical cost exceeds the value compared with conventional systems tooling.

Failure is a valid research result.

---

## North star

> **Describe what computation means.  
> Let surfaces choose how humans express it.  
> Let drivers choose how machines realize it.  
> Refuse what cannot be derived.  
> Keep every proof boundary visible.**

**Meaning is invariant. Prakriyā evolves. Hardware supplies capabilities. Paribhāṣā decides legality. Lean establishes trust.**

[Read the full README](../README.md)
