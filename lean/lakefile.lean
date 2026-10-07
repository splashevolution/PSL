import Lake
open Lake DSL

package «PSL»

@[default_target]
lean_lib «PSL» where
  roots := #[`PSL.SemanticKernel, `PSL.Semantics, `PSL.PVM32Driver]
