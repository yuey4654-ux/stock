$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tracking = $PSScriptRoot
$date = '2026-08-04'
$predictionDate = '2026-08-03'
$reportRel = 'reports/预测命中复盘_2026-08-04.md'

function Write-MarkdownTable {
    param([object[]]$Rows, [string]$Path, [string]$Title)
    $headers = @($Rows[0].PSObject.Properties.Name)
    $lines = @("# $Title", "", "| " + ($headers -join ' | ') + " |", "| " + (($headers | ForEach-Object { '---' }) -join ' | ') + " |")
    foreach ($item in $Rows) {
        $vals = foreach ($header in $headers) { ([string]$item.$header).Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ') }
        $lines += "| " + ($vals -join ' | ') + " |"
    }
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

$predPath = Join-Path $tracking 'daily_predictions.csv'
$rows = @(Import-Csv -LiteralPath $predPath -Encoding UTF8)
foreach ($row in $rows) {
    if ($row.'目标日期' -ne $date -or $row.'复盘结果' -ne '待复盘') { continue }
    switch ($row.'代码') {
        '600036' {
            $row.'收盘价' = '39.28'; $row.'涨跌幅' = '-2.68%'; $row.'是否触发' = '否'; $row.'是否失效' = '否'; $row.'复盘结果' = '未命中'
            $row.'复盘备注' = '开40.16、高40.16、低39.21、收39.28。早盘进入39.85-40.10计划区后继续跌破39.55降级线，14:30后维持39.28-39.40，未站回40.35确认位；最低39.21尚未严格跌破39.20深失效位，故记未命中但不记深失效。数据日期：2026-08-04；来源：东方财富日线及5分钟行情。'
        }
        '002202' {
            $row.'收盘价' = '19.49'; $row.'涨跌幅' = '1.30%'; $row.'是否触发' = '是'; $row.'是否失效' = '否'; $row.'复盘结果' = '命中'
            $row.'复盘备注' = '开19.40、高19.58、低18.94、收19.49。低点进入18.70-18.95计划承接区且未跌破18.45降级线；14:30后维持19.39-19.50并收于19.15确认位上方，且开盘涨幅未超过3%，触发、尾盘确认与未失效三项完整，按规则记命中。数据日期：2026-08-04；来源：东方财富日线及5分钟行情。'
        }
    }
}
$rows | Export-Csv -LiteralPath $predPath -NoTypeInformation -Encoding UTF8

function Upsert-Summary {
    param([string]$CsvName, [string]$MdName, [bool]$RuleOnly)
    $csvPath = Join-Path $tracking $CsvName
    $summary = @(Import-Csv -LiteralPath $csvPath -Encoding UTF8 | Where-Object { $_.'目标日期' -ne $date })
    $next = [ordered]@{
        '目标日期'=$date; '预测日期'=$predictionDate; '总数'=$(if($RuleOnly){'0'}else{'2'}); '命中'=$(if($RuleOnly){'0'}else{'1'}); '部分命中'='0'; '未命中'=$(if($RuleOnly){'0'}else{'1'})
        '严格命中率'=$(if($RuleOnly){'0.0%'}else{'50.0%'}); '调整后命中率'=$(if($RuleOnly){'0.0%'}else{'50.0%'}); '严格加权命中率'=$(if($RuleOnly){'0.0%'}else{'50.0%'}); '调整后加权命中率'=$(if($RuleOnly){'0.0%'}else{'50.0%'})
        '核心承接命中'='0'; '核心承接总数'='0'; '稳健观察命中'='0'; '稳健观察总数'='0'; '弹性进攻命中'='0'; '弹性进攻总数'='0'; '其他类型命中'=$(if($RuleOnly){'0'}else{'1'}); '其他类型总数'=$(if($RuleOnly){'0'}else{'2'})
        '最佳预测'=$(if($RuleOnly){'无'}else{'金风科技'}); '最差预测'=$(if($RuleOnly){'无'}else{'招商银行'})
        '主要误差'=$(if($RuleOnly){'当日无正式规则票，零样本不参与策略阈值判断。'}else{'招商银行进入买点后跌破降级线且尾盘未确认，银行相对强势未形成可执行承接；金风科技完整兑现回踩与尾盘确认。'})
        $(if($RuleOnly){'规则调整信号'}else{'策略提醒'})='否'
        '下一步规则调整'='当日无正式规则票，不新增统计型策略调整信号；延续7月31日收紧状态。建议：正式规则票继续维持0-1只，银行票跌破降级线后不得因防守属性放宽；风电虽命中但连续上涨后只接受回踩确认，不追加速。适用范围：A股正式规则票及银行、风电条件观察票。失效条件：后续连续两次正式规则票调整后加权命中率高于65%，且无买点跌破、尾盘确认失败、深失效或冲高回落样本，方可恢复常规数量。'
        '报告文件'=$reportRel
    }
    $summary += [pscustomobject]$next
    $summary = @($summary | Sort-Object { [datetime]$_.'目标日期' })
    $summary | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
    Write-MarkdownTable -Rows $summary -Path (Join-Path $tracking $MdName) -Title $(if($RuleOnly){'规则票每日预测复盘汇总'}else{'每日预测复盘汇总'})
}
Upsert-Summary 'daily_review_summary.csv' 'daily_review_summary.md' $false
Upsert-Summary 'rule_based_daily_summary.csv' 'rule_based_daily_summary.md' $true

$report = @'
# 预测命中复盘（2026-08-04）

## 今日结论

- 全量2只：1命中、0部分命中、1未命中；严格、调整后及加权命中率均为 **50.0%**。
- 正式规则票0只：零样本不参与60%/65%阈值判断，**不新增策略调整提醒**；继续执行既有收紧状态。
- 当日预测数=当日复盘数=2，A股待复盘归零。

## 新闻政策与美股影响

- 隔夜美股风险偏好修复：8月3日道指上涨约1.3%并创收盘新高，纳指上涨约2.1%；油价回落、长端美债收益率下降缓和通胀压力。指数修复对A股科技情绪偏利好，但不能替代个股买点与尾盘确认。
- 国内产业政策继续支持先进制造、风电电力装备、人工智能与科技创新，同时监管端继续强调全球市场联动与地缘风险。政策只提高候选方向优先级，不放宽高开不追、承接区和失效位。
- A股8月4日：上证 +0.33%、深成指 +3.25%、创业板 +5.64%、科创50 +4.09%，两市成交约2.21万亿元。成长方向显著修复，但指数急涨后次日更需防高开和冲高回落。
- 映射：风电/电力装备与成长制造可继续观察，银行相对强势逻辑降级。下一交易日仍以0-1只正式规则票、最多2只条件观察为宜；不追单日加速。

## 逐票复盘

| 标的 | 日内行情 | 触发/失效 | 结果 | 复盘 |
| --- | --- | --- | --- | --- |
| 招商银行（600036） | 开40.16 / 高40.16 / 低39.21 / 收39.28，-2.68% | 否 / 否 | 未命中 | 进入39.85-40.10计划区后跌破39.55降级线，尾盘未站回40.35；最低价未严格跌破39.20深失效位。 |
| 金风科技（002202） | 开19.40 / 高19.58 / 低18.94 / 收19.49，+1.30% | 是 / 否 | 命中 | 回踩进入18.70-18.95承接区，14:30后及收盘均站在19.15确认位上方，且未高开超过3%。 |

## 主要误差

1. 招商银行把“前一日逆势”外推为次日承接，但开盘即是日内高点，买点缺乏板块同步和尾盘确认。
2. 金风科技验证了“单日加速后只等分歧回踩”的规则；命中来自可执行买点，而非新闻或题材本身。
3. 成长指数单日大幅反弹提高次日冲高回落风险，不能因为市场修复立即恢复规则票数量。

## 明日规则调整建议

- 不新增统计型调整信号，延续收紧：正式规则票0-1只、条件观察最多2只。
- 银行方向降级，必须重新出现板块相对强势、回踩不破和尾盘站回三项共振。
- 风电/成长制造只接受回踩确认；高开超过3%或直线拉升放弃，不把今日命中外推成追涨理由。
- 失效条件：后续连续两次正式规则票调整后加权命中率高于65%，且无破位、尾盘确认失败或冲高回落，才恢复常规票数。

数据日期：2026-08-04。个股及A股指数来自东方财富公开日线与5分钟行情；隔夜美股参考AP 2026-08-03收盘报道；政策背景参考工信部2026年上半年发布会和证监会监管工作座谈会。本文为规则复盘，不构成收益承诺。
'@
Set-Content -LiteralPath (Join-Path $root $reportRel) -Value $report -Encoding UTF8
Write-Output 'Updated 2026-08-04 A-share review, summaries, and report.'

