#!/usr/bin/env python3
import argparse
import socket
import statistics
import time


def rank_value(rank):
    if rank == "A":
        return 11
    if rank in ("J", "Q", "K"):
        return 10
    return int(rank)


def parse_card(text):
    return text[:-1], text[-1]


def hand_value(cards):
    total = sum(rank_value(rank) for rank, _ in cards)
    aces = sum(1 for rank, _ in cards if rank == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


class Remote:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)
        self.buf = b""
        self.read_until_prompt()

    def close(self):
        self.sock.close()

    def read_until_prompt(self):
        prompt = b"\n> "
        while prompt not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            self.buf += chunk
        if prompt in self.buf:
            data, self.buf = self.buf.split(prompt, 1)
        else:
            data = self.buf
            self.buf = b""
        lines = [line.strip() for line in data.decode(errors="replace").splitlines()]
        if lines and lines[-1] == "END":
            lines.pop()
        return [line for line in lines if line]

    def cmd(self, command):
        start = time.perf_counter()
        self.sock.sendall((command + "\n").encode())
        lines = self.read_until_prompt()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return lines, elapsed_ms


def parse_data(lines):
    data_line = next((line for line in reversed(lines) if line.startswith("DATA ")), None)
    if data_line is None:
        raise RuntimeError("server response did not include a DATA line")

    data = {}
    for item in data_line.split()[1:]:
        key, value = item.split("=", 1)
        data[key] = value

    player_cards = [parse_card(card) for card in data["player"].split(",") if card]
    dealer_cards = [card for card in data["dealer"].split(",") if card]

    return {
        "balance": int(data["balance"]),
        "target": int(data["target"]),
        "round": int(data["round"]),
        "max_rounds": int(data["max_rounds"]),
        "phase": data["phase"],
        "player": player_cards,
        "player_total": int(data["player_value"]),
        "dealer_up": parse_card(data["dealer_up"]),
        "dealer": dealer_cards,
        "cashout": data["cashout"] == "1",
    }


def observe_value(remote, samples):
    timings = []
    for _ in range(samples):
        lines, elapsed = remote.cmd("OBSERVE")
        if lines[0].startswith("ERR"):
            raise RuntimeError(lines[0])
        timings.append(elapsed)
    median_ms = statistics.median(timings)

    # The service sleeps for about 35ms per hidden blackjack value.
    value = round(median_ms / 35.0)
    return max(2, min(11, value)), median_ms


def choose_bet(balance, player_total, dealer_up_value, hidden_value):
    dealer_total = dealer_up_value + hidden_value
    if dealer_total > 21 and hidden_value == 11:
        dealer_total -= 10
    if dealer_total > 21 and dealer_up_value == 11:
        dealer_total -= 10

    player_blackjack = player_total == 21
    dealer_blackjack = dealer_total == 21

    if player_blackjack and not dealer_blackjack:
        return balance
    if dealer_total >= 17 and player_total > dealer_total:
        return balance
    if player_total >= 20 and dealer_total < 20:
        return max(1, balance // 2)
    if player_total >= 18 and dealer_total <= 16:
        return max(1, balance // 3)
    return 1


def choose_action(player_cards, dealer_up_value, hidden_value):
    player_total = hand_value(player_cards)
    dealer_total = dealer_up_value + hidden_value
    if dealer_total > 21 and hidden_value == 11:
        dealer_total -= 10
    if dealer_total > 21 and dealer_up_value == 11:
        dealer_total -= 10

    if player_total >= 17:
        return "STAND"
    if dealer_total >= 17 and player_total <= dealer_total:
        return "HIT"
    if player_total <= 11:
        return "HIT"
    if player_total <= 16 and dealer_total >= 7:
        return "HIT"
    return "STAND"


def reveal(remote):
    lines, _ = remote.cmd("REVEAL")
    return lines


def result_line(lines):
    return next((line for line in lines if line.startswith("RESULT ")), None)


def flag_line(lines):
    return next((line for line in lines if line.startswith("FLAG ")), None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1337)
    parser.add_argument("--samples", type=int, default=2)
    args = parser.parse_args()

    remote = Remote(args.host, args.port)
    remote.cmd("MACHINE")

    for _ in range(120):
        hand_lines, _ = remote.cmd("HAND")
        hand = parse_data(hand_lines)

        hidden_value, timing = observe_value(remote, args.samples)
        dealer_up_value = rank_value(hand["dealer_up"][0])
        bet = choose_bet(hand["balance"], hand["player_total"], dealer_up_value, hidden_value)

        print(
            f"round={hand['round']:03d} balance={hand['balance']:3d} player={hand['player_total']:2d} "
            f"dealer_up={dealer_up_value:2d} hidden~={hidden_value:2d} "
            f"t={timing:6.1f}ms bet={bet}"
        )

        lines, _ = remote.cmd(f"BET {bet}")

        while lines and result_line(lines) is None:
            hand_lines, _ = remote.cmd("HAND")
            hand = parse_data(hand_lines)
            action = choose_action(hand["player"], dealer_up_value, hidden_value)
            lines, _ = remote.cmd(action)

        result = result_line(lines)
        print("  " + result)
        flag = flag_line(lines)
        if flag:
            print(flag)
            remote.close()
            return

        hand = parse_data(lines)
        if hand["balance"] >= hand["target"]:
            flag_lines, _ = remote.cmd("CASHOUT")
            flag = flag_line(flag_lines)
            if flag is None:
                raise RuntimeError("cashout response did not include a flag")
            print(flag)
            remote.close()
            return
        if hand["balance"] <= 0:
            raise RuntimeError("bankrupt")

        reveal_lines = reveal(remote)
        reveal_summary = [
            line for line in reveal_lines
            if line.startswith("Dealer hole card:") or line.startswith("Hidden value:")
        ]
        print("  " + " ".join(reveal_summary))
        remote.cmd("NEW")

    raise RuntimeError("round limit reached")


if __name__ == "__main__":
    main()
