import Std.Tactic

/-
  PSL/Semantics.lean
  Pāṇinian Systems Language — Formal Semantics (Lean 4)

  This file encodes the complete PSL type system as Lean 4 definitions.
  It is the formal counterpart of src/utils/paninian_compiler.py.

  Structure:
    §1  ABI word type and field extractors
    §2  IRNode type (Prakriya layer)
    §3  Machine state (State Transition Semantics)
    §4  Compilation phases as pure functions
    §5  Paribhāṣā predicates (P1–P4b)
    §6  Lowering invariants (L1, L2)
    §7  Sañjñā identity predicate
    §8  State transition relation
    §9  Step-level safety theorems (closed)
    §10 compiler-soundness target — explicitly open

  CompCert correspondence:
    Clight  ≅  PSL source (.pvm)
    Cminor  ≅  IRNode list (Prakriya IR)
    RTL     ≅  ABI word list (32-bit big-endian binary)
    compile_correct  ≅  intended future refinement theorem (§10; not yet proved)
-/

-- ─────────────────────────────────────────────────────────────────────────────
-- §1  ABI Word Type
-- ─────────────────────────────────────────────────────────────────────────────

structure ABIWord where
  ring   : Fin 16
  comp   : Fin 16
  opcode : Fin 256
  target : Fin 256
  flags  : Fin 16
  cond   : Fin 16
  deriving Repr, BEq

def ABIWord.toNat (w : ABIWord) : Nat :=
  (w.ring.val <<< 28) ||| (w.comp.val <<< 24) |||
  (w.opcode.val <<< 16) ||| (w.target.val <<< 8) |||
  (w.flags.val <<< 4) ||| w.cond.val

def OP_LOPA  : Fin 256 := ⟨0x00, by decide⟩
def OP_WRITE : Fin 256 := ⟨0x05, by decide⟩
def OP_READ  : Fin 256 := ⟨0x06, by decide⟩
def OP_STORE : Fin 256 := ⟨0xCC, by decide⟩
def OP_OPEN  : Fin 256 := ⟨0xAA, by decide⟩
def OP_CLOSE : Fin 256 := ⟨0xBB, by decide⟩

def ASIDDHA_BASE : Nat := 0x50

-- ─────────────────────────────────────────────────────────────────────────────
-- §2  IRNode Type (Prakriya Layer)
-- ─────────────────────────────────────────────────────────────────────────────

inductive Region where
  | Siddha  : Region
  | Asiddha : Region
  deriving Repr, BEq

def classify (addr : Nat) : Region :=
  if addr < ASIDDHA_BASE then .Siddha else .Asiddha

structure IRNode where
  ring        : Fin 16
  comp        : Fin 16
  opcode      : Fin 256
  target      : Option (Fin 256)
  cond        : Fin 16
  flags       : Fin 16
  in_adhikara : Bool
  sandhi_fused: Bool
  deriving Repr, BEq

def IRNode.lower (n : IRNode) : ABIWord :=
  let t     := n.target.map Fin.val |>.getD 0x00
  let flags := if n.sandhi_fused then 0x0E else n.flags.val
  { ring   := n.ring
  , comp   := n.comp
  , opcode := n.opcode
  , target := ⟨t, by omega⟩
  , flags  := ⟨flags % 16, by omega⟩
  , cond   := n.cond }

-- ─────────────────────────────────────────────────────────────────────────────
-- §3  Machine State
-- ─────────────────────────────────────────────────────────────────────────────

structure MachineState where
  mem     : Nat → Nat
  ring    : Nat
  written : Nat → Bool
  halted  : Bool
  deriving Repr

def MachineState.initial : MachineState :=
  { mem     := fun _ => 0
  , ring    := 2
  , written := fun _ => false
  , halted  := false }

-- ─────────────────────────────────────────────────────────────────────────────
-- §4  Compilation Phases
-- ─────────────────────────────────────────────────────────────────────────────

def lowerAll (ir : List IRNode) : List ABIWord :=
  ir.map IRNode.lower

