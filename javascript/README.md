# JavaScript Client

## Requirements

- Node.js 18+
- No npm dependencies — uses only the built-in `net` and `readline` modules

## Files

| File | Description |
|------|-------------|
| `sushi_go_client.js` | Full-featured client with state tracking and a priority-based strategy |

## Usage

```bash
node sushi_go_client.js <host> <port> <game_id> <player_name>
node sushi_go_client.js localhost 7878 abc123 MyBot
```

## Implementing Your Strategy

Edit the `chooseCard` method in `sushi_go_client.js`:

```javascript
chooseCard(hand) {
    /**
     * Choose which card to play.
     *
     * @param {string[]} hand - Card names (e.g., ["Tempura", "Salmon Nigiri", "Pudding"])
     * @returns {number} Index of the card to play (0-based)
     */
    // Your strategy here!
    return 0;
}
```

The default implementation uses a simple priority list. Replace it with your own logic.

## Key Patterns

### Buffered reading

The client buffers incoming TCP data and splits on newlines, since messages may arrive in chunks:

```javascript
receive() {
    return new Promise((resolve) => {
        const checkBuffer = () => {
            const idx = this.buffer.indexOf('\n');
            if (idx !== -1) {
                const msg = this.buffer.substring(0, idx);
                this.buffer = this.buffer.substring(idx + 1);
                resolve(msg);
                return true;
            }
            return false;
        };
        if (checkBuffer()) return;
        const onData = (data) => {
            this.buffer += data.toString();
            if (checkBuffer()) this.socket.removeListener('data', onData);
        };
        this.socket.on('data', onData);
    });
}
```

### HAND = your turn

Only send `PLAY` when you receive a `HAND` message. The server sends `HAND` exactly when it's time for you to act — not as a status update.

### State tracking

The client tracks played cards, chopsticks, and wasabi state via `this.state`. Use it to make smarter decisions.

## Protocol

See [../PROTOCOL.md](../PROTOCOL.md) for the full protocol specification.
