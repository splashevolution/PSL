import PSL.SemanticContinuityRed1

namespace PSL

/-
  Semantic Continuity GREEN-1
  ---------------------------

  RED-1 showed that capability declaration plus successful lowering is blind to
  whether a supplied target binding is semantically justified.

  GREEN-1 adds the minimum missing object: a target-specific DeviceModel whose
  resource denotation is independent of the realization binding.

  This closes only the binding-correctness gap. It does NOT yet model value
  representation, units, protocol state, acknowledgements, persistence,
  atomicity, timing, or physical-device conformance.
-/

/--
A target-specific model of what each concrete resource denotes semantically.

Resource is intentionally abstract here. A PVM32 instance may use Fin 256;
another hardware generation may use a different resource type.

The target-neutral SemanticScript does not contain a physical resource.
-/
structure DeviceModel (Resource : Type) where
  denotes : Resource → Option SemanticId

/--
A binding matches a device model when the resource selected for a semantic
identity is independently modeled as denoting that same identity.
-/
def bindingMatchesDevice
    {Resource : Type}
    (device : DeviceModel Resource)
    (resourceOf : SemanticId → Option Resource)
    (id : SemanticId) : Prop :=
  match resourceOf id with
  | none => False
  | some resource => device.denotes resource = some id

/--
Executable binding checker.

The realization supplies resourceOf; the device model supplies denotes.
Acceptance therefore does not trust the realization's mapping by itself.
-/
def checkBinding
    {Resource : Type}
    (device : DeviceModel Resource)
    (resourceOf : SemanticId → Option Resource)
    (id : SemanticId) : Bool :=
  match resourceOf id with
  | none => false
  | some resource => decide (device.denotes resource = some id)

/--
The executable checker is sound and complete for the binding relation stated
above. This theorem is generic over the target resource type.
-/
theorem checkBinding_true_iff
    {Resource : Type}
    (device : DeviceModel Resource)
    (resourceOf : SemanticId → Option Resource)
    (id : SemanticId) :
    checkBinding device resourceOf id = true ↔
      bindingMatchesDevice device resourceOf id := by
  unfold checkBinding bindingMatchesDevice
  cases hresource : resourceOf id <;> simp [hresource]

-- PVM32 witness ---------------------------------------------------------------

/--
A second semantic identity used to make 0x21 a modeled resource rather than
merely an unmapped byte. GREEN-1 therefore rejects the adversarial RED-1
binding because 0x21 denotes a different meaning, not just because it is
absent from the model.
-/
def diagnosticIdentity : SemanticId := ⟨1002⟩

/--
Minimal target-specific PVM32 device model for the RED-1 witness.

Physical addresses belong here, at the target model boundary, not in
statusScript or statusIdentity.
-/
def pvm32Green1DeviceModel : DeviceModel (Fin 256) :=
  { denotes := fun resource =>
      if resource = fin256 0x20 then
        some statusIdentity
      else if resource = fin256 0x21 then
        some diagnosticIdentity
      else
        none }

theorem green1_reference_binding_accepts :
    checkBinding
      pvm32Green1DeviceModel
      referencePVM32Bindings.targetOf
      statusIdentity = true := by
  native_decide

theorem green1_adversarial_binding_rejects :
    checkBinding
      pvm32Green1DeviceModel
      adversarialPVM32Bindings.targetOf
      statusIdentity = false := by
  native_decide

/--
GREEN-1 closes exactly the counterexample established by RED-1:

* both bindings still pass the old capability-plus-lowering boundary;
* the independently modeled resource semantics accepts the reference binding;
* the same checker rejects the adversarial binding.

No physical address was added to the target-neutral semantic script.
-/
theorem green1_separates_red1_witness :
    currentRealizationGate referencePVM32Bindings statusScript = true ∧
    currentRealizationGate adversarialPVM32Bindings statusScript = true ∧
    checkBinding
      pvm32Green1DeviceModel
      referencePVM32Bindings.targetOf
      statusIdentity = true ∧
    checkBinding
      pvm32Green1DeviceModel
      adversarialPVM32Bindings.targetOf
      statusIdentity = false := by
  native_decide

/--
Any binding accepted by checkBinding satisfies the stated device-model
denotation relation. The realization generator itself is not trusted for that
claim.
-/
theorem green1_checked_binding_is_model_faithful
    {Resource : Type}
    (device : DeviceModel Resource)
    (resourceOf : SemanticId → Option Resource)
    (id : SemanticId)
    (hcheck : checkBinding device resourceOf id = true) :
    bindingMatchesDevice device resourceOf id :=
  (checkBinding_true_iff device resourceOf id).mp hcheck

end PSL
