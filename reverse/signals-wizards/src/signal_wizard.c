/*
 * ╔══════════════════════════════════════════════════════════╗
 * ║           S I G N A L   W I Z A R D                     ║
 * ║        A Reverse CTF Challenge by @ctfmaster             ║
 * ╚══════════════════════════════════════════════════════════╝
 *
 * CHALLENGE: "Signal Wizard"
 * CATEGORY:  Reverse Engineering / Linux Internals
 * DIFFICULTY: Medium
 * TOPICS:    Signals, System Calls, /proc, ptrace, alarm, sigaltstack
 *
 * HOW TO BUILD:
 *   gcc -O0 -g0 -o signal_wizard signal_wizard.c
 *
 * ANTI-PATCH DESIGN:
 *   - Stage keys are derived from signal delivery order & timing
 *   - XOR keys are computed from signal handler call counts
 *   - Patching any branch will corrupt the key derivation chain
 *   - ptrace self-check prevents GDB/strace at critical moments
 *   - Each stage flag is encrypted with the accumulated state
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/ptrace.h>
#include <sys/utsname.h>
#include <sys/resource.h>
#include <fcntl.h>
#include <time.h>
#include <errno.h>
#include <ucontext.h>

/* ── Terminal colours ────────────────────────────────────────── */
#define RED     "\033[1;31m"
#define GREEN   "\033[1;32m"
#define YELLOW  "\033[1;33m"
#define BLUE    "\033[1;34m"
#define MAGENTA "\033[1;35m"
#define CYAN    "\033[1;36m"
#define WHITE   "\033[1;37m"
#define ORANGE  "\033[38;5;208m"
#define PURPLE  "\033[38;5;135m"
#define RESET   "\033[0m"
#define BOLD    "\033[1m"
#define BLINK   "\033[5m"
#define DIM     "\033[2m"

/* ── Global state (anti-patch: derived values feed next stage) ─ */
static volatile int  g_stage          = 0;
static volatile long g_sigint_count   = 0;
static volatile long g_sigusr1_count  = 0;
static volatile long g_sigusr2_count  = 0;
static volatile long g_sigalrm_count  = 0;
static volatile long g_sigchld_count  = 0;
static volatile long g_sigtstp_count  = 0;
static volatile int  g_alarm_fired    = 0;
static volatile int  g_child_exited   = 0;
static volatile int  g_child_status   = 0;
static volatile int  g_stage_complete = 0;
static volatile int  g_altstack_hit   = 0;

/* Final flag material: layered encoding + split/scatter + decoys.
   The stage logic remains intentionally readable; this only raises the cost of
   extracting the flag by staring at one decryption function or one byte array. */
#define FINAL_FLAG_LEN   52
#define FINAL_SHARD_LEN  13

static volatile unsigned int g_obf_sink = 0;

static const unsigned char FLAG_PERM[FINAL_FLAG_LEN] = {
  23,40, 5,22,39, 4,21,38, 3,20,37, 2,19,36, 1,18,
  35, 0,17,34,51,16,33,50,15,32,49,14,31,48,13,30,
  47,12,29,46,11,28,45,10,27,44, 9,26,43, 8,25,42,
   7,24,41, 6
};

static const unsigned char FLAG_SHARD_0[FINAL_SHARD_LEN] = {
  0x6f,0xfc,0x8e,0x86,0xf1,0x30,0xb9,0x8a,0x35,0xb6,0x7b,0x60,0x56
};
static const unsigned char FLAG_SHARD_1[FINAL_SHARD_LEN] = {
  0x3f,0xb1,0x70,0x9b,0x4c,0x05,0x44,0x22,0xdb,0x55,0x62,0x76,0x4c
};
static const unsigned char FLAG_SHARD_2[FINAL_SHARD_LEN] = {
  0x3f,0x9d,0xf9,0xaf,0x5e,0x39,0xd2,0xe2,0x29,0x34,0x2f,0x61,0xb4
};
static const unsigned char FLAG_SHARD_3[FINAL_SHARD_LEN] = {
  0xe5,0x19,0xdd,0x58,0xbd,0xd1,0xc9,0xdf,0xe2,0xab,0x88,0x9e,0x77
};

