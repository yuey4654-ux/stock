$ErrorActionPreference = 'Stop'
$root = if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) { (Get-Location).Path } else { Split-Path -Parent $PSScriptRoot }
$tracking = Join-Path $root 'prediction_tracking'
$targetDate = '2026-07-27'
$reportRel = 'reports/港股预测命中复盘_2026-07-27.md'

function Write-Utf8Csv {
    param([object[]]$Rows, [string]$Path)
    $Rows | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding utf8
}
function Escape-Md {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    return $Value.Replace('|','\|').Replace("`r",' ').Replace("`n",' ')
}
function Normalize-Date {
    param([string]$Value)
    $parsed=[datetime]::MinValue
    if([datetime]::TryParse($Value,[ref]$parsed)){return $parsed.ToString('yyyy-MM-dd')}
    return $Value
}
function Get-Weight {
    param([string]$Type)
    if($Type -eq '核心承接'){return 1.5}
    if($Type -match '^弹性'){return 0.8}
    return 1.0
}
function Get-Metrics {
    param([object[]]$Rows)
    $reviewed=@($Rows|Where-Object {$_.'复盘结果' -in @('命中','部分命中','未命中')})
    $total=$reviewed.Count
    $hit=@($reviewed|Where-Object {$_.'复盘结果' -eq '命中'}).Count
    $partial=@($reviewed|Where-Object {$_.'复盘结果' -eq '部分命中'}).Count
    $miss=@($reviewed|Where-Object {$_.'复盘结果' -eq '未命中'}).Count
    $weightTotal=0.0;$strictScore=0.0;$adjustedScore=0.0
    foreach($row in $reviewed){
        $weight=Get-Weight $row.'预测类型';$weightTotal+=$weight
        if($row.'复盘结果' -eq '命中'){$strictScore+=$weight;$adjustedScore+=$weight}
        elseif($row.'复盘结果' -eq '部分命中'){$adjustedScore+=0.5*$weight}
    }
    $strict=if($total){100*$hit/$total}else{0}
    $adjusted=if($total){100*($hit+0.5*$partial)/$total}else{0}
    $strictWeighted=if($weightTotal){100*$strictScore/$weightTotal}else{0}
    $adjustedWeighted=if($weightTotal){100*$adjustedScore/$weightTotal}else{0}
    return [ordered]@{
        总数=[string]$total;命中=[string]$hit;部分命中=[string]$partial;未命中=[string]$miss;
        严格命中率=('{0:F1}%' -f $strict);调整后命中率=('{0:F1}%' -f $adjusted);
        严格加权命中率=('{0:F1}%' -f $strictWeighted);调整后加权命中率=('{0:F1}%' -f $adjustedWeighted)
    }
}

$predictionsPath=Join-Path $tracking 'hk_daily_predictions.csv'
$predictions=@(Import-Csv -LiteralPath $predictionsPath -Encoding utf8)
$review=@{
    '00941.HK'=@{
        收盘价='82.500';涨跌幅='+0.92%';是否触发='否';是否失效='否';复盘结果='部分命中';
        复盘备注='开81.80/高82.65/低81.70/收82.50。方向和尾盘强度正确，但最低81.70未进入81.00-81.35计划承接区，没有标准买点；新闻与上涨不能替代回踩触发。数据日期：2026-07-27；来源：腾讯港股收盘行情。'
    }
    '00005.HK'=@{
        收盘价='162.800';涨跌幅='+0.87%';是否触发='否';是否失效='否';复盘结果='部分命中';
        复盘备注='开161.00/高163.40/低160.70/收162.80。金融防守方向兑现，收盘站上161.60确认位，但最低160.70较159.80-160.60计划区上沿高0.10，未给标准回踩买点，只记部分命中。数据日期：2026-07-27；来源：腾讯港股收盘行情。'
    }
    '00981.HK'=@{
        收盘价='70.650';涨跌幅='-0.98%';是否触发='否';是否失效='是';复盘结果='未命中';
        复盘备注='开71.00/高72.10/低68.05/收70.65。盘中穿过69.80-70.80承接区后继续下破，最低跌破69.30降级线及68.50深失效位；收盘未站回72.20确认位，高风险半导体观察失败。数据日期：2026-07-27；来源：腾讯港股收盘行情。'
    }
}
$updated=0
foreach($row in $predictions){
    if((Normalize-Date $row.'目标日期') -eq $targetDate -and $row.'复盘结果' -eq '待复盘' -and $review.ContainsKey($row.'代码')){
        foreach($field in $review[$row.'代码'].Keys){$row.$field=$review[$row.'代码'][$field]}
        $updated++
    }
}
if($updated -notin @(0,3)){throw "Unexpected HK update count: $updated"}
Write-Utf8Csv -Rows $predictions -Path $predictionsPath

