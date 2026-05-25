OUTPUT_ARCH(riscv)
ENTRY(_start)

PHDRS
{
    text PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
}

MEMORY
{
    ram (rwx) : ORIGIN = 0x80000000, LENGTH = 128M
}

SECTIONS
{
    . = ORIGIN(ram);

    .text : {
        KEEP(*(.text.init))
        *(.text*)
    } > ram :text

    .rodata : {
        *(.rodata*)
    } > ram :text

    .data : {
        *(.data*)
    } > ram :data

    .bss : {
        _bss_start = .;
        *(.bss*)
        *(COMMON)
        _bss_end = .;
    } > ram :data

    . = ALIGN(16);
    . += 4096;
    _stack_top = .;
}
