import csv, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'prediction_tracking'; R=ROOT/'reports'; TARGET='2026/7/15'; ISO='2026-07-15'; PREDISO='2026-07-14'
A_LEDGER=P/'daily_predictions.csv'; H_LEDGER=P/'hk_daily_predictions.csv'

A_REV={
'600900':('28.68','+0.46%','是','否','命中','开28.40/高28.77/低28.25/收28.68。低点进入28.30-28.45承接区附近，尾盘站上28.60，稳健规则完整兑现。'),
'600938':('29.79','+0.91%','否','否','部分命中','开28.93/高29.95/低28.74/收29.79。收盘站上29.60且方向正确，但低点跌破29.00承接区下沿，未完整满足回踩不破，记部分命中。'),
'002223':('27.47','+2.12%','是','否','命中','开26.60/高27.70/低26.53/收27.47。低点位于26.40-26.70承接区，收盘站上27.00，康复器械条件观察兑现。'),
'601088':('43.69','+0.62%','是','否','命中','开42.98/高43.80/低42.88/收43.69。低点进入42.80-43.10承接区，尾盘站上43.50，高股息能源条件兑现。'),
'002422':('49.07','+1.18%','是','否','命中','开47.04/高52.72/低47.01/收49.07。低点进入46.50-47.50承接区，收盘站上48.50；虽有冲高回落，但计划低吸与收盘确认均满足。')}
H_REV={
'00941.HK':('79.000','-0.13%','否','否','部分命中','开79.10/高79.60/低78.95/收79.00。低点进入78.80-79.10承接区且未失效，但尾盘未站回79.50，只完成承接。'),
'00883.HK':('22.900','+0.44%','否','否','部分命中','开22.76/高23.10/低22.36/收22.90。收盘站上22.80，但低点短暂跌破22.40承接区下沿，标准路径不完整。'),
'09618.HK':('115.700','+1.67%','是','否','命中','开113.80/高116.20/低112.40/收115.70。低点进入111.50-112.50承接区，尾盘站上114.50，互联网消费条件兑现。'),
'01088.HK':('42.920','+1.47%','是','否','命中','开41.62/高42.92/低41.62/收42.92。低点进入41.50-41.80承接区，收盘站上42.30，能源扩散条件兑现。'),
'01093.HK':('8.430','+3.95%','否','否','部分命中','开8.11/高8.65/低8.11/收8.43。方向强且收盘站上8.22，但低点未进入7.95-8.05计划买点，未给标准低吸机会。')}

def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(rows)
def weight(r):
 k=r['预测类型'];return 1.5 if k.startswith('核心承接') else .8 if k.startswith(('弹性进攻','弹性观察')) else 1.0
def stats(rows):
 n=len(rows);h=sum(r['复盘结果']=='命中' for r in rows);p=sum(r['复盘结果']=='部分命中' for r in rows);m=sum(r['复盘结果']=='未命中' for r in rows);wt=sum(weight(r) for r in rows);wh=sum(weight(r) for r in rows if r['复盘结果']=='命中');wa=sum(weight(r)*(1 if r['复盘结果']=='命中' else .5 if r['复盘结果']=='部分命中' else 0) for r in rows)
 return {'总数':str(n),'命中':str(h),'部分命中':str(p),'未命中':str(m),'严格命中率':f'{h/n*100:.1f}%' if n else '0.0%','调整后命中率':f'{(h+.5*p)/n*100:.1f}%' if n else '0.0%','严格加权命中率':f'{wh/wt*100:.1f}%' if wt else '0.0%','调整后加权命中率':f'{wa/wt*100:.1f}%' if wt else '0.0%'}
