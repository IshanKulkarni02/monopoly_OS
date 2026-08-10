import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import accounts, auctions, banker, board_editor, boards, currency, games, irl_live, players, trading, transfer, virtual, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="monopoly_OS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN/party-game use; narrow this if publicly deployed
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(accounts.router)
app.include_router(games.router)
app.include_router(boards.router)
app.include_router(board_editor.router)
app.include_router(currency.router)
app.include_router(banker.router)
app.include_router(auctions.router)
app.include_router(trading.router)
app.include_router(irl_live.router)
app.include_router(players.router)
app.include_router(transfer.router)
app.include_router(virtual.router)
app.include_router(ws.router)

# Serve the built frontend as a single deployable artifact when present.
# A PyInstaller desktop build has no source tree to walk up from — its data
# files land relative to `sys._MEIPASS` (the bundle's extraction dir) instead.
if getattr(sys, "frozen", False):
    _frontend_dist = Path(getattr(sys, "_MEIPASS", ".")) / "frontend_dist"
else:
    _frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
