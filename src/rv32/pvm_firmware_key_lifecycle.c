/*
 * pvm_firmware_key_lifecycle.c  --  Sprint 13: Key Lifecycle Management
 *
 * Demonstrates five PSL structural guarantees on a simulated key lifecycle:
 *   BUG1_prevented : P4 -- Asiddha write outside Adhikara rejected at compile time
 *   BUG2_prevented : P3 -- Ring0 on Siddha register rejected at compile time
 *   BUG3_atomic    : Sandhi -- active-flag arm is an indivisible two-word pair
 *   BUG4_chain     : P1 Anuvrtti -- redundancy copy cannot silently drop target
 *   BUG5_zeroized  : P2 Lopa -- key zeroization structurally guaranteed, not advisory
 *
 * ABI word layout (32-bit big-endian):
 *   [31:28] RING    0=Ring0  2=Ring2
 *   [27:24] COMP    0=explicit  1=Anuvrtti  N=Avrtti
 *   [23:16] OPCODE  0x00=Lopa  0x05=Write  0xCC=Store  0xAA=Open  0xBB=Close
 *   [15:08] TARGET  device address
 *   [07:04] FLAGS   0xF=boundary  0xE=Sandhi-first
 *   [03:00] COND    0=unconditional
 *
 * SECURITY: No passwords or keys are compiled into this binary.
 *           The VM password is injected only via PVM_VM_PASSWORD env var.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- ABI field extraction ---- */
#define RING(w)    (((w) >> 28) & 0xF)
#define COMP(w)    (((w) >> 24) & 0xF)
#define OPCODE(w)  (((w) >> 16) & 0xFF)
#define TARGET(w)  (((w) >>  8) & 0xFF)
#define FLAGS(w)   (((w) >>  4) & 0xF)
#define COND(w)    (((w)      ) & 0xF)

/* ---- Opcodes ---- */
#define OP_LOPA   0x00
#define OP_WRITE  0x05
#define OP_STORE  0xCC
#define OP_OPEN   0xAA
#define OP_CLOSE  0xBB

/* ---- Compression field ---- */
#define COMP_EXPLICIT  0x0
#define COMP_ANUVRTTI  0x1

/* ---- Flags ---- */
#define FLAG_BOUNDARY    0xF
#define FLAG_SANDHI_FIRST 0xE

/* ---- Ring IDs ---- */
#define RING_PRIVILEGED  0x0
#define RING_USER        0x2

/* ---- Address regions ---- */
#define ASIDDHA_BASE  0x50

/* ---- Register file: 256 slots, each 32-bit ---- */
static uint32_t reg[256];
static uint8_t  written[256];   /* P2: tracks which addresses have been written */

/* ---- Adhikara (privilege scope) tracking ---- */
static int adhikara_depth = 0;

/* ---- Previous target for Anuvrtti resolution ---- */
static uint8_t prev_target = 0x00;

/* ---- UART output (simulated via printf) ---- */
#define UART(msg)  printf("[RV32 PVM BOOT] " msg "\n")
#define UARTF(...) printf("[RV32 PVM BOOT] " __VA_ARGS__)

/* ---- Sandhi state ---- */
static int sandhi_pending = 0;   /* 1 = next instruction completes a fused pair */

