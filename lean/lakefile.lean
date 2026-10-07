import Lake
open Lake DSL

package «PSL»

@[default_target]
lean_lib «PSL» where
  roots := #[`PSL.SemanticKernel, `PSL.Semantics, `PSL.PVM32Driver, `PSL.SemanticContinuityRed1, `PSL.SemanticContinuityGreen1, `PSL.SemanticContinuityRed2, `PSL.SemanticContinuityGreen2, `PSL.SemanticContinuityRed3, `PSL.SemanticContinuityGreen3, `PSL.SemanticContinuityRed4]
