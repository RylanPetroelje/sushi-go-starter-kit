#!/usr/bin/env python3
"""
First Card Bot - A simple Sushi Go player that always picks the first card.

Usage:
    python first_card_bot.py <game_id> <player_name> [host] [port]

Example:
    python first_card_bot.py abc123 FirstBot
    python first_card_bot.py abc123 FirstBot localhost 7878
"""

import socket
import sys
import random
import time


def main():
    if len(sys.argv) < 3:
        print("Usage: python first_card_bot.py <game_id> <player_name> [host] [port]")
        sys.exit(1)

    game_id = sys.argv[1]
    player_name = sys.argv[2]
    host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 7878

    print(f"Connecting to {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock_file = sock.makefile('r')
    print("Connected!")

    def send(cmd):
        print(f">>> {cmd}")
        sock.sendall((cmd + "\n").encode())

    def recv():
        msg = sock_file.readline().strip()
        if not msg:
            raise ConnectionError("Server closed connection")
        print(f"<<< {msg}")
        return msg

    try:
        # Join the game
        send(f"JOIN {game_id} {player_name}")
        response = recv()
        if not response.startswith("WELCOME"):
            print(f"Failed to join: {response}")
            return

        # Signal ready (will be acknowledged even if game already started)
        send("READY")

        # Main game loop - HAND is only sent when it's time to play
        while True:
            msg = recv()

            if msg.startswith("GAME_END"):
                print("Game over!")
                break
            elif msg.startswith("HAND"):
                # HAND means it's our turn - wait a bit then play the first card
                delay = random.uniform(0.5, 2.5)
                time.sleep(delay)
                send("PLAY 0")
            # Ignore other messages (JOINED, GAME_START, ROUND_START, PLAYED, WAITING, OK, etc.)

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
