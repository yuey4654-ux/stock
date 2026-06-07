# 股票分析项目说明

本项目用于股票、指数、行业、宏观、财报和期权相关分析。

## 默认工作方式

- 优先使用本项目内的 AlphaGBM skills：`.codex/skills/alphagbm-*`。
- 当用户请求个股、组合、行业、主题或市场情绪分析时，先判断最匹配的 skill，并读取对应的 `SKILL.md`。
- 常用映射：
  - 个股综合分析：`.codex/skills/alphagbm-stock-analysis/SKILL.md`
  - 公司画像与研究档案：`.codex/skills/alphagbm-company-profile/SKILL.md`
  - 投资逻辑与退出条件：`.codex/skills/alphagbm-investment-thesis/SKILL.md`
  - 多股票对比：`.codex/skills/alphagbm-compare/SKILL.md`
  - 市场情绪与宏观：`.codex/skills/alphagbm-market-sentiment/SKILL.md`、`.codex/skills/alphagbm-macro-view/SKILL.md`
  - 巴菲特/段永平/霍华德马克斯风格分析：对应 `alphagbm-buffett-analysis`、`alphagbm-duan-analysis`、`alphagbm-marks-cycle`
  - 期权、波动率、希腊值、对冲：对应 `alphagbm-options-*`、`alphagbm-iv-rank`、`alphagbm-greeks`、`alphagbm-vol-*`、`alphagbm-hedge-advisor`
  - 观察列表、提醒、止盈：对应 `alphagbm-watchlist`、`alphagbm-alert`、`alphagbm-take-profit`
- 对 A 股、港股和财务数据，优先使用已配置的 `tushareMcp` 获取结构化数据；若需要最新市场新闻、公告、行情或机构观点，先联网核实。
- 输出结论时区分事实、推断和情景判断；涉及买卖建议时说明风险，不把分析写成确定性投资承诺。
- 对近期行情、股价、财报、政策、利率、汇率、新闻和公司事件，必须核对最新日期和来源。

## 项目约定

- 用户偏好中文分析，默认用简洁中文回答。
- 重点关注：趋势、估值、业绩变化、资金情绪、风险点、催化剂、支撑/压力区间和可执行观察信号。
- 生成的数据、图表、报告或临时材料放在项目目录下，避免污染全局 Codex 配置。
