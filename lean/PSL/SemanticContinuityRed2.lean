import PSL.SemanticContinuityGreen1

namespace PSL

/-
  Semantic Continuity RED-2
  -------------------------

  GREEN-1 established binding correctness relative to an independently stated
  DeviceModel.

  RED-2 asks whether that boundary also establishes representation correctness.

  It does not.

  Two candidate writes may select the same semantically correct resource while
  carrying different raw payloads. The GREEN-1 checker inspects only the
  resource binding, so both candidates pass.

  This file deliberately does NOT introduce representation semantics. It
  records the next missing relation.
-/

/--
A minimal target-side write candidate used only for RED-2.

The resource and raw payload are separated explicitly so the theorem can show
which field GREEN-1 observes and which field it ignores.
-/
structure CandidateWrite (Resource : Type) where
  resource : Resource
  rawValue : Nat
  deriving Repr, BEq, DecidableEq

/--
Turn one concrete candidate into the single semantic binding needed by the
GREEN-1 checker.

The raw payload is intentionally absent because GREEN-1 has no representation
semantics.
-/
def CandidateWrite.resourceOf
    {Resource : Type}
    (semanticId : SemanticId)
    (candidate : CandidateWrite Resource) :
    SemanticId → Option Resource :=
  fun id => if id == semanticId then some candidate.resource else none

/--
The strongest GREEN-1 gate available for one explicit write candidate:
binding agreement with the independently stated device model.
-/
def green1CandidateGate
    {Resource : Type}
    (device : DeviceModel Resource)
    (semanticId : SemanticId)
    (candidate : CandidateWrite Resource) : Bool :=
  checkBinding
    device
    (candidate.resourceOf semanticId)
    semanticId

/--
Reference encoding for the next falsification experiment.

At RED-2 this is only an experimental reference payload. The current theory
does not yet state why 250 represents the desired semantic value.
-/
def referenceSetpointWrite : CandidateWrite (Fin 256) :=
  { resource := fin256 0x20
  , rawValue := 250 }

/--
Wrong-scale mutation of the same target resource.

Again, RED-2 does not yet prove that 25 is semantically wrong. It proves that
GREEN-1 cannot distinguish it from the reference payload.
-/
def wrongScaleSetpointWrite : CandidateWrite (Fin 256) :=
  { resource := fin256 0x20
  , rawValue := 25 }

theorem red2_same_resource :
    referenceSetpointWrite.resource =
      wrongScaleSetpointWrite.resource := by
  native_decide

theorem red2_payloads_are_distinct :
    referenceSetpointWrite.rawValue ≠
      wrongScaleSetpointWrite.rawValue := by
  native_decide

theorem red2_reference_passes_green1 :
    green1CandidateGate
      pvm32Green1DeviceModel
      statusIdentity
      referenceSetpointWrite = true := by
  native_decide

theorem red2_wrong_scale_also_passes_green1 :
    green1CandidateGate
      pvm32Green1DeviceModel
      statusIdentity
      wrongScaleSetpointWrite = true := by
  native_decide

/--
RED-2 result.

The two candidates select the same resource and therefore both satisfy the
GREEN-1 binding relation, even though their raw payloads differ.

The theorem deliberately does not claim which payload realizes the intended
semantic value. That relation is exactly what is missing.
-/
theorem red2_green1_is_representation_blind :
    referenceSetpointWrite.rawValue ≠ wrongScaleSetpointWrite.rawValue ∧
    green1CandidateGate
      pvm32Green1DeviceModel
      statusIdentity
      referenceSetpointWrite = true ∧
    green1CandidateGate
      pvm32Green1DeviceModel
      statusIdentity
      wrongScaleSetpointWrite = true := by
  native_decide

end PSL
