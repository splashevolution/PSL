import PSL.SemanticContinuityGreen2

namespace PSL

/-
  Semantic Continuity RED-3
  -------------------------

  GREEN-2 established binding correctness and representation correctness.
  RED-3 asks whether that boundary also establishes protocol/state correctness.

  It does not.

  Two candidate executions may use the same semantically correct resource and
  the same semantically correct raw representation while presenting different
  command/state traces. GREEN-2 has no protocol semantics, so both executions
  pass its strongest current gate.

  This file deliberately does NOT introduce a protocol automaton or execution
  semantics. It records the next missing relation.
-/

inductive ProtocolStep where
  | enterConfig
  | issueWrite
  | observeAck
  | exitConfig
  deriving Repr, BEq, DecidableEq

structure CandidateExecution (Resource : Type) where
  write : CandidateWrite Resource
  trace : List ProtocolStep
  deriving Repr, BEq, DecidableEq

/--
Lift the strongest GREEN-2 checker to an execution.

The trace is intentionally ignored because GREEN-2 has no protocol/state model.
That omission is the property RED-3 is testing.
-/
def green2ExecutionGate
    {Resource SemanticValue : Type}
    (device : DeviceModel Resource)
    (representation : RepresentationModel SemanticValue Nat)
    (semanticId : SemanticId)
    (semanticValue : SemanticValue)
    (execution : CandidateExecution Resource) : Bool :=
  green2CandidateGate
    device
    representation
    semanticId
    semanticValue
    execution.write

/--
Reference execution for the next falsification experiment.

The sequence is only a reference witness at RED-3. The current theory does not
yet prove that this trace is required or valid.
-/
def referenceSetpointExecution : CandidateExecution (Fin 256) :=
  { write := referenceSetpointWrite
  , trace :=
      [ .enterConfig
      , .issueWrite
      , .observeAck
      , .exitConfig ] }

/--
Mutation that keeps the exact same GREEN-2-correct write but omits the
configuration-state transitions.
-/
def missingConfigExecution : CandidateExecution (Fin 256) :=
  { write := referenceSetpointWrite
  , trace :=
      [ .issueWrite
      , .observeAck ] }

theorem red3_writes_are_identical :
    referenceSetpointExecution.write =
      missingConfigExecution.write := by
  native_decide

theorem red3_traces_are_distinct :
    referenceSetpointExecution.trace ≠
      missingConfigExecution.trace := by
  native_decide

theorem red3_reference_passes_green2 :
    green2ExecutionGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      statusIdentity
      setpoint25C
      referenceSetpointExecution = true := by
  native_decide

theorem red3_missing_config_also_passes_green2 :
    green2ExecutionGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      statusIdentity
      setpoint25C
      missingConfigExecution = true := by
  native_decide

/--
RED-3 result.

The two executions carry the same GREEN-2-correct write, but their protocol
traces differ. Since GREEN-2 has no protocol/state semantics, both pass.

The theorem deliberately does not assert which trace is valid. That relation is
exactly what is missing and what GREEN-3 must add.
-/
theorem red3_green2_is_protocol_blind :
    referenceSetpointExecution.write =
      missingConfigExecution.write ∧
    referenceSetpointExecution.trace ≠
      missingConfigExecution.trace ∧
    green2ExecutionGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      statusIdentity
      setpoint25C
      referenceSetpointExecution = true ∧
    green2ExecutionGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      statusIdentity
      setpoint25C
      missingConfigExecution = true := by
  native_decide

end PSL