def update_ledger(path,rev,source):
 rows=read(path);fields=list(rows[0]);seen=set()
 for r in rows:
  if r['目标日期']==TARGET and r['代码'] in rev:
   c,ch,t,i,res,note=rev[r['代码']];r.update({'收盘价':c,'涨跌幅':ch,'是否触发':t,'是否失效':i,'复盘结果':res,'复盘备注':note+f' 数据日期：{ISO}；来源：{source}。'});seen.add(r['代码'])
 if seen!=set(rev):raise RuntimeError(set(rev)-seen)
 write(path,rows,fields);return [r for r in rows if r['目标日期']==TARGET]
def cnt(rows,prefix):
 x=[r for r in rows if r['预测类型'].startswith(prefix)];return str(sum(r['复盘结果']=='命中' for r in x)),str(len(x))
def summary(rows,signal_field,signal,err,adj,report):
 core=cnt(rows,'核心承接');stable=cnt(rows,'稳健观察');elastic=cnt(rows,'弹性进攻');other=[r for r in rows if not r['预测类型'].startswith(('核心承接','稳健观察','弹性进攻'))]
 return {'目标日期':ISO,'预测日期':PREDISO,**stats(rows),'核心承接命中':core[0],'核心承接总数':core[1],'稳健观察命中':stable[0],'稳健观察总数':stable[1],'弹性进攻命中':elastic[0],'弹性进攻总数':elastic[1],'其他类型命中':str(sum(r['复盘结果']=='命中' for r in other)),'其他类型总数':str(len(other)),'最佳预测':'; '.join(r['名称'] for r in rows if r['复盘结果']=='命中') or '无','最差预测':'; '.join(r['名称'] for r in rows if r['复盘结果']=='未命中') or '无','主要误差':err,signal_field:signal,'下一步规则调整':adj,'报告文件':report}
def upsert(path,row):
 old=read(path);fields=list(old[0]);old=[r for r in old if r.get('目标日期')!=ISO];old.append({k:row.get(k,'') for k in fields});old.sort(key=lambda r:r.get('目标日期',''));write(path,old,fields);return old
def md(path,title,rows):
 fields=list(rows[0]);lines=[title,'',f'更新日期：{ISO}','','| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |'];lines += ['| '+' | '.join(r.get(k,'').replace('|','／') for k in fields)+' |' for r in rows];path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
def report(path,title,rows,full,rule,alert,market):
 table='\n'.join(f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['是否触发']} | {r['是否失效']} | {r['复盘结果']} | {r['复盘备注']} |" for r in rows)
 path.write_text(f'''# {title} {ISO}

## 策略调整提醒

{alert}

## 一句话结论

{market}全量{full['总数']}票为 `{full['命中']}命中 / {full['部分命中']}部分命中 / {full['未命中']}未命中`，严格命中率 `{full['严格命中率']}`、调整后命中率 `{full['调整后命中率']}`；规则票严格命中率 `{rule['严格命中率']}`、调整后加权命中率 `{rule['调整后加权命中率']}`。

## 新闻政策与美股影响

- 财联社重要快讯及国内政策／监管／产业新闻已前置核对：上半年经济与外贸数据、医药产业动态及中东局势是当天主要信息变量；未发现可以替代买点、承接区、失效位或“高开不追”的单一政策信号。
- 海外隔夜：7月14日道指微涨、标普500涨0.4%、纳指涨0.9%，通胀数据好于预期后10年美债收益率由约4.62%回落至4.58%；芯片与AI权重反弹，但中东冲突继续推高油价风险。美元、VIX随利率预期缓和而降温，风险偏好较前一日修复但并非全面无风险。
- 7月15日A股沪指跌0.29%、深成指跌0.97%、创业板指跌1.21%、科创50跌4.25%，两市成交约2.57万亿元。CRO、减肥药、青蒿素居前，医药形成扩散；半导体及科技硬件承接偏弱，前一日反攻未延续为全面主升。
- 逐票映射：医药扩散利好鱼跃医疗、科伦药业观察优先级，油价与高股息风格利好中国海油、中国神华、长江电力；但科伦冲高回落、中国海油跌破承接区下沿均说明新闻只决定热点顺序，不能放宽执行条件。
- 下一交易日仍维持1-2只正式规则票并优先稳健观察。科技/半导体只列条件观察，须等板块止跌扩散、个股回踩不破且14:30后确认；若美股科技再转弱、油价冲高回落或国内主线继续跌破承接，则继续降仓降数量。

来源：[财联社](https://www.cls.cn/)、[A股7月15日收评](https://www.sfccn.com/2026/7-15/xOMDE1MjBfMjE4MjkxOQ.html)、[美股7月14日收盘](https://apnews.com/article/eda3fd144dc773fc32cc6c69898d53b0)、[腾讯行情](https://qt.gtimg.cn/)。

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
{table}

## 主要误差与下一步

- 主要误差：方向判断总体较好，但正式票仍有“收盘站回、盘中却跌破承接区下沿”的路径瑕疵，不能追认严格命中。
- 下一步继续优先稳健承接；只有回踩不破且尾盘确认同时满足，才计正式执行信号。
''',encoding='utf-8')