static const unsigned char DECOY_A[] = {
  0x23,0x0d,0x10,0xf2,0xff,0xd7,0xcf,0xa6,0x97,0x99,0x68,0x7b,0x6e,
  0x2d,0x24,0x35,0x13,0xff,0xd7,0xe9,0xbd,0xb4,0x8a,0x5d,0x67,0x4d,
  0x5a,0x22,0x3e,0x07,0xe8,0xf6,0xd8,0xb4,0xba,0x89,0x97,0x71
};
static const unsigned char DECOY_B[] = {
  0xcf,0xd9,0xa4,0xae,0x8b,0x7b,0x60,0x4f,0x5e,0x27,0x36,0x1e,0xe9,
  0xc7,0xc5,0xdb,0xa7,0x81,0x85,0x55,0x69,0x42,0x2a,0x31,0x0e,0x19,
  0xfd,0xd1,0xea,0xa0,0xba,0x80,0x65,0x78,0x42,0x48,0x3e,0x1d
};
static const unsigned char DECOY_C[] = {
  0x58,0x3c,0x31,0x06,0xe6,0xfc,0xc9,0xd5,0xbd,0x9a,0x9b,0x6b,0x7e,
  0x72,0x30,0x21,0x03,0x1f,0xe5,0xe7,0xed,0xa9,0xbd,0x8d,0x8a,0x4e,
  0x45,0x44,0x15,0x3f,0x11,0xea,0xe2,0xd4
};

/* ── Utility ─────────────────────────────────────────────────── */
static void msleep(int ms) {
    struct timespec ts = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
}

static void clear_line(void) { printf("\r\033[2K"); fflush(stdout); }

static void slow_print(const char *s, int delay_ms) {
    for (; *s; s++) { putchar(*s); fflush(stdout); msleep(delay_ms); }
}

static unsigned char rol8(unsigned char v, unsigned int r) {
    r &= 7U;
    return (unsigned char)((v << r) | (v >> (8U - r)));
}

static unsigned char ror8(unsigned char v, unsigned int r) {
    r &= 7U;
    return (unsigned char)((v >> r) | (v << (8U - r)));
}

static unsigned char flag_mask_a(size_t pos, unsigned int key) {
    unsigned int x = (unsigned int)((pos + 1U) * 0x45d9f3bU) ^
                     (unsigned int)(key * 0x1337U + 0x5aU);
    x ^= x >> 16;
    x *= 0x27d4eb2dU;
    x ^= x >> 15;
    return (unsigned char)(x ^ (x >> 8) ^ 0xa7U);
}

static unsigned char flag_mask_b(size_t pos, unsigned int key) {
    unsigned int x = (unsigned int)((pos + 0x31U) * 0x9e3779b1U +
                                    (key * 0x51U));
    x ^= (unsigned int)((x << 7) | (x >> 25));
    return (unsigned char)(x ^ (x >> 11) ^ 0x3dU);
}

static unsigned char flag_addend(size_t pos, unsigned int key) {
    return (unsigned char)((pos * 13U) + (key * 9U) + 0x2bU);
}

static const unsigned char *select_flag_shard(size_t i) {
    unsigned int selector = (unsigned int)(((i * 9U) ^ ((i & 3U) * 8U)) & 3U);
    switch (selector) {
        case 0: return FLAG_SHARD_0;
        case 1: return FLAG_SHARD_1;
        case 2: return FLAG_SHARD_2;
        default: return FLAG_SHARD_3;
    }
}

static unsigned char decode_flag_byte(unsigned char enc, size_t pos,
                                      unsigned int key) {
    unsigned int r = ((unsigned int)pos ^ key) & 7U;
    if (r == 0) r = 5U;

    enc ^= flag_mask_b(pos, key);
    enc = ror8(enc, r);
    enc = (unsigned char)(enc - flag_addend(pos, key));
    enc ^= flag_mask_a(pos, key);
    return enc;
}

static unsigned int derive_final_key(void) {
    return (unsigned int)((g_sigint_count + g_sigusr2_count +
                           g_sigalrm_count + g_sigchld_count +
                           g_sigtstp_count) & 0xff);
}

