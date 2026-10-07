# PSL Semantic Architecture

## Status

This document introduces an architectural layer above the repaired PVM32
compiler/ABI. It does not replace or weaken the verified repair baseline.

## Principle

**Meaning is not a word. Meaning is not an address.**

PSL separates three concerns:

```text
surface expression
      ↓ elaboration
language-neutral semantic script
      ↓ validation / proof
verified semantic script
      ↓ driver contract
target realization
```

A natural-language spelling is a view over meaning. A target address, opcode,
register, GPU buffer, network topic, or circuit is a realization of meaning.

Neither owns the meaning.

## Semantic identity

`SemanticId` is deliberately opaque with respect to human vocabulary and
hardware layout.

The same semantic identity may be rendered by different surfaces:

```text
English      "write status"       ┐
Devanagari   "स्थितिः लिखति ।"    ├─> same SemanticScript
future UI    graphical expression ┘
```

Likewise, a driver may map that identity differently:

```text
PVM32 driver  -> device address / ABI word
GPU driver    -> buffer / kernel operation
FPGA driver   -> signal / pipeline
future target -> target-specific realization
```

The mapping is driver-owned, not language-owned.

## Kernel vocabulary

The first kernel intentionally models only enough structure to establish the
separation:

- `SemanticId` — stable semantic identity
- `RelationKind` — source, destination, instrument, context
- `Action` — read, write, store, consume
- `Authority` — ordinary or privileged
- `ContextMode` — explicit or inherited
- `SemanticTerm` — one target-independent semantic operation
- `SemanticScript` — ordered semantic terms
- `SurfaceForm` — human rendering plus elaborated meaning
- `DriverContract` — capabilities a realization declares

These names are implementation labels inside the formal model, not mandatory
surface-language vocabulary.

## Driver rule

A driver may choose **how** to realize a script. It may not silently change
**what** the script means.

The kernel therefore derives required capabilities from semantic terms and a
driver explicitly declares what it supports. Unsupported scripts are rejected
at the driver boundary.

This is only the first gate. Capability acceptance is not yet a refinement
proof.

## PVM32 status

The existing 32-bit ABI and Python compiler are preserved as the first
realization family: **PVM32 Driver 0**.

Current verified work below this layer remains valid:

```text
Python final IR
    -> Lean validation
    -> ValidProgram
    -> abstract execution
```

The new open obligation is:

```text
SemanticScript
    -> PVM32 realization
    -> existing Prakriya IR
```

That arrow must be specified and proved rather than assumed.

## Non-goals of this first kernel

This commit does not claim:

- universal natural-language understanding;
- that the four relation kinds are a complete Kāraka model;
- that PVM32 refinement from `SemanticScript` is proved;
- GPU/FPGA portability;
- source-language equivalence beyond explicit elaboration;
- that semantic IDs solve ontology alignment by themselves.

Those are later research problems.

## Architectural invariant

Future PSL work should preserve:

> Surfaces may change words. Drivers may change realization. Neither may
> silently change semantic meaning.
