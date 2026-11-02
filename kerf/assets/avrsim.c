/* kerf avrsim: run a compiled Arduino Nano sketch (ATmega328P ELF) in simavr and record what it does to the outside world.
 *
 * Built by kerf/fwcheck.py against libsimavr (apt simavr + libsimavr-dev; Homebrew osx-cross/avr/simavr).
 *   avrsim <firmware.elf> <end_ms> [<at_ms>:<serial text> ...]      (each text is sent followed by '\n')
 * Prints, one record per line:
 *   P <arduino pin> <rise us> <high us>   a high pulse on a digital pin (D0-D13, A0-A5 = 14-19)
 *   U <ms> <text>                         a line the sketch printed on Serial
 *   I <us> <register> <value>             a register write to a PCA9685 at I2C address 0x40, as the chip would apply it
 *                                         (auto-increment only when MODE1.AI is set; PRE_SCALE only while MODE1.SLEEP)
 *   N <us> <8-bit address>                an I2C address nobody answers (NACK)
 *   END <ms> <cpu state>
 * The PCA9685 model answers reads from its register file too (the Adafruit library reads MODE1 and PRE_SCALE back).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sim_avr.h"
#include "sim_elf.h"
#include "sim_irq.h"
#include "avr_ioport.h"
#include "avr_uart.h"
#include "avr_twi.h"

static avr_t *avr;
static double us_of(avr_cycle_count_t c) { return (double)c * 1e6 / avr->frequency; }

/* ---- digital pins: rising edge -> remember, falling edge -> print the pulse */
static avr_cycle_count_t rise[20];
static int level[20];
static void pin_hook(avr_irq_t *irq, uint32_t value, void *param) {
    int pin = (int)(intptr_t)param;
    int v = value ? 1 : 0;
    if (v == level[pin]) return;
    level[pin] = v;
    if (v) rise[pin] = avr->cycle;
    else if (rise[pin]) printf("P %d %.3f %.3f\n", pin, us_of(rise[pin]), us_of(avr->cycle - rise[pin]));
}

/* ---- Serial output, line by line */
static char line[512];
static int nline;
static void uart_hook(avr_irq_t *irq, uint32_t value, void *param) {
    char c = (char)value;
    if (c == '\r') return;
    if (c == '\n' || nline == (int)sizeof(line) - 1) {
        line[nline] = 0;
        printf("U %.3f %s\n", us_of(avr->cycle) / 1000.0, line);
        nline = 0;
        return;
    }
    line[nline++] = c;
}

