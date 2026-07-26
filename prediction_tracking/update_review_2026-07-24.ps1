$ErrorActionPreference = 'Stop'
$root = if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    (Get-Location).Path
} else {
    Split-Path -Parent $PSScriptRoot
}
$tracking = Join-Path $root 'prediction_tracking'
$reportRel = 'reports/预测命中复盘_2026-07-24.md'
$targetDate = '2026-07-24'

function Write-Utf8Csv {
    param([object[]]$Rows, [string]$Path)
    $Rows | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding utf8
}

function Escape-Md {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    return $Value.Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ')
}

$predictionsPath = Join-Path $tracking 'daily_predictions.csv'
$predictions = @(Import-Csv -LiteralPath $predictionsPath -Encoding utf8)
$review = @{
    '600406' = @{
        收盘价='23.58'; 涨跌幅='-3.24%'; 是否触发='否'; 是否失效='是'; 复盘结果='未命中';
        复盘备注='开24.19/高24.37/低23.54/收23.58。盘中进入23.80-24.10承接区后继续走弱，未完成14:30后站回24.35的确认，且最低23.54轻微跌破23.55降级线；电网设备未能逆势承接。数据日期：2026-07-24；来源：腾讯A股收盘行情。'
    }
    '601088' = @{
        收盘价='45.70'; 涨跌幅='+0.84%'; 是否触发='否'; 是否失效='否'; 复盘结果='部分命中';
        复盘备注='开46.00/高46.00/低45.09/收45.70。煤炭高股息方向相对抗跌且收盘站上45.45，但最低45.09未进入44.65-45.00计划买点；方向正确、执行点缺失，最多记部分命中。数据日期：2026-07-24；来源：腾讯A股收盘行情。'
    }
    '600938' = @{
        收盘价='31.91'; 涨跌幅='-3.27%'; 是否触发='否'; 是否失效='是'; 复盘结果='未命中';
        复盘备注='开33.67/高33.83/低31.81/收31.91。高开冲高后快速回落，穿过32.20-32.55承接区并跌破31.90降级线，尾盘未站回33.00；油价利好未转化为有效承接。数据日期：2026-07-24；来源：腾讯A股收盘行情。'
    }
}

$updated = 0
foreach ($row in $predictions) {
    if ($row.'目标日期' -eq $targetDate -and $row.'复盘结果' -eq '待复盘' -and $review.ContainsKey($row.'代码')) {
        foreach ($field in $review[$row.'代码'].Keys) {
            $row.$field = $review[$row.'代码'][$field]
        }
        $updated++
    }
}
if ($updated -ne 3) { throw "Expected to update 3 rows, updated $updated." }
Write-Utf8Csv -Rows $predictions -Path $predictionsPath

$mainError = '正式电网票未扛住指数级普跌并轻微跌破降级线；油气票在油价大涨背景下仍高开冲高回落，说明新闻映射不能替代承接；中国神华虽抗跌但未给计划买点。'
$nextAdjustment = '触发原因：唯一正式规则票国电南瑞未命中并跌破降级线，规则票严格及调整后加权命中率均为0%，低于60%/65%阈值。建议：下一交易日正式规则票维持0-1只，优先银行、军工或低波动方向的回踩承接，电网、煤炭、油气均不得仅凭消息追高；科技/半导体受隔夜纳指与费半转弱影响只作条件观察。适用范围：A股正式规则票及能源、电网、科技映射票。失效条件：连续两日规则票调整后加权命中率高于65%，且无跌破降级线、高开冲高回落或无买点样本。'

function Upsert-Summary {
    param(
        [string]$CsvName,
        [string]$MdName,
        [bool]$RuleOnly
    )
    $csvPath = Join-Path $tracking $CsvName
    $rows = @(Import-Csv -LiteralPath $csvPath -Encoding utf8 | Where-Object { $_.'目标日期' -ne $targetDate })
    if ($RuleOnly) {
        $newRow = [ordered]@{
            目标日期=$targetDate; 预测日期='2026-07-23'; 总数='1'; 命中='0'; 部分命中='0'; 未命中='1';
            严格命中率='0.0%'; 调整后命中率='0.0%'; 严格加权命中率='0.0%'; 调整后加权命中率='0.0%';
            核心承接命中='0'; 核心承接总数='0'; 稳健观察命中='0'; 稳健观察总数='1';
            弹性进攻命中='0'; 弹性进攻总数='0'; 其他类型命中='0'; 其他类型总数='0';
            最佳预测='无'; 最差预测='国电南瑞'; 主要误差=$mainError; 规则调整信号='是';
            下一步规则调整=$nextAdjustment; 报告文件=$reportRel
        }
        $title = '# 每日预测复盘规则票汇总'
    } else {
        $newRow = [ordered]@{
            目标日期=$targetDate; 预测日期='2026-07-23'; 总数='3'; 命中='0'; 部分命中='1'; 未命中='2';
            严格命中率='0.0%'; 调整后命中率='16.7%'; 严格加权命中率='0.0%'; 调整后加权命中率='16.7%';
            核心承接命中='0'; 核心承接总数='0'; 稳健观察命中='0'; 稳健观察总数='1';
            弹性进攻命中='0'; 弹性进攻总数='0'; 其他类型命中='0'; 其他类型总数='2';
            最佳预测='中国神华'; 最差预测='国电南瑞; 中国海油'; 主要误差=$mainError; 策略提醒='是';
            下一步规则调整=$nextAdjustment; 报告文件=$reportRel
        }
        $title = '# 每日预测复盘全量汇总'
    }
    $all = @($rows + [pscustomobject]$newRow | Sort-Object '目标日期')
    Write-Utf8Csv -Rows $all -Path $csvPath

    $headers = @($all[0].PSObject.Properties.Name)
    $lines = @($title, '', "更新日期：$targetDate", '')
    $lines += '| ' + (($headers | ForEach-Object { Escape-Md $_ }) -join ' | ') + ' |'
    $lines += '| ' + (($headers | ForEach-Object { '---' }) -join ' | ') + ' |'
    foreach ($item in $all) {
        $lines += '| ' + (($headers | ForEach-Object { Escape-Md ([string]$item.$_) }) -join ' | ') + ' |'
    }
    Set-Content -LiteralPath (Join-Path $tracking $MdName) -Value $lines -Encoding utf8
}

Upsert-Summary -CsvName 'daily_review_summary.csv' -MdName 'daily_review_summary.md' -RuleOnly $false
Upsert-Summary -CsvName 'rule_based_daily_summary.csv' -MdName 'rule_based_daily_summary.md' -RuleOnly $true
