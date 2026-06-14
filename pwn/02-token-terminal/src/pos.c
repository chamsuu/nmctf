#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
/* ------------------------------------------------------------------ */
/*  BSS target - refund metadata for stable implementation */
struct __attribute__((aligned(8))) {
    uint32_t  reuse_tag;             /* +0x00  */
    uint32_t  reuse_size;            /* +0x04  */
    char      template[4];           /* +0x08  refund writes HERE       */
    void    (*dispatch)(char *);     /* +0x0C  overwrite target (+4)    */
    uint32_t  receipt_id;            /* +0x10                           */
} g_state;

/* ------------------------------------------------------------------ */
/*  Win function — player finds via nm/Ghidra, not obviously named      */
/* ------------------------------------------------------------------ */
void __attribute__((used)) sys_maintenance(char *ignored) {
    (void)ignored;
    system("cat /flag.txt");
    fflush(stdout);
}

static void default_dispatch(char *t) {
    dprintf(1, "[POS] Receipt: %.8s\n", t);
}

/* ------------------------------------------------------------------ */
/*  Item record — sizeof = 28 bytes, chunk_size = 0x28                  */
/*                                                                      */
/*  Heap layout after setup() allocates placeholder then record:        */
/*    [placeholder chunk 0x20][record chunk 0x28][...]                  */
/*                                                                      */
/*  process_order gets placeholder chunk back (via tcache LIFO).        */
/*  Overflow from placeholder user data:                                */
/*    +0x00  [24 bytes]  fill placeholder user data                    */
/*    +0x18  [ 8 bytes]  record chunk header (prev_size + size)        */
/*    +0x20  [ 4 bytes]  record.item_id                                */
/*    +0x24  [ 4 bytes]  record.price                                  */
/*    +0x28  [ 4 bytes]  record.name  ← write &g_state.template HERE  */
/*  Note: offset +0x28 is from placeholder USER DATA, not chunk start  */
/* ------------------------------------------------------------------ */
typedef struct {
    uint32_t  item_id;               /* +0x00 */
    uint32_t  price;                 /* +0x04 */
    char     *name;                  /* +0x08  ← corruption target     */
    char      desc[16];              /* +0x0C */
} record_t;                          /* sizeof = 28, chunk_size = 0x28 */

static record_t *g_record    = NULL;
static void * volatile g_pholder = NULL; /* released to tcache for process_order */
static void     *g_corrupted = NULL;

/* ------------------------------------------------------------------ */
/*  Power-of-2 allocator — all player-visible allocations use this     */
/* ------------------------------------------------------------------ */
static void *safe_alloc(size_t n) {
    if (!n || (n & (n - 1))) { write(1,"[-] Power of 2 only.\n",21); return NULL; }
    if (n < 8 || n > 2048)   { write(1,"[-] Out of range.\n",18);    return NULL; }
    if (n == 16 && g_corrupted) {
        void *p = g_corrupted;
        g_corrupted = NULL;
        return p;
    }
    return malloc(n);
}

/* ------------------------------------------------------------------ */
/*  Menu 1: set refund metadata                                         */
/*  Player writes a tag and size used by the refund reuse bug.          */
/*  Correct values: tag=0, size=0x21.                                  */
/* ------------------------------------------------------------------ */
void cmd_set_metadata(int sockfd) {
    uint32_t prev, csz;
    send(sockfd, "reuse_tag      (4 bytes): ", 26, 0);
    recv(sockfd, &prev, 4, 0);
    send(sockfd, "reuse_size     (4 bytes): ", 26, 0);
    recv(sockfd, &csz,  4, 0);
    g_state.reuse_tag  = prev;
    g_state.reuse_size = csz;
    send(sockfd, "[POS] Metadata set.\n", 20, 0);
}

/* ------------------------------------------------------------------ */
/*  Menu 2: process order — THE VULNERABLE FUNCTION                     */
/*                                                                      */
/*  Integer overflow:                                                   */
/*    alloc_size = (uint16_t)(quantity × 40) → truncates               */
/*    recv reads  quantity × 40 bytes         → full (overflow)        */
/*                                                                      */
/*  Useful quantity: 0x199A                                             */
/*    0x199A × 40 = 0x40010 → lower 16 bits = 0x0010 = 16             */
/*    malloc(16) → gets g_pholder back from tcache (0x20 chunk)        */
/*    recv reads 0x199A × 40 = 262160 bytes but player sends only 44   */
/*                                                                      */
/*  Overflow payload (44 bytes total):                                  */
/*    [0x00-0x17]  24 bytes: fill placeholder user data                */
/*    [0x18-0x1F]   8 bytes: record chunk header — write 0x00000000    */
/*                           prev_size and 0x00000029 (size, keep valid)*/
/*    [0x20-0x23]   4 bytes: record.item_id junk                      */
/*    [0x24-0x27]   4 bytes: record.price junk                        */
/*    [0x28-0x2B]   4 bytes: record.name ← &g_state.template           */
/* ------------------------------------------------------------------ */
void cmd_process_order(int sockfd) {
    uint16_t quantity = 0;
    send(sockfd, "Quantity (2 bytes LE): ", 23, 0);
    recv(sockfd, &quantity, 2, 0);

    uint16_t alloc_size = (uint16_t)((uint32_t)quantity * 40u);
    if (!alloc_size) { send(sockfd,"[-] Bad qty.\n",13,0); return; }

    void *orders = malloc((size_t)alloc_size);
    if (!orders)    { send(sockfd,"[-] OOM.\n",9,0); return; }

    send(sockfd, "Item data: ", 11, 0);

    /* BUG: Integer overflow vulnerability, but cap recv for stability */
    ssize_t to_read = (size_t)quantity * 40u;
    ssize_t got = 0;
    while (got < to_read) {
        ssize_t r = recv(sockfd, (char*)orders + got,
                         to_read - got < 4096 ? to_read - got : 4096, 0);
        if (r <= 0) break;
        got += r;
        if (got >= 44) break;   /* Got enough for the overwrite, stop waiting */
    }

    send(sockfd, "[POS] Order logged.\n", 20, 0);
    free(orders);
}

