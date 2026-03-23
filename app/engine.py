from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from hashlib import blake2b
from random import Random
from typing import Dict, List, Optional


@dataclass
class StockSignal:
    symbol: str
    name: str
    market: str
    sector: str
    direction: str           # "bull" | "bear" | "neutral"
    pattern: str
    technical_score: float
    llm_score: float
    context_score: float
    macro_score: float
    score: float             # weighted composite 0-100
    confidence: float        # alias of score, kept for API compatibility
    reasons: List[str]
    risks: List[str]
    entry_zone: Dict[str, float]
    stop_loss: float
    take_profit: float
    prev_kline: Dict[str, float]       # yesterday actual OHLC
    predicted_kline: Dict[str, float]  # today predicted OHLC


# (symbol, name, market, sector, realistic_base_price)
UNIVERSE = [
    ("600519", "贵州茅台", "CN", "白酒", 1720.0),
    ("000333", "美的集团", "CN", "家电", 65.0),
    ("300750", "宁德时代", "CN", "新能源", 180.0),
    ("601398", "工商银行", "CN", "银行", 5.5),
    ("000858", "五粮液", "CN", "白酒", 130.0),
    ("002594", "比亚迪", "CN", "新能源车", 245.0),
    ("AAPL", "Apple", "US", "科技", 190.0),
    ("NVDA", "NVIDIA", "US", "半导体", 875.0),
    ("TSLA", "Tesla", "US", "新能源车", 172.0),
    ("XOM", "Exxon", "US", "能源", 116.0),
    ("MSFT", "Microsoft", "US", "科技", 415.0),
    ("AMZN", "Amazon", "US", "消费科技", 205.0),
]

PATTERNS = [
    "VolatilityExpansionBreakout",
    "SnapbackMeanReversion",
    "EarningsDrift",
    "SectorBurst",
    "SentimentWashout",
    "GeopoliticalShock",
]

_REASONS: Dict[str, List[str]] = {
    "VolatilityExpansionBreakout": [
        "ATR(14) 较20日均值放大42%，波动率扩张确认有效突破，非低量假突破",
        "收盘价突破近20日高点，成交量同步放大1.8倍，筹码换手充分",
        "资金流向数据显示今日净买入，主力资金参与意愿上升",
    ],
    "SnapbackMeanReversion": [
        "价格连续偏离布林带2σ区间，超卖程度处于近30日90th百分位",
        "今日成交量较前5日均量萎缩22%，恐慌性抛售动能明显衰竭",
        "下影线占全日振幅超40%，盘中有主动性承接盘介入",
    ],
    "EarningsDrift": [
        "财报超预期幅度≥5%，PEAD效应在A/美股历史统计中均显著",
        "分析师集体上调EPS预期，市场对信息的消化尚未充分定价",
        "机构持仓报告显示增配，方向与本次信号一致",
    ],
    "SectorBurst": [
        "行业龙头今日大幅异动，板块联动效应触发二线标的跟进窗口",
        "同行业其他标的尚未跟随，存在1-2日价格补涨空间",
        "行业资金净流入排名上升至市场前三，板块景气度改善",
    ],
    "SentimentWashout": [
        "过去48h负面情绪得分处于近30日高位，悲观情绪出现顶部特征",
        "量价背离：成交量放大但价格止跌，恐慌盘出清信号确认",
        "WorldMonitor 相关事件情绪已从峰值回落，基本面未实质恶化",
    ],
    "GeopoliticalShock": [
        "WorldMonitor CII 7日变化触发高冲击阈值，相关行业暴露度已量化",
        "市场反应过度，地缘事件与行业供应链映射形成非对称定价机会",
        "Polymarket 预测市场概率变动先于媒体确认，属领先指标信号",
    ],
}

_RISKS: Dict[str, List[str]] = {
    "VolatilityExpansionBreakout": ["波动率高峰后可能快速回落，需关注成交量持续性"],
    "SnapbackMeanReversion": ["若基本面利空持续发酵，均值修复可能延迟或失效"],
    "EarningsDrift": ["若市场整体风险偏好下行，财报漂移效应可能被宏观掩盖"],
    "SectorBurst": ["龙头涨幅过大后板块可能获利了结，注意尾盘动向"],
    "SentimentWashout": ["情绪清洗后若有新增负面催化，可能形成二次探底"],
    "GeopoliticalShock": ["地缘事件存在不可预测升级风险，仓位需严格控制在上限内"],
}