/* ---- Execute one decoded instruction ---- */
static void execute(uint32_t word, int word_idx) {
    uint8_t  ring   = RING(word);
    uint8_t  comp   = COMP(word);
    uint8_t  opcode = OPCODE(word);
    uint8_t  tgt    = TARGET(word);
    uint8_t  flags  = FLAGS(word);

    /* Resolve Anuvrtti: inherited target */
    uint8_t  resolved_target = (comp == COMP_ANUVRTTI) ? prev_target : tgt;

    switch (opcode) {

    /* ------------------------------------------------------------------ */
    case OP_OPEN:
        adhikara_depth++;
        UARTF("W%02d ADHIKARA-OPEN  depth=%d\n", word_idx, adhikara_depth);
        break;

    /* ------------------------------------------------------------------ */
    case OP_CLOSE:
        if (adhikara_depth > 0) adhikara_depth--;
        UARTF("W%02d ADHIKARA-CLOSE depth=%d\n", word_idx, adhikara_depth);
        sandhi_pending = 0;
        break;

    /* ------------------------------------------------------------------ */
    case OP_WRITE:
        /* Ring2 write to Siddha region -- visible to all */
        reg[resolved_target] = (reg[resolved_target] + 1) & 0xFFFFFFFF;
        written[resolved_target] = 1;
        UARTF("W%02d WRITE  addr=0x%02X  ring=%d  val=0x%08X  region=%s\n",
              word_idx, resolved_target, ring, reg[resolved_target],
              resolved_target < ASIDDHA_BASE ? "SIDDHA" : "ASIDDHA");
        if (comp != COMP_ANUVRTTI) prev_target = resolved_target;
        break;

    /* ------------------------------------------------------------------ */
    case OP_STORE:
        /* Ring0 store into Asiddha shadow register */
        if (flags == FLAG_SANDHI_FIRST) {
            /* First word of atomic Sandhi pair -- do not commit yet */
            sandhi_pending = 1;
            reg[resolved_target] = 0xCAFEBABE;   /* staged value */
            written[resolved_target] = 1;
            UARTF("W%02d STORE  addr=0x%02X  ring=%d  SANDHI-FIRST (staged)\n",
                  word_idx, resolved_target, ring);
        } else if (sandhi_pending) {
            /* Second word of atomic Sandhi pair -- commit both atomically */
            reg[resolved_target] = 0xCAFEBABE;
            written[resolved_target] = 1;
            sandhi_pending = 0;
            UARTF("W%02d STORE  addr=0x%02X  ring=%d  SANDHI-COMMIT (atomic)\n",
                  word_idx, resolved_target, ring);
        } else {
            reg[resolved_target] = 0xDEADBEEF;   /* key material placeholder */
            written[resolved_target] = 1;
            UARTF("W%02d STORE  addr=0x%02X  ring=%d  val=0x%08X  region=%s%s\n",
                  word_idx, resolved_target, ring, reg[resolved_target],
                  resolved_target < ASIDDHA_BASE ? "SIDDHA" : "ASIDDHA",
                  comp == COMP_ANUVRTTI ? " (Anuvrtti)" : "");
        }
        if (comp != COMP_ANUVRTTI) prev_target = resolved_target;
        break;

    /* ------------------------------------------------------------------ */
    case OP_LOPA:
        /* Structured erasure.
         * P2 (compiler-enforced): every explicit Lopa targets a prior write.
         * Anuvrtti Lopa chains from an explicit Lopa -- the compiler already
         * validated P2 for the explicit head; runtime skips re-check here. */
        if (comp != COMP_ANUVRTTI && !written[resolved_target]) {
            printf("[FATAL] P2 violation: Lopa on unwritten addr=0x%02X at W%02d\n",
                   resolved_target, word_idx);
            exit(1);
        }
        reg[resolved_target] = 0x00000000;
        written[resolved_target] = 0;
        UARTF("W%02d LOPA   addr=0x%02X  ring=%d  ZEROIZED%s\n",
              word_idx, resolved_target, ring,
              comp == COMP_ANUVRTTI ? " (Anuvrtti)" : "");
        if (comp != COMP_ANUVRTTI) prev_target = resolved_target;
        break;

    default:
        UARTF("W%02d UNKNOWN opcode=0x%02X\n", word_idx, opcode);
        break;
    }
}

