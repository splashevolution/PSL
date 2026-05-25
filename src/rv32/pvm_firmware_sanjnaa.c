#include <stdint.h>

#include "pvm_image.h"

/*
 * PVM Sprint 6 Firmware — Sanjnaa Compile-Time Symbol Resolution
 *
 * This firmware is identical to pvm_firmware_lopa.c in execution logic.
 * The proof is not in the firmware — it is in the compiled binary.
 *
 * The pipeline verifies that sanjnaa_core.pvm, which uses symbolic names
 * वाक् and श्रव defined via सञ्ज्ञा declarations, produces byte-for-byte
 * identical ABI words to programs that use built-in Karaka terms directly.
 *
 * Sañjñā is a compile-time abstraction. By the time the firmware runs,
 * the symbol table has been completely erased — only raw addresses remain
 * in the 32-bit instruction words. Zero runtime overhead. Zero indirection.
 *
 * Expected ABI image from sanjnaa_core.pvm:
 *   0x200530F0  — Write वाक्  (0x30, via Sanjnaa, explicit)
 *   0x200550F0  — Write श्रव  (0x50, via Sanjnaa, Asiddha)
 *   0x200030F0  — Lopa  वाक्  (0x30, via Sanjnaa, erase)
 *   0x210500F0  — Anuvrtti write (blocked by Lopa boundary)
 *
 * Expected UART summary:
 *   sanjnaa_writes=0x02  lopa_erasures=0x01
 *   blocked_inheritances=0x01  VAK_after_lopa=0x00  SROTRA_shadow=0xFF
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
    volatile uint32_t sanjnaa_writes;        /* all resolved-symbol writes */
    volatile uint32_t lopa_erasures;
    volatile uint32_t blocked_inheritances;
    volatile uint32_t rejected_counter;
    volatile uint8_t  siddha_global_bus[256];
    volatile uint8_t  asiddha_shadow_cache[256];
    volatile uint8_t  prev_target;
    volatile uint8_t  lopa_boundary;
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
    uint8_t comp   = (uint8_t)((instr >> 24) & 0x0Fu);
    uint8_t opcode = (uint8_t)((instr >> 16) & 0xFFu);
    uint8_t target = (uint8_t)((instr >>  8) & 0xFFu);

    vm.instruction_counter++;
    uart_puts("[RV32 PVM] word=0x"); uart_hex32(instr);
    uart_puts(" op=0x"); uart_hex8(opcode);
    uart_puts(" target=0x"); uart_hex8(target);
    uart_puts("\r\n");

    /* Lopa: explicit erasure + boundary */
    if (opcode == PVM_OP_LOPA) {
        vm.lopa_erasures++;
        vm.siddha_global_bus[target] = 0x00u;
        vm.prev_target   = PVM_NULL_TARGET;
        vm.lopa_boundary = 1u;
        uart_puts("  LOPA: bus[0x"); uart_hex8(target);
        uart_puts("] erased -> 0x00, boundary set\r\n");
        return;
    }

    /* Anuvrtti: inherit target */
    if (comp == PVM_COMP_ANUVRTTI) {
        if (vm.lopa_boundary || vm.prev_target == PVM_NULL_TARGET) {
            vm.blocked_inheritances++;
            uart_puts("  LOPA BOUNDARY: Anuvrtti inheritance blocked\r\n");
            return;
        }
        target = vm.prev_target;
        uart_puts("  ANUVRTTI: inherited target=0x"); uart_hex8(target);
        uart_puts("\r\n");
    } else {
        vm.prev_target   = target;
        vm.lopa_boundary = 0u;
    }

    /* Write / Store */
    if (opcode == PVM_OP_WRITE) {
        vm.sanjnaa_writes++;
        if (target >= PVM_ASIDDHA_BASE) {
            vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
            uart_puts("  ASIDDHA shadow=0x");
            uart_hex8(vm.asiddha_shadow_cache[target]);
            uart_puts(" (Sanjnaa symbol resolved to 0x");
            uart_hex8(target); uart_puts(")\r\n");
        } else {
            vm.siddha_global_bus[target] = PVM_WRITE_VALUE;
            uart_puts("  SIDDHA global=0x");
            uart_hex8(vm.siddha_global_bus[target]);
            uart_puts(" (Sanjnaa symbol resolved to 0x");
            uart_hex8(target); uart_puts(")\r\n");
        }
    }
}

/* ---------- Summary ---------- */

static void print_summary(void) {
    uart_puts("[RV32 PVM SANJNAA SUMMARY]");
    uart_puts(" sanjnaa_writes=0x");       uart_hex8((uint8_t)vm.sanjnaa_writes);
    uart_puts(" lopa_erasures=0x");        uart_hex8((uint8_t)vm.lopa_erasures);
    uart_puts(" blocked_inheritances=0x"); uart_hex8((uint8_t)vm.blocked_inheritances);
    uart_puts(" VAK_after_lopa=0x");       uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" SROTRA_shadow=0x");        uart_hex8(vm.asiddha_shadow_cache[VDEV_SROTRA]);
    uart_puts(" rejected=0x");             uart_hex8((uint8_t)vm.rejected_counter);
    uart_puts("\r\n");
}

/* ---------- Entry point ---------- */

int main(void) {
    uint32_t offset;
    uart_puts("[RV32 PVM BOOT] Sprint 6 — Sanjnaa compile-time symbol resolution\r\n");

    for (offset = 0; offset < PVM_IMAGE_SIZE; offset += 4)
        execute_cycle(read_be32(&pvm_image[offset]));

    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) __asm__ volatile("wfi");
}
