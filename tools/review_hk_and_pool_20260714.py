import csv
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'prediction_tracking'; R=ROOT/'reports'
TARGET='2026/7/14'; ISO='2026-07-14'
LEDGER=P/'hk_daily_predictions.csv'; RULE=P/'hk_rule_based_daily_summary.csv'; RULE_MD=P/'hk_rule_based_daily_summary.md'
REPORT=R/f'港股预测命中复盘_{ISO}.md'; POOL=P/'watch_pool_full.csv'; POOL_MD=P/'watch_pool_full.md'; POOL_REPORT=R/f'股票池整理_{ISO}.md'

REV={
'00883.HK':('22.800','+2.43%','否','否','部分命中','开22.80/高23.04/低22.50/收22.80。能源方向强、收盘站上22.4，但未回踩22.0-22.2计划买点，方向正确而执行点缺失。'),
'00941.HK':('79.100','-0.19%','否','否','部分命中','开79.25/高79.35/低78.80/收79.10。低点进入78.6-79.0承接区且未失效，但尾盘未站回79.5，只完成承接未完成确认。'),
'01093.HK':('8.110','-0.61%','否','否','部分命中','开8.14/高8.24/低7.95/收8.11。盘中进入承接区并未跌破7.82降级线，但收盘未站回8.22，医药防守确认不足。'),
'00388.HK':('389.000','+0.36%','否','否','部分命中','开387.40/高389.60/低380.80/收389.00。尾盘修复至确认位，但盘中短暂跌破381降级线，标准承接路径被破坏，不能记严格命中。'),
'09618.HK':('113.800','+0.53%','否','否','部分命中','开113.20/高114.70/低111.00/收113.80。回踩进入111.0-112.5承接区，但收盘未站回114.5，只有承接、没有尾盘确认。'),
'01088.HK':('42.300','+1.83%','否','否','部分命中','开41.60/高42.48/低41.52/收42.30。能源方向正确且收盘站上41.8，但未回踩40.8-41.3计划买点，缺少可执行低吸点。')}

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(rows)
def stats(rows):
    n=len(rows);h=sum(x['复盘结果']=='命中' for x in rows);p=sum(x['复盘结果']=='部分命中' for x in rows);m=sum(x['复盘结果']=='未命中' for x in rows)
    return n,h,p,m,f'{h/n*100:.1f}%' if n else '0.0%',f'{(h+.5*p)/n*100:.1f}%' if n else '0.0%'
def counts(rows,prefix):
    x=[r for r in rows if r['预测类型'].startswith(prefix)];return sum(r['复盘结果']=='命中' for r in x),len(x)
def summary_row(rows):
    n,h,p,m,strict,adj=stats(rows);core=counts(rows,'核心承接');stable=counts(rows,'稳健观察');elastic=counts(rows,'弹性进攻');other=[r for r in rows if not r['预测类型'].startswith(('核心承接','稳健观察','弹性进攻'))]
    return {'目标日期':ISO,'预测日期':ISO,'总数':str(n),'命中':str(h),'部分命中':str(p),'未命中':str(m),'严格命中率':strict,'调整后命中率':adj,'严格加权命中率':strict,'调整后加权命中率':adj,'核心承接命中':str(core[0]),'核心承接总数':str(core[1]),'稳健观察命中':str(stable[0]),'稳健观察总数':str(stable[1]),'弹性进攻命中':str(elastic[0]),'弹性进攻总数':str(elastic[1]),'其他类型命中':str(sum(r['复盘结果']=='命中' for r in other)),'其他类型总数':str(len(other)),'最佳预测':'中国海洋石油; 中国神华; 京东集团-SW','最差预测':'香港交易所','主要误差':'港股方向强弱判断大致正确，但计划买点与尾盘确认普遍未同时满足；港交所盘中跌破降级线后才修复。','规则调整信号':'是','下一步规则调整':'触发原因：3只正式规则票均仅部分命中，严格命中率0.0%、调整后加权命中率50.0%，低于60%/65%阈值。建议调整：下一交易日港股正式票维持2-3只，优先高股息与低位承接，取消只凭收盘上涨的升级；必须同时满足计划买点和尾盘确认。适用范围：港股能源、高股息、医药、互联网。失效条件：连续两日规则票调整后加权命中率高于65%，且无盘中跌破降级线样本。','报告文件':f'reports/港股预测命中复盘_{ISO}.md'}
