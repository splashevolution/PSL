import PSL.Semantics

/-
  Canonical negative conformance cases.
  Each stream encodes a concrete structural violation and must be rejected.
-/

-- Anuvrtti WRITE with no live context.
example : validateEncodedClosed [0x210500F0] = false := by
  native_decide

-- CLOSE with no active Adhikara.
example : validateEncodedClosed [0x00BB00F0] = false := by
  native_decide

-- Ring-0 WRITE resolves to Siddha 0x30 even though it is scoped.
example : validateEncodedClosed
    [0x00AA00F0, 0x000530F0, 0x00BB00F0] = false := by
  native_decide

-- Store outside Adhikara.
example : validateEncodedClosed [0x00CC60F0] = false := by
  native_decide

-- Ring-2 Store is invalid even inside Adhikara.
example : validateEncodedClosed
    [0x00AA00F0, 0x20CC60F0, 0x00BB00F0] = false := by
  native_decide

-- Asiddha Lopa without a live prior write.
example : validateEncodedClosed
    [0x00AA00F0, 0x000060F0, 0x00BB00F0] = false := by
  native_decide

-- Lopa consumes live-written state: a second Lopa fails.
example : validateEncodedClosed
    [0x200530F0, 0x200030F0, 0x200030F0] = false := by
  native_decide

-- Lopa clears inheritance context: post-Lopa Anuvrtti fails.
example : validateEncodedClosed
    [0x200530F0, 0x200030F0, 0x210500F0] = false := by
  native_decide

-- Unclosed Adhikara is not a valid closed program.
example : validateEncodedClosed [0x00AA00F0] = false := by
  native_decide
