#include <stdint.h>

#include "pvm_image.h"

/*
 * PVM Sprint 3 Firmware — Avrtti Bounded Repetition
 *
 * ABI Word layout (32-bit big-endian):
 *   [31:28] RING_ID    — 0x0 = Ring 0, 0x2 = User
 *   [27:24] COUNT      — Avrtti repeat count (0 = once, N = repeat N times)
 *   [23:16] OPCODE
 *   [15:08] TARGET
 *   [07:04] FLAGS      — 0xF = Lopa boundary
 *   [03:00] COND       — 0=unconditional, 1=Utsarga, 2=Apavada
 *
 * Avrtti semantics:
 *   COUNT = 0 -> execute instruction exactly once (Sprint 1/2 behaviour)
 *   COUNT = N -> execute instruction exactly N times, no branch needed
 *
 * The repeat count is read directly from the instruction word.
 * The firmware does not speculate, predict, or check a runtime variable.
 * The bound is encoded in the rule — this is the hardware efficiency claim.
 *
 * Proof program (avrtti_core.pvm):
 *   Instruction 1: Avrtti 3 — Vak write fires exactly 3 times
 *   Instruction 2: Apavada  — Yantra Ring 0 store fires if Srotra present
 *
 * Expected UART summary:
 *   avrtti_cycles=0x03  VAK=0xFF  YANTRA_shadow=0xFF  apavada_fired=0x01
 */

#define UART0_BASE       0x10000000u
#define SIFIVE_TEST_BASE 0x00100000u

#define VDEV_VAK    0x30u
#define VDEV_SROTRA 0x50u
#define VDEV_YANTRA 0x60u

#define PVM_OP_WRITE    0x05u
#define PVM_OP_STORE    0xCCu
#define PVM_RING_KERNEL 0x00u
#define PVM_ASIDDHA_BASE 0x50u
#define PVM_WRITE_VALUE  0xFFu

#define PVM_COND_UNCONDITIONAL 0x0u
#define PVM_COND_UTSARGA       0x1u
#define PVM_COND_APAVADA       0x2u

typedef struct {
    volatile uint32_t instruction_counter;
    volatile uint32_t rejected_counter;
    volatile uint32_t avrtti_cycles;     /* total Avrtti repeat executions */
    volatile uint32_t apavada_fired;
    volatile uint8_t  siddha_global_bus[256];
    volatile uint8_t  asiddha_shadow_cache[256];
} PVMHardwareState;

static volatile PVMHardwareState vm;

/* ---------- UART helpers ---------- */

static void uart_putc(char c) {
    *(volatile uint8_t *)UART0_BASE = (uint8_t)c;
}

static void uart_puts(const char *s) {
    while (*s) uart_putc(*s++);
}

static void uart_hex8(uint8_t v) {
    static const char hex[] = "0123456789ABCDEF";
    uart_putc(hex[(v >> 4) & 0x0F]);
    uart_putc(hex[v & 0x0F]);
}

static void uart_hex32(uint32_t v) {
    int shift;
    static const char hex[] = "0123456789ABCDEF";
    for (shift = 28; shift >= 0; shift -= 4)
        uart_putc(hex[(v >> shift) & 0x0F]);
}

/* ---------- ABI decoder ---------- */

static uint32_t read_be32(const uint8_t *buf) {
    return ((uint32_t)buf[0] << 24)
         | ((uint32_t)buf[1] << 16)
         | ((uint32_t)buf[2] <<  8)
         | (uint32_t)buf[3];
}

static int is_mutating_opcode(uint8_t op) {
    return op == PVM_OP_WRITE || op == PVM_OP_STORE;
}

/* ---------- Condition evaluator (Sprint 2, preserved) ---------- */

static int evaluate_condition(uint8_t cond) {
    uint8_t srotra = vm.siddha_global_bus[VDEV_SROTRA];
    switch (cond) {
        case PVM_COND_UNCONDITIONAL: return 1;
        case PVM_COND_UTSARGA:       return (srotra == 0x00) ? 1 : 0;
        case PVM_COND_APAVADA:       return (srotra != 0x00) ? 1 : 0;
        default:                     return 0;
    }
}

/* ---------- Single execution body (one application of the rule) ---------- */

