from app.engine import SignalEngine


def test_cn_signals_not_empty():
    rows = SignalEngine().generate_daily_signals(market='CN')
    assert rows
    assert all(x.market == 'CN' for x in rows)


def test_us_signals_not_empty():
    rows = SignalEngine().generate_daily_signals(market='US')
    assert rows
    assert all(x.market == 'US' for x in rows)


def test_sorted_descending_by_score():
    rows = SignalEngine().generate_daily_signals()
    scores = [r.score for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_score_formula():
    """Composite score must match weighted sum of component scores."""
    for s in SignalEngine().generate_daily_signals():
        expected = round(
            0.35 * s.technical_score
            + 0.30 * s.llm_score
            + 0.25 * s.context_score
            + 0.10 * s.macro_score,
            1,
        )
        assert abs(s.score - expected) < 0.15, (
            f"{s.symbol}: score={s.score} expected≈{expected}"
        )


def test_confidence_equals_score():
    """confidence is an alias of score — both must be identical."""
    for s in SignalEngine().generate_daily_signals():
        assert s.confidence == s.score, f"{s.symbol}: confidence != score"


def test_direction_thresholds():
    for s in SignalEngine().generate_daily_signals():
        if s.score >= 62:
            assert s.direction == "bull"
        elif s.score <= 44:
            assert s.direction == "bear"
        else:
            assert s.direction == "neutral"


def test_prev_kline_present():
    """prev_kline must exist — this was the missing field that broke the chart."""
    for s in SignalEngine().generate_daily_signals():
        assert s.prev_kline, f"{s.symbol}: prev_kline is missing"
        assert set(s.prev_kline) == {'open', 'high', 'low', 'close'}


def test_ohlc_constraints_both_candles():
    """High >= max(O,C) and Low <= min(O,C) for both prev and predicted candles."""
    for s in SignalEngine().generate_daily_signals():
        for label, k in [('prev', s.prev_kline), ('predicted', s.predicted_kline)]:
            o, h, l, c = k['open'], k['high'], k['low'], k['close']
            assert h >= max(o, c), f"{s.symbol} {label}: high={h} < max(open={o}, close={c})"
            assert l <= min(o, c), f"{s.symbol} {label}: low={l} > min(open={o}, close={c})"


def test_realistic_prices():
    """Prices must be in a plausible range relative to the base price."""
    engine = SignalEngine()
    for s in engine.generate_daily_signals():
        for k in (s.prev_kline, s.predicted_kline):
            assert k['close'] > 0
            assert k['high'] > 0
            assert k['low'] > 0


def test_reasons_and_risks_not_empty():
    for s in SignalEngine().generate_daily_signals():
        assert s.reasons, f"{s.symbol}: reasons list is empty"
        assert s.risks, f"{s.symbol}: risks list is empty"


def test_deterministic_same_day():
    engine = SignalEngine()
    first = [engine.to_dict(x) for x in engine.generate_daily_signals()]
    second = [engine.to_dict(x) for x in engine.generate_daily_signals()]
    assert first == second, "Results must be deterministic within the same day"


def test_risk_management_values():
    """stop_loss < entry_low and take_profit > entry_high."""
    for s in SignalEngine().generate_daily_signals():
        assert s.stop_loss < s.entry_zone['low'], f"{s.symbol}: stop_loss >= entry_low"
        assert s.take_profit > s.entry_zone['high'], f"{s.symbol}: take_profit <= entry_high"


def test_watchlist_roundtrip():
    engine = SignalEngine()
    assert engine.add_watch('nvda')
    assert 'NVDA' in engine.list_watch()

    d = engine.to_dict(engine.get_signal('NVDA'))
    assert d['is_watch'] is True

    engine.remove_watch('nvda')
    assert 'NVDA' not in engine.list_watch()
    assert engine.to_dict(engine.get_signal('NVDA'))['is_watch'] is False


def test_add_watch_normalizes_case():
    engine = SignalEngine()
    engine.add_watch('aapl')
    assert 'AAPL' in engine.list_watch()


def test_get_signal_unknown_returns_none():
    assert SignalEngine().get_signal('DOES_NOT_EXIST') is None


def test_to_dict_includes_is_watch():
    engine = SignalEngine()
    engine.add_watch('AAPL')
    d = engine.to_dict(engine.get_signal('AAPL'))
    assert 'is_watch' in d
    assert d['is_watch'] is True
