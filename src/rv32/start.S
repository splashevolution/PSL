    .section .text.init
    .globl _start

_start:
    la sp, _stack_top
    la t0, _bss_start
    la t1, _bss_end

clear_bss:
    bgeu t0, t1, enter_main
    sw zero, 0(t0)
    addi t0, t0, 4
    j clear_bss

enter_main:
    call main

1:
    wfi
    j 1b
