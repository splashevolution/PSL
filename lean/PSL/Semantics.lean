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

-- §2.1 Numeric ABI decoder -----------------------------------------------------

def fin16 (n : Nat) : Fin 16 :=
  ⟨n % 16, Nat.mod_lt _ (by decide)⟩

def fin256 (n : Nat) : Fin 256 :=
  ⟨n % 256, Nat.mod_lt _ (by decide)⟩

/-- Decode the low 32 bits of a numeric ABI word into PSL fields. -/
def decodeABIWord (n : Nat) : ABIWord :=
  { ring   := fin16  (n / 0x10000000)
  , comp   := fin16  (n / 0x01000000)
  , opcode := fin256 (n / 0x00010000)
  , target := fin256 (n / 0x00000100)
  , flags  := fin16  (n / 0x00000010)
  , cond   := fin16  n }

theorem decode_known_word_roundtrip :
    ABIWord.toNat (decodeABIWord 0x200530F0) = 0x200530F0 := by
  native_decide

-- §3 Canonical control state ----------------------------------------------------

/-
  Ring is an instruction attribute in the PSL ABI, not mutable global state.
  Runtime control state therefore tracks only the information that flows
  between instructions: written targets, Anuvrtti context, and Adhikara depth.
-/

structure ControlState where
  written       : Nat → Bool
  contextTarget : Option Nat
  scopeDepth    : Nat

def ControlState.initial : ControlState :=
  { written       := fun _ => false
  , contextTarget := none
  , scopeDepth    := 0 }

def markWritten (written : Nat → Bool) (a : Nat) : Nat → Bool :=
  fun x => if x = a then true else written x

def markErased (written : Nat → Bool) (a : Nat) : Nat → Bool :=
  fun x => if x = a then false else written x

/-- Resolve the effective ABI target. COMP=1 inherits live context. -/
def resolveTarget (c : ControlState) (w : ABIWord) : Option Nat :=
  if w.comp.val = 1 then c.contextTarget else some w.target.val

def isExecutableOpcode (w : ABIWord) : Bool :=
  w.opcode == OP_WRITE ||
  w.opcode == OP_READ ||
  w.opcode == OP_STORE ||
  w.opcode == OP_LOPA

/-
  Canonical control transition.

  This mirrors the repaired Python validator:
    * Anuvrtti requires live context.
    * Lopa requires a live write and clears inheritance context.
    * Ring-0 may resolve only to Asiddha and only inside Adhikara.
    * Store always requires Adhikara and Ring-0.
    * Asiddha Lopa requires Adhikara and Ring-0.
    * Ring-2 Write may target either region; visibility is a memory-model issue.
-/
def controlStep (c : ControlState) (w : ABIWord) : Option ControlState :=
  if w.opcode = OP_OPEN then
    some { c with scopeDepth := c.scopeDepth + 1 }
  else if w.opcode = OP_CLOSE then
    if c.scopeDepth = 0 then none
    else some { c with scopeDepth := c.scopeDepth - 1 }
  else if isExecutableOpcode w = false then
    none
  else
    match resolveTarget c w with
    | none => none
    | some tgt =>
        if w.ring.val = 0 ∧ tgt < ASIDDHA_BASE then
          none
        else if w.ring.val = 0 ∧ c.scopeDepth = 0 then
          none
        else if w.opcode = OP_STORE ∧
                (c.scopeDepth = 0 ∨ w.ring.val ≠ 0) then
          none
        else if w.opcode = OP_LOPA ∧ tgt ≥ ASIDDHA_BASE ∧
                (c.scopeDepth = 0 ∨ w.ring.val ≠ 0) then
          none
        else if w.opcode = OP_LOPA ∧ c.written tgt ≠ true then
          none
        else
          let written' :=
            if w.opcode = OP_WRITE ∨ w.opcode = OP_STORE then
              markWritten c.written tgt
            else if w.opcode = OP_LOPA then
              markErased c.written tgt
            else
              c.written
          let context' :=
            if w.opcode = OP_LOPA then none
            else if w.comp.val = 1 then c.contextTarget
            else some tgt
          some
            { written       := written'
            , contextTarget := context'
            , scopeDepth    := c.scopeDepth }

