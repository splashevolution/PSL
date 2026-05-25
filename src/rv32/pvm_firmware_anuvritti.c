#include <stdint.h>

#include "pvm_image.h"

/*
 * PVM Sprint 4 Firmware — Anuvrtti Context Inheritance
 *
 * ABI Word layout (32-bit big-endian):
 *   [31:28] RING_ID
 *   [27:24] COMP      — 0x0 = explicit, 0x1 = Anuvrtti (inherit target)
 *                       N>1 = Avrtti repeat count (Sprint 3, preserved)
 *   [23:16] OPCODE
 *   [15:08] TARGET    — 0x00 when COMP=0x1 (resolved at decode time)
 *   [07:04] FLAGS
 *   [03:00] COND
 *
 * Anuvrtti decode rule:
 *   When COMP == 0x1, the firmware resolves TARGET by inheriting the
 *   target register from the immediately preceding instruction.
 *   No branch. No lookup table. One register read.
 *
 * Proof program (anuvritti_core.pvm):
 *   Instruction 1: COMP=0x0, TARGET=0x30 (Vak, explicit)
 *   Instruction 2: COMP=0x1, TARGET=0x00 (Vak, inherited)
 *
 * Expected UART summary:
 *   explicit_writes=0x01  inherited_writes=0x01  VAK=0xFF
 *   Both instructions commit to the same Siddha bus entry.
 *   Instruction 2 used zero target bits in the ABI word.
 */

#define UART0_BASE       0x10000000u
#define SIFIVE_TEST_BASE 0x00100000u

#define VDEV_VAK     0x30u
#define VDEV_SROTRA  0x50u
#define VDEV_YANTRA  0x60u

#define PVM_OP_WRITE     0x05u
#define PVM_OP_STORE     0xCCu
#define PVM_RING_KERNEL  0x00u
#define PVM_ASIDDHA_BASE 0x50u
#define PVM_WRITE_VALUE  0xFFu

#define PVM_COMP_EXPLICIT  0x0u
#define PVM_COMP_ANUVRTTI  0x1u

typedef struct {
    volatile uint32_t instruction_counter;
    volatile uint32_t explicit_writes;    /* instructions with stated target */
    volatile uint32_t inherited_writes;   /* instructions using Anuvrtti */
    volatile uint32_t rejected_counter;
    volatile uint8_t  siddha_global_bus[256];
    volatile uint8_t  asiddha_shadow_cache[256];
    volatile uint8_t  prev_target;        /* Anuvrtti carry register */
} PVMHardwareState;

static volatile PVMHardwareState vm;

/* ---------- UART helpers ---------- */

static void uart_putc(char c) {
    *(volatile uint8_t *)UART0_BASE = (uint8_t)c;
}
static void uart_puts(const char *s) { while (*s) uart_putc(*s++); }
static void uart_hex8(uint8_t v) {
    static const char h[] = "0123456789ABCDEF";
    uart_putc(h[(v >> 4) & 0xF]);
    uart_putc(h[v & 0xF]);
}
static void uart_hex32(uint32_t v) {
    int s;
    static const char h[] = "0123456789ABCDEF";
    for (s = 28; s >= 0; s -= 4) uart_putc(h[(v >> s) & 0xF]);
}

/* ---------- ABI decoder ---------- */

static uint32_t read_be32(const uint8_t *buf) {
    return ((uint32_t)buf[0] << 24) | ((uint32_t)buf[1] << 16)
         | ((uint32_t)buf[2] <<  8) |  (uint32_t)buf[3];
}

static int is_mutating(uint8_t op) {
    return op == PVM_OP_WRITE || op == PVM_OP_STORE;
}

/* ---------- Execution cycle ---------- */

static void execute_cycle(uint32_t instr) {
    uint8_t ring   = (uint8_t)((instr >> 28) & 0x0Fu);
    uint8_t comp   = (uint8_t)((instr >> 24) & 0x0Fu);
    uint8_t opcode = (uint8_t)((instr >> 16) & 0xFFu);
    uint8_t target = (uint8_t)((instr >>  8) & 0xFFu);

    vm.instruction_counter++;

    uart_puts("[RV32 PVM] word=0x"); uart_hex32(instr);
    uart_puts(" comp=0x"); uart_hex8(comp);
    uart_puts(" target=0x"); uart_hex8(target);
    uart_puts("\r\n");

    /* Anuvrtti: resolve inherited target */
    if (comp == PVM_COMP_ANUVRTTI) {
        target = vm.prev_target;
        vm.inherited_writes++;
        uart_puts("  ANUVRTTI: inherited target=0x"); uart_hex8(target);
        uart_puts(" from previous instruction\r\n");
    } else {
        /* Explicit: update carry register for next instruction */
        vm.prev_target = target;
        vm.explicit_writes++;
        uart_puts("  EXPLICIT: target=0x"); uart_hex8(target);
        uart_puts(" recorded as Anuvrtti context\r\n");
    }

    /* Privilege gate */
    if (target == VDEV_YANTRA && ring != PVM_RING_KERNEL) {
        vm.rejected_counter++;
        uart_puts("  FAULT: YANTRA requires Ring 0\r\n");
        return;
    }

    if (!is_mutating(opcode)) {
        uart_puts("  NO-MUTATION\r\n");
        return;
    }

    /* Siddha / Asiddha routing */
    if (target >= PVM_ASIDDHA_BASE) {
        vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
        uart_puts("  ASIDDHA shadow=0x"); uart_hex8(vm.asiddha_shadow_cache[target]);
        uart_puts(" global=0x"); uart_hex8(vm.siddha_global_bus[target]);
        uart_puts("\r\n");
    } else {
        vm.siddha_global_bus[target] = PVM_WRITE_VALUE;
        uart_puts("  SIDDHA global=0x"); uart_hex8(vm.siddha_global_bus[target]);
        uart_puts("\r\n");
    }
}

/* ---------- Summary ---------- */

static void print_summary(void) {
    uart_puts("[RV32 PVM ANUVRTTI SUMMARY]");
    uart_puts(" explicit_writes=0x");  uart_hex8((uint8_t)vm.explicit_writes);
    uart_puts(" inherited_writes=0x"); uart_hex8((uint8_t)vm.inherited_writes);
    uart_puts(" VAK=0x");              uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" rejected=0x");         uart_hex8((uint8_t)vm.rejected_counter);
    uart_puts("\r\n");
}

/* ---------- Entry point ---------- */

int main(void) {
    uint32_t offset;

    uart_puts("[RV32 PVM BOOT] Sprint 4 — Anuvrtti context inheritance firmware\r\n");

    for (offset = 0; offset < PVM_IMAGE_SIZE; offset += 4)
        execute_cycle(read_be32(&pvm_image[offset]));

    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) __asm__ volatile("wfi");
}
