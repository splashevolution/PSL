import PSL.SemanticKernel
import PSL.Semantics

namespace PSL

/-
  PVM32 is the first PSL driver contract, not the definition of PSL.

  The existing Python compiler and 32-bit ABI remain the executable historical
  implementation underneath this contract. This module gives the first formal
  adapter from target-independent SemanticScript terms into that ABI.

  SemanticId values are not PVM addresses. A PVM32Bindings value owns that
  target-specific association.
-/

def pvm32Supports : Capability → Bool
  | .read           => true
  | .write          => true
  | .store          => true
  | .consume        => true
  | .privileged     => true
  | .inheritContext => true

def pvm32Driver : DriverContract :=
  { name := "pvm32"
  , supports := pvm32Supports }

example : pvm32Driver.acceptsScript statusScript = true := by
  native_decide

/-- A deliberately weaker driver demonstrates capability-based rejection. -/
def writeOnlySupports : Capability → Bool
  | .write => true
  | _      => false

def writeOnlyDriver : DriverContract :=
  { name := "write-only"
  , supports := writeOnlySupports }

def privilegedStoreWitness : SemanticScript :=
  { terms :=
      [{ action := .store
       , relations := [{ kind := .destination, entity := ⟨2001⟩ }]
       , authority := .privileged
       , contextMode := .explicit }] }

example : writeOnlyDriver.acceptsScript privilegedStoreWitness = false := by
  native_decide

-- Target binding --------------------------------------------------------------

/--
Driver-owned mapping from semantic identity to a PVM32 target byte.
The semantic kernel contains no such address.
-/
structure PVM32Bindings where
  targetOf : SemanticId → Option (Fin 256)

def relationEntity?
    (kind : RelationKind) : List Relation → Option SemanticId
  | [] => none
  | r :: rs =>
      if r.kind == kind then some r.entity else relationEntity? kind rs

def principalRelation : Action → RelationKind
  | .read    => .source
  | .write   => .destination
  | .store   => .destination
  | .consume => .destination

def pvm32Opcode : Action → Fin 256
  | .read    => OP_READ
  | .write   => OP_WRITE
  | .store   => OP_STORE
  | .consume => OP_LOPA

def pvm32Ring : Authority → Fin 16
  | .ordinary   => fin16 2
  | .privileged => fin16 0

def pvm32Comp : ContextMode → Fin 16
  | .explicit => fin16 0
  | .inherit  => fin16 1

/--
Lower one semantic term after the driver has accepted its required
capabilities. Explicit terms require a driver binding. Inherited terms carry
no target address in the ABI and rely on the already-defined PVM context rule.
-/
def pvm32LowerTerm?
    (bindings : PVM32Bindings) (t : SemanticTerm) : Option ABIWord :=
  if pvm32Driver.acceptsTerm t then
    match t.contextMode with
    | .inherit =>
        some
          { ring := pvm32Ring t.authority
          , comp := pvm32Comp t.contextMode
          , opcode := pvm32Opcode t.action
          , target := fin256 0
          , flags := fin16 0xF
          , cond := fin16 0 }
    | .explicit =>
        match relationEntity? (principalRelation t.action) t.relations with
        | none => none
        | some semanticTarget =>
            match bindings.targetOf semanticTarget with
            | none => none
            | some physicalTarget =>
                some
                  { ring := pvm32Ring t.authority
                  , comp := pvm32Comp t.contextMode
                  , opcode := pvm32Opcode t.action
                  , target := physicalTarget
                  , flags := fin16 0xF
                  , cond := fin16 0 }
  else
    none

def pvm32LowerTerms?
    (bindings : PVM32Bindings) :
    List SemanticTerm → Option (List ABIWord)
  | [] => some []
  | t :: ts =>
      match pvm32LowerTerm? bindings t, pvm32LowerTerms? bindings ts with
      | some w, some ws => some (w :: ws)
      | _, _ => none

def pvm32LowerScript?
    (bindings : PVM32Bindings) (script : SemanticScript) :
    Option (List ABIWord) :=
  pvm32LowerTerms? bindings script.terms

def pvm32Words?
    (bindings : PVM32Bindings) (script : SemanticScript) :
    Option (List Nat) :=
  match pvm32LowerScript? bindings script with
  | none => none
  | some words => some (words.map ABIWord.toNat)

/--
Reference binding for the cross-surface witness.

The association SemanticId(1001) -> 0x20 exists here, in the PVM32 driver,
rather than in the semantic identity or either source language.
-/
def referencePVM32Bindings : PVM32Bindings :=
  { targetOf := fun id =>
      if id == statusIdentity then some (fin256 0x20) else none }

example :
    pvm32Words? referencePVM32Bindings englishStatusSurface.elaborate =
      some [0x200520F0] := by
  native_decide

example :
    pvm32Words? referencePVM32Bindings devanagariStatusSurface.elaborate =
      some [0x200520F0] := by
  native_decide

theorem surface_choice_does_not_change_pvm32_realization :
    pvm32Words? referencePVM32Bindings englishStatusSurface.elaborate =
    pvm32Words? referencePVM32Bindings devanagariStatusSurface.elaborate := by
  rfl

end PSL
