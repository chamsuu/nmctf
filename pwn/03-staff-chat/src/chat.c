#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAX_LIVE_MSGS 10
#define MAX_MSG_SLOTS 16

typedef struct {
    int     id;
    size_t  data_size;
    char   *data;
    int     archived;
} msg_t;

static msg_t g_messages[MAX_MSG_SLOTS];
static int   g_alloc_count = 0;
static int   g_msg_id_seq  = 0;

static int read_line(char *buf, size_t size) {
    if (!fgets(buf, size, stdin)) return -1;
    size_t len = strlen(buf);
    if (len > 0 && buf[len-1] == '\n') {
        buf[len-1] = '\0';
        return len - 1;
    }
    return len;
}

static int read_int(void) {
    char cbuf[32] = {0};
    read_line(cbuf, sizeof(cbuf));
    return atoi(cbuf);
}

static size_t read_size(void) {
    char cbuf[32] = {0};
    read_line(cbuf, sizeof(cbuf));
    return (size_t)strtoull(cbuf, NULL, 10);
}

static uint64_t compute_key(const msg_t *m) {
    size_t chunk_sz = ((m->data_size + 0x10 + 0x0f) & ~(size_t)0x0f) | 1;
    return (uint64_t)chunk_sz ^ 0x4141414141414141ULL;
}

static char *alloc_msg_data(size_t size) {
    if (g_alloc_count >= 10) {
        puts("[-] Memory limit reached. Archive old messages first.");
        return NULL;
    }
    g_alloc_count++;
    return malloc(size);
}

int cmd_new_message(void) {
    int slot = -1;
    for (int i = 0; i < MAX_MSG_SLOTS; i++) {
        if (!g_messages[i].data && !g_messages[i].archived) {
            slot = i;
            break;
        }
    }
    if (slot < 0) {
        puts("[-] No slots.");
        return -1;
    }

    printf("Message size: ");
    fflush(stdout);

    size_t size = read_size();

    if (size == 0 || size > 0x500) {
        puts("[-] Invalid size.");
        return -1;
    }

    char *buf = alloc_msg_data(size);
    if (!buf) return -1;

    printf("Content: ");
    fflush(stdout);
    fread(buf, 1, size, stdin);

    g_messages[slot].id        = g_msg_id_seq++;
    g_messages[slot].data_size = size;
    g_messages[slot].data      = buf;
    g_messages[slot].archived  = 0;

    printf("[+] Message %d created.\n", g_messages[slot].id);

    return slot;
}

void cmd_view_message(int idx) {
    if (idx < 0 || idx >= MAX_MSG_SLOTS) return;
    msg_t *m = &g_messages[idx];

    if (!m->data && !m->archived) {
        puts("[-] Empty slot.");
        return;
    }
    
    printf("[MSG %02d] ", m->id);
    fflush(stdout);
    fwrite(m->data, 1, m->data_size, stdout);
    fflush(stdout);
    puts("");
}

void cmd_archive_message(int idx) {
    if (idx < 0 || idx >= MAX_MSG_SLOTS) return;
    msg_t *m = &g_messages[idx];
    if (!m->data || m->archived) return;

    free(m->data);
    *(uint64_t *)(m->data) ^= compute_key(m);
    m->archived = 1;
    g_alloc_count--;
    puts("[+] Message archived.");
}

void cmd_edit_message(int idx) {
    if (idx < 0 || idx >= MAX_MSG_SLOTS) return;
    msg_t *m = &g_messages[idx];

    if (!m->data && !m->archived) {
        puts("[-] Empty slot.");
        return;
    }
    
    printf("New content (%zu bytes): ", m->data_size);
    fflush(stdout);
    fread(m->data, 1, m->data_size, stdin);
    puts("[+] Updated.");
}

void cmd_list_messages(void) {
    printf("[*] Messages (%d/%d live):\n", g_alloc_count, MAX_LIVE_MSGS);
    for (int i = 0; i < MAX_MSG_SLOTS; i++) {
        if (g_messages[i].data || g_messages[i].archived) {
            printf("  [%d] ID=%d size=%zu %s\n", i, g_messages[i].id,
                   g_messages[i].data_size, g_messages[i].archived ? "(archived)" : "");
        }
    }
}

int get_slot_index(void) {
    printf("Message index: ");
    fflush(stdout);
    return read_int();
}

void run_chat(void) {
    const char *banner =
        "=== PixelVault Staff Chat ===\n"
        "[1] New message\n"
        "[2] View message\n"
        "[3] Archive message\n"
        "[4] Edit message\n"
        "[5] List messages\n"
        "[6] Exit\n";

    printf("%s", banner);
    fflush(stdout);

    while (1) {
        printf("Choice: ");
        fflush(stdout);

        int choice = read_int();
        if (choice <= 0) break;

        switch (choice) {
            case 1: cmd_new_message(); break;
            case 2: cmd_view_message(get_slot_index()); break;
            case 3: cmd_archive_message(get_slot_index()); break;
            case 4: cmd_edit_message(get_slot_index()); break;
            case 5: cmd_list_messages(); break;
            case 6: return;
            default:
                puts("Invalid choice");
        }
    }
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    run_chat();
    return 0;
}