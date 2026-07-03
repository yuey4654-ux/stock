# TradingAgents-CN 融合方案_2026-07-03

## 结论

TradingAgents-CN 适合做“外部多 Agent 研究引擎”，不适合直接替代当前 AlphaGBM 策略。当前策略刚进入连续失准防守模式，最重要的是减少错误出票；TradingAgents-CN 的多 Agent 结论只能作为证据层，不能绕过买点、承接区、失效位和收盘确认。

## 推荐架构

采用旁路集成：

1. AlphaGBM 先生成候选池和市场状态判断。
2. TradingAgents-CN 对候选票逐只输出多 Agent 研究报告。
3. 解析 TradingAgents-CN 的 market/news/fundamentals/risk/final decision 字段。
4. 映射为 agent_score、agent_bias、agent_key_risk、agent_conflict。
5. AlphaGBM 最终规则决定是否进入正式预测票。

不要采用直接替换：

- 不直接用 TradingAgents-CN 的 final_trade_decision 作为买卖建议。
- 不让 Agent 结论改写失效位。
- 不因为 Agent 看多而增加规则票数量。
- 不因为长期基本面好而忽略次日承接失败。

## 字段映射

TradingAgents-CN 的 `TradingAgentsGraph.propagate()` 返回 `final_state, decision`。优先读取：

| TradingAgents 字段 | 融合到本策略 |
| --- | --- |
| market_report | 技术趋势、支撑压力、是否与触发区一致 |
| news_report | 热点来源、政策/产业催化、是否有外盘映射 |
| fundamentals_report | 财务质量、估值硬伤、长期风险 |
| sentiment_report | 情绪热度，只做低权重参考 |
| investment_debate_state | 多空分歧点，写入复盘备注 |
| risk_debate_state | 风险否决项，决定是否降级观察 |
| final_trade_decision | 只作为 agent_bias，不直接采用 |

## 融合评分

外部 Agent 证据最高 20 分：

| 项目 | 分值 |
| --- | ---: |
| market_report 与本策略趋势一致 | 0-5 |
| news_report 与政策/产业催化一致且盘面扩散 | 0-5 |
| fundamentals_report 无明显财务/估值硬伤 | 0-3 |
| risk_debate_state 无重大否决风险 | 0-5 |
| 多空辩论中风险可被失效位覆盖 | 0-2 |

解释：

- agent_score >= 15：可作为候选票加分，但仍需通过买点。
- agent_score 8-14：中性参考，不改变规则票数量。
- agent_score < 8：降级观察或剔除。
- agent_conflict = 是：只要与失效位、市场状态闸门冲突，直接否决。

## 否决条件

以下任一条件出现，TradingAgents-CN 看多也不采用：

1. 当前市场状态闸门要求不出票。
2. 股票没有清晰回踩承接区。
3. 触发位距离支撑过远，风险收益比不足 1.5:1。
4. 前一日或盘中跌破失效位/降级线。
5. 所属板块没有扩散，只有个股消息刺激。
6. Agent 报告没有引用最新行情或最新财报期。
7. Agent 看多理由主要是长期基本面，但本策略目标是次日短线承接。

## 接入方式

### 方式一：旁路 CLI

把 TradingAgents-CN 克隆到项目外部目录，例如：

```powershell
cd C:\Users\Administrator\Documents
git clone https://github.com/hsliuping/TradingAgents-CN.git
cd TradingAgents-CN
python -m venv .venv
.\.venv\Scripts\pip install -e .
```

然后配置模型 Key，例如 OpenAI、DashScope、DeepSeek 或 AiHubMix。该项目依赖较多，建议独立虚拟环境，不要安装进当前 `股票分析` 项目的环境。

### 方式二：JSON 桥接

在 TradingAgents-CN 目录下运行分析，输出 JSON 到本项目：

```text
reports/tradingagents_raw/YYYY-MM-DD/代码.json
```

本项目只读取 JSON，不 import 它的全部依赖。

推荐 JSON 结构：

```json
{
  "symbol": "300014",
  "trade_date": "2026-07-03",
  "agent_bias": "中性",
  "agent_score": 11,
  "agent_key_risk": "板块扩散不足，触发位未确认",
  "agent_conflict": true,
  "use_decision": "降权",
  "source_fields": {
    "market_report": "...",
    "news_report": "...",
    "fundamentals_report": "...",
    "risk_debate_state": "..."
  }
}
```

### 方式三：后续脚本入口

后续可以新增一个本项目脚本：

```text
tools/import_tradingagents_signal.py
```

职责：

1. 读取 `reports/tradingagents_raw/日期/*.json`。
2. 映射 agent_score 和 agent_conflict。
3. 生成 `prediction_tracking/tradingagents_signals.csv`。
4. 在生成下一交易日预测票时，把 agent_score 作为外部证据分。

## 与当前防守模式的关系

当前是连续失准防守模式，所以融合后也必须遵守：

- 规则票最多 1-2 只。
- 核心承接和弹性进攻暂停作为正式票。
- TradingAgents-CN 只能帮助筛掉风险，不能帮助增加票数。
- 如果外部 Agent 与本策略冲突，优先相信本策略的失效位和市场状态闸门。

## 最小可行落地

第一阶段只做三件事：

1. 对每天候选池前 5-10 只跑 TradingAgents-CN。
2. 只提取 agent_bias、agent_score、agent_key_risk、agent_conflict 四个字段。
3. 在预测报告中新增“外部 Agent 证据”小节，不先改 CSV 主表结构。

等连续 10 个交易日复盘后，再统计：

- agent_score >= 15 的票是否提高命中率。
- agent_conflict = 是 的票是否更容易未命中。
- Agent 风险提示是否提前覆盖跌破失效位样本。

只有验证有效，才把它纳入正式打分。
