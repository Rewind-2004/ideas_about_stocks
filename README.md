# SIGNAL.AI（A股 + 美股）

> 事件驱动 + 量价因子 + LLM 解释的**日频选股与盘中提示**系统。
> 目标不是高频自动交易，而是每天给出“最值得关注的多/空标的 + 原因 + 风险 + 价格区间”。


## 快速开始（现在可运行）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问：
- Web 面板：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`

当前已实现 MVP 页面能力：
- 展示 A股/美股每日预测列表（看涨/看跌/中性）
- 点击查看评分拆解、理由、风险、建议区间、预测 K 线
- 支持加入自选股并高亮显示


## 1. 产品定位

SIGNAL.AI 面向“希望做有依据的日内/隔夜决策”的投资者：

- **每日结算预测**：每天开盘前产出候选看涨/看跌清单（A股与美股分开建模）。
- **盘中提醒**：只做“提示”，不自动下单；当价格回调至设定观察区间并出现动量转强时提醒。
- **可解释优先**：每条建议都输出“为什么看涨/看跌、风险是什么、信号来源是什么”。
- **可复盘与可进化**：收盘自动复盘，更新各模式胜率与权重。

---

## 2. 非功能性原则（像量化基金一样做工程）

- **可靠性**：任何 AI 服务不可用时，规则引擎仍能提供基础结果（降级策略）。
- **可追溯**：每个预测保存快照（输入特征、模型版本、提示词版本、输出）。
- **防泄露**：训练/验证采用 Purged Walk-Forward + Embargo。
- **跨市场隔离**：A股与美股的交易规则、开盘时间、涨跌停机制必须分离。
- **风险先于收益**：先定义“不能做什么”，再定义“做什么”。

---

## 3. 总体架构

```text
[Layer 0] Data Ingestion
  A股行情(akshare/tushare) + 美股行情(yfinance/alpaca)
  + 宏观(FRED/中国宏观) + 新闻(NewsAPI/GDELT) + 事件(WorldMonitor)
  -> TimescaleDB / QuestDB

[Layer 1] Signal Discovery
  6种模式检测 + 基本面/流动性过滤 -> 每日候选池(30~80)

[Layer 2] Feature Engineering
  技术18 + 宏观8 + 事件10 + 历史上下文6 = 42特征

[Layer 3] Scoring & Ranking
  规则引擎(毫秒级) -> LLM异步解释 -> 综合评分排序
  (Phase 2) Pairwise Ranking

[Layer 4] Risk Engine
  ATR止损止盈 + 仓位建议 + 相关性去拥挤 + 强制退出条件

[Layer 5] Delivery
  Web Dashboard + 自选股监控 + Telegram/企业微信提醒 + 收盘复盘
```

---

## 4. 技术栈建议

- **后端**：FastAPI + Pydantic + SQLAlchemy + Celery + Redis
- **数据层**：TimescaleDB（主） + Redis（缓存） + S3/MinIO（归档）
- **计算层**：Pandas/Polars + pandas-ta + scikit-learn + lightgbm
- **NLP**：FinBERT（本地）+ LLM（结构化 JSON 输出）
- **前端**：React + TypeScript + ECharts/Recharts
- **监控**：Prometheus + Grafana + Sentry

---

## 5. 关键数据模型（最小可用）

### 5.1 表设计（建议）

1) `prices_daily`
- `symbol, market, trade_date, open, high, low, close, volume, amount`

2) `signals_daily`
- `trade_date, symbol, market, pattern, direction, raw_score, trigger_payload(jsonb)`

3) `features_daily`
- `trade_date, symbol, market, feature_vector(jsonb), regime`

4) `predictions_daily`
- `trade_date, symbol, market, direction, confidence, score, reason_json, risk_json`

5) `orders_suggestion`
- `trade_date, symbol, entry_zone_low/high, stop_loss, take_profit, position_pct`

6) `postmortem_daily`
- `trade_date, symbol, predicted_direction, realized_return_1d, hit_flag, error_type`

---

## 6. API 草案（FastAPI）

- `GET /api/v1/predictions?market=CN&date=YYYY-MM-DD`
- `GET /api/v1/predictions/{symbol}`
- `POST /api/v1/watchlist`（添加自选）
- `GET /api/v1/watchlist/signals`
- `GET /api/v1/reports/daily-review?date=YYYY-MM-DD`
- `POST /api/v1/admin/recompute?date=YYYY-MM-DD`（补算/重跑）

---

## 7. 每日运行时序（UTC）

- **00:30 UTC**：A股开盘前预计算（对应北京时间早盘前）
- **13:00 UTC**：美股开盘前预计算（对应美东早盘前，按夏令时动态调整）
- **盘中每1分钟**：只轮询候选池与自选池，不做全市场分钟级扫描
- **收盘后**：自动复盘 + 更新模式胜率 + 生成日报

---

## 8. WorldMonitor 接入策略（强烈建议“数据代理层”）

不要把业务直接绑定到单一外部站点。建议使用 `world_events_adapter`：

- Adapter 输入：WorldMonitor/GDELT/自建事件流
- Adapter 输出统一格式：
  - `event_time, region, country, event_type, severity, cii_score, cii_delta_7d, source, url`
- 好处：
  - 更换来源不影响主模型
  - 可做去重、重采样、置信度加权

> 备注：若外部服务接口变化，模型层无需改，只需更新 adapter。

---

## 9. 评分与风控（建议初始参数）

### 9.1 综合评分

`score = 0.35 * technical + 0.30 * llm + 0.25 * context + 0.10 * macro`

### 9.2 风险规则

- 止损：`entry - 1.5 * ATR(14)`
- 止盈：`entry + 2.5 * ATR(14)`
- 单票上限 15%，单行业上限 30%
- 相关性拥挤：同主题高相关只保留 1~2 只

---

## 10. 开发节奏（8周 MVP）

- **W1-W2**：行情/新闻/事件接入 + 落库 + 质量检查
- **W3-W4**：6模式检测 + 42特征计算 + 规则引擎
- **W5-W6**：Dashboard 首版 + 自选股 + 盘中提醒
- **W7**：收盘复盘与胜率追踪
- **W8**：小规模回测 + 参数校准 + 风险审计

---

## 11. 回测与评估指标

- 方向准确率（Hit Ratio）
- Top-N 组合收益 / 基准超额收益
- 最大回撤（MDD）
- 信息比率（IR）
- 置信度校准（Reliability curve）
- 分市场、分行业、分 regime 的分层表现

---

## 12. 合规与免责声明

本项目用于研究与决策辅助，不构成任何投资建议。实盘前请进行独立风控评估，并遵守所在司法辖区证券与数据合规要求。
