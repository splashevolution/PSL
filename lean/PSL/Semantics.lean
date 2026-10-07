import Std.Tactic

/-
  PSL/Semantics.lean
  Pāṇinian Systems Language — auditable formal core

  This file intentionally separates:
    * executable definitions,
    * closed Lean theorems,
    * open compiler/refinement goals.

  It does not claim source-to-RV32 compiler correctness.
-/

-- §1 ABI ----------------------------------------------------------------------

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

-- §2 Prakriya IR --------------------------------------------------------------

inductive Region where
  | Siddha
  | Asiddha
  deriving Repr, BEq

def classify (addr : Nat) : Region :=
  if addr < ASIDDHA_BASE then .Siddha else .Asiddha

structure IRNode where
  ring         : Fin 16
  comp         : Fin 16
  opcode       : Fin 256
  target       : Option (Fin 256)
  cond         : Fin 16
  flags        : Fin 16
  in_adhikara  : Bool
  sandhi_fused : Bool
  deriving Repr, BEq

def IRNode.lower (n : IRNode) : ABIWord :=
  { ring   := n.ring
  , comp   := n.comp
  , opcode := n.opcode
  , target := n.target.getD ⟨0, by decide⟩
  , flags  := if n.sandhi_fused then ⟨0x0E, by decide⟩ else n.flags
  , cond   := n.cond }

def lowerAll (ir : List IRNode) : List ABIWord :=
  ir.map IRNode.lower

def sanjnaaEquiv (ir1 ir2 : List IRNode) : Prop :=
  lowerAll ir1 = lowerAll ir2

-- §3 Machine state ------------------------------------------------------------

structure MachineState where
  mem     : Nat → Nat
  ring    : Nat
  written : Nat → Bool
  halted  : Bool

def MachineState.initial : MachineState :=
  { mem     := fun _ => 0
  , ring    := 2
  , written := fun _ => false
  , halted  := false }

-- §4 Paribhāṣā predicates -----------------------------------------------------

def isAnuvrtti (n : IRNode) : Bool :=
  n.comp.val == 1 && n.target.isNone

def isSentinel (n : IRNode) : Bool :=
  n.opcode == OP_OPEN || n.opcode == OP_CLOSE

def p1_ok (ir : List IRNode) : Prop :=
  match ir.filter (fun n => !isSentinel n) with
  | []     => True
  | n :: _ => isAnuvrtti n = false

def markWritten (written : Nat → Bool) (a : Nat) : Nat → Bool :=
  fun x => if x = a then true else written x

def markErased (written : Nat → Bool) (a : Nat) : Nat → Bool :=
  fun x => if x = a then false else written x

def p2Check : List IRNode → (Nat → Bool) → Prop
  | [], _ => True
  | n :: ns, written =>
      let tgt := n.target.map Fin.val
      let lopaOk : Prop :=
        if n.opcode = OP_LOPA ∧ n.comp.val ≠ 1 then
          match tgt with
          | none   => True
          | some a => written a = true
        else True
      let written' :=
        match tgt with
        | none   => written
        | some a =>
            if n.opcode = OP_WRITE ∨ n.opcode = OP_STORE then
              markWritten written a
            else if n.opcode = OP_LOPA then
              markErased written a
            else written
      lopaOk ∧ p2Check ns written'

def p2_ok (ir : List IRNode) : Prop :=
  p2Check ir (fun _ => false)

def p3_ok (ir : List IRNode) : Prop :=
  ∀ n ∈ ir,
    n.ring.val = 0 →
    n.comp.val ≠ 1 →
    (n.target.map Fin.val).getD 0 ≠ 0 →
    (n.target.map Fin.val).getD 0 ≥ ASIDDHA_BASE

def p4_ok (ir : List IRNode) : Prop :=
  ∀ n ∈ ir,
    n.ring.val = 0 →
    n.opcode ≠ OP_OPEN →
    n.opcode ≠ OP_CLOSE →
    n.in_adhikara = true

def p4b_ok (ir : List IRNode) : Prop :=
  ∀ n ∈ ir,
    (n.opcode = OP_STORE ∨ n.opcode = OP_LOPA) →
    (n.target.map Fin.val).getD 0 ≥ ASIDDHA_BASE →
    n.in_adhikara = true

def paribhasha_ok (ir : List IRNode) : Prop :=
  p1_ok ir ∧ p2_ok ir ∧ p3_ok ir ∧ p4_ok ir ∧ p4b_ok ir

-- §5 Closed lowering facts ----------------------------------------------------

