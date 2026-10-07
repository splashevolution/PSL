# Paninian Systems Language (PSL)

> **Meaning should outlive syntax. Software intent should outlive hardware.**

PSL is a research project exploring a **proof-relevant semantic script**: a program model in which human or machine-facing surfaces elaborate into a language-neutral semantic derivation, and target drivers independently realize that meaning under explicit capability constraints.

Pāṇini is important here for the architecture of derivation — naming, relations, contextual inheritance, authority, exceptions, composition, and rule applicability — **not because Sanskrit syntax is inherently superior to English syntax**.

PSL is not trying to replace C, Rust, Go, LLVM, MLIR, Lean, or natural language. The research question is whether a small semantic layer can preserve meaning across changing notation, software stacks, and hardware generations.

**Research site:** [modern PSL architecture and evidence map](https://splashevolution.github.io/paninian-systems-language/) · **Status:** open research prototype · **Current focus:** repaired verification line + semantic-script kernel

## The Aim

Today, source code usually binds together several concerns too early:

- human vocabulary and syntax;
- semantic intent;
- memory and privilege assumptions;
- compiler IR;
- target architecture;
- device-specific realization.

PSL is testing a different separation:

```text
          human / AI / graphical surfaces
            English · Devanagari · future UI
                       │
                       ▼
              semantic elaboration
                       │
                       ▼
             PANINIAN SEMANTIC SCRIPT
                       │
         identity · relations · actions
       context · authority · lifecycle
             rules · derivation
                       │
                       ▼
                    Lean
             legality / proof boundary
                       │
                       ▼
              verified semantic intent
                       │
           capability-declaring drivers
              ┌────────┼────────┐
              ▼        ▼        ▼
            PVM32     CPU      future
             RV32   LLVM/MLIR  FPGA/GPU/
                               legacy I/O
```

The surface may choose **how meaning is expressed to a human**.

The driver may choose **how meaning is realized on a machine**.

Neither is allowed to silently change **what the program means**.

## Why Pāṇini?

PSL treats selected Pāṇinian ideas as candidates for a computational derivation system rather than decorative terminology.

| Pāṇinian concept | PSL research interpretation |
|---|---|
| **Sañjñā** | stable semantic identity, independent of spelling or hardware address |
| **Kāraka** | semantic relationship: source, destination, instrument, context |
| **Kriyā** | action / transformation |
| **Anuvṛtti** | controlled propagation of live context |
| **Adhikāra** | scoped authority governing subsequent derivations |
| **Lopa** | semantic consumption and context termination |
| **Utsarga / Apavāda** | default rule and specialized exception |
| **Paribhāṣā** | meta-rules governing legal derivation |
| **Sandhi** | legal composition under preserved invariants |
| **Prakriyā** | inspectable derivation by which a program acquires meaning |

Some of these concepts are implemented in the current prototype; others remain research obligations. A Sanskrit name alone is never considered a contribution.

## The Stronger Research Hypothesis

PSL is **not** claiming novelty for any of these individually:

- multiple textual or graphical views of one program;
- portable intermediate representations;
- heterogeneous compiler backends;
- verified compilation;
- proof-carrying code;
- stable semantic identifiers.

Those areas already have substantial prior art.

The hypothesis worth testing is narrower:

> **Can one proof-relevant semantic derivation be independently elaborated from plural surfaces and independently realized by capability-declaring drivers, with machine-checkable evidence at both boundaries?**

If the answer is no, PSL should narrow or abandon that claim.

## What Exists Today

PSL began as a small Pāṇinian-inspired embedded language and PVM32/RV32 experiment. That work is now being treated as **Driver 0**, not as the final definition of PSL.

The current verified repair line establishes a canonical control model for:

- live written state;
- Anuvṛtti context;
- Adhikāra scope;
- privileged Store and Asiddha Lopa;
- Lopa as both lifecycle consumption and an inheritance boundary.

Lean proves a forward simulation from successful canonical validation to successful execution in the abstract machine. The current finite bridge also checks Python compiler output against Lean for **65 accepted word streams** and **22 distinct ABI words**.

The semantic-script experiment adds a layer above that model:

```text
English:      write status
Devanagari:   स्थितिः लिखति ।
                    │
                    ▼
             same SemanticScript
                    │
               PVM32 binding
                    │
                    ▼
              0x200520F0
```

The important separation is:

```text
SemanticId(1001)  ≠  "status"  ≠  स्थितिः  ≠  PVM address 0x20
```

Only the PVM32 driver owns the `SemanticId(1001) -> 0x20` realization binding.

### Active research lines

- **Verification repair:** [`repair/verification-contract`](https://github.com/splashevolution/paninian-systems-language/tree/repair/verification-contract)
- **Semantic script kernel:** [`feature/semantic-script-kernel`](https://github.com/splashevolution/paninian-systems-language/tree/feature/semantic-script-kernel)
- **Verification ledger:** [`docs/VERIFICATION_STATUS.md`](https://github.com/splashevolution/paninian-systems-language/blob/repair/verification-contract/docs/VERIFICATION_STATUS.md)
- **Known semantic gaps:** [`docs/SEMANTIC_GAPS.md`](https://github.com/splashevolution/paninian-systems-language/blob/repair/verification-contract/docs/SEMANTIC_GAPS.md)
- **Semantic architecture:** [`docs/SEMANTIC_ARCHITECTURE.md`](https://github.com/splashevolution/paninian-systems-language/blob/feature/semantic-script-kernel/docs/SEMANTIC_ARCHITECTURE.md)

## What PSL Does **Not** Claim

The project does **not** currently establish:

- universal natural-language understanding;
- universal source-to-hardware correctness;
- complete Python-source-to-Lean compiler correctness;
- GPU or FPGA portability;
- Lean-to-RV32 refinement for the canonical runtime;
- equivalence between QEMU and physical silicon;
- general performance superiority over C, Rust, Go, LLVM, or MLIR;
- that Pāṇinian structure is automatically better than conventional type or capability systems.

Historical repository material predating the verification repair may contain stronger language. Treat the current verification ledger and Lean model as authoritative for proof claims.

## The Legacy-Hardware Test

One practical direction is intentionally unfashionable: **can software intent outlive the machine it was written for?**

The planned experiment is to freeze an emulated legacy device behind a primitive protocol and require the same semantic script to run against both a modern realization and that old machine through independent drivers.

```text
                  same SemanticScript
                    /          \
                   /            \
            modern driver    legacy driver
                 │                │
            modern target     old protocol
                                  │
                              QEMU device
```

The legacy machine should know nothing about PSL.

If the target cannot satisfy the semantic contract, PSL must refuse the realization rather than silently invent compatibility.

## Kill Criteria

The universal-script hypothesis survives only if we can demonstrate all of the following without contaminating the semantic kernel with target-specific assumptions:

1. two genuinely independent surfaces elaborate to equivalent semantic derivations;
2. a second, fundamentally different driver realizes the same script;
3. an incapable or dishonest driver is rejected;
4. a legacy QEMU target and a modern target can share one semantic program;
5. adding a new driver does not force hardware details into `SemanticScript`;
6. proof obligations scale locally rather than requiring every driver to be rewritten.

Failure is a useful research result. PSL should become smaller rather than preserve an attractive claim that the evidence cannot support.

## Verification Philosophy

PSL separates evidence types deliberately.

A passing QEMU run is executable evidence.

A passing compiler regression test is test evidence.

A Lean theorem is a theorem about the model it states.

None of those automatically proves the others.

The intended long-term chain is:

```text
surface expression
      ↓  elaboration evidence
SemanticScript / Prakriyā
      ↓  semantic legality
Lean-checked meaning
      ↓  realization evidence
target driver
      ↓
machine / device
```

Every unproved arrow remains visible.

## Running the Current Verified Line

For the repaired formal core:

```bash
git checkout repair/verification-contract

python -m unittest -v tests/test_semantic_contract.py

cd lean
lake build
lake env lean Audit.lean
```

For the semantic-script experiment:

```bash
git checkout feature/semantic-script-kernel

cd lean
lake build
lake env lean Audit.lean
```

## Repository Map

- `src/utils/paninian_compiler.py` — current Python compiler / PVM32 realization path
- `lean/PSL/Semantics.lean` — repaired canonical abstract/control semantics
- `lean/PSL/SemanticKernel.lean` — surface-neutral semantic kernel on the feature branch
- `lean/PSL/PVM32Driver.lean` — first semantic-to-target driver experiment
- `programs/` — active and historical PSL examples
- `src/rv32/` — historical RV32/QEMU execution experiments
- `docs/` — verification, semantic-gap, architecture, and case-study material
- `paper/` — research manuscript; historical claims must be reconciled with the current ledger
- `evidence/` — captured execution artifacts

## North Star

> **Describe what computation means.  
> Let surfaces choose how humans express it.  
> Let drivers choose how machines realize it.  
> Make legality explicit.  
> Refuse what cannot be derived.  
> Keep every proof boundary visible.**

**Meaning is invariant. Prakriyā evolves. Hardware supplies capabilities. Paribhāṣā decides legality. Lean establishes trust.**

---

PSL is an open research prototype. The goal is not to make Sanskrit-shaped code look novel; it is to discover whether a derivational semantic system can let software meaning survive changes in notation, tooling, and hardware — and to kill that hypothesis if the evidence says it cannot.
