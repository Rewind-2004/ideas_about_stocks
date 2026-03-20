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