A=update_ledger(A_LEDGER,A_REV,'腾讯A股行情');H=update_ledger(H_LEDGER,H_REV,'腾讯港股行情');AR=[r for r in A if not r['预测类型'].startswith('非规则')];HR=[r for r in H if not r['预测类型'].startswith('非规则')]
aerr='中国海油方向与收盘确认正确，但盘中跌破承接区下沿，正式规则只能部分命中。';aadj='触发原因：A股规则票严格命中率50.0%低于60%，但调整后加权命中率75.0%。建议：正式票仍维持1-2只，承接区下沿不得放宽。适用范围：A股稳健规则票。失效条件：连续两日严格命中率高于65%且无承接破位。'
herr='两只港股正式票都守住大结构，但中国移动未完成尾盘确认，中海油盘中跌破承接区下沿。';hadj='触发原因：港股规则票严格命中率0.0%、调整后加权命中率50.0%，低于阈值。建议：正式票维持1-2只并强化尾盘确认。适用范围：港股高股息与能源规则票。失效条件：连续两日调整后加权命中率高于65%且无盘中破位。'
af=upsert(P/'daily_review_summary.csv',summary(A,'策略提醒','是',aerr,aadj,f'reports/预测命中复盘_{ISO}.md'));ar=upsert(P/'rule_based_daily_summary.csv',summary(AR,'规则调整信号','是',aerr,aadj,f'reports/预测命中复盘_{ISO}.md'));md(P/'daily_review_summary.md','# 每日预测复盘全量汇总',af);md(P/'rule_based_daily_summary.md','# 每日预测复盘规则票汇总',ar)
subprocess.run(['python',str(ROOT/'tools'/'calc_hk_prediction_accuracy.py')],cwd=ROOT,check=True)
hr=upsert(P/'hk_rule_based_daily_summary.csv',summary(HR,'规则调整信号','是',herr,hadj,f'reports/港股预测命中复盘_{ISO}.md'));md(P/'hk_rule_based_daily_summary.md','# 港股每日预测复盘规则票汇总',hr)
report(R/f'预测命中复盘_{ISO}.md','预测命中复盘',A,stats(A),stats(AR),'- 已触发：A股规则票严格命中率50.0%低于60%；但调整后加权命中率75.0%，属于轻度提醒，继续保持1-2只正式票。','A股')
report(R/f'港股预测命中复盘_{ISO}.md','港股预测命中复盘',H,stats(H),stats(HR),'- 已触发：港股两只规则票均为部分命中，严格命中率0.0%、调整后加权命中率50.0%；继续压缩正式票并强化尾盘确认。','港股')
subprocess.run(['python',str(ROOT/'tools'/'calc_accuracy_since_inception.py')],cwd=ROOT,check=True)
print('A',stats(A),stats(AR));print('HK',stats(H),stats(HR))
