import PSL.Semantics
import PSL.PVM32Driver
import PSL.SemanticContinuityRed1
import PSL.SemanticContinuityGreen1
import PSL.SemanticContinuityRed2
import PSL.SemanticContinuityGreen2
import PSL.SemanticContinuityRed3

#print axioms validateIRClosed_sound
#print axioms validateWords_execution
#print axioms validated_ir_executes
#print axioms valid_program_executes
#print axioms certified_ir_executes
#print axioms PSL.status_script_realizes_on_pvm32

#print axioms PSL.red1_bindings_are_distinct
#print axioms PSL.red1_capability_gate_is_binding_blind

#print axioms PSL.checkBinding_true_iff
#print axioms PSL.green1_separates_red1_witness
#print axioms PSL.green1_checked_binding_is_model_faithful

#print axioms PSL.red2_same_resource
#print axioms PSL.red2_green1_is_representation_blind

#print axioms PSL.checkRepresentation_true_iff
#print axioms PSL.green2_separates_red2_witness
#print axioms PSL.green2_checked_representation_is_model_faithful

#print axioms PSL.red3_writes_are_identical
#print axioms PSL.red3_green2_is_protocol_blind
