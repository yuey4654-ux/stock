$ErrorActionPreference = 'Stop'
$root = if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) { (Get-Location).Path } else { Split-Path -Parent $PSScriptRoot }
$tracking = Join-Path $root 'prediction_tracking'
$targetDate = '2026-07-24'
$reportRel = 'reports/港股预测命中复盘_2026-07-24.md'

function Write-Utf8Csv {
    param([object[]]$Rows, [string]$Path)
    $Rows | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding utf8
}

function Escape-Md {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    return $Value.Replace('|', '\|').Replace("`r", ' ').Replace("`n", ' ')
}

function Normalize-Date {
    param([string]$Value)
    $parsed = [datetime]::MinValue
    if ([datetime]::TryParse($Value, [ref]$parsed)) { return $parsed.ToString('yyyy-MM-dd') }
    return $Value
}

function Get-Weight {
    param([string]$Type)
    if ($Type -eq '核心承接') { return 1.5 }
    if ($Type -match '^弹性') { return 0.8 }
    return 1.0
}

function Get-Metrics {
    param([object[]]$Rows)
    $reviewed = @($Rows | Where-Object { $_.'复盘结果' -in @('命中','部分命中','未命中') })
    $total = $reviewed.Count
    $hit = @($reviewed | Where-Object { $_.'复盘结果' -eq '命中' }).Count
    $partial = @($reviewed | Where-Object { $_.'复盘结果' -eq '部分命中' }).Count
    $miss = @($reviewed | Where-Object { $_.'复盘结果' -eq '未命中' }).Count
    $weightTotal = 0.0; $strictScore = 0.0; $adjustedScore = 0.0
    foreach ($row in $reviewed) {
        $weight = Get-Weight $row.'预测类型'
        $weightTotal += $weight
        if ($row.'复盘结果' -eq '命中') { $strictScore += $weight; $adjustedScore += $weight }
        elseif ($row.'复盘结果' -eq '部分命中') { $adjustedScore += 0.5 * $weight }
    }
    $strict = if ($total) { 100.0 * $hit / $total } else { 0.0 }
    $adjusted = if ($total) { 100.0 * ($hit + 0.5 * $partial) / $total } else { 0.0 }
    $strictWeighted = if ($weightTotal) { 100.0 * $strictScore / $weightTotal } else { 0.0 }
    $adjustedWeighted = if ($weightTotal) { 100.0 * $adjustedScore / $weightTotal } else { 0.0 }
    return [ordered]@{
        总数=[string]$total; 命中=[string]$hit; 部分命中=[string]$partial; 未命中=[string]$miss;
        严格命中率=('{0:F1}%' -f $strict); 调整后命中率=('{0:F1}%' -f $adjusted);
        严格加权命中率=('{0:F1}%' -f $strictWeighted); 调整后加权命中率=('{0:F1}%' -f $adjustedWeighted)
    }
}

$predictionsPath = Join-Path $tracking 'hk_daily_predictions.csv'
$predictions = @(Import-Csv -LiteralPath $predictionsPath -Encoding utf8)
$review = @{
    '00941.HK' = @{
        收盘价='81.750'; 涨跌幅='+0.43%'; 是否触发='是'; 是否失效='否'; 复盘结果='命中';
        复盘备注='开81.20/高81.95/低81.00/收81.75。低点进入80.70-81.05计划承接区且未破80.35降级线，收盘站上81.45确认位；电讯防守票完成回踩与尾盘确认。数据日期：2026-07-24；来源：腾讯港股收盘行情。'
    }
    '00005.HK' = @{
        收盘价='161.400'; 涨跌幅='-0.06%'; 是否触发='否'; 是否失效='否'; 复盘结果='部分命中';
        复盘备注='开159.80/高161.60/低159.30/收161.40。盘中进入159.80-160.60承接区并守住159.20降级线，但收盘较161.50确认位低0.10；方向防守有效，尾盘确认不足。数据日期：2026-07-24；来源：腾讯港股收盘行情。'
    }
    '00883.HK' = @{
        收盘价='23.560'; 涨跌幅='-2.73%'; 是否触发='否'; 是否失效='是'; 复盘结果='未命中';
        复盘备注='开24.44/高24.64/低23.44/收23.56。高开冲高后跌穿23.85-24.05承接区，并跌破23.60降级线，收盘远低于24.25确认位；油价消息未转化为有效承接。数据日期：2026-07-24；来源：腾讯港股收盘行情。'
    }
}