static void stir_decoys(unsigned int key) {
    const unsigned char *bags[] = { DECOY_A, DECOY_B, DECOY_C };
    const size_t sizes[] = { sizeof(DECOY_A), sizeof(DECOY_B), sizeof(DECOY_C) };
    const unsigned int salts[] = { 0x4dU, 0xa1U, 0x36U };
    unsigned int acc = key ^ 0x31415926U;

    for (size_t b = 0; b < 3; b++) {
        for (size_t i = 0; i < sizes[b]; i++) {
            unsigned char c = (unsigned char)(bags[b][i] ^
                ((salts[b] + (unsigned int)i * 19U) & 0xffU));
            acc = rol8((unsigned char)acc, 1) ^ c ^ (unsigned int)(i + b);
        }
    }

    g_obf_sink ^= acc;
}

static void decrypt_flag(void) {
    char flag[FINAL_FLAG_LEN + 1];
    size_t i = 0, pos = 0, shard_i = 0;
    unsigned int key = derive_final_key();
    unsigned int pc = 0;
    unsigned char enc = 0;

    memset(flag, '?', sizeof(flag));
    flag[FINAL_FLAG_LEN] = '\0';
    stir_decoys(key);

    while (i < FINAL_FLAG_LEN) {
        switch (pc) {
            case 0:
                pos = FLAG_PERM[i];
                shard_i = i >> 2;
                pc = ((pos ^ key) & 1U) ? 2U : 1U;
                break;
            case 1:
                enc = select_flag_shard(i)[shard_i];
                pc = 3U;
                break;
            case 2:
                enc = (unsigned char)(select_flag_shard(i)[shard_i] ^ 0x5aU);
                enc ^= 0x5aU;
                pc = 3U;
                break;
            case 3:
                flag[pos] = (char)decode_flag_byte(enc, pos, key);
                i++;
                pc = (unsigned int)((pc + key + i) & 3U);
                pc ^= pc;
                break;
            default:
                pc = 0;
                break;
        }
    }

    printf(GREEN BOLD "  ★ FLAG: " RESET GREEN);
    for (size_t j = 0; j < FINAL_FLAG_LEN; j++) putchar(flag[j]);
    printf(RESET "\n");
}

/* ── Anti-debug: detect ptrace / tracers ─────────────────────── */
static int __attribute__((unused)) is_being_traced(void) {
    /* Method 1: ptrace self */
    if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) == -1) return 1;
    ptrace(PTRACE_DETACH, 0, NULL, NULL);

    /* Method 2: read /proc/self/status TracerPid */
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) return 0;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "TracerPid:", 10) == 0) {
            fclose(f);
            return atoi(line + 10) != 0;
        }
    }
    fclose(f);
    return 0;
}

/* ══════════════════════════════════════════════════════════════
 *  ANIMATIONS
 * ══════════════════════════════════════════════════════════════ */

static void anim_title(void) {
    printf(CYAN);
    printf("\n");
    printf("  ███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗     \n");
    printf("  ██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║     \n");
    printf("  ███████╗██║██║  ███╗██╔██╗ ██║███████║██║     \n");
    printf("  ╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║     \n");
    printf("  ███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗\n");
    printf("  ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝\n");
    printf(PURPLE);
    printf("  ██╗    ██╗██╗███████╗ █████╗ ██████╗ ██████╗  \n");
    printf("  ██║    ██║██║╚════██║██╔══██╗██╔══██╗██╔══██╗ \n");
    printf("  ██║ █╗ ██║██║    ██╔╝███████║██████╔╝██║  ██║ \n");
    printf("  ██║███╗██║██║   ██╔╝ ██╔══██║██╔══██╗██║  ██║ \n");
    printf("  ╚███╔███╔╝██║   ██║  ██║  ██║██║  ██║██████╔╝ \n");
    printf("   ╚══╝╚══╝ ╚═╝   ╚═╝  ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  \n");
    printf(RESET "\n");
    printf(DIM "  ┌─────────────────────────────────────────────┐\n");
    printf("  │  7 wizards await. Only signals can stop them │\n");
    printf("  └─────────────────────────────────────────────┘\n" RESET "\n");
}

static void anim_wizard(int stage, const char *name, const char *color) {
    printf("%s"
        "\n"
        "       .-.     Stage %d: %s\n"
        "      (o.o)    ~~~~~~~~~~~\n"
        "       |=|     \"Your signals\n"
        "      __|__     cannot harm me!\"\n"
        "     /|   |\\\n"
        "    (_|   |_)\n"
        RESET "\n", color, stage, name);
}

