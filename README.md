# monopoly_OS

A companion platform for running a real-life Monopoly game night: banker, host, and player
accounts, cash + property tracking, and a live play log — running on a laptop for game night or
deployed to a server for remote play.

**Phase 1 (shipped):** the IRL companion mode — a physical board and dice, with the app handling
accounts, money, property, and logs. Players join a lobby with a short code, a banker (human or
the app itself, in **auto banker mode**) tracks every rent/tax/purchase, and everyone sees a live
play log and their own personal transaction history.

**Planned next** (the data model already supports these without a rewrite — see
`backend/app/game_engine/rules.py`): a cash-counter mode and a UPI-style digital-transfer money
mode, spin-the-wheel as an alternative to Chance/Community Chest, an optional buy-in challenge
before purchasing property, per-round/per-lap inflation, and eventually a full virtual
(no-physical-board) game mode.

## Architecture

- `backend/` — Python 3.12 + FastAPI, SQLAlchemy (SQLite by default, swap via `DATABASE_URL`),
  WebSocket broadcast per game room. See `backend/app/game_engine/` for the rules/board/money logic.
- `frontend/` — React + Vite + TypeScript + Tailwind, mobile-first (players use their own phones).

## Run locally (development)

Two terminals:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (e.g. `http://localhost:5173`). To let other players on your WiFi join
from their phones, use your machine's LAN IP instead of `localhost`, e.g. `http://192.168.1.23:5173`
— the dev server is already configured to listen on all interfaces and proxy API/WebSocket calls
to the backend.

Run the backend test suite with:

```bash
cd backend
uv run pytest
```

## Run as one deployable artifact (Docker)

This builds the frontend and bundles it into the FastAPI backend, so a single container serves
everything on one port — the same image works for a living-room game night or a real server.

```bash
docker compose up --build
```

Then open `http://localhost:8000` (or `http://<your-LAN-ip>:8000` for other players on the same
WiFi). Game data persists in a Docker volume (`monopoly_data`) as a SQLite file, so restarting the
container doesn't lose in-progress games.

## Run as a desktop app (macOS/Windows)

For a host who'd rather double-click an icon than run terminal commands, `scripts/build_desktop.py`
bundles the backend (with the built frontend inside it) into a standalone app using PyInstaller —
no Python or Node install required to *run* it, only to *build* it. Launching it starts the server
and opens your browser to it automatically; other players still join the same way, from their own
phones on the same WiFi, using the LAN URL the app logs on startup.

```bash
python scripts/build_desktop.py
```

This produces:
- **macOS**: `dist/monopoly_OS.app`, wrapped into `dist/monopoly_OS.dmg`
- **Windows**: a standalone `dist/monopoly_OS.exe`

PyInstaller can't cross-compile, so a Windows `.exe` has to actually be built on Windows — the
same script runs there too, and `.github/workflows/build-desktop.yml` does exactly that in CI
(macOS + Windows runners) on a version tag push or manual trigger, so you don't need a Windows
machine yourself just to get the `.exe`.

Game data lives in your OS's normal per-app data folder (`~/Library/Application Support/monopoly_OS/`
on macOS, `%APPDATA%\monopoly_OS\` on Windows), not next to the app bundle, so it survives
reinstalling/updating the app. If something goes wrong and no browser tab opens, check
`launcher.log` in that same folder.

**Neither build is code-signed** (that needs a paid Apple Developer / Windows code-signing
certificate), so the OS will flag it the first time: macOS Gatekeeper says the app "can't be
opened because it is from an unidentified developer" (right-click → Open, or allow it in System
Settings → Privacy & Security), and Windows SmartScreen says "Windows protected your PC" (click
"More info" → "Run anyway"). This is expected for an unsigned build, not a sign anything's wrong.

### Deploying to a server

Push the same image to any host that can run a container (a small VPS, Fly.io, Railway, etc.),
expose port 8000 (typically behind a reverse proxy that terminates TLS), and share the public URL
+ join code with players. To use Postgres instead of the bundled SQLite (e.g. for a longer-lived
public deployment), set the `DATABASE_URL` environment variable — the backend reads it directly
and everything else is unchanged.

## How a game works

1. Host creates a game (name, starting cash, and banker mode: **manual** or **auto**) and gets a
   short join code + QR code.
2. Players open the link/QR, enter the code + a nickname — no accounts or passwords.
3. Host starts the game once at least 2 players have joined; the board is seeded from the classic
   Monopoly property list.
4. In **manual** banker mode, the designated banker (defaults to the host, reassignable to anyone)
   logs every transaction by hand. In **auto** banker mode, any player just declares "I landed on
   ___" and the app calculates and applies rent/tax automatically — no math, no banker required.
5. Everyone sees live balances, the property board, a global play log, and their own personal log.
