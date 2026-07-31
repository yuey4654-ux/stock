$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tracking = $PSScriptRoot
$reportRel = 'reports/港股预测命中复盘_2026-07-29.md'

$predPath = Join-Path $tracking 'hk_daily_predictions.csv'
$rows = @(Import-Csv -LiteralPath $predPath)
foreach ($row in $rows) {
    if ($row.'目标日期' -ne '2026-07-29' -or $row.'复盘结果' -ne '待复盘') { continue }
    switch ($row.'代码') {
        '00941.HK' {
            $row.'收盘价' = '84.10'
            $row.'涨跌幅' = '1.02%'
            $row.'是否触发' = '否'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '部分命中'
            $row.'复盘备注' = '开83.25、高84.15、低83.20、收84.10。尾盘站稳83.30且电讯防守方向正确，但全天未进入82.55-82.90计划回踩区；没有可执行买点，只记部分命中。数据日期：2026-07-29；来源：东方财富港股日线及1分钟行情。'
        }
        '00005.HK' {
            $row.'收盘价' = '164.70'
            $row.'涨跌幅' = '1.67%'
            $row.'是否触发' = '否'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '部分命中'
            $row.'复盘备注' = '开162.80、高164.70、低160.40、收164.70。盘中进入计划区后跌破160.80下沿，但未跌破160.00降级线，尾盘站回162.60；方向正确但承接区“不破”条件不完整，条件观察最多部分命中。数据日期：2026-07-29；来源：东方财富港股日线及1分钟行情。'
        }
        '00700.HK' {
            $row.'收盘价' = '466.40'
            $row.'涨跌幅' = '4.29%'
            $row.'是否触发' = '否'
            $row.'是否失效' = '否'
            $row.'复盘结果' = '部分命中'
            $row.'复盘备注' = '开453.00、高469.40、低450.00、收466.40。平台权重方向显著走强且尾盘站上448，但全天未进入441-444计划买点；方向正确、执行点缺失，按高开不追和买点规则只记部分命中。数据日期：2026-07-29；来源：东方财富港股日线及1分钟行情。'
        }
    }
}
$rows | Export-Csv -LiteralPath $predPath -NoTypeInformation -Encoding UTF8