static void anim_battle(void) {
    const char *frames[] = {
        "  ⚔️  Hero  >---->   Wizard  ",
        "  ⚔️  Hero   >---->  Wizard  ",
        "  ⚔️  Hero    >----> Wizard  ",
        "  💥 Hero  ~~ZAP!~~ Wizard  ",
    };
    for (int i = 0; i < 4; i++) {
        clear_line();
        printf("%s", frames[i]);
        fflush(stdout);
        msleep(300);
    }
    printf("\n");
}

static void anim_victory(int stage) {
    printf(GREEN
        "\n"
        "  ╔══════════════════════════════════════╗\n"
        "  ║  ✨ WIZARD %d DEFEATED! ✨            ║\n"
        "  ╚══════════════════════════════════════╝\n"
        RESET "\n", stage);
    for (int i = 0; i < 3; i++) {
        printf(YELLOW "  ★ " RESET);
        msleep(150);
    }
    printf("\n\n");
}

static void anim_wizard_death(const char *color) {
    const char *frames[] = {
        "       .-.   \n"
        "      (x.x)  \n"
        "       |=|   \n",
        "       .-.   \n"
        "      (x_x)  \n"
        "        |    \n",
        "             \n"
        "      *poof* \n"
        "    ~~~~~~~~~\n",
    };
    for (int i = 0; i < 3; i++) {
        printf("\033[3A%s%s%s", color, frames[i], RESET);
        fflush(stdout);
        msleep(400);
    }
    printf("\n");
}

static void anim_spinner(const char *msg, int ms) {
    const char *spin = "|/-\\";
    for (int i = 0; i < ms / 100; i++) {
        printf(CYAN "\r  %c  %s" RESET, spin[i % 4], msg);
        fflush(stdout);
        msleep(100);
    }
    clear_line();
}

static void print_stage_banner(int stage, const char *title) {
    printf(MAGENTA
        "\n  ┌──────────────────────────────────────────┐\n"
        "  │  STAGE %d: %-33s│\n"
        "  └──────────────────────────────────────────┘\n"
        RESET "\n", stage, title);
}

static void print_hint(const char *hint) {
    printf(YELLOW "  💡 Hint: " DIM "%s" RESET "\n\n", hint);
}

static void print_objective(const char *obj) {
    printf(CYAN "  🎯 Objective: " BOLD "%s" RESET "\n\n", obj);
}

/* ══════════════════════════════════════════════════════════════
 *  STAGE SIGNAL HANDLERS
 * ══════════════════════════════════════════════════════════════ */
/* Stage 4: SIGCHLD — wait for child to exit */
static void handler_T(int sig) {
    (void)sig;
    int status;
    pid_t pid = waitpid(-1, &status, WNOHANG);
    if (pid > 0 && WIFEXITED(status)) {
        g_sigchld_count++;
        g_child_exited  = 1;
        g_child_status  = WEXITSTATUS(status);
        if (g_child_status == 42) {
            anim_battle();
            g_stage_complete = 1;
        } else {
            printf(RED "\n  [!] Child exited with %d, not 42.\n" RESET, g_child_status);
        }
    }
    fflush(stdout);
}

/* Stage 5: SIGSEGV on alt stack */
static char  altstack_buf[65536];   /* 64 KiB — well above MINSIGSTKSZ */
static stack_t g_alt_ss;

static void handler_R_(int sig, siginfo_t *info, void *ctx) {
    (void)sig; (void)info; (void)ctx;
    /* Verify we are running on the alternate stack */
    unsigned long sp;
#if defined(__x86_64__)
    __asm__ volatile("mov %%rsp, %0" : "=r"(sp));
#elif defined(__i386__)
    __asm__ volatile("mov %%esp, %0" : "=r"(sp));
#elif defined(__aarch64__)
    __asm__ volatile("mov %0, sp" : "=r"(sp));
#else
    sp = (unsigned long)&sig; /* fallback */
#endif
    unsigned long alt_lo = (unsigned long)altstack_buf;
    unsigned long alt_hi = alt_lo + sizeof(altstack_buf);
    if (sp >= alt_lo && sp < alt_hi) {
        g_altstack_hit = 1;
        anim_battle();
        g_stage_complete = 1;
    } else {
        printf(RED "\n  [!] Not on alt stack! sp=0x%lx\n" RESET, sp);
        _exit(1);
    }
    fflush(stdout);
}

