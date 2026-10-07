import PSL.SemanticContinuityRed2

namespace PSL

/-
  Semantic Continuity GREEN-2
  ---------------------------

  RED-2 showed that GREEN-1 binding correctness is blind to raw
  representation. Two candidates can select the same semantically correct
  resource while carrying different payloads.

  GREEN-2 adds the minimum missing relation: a target-specific representation
  model that independently maps a target-neutral semantic value to a raw
  target representation.

  This closes only the RED-2 representation gap. It does NOT yet model
  protocol state, ordering, acknowledgements, persistence, atomicity, timing,
  or physical-device conformance.
-/

/-- Target-neutral units needed by the current witness. -/
inductive SemanticUnit where
  | celsius
  | fahrenheit
  deriving Repr, BEq, DecidableEq

/--
A minimal target-neutral semantic quantity.

Magnitude is expressed in whole semantic units for the current witness. The
target representation may choose any scaling or encoding.
-/
structure SemanticQuantity where
  magnitude : Nat
  unit      : SemanticUnit
  deriving Repr, BEq, DecidableEq

/--
Target-specific representation semantics.

The semantic value type and raw target type are parameters so future hardware
generations may choose different target encodings without changing the
target-neutral value.
-/
structure RepresentationModel (SemanticValue Raw : Type) where
  encode : SemanticValue → Option Raw

/--
A raw payload matches the target representation model when the independent
model encodes the semantic value to exactly that payload.
-/
def representationMatches
    {SemanticValue Raw : Type}
    (model : RepresentationModel SemanticValue Raw)
    (value : SemanticValue)
    (raw : Raw) : Prop :=
  model.encode value = some raw

/-- Executable representation checker. -/
def checkRepresentation
    {SemanticValue Raw : Type}
    [DecidableEq Raw]
    (model : RepresentationModel SemanticValue Raw)
    (value : SemanticValue)
    (raw : Raw) : Bool :=
  decide (model.encode value = some raw)

/--
The executable checker is sound and complete for the representation relation
that GREEN-2 actually claims.
-/
theorem checkRepresentation_true_iff
    {SemanticValue Raw : Type}
    [DecidableEq Raw]
    (model : RepresentationModel SemanticValue Raw)
    (value : SemanticValue)
    (raw : Raw) :
    checkRepresentation model value raw = true ↔
      representationMatches model value raw := by
  simp [checkRepresentation, representationMatches]

/--
The target-neutral value used by the RED-2 / GREEN-2 witness.

No PVM32 address, scaling factor, or raw payload appears here.
-/
def setpoint25C : SemanticQuantity :=
  { magnitude := 25
  , unit := .celsius }

/--
PVM32 target-specific representation model for the witness.

This target represents supported Celsius values as fixed-point ×10. Fahrenheit
is intentionally unsupported in this minimal model.

The scaling factor belongs here, at the target representation boundary.
-/
def pvm32SetpointRepresentation :
    RepresentationModel SemanticQuantity Nat :=
  { encode := fun value =>
      match value.unit with
      | .celsius    => some (value.magnitude * 10)
      | .fahrenheit => none }

/--
Compose GREEN-1 resource correctness with GREEN-2 representation correctness.

The resource and representation checks remain separate: binding correctness
does not imply representation correctness, and vice versa.
-/
def green2CandidateGate
    {Resource SemanticValue : Type}
    (device : DeviceModel Resource)
    (representation : RepresentationModel SemanticValue Nat)
    (semanticId : SemanticId)
    (semanticValue : SemanticValue)
    (candidate : CandidateWrite Resource) : Bool :=
  green1CandidateGate device semanticId candidate &&
    checkRepresentation representation semanticValue candidate.rawValue

theorem green2_reference_representation_accepts :
    checkRepresentation
      pvm32SetpointRepresentation
      setpoint25C
      referenceSetpointWrite.rawValue = true := by
  native_decide

theorem green2_wrong_scale_representation_rejects :
    checkRepresentation
      pvm32SetpointRepresentation
      setpoint25C
      wrongScaleSetpointWrite.rawValue = false := by
  native_decide

/--
GREEN-2 closes exactly the RED-2 witness:

* both candidates still use the same GREEN-1-correct resource;
* the target representation model maps semantic 25 °C to raw 250;
* the composed checker accepts the reference candidate;
* the same checker rejects the wrong-scale candidate.
-/
theorem green2_separates_red2_witness :
    referenceSetpointWrite.resource =
      wrongScaleSetpointWrite.resource ∧
    green1CandidateGate
      pvm32Green1DeviceModel
      statusIdentity
      referenceSetpointWrite = true ∧
    green1CandidateGate
      pvm32Green1DeviceModel
      statusIdentity
      wrongScaleSetpointWrite = true ∧
    green2CandidateGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      statusIdentity
      setpoint25C
      referenceSetpointWrite = true ∧
    green2CandidateGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      statusIdentity
      setpoint25C
      wrongScaleSetpointWrite = false := by
  native_decide

/--
Any payload accepted by checkRepresentation satisfies the stated target
representation relation. The realization generator itself is not trusted for
that claim.
-/
theorem green2_checked_representation_is_model_faithful
    {SemanticValue Raw : Type}
    [DecidableEq Raw]
    (model : RepresentationModel SemanticValue Raw)
    (value : SemanticValue)
    (raw : Raw)
    (hcheck : checkRepresentation model value raw = true) :
    representationMatches model value raw :=
  (checkRepresentation_true_iff model value raw).mp hcheck

end PSL
