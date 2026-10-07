import Std.Tactic

namespace PSL

/-
  PSL language-neutral semantic kernel.

  This module contains no parser tokens, source-language vocabulary, device
  addresses, or target opcodes. It is an implementation checkpoint beneath the
  semantic-continuity research programme.

  A SemanticId denotes meaning. It is not a word and it is not an address.
-/

structure SemanticId where
  value : Nat
  deriving Repr, BEq, DecidableEq

/-- Target-independent semantic relationships. -/
inductive RelationKind where
  | source
  | destination
  | instrument
  | context
  deriving Repr, BEq, DecidableEq

/-- Target-independent actions understood by the current semantic script. -/
inductive Action where
  | read
  | write
  | store
  | consume
  deriving Repr, BEq, DecidableEq

/-- Authority is semantic; a realization decides how to implement it. -/
inductive Authority where
  | ordinary
  | privileged
  deriving Repr, BEq, DecidableEq

/-- Whether a term states its context or lawfully inherits live context. -/
inductive ContextMode where
  | explicit
  | inherit
  deriving Repr, BEq, DecidableEq

structure Relation where
  kind   : RelationKind
  entity : SemanticId
  deriving Repr, BEq, DecidableEq

/--
A semantic term describes meaning before any ABI, ISA, address, register,
runtime, protocol, or source-language spelling has been chosen.
-/
structure SemanticTerm where
  action      : Action
  relations   : List Relation
  authority   : Authority := .ordinary
  contextMode : ContextMode := .explicit
  deriving Repr, BEq, DecidableEq

structure SemanticScript where
  terms : List SemanticTerm
  deriving Repr, BEq, DecidableEq

-- Initial capability gate -----------------------------------------------------

inductive Capability where
  | read
  | write
  | store
  | consume
  | privileged
  | inheritContext
  deriving Repr, BEq, DecidableEq

def actionCapability : Action → Capability
  | .read    => .read
  | .write   => .write
  | .store   => .store
  | .consume => .consume

def SemanticTerm.requiredCapabilities (t : SemanticTerm) : List Capability :=
  [actionCapability t.action] ++
  (match t.authority with
   | .ordinary   => []
   | .privileged => [.privileged]) ++
  (match t.contextMode with
   | .explicit => []
   | .inherit  => [.inheritContext])

structure DriverContract where
  name     : String
  supports : Capability → Bool

def DriverContract.acceptsTerm
    (d : DriverContract) (t : SemanticTerm) : Bool :=
  t.requiredCapabilities.all d.supports

def DriverContract.acceptsScript
    (d : DriverContract) (s : SemanticScript) : Bool :=
  s.terms.all d.acceptsTerm

/-
  This boolean capability contract is intentionally only an early gate. It does
  not prove that a target binding, representation, sequence, state transition,
  unit, persistence property, or observable behavior realizes the intended
  semantics. The semantic-continuity research line is intended to strengthen
  this boundary with explicit realization evidence.
-/

-- Minimal neutral witness ------------------------------------------------------

/-
  1001 is a semantic identity chosen solely for this implementation witness.
  It is not the historical PVM address 0x20 and must never be interpreted as
  one.
-/
def statusIdentity : SemanticId := ⟨1001⟩

def statusWrite : SemanticTerm :=
  { action := .write
  , relations := [{ kind := .destination, entity := statusIdentity }]
  , authority := .ordinary
  , contextMode := .explicit }

def statusScript : SemanticScript :=
  { terms := [statusWrite] }

end PSL
