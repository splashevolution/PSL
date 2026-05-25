# Pāṇinian Systems Language (PSL) — Project Manifest

**Last updated:** 2026-05-24  
**Status:** Publication-ready. All artefacts verified, paper compiled clean.

---

## What This Project Is

PSL is a domain-specific language for embedded peripheral control whose type
system is derived from Pāṇini's Pāribhāṣā meta-rules. A class of embedded
programming errors is made structurally inexpressible: the compiler produces no
binary for an illegal program. This is stronger than a suppressible warning.

**Paper:** `paper/psl_paper.tex` / `paper/psl_paper.pdf`  
(12 pages, zero overfull hboxes, all citations resolved; submitted to arXiv cs.PL)

---

## Verified Milestones

| Sprint | Concept | Checks | Status |
|--------|---------|--------|--------|
| 1–2 | Siddha/Asiddha isolation + Utsarga/Apavāda | 10 | ✓ |
| 3 | Āvṛtti (bounded repetition) | 5 | ✓ |
| 4 | Anuvṛtti (context inheritance) | 5 | ✓ |
| 5 | Lopa (structured erasure) | 6 | ✓ |
| 6 | Sañjñā (zero-cost name abstraction) | 7 | ✓ |
| 7 | Pāribhāṣā P1–P4 structural rejection | 9 | ✓ |
| 8 | Prakriya IR determinism (L1/L2) | 5 | ✓ |
| 9 | Sandhi instruction fusion (S1–S5) | 11 | ✓ |
| 10 | Adhikāra privilege scope | 15 | ✓ |
| 11 | MMIO Boot Sequencer (real-world vertical) | 26 | ✓ |
| 12 | Safety-Critical Valve Interlock (real-world vertical) | 26 | ✓ |
| 13 | Cryptographic Key Lifecycle (real-world vertical) | 28 | ✓ |
| 14 | CompCert-style verified compilation chain (5 phases) | 47 | ✓ |
| 15 | Lean 4 formal proof of compile_sound_statement | 6 | ✓ |
| **Total** | | **206** | **✓** |

Differential test suite: 5,000 programs, seed 42, 4 invariant properties — all pass.

---

## Repository Layout

```
programs/                   All 12 PSL source files (.pvm)
src/
  utils/
    paninian_compiler.py    PaninianFormalCompiler (832 lines)
    build_firmware.py       .pvm → .bin via compiler
    embed_binary_image.py   .bin → pvm_image.h C array
  rv32/                     Freestanding RV32 firmware (C + asm)
lean/
  PSL/Semantics.lean        Lean 4 formal spec (531 lines, 0 sorrys, 1 axiom)
  lakefile.lean             Lake build descriptor
paper/
  psl_paper.tex             LaTeX source
  psl_paper.pdf             Compiled paper (12 pages)
  psl_paper.bib             Bibliography (14 entries)
evidence/                   15 proof records (one per sprint)
docs/                       Case study document (DOCX + PDF)
run_rv32_*_pipeline.py      Sprint runners (Sprints 1–13, require QEMU VM)
run_prakriya_ir_proof.py    Sprint 8 local IR proof
run_differential_tests.py   5,000-program differential suite
run_verified_compilation_proof.py  Sprint 14–15 harness (53/53, no VM needed)
```

---

## Reproduction

```bash
# Sprint 14–15 verified chain (no VM, no Lean required):
python3 run_verified_compilation_proof.py
# Expected: Sprint 14–15 COMPLETE — 53/53 checks passed

# Differential test suite:
python3 run_differential_tests.py
# Expected: 5000/5000 PASS

# Lean 4 typecheck (requires elan):
cd lean && lake build

# Compile the paper:
cd paper && pdflatex psl_paper.tex && bibtex psl_paper && pdflatex psl_paper.tex && pdflatex psl_paper.tex
```

Sprints 1–13 pipeline runners require `qemu-system-riscv32`, `riscv32-unknown-elf-gcc`,
and SSH access to a Lubuntu VM with `PVM_VM_PASSWORD` set in the environment.
No credentials are ever hardcoded.

---

## Key Files

| File | Purpose |
|------|---------|
| `src/utils/paninian_compiler.py` | Compiler: lexer, IR, Sandhi, Pāribhāṣā, lowering |
| `lean/PSL/Semantics.lean` | Lean 4 formal spec and `compile_sound` proof |
| `run_verified_compilation_proof.py` | 53-check executable proof harness |
| `paper/psl_paper.pdf` | Research paper (12 pages) |
| `STATUS.md` | Living project status document |
| `evidence/` | Sprint proof records (15 files) |
