$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tracking = $PSScriptRoot
$reportRel = 'reports/预测命中复盘_2026-07-30.md'

$predPath = Join-Path $tracking 'daily_predictions.csv'
$rows = @(Import-Csv -LiteralPath $predPath -Encoding UTF8)
foreach ($row in $rows) {
    if ($row.'目标日期' -ne '2026-07-30' -or $row.'复盘结果' -ne '待复盘') { continue }
    switch ($row.'代码') {
        '601939' {
            $row.'收盘价' = '10.97'
            $row.'涨跌幅' = '3.20%'
            $row.'是否触发' = '是'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '命中'
            $row.'复盘备注' = '开10.61、高10.98、低10.55、收10.97。低点进入10.50-10.58计划回踩区，14:30后持续站上10.64确认位，且未触发10.40降级线；买点、尾盘确认与未失效三项完整，按规则记命中。数据日期：2026-07-30；来源：东方财富日线及5分钟行情。'
        }
        '600887' {
            $row.'收盘价' = '27.69'
            $row.'涨跌幅' = '1.39%'
            $row.'是否触发' = '否'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '部分命中'
            $row.'复盘备注' = '开27.19、高27.70、低27.11、收27.69。全天低点高于26.85-27.05计划区上沿0.06元，未形成可执行买点；尾盘站上27.28且方向正确、未失效，但新闻与板块强度不能替代买点，按规则只记部分命中。数据日期：2026-07-30；来源：东方财富日线及5分钟行情。'
        }
        '601398' {
            $row.'收盘价' = '8.15'
            $row.'涨跌幅' = '2.52%'
            $row.'是否触发' = '是'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '命中'
            $row.'复盘备注' = '开7.94、高8.16、低7.91、收8.15。低点进入7.86-7.92计划回踩区，14:30后持续站上7.97确认位，且未触发7.78降级线；银行扩散和个股承接均兑现，按规则记命中。数据日期：2026-07-30；来源：东方财富日线及5分钟行情。'
        }
    }
}
$rows | Export-Csv -LiteralPath $predPath -NoTypeInformation -Encoding UTF8