$historicalReview = @{
    '2026-07-16|09618.HK' = @{收盘价='116.800';涨跌幅='+0.95%';是否触发='否';是否失效='否';复盘结果='部分命中';复盘备注='开115.20/高119.70/低114.80/收116.80。方向与收盘强度正确，但低点未进入113.50-114.50计划买点，只记部分命中。数据日期：2026-07-16；来源：腾讯港股历史行情。'}
    '2026-07-16|01088.HK' = @{收盘价='41.880';涨跌幅='-2.42%';是否触发='是';是否失效='是';复盘结果='未命中';复盘备注='开42.76/高43.26/低41.46/收41.88。盘中进入42.10-42.50承接区后跌破41.80降级线，尾盘未站回43.00，按失效优先记未命中。数据日期：2026-07-16；来源：腾讯港股历史行情。'}
    '2026-07-16|00700.HK' = @{收盘价='484.000';涨跌幅='+2.11%';是否触发='否';是否失效='否';复盘结果='部分命中';复盘备注='开478.00/高494.80/低477.40/收484.00。互联网方向走强且收盘越过476，但未回到466-470计划买点，最多记部分命中。数据日期：2026-07-16；来源：腾讯港股历史行情。'}
    '2026-07-16|02269.HK' = @{收盘价='39.320';涨跌幅='-0.56%';是否触发='否';是否失效='否';复盘结果='未命中';复盘备注='开39.70/高41.00/低38.90/收39.32。低点未进入38.20-38.80计划区，收盘也未站回39.80确认位，条件观察未兑现。数据日期：2026-07-16；来源：腾讯港股历史行情。'}
    '2026-07-16|03690.HK' = @{收盘价='87.200';涨跌幅='+4.56%';是否触发='否';是否失效='否';复盘结果='部分命中';复盘备注='开84.45/高88.95/低84.30/收87.20。方向明显走强，但全天未进入80.50-81.80计划低吸区，不能把上涨等同于可执行命中。数据日期：2026-07-16；来源：腾讯港股历史行情。'}
    '2026-07-17|00941.HK' = @{收盘价='79.950';涨跌幅='+0.44%';是否触发='否';是否失效='否';复盘结果='部分命中';复盘备注='开79.80/高80.45/低79.40/收79.95。收盘站上79.75确认位，但低点较79.35承接上沿高0.05，未给标准买点，只记部分命中。数据日期：2026-07-17；来源：腾讯港股历史行情。'}
    '2026-07-17|09618.HK' = @{收盘价='116.300';涨跌幅='-0.43%';是否触发='否';是否失效='否';复盘结果='部分命中';复盘备注='开116.90/高119.40/低115.60/收116.30。盘中进入114.80-115.80承接区且未失效，但尾盘未站回117.20，只记部分命中。数据日期：2026-07-17；来源：腾讯港股历史行情。'}
    '2026-07-17|00700.HK' = @{收盘价='461.600';涨跌幅='-4.63%';是否触发='是';是否失效='是';复盘结果='未命中';复盘备注='开488.80/高488.80/低458.00/收461.60。高开后快速回落，跌破472降级线及466深失效位，互联网平台承接失败。数据日期：2026-07-17；来源：腾讯港股历史行情。'}
    '2026-07-17|09988.HK' = @{收盘价='112.600';涨跌幅='-3.68%';是否触发='是';是否失效='是';复盘结果='未命中';复盘备注='开116.30/高118.00/低110.70/收112.60。盘中跌破112.80降级线并下破111.00深失效位，高位互联网票冲高回落。数据日期：2026-07-17；来源：腾讯港股历史行情。'}
    '2026-07-17|01088.HK' = @{收盘价='42.400';涨跌幅='+1.24%';是否触发='是';是否失效='否';复盘结果='命中';复盘备注='开41.98/高42.50/低41.54/收42.40。低点进入41.45-41.75承接区且守住41.20降级线，收盘站上42.20确认位，完整命中。数据日期：2026-07-17；来源：腾讯港股历史行情。'}
}