-- §4 Abstract machine ----------------------------------------------------------

structure MachineState where
  control : ControlState
  mem     : Nat → Nat

def MachineState.initial : MachineState :=
  { control := ControlState.initial
  , mem     := fun _ => 0 }

def applyMem
    (mem : Nat → Nat) (c : ControlState) (w : ABIWord) : Nat → Nat :=
  match resolveTarget c w with
  | none => mem
  | some tgt =>
      if w.opcode = OP_WRITE ∨ w.opcode = OP_STORE then
        fun a => if a = tgt then 1 else mem a
      else if w.opcode = OP_LOPA then
        fun a => if a = tgt then 0 else mem a
      else
        mem

def advance (s : MachineState) (w : ABIWord) (c' : ControlState) : MachineState :=
  { control := c'
  , mem := applyMem s.mem s.control w }

def step (s : MachineState) (w : ABIWord) : Option MachineState :=
  match controlStep s.control w with
  | none    => none
  | some c' => some (advance s w c')

def execute : List ABIWord → MachineState → Option MachineState
  | [], s => some s
  | w :: ws, s =>
      match step s w with
      | none    => none
      | some s' => execute ws s'

-- §5 Canonical validation ------------------------------------------------------

def validateWords : List ABIWord → ControlState → Option ControlState
  | [], c => some c
  | w :: ws, c =>
      match controlStep c w with
      | none    => none
      | some c' => validateWords ws c'

def validateIR (ir : List IRNode) : Option ControlState :=
  validateWords (lowerAll ir) ControlState.initial

/-- A valid PSL control program validates and closes every Adhikara scope. -/
def ValidProgram (ir : List IRNode) : Prop :=
  ∃ cFinal,
    validateIR ir = some cFinal ∧
    cFinal.scopeDepth = 0

/-- Executable certificate boundary for Python-emitted IR. -/
def validateIRClosed (ir : List IRNode) : Bool :=
  match validateIR ir with
  | none => false
  | some cFinal => cFinal.scopeDepth == 0

/--
A successful executable IR certificate is sufficient to construct Lean's
propositional ValidProgram witness. This keeps generated compiler certificates
inside the same trust boundary as the abstract validator.
-/
theorem validateIRClosed_sound
    (ir : List IRNode)
    (hcert : validateIRClosed ir = true) :
    ValidProgram ir := by
  unfold validateIRClosed at hcert
  cases hrun : validateIR ir with
  | none =>
      simp [hrun] at hcert
  | some cFinal =>
      have hclosed : cFinal.scopeDepth = 0 := by
        simpa [hrun] using hcert
      exact ⟨cFinal, hrun, hclosed⟩

/-- Executable CI boundary for numeric compiler output. -/
def validateEncodedClosed (words : List Nat) : Bool :=
  match validateWords (words.map decodeABIWord) ControlState.initial with
  | none => false
  | some cFinal => cFinal.scopeDepth == 0

-- §6 Closed lowering facts ----------------------------------------------------

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

-- §7 Closed control-safety facts ----------------------------------------------

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

theorem open_increments_scope (c : ControlState) :
    controlStep c openWord =
      some { c with scopeDepth := c.scopeDepth + 1 } := by
  simp [controlStep, openWord, OP_OPEN, OP_CLOSE]

theorem close_at_zero_fails (c : ControlState) (hzero : c.scopeDepth = 0) :
    controlStep c closeWord = none := by
  simp [controlStep, closeWord, OP_OPEN, OP_CLOSE, hzero]

