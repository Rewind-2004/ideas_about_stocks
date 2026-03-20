# WorldMonitor 接入说明（用于 SIGNAL.AI）

## 目标

把 WorldMonitor 作为“全球事件信号源”之一，提取对股票（尤其行业链条）有影响的地缘与基础设施事件，转成可量化特征。

## 你应该知道的事实（基于公开仓库信息）

- WorldMonitor 是一个“实时全球情报仪表板”，覆盖新闻聚合、地缘风险、基础设施追踪等能力。
- 其公开仓库强调支持 Country Intelligence Index（CII）与金融雷达模块。
- 仓库许可证说明为 AGPL-3.0（并标注商业用途需商业许可），在你计划商用时需要单独审查许可条款。

> 建议：将 WorldMonitor 当作“可替换事件源”，不要硬编码耦合。

## 接入模式（按可行性从高到低）

### 模式 A：自建适配器读取其公开数据流（推荐）

1. 在你的系统中建立 `world_events_adapter` 服务。
2. 适配器做三件事：
   - 抓取（pull）或订阅（stream）事件数据
   - 标准化字段
   - 计算稳定性增量（如 `cii_delta_7d`）
3. 将输出写入 `events_raw` 与 `events_features` 两层表。

### 模式 B：Fork WorldMonitor 并在私有环境增加导出端点

- 适合技术团队可维护前后端的情况。
- 在 fork 中增加一个只暴露必要字段的 API（避免把 UI 与内部结构耦合到交易系统）。

### 模式 C：只用其站点作为人工监控补充

- 如果短期无法拿到稳定 machine-readable API，可以先用 GDELT/NewsAPI 构建主流程，
  WorldMonitor 用作事件验证与策略研究。

---

## 标准化事件结构（建议）

```json
{
  "event_id": "wm_xxx",
  "event_time": "2026-03-20T00:00:00Z",
  "country": "US",
  "region": "North America",
  "event_type": "sanction|conflict|infrastructure|energy|disaster|policy",
  "severity": 0.0,
  "cii_score": 64.2,
  "cii_delta_7d": -12.3,
  "summary": "...",
  "source_url": "...",
  "source": "worldmonitor"
}
```

---

## 事件到行业映射（示例）

- `energy/geopolitical` → 油气、航运、化工
- `semiconductor/sanction` → 芯片设计、设备、材料
- `shipping/chokepoint` → 港口、航运、保险
- `disaster/grid` → 电力设备、应急物资、工程基建

映射方式建议：
1) 专家规则表（先跑起来）
2) LLM 解释补充（给原因）
3) 历史收益反馈回写映射权重（长期）

---

## 与 A股/美股策略结合方式

1. 先做“冲击识别”：
   - `abs(cii_delta_7d) >= 15` 标为高冲击。
2. 再做“暴露度计算”：
   - 股票行业 × 供应链国家暴露表。
3. 进入评分：
   - 把 `cii_score / cii_delta_7d / focal_urgency` 作为事件特征输入 Layer 2。
4. 风险联动：
   - 当冲击阈值过高时，限制仓位上限或触发强制退出评估。

---

## 工程注意事项

- 事件源常有重复与噪音：必须做去重（标题 + 时间窗口 + 地理位置）。
- 时间戳统一为 UTC，落库时保存原时区字段。
- 新闻情绪不要直接交易：应与价格行为（量/波动/形态）联合确认。
- 任何外部数据中断都应可降级：缺少事件数据时，系统仍能跑纯技术+宏观流程。
