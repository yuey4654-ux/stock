import csv
from pathlib import Path
from update_daily_hot_stocks import classify, build_conditions

ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'prediction_tracking'; R=ROOT/'reports'; DATE='2026-07-15'
POOL=P/'watch_pool_full.csv'; LOG=P/'daily_hot_stocks.csv'; POOL_MD=P/'watch_pool_full.md'; REPORT=R/f'市场热点新增观察池_{DATE}.md'
NEW=[
('300750','宁德时代','电池','373.00',2.47,13440215220.78),('600519','贵州茅台','白酒','1251.06',2.98,8922861367),
('603501','豪威集团','半导体/CIS','111.12',4.68,7232406659),('603083','剑桥科技','CPO/光模块','208.10',3.93,6929891340),
('601318','中国平安','保险/高股息','50.95',2.72,6486059071),('300759','康龙化成','CXO','40.30',9.13,6420926376.03),
('002484','江海股份','元件/电容器','87.86',1.94,5384740891.32),('600030','中信证券','证券','28.60',2.14,5304478301),
('000858','五粮液','白酒','76.40',4.09,4805702853.56),('002594','比亚迪','新能源车','91.76',1.75,4733650608.75),
('300033','同花顺','金融科技/软件','224.30',3.04,4392805996.33),('002558','巨人网络','游戏/AI应用','29.56',10.01,4256003147.5),
('002821','凯莱英','CXO','195.75',10.00,4240287772.98),('000807','云铝股份','工业金属/铝','26.10',4.48,4119220846.75)]

def read(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
 with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

pool=read(POOL);pf=list(pool[0]);by={r['代码']:r for r in pool};added=[]
for code,name,direction,close,pct,amount in NEW:
 if code in by:continue
 score=pct*3+min(amount/1e8,80); theme,level=classify(name,direction,pct,score);remind,down=build_conditions(close,pct,theme)
 row={'代码':code,'名称':name,'市场':'A股','方向':direction,'当前层级':level,'提醒条件':remind,'降级条件':down,'来源':f'全市场热点扩展-{DATE}','更新时间':DATE};pool.append(row);by[code]=row
 added.append({'日期':DATE,'代码':code,'名称':name,'市场':'A股','方向':direction,'分类':level,'热度来源':'东方财富全市场成交额前200去重','收盘价':close,'涨跌幅':f'{pct:.2f}%','成交额':str(amount),'热度评分':f'{score:.1f}','入池动作':'新增','记录备注':'新增热点只进入观察池，不自动升级为正式预测票'})
pool.sort(key=lambda r:(r['当前层级'],r['方向'],r['代码']));write(POOL,pool,pf)
log=read(LOG);lf=list(log[0]);keys={(r['日期'],r['代码']) for r in log};log += [r for r in added if (r['日期'],r['代码']) not in keys];log.sort(key=lambda r:(r['日期'],r['分类'],r['方向'],r['代码']));write(LOG,log,lf)
lines=['# 全量自选池','',f'更新日期：{DATE}','','| 代码 | 名称 | 市场 | 方向 | 层级 | 提醒条件 | 降级条件 |','| --- | --- | --- | --- | --- | --- | --- |']
for r in pool:lines.append(f"| {r['代码']} | {r['名称']} | {r['市场']} | {r['方向']} | {r['当前层级']} | {r['提醒条件']} | {r['降级条件']} |")
POOL_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
rows='\n'.join(f"| {r['分类']} | {r['方向']} | {r['代码']} | {r['名称']} | {r['收盘价']} | {r['涨跌幅']} | {r['提醒条件']} |" for r in [{**x,'提醒条件':by[x['代码']]['提醒条件']} for x in added])
REPORT.write_text(f'''# 市场热点新增观察池 {DATE}

## 处理结果

- 全市场成交额前200名与现有观察池去重后，新增 `{len(added)}` 只。
- 热点覆盖：电池与新能源车、白酒消费、证券保险、半导体与光模块、CXO、游戏/AI应用、工业金属。
- 所有新增票只进入观察层；涨停和单日大涨票不自动升级为正式规则票。

## 新增明细

| 层级 | 方向 | 代码 | 名称 | 收盘价 | 涨跌幅 | 提醒条件 |
| --- | --- | --- | --- | ---: | ---: | --- |
{rows}

## 分层重点

- 高热度但需冷却：康龙化成、凯莱英、巨人网络。前一日涨幅接近或达到10%，次日只看回踩，不追高。
- 科技观察：豪威集团、剑桥科技、江海股份、同花顺。必须等待板块扩散与尾盘确认。
- 稳健权重观察：宁德时代、贵州茅台、中国平安、中信证券、五粮液、比亚迪。用于判断指数与风险偏好，不等同于短线买点。
- 周期观察：云铝股份。需同时观察铝价、板块扩散和个股承接。

数据来源：[东方财富行情榜单](https://quote.eastmoney.com/center/gridlist.html)。
''',encoding='utf-8')
print('added',len(added),'pool',len(pool))
