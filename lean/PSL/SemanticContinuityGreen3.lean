import PSL.SemanticContinuityRed3

namespace PSL

/-
  Semantic Continuity GREEN-3
  ---------------------------

  RED-3 showed that GREEN-2 is blind to protocol/state behavior: two candidate
  executions can carry the same correct resource and representation while
  differing only in their surrounding command trace.

  GREEN-3 adds the minimum missing relation: a target-specific transition model
  plus an executable trace checker.

  This closes only the RED-3 protocol-sequencing gap relative to the stated
  model. It does NOT yet establish persistence, timing, concrete I/O
  observations, simulator conformance, or physical-device conformance.
-/

/--
A target-specific protocol transition model.

The semantic contract does not contain these target states or transitions.
Different hardware generations may supply different State and Step types while
the target-neutral intent remains unchanged.
-/
structure ProtocolModel (State Step : Type) where
  initial    : State
  transition : State → Step → Option State
  accepting  : State → Bool

/-- Execute a protocol trace from an explicit state. -/
def runProtocol
    {State Step : Type}
    (model : ProtocolModel State Step) :
    State → List Step → Option State
  | state, [] => some state
  | state, event :: rest =>
      match model.transition state event with
      | none => none
      | some next => runProtocol model next rest

/--
Formal acceptance relation for the target protocol model.

A trace is accepted when all transitions are defined and the resulting state
is marked accepting.
-/
def protocolAccepts
    {State Step : Type}
    (model : ProtocolModel State Step)
    (trace : List Step) : Prop :=
  match runProtocol model model.initial trace with
  | none => False
  | some finalState => model.accepting finalState = true

/-- Executable protocol checker. -/
def checkProtocol
    {State Step : Type}
    (model : ProtocolModel State Step)
    (trace : List Step) : Bool :=
  match runProtocol model model.initial trace with
  | none => false
  | some finalState => model.accepting finalState

/--
The executable checker is sound and complete for the protocol relation that
GREEN-3 actually states.
-/
theorem checkProtocol_true_iff
    {State Step : Type}
    (model : ProtocolModel State Step)
    (trace : List Step) :
    checkProtocol model trace = true ↔
      protocolAccepts model trace := by
  unfold checkProtocol protocolAccepts
  cases hrun : runProtocol model model.initial trace with
  | none => simp [hrun]
  | some finalState => simp [hrun]

-- PVM32 witness ---------------------------------------------------------------

/--
Minimal target-specific states needed to close the RED-3 witness.

These states belong to the target protocol model, not to the target-neutral
semantic quantity or semantic identity.
-/
inductive PVM32ProtocolState where
  | operational
  | config
  | awaitingAck
  deriving Repr, BEq, DecidableEq

/--
State-machine semantics for the RED-3 witness.

This is intentionally a transition relation, not a hard-coded comparison
against one accepted trace:

  operational --enterConfig--> config
  config      --issueWrite--> awaitingAck
  awaitingAck --observeAck--> config
  config      --exitConfig--> operational

Every other transition fails closed.
-/
def pvm32SetpointProtocol :
    ProtocolModel PVM32ProtocolState ProtocolStep :=
  { initial := .operational
  , transition := fun state event =>
      match state, event with
      | .operational, .enterConfig => some .config
      | .config, .issueWrite       => some .awaitingAck
      | .awaitingAck, .observeAck  => some .config
      | .config, .exitConfig       => some .operational
      | _, _                       => none
  , accepting := fun state =>
      match state with
      | .operational => true
      | _            => false }

/--
Compose GREEN-2 resource/representation checking with GREEN-3 protocol
checking. The obligations remain separate.
-/
def green3ExecutionGate
    {Resource SemanticValue State Step : Type}
    (device : DeviceModel Resource)
    (representation : RepresentationModel SemanticValue Nat)
    (protocol : ProtocolModel State Step)
    (semanticId : SemanticId)
    (semanticValue : SemanticValue)
    (execution : CandidateExecution Resource)
    (traceOf : CandidateExecution Resource → List Step) : Bool :=
  green2ExecutionGate
      device
      representation
      semanticId
      semanticValue
      execution &&
    checkProtocol protocol (traceOf execution)

/--
Specialized trace projection for the RED-3 witness.
-/
def red3ProtocolTrace
    (execution : CandidateExecution (Fin 256)) : List ProtocolStep :=
  execution.trace

theorem green3_reference_protocol_accepts :
    checkProtocol
      pvm32SetpointProtocol
      referenceSetpointExecution.trace = true := by
  native_decide

theorem green3_missing_config_protocol_rejects :
    checkProtocol
      pvm32SetpointProtocol
      missingConfigExecution.trace = false := by
  native_decide

/--
GREEN-3 closes exactly the RED-3 counterexample:

* both executions still carry the same GREEN-2-correct write;
* GREEN-2 therefore accepts both;
* the target transition model accepts the reference trace;
* the same model rejects the missing-configuration trace.
-/
theorem green3_separates_red3_witness :
    referenceSetpointExecution.write =
      missingConfigExecution.write ∧
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
      missingConfigExecution = true ∧
    green3ExecutionGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      pvm32SetpointProtocol
      statusIdentity
      setpoint25C
      referenceSetpointExecution
      red3ProtocolTrace = true ∧
    green3ExecutionGate
      pvm32Green1DeviceModel
      pvm32SetpointRepresentation
      pvm32SetpointProtocol
      statusIdentity
      setpoint25C
      missingConfigExecution
      red3ProtocolTrace = false := by
  native_decide

/--
Any trace accepted by checkProtocol satisfies the stated target transition
relation. The realization generator itself is not trusted for that claim.
-/
theorem green3_checked_protocol_is_model_faithful
    {State Step : Type}
    (model : ProtocolModel State Step)
    (trace : List Step)
    (hcheck : checkProtocol model trace = true) :
    protocolAccepts model trace :=
  (checkProtocol_true_iff model trace).mp hcheck

end PSL