theorem step_of_controlStep
    (s : MachineState) (w : ABIWord) (c' : ControlState)
    (h : controlStep s.control w = some c') :
    step s w = some (advance s w c') := by
  simp [step, h]

-- §8 Forward simulation: validator -> abstract execution ----------------------

/--
If control validation succeeds for a word stream, abstract execution succeeds
from any machine state whose control state is the validator's starting state,
and both end in the same control state.

This is a genuine axiom-free forward-simulation theorem for the PSL control
model. It does not claim source-to-RV32 semantic preservation, Sandhi atomicity,
conditional semantics, or physical-hardware correctness.
-/
theorem validateWords_execution
    (words : List ABIWord) :
    ∀ (c0 : ControlState) (s0 : MachineState) (cFinal : ControlState),
      s0.control = c0 →
      validateWords words c0 = some cFinal →
      ∃ sFinal,
        execute words s0 = some sFinal ∧
        sFinal.control = cFinal := by
  induction words with
  | nil =>
      intro c0 s0 cFinal hcontrol hvalid
      simp [validateWords] at hvalid
      subst cFinal
      refine ⟨s0, ?_, hcontrol⟩
      rfl
  | cons w ws ih =>
      intro c0 s0 cFinal hcontrol hvalid
      cases hstep : controlStep c0 w with
      | none =>
          simp [validateWords, hstep] at hvalid
      | some c1 =>
          have hvalidTail : validateWords ws c1 = some cFinal := by
            simpa [validateWords, hstep] using hvalid
          have hcontrolStep : controlStep s0.control w = some c1 := by
            rw [hcontrol]
            exact hstep
          have hmachineStep :
              step s0 w = some (advance s0 w c1) :=
            step_of_controlStep s0 w c1 hcontrolStep
          obtain ⟨sFinal, hexecTail, hfinalControl⟩ :=
            ih c1 (advance s0 w c1) cFinal rfl hvalidTail
          refine ⟨sFinal, ?_, hfinalControl⟩
          simp [execute, hmachineStep, hexecTail]

/-- A validated lowered IR stream cannot abort in the abstract control model. -/
theorem validated_ir_executes
    (ir : List IRNode) (cFinal : ControlState)
    (hvalid : validateIR ir = some cFinal) :
    ∃ sFinal,
      execute (lowerAll ir) MachineState.initial = some sFinal ∧
      sFinal.control = cFinal := by
  exact validateWords_execution (lowerAll ir)
    ControlState.initial MachineState.initial cFinal rfl hvalid

theorem valid_program_executes
    (ir : List IRNode)
    (hvalid : ValidProgram ir) :
    ∃ sFinal,
      execute (lowerAll ir) MachineState.initial = some sFinal ∧
      sFinal.control.scopeDepth = 0 := by
  obtain ⟨cFinal, hrun, hclosed⟩ := hvalid
  obtain ⟨sFinal, hexec, hcontrol⟩ :=
    validated_ir_executes ir cFinal hrun
  refine ⟨sFinal, hexec, ?_⟩
  rw [hcontrol]
  exact hclosed

/--
A generated compiler IR certificate that evaluates to true therefore carries
all the way to non-aborting abstract execution with closed Adhikara scope.
-/
theorem certified_ir_executes
    (ir : List IRNode)
    (hcert : validateIRClosed ir = true) :
    ∃ sFinal,
      execute (lowerAll ir) MachineState.initial = some sFinal ∧
      sFinal.control.scopeDepth = 0 := by
  exact valid_program_executes ir (validateIRClosed_sound ir hcert)

-- §9 Explicitly open refinement goals -----------------------------------------

/-
  Remaining proof boundaries:

  1. Python compiler -> Lean ValidProgram correspondence.
  2. Avrtti repetition semantics.
  3. Utsarga/Apavada conditional semantics.
  4. Sandhi atomicity semantics.
  5. Lean abstract machine -> canonical RV32 firmware refinement.
  6. QEMU -> physical-hardware evidence.

  None of these is implied by valid_program_executes.
-/

-- End of PSL/Semantics.lean
