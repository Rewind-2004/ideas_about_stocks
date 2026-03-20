# SIGNAL.AI 系统蓝图（可直接开工）

## 1) 推荐目录结构

```text
signal-ai/
  backend/
    app/
      api/
      core/
      services/
      models/
      schemas/
      tasks/
      strategy/
    tests/
  frontend/
    src/
      pages/
      components/
      hooks/
      services/
  infra/
    docker/
    sql/
    monitoring/
  docs/
```

## 2) 核心服务拆分

- `market-ingestor`：A股/美股行情与交易日历采集
- `event-ingestor`：WorldMonitor/GDELT/NewsAPI 事件采集
- `feature-engine`：42特征计算
- `signal-engine`：6种模式触发
- `scoring-engine`：规则 + LLM + 排序
- `risk-engine`：仓位、止损止盈、组合相关性
- `notifier`：Telegram/企业微信推送
- `review-engine`：收盘复盘与指标统计

## 3) Celery 队列规划

- `q_ingest_cn`
- `q_ingest_us`
- `q_events`
- `q_features`
- `q_scoring`
- `q_notify`
- `q_review`

每个任务要实现：幂等、重试、超时、死信。

## 4) MVP 的最小策略闭环

1. 每日开盘前生成候选池（规则触发）
2. 计算特征并评分，输出 TopN 看涨 + TopN 看跌
3. 盘中监控回踩与动量转强信号，推送提示
4. 收盘后复盘命中率，更新 pattern 胜率

## 5) “为什么会失败”与预防

- **失败点1：信号太多，噪音高**
  - 预防：先做候选池，再做评分，不对全市场逐分钟预测。
- **失败点2：仅凭新闻情绪交易**
  - 预防：情绪必须与价格行为共同确认。
- **失败点3：回测与实盘偏差大**
  - 预防：加滑点/冲击成本、限制低流动性标的。
- **失败点4：LLM 幻觉影响决策**
  - 预防：LLM 只做解释与二级打分，不做唯一交易信号。

## 6) 关键 KPI（产品 + 策略 + 工程）

- 产品：DAU、留存、自选股使用率、分析展开率
- 策略：TopN 超额收益、Hit Ratio、MDD、IR、校准误差
- 工程：任务成功率、延迟、数据新鲜度、API 错误率