/* ------------------------------------------------------------------ */
/*  Menu 3: delete record                                               */
/*  If record->name was corrupted to &g_state.template and metadata is  */
/*  valid, queue that pointer for the next refund allocation. Otherwise */
/*  delete the real heap name normally.                                 */
/* ------------------------------------------------------------------ */
void cmd_delete_record(int sockfd) {
    if (!g_record) { send(sockfd,"[-] No record.\n",15,0); return; }
    if (g_record->name) {
        /* Check if pointer is in BSS region (0x08040000-0x08050000) */
        uint32_t addr = (uint32_t)g_record->name;
        if (addr >= 0x08040000 && addr < 0x08050000) {
            /* Likely corrupted to BSS, queue it */
            g_corrupted = g_record->name;
        } else {
            free(g_record->name);
        }
        g_record->name = NULL;
    }
    send(sockfd, "[POS] Record deleted.\n", 22, 0);
}

/* ------------------------------------------------------------------ */
/*  Menu 4: claim refund — safe_alloc, player writes to returned ptr   */
/*  After the corrupted delete, safe_alloc(16) returns &g_state.template*/
/* ------------------------------------------------------------------ */
void cmd_claim_refund(int sockfd) {
    uint32_t sz;
    send(sockfd, "Refund size (4 bytes): ", 23, 0);
    recv(sockfd, &sz, 4, 0);

    void *p = safe_alloc((size_t)sz);
    if (!p) return;

    char info[48];
    int  n = snprintf(info, sizeof(info), "[POS] Chunk @ %p. Data: ", p);
    send(sockfd, info, n, 0);
    recv(sockfd, p, (size_t)sz, 0);
    send(sockfd, "\n[POS] Done.\n", 13, 0);
}

/* ------------------------------------------------------------------ */
/*  Menu 5: print receipt — triggers dispatch function pointer          */
/* ------------------------------------------------------------------ */
void cmd_print_receipt(int sockfd) {
    dup2(sockfd, STDOUT_FILENO);
    dup2(sockfd, STDERR_FILENO);
    setvbuf(stdout, NULL, _IONBF, 0);
    g_state.dispatch(g_state.template);
}

/* ------------------------------------------------------------------ */
/*  Connection init — sets up heap layout                               */
/*                                                                      */
/*  Heap after init:                                                    */
/*    [placeholder 0x20][record 0x28][record.name 0x20][...]           */
/*    free(placeholder) → tcache[0x20 bin]: [placeholder]              */
/*                                                                      */
/*  process_order malloc(16) → gets placeholder back (LIFO)             */
/*  Overflow from placeholder → record sits immediately after it        */
/* ------------------------------------------------------------------ */
void handle_connection(int sockfd) {
    /* Init g_state */
    memset(&g_state, 0, sizeof(g_state));
    memcpy(g_state.template, "PIXL", 4);
    g_state.dispatch   = default_dispatch;
    g_state.receipt_id = 0x1001;

    /* Heap grooming — MUST happen in this order */
    g_pholder = malloc(16);                /* placeholder: 0x20 chunk */
    g_record  = malloc(sizeof(record_t));  /* record:      0x28 chunk, adjacent */

    g_record->item_id = 1;
    g_record->price   = 500;
    g_record->name    = malloc(24);        /* name buf: separate alloc */
    strncpy(g_record->name, "ARCADE TOKEN", 13);
    strncpy(g_record->desc,  "Standard",    9);

    free(g_pholder);  /* releases to tcache[1]: process_order reclaims it */
    g_pholder = NULL;

    const char *banner =
        "=== PixelVault Token Terminal ===\n"
        "[1] Set receipt metadata\n"
        "[2] Process order\n"
        "[3] Delete record\n"
        "[4] Claim refund\n"
        "[5] Print receipt\n"
        "[6] Exit\n> ";

    send(sockfd, banner, strlen(banner), 0);

    while (1) {
        char c[4] = {0};
        if (recv(sockfd, c, 1, 0) <= 0) break;
        switch (c[0]) {
            case '1': cmd_set_metadata(sockfd);   break;
            case '2': cmd_process_order(sockfd);  break;
            case '3': cmd_delete_record(sockfd);  break;
            case '4': cmd_claim_refund(sockfd);   break;
            case '5': cmd_print_receipt(sockfd);  return;
            case '6': return;
            default:  send(sockfd, "[-] Unknown.\n", 13, 0);
        }
        send(sockfd, "> ", 2, 0);
    }
}

int main(void) {
    int sfd, cfd;
    struct sockaddr_in a = {0};
    sfd = socket(AF_INET, SOCK_STREAM, 0);
    setsockopt(sfd, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int));
    a.sin_family = AF_INET; a.sin_addr.s_addr = INADDR_ANY;
    a.sin_port = htons(1337);
    bind(sfd, (struct sockaddr *)&a, sizeof(a));
    listen(sfd, 5);
    while (1) {
        cfd = accept(sfd, NULL, NULL);
        if (fork() == 0) { close(sfd); handle_connection(cfd); close(cfd); exit(0); }
        close(cfd);
    }
}
