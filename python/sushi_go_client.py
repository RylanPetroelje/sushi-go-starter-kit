#!/usr/bin/env python3
"""
Sushi Go Client - Python Starter Kit

This client connects to the Sushi Go server and plays using a simple strategy.
Modify the `choose_card` method to implement your own AI!

Usage:
    python sushi_go_client.py <server_host> <server_port> <game_id> <player_name>

Example:
    python sushi_go_client.py localhost 7878 abc123 MyBot
"""

import random
import re
import socket
import sys
from dataclasses import dataclass
from typing import Optional

# Card names used by the protocol (now using full names instead of codes)
CARD_NAMES = {
    "Tempura": "Tempura",
    "Sashimi": "Sashimi",
    "Dumpling": "Dumpling",
    "Maki Roll (1)": "Maki Roll (1)",
    "Maki Roll (2)": "Maki Roll (2)",
    "Maki Roll (3)": "Maki Roll (3)",
    "Egg Nigiri": "Egg Nigiri",
    "Salmon Nigiri": "Salmon Nigiri",
    "Squid Nigiri": "Squid Nigiri",
    "Pudding": "Pudding",
    "Wasabi": "Wasabi",
    "Chopsticks": "Chopsticks",
}

DECK_COUNTS = {
    "Tempura": 14,
    "Sashimi": 14,
    "Dumpling": 14,
    "Maki Roll (1)": 6,
    "Maki Roll (2)": 12,
    "Maki Roll (3)": 8,
    "Egg Nigiri": 5,
    "Salmon Nigiri": 10,
    "Squid Nigiri": 5,
    "Pudding": 10,
    "Wasabi": 6,
    "Chopsticks": 4,
}


@dataclass
class GameState:
    """Tracks the current state of the game."""

    game_id: str
    player_id: int
    hand: list[str]
    round: int = 1
    turn: int = 1
    played_cards: list[str] = None
    has_chopsticks: bool = False
    has_unused_wasabi: bool = False
    puddings: int = 0

    def __post_init__(self):
        if self.played_cards is None:
            self.played_cards = []