# 全量每日及累计分类表
$reviewedAll=@($predictions|Where-Object {$_.'是否计入准确率' -eq '是' -and $_.'复盘结果' -in @('命中','部分命中','未命中')})
$pendingAll=@($predictions|Where-Object {$_.'是否计入准确率' -eq '是' -and $_.'复盘结果' -eq '待复盘'})
$dateRows=@()
foreach($group in ($reviewedAll|Group-Object {Normalize-Date $_.'目标日期'})){
    $metrics=Get-Metrics @($group.Group)
    if([int]$metrics.总数 -gt 0){$dateRows += [pscustomobject]([ordered]@{分类=$group.Name}+$metrics)}
}
$dateRows=@($dateRows|Sort-Object @{Expression={[datetime](Normalize-Date $_.'分类')}})
$groups=@(
    @{Name='其他';Rows=@($reviewedAll|Where-Object {$_.'预测类型' -notmatch '^(核心承接|稳健观察|弹性|条件观察|非规则)'})},
    @{Name='弹性观察';Rows=@($reviewedAll|Where-Object {$_.'预测类型' -match '^弹性'})},
    @{Name='条件观察';Rows=@($reviewedAll|Where-Object {$_.'预测类型' -match '^条件观察'})},
    @{Name='核心承接';Rows=@($reviewedAll|Where-Object {$_.'预测类型' -eq '核心承接'})},
    @{Name='港股全量已复盘';Rows=$reviewedAll},
    @{Name='港股待复盘';Rows=$pendingAll},
    @{Name='稳健观察';Rows=@($reviewedAll|Where-Object {$_.'预测类型' -eq '稳健观察'})},
    @{Name='非规则观察';Rows=@($reviewedAll|Where-Object {$_.'预测类型' -match '^非规则'})}
)
$aggregateRows=foreach($group in $groups){
    if($group.Name -eq '港股待复盘'){
        [pscustomobject][ordered]@{分类=$group.Name;总数=[string]$group.Rows.Count;命中='0';部分命中='0';未命中='0';严格命中率='0.0%';调整后命中率='0.0%';严格加权命中率='0.0%';调整后加权命中率='0.0%'}
    }else{
        [pscustomobject]([ordered]@{分类=$group.Name}+(Get-Metrics $group.Rows))
    }
}
$fullRows=@($dateRows+$aggregateRows)
$fullPath=Join-Path $tracking 'hk_daily_review_summary.csv'
Write-Utf8Csv -Rows $fullRows -Path $fullPath
$headers=@($fullRows[0].PSObject.Properties.Name)
$md=@('# 港股每日预测复盘全量汇总','',"更新日期：$targetDate",'')
$md+='| '+(($headers|ForEach-Object {Escape-Md $_}) -join ' | ')+' |'
$md+='| '+(($headers|ForEach-Object {'---'}) -join ' | ')+' |'
foreach($item in $fullRows){$md+='| '+(($headers|ForEach-Object {Escape-Md ([string]$item.$_)}) -join ' | ')+' |'}
Set-Content -LiteralPath (Join-Path $tracking 'hk_daily_review_summary.md') -Value $md -Encoding utf8

# 规则票专用表
$rulePath=Join-Path $tracking 'hk_rule_based_daily_summary.csv'
$ruleRows=@(Import-Csv -LiteralPath $rulePath -Encoding utf8|Where-Object {$_.'目标日期' -ne $targetDate})
$ruleNew=[pscustomobject][ordered]@{
    目标日期=$targetDate;预测日期='2026-07-26';总数='1';命中='0';部分命中='1';未命中='0';
    严格命中率='0.0%';调整后命中率='50.0%';严格加权命中率='0.0%';调整后加权命中率='50.0%';
    核心承接命中='0';核心承接总数='0';稳健观察命中='0';稳健观察总数='1';弹性进攻命中='0';弹性进攻总数='0';其他类型命中='0';其他类型总数='0';
    最佳预测='中国移动';最差预测='无';
    主要误差='中国移动方向正确且收盘走强，但未进入计划回踩区；全量中汇丰同样缺少标准买点，中芯国际则跌破降级线和深失效位。';
    规则调整信号='是';
    下一步规则调整='触发原因：唯一港股正式规则票仅部分命中，严格命中率0%、调整后加权命中率50%，低于60%/65%阈值。建议：下一交易日正式票继续限制为1只，优先低波动电讯或银行，并把承接区设在可交易波动范围内但不取消尾盘确认；半导体高风险票冷却。适用范围：港股正式规则票及科技高波动候选。失效条件：连续两日规则票调整后加权命中率高于65%，且无深失效或无买点样本。';
    报告文件=$reportRel
}
$ruleRows=@($ruleRows+$ruleNew|Sort-Object '目标日期')
Write-Utf8Csv -Rows $ruleRows -Path $rulePath
$ruleHeaders=@($ruleRows[0].PSObject.Properties.Name)
$ruleMd=@('# 港股每日预测复盘规则票汇总','',"更新日期：$targetDate",'')
$ruleMd+='| '+(($ruleHeaders|ForEach-Object {Escape-Md $_}) -join ' | ')+' |'
$ruleMd+='| '+(($ruleHeaders|ForEach-Object {'---'}) -join ' | ')+' |'
foreach($item in $ruleRows){$ruleMd+='| '+(($ruleHeaders|ForEach-Object {Escape-Md ([string]$item.$_)}) -join ' | ')+' |'}
Set-Content -LiteralPath (Join-Path $tracking 'hk_rule_based_daily_summary.md') -Value $ruleMd -Encoding utf8

