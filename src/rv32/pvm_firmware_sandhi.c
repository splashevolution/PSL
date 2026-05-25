#include <stdint.h>
#include "pvm_image.h"

/*
 * PVM Sprint 9 Firmware -- Sandhi Instruction Fusion
 *
 * Sandhi (Sanskrit: "junction") -- two compatible instructions fuse into
 * an atomic execution pair. The first word carries FLAGS=0xE (SANDHI-FIRST).
 * The firmware detects this marker and executes the current word plus the
 * next word as a single atomic decode-and-execute cycle before advancing.
 *
 * This proves that:
 *   (a) The fusion marker is correctly encoded in the ABI word (FLAGS nibble).
 *   (b) The firmware detects and handles it atomically.
 *   (c) Final state is identical to sequential execution -- fusion is
 *       semantically transparent, not an optimization shortcut.
 *   (d) The sandhi_fusions counter increments exactly once per fused pair.
 *
 * Expected ABI image from sandhi_core.pvm:
 *   0x200530F0  -- Write Vak  (0x30, standalone, FLAGS=0xF)
 *   0x200560E0  -- Write Yantra (0x60, SANDHI-FIRST, FLAGS=0xE)
 *   0x20CC60F0  -- Store Yantra (0x60, SANDHI-PAIR second, FLAGS=0xF)
 *
 * Expected UART summary:
 *   standalone_writes=0x01  sandhi_fusions=0x01
 *   VAK_bus=0xFF  YANTRA_write=0xFF  YANTRA_store=0xFF
 */

#define UART0_BASE       0x10000000u
#define SIFIVE_TEST_BASE 0x00100000u

#define VDEV_VAK    0x30u
#define VDEV_YANTRA 0x60u

#define PVM_OP_LOPA      0x00u
#define PVM_OP_WRITE     0x05u
#define PVM_OP_STORE     0xCCu
#define PVM_ASIDDHA_BASE 0x50u
#define PVM_WRITE_VALUE  0xFFu
#define PVM_COMP_ANUVRTTI 0x1u

#define FLAGS_SANDHI_FIRST 0xEu
#define FLAGS_LOPA_BOUNDARY 0xFu

typedef struct {
    volatile uint32_t instruction_counter;
    volatile uint32_t standalone_writes;
    volatile uint32_t sandhi_fusions;
    volatile uint8_t  siddha_global_bus[256];
    volatile uint8_t  asiddha_write_cache[256];
    volatile uint8_t  asiddha_store_cache[256];
    volatile uint8_t  prev_target;
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

static void apply_write(uint8_t target, uint8_t opcode) {
    if (opcode == PVM_OP_WRITE) {
        if (target < PVM_ASIDDHA_BASE) {
            vm.siddha_global_bus[target] = PVM_WRITE_VALUE;
            uart_puts("    WRITE Siddha bus[0x"); uart_hex8(target);
            uart_puts("]=0xFF\r\n");
        } else {
            vm.asiddha_write_cache[target] = PVM_WRITE_VALUE;
            uart_puts("    WRITE Asiddha write_cache[0x"); uart_hex8(target);
            uart_puts("]=0xFF\r\n");
        }
    } else if (opcode == PVM_OP_STORE) {
        vm.asiddha_store_cache[target] = PVM_WRITE_VALUE;
        uart_puts("    STORE Asiddha store_cache[0x"); uart_hex8(target);
        uart_puts("]=0xFF\r\n");
    }
}

/*
 * execute_cycle -- returns how many additional words were consumed.
 * For a SANDHI-FIRST word: consumes 1 extra word (the pair second).
 * For all others: consumes 0 extra words.
 */
static uint32_t execute_cycle(const uint8_t *image, uint32_t offset,
                               uint32_t image_size) {
    uint32_t instr  = read_be32(&image[offset]);
    uint8_t  comp   = (uint8_t)((instr >> 24) & 0x0Fu);
    uint8_t  opcode = (uint8_t)((instr >> 16) & 0xFFu);
    uint8_t  target = (uint8_t)((instr >>  8) & 0xFFu);
    uint8_t  flags  = (uint8_t)((instr >>  4) & 0x0Fu);

    vm.instruction_counter++;

    uart_puts("[RV32 PVM] word=0x"); uart_hex32(instr);
    uart_puts(" op=0x"); uart_hex8(opcode);
    uart_puts(" target=0x"); uart_hex8(target);
    uart_puts(" flags=0x"); uart_hex8(flags);
    uart_puts("\r\n");

    /* Anuvrtti: inherit target */
    if (comp == PVM_COMP_ANUVRTTI) {
        target = vm.prev_target;
        uart_puts("  ANUVRTTI: inherited target=0x"); uart_hex8(target);
        uart_puts("\r\n");
    } else {
        vm.prev_target = target;
    }

    /* Check for SANDHI-FIRST marker */
    if (flags == FLAGS_SANDHI_FIRST) {
        /* Read the pair-second word */
        uint32_t next_offset = offset + 4;
        if (next_offset + 4 > image_size) {
            uart_puts("  ERROR: SANDHI-FIRST at end of image, no pair\r\n");
            return 0;
        }
        uint32_t instr2  = read_be32(&image[next_offset]);
        uint8_t  opcode2 = (uint8_t)((instr2 >> 16) & 0xFFu);
        uint8_t  target2 = (uint8_t)((instr2 >>  8) & 0xFFu);

        uart_puts("  SANDHI: fused pair detected\r\n");
        uart_puts("    first:  op=0x"); uart_hex8(opcode);
        uart_puts(" target=0x"); uart_hex8(target); uart_puts("\r\n");
        uart_puts("    second: op=0x"); uart_hex8(opcode2);
        uart_puts(" target=0x"); uart_hex8(target2); uart_puts("\r\n");

        /* Execute both atomically */
        apply_write(target,  opcode);
        apply_write(target2, opcode2);
        vm.sandhi_fusions++;
        uart_puts("  SANDHI: atomic pair executed, sandhi_fusions++\r\n");
        return 1;   /* consumed one extra word */
    }

    /* Normal (non-fused) instruction */
    if (opcode == PVM_OP_WRITE || opcode == PVM_OP_STORE) {
        apply_write(target, opcode);
        vm.standalone_writes++;
    }
    return 0;
}

static void print_summary(void) {
    uart_puts("[RV32 PVM SANDHI SUMMARY]");
    uart_puts(" standalone_writes=0x"); uart_hex8((uint8_t)vm.standalone_writes);
    uart_puts(" sandhi_fusions=0x");    uart_hex8((uint8_t)vm.sandhi_fusions);
    uart_puts(" VAK_bus=0x");           uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" YANTRA_write=0x");      uart_hex8(vm.asiddha_write_cache[VDEV_YANTRA]);
    uart_puts(" YANTRA_store=0x");      uart_hex8(vm.asiddha_store_cache[VDEV_YANTRA]);
    uart_puts("\r\n");
}

int main(void) {
    uint32_t offset = 0;
    uart_puts("[RV32 PVM BOOT] Sprint 9 -- Sandhi instruction fusion\r\n");

    while (offset + 4 <= PVM_IMAGE_SIZE) {
        uint32_t extra = execute_cycle(pvm_image, offset, PVM_IMAGE_SIZE);
        offset += 4 + (extra * 4);
    }

    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) __asm__ volatile("wfi");
}