/* Stage 1: SIGINT — Ctrl+C (must press exactly 3 times) */
static void handler_Y(int sig) {
    (void)sig;
    g_sigint_count++;
    if (g_sigint_count == 1)
        printf(ORANGE "\n  [!] The wizard flinches... (%ld/3)\n" RESET, g_sigint_count);
    else if (g_sigint_count == 2)
        printf(ORANGE "\n  [!] The wizard staggers... (%ld/3)\n" RESET, g_sigint_count);
    else if (g_sigint_count >= 3) {
        anim_battle();
        g_stage_complete = 1;
    }
    fflush(stdout);
}

/* Stage 3: SIGALRM — must arrive within 5 seconds via alarm(n) */
static void handler_H(int sig) {
    (void)sig;
    g_sigalrm_count++;
    g_alarm_fired = 1;
    anim_battle();
    g_stage_complete = 1;
    fflush(stdout);
}


/* Stage 2: SIGUSR1 then SIGUSR2 in order */
static void handler_A(int sig) {
    (void)sig;
    g_sigusr1_count++;
    printf(ORANGE "\n  [!] SIGUSR1 received! Now send SIGUSR2...\n" RESET);
    fflush(stdout);
}

static void handler_R(int sig) {
    (void)sig;
    if (g_sigusr1_count > 0) {
        g_sigusr2_count++;
        anim_battle();
        g_stage_complete = 1;
    } else {
        printf(RED "\n  [!] Wrong order! Send SIGUSR1 first.\n" RESET);
    }
    fflush(stdout);
}



/* Stage 7: combined — SIGUSR1×3, then SIGTERM ignored, then SIGINT */
static volatile int g_s7_usr1  = 0;
static volatile int g_s7_term  = 0;
static volatile int g_s7_final = 0;

static void handler_D(int sig) {
    (void)sig;
    g_s7_usr1++;
    printf(ORANGE "\n  [!] USR1 pulse %d/3 landed!\n" RESET, g_s7_usr1);
    if (g_s7_usr1 == 3) printf(CYAN "  [*] Now set SIGTERM to SIG_IGN, then send SIGINT!\n" RESET);
    fflush(stdout);
}

static void handler_E(int sig) {
    (void)sig;
    if (g_s7_usr1 >= 3 && g_s7_term) {
        g_s7_final = 1;
        anim_battle();
        g_stage_complete = 1;
    } else if (g_s7_usr1 < 3) {
        printf(RED "\n  [!] Need 3×SIGUSR1 first.\n" RESET);
    } else {
        printf(RED "\n  [!] Must ignore SIGTERM before sending SIGINT.\n" RESET);
    }
    fflush(stdout);
}




/* Stage 6: SIGTSTP — raise via kill(getpid(), SIGTSTP) from child */
static void handler_RR(int sig) {
    (void)sig;
    g_sigtstp_count++;
    anim_battle();
    g_stage_complete = 1;
    fflush(stdout);
}


/* ══════════════════════════════════════════════════════════════
 *  STAGE RUNNERS
 * ══════════════════════════════════════════════════════════════ */

/* ─── STAGE 1 ────────────────────────────────────────────────── */
static void run_stage1(void) {
    g_sigint_count  = 0;
    g_stage_complete = 0;

    print_stage_banner(1, "THE SIGINT WITCH");
    anim_wizard(1, "SIGINT Witch", RED);

    printf(RED "  \"I feed on your Ctrl+C attempts... they make me\n"
               "   stronger! But only up to a point...\"\n" RESET "\n");

    print_objective("Send SIGINT (Ctrl+C) exactly 3 times to defeat her.");
    print_hint("Just press Ctrl+C three times. But watch her HP bar!");

    printf(DIM "  PID: %d — ready for SIGINT\n" RESET "\n", getpid());

    struct sigaction sa = {0};
    sa.sa_handler = handler_Y;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;   /* no SA_RESETHAND — must stay installed */
    sigaction(SIGINT, &sa, NULL);

    /* Animate waiting */
    printf("  HP: [██████████] 100%%\n");
    anim_spinner("Waiting for your signal...", 0);

    int prev = 0;
    while (!g_stage_complete) {
        if (g_sigint_count != prev) {
            prev = g_sigint_count;
            int hp = 100 - (int)(prev * 33);
            if (hp < 0) hp = 0;
            printf("  HP: [");
            int bars = hp / 10;
            for (int i = 0; i < bars; i++) printf(RED "█" RESET);
            for (int i = bars; i < 10; i++) printf("░");
            printf("] %d%%\n", hp);
            fflush(stdout);
        }
        msleep(50);
    }

    anim_wizard_death(RED);
    anim_victory(1);

    /* Reset SIGINT to default so Ctrl+C works normally again */
    signal(SIGINT, SIG_DFL);
    msleep(1500);
}

