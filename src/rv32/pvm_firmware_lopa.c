#include <stdint.h>

#include "pvm_image.h"

/*
 * PVM Sprint 5 Firmware — Lopa Structured Erasure
 *
 * ABI Word layout (32-bit big-endian):
 *   [31:28] RING_ID
 *   [27:24] COMP       — 0x0 = explicit, 0x1 = Anuvrtti (inherit target)
 *   [23:16] OPCODE     — 0x00 = Lopa (erasure), 0x05 = Write
 *   [15:08] TARGET
 *   [07:04] FLAGS      — 0xF = Immediate Lopa boundary
 *   [03:00] COND
 *
 * Lopa semantics:
 *   When OPCODE == 0x00 (Lopa):
 *     1. Zero the target's Siddha bus entry (explicit nullification)
 *     2. Reset prev_target carry register to 0x00
 *     3. Report LOPA BOUNDARY — no subsequent Anuvrtti may inherit
 *        a target established before this erasure
 *
 * Proof program (lopa_core.pvm):
 *   Instruction 1: Write Vak  — Siddha bus[0x30] = 0xFF
 *   Instruction 2: Lopa Vak   — Siddha bus[0x30] = 0x00, prev_target = 0x00
 *   Instruction 3: Anuvrtti   — prev_target == 0x00, inheritance blocked
 *
 * Expected UART summary:
 *   lopa_erasures=0x01  blocked_inheritances=0x01
 *   VAK_after_lopa=0x00  (bus was cleared)
 */

#define UART0_BASE       0x10000000u
#define SIFIVE_TEST_BASE 0x00100000u

#define VDEV_VAK     0x30u
#define VDEV_SROTRA  0x50u
#define VDEV_YANTRA  0x60u

#define PVM_OP_LOPA      0x00u
#define PVM_OP_WRITE     0x05u
#define PVM_OP_STORE     0xCCu
#define PVM_RING_KERNEL  0x00u
#define PVM_ASIDDHA_BASE 0x50u
#define PVM_WRITE_VALUE  0xFFu
#define PVM_NULL_TARGET  0x00u

#define PVM_COMP_EXPLICIT 0x0u
#define PVM_COMP_ANUVRTTI 0x1u

typedef struct {
    volatile uint32_t instruction_counter;
    volatile uint32_t explicit_writes;
    volatile uint32_t lopa_erasures;
    volatile uint32_t blocked_inheritances;
    volatile uint32_t committed_inheritances;
    volatile uint32_t rejected_counter;
    volatile uint8_t  siddha_global_bus[256];
    volatile uint8_t  asiddha_shadow_cache[256];
    volatile uint8_t  prev_target;       /* Anuvrtti carry register */
    volatile uint8_t  lopa_boundary;     /* 1 = Lopa fired, inheritance blocked */
} PVMHardwareState;

static volatile PVMHardwareState vm;

/* ---------- UART helpers ---------- */

static void uart_putc(char c) { *(volatile uint8_t *)UART0_BASE = (uint8_t)c; }
static void uart_puts(const char *s) { while (*s) uart_putc(*s++); }
static void uart_hex8(uint8_t v) {
    static const char h[] = "0123456789ABCDEF";
    uart_putc(h[(v >> 4) & 0xF]);
    uart_putc(h[v & 0xF]);
}
static void uart_hex32(uint32_t v) {
    int s; static const char h[] = "0123456789ABCDEF";
    for (s = 28; s >= 0; s -= 4) uart_putc(h[(v >> s) & 0xF]);
}

static uint32_t read_be32(const uint8_t *buf) {
    return ((uint32_t)buf[0] << 24) | ((uint32_t)buf[1] << 16)
         | ((uint32_t)buf[2] <<  8) |  (uint32_t)buf[3];
}

/* ---------- Execution cycle ---------- */

