#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>

void unlock_door(unsigned int door_code) {
    if (door_code == 0xC0DEC0DE) {
        puts("[GATE] Access granted.");
        fflush(stdout);                    // ensure it flushes before system()
        system("cat /flag.txt");
    } else {
        puts("[GATE] Invalid code. Security alert triggered.");
    }
}

void process_header(const char *data) {
    printf("[FW] Version: %.8s\n", data);
}

static void __attribute__((noinline)) recv_firmware_payload(int sockfd) {
    char incoming[128];
    recv(sockfd, incoming, 256, 0);
}

void handle_firmware_update(int sockfd) {
    send(sockfd, "[FW] Send payload:\n", 19, 0);

    dup2(sockfd, STDOUT_FILENO);           // redirect stdout to socket
    dup2(sockfd, STDERR_FILENO);           // redirect stderr to socket

    recv_firmware_payload(sockfd);
    process_header("ok");
    send(sockfd, "[FW] Done.\n", 11, 0);
}

int authenticate(int sockfd) {
    char pin[8];
    send(sockfd, "PIN: ", 5, 0);
    recv(sockfd, pin, sizeof(pin), 0);
    return (pin[0] == '\x00');
}

void handle_connection(int sockfd) {
    const char *banner =
        "=== PixelVault Entry System v1.2 ===\n"
        "[1] Authenticate\n"
        "[2] Upload firmware update\n"
        "Choice: ";

    send(sockfd, banner, strlen(banner), 0);

    char choice[4];
    recv(sockfd, choice, sizeof(choice), 0);

    if (choice[0] == '1') {
        authenticate(sockfd);
        send(sockfd, "[AUTH] Access denied.\n", 22, 0);
    } else {
        handle_firmware_update(sockfd);
    }
}

int main(void) {
    int server_fd, client_fd;
    struct sockaddr_in addr = {0};

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int));

    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port        = htons(1337);

    bind(server_fd, (struct sockaddr *)&addr, sizeof(addr));
    listen(server_fd, 5);

    while (1) {
        client_fd = accept(server_fd, NULL, NULL);
        if (fork() == 0) {
            close(server_fd);
            handle_connection(client_fd);
            close(client_fd);
            exit(0);
        }
        close(client_fd);
    }
}