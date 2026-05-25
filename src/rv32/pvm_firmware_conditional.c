#include <stdint.h>

#include "pvm_image.h"

/*
 * PVM Sprint 2 Firmware — Utsarga / Apavada Conditional Execution
 *
 * ABI Word layout (32-bit big-endian):
 *   [31:28] RING_ID
 *   [27:24] COMPRESSION
 *   [23:16] OPCODE
 *   [15:08] TARGET
 *   [07:04] FLAGS  (always 0xF = Lopa boundary)
 *   [03:00] COND   (0=unconditional, 1=Utsarga, 2=Apavada)
 *
 * Utsarga  (0x1): general rule  — fires when Srotra global bus == 0x00
 * Apavada  (0x2): exception rule — fires when Srotra global bus != 0x00
 * Unconditional (0x0): always fires (Sprint 1 backward compatibility)
 *
 * The firmware preloads a non-zero signal on the Srotra bus to simulate
 * an active input event. This means:
 *   - Utsarga  instruction is SKIPPED  (input present, general rule deferred)
 *   - Apavada  instruction is EXECUTED (exception takes precedence)
 *
 * Expected UART summary:
 *   UTSARGA SKIPPED  — Apavada takes precedence (Srotra signal present)
 *   APAVADA FIRED    — Ring 0 store to Yantra shadow committed
 */

#define UART0_BASE       0x10000000u
#define SIFIVE_TEST_BASE 0x00100000u

#define VDEV_VAK    0x30u
#define VDEV_SROTRA 0x50u
#define VDEV_YANTRA 0x60u

#define PVM_OP_WRITE  0x05u
#define PVM_OP_STORE  0xCCu
#define PVM_RING_KERNEL 0x00u
#define PVM_ASIDDHA_BASE 0x50u
#define PVM_WRITE_VALUE  0xFFu

#define PVM_COND_UNCONDITIONAL 0x0u
#define PVM_COND_UTSARGA       0x1u
#define PVM_COND_APAVADA       0x2u

typedef struct {
    volatile uint32_t instruction_counter;
    volatile uint32_t rejected_counter;
    volatile uint32_t utsarga_skipped;
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

/* ---------- Condition evaluator ---------- */

/*
 * evaluate_condition — Paninian precedence gate.
 *
 * Pāṇini's Utsarga/Apavāda model:
 *   The Apavāda (exception) overrides the Utsarga (general rule) whenever
 *   its condition is satisfied. The Utsarga fires only when no exception
 *   applies. Neither rule is discarded — precedence is determined by
 *   the hardware state at execution time.
 *
 * Returns 1 if the instruction should execute, 0 if it should be skipped.
 */
static int evaluate_condition(uint8_t cond) {
    uint8_t srotra_signal = vm.siddha_global_bus[VDEV_SROTRA];

    switch (cond) {
        case PVM_COND_UNCONDITIONAL:
            return 1;
        case PVM_COND_UTSARGA:
            /* General rule: applies only when no input signal is present */
            return (srotra_signal == 0x00) ? 1 : 0;
        case PVM_COND_APAVADA:
            /* Exception rule: applies when input signal is present */
            return (srotra_signal != 0x00) ? 1 : 0;
        default:
            return 0;
    }
}

/* ---------- Execution cycle ---------- */

static void execute_cycle(uint32_t instr) {
    uint8_t ring   = (uint8_t)((instr >> 28) & 0x0Fu);
    uint8_t opcode = (uint8_t)((instr >> 16) & 0xFFu);
    uint8_t target = (uint8_t)((instr >>  8) & 0xFFu);
    uint8_t cond   = (uint8_t)(instr & 0x0Fu);

    vm.instruction_counter++;

    uart_puts("[RV32 PVM] word=0x");
    uart_hex32(instr);
    uart_puts(" target=0x");
    uart_hex8(target);
    uart_puts(" cond=0x");
    uart_hex8(cond);
    uart_puts("\r\n");

    /* Paninian precedence gate */
    if (!evaluate_condition(cond)) {
        if (cond == PVM_COND_UTSARGA) {
            vm.utsarga_skipped++;
            uart_puts("  UTSARGA SKIPPED — Apavada takes precedence (Srotra signal present)\r\n");
        } else {
            uart_puts("  CONDITION NOT MET — instruction skipped\r\n");
        }
        return;
    }

    /* Privilege gate: Yantra requires Ring 0 */
    if (target == VDEV_YANTRA && ring != PVM_RING_KERNEL) {
        vm.rejected_counter++;
        uart_puts("  FAULT: YANTRA requires Ring 0\r\n");
        return;
    }

    if (!is_mutating_opcode(opcode)) {
        uart_puts("  NO-MUTATION\r\n");
        return;
    }

    /* Siddha / Asiddha visibility model (Sprint 1 preserved) */
    if (target >= PVM_ASIDDHA_BASE) {
        vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
        if (cond == PVM_COND_APAVADA) {
            vm.apavada_fired++;
            uart_puts("  APAVADA FIRED — Ring 0 store to Yantra shadow committed\r\n");
        }
        uart_puts("  ASIDDHA shadow=0x");
        uart_hex8(vm.asiddha_shadow_cache[target]);
        uart_puts(" global=0x");
        uart_hex8(vm.siddha_global_bus[target]);
        uart_puts("\r\n");
        return;
    }

    vm.siddha_global_bus[target] = PVM_WRITE_VALUE;
    uart_puts("  SIDDHA global=0x");
    uart_hex8(vm.siddha_global_bus[target]);
    uart_puts("\r\n");
}

/* ---------- Summary ---------- */

static void print_summary(void) {
    uart_puts("[RV32 PVM CONDITIONAL SUMMARY]");
    uart_puts(" VAK=0x");       uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" YANTRA_shadow=0x"); uart_hex8(vm.asiddha_shadow_cache[VDEV_YANTRA]);
    uart_puts(" utsarga_skipped=0x"); uart_hex8((uint8_t)vm.utsarga_skipped);
    uart_puts(" apavada_fired=0x");   uart_hex8((uint8_t)vm.apavada_fired);
    uart_puts(" rejected=0x");        uart_hex8((uint8_t)vm.rejected_counter);
    uart_puts("\r\n");
}

/* ---------- Entry point ---------- */

int main(void) {
    uint32_t offset;

    uart_puts("[RV32 PVM BOOT] Sprint 2 — Utsarga/Apavada conditional firmware\r\n");

    /*
     * Preload Srotra with a non-zero signal to simulate an active input event.
     * This drives the Apavada path: the exception rule fires, Utsarga is skipped.
     * To test the Utsarga path, set this to 0x00.
     */
    vm.siddha_global_bus[VDEV_SROTRA] = 0xA5u;
    uart_puts("[RV32 PVM] Srotra preloaded with 0xA5 (input signal present)\r\n");

    for (offset = 0; offset < PVM_IMAGE_SIZE; offset += 4) {
        execute_cycle(read_be32(&pvm_image[offset]));
    }

    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) {
        __asm__ volatile("wfi");
    }
}