static void execute_cycle(uint32_t instr) {
    uint8_t ring   = (uint8_t)((instr >> 28) & 0x0Fu);
    uint8_t comp   = (uint8_t)((instr >> 24) & 0x0Fu);
    uint8_t opcode = (uint8_t)((instr >> 16) & 0xFFu);
    uint8_t target = (uint8_t)((instr >>  8) & 0xFFu);

    (void)ring;  /* ring enforcement not exercised in this proof */

    vm.instruction_counter++;
    uart_puts("[RV32 PVM] word=0x"); uart_hex32(instr);
    uart_puts(" comp=0x"); uart_hex8(comp);
    uart_puts(" op=0x");   uart_hex8(opcode);
    uart_puts(" target=0x"); uart_hex8(target);
    uart_puts("\r\n");

    /* ---- Lopa: explicit erasure ---- */
    if (opcode == PVM_OP_LOPA) {
        vm.lopa_erasures++;
        /* Zero the Siddha bus entry for the stated target */
        vm.siddha_global_bus[target] = 0x00u;
        /* Reset Anuvrtti carry register — inheritance boundary */
        vm.prev_target    = PVM_NULL_TARGET;
        vm.lopa_boundary  = 1u;
        uart_puts("  LOPA: bus[0x"); uart_hex8(target);
        uart_puts("] erased -> 0x00\r\n");
        uart_puts("  LOPA BOUNDARY SET: Anuvrtti inheritance reset\r\n");
        return;
    }

    /* ---- Anuvrtti: resolve inherited target ---- */
    if (comp == PVM_COMP_ANUVRTTI) {
        if (vm.lopa_boundary || vm.prev_target == PVM_NULL_TARGET) {
            /* Inheritance blocked — Lopa erased the context */
            vm.blocked_inheritances++;
            uart_puts("  LOPA BOUNDARY: Anuvrtti inheritance blocked"
                      " — no valid context after erasure\r\n");
            return;
        }
        target = vm.prev_target;
        vm.committed_inheritances++;
        uart_puts("  ANUVRTTI: inherited target=0x"); uart_hex8(target);
        uart_puts("\r\n");
    } else {
        /* Explicit: update carry register, clear Lopa boundary */
        vm.prev_target   = target;
        vm.lopa_boundary = 0u;
        vm.explicit_writes++;
        uart_puts("  EXPLICIT: target=0x"); uart_hex8(target);
        uart_puts(" recorded, Lopa boundary cleared\r\n");
    }

    /* ---- Write / Store ---- */
    if (opcode == PVM_OP_WRITE) {
        if (target >= PVM_ASIDDHA_BASE) {
            vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
            uart_puts("  ASIDDHA shadow=0x");
            uart_hex8(vm.asiddha_shadow_cache[target]);
            uart_puts("\r\n");
        } else {
            vm.siddha_global_bus[target] = PVM_WRITE_VALUE;
            uart_puts("  SIDDHA global=0x");
            uart_hex8(vm.siddha_global_bus[target]);
            uart_puts("\r\n");
        }
    } else if (opcode == PVM_OP_STORE) {
        vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
        uart_puts("  STORE shadow=0x");
        uart_hex8(vm.asiddha_shadow_cache[target]);
        uart_puts("\r\n");
    } else {
        uart_puts("  NO-MUTATION\r\n");
    }
}

/* ---------- Summary ---------- */

static void print_summary(void) {
    uart_puts("[RV32 PVM LOPA SUMMARY]");
    uart_puts(" lopa_erasures=0x");         uart_hex8((uint8_t)vm.lopa_erasures);
    uart_puts(" blocked_inheritances=0x");  uart_hex8((uint8_t)vm.blocked_inheritances);
    uart_puts(" VAK_after_lopa=0x");        uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" explicit_writes=0x");       uart_hex8((uint8_t)vm.explicit_writes);
    uart_puts(" rejected=0x");              uart_hex8((uint8_t)vm.rejected_counter);
    uart_puts("\r\n");
}

/* ---------- Entry point ---------- */

int main(void) {
    uint32_t offset;
    uart_puts("[RV32 PVM BOOT] Sprint 5 — Lopa structured erasure firmware\r\n");

    for (offset = 0; offset < PVM_IMAGE_SIZE; offset += 4)
        execute_cycle(read_be32(&pvm_image[offset]));

    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) __asm__ volatile("wfi");
}
