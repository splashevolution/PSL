# Paninian Systems Language (PSL)

**PSL is a Paninian type system for verifiable embedded firmware.** It maps the structural rules of Panini's *Astadhyayi* (4th c. BCE) directly onto instruction-set semantics, with the goal of making entire classes of embedded bugs *structurally inexpressible* rather than merely caught at runtime.

The project pairs a working compiler and RISC-V firmware pipeline with machine-checked formal semantics in **Lean 4**.

## The Thesis

Modern hardware/software stacks are bloated because they lack semantic precision at the ISA level. The *Astadhyayi* is a formally complete, unambiguous rule system — every derivation is either provably valid or structurally impossible. PSL applies those principles to a real instruction set and proves, at each step on freestanding RV32 firmware under QEMU, that Paninian logic yields a leaner, more deterministic execution model than the heuristic layers modern systems accumulate.

## Status

- **15 proof sprints** complete
- **206 machine-checked assertions** (153 firmware checks on RV32 QEMU + 53 verified-compilation checks)
- **Differential testing:** 5000/5000 passing
- **Lean 4 formal spec:** `compile_sound` proved (zero `sorry`s, one axiom)
- **Paper:** 12 pages, clean citations and tables
- Three real-world verticals complete (Sprints 11–13)

> Research prototype. Proofs establish system-emulated MMIO output and RAM-backed decoder state under QEMU. They do **not** yet establish execution on physical silicon or an HDL gate-array implementation.

## Core Ideas

PSL maps Paninian grammatical concepts to machine semantics:

- **Karakas (data-flow relations)** — source (*apadana*), destination (*karman*), instrument (*karana*), and context (*adhikarana*) map to registers, memory, buses, and execution context
- **Anuvrtti (context inheritance)** — omitted operands are inherited from the preceding instruction, compressing code footprint
- **Avrtti (bounded repetition)** — loop counts are a structural property of the instruction word, eliminating off-by-one risk
- **Lopa (structured erasure)** — nullification with explicit boundary effects
- **Vrddhi (privilege escalation)** — structural expansion triggers Ring 0 clearance
- **Siddha / Asiddha visibility** — a deterministic globally-visible vs. shadow-cache memory model

## Bytecode / ABI

Every operation compiles to a fixed **32-bit, big-endian** instruction word:

```
31-28   27-24    23-16      15-08      07-00
RING_ID | COMP | OPCODE | TARGET | FLAGS/COND
```

A rigid layout eliminates decoding drift and keeps binaries predictable and inspectable.

## Repository Layout

- `src/` — the PSL compiler and RV32 firmware sources
- `lean/` — Lean 4 formal semantics and machine-checked proofs
- `programs/` — the `.pvm` source programs (one per sprint)
- `paper/` — the LaTeX paper and generated PDF
- `docs/` — specification and supporting documentation
- `evidence/` — per-sprint proof artifacts and captured UART traces
- `run_rv32_*_pipeline.py` — self-asserting build/execute/verify pipelines
- `run_verified_compilation_proof.py`, `run_differential_tests.py` — proof and differential-test drivers
- `SPEC.md`, `STATUS.md`, `formal_semantics.md` — deep-dive references

## How the Proofs Work

Each sprint produces one concept, one `.pvm` source file, one compiler extension, one firmware, and one self-asserting pipeline. A pipeline builds the firmware, embeds the compiled binary, runs it under QEMU (`-M virt -bios none`), captures UART output at MMIO `0x10000000`, and asserts the expected markers. **The proof is the test passing — not a simulation.**

## Getting Started

Prerequisites: Python 3.10+, a RISC-V toolchain (`riscv64-unknown-elf-gcc`), and `qemu-system-riscv32`. A `Dockerfile` is provided for a reproducible environment.

```bash
# Run the verified compilation proof
python run_verified_compilation_proof.py

# Run the differential test suite
python run_differential_tests.py

# Run a specific RV32 firmware sprint pipeline
python run_rv32_conditional_pipeline.py
```

See `STATUS.md` for the full toolchain flags and the per-sprint history.

## Documentation

- `SPEC.md` — language and VM specification
- `formal_semantics.md` — formal semantics
- `STATUS.md` — sprint-by-sprint history and current state
- `paper/` — the accompanying paper
- `comparative_examples.md` — PSL vs. conventional examples

## Topics

compiler · firmware · dsl · embedded-systems · type-theory · formal-methods · sanskrit · compcert · formal-verification · risc-v · panini · lean4
