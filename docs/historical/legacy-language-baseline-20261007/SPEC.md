# PSL Canonical Language and VM Specification

**Revision:** verification repair, 2026-10-07
**Status:** research prototype; feature development frozen while semantic/refinement work is completed.

The pre-repair specification is preserved at
`docs/historical/SPEC-pre-verification-repair.md`.

## 1. Purpose

PSL is a small systems-language research prototype inspired by structural ideas
from Pāṇinian grammar. The current goal is not to replace conventional systems
languages. It is to test whether explicit structural legality rules can produce
a compact, auditable compiler/runtime contract.

The normative abstract semantics are in `lean/PSL/Semantics.lean`.

## 2. 32-bit ABI

```text
31..28   27..24   23..16   15..08   07..04   03..00
RING     COMP      OPCODE    TARGET    FLAGS     COND
```

The binary image is serialized big-endian.

Current opcodes:

- `0x00` Lopa
- `0x05` Write
- `0x06` Read
- `0xCC` Store
- `0xAA` Adhikāra OPEN
- `0xBB` Adhikāra CLOSE

`COMP=0` is explicit target form.
`COMP=1` is Anuvṛtti.
`COMP>1` is reserved by the historical language for Āvṛtti count encoding;
full repetition semantics remain outside the current proved core.

`FLAGS=0xE` marks the first member of a compiler-declared Sandhi pair.
Atomic runtime meaning is not yet formally established.

## 3. Address regions

```text
Siddha   = addresses < 0x50
Asiddha  = addresses >= 0x50
```

The address partition is static.

A Ring-2 WRITE may target either region. The eventual canonical runtime must
define the visibility/storage behavior of Asiddha writes precisely.

Ring-0 instructions may resolve only to Asiddha targets.

## 4. Instruction privilege

Ring is encoded in each instruction.

Adhikāra supplies scope authority. Canonical legality requires:

- Ring 0 instruction -> active Adhikāra scope;
- Ring 0 instruction -> resolved Asiddha target;
- Store -> active Adhikāra + Ring 0;
- Lopa of Asiddha -> active Adhikāra + Ring 0.

The compiler auto-promotes Store and Lopa to Ring 0 where its source-building
rules specify that behavior, but the validator independently checks the emitted
IR rather than trusting promotion.

## 5. Anuvṛtti

An Anuvṛtti instruction carries `COMP=1` and no independent semantic target.
Its effective target is the current live context.

Anuvṛtti is illegal when no live context exists.

A successful explicit non-Lopa instruction establishes target context.

## 6. Lopa

Lopa is structured erasure.

Canonical rules:

1. the resolved target must have live written state;
2. Lopa consumes that written state;
3. Lopa clears Anuvṛtti context.

Therefore Lopa is both a state-lifecycle operation and a context boundary.

## 7. Pāṇinian legality rules

The current compiler groups several checks under the historical P1-P4 naming.
The canonical semantic content is:

### P1 — context validity

Anuvṛtti requires live target context.

### P2 — live erasure

Lopa requires a currently live written target.

### P3 — privileged target region

Ring 0 may resolve only to Asiddha.

### P4 — privilege scope

Ring 0 requires Adhikāra. Store is always scoped Ring 0. Asiddha Lopa is scoped
Ring 0.

Error identifiers remain implementation-facing compatibility labels; the
semantic rules above are normative.

## 8. Written-state transitions

For resolved target `t`:

```text
WRITE(t): W[t] := true
STORE(t): W[t] := true
LOPA(t):  require W[t] = true; W[t] := false
READ(t):  W unchanged
```

Inherited WRITE/STORE affect the resolved inherited target exactly as explicit
forms do.

## 9. Adhikāra transitions

```text
OPEN  -> scopeDepth + 1
CLOSE -> require scopeDepth > 0; scopeDepth - 1
```

A valid complete program finishes with scope depth zero.

## 10. Sandhi

Sandhi remains a compiler transform that:

- requires two compatible write-class instructions;
- requires same target;
- requires an explicit first instruction;
- requires same ring;
- marks the first lowered word with `FLAGS=0xE`.

The active canonical example places two Stores inside Adhikāra.

**Atomic execution is not yet part of the repaired formal theorem.**

## 11. Current conformance

The following are current conformance mechanisms:

- `tests/test_semantic_contract.py`
- `tests/test_canonical_programs.py`
- `lean/PSL/Semantics.lean`
- `lean/Audit.lean`
- GitHub Actions for Python semantic contract + Lean verification

Historical firmware pipelines are not all normative because their semantics
evolved between sprints.

## 12. Current proof boundary

Machine-checked:

```text
successful canonical ABI validation
              =>
successful abstract execution
with the same final control state
```

Still open:

```text
PSL source
  -> Python compiler
  -> canonical ABI validation
  -> Lean abstract execution
  -> canonical RV32 runtime
  -> physical hardware
```

The first open arrow to close is the Python compiler / Lean validator
correspondence for the canonical subset.

## 13. Research claims

The following are not specification facts and must be tested independently:

- PSL is smaller/faster than conventional approaches;
- PSL improves deterministic timing;
- Pāṇinian structure is superior to existing type/capability systems;
- the design prevents broad categories of embedded bugs;
- QEMU behavior predicts physical hardware behavior.

The project should report negative results where they occur.