class SignalEngine:
    def __init__(self) -> None:
        # In-memory only. Production: persist to Redis or DB.
        self._watchlist: set[str] = set()

    @staticmethod
    def _seed(today: date, symbol: str) -> int:
        raw = blake2b(f"{today.isoformat()}::{symbol}".encode(), digest_size=8).digest()
        return int.from_bytes(raw, byteorder="big", signed=False)

    @staticmethod
    def _build_candle(rnd: Random, base: float, drift: float = 1.0) -> Dict[str, float]:
        """Single OHLC candle biased by drift (>1 bullish, <1 bearish, 1.0 neutral)."""
        close = round(base * drift * rnd.uniform(0.994, 1.006), 2)
        open_ = round(base * rnd.uniform(0.997, 1.003), 2)
        high = round(max(open_, close) * rnd.uniform(1.003, 1.018), 2)
        low = round(min(open_, close) * rnd.uniform(0.982, 0.997), 2)
        return {
            "open": open_,
            "high": max(high, open_, close),  # H ≥ max(O,C) guaranteed
            "low": min(low, open_, close),  # L ≤ min(O,C) guaranteed
            "close": close,
        }

    def _make_signal(
        self,
        symbol: str,
        name: str,
        market: str,
        sector: str,
        base: float,
        rnd: Random,
    ) -> StockSignal:
        tech = round(rnd.uniform(38, 94), 1)
        llm_s = round(rnd.uniform(35, 96), 1)
        ctx = round(rnd.uniform(30, 92), 1)
        macro_s = round(rnd.uniform(28, 88), 1)
        score = round(0.35 * tech + 0.30 * llm_s + 0.25 * ctx + 0.10 * macro_s, 1)

        direction = "bull" if score >= 62 else "bear" if score <= 44 else "neutral"
        pattern = PATTERNS[rnd.randrange(len(PATTERNS))]

        # Yesterday: neutral; today: biased by signal direction
        drift = 1.018 if direction == "bull" else 0.982 if direction == "bear" else 1.0
        prev_k = self._build_candle(rnd, base, drift=1.0)
        pred_k = self._build_candle(rnd, prev_k["close"], drift=drift)

        atr = base * rnd.uniform(0.015, 0.030)
        entry_low = round(prev_k["close"] * 0.985, 2)
        entry_high = round(prev_k["close"] * 1.000, 2)

        reasons = list(_REASONS.get(pattern, ["技术指标综合信号触发", "量价结构改善", "行业相对强弱提升"]))
        risks = list(_RISKS.get(pattern, ["宏观波动率上行可能压制短期表现"]))
        if direction == "bear":
            risks.append("破位后建议快速止损，控制单笔损失在预设范围内")

        return StockSignal(
            symbol=symbol,
            name=name,
            market=market,
            sector=sector,
            direction=direction,
            pattern=pattern,
            technical_score=tech,
            llm_score=llm_s,
            context_score=ctx,
            macro_score=macro_s,
            score=score,
            confidence=score,
            reasons=reasons,
            risks=risks,
            entry_zone={"low": entry_low, "high": entry_high},
            stop_loss=round(entry_low - 1.5 * atr, 2),
            take_profit=round(entry_high + 2.5 * atr, 2),
            prev_kline=prev_k,
            predicted_kline=pred_k,
        )

    def generate_daily_signals(self, market: Optional[str] = None) -> List[StockSignal]:
        today = date.today()
        rows: List[StockSignal] = []
        for symbol, name, mkt, sector, base in UNIVERSE:
            if market and mkt != market:
                continue
            rnd = Random(self._seed(today, symbol))
            rows.append(self._make_signal(symbol, name, mkt, sector, base, rnd))
        rows.sort(key=lambda x: x.score, reverse=True)
        return rows

    def get_signal(self, symbol: str) -> Optional[StockSignal]:
        for item in self.generate_daily_signals():
            if item.symbol.upper() == symbol.upper():
                return item
        return None

    def add_watch(self, symbol: str) -> bool:
        s = symbol.upper().strip()
        if not s:
            return False
        self._watchlist.add(s)
        return True

    def remove_watch(self, symbol: str) -> None:
        self._watchlist.discard(symbol.upper().strip())

    def list_watch(self) -> List[str]:
        return sorted(self._watchlist)

    def to_dict(self, signal: StockSignal) -> Dict:
        d = asdict(signal)
        d["is_watch"] = signal.symbol.upper() in self._watchlist
        return d