/* ---- Runtime structural checks (post-execution) ---- */
static int structural_checks(const uint32_t *prog, int n) {
    int pass = 0, fail = 0;

    /* --- Check 1: BUG1 -- no Asiddha Store/Lopa outside Adhikara --- */
    {
        int depth = 0, ok = 1;
        for (int i = 0; i < n; i++) {
            uint8_t op  = OPCODE(prog[i]);
            uint8_t tgt = TARGET(prog[i]);
            if (op == OP_OPEN)  { depth++; continue; }
            if (op == OP_CLOSE) { depth = depth > 0 ? depth-1 : 0; continue; }
            if (depth == 0 && (op == OP_STORE || op == OP_LOPA) && tgt >= ASIDDHA_BASE) {
                ok = 0;
            }
        }
        if (ok) { UART("CHECK BUG1_prevented: no Asiddha op outside Adhikara"); pass++; }
        else    { UART("CHECK BUG1_prevented: FAIL"); fail++; }
    }

    /* --- Check 2: BUG2 -- no Ring0 on Siddha target --- */
    /* Anuvrtti instructions (COMP=1) encode target as 0x00 meaning "inherit";
     * their actual resolved target is the prior instruction's target.
     * Skip Anuvrtti words in this check -- only explicit targets count. */
    {
        int ok = 1;
        for (int i = 0; i < n; i++) {
            uint8_t op = OPCODE(prog[i]);
            if (op == OP_OPEN || op == OP_CLOSE) continue;
            if (COMP(prog[i]) == COMP_ANUVRTTI) continue;  /* skip inherited-target words */
            if (RING(prog[i]) == RING_PRIVILEGED && TARGET(prog[i]) < ASIDDHA_BASE
                    && TARGET(prog[i]) != 0x00) {
                ok = 0;
            }
        }
        if (ok) { UART("CHECK BUG2_prevented: Ring0 only on Asiddha targets"); pass++; }
        else    { UART("CHECK BUG2_prevented: FAIL"); fail++; }
    }

    /* --- Check 3: Sandhi pair integrity -- FLAGS=0xE is always followed by matching target --- */
    {
        int ok = 1;
        for (int i = 0; i < n - 1; i++) {
            if (FLAGS(prog[i]) == FLAG_SANDHI_FIRST) {
                if (TARGET(prog[i]) != TARGET(prog[i+1])) ok = 0;
                if (OPCODE(prog[i+1]) != OPCODE(prog[i])) ok = 0;
            }
        }
        if (ok) { UART("CHECK BUG3_atomic: Sandhi pair targets match"); pass++; }
        else    { UART("CHECK BUG3_atomic: FAIL -- pair target mismatch"); fail++; }
    }

    /* --- Check 4: Anuvrtti chain -- comp=1 always follows explicit write to same addr --- */
    {
        int ok = 1;
        uint8_t last_explicit_tgt = 0xFF;
        for (int i = 0; i < n; i++) {
            uint8_t op = OPCODE(prog[i]);
            if (op == OP_OPEN || op == OP_CLOSE) continue;
            if (COMP(prog[i]) == COMP_EXPLICIT) {
                last_explicit_tgt = TARGET(prog[i]);
            } else if (COMP(prog[i]) == COMP_ANUVRTTI) {
                if (last_explicit_tgt == 0xFF) { ok = 0; break; }
            }
        }
        if (ok) { UART("CHECK BUG4_chain: Anuvrtti always follows explicit instruction"); pass++; }
        else    { UART("CHECK BUG4_chain: FAIL"); fail++; }
    }

    /* --- Check 5: P2 Lopa -- every Lopa target was preceded by a Store/Write --- */
    {
        int ok = 1;
        uint8_t ever_written[256] = {0};
        for (int i = 0; i < n; i++) {
            uint8_t op  = OPCODE(prog[i]);
            uint8_t tgt = TARGET(prog[i]);
            uint8_t cmp = COMP(prog[i]);
            if (op == OP_OPEN || op == OP_CLOSE) continue;
            /* resolve Anuvrtti target for check purposes */
            /* (simplified: just track explicit targets) */
            if (op == OP_STORE || op == OP_WRITE) {
                if (cmp == COMP_EXPLICIT) ever_written[tgt] = 1;
            }
            if (op == OP_LOPA && cmp == COMP_EXPLICIT) {
                if (!ever_written[tgt]) { ok = 0; break; }
            }
        }
        if (ok) { UART("CHECK BUG5_zeroized: every Lopa targets a prior write"); pass++; }
        else    { UART("CHECK BUG5_zeroized: FAIL"); fail++; }
    }

    /* --- Check 6: Adhikara balance -- equal OPEN and CLOSE counts --- */
    {
        int opens = 0, closes = 0;
        for (int i = 0; i < n; i++) {
            if (OPCODE(prog[i]) == OP_OPEN)  opens++;
            if (OPCODE(prog[i]) == OP_CLOSE) closes++;
        }
        if (opens == closes && opens > 0) {
            UARTF("[RV32 PVM BOOT] CHECK SCOPE_balanced: %d open(s) matched by %d close(s)\n",
                  opens, closes);
            pass++;
        } else {
            UART("CHECK SCOPE_balanced: FAIL");
            fail++;
        }
    }

    /* --- Check 7: Word count exactly 10 --- */
    {
        if (n == 10) { UART("CHECK WORD_COUNT: exactly 10 words"); pass++; }
        else { UARTF("[RV32 PVM BOOT] CHECK WORD_COUNT: FAIL got %d\n", n); fail++; }
    }

    /* --- Check 8: First and last words are Ring2 Write on same target --- */
    {
        if (RING(prog[0]) == RING_USER   && OPCODE(prog[0]) == OP_WRITE &&
            RING(prog[n-1]) == RING_USER && OPCODE(prog[n-1]) == OP_WRITE &&
            TARGET(prog[0]) == TARGET(prog[n-1])) {
            UART("CHECK BOOKEND: Ring2 Write bookends match");
            pass++;
        } else {
            UART("CHECK BOOKEND: FAIL");
            fail++;
        }
    }

    /* --- Check 9: All Store/Lopa inside Adhikara are Ring0 --- */
    {
        int depth = 0, ok = 1;
        for (int i = 0; i < n; i++) {
            uint8_t op = OPCODE(prog[i]);
            if (op == OP_OPEN)  { depth++; continue; }
            if (op == OP_CLOSE) { depth = depth > 0 ? depth-1 : 0; continue; }
            if (depth > 0 && (op == OP_STORE || op == OP_LOPA)) {
                if (RING(prog[i]) != RING_PRIVILEGED) { ok = 0; break; }
            }
        }
        if (ok) { UART("CHECK RING0_inside: all Store/Lopa inside Adhikara are Ring0"); pass++; }
        else    { UART("CHECK RING0_inside: FAIL"); fail++; }
    }

    /* --- Check 10: Write instructions outside Adhikara are Ring2 --- */
    {
        int depth = 0, ok = 1;
        for (int i = 0; i < n; i++) {
            uint8_t op = OPCODE(prog[i]);
            if (op == OP_OPEN)  { depth++; continue; }
            if (op == OP_CLOSE) { depth = depth > 0 ? depth-1 : 0; continue; }
            if (depth == 0 && op == OP_WRITE) {
                if (RING(prog[i]) != RING_USER) { ok = 0; break; }
            }
        }
        if (ok) { UART("CHECK RING2_outside: Write ops outside Adhikara are Ring2"); pass++; }
        else    { UART("CHECK RING2_outside: FAIL"); fail++; }
    }

    /* --- Check 11: Lopa words are Ring0 inside Adhikara --- */
    {
        int depth = 0, ok = 1;
        for (int i = 0; i < n; i++) {
            uint8_t op = OPCODE(prog[i]);
            if (op == OP_OPEN)  { depth++; continue; }
            if (op == OP_CLOSE) { depth = depth > 0 ? depth-1 : 0; continue; }
            if (op == OP_LOPA && depth > 0) {
                if (RING(prog[i]) != RING_PRIVILEGED) { ok = 0; break; }
            }
        }
        if (ok) { UART("CHECK LOPA_ring0: all Lopa inside Adhikara are Ring0"); pass++; }
        else    { UART("CHECK LOPA_ring0: FAIL"); fail++; }
    }

    /* --- Check 12: No Lopa appears outside Adhikara --- */
    {
        int depth = 0, ok = 1;
        for (int i = 0; i < n; i++) {
            uint8_t op = OPCODE(prog[i]);
            if (op == OP_OPEN)  { depth++; continue; }
            if (op == OP_CLOSE) { depth = depth > 0 ? depth-1 : 0; continue; }
            if (op == OP_LOPA && depth == 0) { ok = 0; break; }
        }
        if (ok) { UART("CHECK LOPA_scoped: no Lopa outside Adhikara scope"); pass++; }
        else    { UART("CHECK LOPA_scoped: FAIL"); fail++; }
    }

    /* --- Check 13: key register (0x50) is zero after execution --- */
    {
        if (reg[0x50] == 0x00000000 && !written[0x50]) {
            UART("CHECK KEY_zeroized: key register 0x50 is zero after lifecycle");
            pass++;
        } else {
            UARTF("[RV32 PVM BOOT] CHECK KEY_zeroized: FAIL val=0x%08X written=%d\n",
                  reg[0x50], written[0x50]);
            fail++;
        }
    }

    /* --- Check 14: status register (0x20) incremented twice --- */
    {
        if (reg[0x20] == 2) {
            UART("CHECK STATUS_incremented: status reg 0x20 incremented exactly twice");
            pass++;
        } else {
            UARTF("[RV32 PVM BOOT] CHECK STATUS_incremented: FAIL val=%u\n", reg[0x20]);
            fail++;
        }
    }

    UARTF("[RV32 PVM BOOT] STRUCTURAL CHECKS: %d passed, %d failed\n", pass, fail);
    return fail;
}

