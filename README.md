# Paninian Systems Language (PSL)

**PSL is a research prototype for applying Pāṇinian structural concepts to a small systems language and embedded-firmware execution model.** It explores whether selected invalid states can be rejected structurally before execution and whether those compiler rules can be connected to an executable formal machine.

The repository contains a compiler, historical RV32/QEMU firmware experiments, differential tests, and a Lean 4 formal model. These layers provide different kinds of evidence and are deliberately kept separate.

## Research Question

Can concepts inspired by Pāṇini's *Aṣṭādhyāyī* be expressed as useful compiler and machine invariants for embedded systems?

Claims that PSL is generally leaner, faster, safer, or more deterministic than conventional systems remain **research hypotheses** until they are supported by controlled comparisons and stronger refinement proofs.

## Current Verification Status

The current repaired formal core is typechecked in CI with pinned **Lean 4.34.1**.

What is currently established:

- the canonical PSL control state explicitly tracks live written targets, Anuvṛtti context, and Adhikāra scope depth;
- **Lopa is a hard inheritance boundary**: successful Lopa consumes live-written state and clears inherited target context;
- Ring-2 WRITE to an Asiddha address remains legal in the canonical control contract;
- Store requires Adhikāra and Ring 0;
- Asiddha Lopa requires Adhikāra and Ring 0;
- malformed scope close, inherited instruction without live context, and Lopa of non-live state are rejected by the canonical validator;
- Lean proves an **axiom-free forward simulation** from successful control validation to successful execution in the PSL abstract machine:
  - `validateWords_execution`
  - `validated_ir_executes`
  - `valid_program_executes`
- Python semantic-contract tests exercise the corresponding compiler boundary cases.

The retired project axiom `p2_runtime_correctness` is no longer part of the repaired formal model. CI audits the principal theorems for `sorryAx` and for reintroduction of that project axiom.

What is **not** yet established:

- Python source compiler → Lean `ValidProgram` correspondence;
- complete Āvṛtti execution semantics;
- complete Utsarga/Apavāda conditional semantics;
- a formal Sandhi atomicity model;
- Lean abstract-machine → canonical RV32 firmware refinement;
- QEMU → physical RISC-V hardware equivalence;
- a CompCert-equivalent end-to-end compiler-correctness theorem.

See [`docs/VERIFICATION_STATUS.md`](docs/VERIFICATION_STATUS.md) for the claim ledger and [`docs/SEMANTIC_GAPS.md`](docs/SEMANTIC_GAPS.md) for repaired and still-open semantic conflicts.

> A passing QEMU test is executable evidence, not a mathematical proof. A Lean theorem about PSL's abstract machine is not automatically a theorem about RV32 firmware or physical hardware.

## Canonical Semantic Decisions

The repair work freezes three decisions before further feature development:

1. **Ring is an instruction attribute**, not a mutable global privilege register in the formal machine.
2. **Lopa ends inheritance context.** An Anuvṛtti immediately after Lopa is structurally invalid unless a new explicit target establishes context.
3. **Ring-2 WRITE may address Asiddha.** Visibility and storage behavior belong to the memory/refinement model; WRITE is not rejected solely because the address is Asiddha.

Historical sprint artifacts that contradict these rules are retained as historical evidence, not treated as the current canonical semantics.

## Core Ideas

PSL maps selected Pāṇinian concepts to machine/compiler abstractions:

- **Kārakas** — data-flow roles such as source, destination, instrument, and context
- **Anuvṛtti** — explicit context inheritance
- **Āvṛtti** — structurally encoded bounded repetition
- **Lopa** — structured erasure and context boundary
- **Vṛddhi** — privileged role encoding
- **Siddha / Asiddha** — visible/shadow address partition in the PSL model
- **Adhikāra** — lexical privilege scope
- **Paribhāṣā** — compiler legality predicates
- **Sandhi** — declared instruction-pair fusion; formal atomicity is still open

Similar concepts exist in conventional compiler, type-system, capability, privilege, and state-machine designs. PSL's contribution must therefore be demonstrated by the exact structural rules, formal results, and empirical comparisons—not by terminology alone.

## Bytecode / ABI

Every operation lowers to a fixed **32-bit, big-endian** instruction word:

```
31-28   27-24    23-16      15-08      07-00
RING_ID | COMP | OPCODE | TARGET | FLAGS/COND
```

The fixed layout is intended to keep decoding predictable and inspectable.

## Repository Layout

- `src/utils/paninian_compiler.py` — canonical Python compiler implementation under repair
- `lean/PSL/Semantics.lean` — current Lean abstract/control semantics
- `lean/Audit.lean` — principal-theorem dependency audit
- `tests/test_semantic_contract.py` — compiler semantic-contract regression tests
- `programs/` — PSL example programs; some are historical and may predate the repaired contract
- `src/rv32/` — historical freestanding RV32/QEMU firmware experiments
- `paper/` — historical research manuscript; claims must be reconciled with the current ledger
- `evidence/` — captured sprint execution artifacts
- `docs/VERIFICATION_STATUS.md` — authoritative claim ledger
- `docs/SEMANTIC_GAPS.md` — semantic conflicts and their repair decisions
- `STATUS.md` — sprint history plus current repair status

## Running the Current Checks

```bash
# Compiler semantic contract
python -m unittest -v tests/test_semantic_contract.py

# Lean formal core
cd lean
lake build

# Principal theorem dependency audit
lake env lean Audit.lean
```

Historical QEMU/RV32 scripts remain useful execution evidence, but they are not all canonical refinement targets because firmware behavior evolved between sprints.

## Project Scope

PSL remains a **research prototype**. The repaired branch has a real, CI-backed, axiom-free theorem connecting its canonical control validator to its abstract execution model. The next major verification boundary is connecting the Python compiler to that Lean model, followed by a single canonical RV32 runtime refinement.

compiler · firmware · dsl · embedded-systems · formal-methods · sanskrit · risc-v · panini · lean4
