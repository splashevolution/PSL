import Lake
open Lake DSL

package «PSL» where
  name := "PSL"

lean_lib «PSL» where
  roots := #[`PSL.Semantics]
