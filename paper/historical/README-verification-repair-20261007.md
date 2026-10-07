# PSL paper

`psl_paper.tex` is the active verification-repair manuscript.

The pre-repair source is preserved under `paper/historical/` for provenance.
The previously committed PDF was removed because it contained superseded
verification claims.

PDFs are now build artifacts, not source-controlled authorities. The paper CI
workflow compiles the active TeX source and uploads `psl_paper.pdf` as a
workflow artifact.

The claim authority remains:

1. `docs/VERIFICATION_STATUS.md`
2. `lean/PSL/Semantics.lean`
3. the current compiler/tests

A successful PDF build demonstrates document reproducibility, not correctness
of the research claims.
