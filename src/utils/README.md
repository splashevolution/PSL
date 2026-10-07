# Utility code status

`paninian_compiler.py` is a **legacy compatibility compiler** retained because
the repaired regression and Python-to-Lean conformance baseline depends on its
exact behavior.

Its class names, exception names, source tokens, and internal historical
terminology are frozen compatibility vocabulary. They are not the naming model
for new PSL research.

Do not add new semantic-continuity features to this compiler merely to make the
new theory fit the old DSL. New formal work should define neutral semantic
contracts and realization evidence independently, then use the legacy PVM32
path only as one compatibility realization where useful.
