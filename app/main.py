from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.engine import SignalEngine


class WatchlistRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=12)


class WatchlistResponse(BaseModel):
    watchlist: list[str]


app = FastAPI(title="SIGNAL.AI MVP", version="0.1.0")
engine = SignalEngine()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "date": date.today().isoformat()}


@app.get("/api/v1/predictions")
def predictions(market: Optional[Literal["CN", "US"]] = None) -> dict:
    rows = [engine.to_dict(x) for x in engine.generate_daily_signals(market=market)]
    return {"date": date.today().isoformat(), "count": len(rows), "items": rows}


@app.get("/api/v1/predictions/{symbol}")
def prediction_detail(symbol: str) -> dict:
    signal = engine.get_signal(symbol)
    if not signal:
        raise HTTPException(status_code=404, detail="Symbol not found in current universe")
    return engine.to_dict(signal)


@app.get("/api/v1/watchlist", response_model=WatchlistResponse)
def get_watchlist() -> WatchlistResponse:
    return WatchlistResponse(watchlist=engine.list_watch())


@app.post("/api/v1/watchlist", response_model=WatchlistResponse)
def add_watchlist(req: WatchlistRequest) -> WatchlistResponse:
    if not engine.add_watch(req.symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")
    return WatchlistResponse(watchlist=engine.list_watch())


@app.delete("/api/v1/watchlist/{symbol}", response_model=WatchlistResponse)
def delete_watchlist(symbol: str) -> WatchlistResponse:
    engine.remove_watch(symbol)
    return WatchlistResponse(watchlist=engine.list_watch())