$updated = 0
foreach ($row in $predictions) {
    if ($row.'预测日期' -eq '2026-07-23' -and $row.'目标日期' -eq $targetDate -and $row.'复盘结果' -eq '待复盘' -and $review.ContainsKey($row.'代码')) {
        foreach ($field in $review[$row.'代码'].Keys) { $row.$field = $review[$row.'代码'][$field] }
        $updated++
    }
    $normalizedDate = Normalize-Date $row.'目标日期'
    $historicalKey = "$normalizedDate|$($row.'代码')"
    if ($row.'复盘结果' -eq '待复盘' -and $historicalReview.ContainsKey($historicalKey)) {
        foreach ($field in $historicalReview[$historicalKey].Keys) { $row.$field = $historicalReview[$historicalKey][$field] }
        $updated++
    }
}
if ($updated -notin @(0,10,13)) { throw "Unexpected Hong Kong update count: $updated." }
Write-Utf8Csv -Rows $predictions -Path $predictionsPath

# 港股全量表沿用原有精简字段，保留所有旧日期行，更新当日与累计分类。
$fullPath = Join-Path $tracking 'hk_daily_review_summary.csv'
$dateRows = @()
foreach ($group in ($predictions | Where-Object { $_.'是否计入准确率' -eq '是' -and $_.'复盘结果' -in @('命中','部分命中','未命中') } | Group-Object { Normalize-Date $_.'目标日期' })) {
    $metrics = Get-Metrics @($group.Group)
    if ([int]$metrics.总数 -gt 0) {
        $dateRows += [pscustomobject]([ordered]@{分类=$group.Name} + $metrics)
    }
}
$dateRows = @($dateRows | Sort-Object @{Expression={ [datetime](Normalize-Date $_.'分类') }})

$reviewedAll = @($predictions | Where-Object { $_.'是否计入准确率' -eq '是' -and $_.'复盘结果' -in @('命中','部分命中','未命中') })
$pendingAll = @($predictions | Where-Object { $_.'是否计入准确率' -eq '是' -and $_.'复盘结果' -eq '待复盘' })
$groups = @(
    @{Name='其他'; Rows=@($reviewedAll | Where-Object { $_.'预测类型' -notmatch '^(核心承接|稳健观察|弹性|条件观察|非规则)' })},
    @{Name='弹性观察'; Rows=@($reviewedAll | Where-Object { $_.'预测类型' -match '^弹性' })},
    @{Name='条件观察'; Rows=@($reviewedAll | Where-Object { $_.'预测类型' -match '^条件观察' })},
    @{Name='核心承接'; Rows=@($reviewedAll | Where-Object { $_.'预测类型' -eq '核心承接' })},
    @{Name='港股全量已复盘'; Rows=$reviewedAll},
    @{Name='港股待复盘'; Rows=$pendingAll},
    @{Name='稳健观察'; Rows=@($reviewedAll | Where-Object { $_.'预测类型' -eq '稳健观察' })},
    @{Name='非规则观察'; Rows=@($reviewedAll | Where-Object { $_.'预测类型' -match '^非规则' })}
)
$aggregateRows = foreach ($group in $groups) {
    if ($group.Name -eq '港股待复盘') {
        [pscustomobject][ordered]@{分类=$group.Name; 总数=[string]$group.Rows.Count; 命中='0'; 部分命中='0'; 未命中='0'; 严格命中率='0.0%'; 调整后命中率='0.0%'; 严格加权命中率='0.0%'; 调整后加权命中率='0.0%'}
    } else {
        [pscustomobject]([ordered]@{分类=$group.Name} + (Get-Metrics $group.Rows))
    }
}
$fullRows = @($dateRows + $aggregateRows)
Write-Utf8Csv -Rows $fullRows -Path $fullPath

$fullHeaders = @($fullRows[0].PSObject.Properties.Name)
$fullMd = @('# 港股每日预测复盘全量汇总', '', "更新日期：$targetDate", '')
$fullMd += '| ' + (($fullHeaders | ForEach-Object { Escape-Md $_ }) -join ' | ') + ' |'
$fullMd += '| ' + (($fullHeaders | ForEach-Object { '---' }) -join ' | ') + ' |'
foreach ($item in $fullRows) {
    $fullMd += '| ' + (($fullHeaders | ForEach-Object { Escape-Md ([string]$item.$_) }) -join ' | ') + ' |'
}
Set-Content -LiteralPath (Join-Path $tracking 'hk_daily_review_summary.md') -Value $fullMd -Encoding utf8