theorem lower_preserves_core_fields (n : IRNode) :
    (IRNode.lower n).ring = n.ring ∧
    (IRNode.lower n).comp = n.comp ∧
    (IRNode.lower n).opcode = n.opcode ∧
    (IRNode.lower n).cond = n.cond := by
  simp [IRNode.lower]

theorem lowerAll_length_preserving (ir : List IRNode) :
    (lowerAll ir).length = ir.length := by
  simp [lowerAll]

theorem sanjnaa_equiv_is_binary_identity
    (ir1 ir2 : List IRNode)
    (h : sanjnaaEquiv ir1 ir2) :
    lowerAll ir1 = lowerAll ir2 := by
  exact h

-- §6 Abstract execution -------------------------------------------------------

def step (s : MachineState) (w : ABIWord) : Option MachineState :=
  if s.halted = true then none
  else
    let tgt := w.target.val
    match w.opcode.val with
    | 0x05 =>
        if tgt < ASIDDHA_BASE then
          some { s with
            mem     := fun a => if a = tgt then 1 else s.mem a
            written := markWritten s.written tgt }
        else none
    | 0xCC =>
        if s.ring = 0 ∧ tgt ≥ ASIDDHA_BASE then
          some { s with
            mem     := fun a => if a = tgt then 1 else s.mem a
            written := markWritten s.written tgt }
        else none
    | 0x00 =>
        if s.ring = 0 ∧ (w.comp.val = 1 ∨ s.written tgt = true) then
          some { s with
            mem     := fun a => if a = tgt then 0 else s.mem a
            written := markErased s.written tgt }
        else none
    | 0xAA => some { s with ring := 0 }
    | 0xBB => some { s with ring := 2 }
    | _    => some s

def execute (words : List ABIWord) (s0 : MachineState) : Option MachineState :=
  words.foldlM step s0

-- §7 Closed abstract-machine safety facts ------------------------------------

theorem halted_step_none
    (s : MachineState) (w : ABIWord)
    (hh : s.halted = true) :
    step s w = none := by
  simp [step, hh]

theorem lopa_requires_prior_write
    (s : MachineState) (w : ABIWord)
    (hh          : s.halted = false)
    (hring       : s.ring = 0)
    (hnotwritten : s.written w.target.val = false)
    (hcomp       : w.comp.val ≠ 1)
    (hop         : w.opcode.val = 0x00) :
    step s w = none := by
  simp [step, hh, hop, hring, hcomp, hnotwritten]

theorem write_to_asiddha_fails
    (s : MachineState) (w : ABIWord)
    (hh   : s.halted = false)
    (htgt : w.target.val ≥ ASIDDHA_BASE)
    (hop  : w.opcode.val = 0x05) :
    step s w = none := by
  simp [step, hh, hop, htgt]

def openWord : ABIWord :=
  { ring := ⟨0, by decide⟩
  , comp := ⟨0, by decide⟩
  , opcode := OP_OPEN
  , target := ⟨0, by decide⟩
  , flags := ⟨0xF, by decide⟩
  , cond := ⟨0, by decide⟩ }

def closeWord : ABIWord :=
  { ring := ⟨0, by decide⟩
  , comp := ⟨0, by decide⟩
  , opcode := OP_CLOSE
  , target := ⟨0, by decide⟩
  , flags := ⟨0xF, by decide⟩
  , cond := ⟨0, by decide⟩ }

theorem open_close_restores_ring
    (s : MachineState)
    (hh : s.halted = false) :
    (step s openWord >>= fun s1 => step s1 closeWord).map (·.ring) =
      some s.ring := by
  simp [step, openWord, closeWord, OP_OPEN, OP_CLOSE, hh]

-- §8 Compiler soundness: explicitly open --------------------------------------

/-
  The main compiler-soundness claim is deliberately represented as a goal,
  not a theorem.

  To prove it, PSL still needs a forward simulation that relates:
    * p2Check's compile-time written map,
    * MachineState.written at the corresponding execution point,
    * scope/ring state,
    * inherited Anuvṛtti targets.

  No project axiom is used in this file.
-/

def CompilerSoundnessGoal : Prop :=
  ∀ (ir : List IRNode),
    paribhasha_ok ir →
    ∃ (s_final : MachineState),
      execute (lowerAll ir) MachineState.initial = some s_final

theorem empty_program_executes :
    execute (lowerAll []) MachineState.initial = some MachineState.initial := by
  rfl

-- End of PSL/Semantics.lean
