# Paninian Systems Language (PSL)

**PSL is a research prototype for applying Paninian structural concepts to a small systems language and embedded-firmware execution model.** The project explores whether compile-time structural rules can make selected classes of invalid programs unrepresentable or reject them before execution.

The repository contains a compiler, a freestanding RV32/QEMU firmware pipeline, differential tests, and a Lean 4 abstract semantics. These layers provide different kinds of evidence and are intentionally distinguished below.

## Research Question

PSL investigates whether concepts inspired by Pāṇini's *Aṣṭādhyāyī* can be expressed as useful compiler and machine invariants for embedded systems.

The stronger claims — that this approach is generally leaner, faster, safer, or more deterministic than conventional systems techniques — remain **research hypotheses** and require controlled comparative evidence.

## Verification Status

- **15 historical development sprints**
- **RV32/QEMU execution evidence:** self-asserting firmware pipelines and captured UART/MMIO behaviour
- **Differential testing:** historical run reported 5000/5000 generated cases passing
- **Lean 4:** formal source exists, but the repair branch's first real `lake build` currently exposes type errors; no current revision-wide proof claim is made
- **Principal soundness theorem:** withdrawn during repair; the earlier argument was axiom-dependent and did not typecheck under the new CI gate
- **Physical RISC-V silicon:** not yet established
- **Source-to-RV32 semantic refinement:** not yet proved

The authoritative claim ledger is [`docs/VERIFICATION_STATUS.md`](docs/VERIFICATION_STATUS.md). Active semantic contradictions are tracked in [`docs/SEMANTIC_GAPS.md`](docs/SEMANTIC_GAPS.md).

> **Important:** a passing QEMU test is executable evidence, not a mathematical proof. A Lean theorem about PSL's abstract machine is not automatically a theorem about the RV32 implementation or physical hardware.

## Core Ideas

PSL maps selected Paninian grammatical concepts to machine semantics:

- **Kārakas (data-flow relations)** — source (*apādāna*), destination (*karman*), instrument (*karaṇa*), and context (*adhikaraṇa*) map to registers, memory, buses, and execution context
- **Anuvṛtti (context inheritance)** — omitted operands inherit context from a preceding instruction
- **Āvṛtti (bounded repetition)** — a repetition count is encoded structurally in the instruction word
- **Lopa (structured erasure)** — explicit nullification with boundary effects
- **Vṛddhi (privilege role)** — maps selected operations into the privileged model
- **Siddha / Asiddha visibility** — a deterministic visible/shadow state partition in the PSL model
- **Adhikāra (scope)** — an explicit lexical domain for privileged operations
- **Paribhāṣā (legality rules)** — compiler predicates that reject specified invalid structures

These are PSL abstractions. Similar concepts exist in conventional compiler, type-system, capability, privilege, and state-machine designs; PSL's research question is whether this particular structural formulation is useful.

## Bytecode / ABI

Every operation compiles to a fixed **32-bit, big-endian** instruction word:

```
31-28   27-24    23-16      15-08      07-00
RING_ID | COMP | OPCODE | TARGET | FLAGS/COND
```

The fixed layout is intended to keep decoding predictable and inspectable.

## Repository Layout

- `src/` — PSL compiler and RV32 firmware sources
- `lean/` — Lean 4 abstract semantics and machine-checked results
- `programs/` — `.pvm` example programs
- `paper/` — accompanying research manuscript
- `docs/` — specification and verification status
- `evidence/` — per-sprint execution artifacts and captured UART traces
- `run_rv32_*_pipeline.py` — build/execute/verify pipelines under QEMU
- `run_verified_compilation_proof.py` — executable verification harness; despite the historical filename, not all checks are mathematical proofs
- `run_differential_tests.py` — generated differential-test driver
- `SPEC.md`, `STATUS.md`, `formal_semantics.md` — deeper technical documentation

## Evidence Model

PSL uses four distinct evidence classes:

1. **Lean proofs** — propositions checked by the Lean kernel.
2. **Axiom-dependent Lean results** — checked conditional on explicit project assumptions.
3. **Executable tests** — Python, compiler, firmware, and QEMU observations.
4. **Research hypotheses** — claims requiring further proof or comparative experimentation.

These categories must not be conflated. See `docs/VERIFICATION_STATUS.md` for the current claim-by-claim classification.

## Current Formal Blocker

The principal formal gap is the relation between compile-time P2 tracking and the runtime `MachineState.written` state. The current Lean development names this assumption:

```lean
axiom p2_runtime_correctness ...
```

Closing that forward-simulation obligation is the next verification priority. Until it is removed, `compile_sound` should be described as **axiom-dependent**, not as a fully closed compiler-correctness proof.

## Getting Started

Prerequisites for the RV32 path include Python 3.10+, a RISC-V toolchain, and `qemu-system-riscv32`.

```bash
# Executable verification harness
python run_verified_compilation_proof.py

# Differential tests
python run_differential_tests.py

# Example RV32/QEMU pipeline
python run_rv32_conditional_pipeline.py
```

For the Lean development, use the files under `lean/` and typecheck them with the repository's Lean/Lake configuration.

## Documentation

- `docs/VERIFICATION_STATUS.md` — authoritative claim ledger and repair gate
- `SPEC.md` — language and VM specification
- `formal_semantics.md` — formal-semantics design document
- `STATUS.md` — historical sprint record
- `paper/` — accompanying manuscript
- `comparative_examples.md` — PSL/conventional examples

## Project Scope

PSL is currently a **research prototype**. Its QEMU evidence does not establish behaviour on physical silicon, and its abstract Lean semantics do not yet have a proved refinement to the RV32 firmware implementation.

compiler · firmware · dsl · embedded-systems · type-theory · formal-methods · sanskrit · risc-v · panini · lean4