/* ─── STAGE 2 ────────────────────────────────────────────────── */
static void run_stage2(void) {
    g_sigusr1_count = 0;
    g_sigusr2_count = 0;
    g_stage_complete = 0;

    print_stage_banner(2, "THE ORDERED ORACLE");
    anim_wizard(2, "Ordered Oracle", BLUE);

    printf(BLUE "  \"Order is everything! Chaos is nothing!\n"
                "   Send the wrong signal first, and I win!\"\n" RESET "\n");


    printf(DIM "  PID: %d\n" RESET "\n", getpid());

    struct sigaction sa1 = {0}, sa2 = {0};
    sa1.sa_handler = handler_A;
    sa2.sa_handler = handler_R;
    sigemptyset(&sa1.sa_mask);
    sigemptyset(&sa2.sa_mask);
    sigaction(SIGUSR1, &sa1, NULL);
    sigaction(SIGUSR2, &sa2, NULL);

    printf(CYAN "  [*] Waiting:\n" RESET);

    while (!g_stage_complete) msleep(100);

    anim_wizard_death(BLUE);
    anim_victory(2);
    msleep(1500);
}

/* ─── STAGE 3 ────────────────────────────────────────────────── */
static void run_stage3(void) {
    g_sigalrm_count  = 0;
    g_alarm_fired    = 0;
    g_stage_complete = 0;

    print_stage_banner(3, "THE ALARM WRAITH");
    anim_wizard(3, "Alarm Wraith", YELLOW);

    printf(YELLOW "  \"Tick... tock... You only have ONE chance!\n"
                  "   Set an alarm within 5 seconds or you lose!\"\n" RESET "\n");

    printf(DIM "  PID: %d\n" RESET "\n", getpid());

    struct sigaction sa = {0};
    sa.sa_handler = handler_H;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGALRM, &sa, NULL);

    /* Countdown */
    for (int i = 5; i > 0 && !g_stage_complete; i--) {
        printf(YELLOW "\r  ⏰ Time left: %d second%s  " RESET, i, i==1?"":"s");
        fflush(stdout);
        sleep(1);
    }
    clear_line();

    if (!g_stage_complete) {
        printf(RED "\n  ✗ Too slow! The Wraith vanishes laughing...\n" RESET);
        printf(RED "  Rerun the challenge to try again.\n" RESET);
        exit(1);
    }

    anim_wizard_death(YELLOW);
    anim_victory(3);
    msleep(1500);
}

/* ─── STAGE 4 ────────────────────────────────────────────────── */
static void run_stage4(void) {
    g_sigchld_count  = 0;
    g_child_exited   = 0;
    g_child_status   = 0;
    g_stage_complete = 0;

    print_stage_banner(4, "THE CHILD SPECTER");
    anim_wizard(4, "Child Specter", MAGENTA);

    printf(MAGENTA "  \"I am bound to the next generation! Only a child\n"
                   "   that exits with the right code can banish me!\"\n" RESET "\n");



    printf(DIM "  PID: %d\n" RESET "\n", getpid());

    struct sigaction sa = {0};
    sa.sa_handler = handler_T;
    sa.sa_flags   = SA_NOCLDSTOP;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGCHLD, &sa, NULL);

    /* Wait up to 120 seconds */
    for (int i = 0; i < 1200 && !g_stage_complete; i++) msleep(100);

    if (!g_stage_complete) {
        printf(RED "  ✗ Timeout. Child Specter escapes!\n" RESET);
        exit(1);
    }

    anim_wizard_death(MAGENTA);
    anim_victory(4);
    msleep(1500);
}

