import PSL.SemanticKernel

namespace PSL

/-
  PVM32 is the first PSL driver contract, not the definition of PSL.

  The existing Python compiler and 32-bit ABI remain the executable historical
  implementation underneath this contract. This module only states which
  target-independent semantic capabilities that driver family currently
  claims to realize. Actual SemanticScript -> PVM32 refinement is a separate
  proof obligation and is not claimed here.
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

end PSL
