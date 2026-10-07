namespace PSL

/-
  PSL language-neutral semantic kernel.

  The kernel deliberately contains no parser tokens, source-language keywords,
  device addresses, ABI opcodes, or natural-language names. Surface forms and
  hardware drivers are adapters around this layer.

  A SemanticId denotes meaning. It is not a word and it is not an address.
-/

structure SemanticId where
  value : Nat
  deriving Repr, BEq, DecidableEq

/-- Stable semantic relationships inspired by Karaka roles. -/
inductive RelationKind where
  | source
  | destination
  | instrument
  | context
  deriving Repr, BEq, DecidableEq

/-- Target-independent actions understood by the semantic script. -/
inductive Action where
  | read
  | write
  | store
  | consume
  deriving Repr, BEq, DecidableEq

/-- Authority is semantic; a driver decides how to realize it physically. -/
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
runtime, or natural-language spelling has been chosen.
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

/--
A SurfaceForm is only a rendering/elaboration boundary. Its text and language
do not participate in semantic equality.
-/
structure SurfaceForm where
  language : String
  text     : String
  meaning  : SemanticScript
  deriving Repr

def SurfaceForm.elaborate (s : SurfaceForm) : SemanticScript :=
  s.meaning

def semanticallyEquivalent (a b : SurfaceForm) : Prop :=
  a.elaborate = b.elaborate

theorem same_meaning_implies_surface_equivalence
    (a b : SurfaceForm)
    (h : a.meaning = b.meaning) :
    semanticallyEquivalent a b := by
  simpa [semanticallyEquivalent, SurfaceForm.elaborate] using h

-- Driver capability contract --------------------------------------------------

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
  The driver may choose a realization only after declaring that it supports
  the semantic capabilities required by the script. This is intentionally
  independent of any particular backend representation.
-/

-- Cross-surface witness -------------------------------------------------------

/-
  1001 is a semantic identity chosen solely for this witness. It is NOT the
  historical PVM address 0x20 and must never be interpreted as one.
-/
def statusIdentity : SemanticId := ⟨1001⟩

def statusWrite : SemanticTerm :=
  { action := .write
  , relations := [{ kind := .destination, entity := statusIdentity }]
  , authority := .ordinary
  , contextMode := .explicit }

def statusScript : SemanticScript :=
  { terms := [statusWrite] }

def englishStatusSurface : SurfaceForm :=
  { language := "en"
  , text := "write status"
  , meaning := statusScript }

def devanagariStatusSurface : SurfaceForm :=
  { language := "sa-Deva"
  , text := "स्थितिः लिखति ।"
  , meaning := statusScript }

theorem english_and_devanagari_status_are_same_program :
    semanticallyEquivalent englishStatusSurface devanagariStatusSurface := by
  rfl

end PSL