def md(path,title,rows):
    fields=list(rows[0]);lines=[title,'',f'更新日期：{ISO}','','| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |'];lines += ['| '+' | '.join(r.get(k,'').replace('|','／') for k in fields)+' |' for r in rows];path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def update_hk():
    rows=read(LEDGER);fields=list(rows[0]);seen=set()
    for r in rows:
        if r['目标日期']==TARGET and r['代码'] in REV:
            c,ch,t,i,res,note=REV[r['代码']];r.update({'收盘价':c,'涨跌幅':ch,'是否触发':t,'是否失效':i,'复盘结果':res,'复盘备注':note+' 数据日期：2026-07-14；来源：腾讯港股行情。'});seen.add(r['代码'])
    if seen!=set(REV):raise RuntimeError(set(REV)-seen)
    write(LEDGER,rows,fields);today=[r for r in rows if r['目标日期']==TARGET];rules=[r for r in today if not r['预测类型'].startswith('非规则')]
    subprocess.run(['python',str(ROOT/'tools'/'calc_hk_prediction_accuracy.py')],cwd=ROOT,check=True)
    old=read(RULE);fields=list(old[0]);old=[r for r in old if r['目标日期']!=ISO];new=summary_row(rules);old.append({k:new.get(k,'') for k in fields});old.sort(key=lambda r:r['目标日期']);write(RULE,old,fields);md(RULE_MD,'# 港股每日预测复盘规则票汇总',old)
    table='\n'.join(f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['是否触发']} | {r['是否失效']} | {r['复盘结果']} | {r['复盘备注']} |" for r in today)
    REPORT.write_text(f'''# 港股预测命中复盘 {ISO}

## 策略调整提醒

- 已触发：3只正式规则票均为部分命中，严格命中率 `0.0%`、调整后加权命中率 `50.0%`，低于60%/65%阈值。
- 下一交易日正式票维持2-3只，必须同时满足计划买点与尾盘确认；适用于港股能源、高股息、医药和互联网。失效条件为连续两日规则票调整后加权命中率高于65%，且无盘中跌破降级线样本。

## 一句话结论

港股全量6票全部为部分命中，严格命中率 `0.0%`、调整后命中率 `50.0%`。恒指涨0.52%、恒生科技涨0.06%，能源偏强，但大多数票只兑现方向或承接，没有完整兑现可执行买点与收盘确认。

## 新闻政策与美股影响

- 隔夜纳指与费城半导体显著走弱，港股科技只小幅修复，互联网票仍需尾盘确认；能源受油价上行映射相对占优。
- 中国海洋石油与中国神华方向正确，但都没有给到计划低吸区，因此不能因收涨追认命中。新闻与外盘只决定观察优先级，不替代买点。

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
{table}

## 主要误差与明日建议

- 主要误差是把方向正确与执行命中混在一起：港交所虽然收回389，但盘中跌破降级线；中海油、神华上涨却没有计划内买点。
- 明日继续收紧：高开不追；先回踩承接区，再看14:30后确认。若只满足其中一项，最多部分命中。
''',encoding='utf-8')