class SushiGoClient:
    """A client for playing Sushi Go."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.state: Optional[GameState] = None
        self._recv_buffer = ""

    def connect(self):
        """Connect to the server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self._recv_buffer = ""
        print(f"Connected to {self.host}:{self.port}")

    def disconnect(self):
        """Disconnect from the server."""
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, command: str):
        """Send a command to the server."""
        message = command + "\n"
        self.sock.sendall(message.encode("utf-8"))
        print(f">>> {command}")

    def receive(self) -> str:
        """Receive one line-delimited message from the server."""
        while True:
            if "\n" in self._recv_buffer:
                line, self._recv_buffer = self._recv_buffer.split("\n", 1)
                message = line.strip()
                print(f"<<< {message}")
                return message

            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Server closed connection")
            self._recv_buffer += chunk.decode("utf-8", errors="replace")

    def receive_until(self, predicate) -> str:
        """Read lines until one matches predicate."""
        while True:
            message = self.receive()
            if not message:
                continue
            if predicate(message):
                return message

    def join_game(self, game_id: str, player_name: str) -> bool:
        """Join a game."""
        self.send(f"JOIN {game_id} {player_name}")
        response = self.receive_until(
            lambda line: line.startswith("WELCOME") or line.startswith("ERROR")
        )

        if response.startswith("WELCOME"):
            parts = response.split()
            self.state = GameState(game_id=parts[1], player_id=int(parts[2]), hand=[])
            return True
        elif response.startswith("ERROR"):
            print(f"Failed to join: {response}")
            return False
        return False

    def signal_ready(self):
        """Signal that we're ready to start."""
        self.send("READY")
        return self.receive()

    def play_card(self, card_index: int):
        """Play a card by index."""
        self.send(f"PLAY {card_index}")
        return self.receive()

    def play_chopsticks(self, index1: int, index2: int):
        """Use chopsticks to play two cards."""
        self.send(f"CHOPSTICKS {index1} {index2}")
        return self.receive()

    def parse_hand(self, message: str):
        """Parse a HAND message and update state."""
        if message.startswith("HAND"):
            payload = message[len("HAND ") :]
            cards = []
            for match in re.finditer(r"(\d+):(.*?)(?=\s\d+:|$)", payload):
                cards.append(match.group(2).strip())
            if self.state:
                self.state.hand = cards
                # Update chopsticks/wasabi tracking based on played cards
                self.state.has_chopsticks = "Chopsticks" in self.state.played_cards
                self.state.has_unused_wasabi = any(
                    c == "Wasabi" for c in self.state.played_cards
                ) and not any(
                    c in ("Egg Nigiri", "Salmon Nigiri", "Squid Nigiri")
                    for c in self.state.played_cards
                )

    def estimate_remaining_probability(self, card_name: str) -> float:
        """
        Estimate probability of seeing at least one of card_name later this round.
        """

        state = self.state
        total_seen = state.played_cards + state.hand

        total_in_deck = DECK_COUNTS.get(card_name, 0)
        seen_count = total_seen.count(card_name)

        remaining = max(total_in_deck - seen_count, 0)

        # Rough estimate of cards we'll still see this round
        cards_left_in_round = max(0, 10 - state.turn)

        if remaining <= 0 or cards_left_in_round == 0:
            return 0.0

        # Simple probability approximation
        # P(seen at least once) ≈ 1 - (no hit probability)
        prob_not_seen = (1 - remaining / sum(DECK_COUNTS.values())) ** cards_left_in_round
        return 1 - prob_not_seen

    def choose_card(self, hand: list[str]) -> int:
        """
        Choose which card to play.

        This is where you implement your AI strategy!
        The default implementation uses a simple priority-based approach.

        Args:
            hand: List of card codes in your current hand

        Returns:
            Index of the card to play (0-based)
        """
        # # Simple priority-based strategy
        # priority = [
        #     "Squid Nigiri",  # 3 points, or 9 with wasabi
        #     "Salmon Nigiri",  # 2 points, or 6 with wasabi
        #     "Maki Roll (3)",  # 3 maki rolls
        #     "Maki Roll (2)",  # 2 maki rolls
        #     "Tempura",  # 5 points per pair
        #     "Sashimi",  # 10 points per set of 3
        #     "Dumpling",  # Increasing value
        #     "Wasabi",  # Triples next nigiri
        #     "Egg Nigiri",  # 1 point, or 3 with wasabi
        #     "Pudding",  # End game scoring
        #     "Maki Roll (1)",  # 1 maki roll
        #     "Chopsticks",  # Play 2 cards next turn
        # ]

        # # If we have wasabi, prioritize nigiri
        # if self.state and self.state.has_unused_wasabi:
        #     for nigiri in ["Squid Nigiri", "Salmon Nigiri", "Egg Nigiri"]:
        #         if nigiri in hand:
        #             return hand.index(nigiri)

        # # Otherwise use priority list
        # for card in priority:
        #     if card in hand:
        #         return hand.index(card)

        # # Fallback: random
        # return random.randint(0, len(hand) - 1)
        """
        Strategic AI:
        - Early Sashimi commitment
        - Strong Dumpling scaling
        - Complete Tempura pairs
        - Proper Wasabi usage
        - Grab pudding safely
        """

        state = self.state
        played = state.played_cards

        # ---- Count what we've already built ----
        dumplings = played.count("Dumpling")
        sashimi = played.count("Sashimi")
        tempura = played.count("Tempura")
        puddings = state.puddings

        # ---- 1. If we have unused Wasabi, play best Nigiri ----
        # If we already have unused Wasabi
        if state.has_unused_wasabi:

            # Always take Squid
            if "Squid Nigiri" in hand:
                return hand.index("Squid Nigiri")

            # If probability of future Squid is low, settle
            p_squid = self.estimate_remaining_probability("Squid Nigiri")

            if p_squid < 0.25:
                for nigiri in ["Salmon Nigiri", "Egg Nigiri"]:
                    if nigiri in hand:
                        return hand.index(nigiri)

        # If considering playing Wasabi
        if "Wasabi" in hand:

            p_squid = self.estimate_remaining_probability("Squid Nigiri")
            p_salmon = self.estimate_remaining_probability("Salmon Nigiri")
            p_egg = self.estimate_remaining_probability("Egg Nigiri")

            # Expected value of playing Wasabi
            ev = (
                p_squid * 9 +
                (1 - p_squid) * p_salmon * 6 +
                (1 - p_squid) * (1 - p_salmon) * p_egg * 3
            )

            # Since Wasabi costs a card, compare against average card value (~2.5)
            if ev > 3.5:  # threshold tuned experimentally
                return hand.index("Wasabi")

        # ---- 2. Early round Sashimi commitment ----
        # Only pursue in first half of round
        if state.turn <= 4:
            if sashimi < 3 and hand.count("Sashimi") > 0:
                # Only commit if we already have 1 OR multiple in hand
                if sashimi >= 1 or hand.count("Sashimi") >= 2:
                    return hand.index("Sashimi")

        # ---- 3. Complete Tempura pairs ----
        if tempura % 2 == 1 and "Tempura" in hand:
            return hand.index("Tempura")

        # ---- 4. Strong Dumpling scaling (best consistent strategy) ----
        if dumplings < 5 and "Dumpling" in hand:
            return hand.index("Dumpling")

        # ---- 5. Grab Pudding safely (early or mid round) ----
        if state.round <= 2 and "Pudding" in hand:
            return hand.index("Pudding")

        # ---- 6. Wasabi setup (only if nigiri likely) ----
        if "Wasabi" in hand and any(
            c in hand for c in ["Squid Nigiri", "Salmon Nigiri"]
        ):
            return hand.index("Wasabi")

        # ---- 7. High-value Nigiri fallback ----
        for nigiri in ["Squid Nigiri", "Salmon Nigiri", "Egg Nigiri"]:
            if nigiri in hand:
                return hand.index(nigiri)

        # ---- 8. Tempura starter ----
        if "Tempura" in hand:
            return hand.index("Tempura")

        # ---- 9. Light Maki only if nothing better ----
        for maki in ["Maki Roll (3)", "Maki Roll (2)", "Maki Roll (1)"]:
            if maki in hand:
                return hand.index(maki)

        # ---- 10. Chopsticks last ----
        if "Chopsticks" in hand:
            return hand.index("Chopsticks")

        # Fallback
        return random.randint(0, len(hand) - 1)

    def handle_message(self, message: str):
        """Handle a message from the server."""
        if message.startswith("HAND"):
            self.parse_hand(message)
        elif message.startswith("ROUND_START"):
            parts = message.split()
            if self.state:
                self.state.round = int(parts[1])
                self.state.turn = 1
                self.state.played_cards = []
        elif message.startswith("PLAYED"):
            # Cards were revealed, next turn
            if self.state:
                self.state.turn += 1
        elif message.startswith("ROUND_END"):
            # Round ended
            if self.state:
                self.state.played_cards = []
        elif message.startswith("GAME_END"):
            print("Game over!")
            return False
        elif message.startswith("WAITING"):
            # Our move was accepted, waiting for others
            pass
        return True

    def play_turn(self):
        """Play a single turn."""
        if not self.state or not self.state.hand:
            return

        card_index = self.choose_card(self.state.hand)

        # Track the card we're about to play
        played_card = self.state.hand[card_index]

        response = self.play_card(card_index)

        if response.startswith("OK"):
            if self.state:
                self.state.played_cards.append(played_card)

    def run(self, game_id: str, player_name: str):
        """Main game loop."""
        try:
            self.connect()

            if not self.join_game(game_id, player_name):
                return

            # Signal ready
            response = self.signal_ready()

            # Main game loop
            running = True
            while running:
                # Check for incoming messages
                message = self.receive()
                running = self.handle_message(message)

                # If we received our hand, play a card
                if message.startswith("HAND") and self.state and self.state.hand:
                    self.play_turn()

        except KeyboardInterrupt:
            print("\nDisconnecting...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.disconnect()


def main():
    if len(sys.argv) != 5:
        print("Usage: python sushi_go_client.py <host> <port> <game_id> <player_name>")
        print("Example: python sushi_go_client.py localhost 7878 abc123 MyBot")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    game_id = sys.argv[3]
    player_name = sys.argv[4]

    client = SushiGoClient(host, port)
    client.run(game_id, player_name)


if __name__ == "__main__":
    main()