/* ---- PCA9685 on the I2C bus (8-bit address 0x80/0x81) */
static avr_irq_t *twi_irq;          /* our two irqs: [0] = to the AVR (input), [1] = from the AVR (output) */
static uint8_t reg[256];
static int selected, have_ptr;
static uint8_t ptr;
static void twi_hook(avr_irq_t *irq, uint32_t value, void *param) {
    avr_twi_msg_irq_t v;
    v.u.v = value;
    if (v.u.twi.msg & TWI_COND_STOP) { selected = 0; have_ptr = 0; }
    if (v.u.twi.msg & TWI_COND_START) {
        selected = 0; have_ptr = 0;
        if ((v.u.twi.addr & 0xFE) == 0x80) {
            selected = v.u.twi.addr;
            avr_raise_irq(twi_irq + TWI_IRQ_INPUT, avr_twi_irq_msg(TWI_COND_ACK, selected, 1));
        } else {
            printf("N %.3f %d\n", us_of(avr->cycle), v.u.twi.addr);
        }
    }
    if (!selected) return;
    if (v.u.twi.msg & TWI_COND_WRITE) {
        avr_raise_irq(twi_irq + TWI_IRQ_INPUT, avr_twi_irq_msg(TWI_COND_ACK, selected, 1));
        if (!have_ptr) { ptr = v.u.twi.data; have_ptr = 1; return; }
        uint8_t d = v.u.twi.data;
        if (ptr == 0xFE && !(reg[0] & 0x10)) {           /* PRE_SCALE is write-protected unless MODE1.SLEEP */
            printf("I %.3f %d %d ignored\n", us_of(avr->cycle), ptr, d);
        } else {
            reg[ptr] = d;
            printf("I %.3f %d %d\n", us_of(avr->cycle), ptr, d);
        }
        if (reg[0] & 0x20) ptr++;                         /* MODE1.AI */
    }
    if (v.u.twi.msg & TWI_COND_READ) {
        uint8_t d = reg[ptr];
        if (reg[0] & 0x20) ptr++;
        avr_raise_irq(twi_irq + TWI_IRQ_INPUT, avr_twi_irq_msg(TWI_COND_READ, selected, d));
    }
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: avrsim <elf> <end_ms> [<at_ms>:<text> ...]\n"); return 2; }
    elf_firmware_t f;
    memset(&f, 0, sizeof f);
    if (elf_read_firmware(argv[1], &f)) { fprintf(stderr, "cannot read %s\n", argv[1]); return 2; }
    avr = avr_make_mcu_by_name("atmega328p");
    if (!avr) { fprintf(stderr, "simavr has no atmega328p\n"); return 2; }
    avr_init(avr);
    f.frequency = 16000000;                               /* Nano: 16 MHz crystal */
    avr_load_firmware(avr, &f);
    avr->frequency = 16000000;
    avr->log = 0;

    const char ports[3] = {'D', 'B', 'C'};               /* D0-7 = PORTD, D8-13 = PORTB0-5, A0-5 = PORTC0-5 */
    for (int p = 0; p < 3; p++)
        for (int b = 0; b < 8; b++) {
            int pin = p == 0 ? b : p == 1 ? 8 + b : 14 + b;
            if (pin >= 20 || (p > 0 && b > 5)) continue;
            avr_irq_register_notify(avr_io_getirq(avr, AVR_IOCTL_IOPORT_GETIRQ(ports[p]), b), pin_hook, (void *)(intptr_t)pin);
        }

    uint32_t fl = 0;
    avr_ioctl(avr, AVR_IOCTL_UART_GET_FLAGS('0'), &fl);
    fl &= ~(AVR_UART_FLAG_STDIO | AVR_UART_FLAG_POLL_SLEEP);
    avr_ioctl(avr, AVR_IOCTL_UART_SET_FLAGS('0'), &fl);
    avr_irq_register_notify(avr_io_getirq(avr, AVR_IOCTL_UART_GETIRQ('0'), UART_IRQ_OUTPUT), uart_hook, NULL);
    avr_irq_t *uart_in = avr_io_getirq(avr, AVR_IOCTL_UART_GETIRQ('0'), UART_IRQ_INPUT);

    static const char *names[] = {"twi.in", "twi.out"};
    twi_irq = avr_alloc_irq(&avr->irq_pool, 0, 2, names);
    avr_connect_irq(twi_irq + TWI_IRQ_INPUT, avr_io_getirq(avr, AVR_IOCTL_TWI_GETIRQ(0), TWI_IRQ_INPUT));
    avr_connect_irq(avr_io_getirq(avr, AVR_IOCTL_TWI_GETIRQ(0), TWI_IRQ_OUTPUT), twi_irq + TWI_IRQ_OUTPUT);
    avr_irq_register_notify(twi_irq + TWI_IRQ_OUTPUT, twi_hook, NULL);

    avr_cycle_count_t end = (avr_cycle_count_t)(atof(argv[2]) * 16000.0);
    int next = 3, state = cpu_Running;
    while (avr->cycle < end) {
        while (next < argc && avr->cycle >= (avr_cycle_count_t)(atof(argv[next]) * 16000.0)) {
            const char *t = strchr(argv[next], ':');
            for (t = t ? t + 1 : ""; *t; t++) avr_raise_irq(uart_in, (uint8_t)*t);
            avr_raise_irq(uart_in, '\n');
            next++;
        }
        state = avr_run(avr);
        if (state == cpu_Done || state == cpu_Crashed) break;
    }
    printf("END %.3f %d\n", us_of(avr->cycle) / 1000.0, state);
    return state == cpu_Crashed ? 3 : 0;
}
