# RV32 QEMU Virt Proof Record - 2026-05-23

## Claim Tested

The packed PVM ABI image produced from `isolation_core.pvm` can be embedded into
a freestanding RV32 firmware image, decoded after reset, and produce observable
Siddha/Asiddha state results while reporting through a system-emulated UART MMIO
device.

## Environment

- Guest execution host: Lubuntu VM over SSH
- Cross-compiler: `riscv64-unknown-elf-gcc (14.2.0+19) 14.2.0`
- Emulator: `QEMU emulator version 10.2.1`
- Machine: `qemu-system-riscv32 -M virt -nographic -bios none`

## Compiled PVM ABI Image

```text
ABI_EMIT 0x2005300F
ABI_EMIT 0x2005500F
ABI_EMIT 0x2005600F
ABI_EMIT 0x00CC600F
```

## Live QEMU Device-Tree Evidence

The QEMU-generated device tree reported:

```text
memory@80000000 {
    reg = <0x00 0x80000000 0x00 0x8000000>;
};

serial@10000000 {
    reg = <0x00 0x10000000 0x00 0x100>;
};

test@100000 {
    reg = <0x00 0x100000 0x00 0x1000>;
    compatible = "sifive,test1", "sifive,test0", "syscon";
};
```

## Firmware Build Evidence

```text
text    data    bss    dec    hex    filename
1427    0       520    1947   79b    pvm_rv32.elf

.text    VMA 80000000
.rodata  VMA 80000448
.bss     VMA 80000598
```

## Execution Output

```text
[RV32 PVM BOOT] Packed ABI image executing on QEMU virt UART MMIO
[RV32 PVM] word=0x2005300F target=0x30
  SIDDHA global=0xFF
[RV32 PVM] word=0x2005500F target=0x50
  ASIDDHA shadow=0xFF global=0x00
[RV32 PVM] word=0x2005600F target=0x60
  FAULT: YANTRA requires Ring 0
[RV32 PVM] word=0x00CC600F target=0x60
  ASIDDHA shadow=0xFF global=0x00
[RV32 PVM SUMMARY] VAK global=0xFF SROTRA global=0x00 shadow=0xFF YANTRA global=0x00 shadow=0xFF rejected=0x01
```

## Conclusion

This test verifies a freestanding RV32 firmware execution path under full-system
QEMU emulation, using the compiled PVM ABI image and observable UART MMIO output.
It establishes system-emulated MMIO behavior and RAM-backed isolation state. It
does not claim physical GPIO, physical SRAM, fabricated silicon, or HDL
implementation.