function Upsert-HkSummary {
    param([string]$CsvName, [string]$MdName, [bool]$RuleOnly)
    $csvPath = Join-Path $tracking $CsvName
    $summary = @(Import-Csv -LiteralPath $csvPath | Where-Object { $_.'目标日期' -ne '2026-07-29' })
    $next = [ordered]@{
        '目标日期' = '2026-07-29'
        '预测日期' = '2026-07-28'
        '总数' = $(if ($RuleOnly) { '1' } else { '3' })
        '命中' = '0'
        '部分命中' = $(if ($RuleOnly) { '1' } else { '3' })
        '未命中' = '0'
        '严格命中率' = '0.0%'
        '调整后命中率' = '50.0%'
        '严格加权命中率' = '0.0%'
        '调整后加权命中率' = '50.0%'
        '核心承接命中' = '0'
        '核心承接总数' = '0'
        '稳健观察命中' = '0'
        '稳健观察总数' = '1'
        '弹性进攻命中' = '0'
        '弹性进攻总数' = '0'
        '其他类型命中' = '0'
        '其他类型总数' = $(if ($RuleOnly) { '0' } else { '2' })
        '最佳预测' = $(if ($RuleOnly) { '中国移动' } else { '中国移动; 汇丰控股; 腾讯控股' })
        '最差预测' = '无'
        '主要误差' = $(if ($RuleOnly) {
            '中国移动方向和尾盘确认正确，但最低83.20仍未进入82.55-82.90计划买点，连续出现方向正确而执行点缺失。'
        } else {
            '中国移动、腾讯控股未给计划买点；汇丰控股虽进入买点区并尾盘确认，但盘中跌破承接区下沿。三票方向正确，执行条件均不完整。'
        })
        $(if ($RuleOnly) { '规则调整信号' } else { '策略提醒' }) = '是'
        '下一步规则调整' = '触发原因：唯一正式规则票中国移动仅部分命中，规则票严格命中率0%、调整后加权命中率50%，低于60%/65%阈值。建议：下一交易日正式规则票维持0-1只，电讯与金融买点参考真实波动区，但不得取消尾盘确认；平台科技只作条件观察。适用范围：港股正式规则票及平台科技、金融防守候选。失效条件：连续两日规则票调整后加权命中率高于65%，且无买点缺失、承接区跌破或冲高回落样本。'
        '报告文件' = $reportRel
    }
    $summary += [pscustomobject]$next
    $summary = @($summary | Sort-Object { [datetime]$_.'目标日期' })
    $summary | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
    $headers = @($summary[0].PSObject.Properties.Name)
    $lines = @("# 港股每日预测复盘汇总", "", "| " + ($headers -join ' | ') + " |", "| " + (($headers | ForEach-Object { '---' }) -join ' | ') + " |")
    foreach ($item in $summary) {
        $vals = foreach ($header in $headers) { ([string]$item.$header).Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ') }
        $lines += "| " + ($vals -join ' | ') + " |"
    }
    Set-Content -LiteralPath (Join-Path $tracking $MdName) -Value $lines -Encoding UTF8
}

Upsert-HkSummary 'hk_rule_based_daily_summary.csv' 'hk_rule_based_daily_summary.md' $true

$report = @'
# 港股预测命中复盘（2026-07-29）

## 策略调整提醒

- **规则调整信号：是。** 唯一规则票中国移动仅部分命中；严格命中率 0.0%、调整后加权命中率 50.0%，低于 60%/65% 阈值。
- 建议：下一交易日正式规则票维持 0-1 只；电讯与金融的买点贴近真实波动区，但尾盘确认和失效位不放宽。连续两日规则票调整后加权命中率高于 65% 且无买点缺失后，提醒失效。

## 今日结论

- 全量：0 命中、3 部分命中、0 未命中；严格命中率 0.0%，调整后命中率 50.0%。
- 规则票：中国移动 1 只，仅部分命中；当日预测数 = 复盘数 = 3。

## 新闻政策与美股影响

- 隔夜纳指及费城半导体继续偏弱，港股平台科技虽出现强修复，但仍按高波动条件观察处理；不得用腾讯单日大涨替代回踩买点。
- 油价与美债收益率回落有利传统蓝筹估值稳定；电讯、金融仍具防守价值，但连续未给计划买点，规则票数量继续收紧。

## 逐票复盘

| 标的 | 收盘表现 | 结果 | 复盘 |
| --- | --- | --- | --- |
| 中国移动 | 84.10，+1.02% | 部分命中 | 低 83.20，未进 82.55-82.90 买点；尾盘确认正确但不可执行。 |
| 汇丰控股 | 164.70，+1.67% | 部分命中 | 进入计划区后跌破 160.80 下沿，尾盘虽站回 162.60，承接“不破”条件不完整。 |
| 腾讯控股 | 466.40，+4.29% | 部分命中 | 全日未回到 441-444 买点，方向强但执行点缺失。 |

## 明日规则调整

- 正式规则票 0-1 只；优先低波动、电讯或现金流稳定权重。
- 平台科技仅在回踩承接且尾盘确认时触发，高开或直线拉升不追。
- 连续“未到买点”说明区间需要参考近 3-5 日真实振幅重估，但不得事后放宽命中标准。

数据日期：2026-07-29；行情来源：东方财富公开港股日线及分钟接口。本文为规则复盘，不构成收益承诺。
'@
Set-Content -LiteralPath (Join-Path $root $reportRel) -Value $report -Encoding UTF8
Write-Output 'Updated 2026-07-29 HK review, summaries, and report.'
