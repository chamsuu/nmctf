#!/usr/bin/env python3
import argparse
import random
import socket
import socketserver
import time

HOST = "0.0.0.0"
PORT = 777

FLAG = "nmctf{bl4ckj4ck_t1m1n6_b4nkr0ll_w1ll_m4k3_y0u_r1ch}"

STARTING_BALANCE = 100
TARGET_BALANCE = 500
MAX_ROUNDS = 120
MAX_OBSERVE_CALLS = 5

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["S", "H", "D", "C"]

VALUE_DELAY_SECONDS = 0.035
JITTER_MAX = 0.004


def card_text(card):
    return f"{card[0]}{card[1]}"


def cards_text(cards):
    return " ".join(card_text(card) for card in cards)


def draw_card():
    return random.choice(RANKS), random.choice(SUITS)


def hard_value(card):
    rank, _ = card
    if rank == "A":
        return 11
    if rank in ("J", "Q", "K"):
        return 10
    return int(rank)


def hand_value(cards):
    total = sum(hard_value(card) for card in cards)
    aces = sum(1 for rank, _ in cards if rank == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_blackjack(cards):
    return len(cards) == 2 and hand_value(cards) == 21


def observe_delay(hidden_card):
    value = hard_value(hidden_card)
    time.sleep(value * VALUE_DELAY_SECONDS)
    time.sleep(random.uniform(0, JITTER_MAX))


class Game:
    def __init__(self):
        self.balance = STARTING_BALANCE
        self.round_no = 0
        self.phase = "ready"
        self.bet = 0
        self.player = []
        self.dealer = []
        self.observe_calls = 0
        self.last_reveal = None
        self.deal_round()

    def deal_round(self):
        if self.balance <= 0:
            self.phase = "bankrupt"
            return self.message("ERR bankroll is empty")
        if self.round_no >= MAX_ROUNDS:
            self.phase = "finished"
            return self.message("ERR table closed: round limit reached")

        self.round_no += 1
        self.phase = "betting"
        self.bet = 0
        self.player = [draw_card(), draw_card()]
        self.dealer = [draw_card(), draw_card()]
        self.observe_calls = 0
        self.last_reveal = None
        return self.status("New hand", "Use OBSERVE to study the table, then BET amount.")

    def new_round(self):
        if self.phase != "over":
            raise ValueError("new hand is only available after the current hand ends")
        return self.deal_round()

    def visible_dealer_cards(self):
        if self.phase in ("over", "bankrupt", "finished"):
            return cards_text(self.dealer)
        return f"{card_text(self.dealer[0])} ??"

    def visible_dealer_value(self):
        if self.phase in ("over", "bankrupt", "finished"):
            return str(hand_value(self.dealer))
        return f"{hand_value([self.dealer[0]])}+?"

    def next_hint(self):
        if self.balance >= TARGET_BALANCE:
            return "Use CASHOUT to claim the flag."
        if self.phase == "betting":
            return "Use OBSERVE, then BET amount."
        if self.phase == "playing":
            return "Choose HIT, STAND, or DOUBLE."
        if self.phase == "over":
            return "Use REVEAL to review the hand, then NEW."
        if self.phase == "bankrupt":
            return "Bankrupt."
        if self.phase == "finished":
            return "Table closed."
        return "Use HELP for commands."

    def data_line(self):
        dealer_cards = self.visible_dealer_cards().replace(" ", ",")
        player_cards = cards_text(self.player).replace(" ", ",")
        return (
            "DATA "
            f"balance={self.balance} "
            f"target={TARGET_BALANCE} "
            f"round={self.round_no} "
            f"max_rounds={MAX_ROUNDS} "
            f"phase={self.phase} "
            f"bet={self.bet} "
            f"observe_calls={self.observe_calls} "
            f"observe_left={max(0, MAX_OBSERVE_CALLS - self.observe_calls)} "
            f"player={player_cards} "
            f"player_value={hand_value(self.player)} "
            f"dealer={dealer_cards} "
            f"dealer_up={card_text(self.dealer[0])} "
            f"cashout={int(self.balance >= TARGET_BALANCE)}"
        )

    def status(self, title=None, note=None):
        lines = []
        if title:
            lines.extend([f"== {title} ==", ""])

        lines.extend([
            f"Bankroll: ${self.balance} / ${TARGET_BALANCE}    Round: {self.round_no}/{MAX_ROUNDS}    Phase: {self.phase.upper()}",
            f"Player:   {cards_text(self.player):<14} value {hand_value(self.player)}",
            f"Dealer:   {self.visible_dealer_cards():<14} value {self.visible_dealer_value()}",
            f"Bet:      ${self.bet:<5}          Observe: {self.observe_calls}/{MAX_OBSERVE_CALLS}",
        ])

        if note:
            lines.append(f"Note:     {note}")
        lines.append(f"Next:     {self.next_hint()}")
        lines.append("")
        lines.append(self.data_line())
        return lines

    def message(self, text):
        return [text, "", self.data_line()]

    def hand_lines(self):
        return self.status("Table")

    def observe(self):
        if self.phase not in ("betting", "playing"):
            raise ValueError("observe is only available during an active hand")
        if self.observe_calls >= MAX_OBSERVE_CALLS:
            raise ValueError("observe limit reached for this hand")
        self.observe_calls += 1
        observe_delay(self.dealer[1])

    def reveal(self):
        if self.phase != "over":
            raise ValueError("reveal is available after a hand ends")
        hole = self.dealer[1]
        return [
            "== Reveal ==",
            "",
            f"Dealer hole card: {card_text(hole)}",
            f"Hidden value:     {hard_value(hole)}",
            f"Observations:     {self.observe_calls}",
            "",
        ] + self.status(note="Use NEW for the next hand.")

    def place_bet(self, amount):
        if self.phase != "betting":
            raise ValueError("bet is only allowed before playing this hand")
        if amount < 1:
            raise ValueError("minimum bet is 1")
        if amount > self.balance:
            raise ValueError("bet exceeds balance")

        self.bet = amount
        self.phase = "playing"

        player_bj = is_blackjack(self.player)
        dealer_bj = is_blackjack(self.dealer)
        if player_bj or dealer_bj:
            return self.finish_hand(player_bj=player_bj, dealer_bj=dealer_bj)

        return self.status("Bet accepted", "Choose HIT, STAND, or DOUBLE.")

    def hit(self):
        if self.phase != "playing":
            raise ValueError("hit is only allowed after betting")
        self.player.append(draw_card())
        if hand_value(self.player) > 21:
            return self.finish_hand(force="loss", reason="player_bust")
        return self.status("Hit", f"Drew {card_text(self.player[-1])}.")

    def double(self):
        if self.phase != "playing":
            raise ValueError("double is only allowed after betting")
        if self.bet * 2 > self.balance:
            raise ValueError("not enough balance to double")
        self.bet *= 2
        self.player.append(draw_card())
        if hand_value(self.player) > 21:
            return self.finish_hand(force="loss", reason="player_bust_after_double")
        return self.stand(reason="double")

    def stand(self, reason="stand"):
        if self.phase != "playing":
            raise ValueError("stand is only allowed after betting")
        while hand_value(self.dealer) < 17:
            self.dealer.append(draw_card())
        return self.finish_hand(reason=reason)

    def finish_hand(self, force=None, reason="settled", player_bj=False, dealer_bj=False):
        player_total = hand_value(self.player)
        dealer_total = hand_value(self.dealer)

        if force == "loss":
            result = "loss"
        elif player_bj and dealer_bj:
            result = "push"
            reason = "both_blackjack"
        elif player_bj:
            result = "win"
            reason = "blackjack"
        elif dealer_bj:
            result = "loss"
            reason = "dealer_blackjack"
        elif dealer_total > 21:
            result = "win"
            reason = "dealer_bust"
        elif player_total > dealer_total:
            result = "win"
        elif player_total < dealer_total:
            result = "loss"
        else:
            result = "push"

        if result == "win":
            self.balance += self.bet
        elif result == "loss":
            self.balance -= self.bet

        self.last_reveal = self.dealer[1]
        self.phase = "over"

        lines = [
            "== Result ==",
            "",
            f"RESULT {result} reason={reason}",
            f"Player: {cards_text(self.player)} value {player_total}",
            f"Dealer: {cards_text(self.dealer)} value {dealer_total}",
            f"Balance: ${self.balance}",
            "",
        ]
        if self.balance >= TARGET_BALANCE:
            lines.append("GG, you became a pro gambler. Go claim your reward with CASHOUT.")
        elif self.balance >= 400:
            lines.append("You are too close to the big win now. One clean hand can change everything.")
        elif result == "win":
            lines.append("If I were you, I would run with this money. Do not get greedy.")
        if self.balance <= 0:
            self.phase = "bankrupt"
            lines.append("Bankrupt.")
        return lines + self.status(note="Use REVEAL to review the hand, then NEW.")

    def cashout(self):
        if self.balance < TARGET_BALANCE:
            raise ValueError(f"need balance >= {TARGET_BALANCE}")
        self.phase = "finished"
        return [
            "GG, you became a pro gambler. Here is your reward.",
            f"FLAG {FLAG}",
        ]


class Handler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.game = Game()
        self.machine = False

    def send_block(self, lines):
        for line in lines:
            if line.startswith("DATA ") and not self.machine:
                continue
            self.wfile.write((line + "\n").encode())
        self.wfile.write(b"END\n")
        self.wfile.flush()

    def help_lines(self):
        return [
            "== Help ==",
            "",
            "Goal: grow your bankroll to the target and CASHOUT.",
            "The dealer hole card is hidden until the hand is over.",
            "REVEAL is free after a hand if you want to review the deal.",
            "",
            *self.menu_lines(),
        ] + self.game.status()

    def menu_lines(self):
        return [
            "== Command Menu ==",
            "",
            "Information:",
            "  HAND, TABLE           show the current hand and bankroll",
            "  HELP, ?               show this command menu",
            "",
            "Table actions:",
            "  OBSERVE, O            study the dealer before betting",
            "  REVEAL, R             reveal the hidden card after the hand ends",
            "",
            "Betting and play:",
            "  BET amount, B n       place a bet before playing",
            "  HIT, H                draw one card",
            "  STAND, S              keep your hand and let dealer play",
            "  DOUBLE, D             double your bet, draw once, then stand",
            "",
            "Round control:",
            "  NEW, NEXT, N          deal the next hand after a result",
            "  CASHOUT, C            claim the flag when bankroll reaches target",
            "  QUIT, Q               disconnect",
            "",
        ]

    def handle(self):
        self.send_block([
            "== Blackjack Table ==",
            "",
            f"Grow ${STARTING_BALANCE} into ${TARGET_BALANCE} and CASHOUT.",
            "Each hand is dealt before betting. OBSERVE is free but limited.",
            "REVEAL is free after a hand if you want to review the deal.",
            "",
        ] + self.menu_lines() + self.game.hand_lines())

        while True:
            self.wfile.write(b"> ")
            self.wfile.flush()
            raw = self.rfile.readline()
            if not raw:
                return

            line = raw.decode(errors="replace").strip()
            if not line:
                continue

            parts = line.split()
            command = parts[0].upper()

            try:
                if command in ("HELP", "?"):
                    self.send_block(self.help_lines())

                elif command == "MACHINE":
                    self.machine = True
                    self.send_block(["OK machine=1"] + self.game.status())

                elif command in ("HAND", "TABLE"):
                    self.send_block(self.game.hand_lines())

                elif command in ("OBSERVE", "O"):
                    self.game.observe()
                    self.send_block(self.game.status("Observation complete", "Use the table information before betting."))

                elif command in ("BET", "B"):
                    if len(parts) != 2:
                        self.send_block(["ERR usage: BET amount", ""] + self.game.status())
                        continue
                    self.send_block(self.game.place_bet(int(parts[1])))

                elif command in ("HIT", "H"):
                    self.send_block(self.game.hit())

                elif command in ("STAND", "S"):
                    self.send_block(self.game.stand())

                elif command in ("DOUBLE", "D"):
                    self.send_block(self.game.double())

                elif command in ("REVEAL", "R"):
                    self.send_block(self.game.reveal())

                elif command in ("NEW", "NEXT", "N"):
                    self.send_block(self.game.new_round() + self.game.hand_lines())

                elif command in ("CASHOUT", "C"):
                    self.send_block(self.game.cashout())
                    return

                elif command in ("QUIT", "Q"):
                    self.send_block(["bye"])
                    return

                else:
                    self.send_block([f"ERR unknown: {command}", "Type HELP for commands.", ""] + self.game.status())
            except ValueError as exc:
                self.send_block([f"ERR {exc}", ""] + self.game.status())
            except Exception:
                self.send_block(["ERR internal error", ""] + self.game.status())


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    with ThreadedTCPServer((args.host, args.port), Handler) as server:
        print(f"Blackjack Table listening on {args.host}:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
