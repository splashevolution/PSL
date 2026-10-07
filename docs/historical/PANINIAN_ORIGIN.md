# Historical Note: Pāṇinian Origin of PSL

## Why this document exists

PSL began as the **Paninian Systems Language**, exploring whether selected structures associated with Pāṇini's derivational system could inspire a programming-language and systems-semantics architecture.

That exploration produced useful questions about semantic identity, context, authority, lifecycle, exceptions, and explicit derivation.

It did **not** establish that Pāṇinian terminology or structure was itself a novel systems contribution.

## Why the project changed direction

A broader prior-art review showed that many ideas surrounding the original framing already have deep research traditions:

- multilingual abstract/concrete syntax;
- formal and controlled languages;
- verified compilation;
- proof-carrying code;
- extensible IRs;
- modular metatheory;
- platform-independent models;
- legacy-system preservation;
- verified device drivers.

Keeping Pāṇini at the center without demonstrating a specific formal advantage would risk turning historical inspiration into branding rather than research.

The project therefore moved to neutral terminology and a narrower problem:

> semantic continuity across changing implementations and hardware generations.

## What remains in the code

Historical names and semantics remain in parts of the current verified baseline, including concepts originally described using terms such as context inheritance, authority scope, lifecycle consumption, and visibility.

They remain because they are part of an already-tested development history, not because the current research programme asserts a Pāṇinian novelty claim.

Future refactoring may replace some terminology with neutral names where that improves clarity without weakening the verified baseline.

## When Pāṇini should return

A Pāṇinian connection should become a current technical claim only if a controlled comparison demonstrates a meaningful property such as:

- stronger locality of exception reasoning;
- better provenance for inherited context;
- useful scoped-authority theorems;
- conservative evolution under explicit rule applicability;
- smaller or more reusable proof obligations than a conventional formulation.

If a standard transition-system or refinement calculus performs equally well, PSL should prefer the standard formulation.

## Respectful position

Archiving the Pāṇinian origin is not a rejection of the inspiration.

It is a decision not to use Pāṇini's name as evidence.

If the mathematics later shows that a Pāṇinian structure contributes something genuinely useful, the project can restore that connection with stronger justification.
