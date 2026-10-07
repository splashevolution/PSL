import PSL.PVM32Driver

namespace PSL

/-
  Semantic Continuity RED-1
  -------------------------

  Purpose:
  exhibit a machine-checked counterexample to the idea that the current
  capability gate establishes realization correctness.

  The existing model can check whether a script requires WRITE and whether the
  PVM32 driver declares WRITE support. It can also lower any supplied
  SemanticId -> target-byte binding.

  What it cannot express is why one supplied binding is semantically faithful
  and another is not.

  This file deliberately does NOT introduce the missing device model or
  realization-proof machinery. It records the gap we want GREEN-1 to close.
-/

/-- An adversarial alternative to the existing reference binding.

Both bindings are total enough for statusScript to lower. The current core has
no semantic relation capable of preferring 0x20 over 0x21.
-/
def adversarialPVM32Bindings : PVM32Bindings :=
  { targetOf := fun id =>
      if id == statusIdentity then some (fin256 0x21) else none }

/--
Characterize the acceptance boundary that exists today:
  1. the driver declares the script's required capabilities, and
  2. lowering succeeds for the supplied target binding.

This is an observation of the current architecture, not the desired future
definition of realization correctness.
-/
def currentRealizationGate
    (bindings : PVM32Bindings) (script : SemanticScript) : Bool :=
  pvm32Driver.acceptsScript script &&
    (pvm32LowerScript? bindings script).isSome

theorem red1_bindings_are_distinct :
    referencePVM32Bindings.targetOf statusIdentity ≠
      adversarialPVM32Bindings.targetOf statusIdentity := by
  native_decide

theorem red1_reference_binding_lowers :
    pvm32Words? referencePVM32Bindings statusScript =
      some [0x200520F0] := by
  native_decide

theorem red1_adversarial_binding_also_lowers :
    pvm32Words? adversarialPVM32Bindings statusScript =
      some [0x200521F0] := by
  native_decide

/--
RED-1 result.

Two distinct target bindings for the same semantic script both pass the entire
acceptance boundary available today, even though they produce different target
programs.

The theorem does NOT assert which target byte is physically correct. That fact
cannot be stated in the current model. The inability to state and check that
relationship is exactly the research gap.
-/
theorem red1_capability_gate_is_binding_blind :
    currentRealizationGate referencePVM32Bindings statusScript = true ∧
    currentRealizationGate adversarialPVM32Bindings statusScript = true ∧
    pvm32Words? referencePVM32Bindings statusScript ≠
      pvm32Words? adversarialPVM32Bindings statusScript := by
  native_decide

end PSL
