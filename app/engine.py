from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from random import Random
from typing import Dict, List


@dataclass
class StockSignal:
    symbol: str
    name: str
    market: str
    sector: str
    direction: str
    pattern: str
    technical_score: float
    llm_score: float
    context_score: float
    macro_score: float
    confidence: float
    score: float
    reasons: List[str]
    risks: List[str]
    entry_zone: Dict[str, float]
    stop_loss: float
    take_profit: float
    predicted_kline: Dict[str, float]


UNIVERSE = [
    ("600519", "贵州茅台", "CN", "消费"),
    ("000333", "美的集团", "CN", "家电"),
    ("300750", "宁德时代", "CN", "新能源"),
    ("AAPL", "Apple", "US", "科技"),
    ("NVDA", "NVIDIA", "US", "半导体"),
    ("XOM", "Exxon Mobil", "US", "能源"),
]

PATTERNS = [
    "VolatilityExpansionBreakout",
    "SnapbackMeanReversion",
    "EarningsDrift",
    "SectorBurst",
    "SentimentWashout",
    "GeopoliticalShock",
]


class SignalEngine:
    def __init__(self) -> None:
        self._watchlist: set[str] = set()

    @staticmethod
    def _seed_for(today: date, symbol: str) -> int:
        return hash(f"{today.isoformat()}::{symbol}") & 0xFFFFFFFF

    def generate_daily_signals(self, market: str | None = None) -> List[StockSignal]:
        today = date.today()
        rows: List[StockSignal] = []
        for symbol, name, mkt, sector in UNIVERSE:
            if market and mkt != market:
                continue
            rnd = Random(self._seed_for(today, symbol))
            tech = round(rnd.uniform(40, 92), 2)
            llm = round(rnd.uniform(35, 95), 2)
            context = round(rnd.uniform(30, 90), 2)
            macro = round(rnd.uniform(30, 85), 2)
            score = round(0.35 * tech + 0.30 * llm + 0.25 * context + 0.10 * macro, 2)
            direction = "bull" if score >= 62 else "bear" if score <= 45 else "neutral"
            base = round(rnd.uniform(20, 280), 2)
            atr = round(base * rnd.uniform(0.015, 0.04), 2)
            entry_low = round(base * 0.985, 2)
            entry_high = round(base * 1.0, 2)
            candle = {
                "open": round(base * rnd.uniform(0.99, 1.01), 2),
                "high": round(base * rnd.uniform(1.01, 1.04), 2),
                "low": round(base * rnd.uniform(0.96, 0.99), 2),
                "close": round(base * rnd.uniform(0.985, 1.03), 2),
            }
            rows.append(
                StockSignal(
                    symbol=symbol,
                    name=name,
                    market=mkt,
                    sector=sector,
                    direction=direction,
                    pattern=PATTERNS[rnd.randrange(0, len(PATTERNS))],
                    technical_score=tech,
                    llm_score=llm,
                    context_score=context,
                    macro_score=macro,
                    confidence=score,
                    score=score,
                    reasons=[
                        "成交量放大并伴随趋势确认",
                        "行业相对强弱排名提升",
                        "事件冲击与行业暴露度匹配",
                    ],
                    risks=["宏观波动率上行", "事件噪音导致误判"],
                    entry_zone={"low": entry_low, "high": entry_high},
                    stop_loss=round(entry_low - 1.5 * atr, 2),
                    take_profit=round(entry_high + 2.5 * atr, 2),
                    predicted_kline=candle,
                )
            )

        rows.sort(key=lambda x: x.score, reverse=True)
        return rows

    def get_signal(self, symbol: str) -> StockSignal | None:
        symbol = symbol.upper()
        for item in self.generate_daily_signals():
            if item.symbol.upper() == symbol:
                return item
        return None

    def add_watch(self, symbol: str) -> bool:
        symbol = symbol.upper().strip()
        if not symbol:
            return False
        self._watchlist.add(symbol)
        return True

    def remove_watch(self, symbol: str) -> None:
        self._watchlist.discard(symbol.upper().strip())

    def list_watch(self) -> List[str]:
        return sorted(self._watchlist)

    def to_dict(self, signal: StockSignal) -> Dict:
        payload = asdict(signal)
        payload["is_watch"] = signal.symbol.upper() in self._watchlist
        return payload