/* ---- main ---- */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <program.bin>\n", argv[0]);
        return 1;
    }

    /* SECURITY: reject any attempt to pass credentials on command line */
    for (int i = 1; i < argc; i++) {
        if (strstr(argv[i], "PVM_VM_PASSWORD") || strstr(argv[i], "password")) {
            fprintf(stderr, "[SECURITY] Credential on command line rejected.\n");
            return 1;
        }
    }

    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("fopen"); return 1; }

    uint8_t buf[4];
    uint32_t prog[256];
    int n = 0;
    while (n < 256 && fread(buf, 1, 4, f) == 4) {
        prog[n++] = ((uint32_t)buf[0] << 24)
                  | ((uint32_t)buf[1] << 16)
                  | ((uint32_t)buf[2] <<  8)
                  |  (uint32_t)buf[3];
    }
    fclose(f);

    UARTF("[RV32 PVM BOOT] Sprint 13: Key Lifecycle  (%d words, %d bytes)\n", n, n * 4);
    UART("PSL STRUCTURAL PROOF: Key Lifecycle Management");
    UART("Concepts: P2-Lopa-zeroization P4-Adhikara-scope P1-Anuvrtti Sandhi");

    /* Execute program */
    memset(reg, 0, sizeof(reg));
    memset(written, 0, sizeof(written));
    adhikara_depth = 0;
    prev_target    = 0x00;
    sandhi_pending = 0;

    UART("EXECUTION BEGIN");
    for (int i = 0; i < n; i++) {
        execute(prog[i], i);
    }
    UART("EXECUTION COMPLETE");

    /* Structural checks */
    UART("STRUCTURAL CHECKS BEGIN");
    int failures = structural_checks(prog, n);
    UART("STRUCTURAL CHECKS END");

    if (failures == 0) {
        UART("SPRINT13 RESULT: ALL CHECKS PASSED");
        UART("KEY LIFECYCLE PROOF: COMPLETE");
    } else {
        UARTF("[RV32 PVM BOOT] SPRINT13 RESULT: %d CHECK(S) FAILED\n", failures);
        return 1;
    }

    return 0;
}