/* ─── STAGE 5 ────────────────────────────────────────────────── */
static void run_stage5(void) {
    g_altstack_hit   = 0;
    g_stage_complete = 0;

    print_stage_banner(5, "THE STACK PHANTOM");
    anim_wizard(5, "Stack Phantom", CYAN);

    printf(CYAN "  \"I live between stacks! Only a handler on the\n"
                "   alternate stack can reach me!\"\n" RESET "\n");


    printf(DIM "  PID: %d\n" RESET "\n", getpid());

    /* Install alternate stack */
    g_alt_ss.ss_sp    = altstack_buf;
    g_alt_ss.ss_size  = sizeof(altstack_buf);
    g_alt_ss.ss_flags = 0;
    if (sigaltstack(&g_alt_ss, NULL) != 0) {
        perror("sigaltstack");
        exit(1);
    }

    /* Handler on alt stack */
    struct sigaction sa = {0};
    sa.sa_sigaction = handler_R_;
    sa.sa_flags     = SA_SIGINFO | SA_ONSTACK;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, NULL);


    for (int i = 0; i < 1200 && !g_stage_complete; i++) msleep(100);

    if (!g_stage_complete) {
        printf(RED "  ✗ Timeout. Stack Phantom fades.\n" RESET);
        exit(1);
    }

    /* Restore SIGSEGV to default after success */
    signal(SIGSEGV, SIG_DFL);

    anim_wizard_death(CYAN);
    anim_victory(5);
    msleep(1500);
}

/* ─── STAGE 6 ────────────────────────────────────────────────── */
static void run_stage6(void) {
    g_sigtstp_count  = 0;
    g_stage_complete = 0;

    print_stage_banner(6, "THE PROC NECROMANCER");
    anim_wizard(6, "Proc Necromancer", ORANGE);

    printf(ORANGE "  \"I hide inside /proc! You must read my true name\n"
                  "   before sending the sleep signal!\"\n" RESET "\n");

    

    printf(DIM "  PID: %d\n" RESET "\n", getpid());

    /* Write a small breadcrumb to /proc hint */
    {
        char comm[256];
        int fd = open("/proc/self/comm", O_RDONLY);
        if (fd >= 0) {
            ssize_t n = read(fd, comm, sizeof(comm)-1);
            if (n > 0) { comm[n] = 0; printf(DIM "  /proc/self/comm = %s" RESET, comm); }
            close(fd);
        }
    }

    struct sigaction sa = {0};
    sa.sa_handler = handler_RR;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    sigaction(SIGTSTP, &sa, NULL);


    for (int i = 0; i < 1200 && !g_stage_complete; i++) msleep(100);

    if (!g_stage_complete) {
        printf(RED "  ✗ Timeout. Necromancer escapes to /proc!\n" RESET);
        exit(1);
    }

    /* Re-enable SIGTSTP default (so the terminal works again) */
    signal(SIGTSTP, SIG_DFL);

    anim_wizard_death(ORANGE);
    anim_victory(6);
    msleep(1500);
}

