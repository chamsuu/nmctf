#!/usr/bin/env python3

import hashlib
import random
import re

FLAG = open("flag.txt").read().strip()


def seal(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()[:12]


def decode_message(s: str) -> bytes:
    """Decode hex-encoded input if valid hex, otherwise encode as UTF-8."""
    try:
        if len(s) >= 2 and len(s) % 2 == 0 and all(c in '0123456789abcdefABCDEF' for c in s):
            return bytes.fromhex(s)
    except ValueError:
        pass
    return s.encode()


class Player:
    def __init__(self, name: str, balance: int = None):
        self.name = name
        self.balance = balance if balance is not None else random.randint(90, 120)
        self.bid = None

    def commit(self, message: str):
        msg_bytes = decode_message(message)
        msg_str = msg_bytes.decode('latin-1')
        match = re.search(r'bid=(\d+)&item=flag', msg_str)
        if not match:
            return False, "Invalid format (expected: bid=<amount>&item=flag)."
        bid = int(match.group(1))
        if bid > self.balance:
            return False, f"Over budget! Your balance is {self.balance}."
        h = seal(msg_bytes)
        return True, h

    def place_bid(self, amount: int):
        self.bid = amount


class NPC(Player):
    def __init__(self, name: str, min_bid: int, max_bid: int):
        super().__init__(name, balance=float('inf'))
        self.min_bid = min_bid
        self.max_bid = max_bid

    def generate_bid(self):
        bid = random.randint(self.min_bid, self.max_bid)
        self.place_bid(bid)
        return bid


class Auction:
    def __init__(self):
        self.players = []
        self.commitments = {}

    def add_player(self, player: Player):
        self.players.append(player)

    def commit(self, player_name: str, h: str):
        self.commitments[player_name] = h

    def reveal(self, player_name: str, message: str):
        if player_name not in self.commitments:
            return False, "No commitment found."
        msg_bytes = decode_message(message)
        if seal(msg_bytes) != self.commitments[player_name]:
            return False, "Seal mismatch."
        msg_str = msg_bytes.decode('latin-1')
        match = re.search(r'bid=(\d+)&item=flag', msg_str)
        if not match:
            return False, "Invalid format (expected: bid=<amount>&item=flag)."
        bid = int(match.group(1))
        return True, bid

    def all_bids(self):
        return {p.name: p.bid for p in self.players if p.bid is not None}

    def highest_bid(self):
        valid = [p for p in self.players if p.bid is not None]
        if not valid:
            return None
        return max(valid, key=lambda p: p.bid)


def main():
    print("=== Blind Auction ===")

    name = f"Player_{random.randint(1000, 9999)}"
    human = Player(name)
    auction = Auction()

    npc_data = [
        ("Orion", 100, 180),
        ("Luna",  120, 200),
        ("Kai",   140, 220),
    ]
    npcs = [NPC(n, low, high) for n, low, high in npc_data]

    auction.add_player(human)
    for npc in npcs:
        auction.add_player(npc)

    print(f"Hello {human.name}! Your budget: {human.balance}")
    print("Message format: bid=<amount>&item=flag")
    print("Hex-encoded messages are detected automatically")

    while True:
        print("\n--- MENU ---")
        print("1. COMMIT (submit your bid seal)")
        print("2. OPEN (reveal your bid message)")
        print("3. EXIT")
        choice = input("> ").strip()

        if choice == "3":
            print("Goodbye.")
            break

        if choice == "1":
            msg = input("Enter your bid message: ").strip()
            if not msg:
                print("Empty message.")
                continue
            ok, result = human.commit(msg)
            if not ok:
                print(result)
                continue
            auction.commit(human.name, result)
            print(f"Ticket: {result}")

        elif choice == "2":
            msg = input("Enter your FULL bid message: ").strip()
            if not msg:
                continue
            ok, result = auction.reveal(human.name, msg)
            if not ok:
                print(result)
                continue
            bid = result
            human.place_bid(bid)

            for npc in npcs:
                npc.generate_bid()

            print("\nAll bids:")
            for p in auction.players:
                if p.bid is not None:
                    print(f"  {p.name}: {p.bid}")

            winner = auction.highest_bid()
            if winner is None:
                print("\nNo valid bids.")
            else:
                print(f"\nHighest bid: {winner.name} with {winner.bid}")

                if winner is human:
                    print("You win!")
                    print(f"FLAG: {FLAG}")
                    break
                else:
                    print("You lose.")

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
