# Historical PSL program fixtures

These files preserve pre-verification-repair examples exactly as they existed
before the October 2026 semantic reconciliation.

They are retained for provenance and regression archaeology. They are **not**
authorities for the current PSL language contract.

Known reasons for archival:

- `lopa_core`: allowed a post-Lopa Anuvrtti instruction to reach firmware;
  canonical PSL now rejects it structurally because Lopa clears context.
- `sandhi_core`: paired a Ring-2 WRITE with a Store outside Adhikara; later
  privilege rules make Store a scoped Ring-0 operation.
- `paribhasha_valid_core`: predates P4 and therefore called an unscoped
  privileged Store "valid".
- `key_lifecycle`: used inherited Lopa immediately after explicit Lopa;
  canonical PSL now treats Lopa as a hard inheritance boundary.

Do not use these fixtures as current positive conformance tests.
