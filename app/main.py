from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.engine import SignalEngine

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class WatchlistRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=12)


class WatchlistResponse(BaseModel):
    watchlist: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATIC_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(title="SIGNAL.AI", version="0.2.0", lifespan=lifespan)
engine = SignalEngine()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "date": date.today().isoformat(), "version": "0.2.0"}


@app.get("/api/v1/predictions")
def predictions(market: Optional[Literal["CN", "US"]] = None) -> dict:
    items = [engine.to_dict(x) for x in engine.generate_daily_signals(market=market)]
    return {
        "date": date.today().isoformat(),
        "count": len(items),
        "bull_count": sum(1 for x in items if x["direction"] == "bull"),
        "bear_count": sum(1 for x in items if x["direction"] == "bear"),
        "items": items,
    }


@app.get("/api/v1/predictions/{symbol}")
def prediction_detail(symbol: str) -> dict:
    signal = engine.get_signal(symbol)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
    return engine.to_dict(signal)


@app.get("/api/v1/watchlist", response_model=WatchlistResponse)
def get_watchlist() -> WatchlistResponse:
    return WatchlistResponse(watchlist=engine.list_watch())


@app.post("/api/v1/watchlist", response_model=WatchlistResponse, status_code=201)
def add_watchlist(req: WatchlistRequest) -> WatchlistResponse:
    if not engine.add_watch(req.symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")
    return WatchlistResponse(watchlist=engine.list_watch())


@app.delete("/api/v1/watchlist/{symbol}", response_model=WatchlistResponse)
def delete_watchlist(symbol: str) -> WatchlistResponse:
    engine.remove_watch(symbol)
    return WatchlistResponse(watchlist=engine.list_watch())
