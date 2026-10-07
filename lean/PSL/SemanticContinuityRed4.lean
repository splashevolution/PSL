import PSL.SemanticContinuityGreen3

namespace PSL

/-
  Semantic Continuity RED-4
  -------------------------

  GREEN-3 established:
    * binding correctness relative to a DeviceModel,
    * representation correctness relative to a RepresentationModel, and
    * protocol-sequence correctness relative to a ProtocolModel.

  RED-4 asks whether that is enough to establish that the intended device
  effect was actually observed.

  It is not.

  Two candidate outcomes may contain the exact same GREEN-3-valid execution
  while differing only in externally reported observation. GREEN-3 has no
  observation/effect relation, so both outcomes pass its strongest current
  gate.

  This file deliberately does NOT introduce observation semantics. It records
  the next missing relation.
-/

/--
A minimal post-execution outcome.

The execution is the object already checked by GREEN-3. The observation is kept
separate so RED-4 can show that GREEN-3 does not inspect it.

RawObservation is generic because different targets may expose different
observable state.
-/
structure CandidateOutcome (Resource RawObservation : Type) where
  execution   : CandidateExecution Resource
  observation : Option RawObservation
  deriving Repr, BEq, DecidableEq

/--
Lift the strongest GREEN-3 gate to an outcome.

The observation is intentionally ignored because GREEN-3 has no observation or
effect model. That omission is the property RED-4 is testing.
-/
def green3OutcomeGate
    {Resource SemanticValue State Step RawObservation : Type}
    (device : DeviceModel Resource)
    (representation : RepresentationModel SemanticValue Nat)
    (protocol : ProtocolModel State Step)
    (semanticId : SemanticId)
    (semanticValue : SemanticValue)
    (traceOf : CandidateExecution Resource → List Step)
    (outcome : CandidateOutcome Resource RawObservation) : Bool :=
  green3ExecutionGate
    device
    representation
    protocol
    semanticId
    semanticValue
    outcome.execution
    traceOf

/--
Reference outcome for the RED-4 witness.

The raw observation 250 is only an experiment fixture at RED-4. The current
theory does not yet state why this observation demonstrates the intended
semantic effect.
-/
def referenceObservedOutcome : CandidateOutcome (Fin 256) Nat :=
  { execution := referenceSetpointExecution
  , observation := some 250 }

/--
Mutation that keeps the exact same GREEN-3-valid execution but provides no
post-execution observation.
-/
def missingObservationOutcome : CandidateOutcome (Fin 256) Nat :=
  { execution := referenceSetpointExecution
  , observation := none }

theorem red4_executions_are_identical :
    referenceObservedOutcome.execution =
      missingObservationOutcome.execution := by
  native_decide

theorem red4_observations_are_distinct :
    referenceObservedOutcome.observation ≠
      missingObservationOutcome.observation := by
  native_decide

theorem red4_reference_outcome_passes_green3 :
    green3OutcomeGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      pvm32SetpointProtocol
      statusIdentity
      setpoint25C
      red3ProtocolTrace
      referenceObservedOutcome = true := by
  native_decide

theorem red4_missing_observation_also_passes_green3 :
    green3OutcomeGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      pvm32SetpointProtocol
      statusIdentity
      setpoint25C
      red3ProtocolTrace
      missingObservationOutcome = true := by
  native_decide

/--
RED-4 result.

The two outcomes contain the same GREEN-3-valid execution but differ in
post-execution observation. Since GREEN-3 has no observation/effect semantics,
both pass.

The theorem deliberately does not assert that raw 250 proves the intended
semantic effect. That relation is exactly what is missing and what GREEN-4 must
add.
-/
theorem red4_green3_is_observation_blind :
    referenceObservedOutcome.execution =
      missingObservationOutcome.execution ∧
    referenceObservedOutcome.observation ≠
      missingObservationOutcome.observation ∧
    green3OutcomeGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      pvm32SetpointProtocol
      statusIdentity
      setpoint25C
      red3ProtocolTrace
      referenceObservedOutcome = true ∧
    green3OutcomeGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      pvm32SetpointProtocol
      statusIdentity
      setpoint25C
      red3ProtocolTrace
      missingObservationOutcome = true := by
  native_decide

end PSL