function Upsert-Summary {
    param([string]$CsvName, [string]$MdName, [bool]$RuleOnly)
    $csvPath = Join-Path $tracking $CsvName
    $summary = @(Import-Csv -LiteralPath $csvPath -Encoding UTF8 | Where-Object { $_.'目标日期' -ne '2026-07-30' })
    $next = [ordered]@{
        '目标日期' = '2026-07-30'
        '预测日期' = '2026-07-29'
        '总数' = $(if ($RuleOnly) { '1' } else { '3' })
        '命中' = $(if ($RuleOnly) { '1' } else { '2' })
        '部分命中' = $(if ($RuleOnly) { '0' } else { '1' })
        '未命中' = '0'
        '严格命中率' = $(if ($RuleOnly) { '100.0%' } else { '66.7%' })
        '调整后命中率' = $(if ($RuleOnly) { '100.0%' } else { '83.3%' })
        '严格加权命中率' = $(if ($RuleOnly) { '100.0%' } else { '66.7%' })
        '调整后加权命中率' = $(if ($RuleOnly) { '100.0%' } else { '83.3%' })
        '核心承接命中' = '0'
        '核心承接总数' = '0'
        '稳健观察命中' = '1'
        '稳健观察总数' = '1'
        '弹性进攻命中' = '0'
        '弹性进攻总数' = '0'
        '其他类型命中' = $(if ($RuleOnly) { '0' } else { '1' })
        '其他类型总数' = $(if ($RuleOnly) { '0' } else { '2' })
        '最佳预测' = $(if ($RuleOnly) { '建设银行' } else { '建设银行; 工商银行' })
        '最差预测' = $(if ($RuleOnly) { '无' } else { '伊利股份' })
        '主要误差' = $(if ($RuleOnly) {
            '建设银行完整进入计划回踩区并完成尾盘确认，正式规则票无执行误差。'
        } else {
            '伊利股份方向与尾盘强度正确，但最低27.11仍高于26.85-27.05计划买点，连续走强环境下没有给出可执行回踩。'
        })
        $(if ($RuleOnly) { '规则调整信号' } else { '策略提醒' }) = '否'
        '下一步规则调整' = '本日唯一正式规则票建设银行完整命中，规则票严格及调整后加权命中率均为100%，不新增调整信号。建议：隔夜美股与A股科技主线同步转弱，下一交易日正式规则票仍限制为0-1只，优先银行、电讯等低波动承接；连续上涨但未回踩的消费票只作条件观察。适用范围：A股正式规则票及防守型观察票。失效条件：若科技主线重新站回关键承接且规则票连续两日调整后加权命中率高于65%，可恢复常规数量；若规则票再次低于60%/65%阈值则重新触发收紧。'
        '报告文件' = $reportRel
    }
    $summary += [pscustomobject]$next
    $summary = @($summary | Sort-Object { [datetime]$_.'目标日期' })
    $summary | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
    $headers = @($summary[0].PSObject.Properties.Name)
    $lines = @("# 每日预测复盘汇总", "", "| " + ($headers -join ' | ') + " |", "| " + (($headers | ForEach-Object { '---' }) -join ' | ') + " |")
    foreach ($item in $summary) {
        $vals = foreach ($header in $headers) { ([string]$item.$header).Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ') }
        $lines += "| " + ($vals -join ' | ') + " |"
    }
    Set-Content -LiteralPath (Join-Path $tracking $MdName) -Value $lines -Encoding UTF8
}

Upsert-Summary -CsvName 'daily_review_summary.csv' -MdName 'daily_review_summary.md' -RuleOnly $false
Upsert-Summary -CsvName 'rule_based_daily_summary.csv' -MdName 'rule_based_daily_summary.md' -RuleOnly $true

$report = @'
# 预测命中复盘（2026-07-30）

## 今日结论

- 全量：2 命中、1 部分命中、0 未命中；严格命中率 **66.7%**，调整后命中率 **83.3%**。
- 规则票：建设银行 1/1 命中；严格及调整后加权命中率均为 **100.0%**，本日不新增策略调整提醒。
- 当日 A 股预测数 = 当日复盘数 = **3**，无待复盘记录。

## 新闻政策与美股影响

- 隔夜美股风险偏好显著降温：标普 500 跌 1.5%、道指跌 2.2%、纳指跌 1.7%；AI 芯片继续拖累科技，油价跳升并放大通胀与利率不确定性。
- 国内盘面同步分化：上证指数跌 0.62%，深证成指跌 2.73%，创业板指跌 3.97%，科创 50 跌 5.38%；沪深成交约 2.34 万亿元。高波动科技与半导体承压，银行等低波动权重相对占优。
- 财联社快讯、国内政策和产业新闻仅用于热点排序；今日实际验证仍以回踩买点、14:30 后确认、失效位和高开不追为准。
- 映射方向：银行、电讯、现金流稳定的防守方向优先；半导体、AI 硬件继续降级。下一交易日正式规则票继续限制为 0-1 只，科技主线未重回关键承接前不扩张。

## 逐票复盘

| 标的 | 类型 | 收盘表现 | 触发/失效 | 结果 | 复盘 |
| --- | --- | --- | --- | --- | --- |
| 建设银行（601939） | 稳健观察·规则票 | 10.97，+3.20% | 是 / 否 | 命中 | 低 10.55 进入 10.50-10.58 买点，14:30 后站稳 10.64，三项条件完整。 |
| 伊利股份（600887） | 非规则条件观察 | 27.69，+1.39% | 否 / 否 | 部分命中 | 低 27.11，较计划区上沿高 0.06 元；方向和尾盘强度正确，但没有可执行买点。 |
| 工商银行（601398） | 非规则条件观察 | 8.15，+2.52% | 是 / 否 | 命中 | 低 7.91 进入 7.86-7.92 买点，14:30 后站稳 7.97，银行扩散兑现。 |

## 主要误差

1. 伊利股份连续走强后没有回到计划买点；误差在执行区间而非方向。
2. 银行防守逻辑兑现，但单日上涨后次日追高风险上升，不能机械外推。
3. 科技与半导体的系统性弱势强化了防守票相对收益，仍不能替代逐票承接确认。

## 明日规则调整建议

- 正式规则票维持 0-1 只，优先低波动、可回踩、尾盘可确认的防守标的。
- 建设银行、工商银行次日若高开超过 3%不追；只有回踩承接区后再站回确认位才可触发。
- 消费票若继续不给回踩，只保留方向观察，不因收盘上涨改判可执行。
- 半导体、AI 芯片须同时满足海外科技止跌与 A 股主线重回关键承接，方可恢复正式规则席位。

数据日期：2026-07-30。个股与指数行情来自东方财富公开行情接口；隔夜美股数据参考 AP 收盘报道。本文为规则复盘，不构成收益承诺。
'@
Set-Content -LiteralPath (Join-Path $root $reportRel) -Value $report -Encoding UTF8

Write-Output 'Updated 2026-07-30 A-share review, summaries, and report.'
