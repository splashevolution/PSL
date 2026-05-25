#include <stdint.h>

#include "pvm_image.h"

#define UART0_BASE 0x10000000u
#define SIFIVE_TEST_BASE 0x00100000u

#define VDEV_VAK 0x30u
#define VDEV_SROTRA 0x50u
#define VDEV_YANTRA 0x60u

#define PVM_OP_WRITE 0x05u
#define PVM_OP_STORE 0xCCu
#define PVM_RING_KERNEL 0x00u
#define PVM_ASIDDHA_BASE 0x50u
#define PVM_WRITE_VALUE 0xFFu

typedef struct {
    volatile uint32_t instruction_counter;
    volatile uint32_t rejected_instruction_counter;
    volatile uint8_t siddha_global_bus[256];
    volatile uint8_t asiddha_shadow_cache[256];
} PVMHardwareState;

static volatile PVMHardwareState vm;

static void uart_putc(char value) {
    *(volatile uint8_t *)UART0_BASE = (uint8_t)value;
}

static void uart_puts(const char *value) {
    while (*value != '\0') {
        uart_putc(*value++);
    }
}

static void uart_hex8(uint8_t value) {
    static const char hex[] = "0123456789ABCDEF";
    uart_putc(hex[(value >> 4) & 0x0F]);
    uart_putc(hex[value & 0x0F]);
}

static void uart_hex32(uint32_t value) {
    int shift;
    for (shift = 28; shift >= 0; shift -= 4) {
        static const char hex[] = "0123456789ABCDEF";
        uart_putc(hex[(value >> shift) & 0x0F]);
    }
}

static uint32_t read_be32(const uint8_t *buffer) {
    return ((uint32_t)buffer[0] << 24)
         | ((uint32_t)buffer[1] << 16)
         | ((uint32_t)buffer[2] << 8)
         | (uint32_t)buffer[3];
}

static int is_mutating_opcode(uint8_t opcode) {
    return opcode == PVM_OP_WRITE || opcode == PVM_OP_STORE;
}

static void execute_cycle(uint32_t instruction) {
    uint8_t ring = (uint8_t)((instruction >> 28) & 0x0F);
    uint8_t opcode = (uint8_t)((instruction >> 16) & 0xFF);
    uint8_t target = (uint8_t)((instruction >> 8) & 0xFF);

    vm.instruction_counter++;
    uart_puts("[RV32 PVM] word=0x");
    uart_hex32(instruction);
    uart_puts(" target=0x");
    uart_hex8(target);
    uart_puts("\r\n");

    if (target == VDEV_YANTRA && ring != PVM_RING_KERNEL) {
        vm.rejected_instruction_counter++;
        uart_puts("  FAULT: YANTRA requires Ring 0\r\n");
        return;
    }

    if (!is_mutating_opcode(opcode)) {
        uart_puts("  NO-MUTATION\r\n");
        return;
    }

    if (target >= PVM_ASIDDHA_BASE) {
        vm.asiddha_shadow_cache[target] = PVM_WRITE_VALUE;
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

static void print_summary(void) {
    uart_puts("[RV32 PVM SUMMARY] VAK global=0x");
    uart_hex8(vm.siddha_global_bus[VDEV_VAK]);
    uart_puts(" SROTRA global=0x");
    uart_hex8(vm.siddha_global_bus[VDEV_SROTRA]);
    uart_puts(" shadow=0x");
    uart_hex8(vm.asiddha_shadow_cache[VDEV_SROTRA]);
    uart_puts(" YANTRA global=0x");
    uart_hex8(vm.siddha_global_bus[VDEV_YANTRA]);
    uart_puts(" shadow=0x");
    uart_hex8(vm.asiddha_shadow_cache[VDEV_YANTRA]);
    uart_puts(" rejected=0x");
    uart_hex8((uint8_t)vm.rejected_instruction_counter);
    uart_puts("\r\n");
}

int main(void) {
    uint32_t offset;

    uart_puts("[RV32 PVM BOOT] Packed ABI image executing on QEMU virt UART MMIO\r\n");
    for (offset = 0; offset < PVM_IMAGE_SIZE; offset += 4) {
        execute_cycle(read_be32(&pvm_image[offset]));
    }
    print_summary();

    *(volatile uint32_t *)SIFIVE_TEST_BASE = 0x5555u;
    for (;;) {
        __asm__ volatile("wfi");
    }
}