def sanjnaaEquiv (ir1 ir2 : List IRNode) : Prop :=
  lowerAll ir1 = lowerAll ir2

-- ─────────────────────────────────────────────────────────────────────────────
-- §5  Paribhāṣā Predicates (P1–P4b)
-- ─────────────────────────────────────────────────────────────────────────────

def isAnuvrtti (n : IRNode) : Bool :=
  n.comp.val == 1 && n.target.isNone

def isSentinel (n : IRNode) : Bool :=
  n.opcode == OP_OPEN || n.opcode == OP_CLOSE

def p1_ok (ir : List IRNode) : Prop :=
  match ir.filter (fun n => !isSentinel n) with
  | []     => True
  | n :: _ => !isAnuvrtti n

def p2_ok (ir : List IRNode) : Prop :=
  let rec check (remaining : List IRNode) (written : Finset Nat) : Prop :=
    match remaining with
    | []      => True
    | n :: ns =>
        let tgt := n.target.map Fin.val
        let lopa_ok : Prop :=
          if n.opcode == OP_LOPA && n.comp.val ≠ 1 then
            match tgt with
            | none   => True
            | some a => a ∈ written
          else True
        let written' : Finset Nat :=
          match tgt with
          | none   => written
          | some a =>
            if n.opcode == OP_WRITE || n.opcode == OP_STORE then
              written ∪ {a}
            else if n.opcode == OP_LOPA then
              written.erase a
            else written
        lopa_ok ∧ check ns written'
  check ir ∅

def p3_ok (ir : List IRNode) : Prop :=
  ∀ n ∈ ir,
    n.ring.val == 0 →
    n.comp.val ≠ 1 →
    (n.target.map Fin.val).getD 0x00 ≠ 0x00 →
    (n.target.map Fin.val).getD 0x00 ≥ ASIDDHA_BASE

def p4_ok (ir : List IRNode) : Prop :=
  ∀ n ∈ ir,
    n.ring.val == 0 →
    ¬isSentinel n →
    n.in_adhikara

def p4b_ok (ir : List IRNode) : Prop :=
  ∀ n ∈ ir,
    (n.opcode == OP_STORE || n.opcode == OP_LOPA) →
    (n.target.map Fin.val).getD 0x00 ≥ ASIDDHA_BASE →
    n.in_adhikara

def paribhasha_ok (ir : List IRNode) : Prop :=
  p1_ok ir ∧ p2_ok ir ∧ p3_ok ir ∧ p4_ok ir ∧ p4b_ok ir

-- ─────────────────────────────────────────────────────────────────────────────
-- §6  Lowering Invariants (L1, L2)
-- ─────────────────────────────────────────────────────────────────────────────

theorem L1_lower_deterministic (n : IRNode) :
    IRNode.lower n = IRNode.lower n := rfl

theorem L2_lower_length_preserving (ir : List IRNode) :
    (lowerAll ir).length = ir.length := by
  simp [lowerAll]

theorem lowerAll_binary_eq (ir1 ir2 : List IRNode)
    (h : lowerAll ir1 = lowerAll ir2) :
    ∀ i, (lowerAll ir1).get? i = (lowerAll ir2).get? i := by
  intro i; rw [h]

-- ─────────────────────────────────────────────────────────────────────────────
-- §7  Sañjñā Identity Theorem
-- ─────────────────────────────────────────────────────────────────────────────

theorem sanjnaa_identity_is_binary_identity
    (ir_named ir_direct : List IRNode)
    (h : sanjnaaEquiv ir_named ir_direct) :
    lowerAll ir_named = lowerAll ir_direct := h

-- ─────────────────────────────────────────────────────────────────────────────
-- §8  State Transition Relation
-- ─────────────────────────────────────────────────────────────────────────────