static void apply_once(uint32_t instr __attribute__((unused)), uint8_t ring, uint8_t opcode,
                       uint8_t target, uint8_t cond, uint32_t cycle_num) {
    uart_puts("    [cycle ");
    uart_hex8((uint8_t)cycle_num);
    uart_puts("] target=0x");
    uart_hex8(target);
    uart_puts("\r\n");

    /* Privilege gate */
    if (target == VDEV_YANTRA && ring != PVM_RING_KERNEL) {
        vm.rejected_counter++;
        uart_puts("      FAULT: YANTRA requires Ring 0\r\n");
        return;
    }

    if (!is_mutating_opcode(opcode)) {
        uart_puts("      NO-MUTATION\r\n");
        return;
    }

    /* Siddha / Asiddha routing */
    if (target >= PVM_ASIDDHA_BASE) {
        vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
        if (cond == PVM_COND_APAVADA) vm.apavada_fired++;
        uart_puts("      ASIDDHA shadow=0x");
        uart_hex8(vm.asiddha_shadow_cache[target]);
        uart_puts(" global=0x");
        uart_hex8(vm.siddha_global_bus[target]);
        uart_puts("\r\n");
    } else {
        vm.siddha_global_bus[target] = PVM_WRITE_VALUE;
        uart_puts("      SIDDHA global=0x");
        uart_hex8(vm.siddha_global_bus[target]);
        uart_puts("\r\n");
    }
}

/* ---------- Execution cycle with Avrtti ---------- */

static void execute_cycle(uint32_t instr) {
    uint8_t  ring   = (uint8_t)((instr >> 28) & 0x0Fu);
    uint8_t  count  = (uint8_t)((instr >> 24) & 0x0Fu);
    uint8_t  opcode = (uint8_t)((instr >> 16) & 0xFFu);
    uint8_t  target = (uint8_t)((instr >>  8) & 0xFFu);
    uint8_t  cond   = (uint8_t)(instr & 0x0Fu);
    uint32_t repeat = (count == 0) ? 1u : (uint32_t)count;

    vm.instruction_counter++;

    uart_puts("[RV32 PVM] word=0x");
    uart_hex32(instr);
    uart_puts(" count=");
    uart_hex8(count);
    uart_puts(" repeat=");
    uart_hex8((uint8_t)repeat);
    uart_puts("\r\n");

    /* Condition gate — applies to the whole Avrtti block */
    if (!evaluate_condition(cond)) {
        uart_puts("  CONDITION NOT MET — block skipped\r\n");
        return;
    }

    if (count > 0) {
        uart_puts("  AVRTTI: applying rule ");
        uart_hex8(count);
        uart_puts(" times (bound from instruction word)\r\n");
    }

    /* Deterministic repeat — no branch prediction, bound is in the word */
    uint32_t i;
    for (i = 0; i < repeat; i++) {
        if (count > 0) vm.avrtti_cycles++;   /* only Avrtti instructions count */
        apply_once(instr, ring, opcode, target, cond, i + 1);
    }
}

/* ---------- Summary ---------- */

static void print_summary(void) {
    uart_puts("[RV32 PVM AVRTTI SUMMARY]");
    uart_puts(" avrtti_cycles=0x");  uart_hex8((uint8_t)vm.avrtti_cycles);
    uart_puts(" VAK=0x");            uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" YANTRA_shadow=0x");  uart_hex8(vm.asiddha_shadow_cache[VDEV_YANTRA]);
    uart_puts(" apavada_fired=0x");  uart_hex8((uint8_t)vm.apavada_fired);
    uart_puts(" rejected=0x");       uart_hex8((uint8_t)vm.rejected_counter);
    uart_puts("\r\n");
}

/* ---------- Entry point ---------- */

int main(void) {
    uint32_t offset;

    uart_puts("[RV32 PVM BOOT] Sprint 3 — Avrtti bounded repetition firmware\r\n");

    /* Preload Srotra so Apavada condition fires for instruction 2 */
    vm.siddha_global_bus[VDEV_SROTRA] = 0xA5u;
    uart_puts("[RV32 PVM] Srotra preloaded with 0xA5\r\n");

    for (offset = 0; offset < PVM_IMAGE_SIZE; offset += 4) {
        execute_cycle(read_be32(&pvm_image[offset]));
    }

    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) {
        __asm__ volatile("wfi");
    }
}
