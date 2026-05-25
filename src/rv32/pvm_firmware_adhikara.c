/*
 * pvm_firmware_adhikara.c -- Sprint 10: Adhikara privilege scope domains
 *
 * pvm_image is a uint8_t[] stored in big-endian (MSB first) byte order.
 * RV32 is little-endian, so we reassemble each 32-bit word explicitly:
 *   word = (b[0]<<24)|(b[1]<<16)|(b[2]<<8)|b[3]
 *
 * Expected ABI words (adhikara_core.pvm):
 *   0x200530F0  Write  Vak    (Ring2, outside scope)
 *   0x00AA00F0  ADHIKARA_OPEN
 *   0x00CC60F0  Store  Yantra (Ring0, inside scope)
 *   0x00BB00F0  ADHIKARA_CLOSE
 *   0x200530F0  Write  Vak    (Ring2, restored)
 *
 * Expected UART:
 *   ring2_writes=0x02  adhikara_opens=0x01  adhikara_closes=0x01
 *   ring0_stores=0x01  scope_restored=0x01
 *   VAK_bus=0xFF  YANTRA_shadow=0xFF
 */

#include "pvm_image.h"
#include <stdint.h>

/* MMIO addresses */
#define UART_BASE    0x10000000U
#define POWEROFF_REG 0x00100000U

/* Virtual device addresses */
#define BUS_VAK_ADDR    0x30U
#define BUS_YANTRA_ADDR 0x60U

/* ABI field extraction from a correctly reassembled big-endian word */
#define RING(w)   (((w) >> 28) & 0xFU)
#define OPCODE(w) (((w) >> 16) & 0xFFU)
#define TARGET(w) (((w) >>  8) & 0xFFU)

/* Scope sentinel opcodes */
#define OPCODE_ADHIKARA_OPEN  0xAAU
#define OPCODE_ADHIKARA_CLOSE 0xBBU
#define OPCODE_WRITE          0x05U
#define OPCODE_STORE          0xCCU

/* Ring levels */
#define RING_USER   0x2U
#define RING_KERNEL 0x0U

/* Number of 32-bit words in the image */
#define NWORDS (sizeof(pvm_image) / 4U)

/* ------------------------------------------------------------------ */
static const char HEX_DIGITS[] = "0123456789ABCDEF";

static void uart_putc(char c) {
    volatile uint8_t *uart = (volatile uint8_t *)UART_BASE;
    *uart = (uint8_t)c;
}

static void uart_puts(const char *s) {
    while (*s) uart_putc(*s++);
}

static void uart_put_hex8(uint32_t v) {
    uart_putc('0'); uart_putc('x');
    uart_putc(HEX_DIGITS[(v >> 4) & 0xFU]);
    uart_putc(HEX_DIGITS[ v       & 0xFU]);
}

static void uart_put_hex32(uint32_t v) {
    uart_putc('0'); uart_putc('x');
    for (int b = 28; b >= 0; b -= 4)
        uart_putc(HEX_DIGITS[(v >> b) & 0xFU]);
}

/* Read one big-endian 32-bit word from the byte image */
static uint32_t read_word(uint32_t idx) {
    const uint8_t *b = pvm_image + idx * 4U;
    return ((uint32_t)b[0] << 24)
         | ((uint32_t)b[1] << 16)
         | ((uint32_t)b[2] <<  8)
         |  (uint32_t)b[3];
}

/* ------------------------------------------------------------------ */
void main(void) {
    uint32_t nword = (uint32_t)NWORDS;

    /* Scope state */
    uint32_t scope_ring = RING_USER;

    /* Virtual device buses */
    uint8_t vak_bus       = 0x00U;
    uint8_t yantra_shadow = 0x00U;

    /* Counters */
    uint32_t ring2_writes    = 0U;
    uint32_t adhikara_opens  = 0U;
    uint32_t adhikara_closes = 0U;
    uint32_t ring0_stores    = 0U;
    uint32_t scope_restored  = 0U;

    uart_puts("[RV32 PVM BOOT] Sprint 10 -- Adhikara privilege scope\r\n");

    for (uint32_t i = 0U; i < nword; i++) {
        uint32_t w      = read_word(i);
        uint32_t opcode = OPCODE(w);
        uint32_t target = TARGET(w);

        uart_puts("[RV32 PVM] word=");
        uart_put_hex32(w);
        uart_puts(" op=");
        uart_put_hex8(opcode);
        uart_puts(" scope=Ring");
        uart_putc('0' + (char)scope_ring);
        uart_puts("\r\n");

        /* ---- Scope sentinels ---- */
        if (opcode == OPCODE_ADHIKARA_OPEN) {
            scope_ring = RING_KERNEL;
            adhikara_opens++;
            uart_puts("  ADHIKARA_OPEN: scope_ring -> Ring0\r\n");
            continue;
        }

        if (opcode == OPCODE_ADHIKARA_CLOSE) {
            scope_ring = RING_USER;
            adhikara_closes++;
            scope_restored++;
            uart_puts("  ADHIKARA_CLOSE: scope_ring -> Ring2\r\n");
            continue;
        }

        /* ---- Regular instructions ---- */
        if (opcode == OPCODE_WRITE && scope_ring == RING_USER) {
            if (target == BUS_VAK_ADDR) {
                vak_bus = 0xFFU;
                ring2_writes++;
                uart_puts("    WRITE Ring2 bus[0x30]=0xFF\r\n");
            }
        } else if (opcode == OPCODE_STORE && scope_ring == RING_KERNEL) {
            if (target == BUS_YANTRA_ADDR) {
                yantra_shadow = 0xFFU;
                ring0_stores++;
                uart_puts("    STORE Ring0 shadow[0x60]=0xFF\r\n");
            }
        }
    }

    /* ---- Summary ---- */
    uart_puts("[RV32 PVM ADHIKARA SUMMARY]");
    uart_puts(" ring2_writes=");    uart_put_hex8(ring2_writes);
    uart_puts(" adhikara_opens=");  uart_put_hex8(adhikara_opens);
    uart_puts(" adhikara_closes="); uart_put_hex8(adhikara_closes);
    uart_puts(" ring0_stores=");    uart_put_hex8(ring0_stores);
    uart_puts(" scope_restored=");  uart_put_hex8(scope_restored);
    uart_puts(" VAK_bus=");         uart_put_hex8(vak_bus);
    uart_puts(" YANTRA_shadow=");   uart_put_hex8(yantra_shadow);
    uart_puts("\r\n");

    /* Poweroff */
    *((volatile uint32_t *)POWEROFF_REG) = 0x5555U;
    while (1) {}
}