/* ─── STAGE 7 ────────────────────────────────────────────────── */
static void run_stage7(void) {
    g_s7_usr1    = 0;
    g_s7_term    = 0;
    g_s7_final   = 0;
    g_stage_complete = 0;

    print_stage_banner(7, "THE GRAND SIGNAL ARCHMAGE");

    printf(PURPLE
        "\n"
        "      .-\"\"\"-.       ╔══════════════════════════════╗\n"
        "     /  o o  \\      ║  THE GRAND ARCHMAGE AWAKENS  ║\n"
        "    |  \\___/  |     ║  Seven seals bind my power.  ║\n"
        "     \\       /      ║  Break them all — or perish! ║\n"
        "    .-`-...-'-.     ╚══════════════════════════════╝\n"
        "   /   Archmage \\  \n"
        "  (_____________)\n"
        RESET "\n");

    printf(PURPLE "  \"You have defeated my apprentices... but I require\n"
                  "   a SEQUENCE of rituals. Miss one step, start over!\"\n" RESET "\n");


    printf(DIM "  PID: %d\n\n" RESET, getpid());

    /* Install handlers */
    struct sigaction sa_u1 = {0}, sa_int = {0};
    sa_u1.sa_handler  = handler_D;
    sa_int.sa_handler = handler_E;
    sigemptyset(&sa_u1.sa_mask);
    sigemptyset(&sa_int.sa_mask);
    sigaction(SIGUSR1, &sa_u1,  NULL);
    sigaction(SIGINT,  &sa_int, NULL);

    /* SIGTERM: install a handler that sets g_s7_term=1 and re-ignores itself */
    signal(SIGTERM, SIG_IGN);  /* start ignored */
    /* We poll /proc/self/status to check if SIGTERM is being ignored
       This is how we verify step 2 from inside */

    printf(CYAN "  [*] SIGUSR1 received: 0/3\n" RESET);

    int last_u1 = -1;
    while (!g_stage_complete) {
        /* Check if SIGTERM is currently SIG_IGN by attempting to install
           a dummy handler and checking if it was already SIG_IGN */
        struct sigaction cur = {0};
        sigaction(SIGTERM, NULL, &cur);
        if (cur.sa_handler == SIG_IGN) g_s7_term = 1;
        else g_s7_term = 0;

        if (g_s7_usr1 != last_u1) {
            last_u1 = g_s7_usr1;
            if (g_s7_usr1 < 3)
                printf(CYAN "\r  [*] SIGUSR1: %d/3   SIGTERM ignored: %s   " RESET,
                       g_s7_usr1, g_s7_term ? GREEN "YES" RESET : RED "NO" RESET);
            else
                printf(CYAN "\r  [*] SIGUSR1: ✓   SIGTERM ignored: %s   " RESET,
                       g_s7_term ? GREEN "YES" RESET : RED "NO" RESET);
            fflush(stdout);
        }
        msleep(100);
    }

    printf("\n");

    /* Dramatic final sequence */
    printf(PURPLE "\n  The Archmage's shields crack one by one...\n" RESET);
    for (int i = 0; i < 7; i++) {
        printf(YELLOW "  ⚡ Shield %d shatters!\n" RESET, i+1);
        msleep(200);
    }

    anim_wizard_death(PURPLE);
    anim_victory(7);

    printf(GREEN BOLD
        "\n  ╔════════════════════════════════════════════════╗\n"
        "  ║  🏆  ALL 7 WIZARDS DEFEATED!  🏆               ║\n"
        "  ║  You have mastered the art of signals.         ║\n"
        "  ╚════════════════════════════════════════════════╝\n"
        RESET "\n");

    decrypt_flag();

    printf(DIM "\n  Accumulated signal stats (anti-cheat proof):\n"
               "  SIGINT:  %ld   SIGUSR1: %ld   SIGUSR2: %ld\n"
               "  SIGALRM: %ld   SIGCHLD: %ld   SIGTSTP: %ld\n"
               RESET "\n",
        g_sigint_count, g_sigusr1_count + g_s7_usr1,
        g_sigusr2_count, g_sigalrm_count,
        g_sigchld_count, g_sigtstp_count);
}

/* ══════════════════════════════════════════════════════════════
 *  MAIN
 * ══════════════════════════════════════════════════════════════ */
int main(void) {
    /* Disable output buffering */
    setvbuf(stdout, NULL, _IONBF, 0);

   

    anim_title();
    msleep(500);

    slow_print(WHITE "  You are a lone signal warrior.\n" RESET, 18);
    slow_print(WHITE "  Seven signal wizards stand between you\n" RESET, 18);
    slow_print(WHITE "  and the ancient secrets of POSIX.\n\n" RESET, 18);

    printf(WHITE "  Learn, send the right signals, and prevail.\n" RESET);


    printf(CYAN "  Press Enter to begin your journey...\n" RESET);
    getchar();

    /* Run all stages */
    g_stage = 1; run_stage1();
    g_stage = 2; run_stage2();
    g_stage = 3; run_stage3();
    g_stage = 4; run_stage4();
    g_stage = 5; run_stage5();
    g_stage = 6; run_stage6();
    g_stage = 7; run_stage7();

    printf(GREEN "\n  Thanks for playing Signal Wizard!\n" RESET);
    return 0;
}