def step (s : MachineState) (w : ABIWord) : Option MachineState :=
  if s.halted then none
  else
    let tgt := w.target.val
    match w.opcode with
    | ⟨0x05, _⟩ =>
      if tgt < ASIDDHA_BASE then
        some { s with
          mem     := fun a => if a == tgt then 1 else s.mem a
          written := fun a => if a == tgt then true else s.written a }
      else none
    | ⟨0xCC, _⟩ =>
      if s.ring == 0 && tgt ≥ ASIDDHA_BASE then
        some { s with
          mem     := fun a => if a == tgt then 1 else s.mem a
          written := fun a => if a == tgt then true else s.written a }
      else none
    | ⟨0x00, _⟩ =>
      if s.ring == 0 && (w.comp.val == 1 || s.written tgt) then
        some { s with
          mem     := fun a => if a == tgt then 0 else s.mem a
          written := fun a => if a == tgt then false else s.written a }
      else none
    | ⟨0xAA, _⟩ => some { s with ring := 0 }
    | ⟨0xBB, _⟩ => some { s with ring := 2 }
    | _          => some s

def execute (words : List ABIWord) (s0 : MachineState) : Option MachineState :=
  words.foldlM step s0

-- ─────────────────────────────────────────────────────────────────────────────
-- §9  Step-level Safety Theorems (closed)
-- ─────────────────────────────────────────────────────────────────────────────

theorem lopa_requires_prior_write
    (s : MachineState) (w : ABIWord)
    (hring       : s.ring = 0)
    (hnotwritten : ¬s.written w.target.val)
    (hcomp       : w.comp.val ≠ 1) :
    w.opcode = OP_LOPA →
    step s w = none := by
  intro hop
  simp [step, hop, OP_LOPA, hring, hcomp, hnotwritten]

theorem write_to_asiddha_fails
    (s : MachineState) (w : ABIWord)
    (htgt : w.target.val ≥ ASIDDHA_BASE) :
    w.opcode = OP_WRITE →
    step s w = none := by
  intro hop
  simp [step, hop, OP_WRITE, ASIDDHA_BASE]
  omega

theorem open_close_ring_identity (s : MachineState) (hh : s.halted = false) :
    let w_open  : ABIWord :=
      { ring := ⟨0, by decide⟩, comp := ⟨0, by decide⟩, opcode := OP_OPEN
      , target := ⟨0, by decide⟩, flags := ⟨0xF, by decide⟩, cond := ⟨0, by decide⟩ }
    let w_close : ABIWord :=
      { ring := ⟨0, by decide⟩, comp := ⟨0, by decide⟩, opcode := OP_CLOSE
      , target := ⟨0, by decide⟩, flags := ⟨0xF, by decide⟩, cond := ⟨0, by decide⟩ }
    (step s w_open >>= fun s1 => step s1 w_close).map (·.ring) = some s.ring := by
  simp [step, OP_OPEN, OP_CLOSE, hh]

-- ─────────────────────────────────────────────────────────────────────────────
-- §10  Compiler Soundness — Open Proof Obligation
-- ─────────────────────────────────────────────────────────────────────────────

/-
  IMPORTANT VERIFICATION BOUNDARY

  Earlier revisions presented a theorem named `compile_sound_statement` here.
  That argument depended on an explicit project axiom
  `p2_runtime_correctness` and, more importantly, had not been exercised by a
  real Lake build. The first CI-backed typecheck exposed additional proof errors.

  We therefore remove the axiom and the unverified theorem rather than weakening
  Lean's trust boundary.

  The proposition below records the research target without claiming a proof.
  Future work must establish a forward simulation relating:
    1. compile-time P2 written-target tracking,
    2. runtime MachineState.written,
    3. Adhikāra/ring state, and
    4. the actual semantics of inherited (Anuvṛtti) targets.

  Only after those relations are formalized should this proposition be promoted
  to a theorem.
-/

/-- Intended compiler-soundness statement. This is a proposition, not a theorem. -/
def CompilerSoundnessGoal : Prop :=
  ∀ (ir : List IRNode),
    paribhasha_ok ir →
    ∃ (s_final : MachineState),
      execute (lowerAll ir) MachineState.initial = some s_final

/-- The empty program executes successfully in the current abstract machine. -/
theorem empty_program_executes :
    execute (lowerAll []) MachineState.initial = some MachineState.initial := by
  rfl

-- End of PSL/Semantics.lean
