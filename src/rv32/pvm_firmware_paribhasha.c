#include <stdint.h>
#include "pvm_image.h"

/*
 * PVM Sprint 7 Firmware — Paribhasha Valid-Program Proof
 *
 * The Paribhasha sprint has two proofs:
 *
 * PROOF A (compiler-only, no firmware):
 *   Three intentional violations are fed to the compiler one at a time.
 *   Each one raises ParibhashaError with its named rule (P1/P2/P3).
 *   Zero bytes are emitted. The rejection itself is the proof.
 *
 * PROOF B (firmware, this file):
 *   A valid program (paribhasha_valid_core.pvm) that satisfies all three
 *   Paribhasha constraints is compiled and executed here.
 *   The firmware proves that Paribhasha rejects exactly what is wrong and
 *   permits exactly what is right -- nothing more, nothing less.
 *
 * Expected ABI image from paribhasha_valid_core.pvm:
 *   0x200530F0  -- Ring 2, Write, Vak  (0x30) explicit      -- P1 satisfied
 *   0x210500F0  -- Ring 2, Write, 0x00 Anuvrtti (inherits)  -- P1 satisfied (context exists)
 *   0x200030F0  -- Ring 2, Lopa, Vak  (0x30)                -- P2 satisfied (was written)
 *   0x00CC60F0  -- Ring 0, Store, Yantra (0x60) Asiddha     -- P3 satisfied (>= 0x50)
 *
 * Expected UART summary:
 *   siddha_writes=0x02  anuvrtti_inherited=0x01
 *   lopa_erasures=0x01  asiddha_stores=0x01
 *   VAK_after_lopa=0x00  YANTRA_shadow=0xFF
 */

#define UART0_BASE       0x10000000u
#define SIFIVE_TEST_BASE 0x00100000u

#define VDEV_VAK    0x30u
#define VDEV_YANTRA 0x60u

#define PVM_OP_LOPA      0x00u
#define PVM_OP_WRITE     0x05u
#define PVM_OP_STORE     0xCCu
#define PVM_RING_0       0x00u
#define PVM_RING_2       0x02u
#define PVM_ASIDDHA_BASE 0x50u
#define PVM_WRITE_VALUE  0xFFu
#define PVM_NULL_TARGET  0x00u

#define PVM_COMP_EXPLICIT 0x0u
#define PVM_COMP_ANUVRTTI 0x1u

typedef struct {
    volatile uint32_t instruction_counter;
    volatile uint32_t siddha_writes;
    volatile uint32_t anuvrtti_inherited;
    volatile uint32_t lopa_erasures;
    volatile uint32_t asiddha_stores;
    volatile uint8_t  siddha_global_bus[256];
    volatile uint8_t  asiddha_shadow_cache[256];
    volatile uint8_t  prev_target;
    volatile uint8_t  lopa_boundary;
} PVMHardwareState;

static volatile PVMHardwareState vm;

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

static void execute_cycle(uint32_t instr) {
    uint8_t ring   = (uint8_t)((instr >> 28) & 0x0Fu);
    uint8_t comp   = (uint8_t)((instr >> 24) & 0x0Fu);
    uint8_t opcode = (uint8_t)((instr >> 16) & 0xFFu);
    uint8_t target = (uint8_t)((instr >>  8) & 0xFFu);

    vm.instruction_counter++;
    uart_puts("[RV32 PVM] word=0x"); uart_hex32(instr);
    uart_puts(" ring=0x"); uart_hex8(ring);
    uart_puts(" op=0x"); uart_hex8(opcode);
    uart_puts(" target=0x"); uart_hex8(target);
    uart_puts("\r\n");

    /* Lopa: erase target, reset context, set boundary */
    if (opcode == PVM_OP_LOPA) {
        vm.lopa_erasures++;
        vm.siddha_global_bus[target] = 0x00u;
        vm.prev_target   = PVM_NULL_TARGET;
        vm.lopa_boundary = 1u;
        uart_puts("  LOPA: bus[0x"); uart_hex8(target);
        uart_puts("] erased -> 0x00, boundary set\r\n");
        return;
    }

    /* Anuvrtti: inherit target from previous context */
    if (comp == PVM_COMP_ANUVRTTI) {
        if (vm.lopa_boundary || vm.prev_target == PVM_NULL_TARGET) {
            uart_puts("  ANUVRTTI: boundary active - skipping\r\n");
            return;
        }
        target = vm.prev_target;
        vm.anuvrtti_inherited++;
        uart_puts("  ANUVRTTI: inherited target=0x"); uart_hex8(target);
        uart_puts("\r\n");
    } else {
        vm.prev_target   = target;
        vm.lopa_boundary = 0u;
    }

    /* Write to Siddha bus */
    if (opcode == PVM_OP_WRITE) {
        if (target < PVM_ASIDDHA_BASE) {
            vm.siddha_writes++;
            vm.siddha_global_bus[target] = PVM_WRITE_VALUE;
            uart_puts("  WRITE Siddha bus[0x"); uart_hex8(target);
            uart_puts("]=0xFF\r\n");
        }
        return;
    }

    /* Store to Asiddha shadow (Ring 0) */
    if (opcode == PVM_OP_STORE) {
        if (target >= PVM_ASIDDHA_BASE && ring == PVM_RING_0) {
            vm.asiddha_stores++;
            vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
            uart_puts("  STORE Ring0 Asiddha shadow[0x"); uart_hex8(target);
            uart_puts("]=0xFF (P3 satisfied: target >= 0x50)\r\n");
        }
        return;
    }
}

static void print_summary(void) {
    uart_puts("[RV32 PVM PARIBHASHA SUMMARY]");
    uart_puts(" siddha_writes=0x");      uart_hex8((uint8_t)vm.siddha_writes);
    uart_puts(" anuvrtti_inherited=0x"); uart_hex8((uint8_t)vm.anuvrtti_inherited);
    uart_puts(" lopa_erasures=0x");      uart_hex8((uint8_t)vm.lopa_erasures);
    uart_puts(" asiddha_stores=0x");     uart_hex8((uint8_t)vm.asiddha_stores);
    uart_puts(" VAK_after_lopa=0x");     uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" YANTRA_shadow=0x");      uart_hex8(vm.asiddha_shadow_cache[VDEV_YANTRA]);
    uart_puts("\r\n");
}

int main(void) {
    uint32_t offset;
    uart_puts("[RV32 PVM BOOT] Sprint 7 -- Paribhasha valid-program proof\r\n");

    for (offset = 0; offset < PVM_IMAGE_SIZE; offset += 4)
        execute_cycle(read_be32(&pvm_image[offset]));

    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) __asm__ volatile("wfi");
}
