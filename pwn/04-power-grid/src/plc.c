#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CMD_APPLY_CONFIG 0x02
#define CMD_EMERGENCY    0xff
#define MAX_PACKET       8192

volatile uint64_t g_tick = 0;
char g_command_buf[8192];

typedef struct {
    char cmd_buf[128];
    uint64_t canary;
    void (*pivot)(uint64_t *);
    uint64_t *pivot_arg;
} command_frame_t;

static volatile uint64_t g_last_diag_sp = 0;

static uint16_t load_u16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint8_t checksum_packet(const uint8_t *packet, size_t pkt_len) {
    uint8_t c = 0xa5;

    for (size_t i = 0; i < pkt_len; i++) {
        if (i != 1) {
            c ^= packet[i];
            c = (uint8_t)((c << 1) | (c >> 7));
        }
    }
    return c;
}

__attribute__((noinline))
static uint64_t current_sp(void) {
    uint64_t sp;
    asm volatile("mov %0, sp" : "=r"(sp));
    return sp;
}

__attribute__((noinline))
static uint64_t generate_canary(uint64_t sp_context) {
    uint64_t raw = g_tick ^ (uint64_t)getpid() ^ sp_context ^ 0xdeadbeefULL;
    return raw * 0x1337133713371337ULL;
}

__attribute__((noinline))
void plc_emergency_dump(void) {
    uint64_t sp = current_sp();

    g_last_diag_sp = sp;
    dprintf(STDERR_FILENO,
            "[EMERG] SP=0x%016lx TICK=%llu PID=%d CODE=%p\n",
            sp, (unsigned long long)g_tick, (int)getpid(),
            (void *)plc_emergency_dump);
}

__attribute__((naked, noinline))
void stack_pivot(uint64_t *chain) {
    (void)chain;
    asm volatile(
        "mov sp, x0\n"
        "ldp x29, x30, [sp], #16\n"
        "ldp x0, x1, [sp], #16\n"
        "ret\n"
    );
}

__attribute__((noinline))
void handle_command(int out_fd, const uint8_t *packet, size_t pkt_len) {
    volatile command_frame_t frame;
    uint64_t sp_context = g_last_diag_sp ? g_last_diag_sp : current_sp();
    size_t copy_len = pkt_len >= 4 ? pkt_len - 4 : 0;

    memset((void *)&frame, 0, sizeof(frame));
    frame.canary = generate_canary(sp_context);

    if (copy_len != 0) {
        memcpy((void *)frame.cmd_buf, packet + 4, copy_len);
    }

    dprintf(out_fd, "[PLC] Command: %.*s\n", 32, (const char *)frame.cmd_buf);

    if (frame.canary != generate_canary(sp_context)) {
        write(STDERR_FILENO, "[PLC] Stack corruption!\n", 24);
        _exit(1);
    }

    g_tick++;

    if (frame.pivot != NULL) {
        frame.pivot((uint64_t *)frame.pivot_arg);
    }
}

static void apply_config(int out_fd, const uint8_t *packet, size_t pkt_len) {
    size_t data_len;

    if (pkt_len < 4) {
        return;
    }

    data_len = load_u16(packet + 2);
    if (data_len > pkt_len - 4) {
        data_len = pkt_len - 4;
    }
    if (data_len > sizeof(g_command_buf) - 1) {
        data_len = sizeof(g_command_buf) - 1;
    }

    memcpy(g_command_buf, packet + 4, data_len);
    g_command_buf[data_len] = '\0';
    g_tick++;
    write(out_fd, "[PLC] Config loaded.\n", 21);
}

void handle_connection(int in_fd, int out_fd) {
    uint8_t pkt[MAX_PACKET];
    uint16_t pkt_len;

    while (1) {
        ssize_t got = read(in_fd, &pkt_len, sizeof(pkt_len));
        if (got == 0) {
            break;
        }
        if (got != (ssize_t)sizeof(pkt_len)) {
            break;
        }
        if (pkt_len > sizeof(pkt)) {
            write(out_fd, "[PLC] Packet too large.\n", 24);
            break;
        }
        if (read(in_fd, pkt, pkt_len) != (ssize_t)pkt_len) {
            break;
        }
        if (pkt_len < 4) {
            write(out_fd, "[PLC] Bad packet.\n", 18);
            continue;
        }

        if (pkt[0] == CMD_EMERGENCY && pkt[1] != checksum_packet(pkt, pkt_len)) {
            plc_emergency_dump();
            continue;
        }

        if (pkt[0] == CMD_APPLY_CONFIG) {
            apply_config(out_fd, pkt, pkt_len);
        } else {
            handle_command(out_fd, pkt, pkt_len);
            write(out_fd, "[PLC] Command processed.\n", 25);
        }
    }
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    if (getpid() == -1) {
        system("true");
    }

    handle_connection(STDIN_FILENO, STDOUT_FILENO);
    return 0;
}
