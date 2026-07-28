$ErrorActionPreference = 'Stop'
$root = if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) { (Get-Location).Path } else { Split-Path -Parent $PSScriptRoot }
$tracking = Join-Path $root 'prediction_tracking'
$targetDate = '2026-07-27'
$reportRel = 'reports/预测命中复盘_2026-07-27.md'

function Write-Utf8Csv([object[]]$Rows, [string]$Path) {
    $Rows | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding utf8
}

function Escape-Md([string]$Value) {
    if ($null -eq $Value) { return '' }
    $Value.Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ')
}

$predictionsPath = Join-Path $tracking 'daily_predictions.csv'
$predictions = @(Import-Csv -LiteralPath $predictionsPath -Encoding utf8)
$review = @{
    '601939' = @{
        收盘价='10.36'; 涨跌幅='+0.97%'; 是否触发='是'; 是否失效='否'; 复盘结果='命中';
        复盘备注='开10.24/高10.47/低10.19/收10.36。回踩10.16-10.24承接区未破，14:30报10.35并收于10.36，均站上10.30确认位；未触及10.10降级线。数据日期：2026-07-27；来源：东方财富日线及分钟行情、腾讯收盘行情。'
    }
    '600760' = @{
        收盘价='43.27'; 涨跌幅='-0.07%'; 是否触发='否'; 是否失效='否'; 复盘结果='未命中';
        复盘备注='开43.70/高43.80/低42.76/收43.27。盘中穿过42.90-43.20承接区后收回，但14:30仅43.40、收盘43.27，均未站上43.60确认位；在全市场普涨背景下仍微跌，条件观察未兑现。数据日期：2026-07-27；来源：东方财富日线及分钟行情、腾讯收盘行情。'
    }
    '601088' = @{
        收盘价='44.83'; 涨跌幅='-1.90%'; 是否触发='否'; 是否失效='是'; 复盘结果='未命中';
        复盘备注='开45.70/高45.70/低44.50/收44.83。进入45.05-45.35承接区后继续下破，最低跌破44.70降级线；14:30报44.83且收盘未站回45.75确认位。油价回落与煤炭偏弱映射兑现，条件观察未兑现。数据日期：2026-07-27；来源：东方财富日线及分钟行情、腾讯收盘行情。'
    }
}

$updated = 0
foreach ($row in $predictions) {
    if ($row.'目标日期' -eq $targetDate -and $row.'复盘结果' -eq '待复盘' -and $review.ContainsKey($row.'代码')) {
        foreach ($field in $review[$row.'代码'].Keys) { $row.$field = $review[$row.'代码'][$field] }
        $updated++
    }
}
if ($updated -ne 3) { throw "Expected 3 pending rows, updated $updated." }
Write-Utf8Csv $predictions $predictionsPath

$mainError = '中航沈飞虽回踩承接区但尾盘未站回确认位，军工题材相对强度未转化为可执行命中；中国神华跌破降级线，说明能源与高股息不能仅凭前一日抗跌延续。'
$nextAdjustment = '本日唯一正式规则票建设银行完整命中，规则票严格及调整后加权命中率均为100%，不新增策略调整信号。建议：下一交易日仍以1只稳健观察正式票为基准，不因单日普涨扩张；军工、煤炭等条件票必须尾盘站回确认位。适用范围：A股正式规则票与题材条件观察票。失效条件：若后续规则票再次低于60%或调整后加权命中率低于65%，立即恢复0-1只收紧模式。'

function Upsert-Summary([string]$CsvName, [string]$MdName, [bool]$RuleOnly) {
    $csvPath = Join-Path $tracking $CsvName
    $rows = @(Import-Csv -LiteralPath $csvPath -Encoding utf8 | Where-Object { $_.'目标日期' -ne $targetDate })
    if ($RuleOnly) {
        $newRow = [ordered]@{
            目标日期=$targetDate; 预测日期='2026-07-26'; 总数='1'; 命中='1'; 部分命中='0'; 未命中='0';
            严格命中率='100.0%'; 调整后命中率='100.0%'; 严格加权命中率='100.0%'; 调整后加权命中率='100.0%';
            核心承接命中='0'; 核心承接总数='0'; 稳健观察命中='1'; 稳健观察总数='1'; 弹性进攻命中='0'; 弹性进攻总数='0';
            其他类型命中='0'; 其他类型总数='0'; 最佳预测='建设银行'; 最差预测='无'; 主要误差=$mainError;
            规则调整信号='否'; 下一步规则调整=$nextAdjustment; 报告文件=$reportRel
        }
        $title = '# 每日预测复盘规则票汇总'
    } else {
        $newRow = [ordered]@{
            目标日期=$targetDate; 预测日期='2026-07-26'; 总数='3'; 命中='1'; 部分命中='0'; 未命中='2';
            严格命中率='33.3%'; 调整后命中率='33.3%'; 严格加权命中率='33.3%'; 调整后加权命中率='33.3%';
            核心承接命中='0'; 核心承接总数='0'; 稳健观察命中='1'; 稳健观察总数='1'; 弹性进攻命中='0'; 弹性进攻总数='0';
            其他类型命中='0'; 其他类型总数='2'; 最佳预测='建设银行'; 最差预测='中国神华; 中航沈飞'; 主要误差=$mainError;
            策略提醒='否'; 下一步规则调整=$nextAdjustment; 报告文件=$reportRel
        }
        $title = '# 每日预测复盘全量汇总'
    }
    $all = @($rows + [pscustomobject]$newRow | Sort-Object '目标日期')
    Write-Utf8Csv $all $csvPath
    $headers = @($all[0].PSObject.Properties.Name)
    $lines = @($title, '', "更新日期：$targetDate", '')
    $lines += '| ' + (($headers | ForEach-Object { Escape-Md $_ }) -join ' | ') + ' |'
    $lines += '| ' + (($headers | ForEach-Object { '---' }) -join ' | ') + ' |'
    foreach ($item in $all) { $lines += '| ' + (($headers | ForEach-Object { Escape-Md ([string]$item.$_) }) -join ' | ') + ' |' }
    Set-Content -LiteralPath (Join-Path $tracking $MdName) -Value $lines -Encoding utf8
}

Upsert-Summary 'daily_review_summary.csv' 'daily_review_summary.md' $false
Upsert-Summary 'rule_based_daily_summary.csv' 'rule_based_daily_summary.md' $true
