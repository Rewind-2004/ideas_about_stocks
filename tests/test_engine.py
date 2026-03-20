from app.engine import SignalEngine


def test_generate_cn_signals() -> None:
    engine = SignalEngine()
    rows = engine.generate_daily_signals(market='CN')
    assert rows
    assert all(x.market == 'CN' for x in rows)


def test_watchlist_roundtrip() -> None:
    engine = SignalEngine()
    assert engine.add_watch('nvda')
    assert 'NVDA' in engine.list_watch()
    engine.remove_watch('nvda')
    assert 'NVDA' not in engine.list_watch()


def test_deterministic_generation_for_same_day() -> None:
    engine = SignalEngine()
    first = [engine.to_dict(x) for x in engine.generate_daily_signals()]
    second = [engine.to_dict(x) for x in engine.generate_daily_signals()]
    assert first == second


def test_kline_ohlc_constraints() -> None:
    engine = SignalEngine()
    rows = engine.generate_daily_signals()
    for item in rows:
        k = item.predicted_kline
        assert k['high'] >= max(k['open'], k['close'])
        assert k['low'] <= min(k['open'], k['close'])