def update_pool():
    rows=read(POOL);fields=list(rows[0]);by={r['代码']:r for r in rows}
    changes={
    '600938':('中国海油','A股','油气/高股息','核心执行池','回踩29.0-29.3不破，尾盘站稳29.5；高开超过3%不追','跌破28.7降级，跌破28.4移出执行池'),
    '600900':('长江电力','A股','电力/高股息','核心执行池','回踩28.25-28.40不破，尾盘站稳28.55','跌破28.1降级，跌破27.8转低权重'),
    '002422':('科伦药业','A股','创新药','强势观察池','大涨后只看回踩46.5-47.5承接，重新站回48.5；高开不追','跌破46.0降级，放量跌破44.8转冷却'),
    '002223':('鱼跃医疗','A股','医疗器械/康复器械','轮动观察池','回踩26.3-26.6不破，尾盘站稳26.9','跌破26.0降级，跌破25.5移出优先池'),
    '601088':('中国神华','A股','煤炭/高股息能源','稳健观察池','回踩42.6-43.0不破，尾盘站稳43.4；不追能源高开','跌破42.4降级，跌破41.8转低权重'),
    '600276':('恒瑞医药','A股','创新药','降级观察池','重新站回55.8并强于创新药板块，再看56.2确认','跌破54.2继续降级，跌破53.6移出近期候选'),
    '00883.HK':('中国海洋石油','港股','油气/高股息','稳健观察池','回踩22.4-22.6不破，尾盘站回22.8；高开不追','跌破22.2降级，跌破21.7转低权重'),
    '00941.HK':('中国移动','港股','通信运营/高股息','稳健观察池','回踩78.8-79.1不破，尾盘站回79.5','跌破78.6降级，跌破78.0转低权重'),
    '01093.HK':('石药集团','港股','医药','轮动观察池','回踩7.95-8.05不破，尾盘站回8.22','跌破7.82降级，跌破7.66移出近期候选'),
    '00388.HK':('香港交易所','港股','交易所/市场活跃度','降级观察池','先站稳386，再回踩不破并收复389','再度跌破381继续降级，跌破377移出近期候选'),
    '09618.HK':('京东集团-SW','港股','互联网消费','轮动观察池','回踩111-112.5不破，尾盘站回114.5','跌破109.5降级，跌破108移出近期候选'),
    '01088.HK':('中国神华','港股','煤炭/高股息能源','稳健观察池','回踩41.5-41.8不破，尾盘站回42.3','跌破41.3降级，跌破40.4转低权重')}
    for code,v in changes.items():
        name,market,direction,level,alert,down=v
        item=by.get(code,{k:'' for k in fields});item.update({'代码':code,'名称':name,'市场':market,'方向':direction,'当前层级':level,'提醒条件':alert,'降级条件':down,'来源':'2026-07-14收盘复盘整理','更新时间':ISO});by[code]=item
    out=list(by.values());out.sort(key=lambda r:(r['市场'],r['当前层级'],r['代码']));write(POOL,out,fields)
    order=['核心执行池','稳健观察池','强势观察池','轮动观察池','低权重观察池','降级观察池']
    lines=['# 全量自选池','',f'更新日期：{ISO}','','> 分层原则：方向正确但未给计划买点的票只保留观察；跌破降级线的票不因尾盘修复直接升回执行层。','']
    for level in order:
        items=[r for r in out if r['当前层级']==level]
        if not items:continue
        lines += [f'## {level}','','| 代码 | 名称 | 市场 | 方向 | 提醒条件 | 降级条件 |','| --- | --- | --- | --- | --- | --- |']
        lines += [f"| {r['代码']} | {r['名称']} | {r['市场']} | {r['方向']} | {r['提醒条件']} | {r['降级条件']} |" for r in items];lines.append('')
    POOL_MD.write_text('\n'.join(lines),encoding='utf-8')
    POOL_REPORT.write_text(f'''# 股票池整理 {ISO}

## 今日结论

- 核心执行：`中国海油、长江电力`。两只A股正式规则票均完成计划承接与收盘确认。
- 稳健观察：`中国神华A/H、中国移动、中国海洋石油H`。方向偏强，但部分未提供计划买点，不能追高。
- 强势观察：`科伦药业`。今日大涨8.26%，次日只等回踩，不把加速上涨直接当买点。
- 轮动观察：`鱼跃医疗、石药集团、京东集团`。有题材或承接，但尾盘确认不完整。
- 降级观察：`恒瑞医药、香港交易所`。恒瑞跌破降级线；港交所盘中跌破381后修复，需重新完成承接。

## 明日优先顺序

1. 先看中国海油、长江电力是否给低吸承接，不追高。
2. 科伦药业只接受回踩46.5-47.5后重新站回48.5，不接加速段。
3. 科技反弹恢复观察但暂不进入核心执行池；必须回踩不破并完成14:30后确认。
4. 恒瑞与港交所只有重新站回确认位后才能解除降级。

完整池已同步更新至 `prediction_tracking/watch_pool_full.csv` 和 `prediction_tracking/watch_pool_full.md`。
''',encoding='utf-8')

if __name__=='__main__':update_hk();update_pool();print('done')