# 港股规则票专用表。
$rulePath = Join-Path $tracking 'hk_rule_based_daily_summary.csv'
$ruleRows = @(Import-Csv -LiteralPath $rulePath -Encoding utf8 | Where-Object { $_.'目标日期' -notin @('2026-07-16','2026-07-17',$targetDate) })
$ruleHistorical = @(
    [pscustomobject][ordered]@{
        目标日期='2026-07-16';预测日期='2026-07-15';总数='2';命中='0';部分命中='1';未命中='1';严格命中率='0.0%';调整后命中率='25.0%';严格加权命中率='0.0%';调整后加权命中率='25.0%';
        核心承接命中='0';核心承接总数='0';稳健观察命中='0';稳健观察总数='2';弹性进攻命中='0';弹性进攻总数='0';其他类型命中='0';其他类型总数='0';
        最佳预测='京东集团-SW';最差预测='中国神华';主要误差='京东方向正确但未给计划买点；中国神华进入承接区后跌破降级线，正式防守票失效。';规则调整信号='是';
        下一步规则调整='规则票严格命中率0%、调整后加权命中率25%，低于阈值。下一交易日正式票维持1-2只，要求回踩后尾盘确认；能源弱于预期时不因油价新闻放宽。适用范围：港股稳健票。失效条件：连续两日规则票调整后加权命中率高于65%且无破位。';报告文件='reports/港股预测命中复盘_2026-07-16.md'
    },
    [pscustomobject][ordered]@{
        目标日期='2026-07-17';预测日期='2026-07-16';总数='2';命中='0';部分命中='2';未命中='0';严格命中率='0.0%';调整后命中率='50.0%';严格加权命中率='0.0%';调整后加权命中率='50.0%';
        核心承接命中='0';核心承接总数='0';稳健观察命中='0';稳健观察总数='2';弹性进攻命中='0';弹性进攻总数='0';其他类型命中='0';其他类型总数='0';
        最佳预测='中国移动; 京东集团-SW';最差预测='无';主要误差='中国移动差标准回踩买点，京东完成回踩但未完成尾盘确认，两只正式票均只能部分命中。';规则调整信号='是';
        下一步规则调整='规则票严格命中率0%、调整后加权命中率50%，继续低于阈值。正式票压缩至1只，优先低波动电讯/银行并保留尾盘确认。适用范围：港股正式规则票。失效条件：连续两日调整后加权命中率高于65%。';报告文件='reports/港股预测命中复盘_2026-07-17.md'
    }
)
$ruleNew = [pscustomobject][ordered]@{
    目标日期=$targetDate; 预测日期='2026-07-23'; 总数='1'; 命中='1'; 部分命中='0'; 未命中='0';
    严格命中率='100.0%'; 调整后命中率='100.0%'; 严格加权命中率='100.0%'; 调整后加权命中率='100.0%';
    核心承接命中='0'; 核心承接总数='0'; 稳健观察命中='1'; 稳健观察总数='1';
    弹性进攻命中='0'; 弹性进攻总数='0'; 其他类型命中='0'; 其他类型总数='0';
    最佳预测='中国移动'; 最差预测='无';
    主要误差='规则票中国移动完成回踩和收盘确认；全量误差主要来自中国海洋石油在油价大涨背景下仍高开冲高回落并跌破降级线。';
    规则调整信号='否';
    下一步规则调整='当日唯一规则票命中，未触发60%/65%阈值；但此前连续多日仅部分命中，尚不足以扩张票数。下一交易日仍只保留1只低波动稳健票，科技与能源高开映射仅作条件观察。适用范围：港股正式规则票。失效条件：若规则票再次低于60%或调整后加权低于65%，立即恢复策略调整提醒。';
    报告文件=$reportRel
}
$ruleRows = @($ruleRows + $ruleHistorical + $ruleNew | Sort-Object '目标日期')
Write-Utf8Csv -Rows $ruleRows -Path $rulePath

$ruleHeaders = @($ruleRows[0].PSObject.Properties.Name)
$ruleMd = @('# 港股每日预测复盘规则票汇总', '', "更新日期：$targetDate", '')
$ruleMd += '| ' + (($ruleHeaders | ForEach-Object { Escape-Md $_ }) -join ' | ') + ' |'
$ruleMd += '| ' + (($ruleHeaders | ForEach-Object { '---' }) -join ' | ') + ' |'
foreach ($item in $ruleRows) {
    $ruleMd += '| ' + (($ruleHeaders | ForEach-Object { Escape-Md ([string]$item.$_) }) -join ' | ') + ' |'
}
Set-Content -LiteralPath (Join-Path $tracking 'hk_rule_based_daily_summary.md') -Value $ruleMd -Encoding utf8
