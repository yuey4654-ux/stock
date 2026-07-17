$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Join-Path (Get-Location) 'prediction_tracking' }
$root = Split-Path -Parent $scriptDir
$ledgerPath = Join-Path $scriptDir 'daily_predictions.csv'
$allCsv = Join-Path $scriptDir 'daily_review_summary.csv'
$allMd = Join-Path $scriptDir 'daily_review_summary.md'
$ruleCsv = Join-Path $scriptDir 'rule_based_daily_summary.csv'
$ruleMd = Join-Path $scriptDir 'rule_based_daily_summary.md'
$reportRel = 'reports/预测命中复盘_2026-07-17.md'
$target = '2026-07-17'

function Normalize-Date([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) { return '' }
    return ([datetime]$value).ToString('yyyy-MM-dd')
}

$review = @{
    '600170' = @{ Close='2.28'; Change='-2.15%'; Trigger='否'; Invalid='是'; Result='未命中'; Note='收盘2.28，-2.15%；开2.33/高2.36/低2.26。盘中跌破2.27降级线，收盘未站回2.34，基建未形成有效扩散，按失效优先记未命中。数据：腾讯行情，2026-07-17。' }
    '600900' = @{ Close='27.99'; Change='+1.97%'; Trigger='否'; Invalid='是'; Result='未命中'; Note='除息日收盘27.99，+1.97%（按除息参考价）；开27.61/高28.19/低27.35。原预测未前置校正XD除息，绝对触发位28.35及失效位27.85失真，且收盘未达原触发位，按规则记未命中并列为流程误差。数据：腾讯行情，2026-07-17。' }
    '600519' = @{ Close='1253.00'; Change='-0.48%'; Trigger='否'; Invalid='否'; Result='未命中'; Note='收盘1253.00，-0.48%；开1269.01/高1269.33/低1238.98。低点跌破1245承接区下沿，尾盘未站回1262，白酒亦未形成板块扩散；未跌破1238降级线，但触发条件不成立，记未命中。数据：腾讯行情，2026-07-17。' }
    '601595' = @{ Close='17.34'; Change='-4.52%'; Trigger='否'; Invalid='否'; Result='未命中'; Note='收盘17.34，-4.52%；开18.38/高18.78/低17.30。高开冲高后回落，回踩跌破17.35承接下沿，尾盘未站回17.90；未触及17.10降级线，但影视分化，条件观察未兑现。数据：腾讯行情，2026-07-17。' }
    '002739' = @{ Close='10.09'; Change='-2.23%'; Trigger='否'; Invalid='否'; Result='未命中'; Note='收盘10.09，-2.23%；开10.99/高11.26/低10.02。开盘较昨收高约6.5%，触发高开不追，且未回踩9.75-9.95买点；冲高后明显回落，影视过热样本失败。数据：腾讯行情，2026-07-17。' }
}

$rows = Import-Csv -LiteralPath $ledgerPath
foreach ($row in $rows) {
    if ((Normalize-Date $row.目标日期) -eq $target -and $row.复盘结果 -eq '待复盘' -and $review.ContainsKey($row.代码)) {
        $x = $review[$row.代码]
        $row.收盘价 = $x.Close
        $row.涨跌幅 = $x.Change
        $row.是否触发 = $x.Trigger
        $row.是否失效 = $x.Invalid
        $row.复盘结果 = $x.Result
        $row.复盘备注 = $x.Note
    }
}
$rows | Export-Csv -LiteralPath $ledgerPath -NoTypeInformation -Encoding utf8

function Upsert-Summary([string]$path, [hashtable]$record) {
    $existing = if (Test-Path -LiteralPath $path) { @(Import-Csv -LiteralPath $path) } else { @() }
    $headers = if ($existing.Count -gt 0) { @($existing[0].PSObject.Properties.Name) } else { @($record.Keys) }
    $kept = @($existing | Where-Object { (Normalize-Date $_.目标日期) -ne $target })
    $obj = [ordered]@{}
    foreach ($h in $headers) { $obj[$h] = if ($record.ContainsKey($h)) { $record[$h] } else { '' } }
    $combined = @($kept) + @([pscustomobject]$obj)
    $combined | Sort-Object { [datetime](Normalize-Date $_.目标日期) } | Export-Csv -LiteralPath $path -NoTypeInformation -Encoding utf8
}

$common = @{
    '目标日期'='2026-07-17'; '预测日期'='2026-07-16'; '总数'='5'; '命中'='0'; '部分命中'='0'; '未命中'='5';
    '严格命中率'='0.0%'; '调整后命中率'='0.0%'; '严格加权命中率'='0.0%'; '调整后加权命中率'='0.0%';
    '核心承接命中'='0'; '核心承接总数'='0'; '稳健观察命中'='0'; '稳健观察总数'='2'; '弹性进攻命中'='0'; '弹性进攻总数'='0';
    '其他类型命中'='0'; '其他类型总数'='3'; '最佳预测'='长江电力（方向偏强但除息价位失真）';
    '最差预测'='上海建工; 上海电影; 儒意电影';
    '主要误差'='正式票未适应指数级风险释放；长江电力除息未前置校正触发/失效价位；影视过热票虽标为非规则，但高开冲高回落风险仍然突出。';
    '规则调整信号'='是'; '策略提醒'='是';
    '下一步规则调整'='触发原因：正式规则票2只均未命中，严格及调整后加权命中率均为0%，低于60%/65%阈值。建议：下一交易日正式规则票降至0-1只，优先电力/银行等逆势板块的低波动承接；所有含权、除权除息票先复权校正买点和失效位；科技、半导体与影视仅作条件观察。适用范围：A股正式规则票及含权标的。失效条件：连续两日规则票调整后加权命中率回到65%以上，且无深失效、冲高回落或公司行动价位失真样本。';
    '报告文件'=$reportRel
}
Upsert-Summary $allCsv $common

$rule = $common.Clone()
$rule['总数']='2'; $rule['未命中']='2'; $rule['其他类型总数']='0'
$rule['最佳预测']='长江电力（相对市场偏强但规则未触发）'
$rule['最差预测']='上海建工; 长江电力'
$rule['主要误差']='两只稳健观察票均未完成承接与尾盘确认；长江电力除息未校正绝对价位，是当日最重要的流程误差。'
Upsert-Summary $ruleCsv $rule

function Csv-To-Markdown([string]$csvPath, [string]$mdPath, [string]$title) {
    $data = @(Import-Csv -LiteralPath $csvPath)
    if ($data.Count -eq 0) { return }
    $headers = @($data[0].PSObject.Properties.Name)
    $lines = @('# ' + $title, '', '| ' + ($headers -join ' | ') + ' |', '| ' + (($headers | ForEach-Object { '---' }) -join ' | ') + ' |')
    foreach ($r in $data) {
        $vals = foreach ($h in $headers) { ([string]$r.$h).Replace('|','\|').Replace("`r",' ').Replace("`n",' ') }
        $lines += '| ' + ($vals -join ' | ') + ' |'
    }
    Set-Content -LiteralPath $mdPath -Value $lines -Encoding utf8
}
Csv-To-Markdown $allCsv $allMd '每日预测全量复盘汇总'
Csv-To-Markdown $ruleCsv $ruleMd '每日预测交易规则专用汇总'

Write-Output 'Updated ledger and both summary histories for 2026-07-17.'
