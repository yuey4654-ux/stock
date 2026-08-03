$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tracking = $PSScriptRoot
$date = '2026-08-03'
$predictionDate = '2026-07-31'
$reportRel = 'reports/预测命中复盘_2026-08-03.md'

function Write-MarkdownTable {
    param([object[]]$Rows, [string]$Path, [string]$Title)
    $headers = @($Rows[0].PSObject.Properties.Name)
    $lines = @("# $Title", "", "| " + ($headers -join ' | ') + " |", "| " + (($headers | ForEach-Object { '---' }) -join ' | ') + " |")
    foreach ($item in $Rows) {
        $vals = foreach ($header in $headers) {
            ([string]$item.$header).Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ')
        }
        $lines += "| " + ($vals -join ' | ') + " |"
    }
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

$predPath = Join-Path $tracking 'daily_predictions.csv'
$rows = @(Import-Csv -LiteralPath $predPath -Encoding UTF8)
foreach ($row in $rows) {
    if ($row.'目标日期' -ne $date -or $row.'复盘结果' -ne '待复盘') { continue }
    switch ($row.'代码') {
        '601398' {
            $row.'收盘价' = '7.96'
            $row.'涨跌幅' = '-0.38%'
            $row.'是否触发' = '否'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '未命中'
            $row.'复盘备注' = '开7.93、高8.01、低7.74、收7.96。盘中跌破7.82承接区下沿，且收盘未站回8.02确认位；低点仍高于7.72降级线与7.65深失效位，故未失效但承接修复未兑现，按规则记未命中。数据日期：2026-08-03；来源：东方财富日线行情。'
        }
        '600887' {
            $row.'收盘价' = '27.12'
            $row.'涨跌幅' = '0.07%'
            $row.'是否触发' = '否'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '部分命中'
            $row.'复盘备注' = '开27.25、高27.63、低26.98、收27.12。低点进入26.88-27.02承接区且未跌破26.68降级线，但收盘未站回27.32确认位；属于守住支撑但未完成尾盘转强，按规则记部分命中。数据日期：2026-08-03；来源：东方财富日线行情。'
        }
    }
}
$rows | Export-Csv -LiteralPath $predPath -NoTypeInformation -Encoding UTF8

function Upsert-Summary {
    param([string]$CsvName, [string]$MdName, [bool]$RuleOnly)
    $csvPath = Join-Path $tracking $CsvName
    $summary = @(Import-Csv -LiteralPath $csvPath -Encoding UTF8 | Where-Object { $_.'目标日期' -ne $date })
    $next = [ordered]@{
        '目标日期' = $date; '预测日期' = $predictionDate
        '总数' = $(if ($RuleOnly) { '0' } else { '2' })
        '命中' = '0'; '部分命中' = $(if ($RuleOnly) { '0' } else { '1' }); '未命中' = $(if ($RuleOnly) { '0' } else { '1' })
        '严格命中率' = '0.0%'; '调整后命中率' = $(if ($RuleOnly) { '0.0%' } else { '25.0%' })
        '严格加权命中率' = '0.0%'; '调整后加权命中率' = $(if ($RuleOnly) { '0.0%' } else { '25.0%' })
        '核心承接命中' = '0'; '核心承接总数' = '0'; '稳健观察命中' = '0'; '稳健观察总数' = '0'
        '弹性进攻命中' = '0'; '弹性进攻总数' = '0'; '其他类型命中' = '0'; '其他类型总数' = $(if ($RuleOnly) { '0' } else { '2' })
        '最佳预测' = $(if ($RuleOnly) { '无' } else { '伊利股份' })
        '最差预测' = $(if ($RuleOnly) { '无' } else { '工商银行' })
        '主要误差' = $(if ($RuleOnly) { '当日无正式规则票，零样本不参与策略阈值判断。' } else { '工商银行跌破承接区且未完成尾盘确认；伊利股份守住承接区但收盘未站回确认位。两只修复观察票均缺少完整可执行确认。' })
        $(if ($RuleOnly) { '规则调整信号' } else { '策略提醒' }) = '否'
        '下一步规则调整' = '当日无正式规则票，不新增统计型策略调整信号；延续7月31日收紧状态。建议：下一交易日正式规则票仍为0-1只，科技/半导体因科创50大跌及美股芯片持续分化仅作条件观察，银行与消费必须同时满足承接不破和尾盘确认。适用范围：A股正式规则票及银行、消费、科技条件观察票。失效条件：后续连续两次规则票调整后加权命中率高于65%，且无买点跌破、尾盘确认失败、深失效或冲高回落样本，方可恢复常规数量。'
        '报告文件' = $reportRel
    }
    $summary += [pscustomobject]$next
    $summary = @($summary | Sort-Object { [datetime]$_.'目标日期' })
    $summary | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
    Write-MarkdownTable -Rows $summary -Path (Join-Path $tracking $MdName) -Title $(if ($RuleOnly) { '规则票每日预测复盘汇总' } else { '每日预测复盘汇总' })
}

Upsert-Summary 'daily_review_summary.csv' 'daily_review_summary.md' $false
Upsert-Summary 'rule_based_daily_summary.csv' 'rule_based_daily_summary.md' $true

$report = @'
# 预测命中复盘（2026-08-03）

## 今日结论

- 全量2只：0命中、1部分命中、1未命中；严格命中率 **0.0%**，调整后及调整后加权命中率均为 **25.0%**。
- 正式规则票0只：零样本不参与60%/65%阈值判断，**不新增**策略调整信号；仍延续7月31日的收紧状态。
- 当日预测数=当日复盘数=2，待复盘归零。

## 新闻政策与美股影响

- 7月31日美股收官分化：道指约+0.5%、纳指约+1.0%，但AI投资回报与芯片估值争议仍大；10年期美债收益率约4.71%，布伦特原油约87.93美元。到8月3日美股早盘，油价回落推动道指显著反弹，但Micron、AMD等芯片股继续承压，说明“指数修复、半导体偏弱”的分化尚未结束。
- 国内政策继续支持先进制造、科技创新、人工智能与产业链韧性；证监会近期同时提示地缘冲突和全球市场联动风险。政策仅提高科技制造方向的观察优先级，不替代承接区、确认位和高开不追。
- A股8月3日：上证 **-0.59%**、深成指 **-0.96%**、创业板 **-1.24%**、科创50 **-5.08%**；两市成交约 **2.00万亿元**。科技与半导体明显承压，银行、消费虽相对抗跌，但两只观察票仍未形成完整尾盘确认。
- 对下一交易日的影响：科技/半导体降仓降数量，仅保留回踩后收盘确认的条件票；银行、消费不能因相对抗跌直接升级。正式规则票维持0-1只，触发和失效条件不放宽。

## 逐票复盘

| 标的 | 日内行情 | 触发/失效 | 结果 | 复盘 |
| --- | --- | --- | --- | --- |
| 工商银行（601398） | 开7.93 / 高8.01 / 低7.74 / 收7.96，-0.38% | 否 / 否 | 未命中 | 跌破7.82承接区下沿，收盘未站回8.02；虽未跌破7.72降级线，但修复条件未兑现。 |
| 伊利股份（600887） | 开27.25 / 高27.63 / 低26.98 / 收27.12，+0.07% | 否 / 否 | 部分命中 | 进入并守住26.88-27.02承接区，但收盘未站回27.32；守支撑而未转强。 |

## 主要误差

1. 工商银行的银行修复假设仍偏早，承接区安全垫不足，盘中跌破后尾盘也未确认。
2. 伊利股份方向和支撑判断尚可，但把“守住承接”误当作接近触发；没有收盘站回确认位，执行仍不完整。
3. 市场最重要的风险是科创50单日大跌5.08%；即使指数或消息面存在局部利好，也不能放宽科技票买点。

## 明日规则调整建议

- 不新增统计型收紧，但延续既有防守状态：正式规则票0-1只、条件观察最多2只。
- 科技/半导体只有在板块止跌、个股回踩不破且14:30后站回确认位时才可升级；高开超过3%不追。
- 银行与消费需证明相对强度和尾盘承接同时恢复，单纯抗跌最多保留观察。
- 若后续连续两次正式规则票调整后加权命中率高于65%，且无破位或冲高回落样本，再恢复常规票数。

数据日期：2026-08-03。个股与A股指数行情来自东方财富公开日线接口；海外市场参考 [AP 7月31日美股收盘](https://apnews.com/article/e31b3a442bcb957a53f1823ef21e73e8) 与 [AP 8月3日盘中市场报道](https://apnews.com/article/d19a8f9a77b6fceca41da3e4b6bf17aa)；国内政策背景参考 [新华社工信部上半年发布会](https://www.news.cn/info/20260720/3f1a4b956f5941cc919139c8a17c1254/c.html) 与 [新华社证监会监管工作座谈会](https://www.news.cn/20260724/601338d3e6394b4e95aae58c985dad9a/c.html)。本文为规则复盘，不构成收益承诺。
'@
Set-Content -LiteralPath (Join-Path $root $reportRel) -Value $report -Encoding UTF8

Write-Output 'Updated 2026-08-03 A-share review, both summaries, and report.'
