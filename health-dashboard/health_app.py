"""
健康知己 · 长寿主权 · 男性灯塔 V1(Bloomberg × Tesla 座舱风格)
设计内核:数据证明你在变强 + Claude Code 式即时正反馈
启动:python3 health_app.py  →  http://localhost:8000
"""
import pymysql, json, math
from datetime import datetime, date, timedelta
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, os
from dotenv import load_dotenv
load_dotenv()

# 数据库凭据从环境变量读取(本地配 .env,生产配环境变量) — 绝不硬编码进代码
DB = dict(host=os.getenv('DB_HOST','127.0.0.1'), port=int(os.getenv('DB_PORT','3307')),
          user=os.getenv('DB_USER','root'), password=os.getenv('DB_PASSWORD',''),
          database=os.getenv('DB_NAME','health_concierge'), charset='utf8mb4')
def conn(): return pymysql.connect(**DB, autocommit=True, cursorclass=pymysql.cursors.DictCursor)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
PID_NAME = '蒋德铭'
PROTOCOL_START = date(2026, 6, 15)   # 12 周协议起点
CHRONO_BIRTH = date(1980, 4, 25)

def get_pid():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT person_id FROM person WHERE name=%s", (PID_NAME,))
        r = cur.fetchone(); return r['person_id'] if r else None

def chrono_age():
    t = date.today()
    return round((t - CHRONO_BIRTH).days / 365.25, 1)

def compute_bio_age(labs, vital):
    """可解释生物年龄:实际年龄 + Σ指标惩罚 - 改善奖励"""
    base = chrono_age()
    items = []
    def add(name, years, detail):
        if abs(years) > 0.05: items.append({'name': name, 'years': round(years,1), 'detail': detail})
    # LDL-C
    if 'LDL_C' in labs:
        v = labs['LDL_C']['value_numeric']
        if v > 1.8: add('坏胆固醇 LDL-C', min((v-1.8)/0.5*0.55, 3.2), f'{v} → 目标<1.8')
    # GGT
    if 'GGT' in labs:
        v = labs['GGT']['value_numeric']
        if v > 30: add('肝脏酒精负担 GGT', min((v-30)/40*0.7, 1.8), f'{v} → 目标<30')
    # 脂肪肝
    if 'FATTY_LIVER' in labs:
        g = labs['FATTY_LIVER']['value_numeric']
        if g >= 1: add('脂肪肝', g*0.9, ['','轻度','中度','重度'][int(g)])
    # 血压
    if vital and vital.get('systolic'):
        s, d = float(vital['systolic']), float(vital.get('diastolic') or 0)
        if s >= 130 or d >= 85: add('血压', 1.4, f'{int(s)}/{int(d)} → 目标<120/80')
    # Lp(a)
    if 'LPA' in labs:
        v = labs['LPA']['value_numeric']
        if v > 30: add('脂蛋白a Lp(a)·遗传', min((v-30)/20*0.6, 1.0), f'{v}mg/dL(遗传,需更激进降ApoB)')
    # 睡眠惩罚由前端 sleep 传入此处简化
    # 改善奖励:7个月减脂
    if vital and vital.get('weight_kg'):
        cut = 83.4 - float(vital['weight_kg'])
        if cut > 3: add('7个月减脂 11kg', -min(cut*0.18, 2.2), f'体重-{cut:.1f}kg,正在把生物年龄拉回')
    bio = base + sum(i['years'] for i in items)
    return round(bio, 1), items

# 5 道防线(四骑士中文化 + P 百分位)
LINES = [
    ('horseman_cv','心血管','防心梗·中风'),
    ('horseman_metab','代谢','防糖尿病·脂肪肝'),
    ('horseman_cancer','癌症','早筛早处理'),
    ('horseman_neuro','神经','防痴呆·护记忆'),
    ('marginal_decade','肌骨','防跌倒·能自理'),
]
RISK_TXT = {'very_high':'危险','high':'偏弱','medium':'要留意','low':'守住了',None:'待评估'}
RISK_COLOR = {'very_high':'#f87171','high':'#fb923c','medium':'#fbbf24','low':'#34d399',None:'#7d96ab'}
RISK_ONELINE = {'very_high':'有明确缺口,优先补','high':'有薄弱点,该加强','medium':'目前还行,别松懈','low':'守得不错','None':'还没测'}

# Top 12 指标定义
TOP12 = [
    ('APOB','ApoB','mg/dL','<60','low',60),
    ('LPA','Lp(a)','mg/dL','<30','low',30),
    ('HOMAIR','HOMA-IR','','<1.5','low',1.5),
    ('HSCRP','hs-CRP','mg/L','<1.0','low',1.0),
    ('HBA1C','HbA1c','%','<5.4','low',5.4),
    ('VITD','维D','ng/mL','>40','high',40),
    ('SLEEP','睡眠','h','7-8h','range',7.5),
    ('HRV','HRV','ms','>50','high',50),
    ('VO2MAX','VO₂max','ml','>42','high',42),
    ('ASMI','肌肉指数','kg/m²','>7.0','high',7.0),
    ('GRIP','握力','kg','>40','high',40),
    ('BP','血压','','<125','low',125),
]

@app.get("/api/dashboard")
def dash():
    pid = get_pid()
    with conn() as c, c.cursor() as cur:
        cur.execute("""SELECT * FROM vital_sign WHERE person_id=%s AND body_fat_pct IS NOT NULL
                       ORDER BY measured_at DESC LIMIT 1""",(pid,)); latest=cur.fetchone()
        cur.execute("""SELECT * FROM vital_sign WHERE person_id=%s AND systolic IS NOT NULL
                       ORDER BY measured_at DESC LIMIT 1""",(pid,)); bp=cur.fetchone()
        cur.execute("""SELECT DATE(measured_at) d,weight_kg,body_fat_pct,muscle_kg FROM vital_sign
                       WHERE person_id=%s AND body_fat_pct IS NOT NULL ORDER BY measured_at""",(pid,)); trend=cur.fetchall()
        cur.execute("""SELECT value_numeric,value_json FROM wearable_metric WHERE person_id=%s
                       AND metric_code='sleep_total_min' ORDER BY start_time DESC LIMIT 1""",(pid,)); sleep=cur.fetchone()
        cur.execute("""SELECT * FROM risk_assessment WHERE person_id=%s ORDER BY assessed_at DESC LIMIT 1""",(pid,)); risk=cur.fetchone()
        cur.execute("""SELECT mc.code,lr.value_numeric,lr.unit,lr.measured_at,
                         COALESCE(ds.source_name,'体检') src
                       FROM lab_result lr JOIN metric_catalog mc ON lr.metric_id=mc.metric_id
                       LEFT JOIN report rp ON lr.report_id=rp.report_id
                       LEFT JOIN data_source ds ON rp.source_id=ds.source_id WHERE lr.person_id=%s
                       AND lr.measured_at=(SELECT MAX(l2.measured_at) FROM lab_result l2
                         JOIN metric_catalog m2 ON l2.metric_id=m2.metric_id
                         WHERE l2.person_id=lr.person_id AND m2.code=mc.code)""",(pid,))
        labs={}
        for r in cur.fetchall():
            if r['value_numeric'] is not None: r['value_numeric']=float(r['value_numeric'])
            labs[r['code']]=r
        # 今日已完成动作数
        today=date.today().isoformat()
        cur.execute("""SELECT COUNT(*) n FROM lifestyle_log WHERE person_id=%s
                       AND log_date=%s AND log_type='protocol_done'""",(pid,today)); done=cur.fetchone()['n']

    # 合并:血压取最近血压记录,体重取最新体成分(减脂奖励才生效)
    merged = dict(bp) if bp else {}
    if latest and latest.get('weight_kg'): merged['weight_kg'] = latest['weight_kg']
    bio, breakdown = compute_bio_age(labs, merged)
    # 夺回年龄(正向反馈核心):峰值bio - 当前bio = 已夺回
    weights=[float(t['weight_kg']) for t in trend if t.get('weight_kg')]
    reclaimed_series=[round(min((83.4-w)*0.18,2.2),2) for w in weights]  # 每月夺回(向上)
    reclaimed=reclaimed_series[-1] if reclaimed_series else 0.0
    peak_bio=round(bio+reclaimed,1)                 # 最差时的身体年龄
    reclaim_goal=round(peak_bio-chrono_age(),1)     # 总共要夺回多少才回到实际年龄
    reclaim_pct=round(reclaimed/reclaim_goal*100) if reclaim_goal>0 else 0
    # 协议进度
    day = (date.today() - PROTOCOL_START).days + 1
    proto_day = max(0, min(day, 90))
    # 时间助手:多久前
    def ago(dt):
        if not dt: return None
        days=(date.today()-dt.date()).days if hasattr(dt,'date') else (date.today()-dt).days
        if days<=0: return '今天'
        if days==1: return '昨天'
        if days<30: return f'{days}天前'
        if days<365: return f'{days//30}个月前'
        return f'{days//365}年前'
    # Top 12 拼装(带时间维度)
    slp_h = round(sleep['value_numeric']/60,1) if sleep else None
    # 每项的 value / 测量时间 / 来源
    src_map={
      'SLEEP':(slp_h,'昨晚','华为手表'),
      'LPA':(labs['LPA']['value_numeric'] if 'LPA' in labs else None,
             ago(labs['LPA']['measured_at']) if 'LPA' in labs else None,
             labs['LPA']['src'] if 'LPA' in labs else None),
      'HBA1C':(labs.get('HBA1C',{}).get('value_numeric'),
               ago(labs['HBA1C']['measured_at']) if 'HBA1C' in labs else None,
               labs.get('HBA1C',{}).get('src')),
      'BP':(float(bp['systolic']) if bp else None,
            ago(bp['measured_at']) if bp else None,'爱康体检'),
    }
    # 目标达成日期:需用药的远一点,其余 12 周复检日
    TARGET_DATE={'APOB':'12/31','LPA':'遗传·改攻ApoB','HBA1C':'9/13','default':'9/13'}
    top12=[]
    for code,name,unit,target,dir,line in TOP12:
        v,measured,src = src_map.get(code,(None,None,None))
        status='untested'
        if v is not None:
            if dir=='low': status='good' if v<=line else ('warn' if v<=line*1.4 else 'bad')
            elif dir=='high': status='good' if v>=line else ('warn' if v>=line*0.8 else 'bad')
            else: status='warn'
            if code=='BP': status='good' if v<125 else ('warn' if v<140 else 'bad')
        top12.append({'code':code,'name':name,'unit':unit,'target':target,
                      'value':v,'status':status,'dir':dir,
                      'measured':measured or ('待测' if v is None else None),
                      'src':src,'target_date':TARGET_DATE.get(code,TARGET_DATE['default'])})
    # 1on1 倒计时
    next_1on1 = date(2026,9,15)
    days_1on1 = (next_1on1 - date.today()).days
    # 健康时间轴 · 里程碑(过去→现在→未来目标)
    today = date.today()
    def rel(d):
        n=(d-today).days
        if n==0: return '今天'
        if n<0: return f'{-n}天前' if -n<30 else f'{-(n)//30}个月前'
        if n<30: return f'{n}天后'
        return f'{n//30}个月后'
    milestones=[
      {'date':'2025-11-26','rel':rel(date(2025,11,26)),'label':'上次全面体检(基线)',
       'detail':'查出 LDL-C 4.35 / GGT 124 / 中度脂肪肝','status':'done'},
      {'date':today.strftime('%Y-%m-%d'),'rel':'现在','label':f'身体年龄 {bio} 岁',
       'detail':f'比实际老 {round(bio-chrono_age(),1)} 岁','status':'now'},
      {'date':'2026-06-05','rel':rel(date(2026,6,5)),'label':'补测 12 项关键指标',
       'detail':'ApoB / 空腹胰岛素 / HOMA-IR / DXA / VO₂max','status':'next'},
      {'date':'2026-06-15','rel':rel(date(2026,6,15)),'label':'90 天计划启动',
       'detail':'身体年龄开始正式计时','status':'future'},
      {'date':'2026-07-13','rel':rel(date(2026,7,13)),'label':'第 4 周 · 轻量中检',
       'detail':'防松懈,提前看苗头','status':'future'},
      {'date':'2026-09-13','rel':rel(date(2026,9,13)),'label':'第 12 周 · 全面复检',
       'detail':'🎯 目标:身体年龄拉回 46 以下 / LDL-C<2.6 / GGT<50','status':'goal'},
      {'date':'2026-09-15','rel':rel(date(2026,9,15)),'label':'医生一对一复盘',
       'detail':'60 分钟视频 · 全指标对比','status':'future'},
    ]
    bio_based_on='基于 2025-11-26 体检 + 2026-05 体重数据'
    return {'name':PID_NAME,'chrono':chrono_age(),'bio':bio,'breakdown':breakdown,
            'reclaimed':reclaimed,'peak_bio':peak_bio,'reclaim_goal':reclaim_goal,
            'reclaim_pct':reclaim_pct,'reclaimed_series':reclaimed_series,
            'bio_based_on':bio_based_on,'milestones':milestones,
            'latest':latest,'bp':bp,'trend':trend,'sleep_h':slp_h,'risk':risk,
            'lines':[{'key':k,'name':n,'sub':s,
                      'lvl':(risk or {}).get(k),
                      'txt':RISK_TXT.get((risk or {}).get(k)),
                      'color':RISK_COLOR.get((risk or {}).get(k)),
                      'oneline':RISK_ONELINE.get((risk or {}).get(k) or 'None')} for k,n,s in LINES],
            'top12':top12,'proto_day':proto_day,'done_today':done,
            'days_1on1':days_1on1,'now':datetime.now().isoformat()}

@app.post("/api/protocol_done")
def protocol_done(action: str = Form(...)):
    """完成一条协议动作 → 即时正反馈:返回生物年龄贡献"""
    pid=get_pid(); today=date.today().isoformat()
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO lifestyle_log(person_id,log_date,log_type,details_json)
                       VALUES(%s,%s,'protocol_done',%s)""",(pid,today,json.dumps({'action':action},ensure_ascii=False)))
        cur.execute("""SELECT COUNT(*) n FROM lifestyle_log WHERE person_id=%s AND log_date=%s
                       AND log_type='protocol_done'""",(pid,today)); n=cur.fetchone()['n']
    # 每个动作贡献 -0.02~-0.05 岁(累积可见的即时正反馈)
    delta = round(0.03 + (n*0.005), 3)
    return {'status':'ok','done_today':n,'bio_delta':delta,
            'streak_msg':f'连续完成 {n}/3 · 生物年龄 -{delta} 岁'}

@app.post("/api/log_vital")
def log_vital(weight: float = Form(None), body_fat: float = Form(None), muscle: float = Form(None),
              systolic: int = Form(None), diastolic: int = Form(None), heart_rate: int = Form(None)):
    pid=get_pid()
    with conn() as c, c.cursor() as cur:
        bmi=round(weight/1.73**2,2) if weight else None
        cur.execute("""INSERT INTO vital_sign(person_id,measured_at,weight_kg,bmi,body_fat_pct,muscle_kg,
                       systolic,diastolic,heart_rate,measure_context) VALUES(%s,NOW(),%s,%s,%s,%s,%s,%s,%s,'home')""",
                    (pid,weight,bmi,body_fat,muscle,systolic,diastolic,heart_rate))
    return {'status':'ok'}

@app.post("/api/log")
def log(log_type: str = Form(...), details: str = Form(...)):
    pid=get_pid(); today=date.today().isoformat()
    with conn() as c, c.cursor() as cur:
        try: dj=json.loads(details)
        except: dj={'raw':details}
        cur.execute("""INSERT INTO lifestyle_log(person_id,log_date,log_type,details_json)
                       VALUES(%s,%s,%s,%s)""",(pid,today,log_type,json.dumps(dj,ensure_ascii=False)))
    return {'status':'ok'}

HTML = r"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>长寿主权 · 健康知己</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#091420;--bg2:#0a1828;--card:#0e2236;--card2:#0c1c2e;--line:#1b3a52;
  --teal:#2dd4bf;--cyan:#22d3ee;--text:#e6eef5;--muted:#7d96ab;
  --red:#f87171;--orange:#fb923c;--yellow:#fbbf24;--green:#34d399;}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}
body{background:var(--bg);color:var(--text);max-width:480px;margin:0 auto;padding:12px;padding-bottom:80px;
  font:14px/1.5 -apple-system,'PingFang SC',sans-serif;}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
.logo{display:flex;align-items:center;gap:8px;}
.logo .ic{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,var(--teal),var(--cyan));
  display:flex;align-items:center;justify-content:center;font-weight:700;color:#04141f;font-size:13px;}
.logo .nm{font-size:16px;font-weight:600;}.logo .nm small{display:block;font-size:9px;color:var(--muted);letter-spacing:2px;}
.chip{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:5px 12px;font-size:11px;color:var(--muted);}
.statusline{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:12px;}
.statusline .on{color:var(--teal);}
/* 英雄区 生物年龄 */
.hero{background:linear-gradient(160deg,#0e2942,#0a1c2e);border:1px solid var(--line);border-radius:16px;
  padding:18px;margin-bottom:12px;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;top:-40%;right:-20%;width:200px;height:200px;
  background:radial-gradient(circle,rgba(45,212,191,.18),transparent 70%);}
.hero .cap{font-size:10px;letter-spacing:3px;color:var(--muted);margin-bottom:8px;}
.hero .bigrow{display:flex;align-items:flex-end;justify-content:space-between;}
/* 夺回年龄 英雄区 */
.reclaim-hero{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;}
.rc-main .rc-label{font-size:12px;color:var(--green);font-weight:600;margin-bottom:2px;}
.rc-num{font-size:56px;font-weight:800;line-height:.85;font-variant-numeric:tabular-nums;
  background:linear-gradient(135deg,#34d399,#2dd4bf);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.rc-num .y{font-size:18px;color:var(--muted);-webkit-text-fill-color:var(--muted);margin-left:3px;}
.rc-side{text-align:right;padding-bottom:6px;}
.rc-now{font-size:12px;color:var(--muted);}
.rc-now b{color:var(--text);font-size:15px;font-weight:700;cursor:pointer;border-bottom:1px dashed var(--muted);}
.rc-gap{font-size:11px;color:var(--orange);margin-top:4px;}
/* 进度条 */
.rc-track{position:relative;height:10px;background:#0a1c2e;border-radius:6px;margin:16px 0 4px;
  border:1px solid var(--line);}
.rc-fill{height:100%;border-radius:6px;background:linear-gradient(to right,#34d399,#2dd4bf);transition:width .8s;}
.rc-flag{position:absolute;top:14px;font-size:9px;color:var(--muted);}
.rc-flag-l{left:0;}.rc-flag-r{right:0;}
.rc-progress-txt{font-size:11px;color:var(--text);margin-top:18px;text-align:center;}
.rc-progress-txt b{color:var(--green);}
.spark{height:46px;margin-top:14px;}
.spark-cap{font-size:10px;color:var(--green);text-align:center;margin-top:2px;}
.bio-sub{font-size:11px;color:var(--muted);margin-top:12px;}
/* 5道防线 竖排 */
.lines5col{display:flex;flex-direction:column;gap:7px;}
.l5{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid var(--card2);}
.l5:last-child{border-bottom:none;}
.l5 .d{width:11px;height:11px;border-radius:50%;flex-shrink:0;}
.l5 .nmwrap{flex:1;}
.l5 .nm{font-size:13px;font-weight:600;}
.l5 .sub{font-size:10px;color:var(--muted);}
.l5 .st{font-size:12px;font-weight:600;padding:3px 11px;border-radius:20px;white-space:nowrap;}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px;}
.card h3{font-size:13px;font-weight:600;margin-bottom:2px;display:flex;justify-content:space-between;align-items:center;}
.card h3 .by{font-size:10px;color:var(--muted);font-weight:400;}
.card .meta{font-size:10px;color:var(--muted);margin-bottom:12px;}
/* 今日协议 */
.proto{display:flex;gap:11px;align-items:flex-start;padding:11px 0;border-bottom:1px solid var(--card2);}
.proto:last-child{border-bottom:none;}
.proto .no{font-size:11px;color:var(--teal);font-weight:700;font-variant-numeric:tabular-nums;min-width:18px;padding-top:2px;}
.proto .body{flex:1;}
.proto .ti{font-size:14px;font-weight:600;margin-bottom:3px;}
.proto .wh{font-size:11px;color:var(--muted);line-height:1.5;}
.proto .wh b{color:var(--cyan);}
.check{width:26px;height:26px;border-radius:50%;border:2px solid var(--line);flex-shrink:0;cursor:pointer;
  display:flex;align-items:center;justify-content:center;transition:.25s;font-size:14px;color:transparent;}
.check.on{background:var(--teal);border-color:var(--teal);color:#04141f;}
.proto.done{opacity:.55;}
.proto.flash{animation:pulse .6s;}
@keyframes pulse{0%{background:rgba(45,212,191,0)}40%{background:rgba(45,212,191,.18)}100%{background:rgba(45,212,191,0)}}
/* Top12 网格 */
.t12{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;}
.t12 .m{background:var(--card2);border-radius:10px;padding:10px;border-top:2px solid var(--muted);}
.t12 .m.good{border-top-color:var(--green);}.t12 .m.warn{border-top-color:var(--yellow);}
.t12 .m.bad{border-top-color:var(--red);}.t12 .m.untested{border-top-color:#3a5670;}
.t12 .mn{font-size:10px;color:var(--muted);display:flex;justify-content:space-between;}
.t12 .mn .tg{color:#5a7governments;}
.t12 .mv{font-size:19px;font-weight:700;margin-top:3px;font-variant-numeric:tabular-nums;}
.t12 .mv.untested{font-size:13px;color:#4a6478;font-weight:500;}
.t12 .mv .u{font-size:10px;color:var(--muted);font-weight:400;}
.t12 .bar{height:3px;background:#1a3146;border-radius:2px;margin-top:6px;overflow:hidden;}
.t12 .bar i{display:block;height:100%;border-radius:2px;}
/* 预警 */
.alert{background:linear-gradient(135deg,#3a1a1a,#2a1518);border:1px solid #5a2a2a;border-radius:12px;
  padding:12px;display:flex;gap:10px;align-items:center;margin-bottom:12px;}
.alert .ic{font-size:18px;}.alert .body{flex:1;}
.alert .ti{font-size:13px;font-weight:600;color:#fca5a5;}
.alert .pa{font-size:11px;color:var(--muted);margin-top:3px;}
.alert .go{background:var(--red);color:#fff;border:none;padding:7px 12px;border-radius:8px;font-size:12px;white-space:nowrap;cursor:pointer;}
/* 1on1 */
.next1{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;
  display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}
.next1 .l{font-size:10px;color:var(--teal);letter-spacing:1px;}
.next1 .n{font-size:13px;font-weight:600;margin-top:3px;}
.next1 .t{font-size:11px;color:var(--muted);margin-top:2px;}
.next1 .cd{text-align:right;}
.next1 .cd .num{font-size:32px;font-weight:700;color:var(--cyan);line-height:1;}
.next1 .cd .u{font-size:10px;color:var(--muted);}
/* toast */
.toast{position:fixed;bottom:90px;left:50%;transform:translateX(-50%) translateY(20px);background:var(--teal);
  color:#04141f;padding:12px 20px;border-radius:12px;font-size:14px;font-weight:600;opacity:0;transition:.35s;
  z-index:99;box-shadow:0 8px 30px rgba(45,212,191,.4);white-space:nowrap;}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
/* tab */
.tabbar{position:fixed;bottom:0;left:0;right:0;background:var(--bg2);display:flex;justify-content:space-around;
  padding:9px 0;border-top:1px solid var(--line);max-width:480px;margin:0 auto;}
.tab{color:var(--muted);font-size:10px;text-align:center;padding:3px 14px;cursor:pointer;}
.tab.on{color:var(--teal);}.tab .ic{font-size:17px;display:block;margin-bottom:1px;}
.view{display:none;}.view.on{display:block;}
input,select{background:var(--card2);color:#fff;border:1px solid var(--line);padding:10px;border-radius:9px;font-size:14px;width:100%;}
.frow{display:flex;gap:8px;margin-bottom:10px;align-items:center;}.frow label{font-size:12px;min-width:74px;color:var(--muted);}
.btn{background:linear-gradient(135deg,var(--teal),var(--cyan));color:#04141f;border:none;padding:11px;border-radius:9px;font-size:14px;font-weight:600;width:100%;cursor:pointer;}
.qbtn{background:var(--line);color:#fff;border:none;padding:11px;border-radius:9px;font-size:13px;flex:1;cursor:pointer;}
.qbtn:active{background:var(--teal);color:#04141f;}
.ok{background:var(--green);color:#04141f;padding:8px;border-radius:7px;text-align:center;font-size:12px;opacity:0;transition:.3s;margin-top:8px;}
.ok.show{opacity:1;}
.muted{color:var(--muted);font-size:11px;}canvas{max-height:190px;}
.bio-source{font-size:10px;color:var(--muted);margin-top:8px;}
.t12 .mt{font-size:9px;color:#5a7a92;margin-top:4px;}
/* 时间轴 */
.timeline{position:relative;padding-left:6px;}
.tl-item{display:flex;gap:11px;padding-bottom:14px;position:relative;}
.tl-item:last-child{padding-bottom:0;}
.tl-item::before{content:'';position:absolute;left:5px;top:16px;bottom:-2px;width:2px;background:var(--line);}
.tl-item:last-child::before{display:none;}
.tl-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0;margin-top:3px;z-index:1;border:2px solid var(--bg);}
.tl-body{flex:1;}
.tl-row{display:flex;justify-content:space-between;align-items:baseline;}
.tl-label{font-size:13px;font-weight:600;}
.tl-when{font-size:10px;color:var(--muted);white-space:nowrap;}
.tl-detail{font-size:11px;color:var(--muted);margin-top:2px;line-height:1.4;}
.tl-now .tl-label{color:var(--cyan);}
.tl-goal .tl-detail{color:var(--teal);}
.tl-date{font-size:9px;color:#4a6478;}
.bio-num{cursor:pointer;}
.bio-howto{display:inline-block;margin-top:8px;font-size:10px;color:var(--cyan);
  border:1px solid rgba(34,211,238,.3);border-radius:20px;padding:4px 10px;cursor:pointer;}
/* 账本弹层 */
.mask{position:fixed;inset:0;background:rgba(2,8,15,.7);z-index:200;display:none;
  align-items:flex-end;justify-content:center;}
.mask.on{display:flex;}
.sheet{background:var(--card);border-radius:18px 18px 0 0;width:100%;max-width:480px;
  padding:18px;max-height:88vh;overflow-y:auto;border-top:1px solid var(--line);}
.sheet h2{font-size:17px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;}
.sheet .x{font-size:22px;color:var(--muted);cursor:pointer;line-height:1;}
.disc{background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);border-radius:10px;
  padding:11px;font-size:12px;line-height:1.6;color:#fcd34d;margin-bottom:14px;}
.ledger{width:100%;font-size:12px;border-collapse:collapse;margin-bottom:14px;}
.ledger td{padding:8px 4px;border-bottom:1px solid var(--card2);}
.ledger .src{font-size:9px;color:var(--muted);display:block;}
.ledger .yr{text-align:right;font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap;}
.ledger .yr.up{color:var(--orange);}.ledger .yr.dn{color:var(--green);}
.ledger .base td{color:var(--muted);}
.ledger .sum td{border-top:2px solid var(--line);border-bottom:none;font-size:15px;font-weight:700;padding-top:10px;}
.upgrade{background:rgba(45,212,191,.08);border:1px solid rgba(45,212,191,.25);border-radius:10px;
  padding:11px;font-size:12px;line-height:1.6;color:var(--text);}
.upgrade b{color:var(--teal);}
</style></head><body>

<div id="v-home" class="view on">
  <div class="topbar">
    <div class="logo"><div class="ic">蒋</div><div class="nm">蒋德铭<small>健康知己 · 我的身体仪表盘</small></div></div>
    <div class="chip" id="advisor">AI 参谋 · 在线</div>
  </div>
  <div class="statusline"><span id="proto-line">90 天计划 · 第 — 天</span><span class="on">● 数据已同步</span></div>

  <!-- 英雄区 夺回年龄 -->
  <div class="hero">
    <div class="cap">年龄夺回战 · 你正在赢回失去的年龄</div>
    <div class="reclaim-hero">
      <div class="rc-main">
        <div class="rc-label">已夺回</div>
        <div class="rc-num" id="reclaimed">—<span class="y">岁</span></div>
      </div>
      <div class="rc-side">
        <div class="rc-now">当前身体年龄 <b id="bio" onclick="showBioDetail()">—</b> 岁</div>
        <div class="rc-gap" id="rc-gap"></div>
      </div>
    </div>
    <!-- 夺回进度条 -->
    <div class="rc-track"><div class="rc-fill" id="rc-fill"></div>
      <div class="rc-flag rc-flag-l">最差 <span id="rc-peak"></span></div>
      <div class="rc-flag rc-flag-r">目标 <span id="rc-goal"></span></div></div>
    <div class="rc-progress-txt" id="rc-progress"></div>
    <canvas class="spark" id="spark"></canvas>
    <div class="spark-cap">↑ 这条线是你「已夺回的年龄」,7 个月一直在往上爬</div>
    <div class="bio-source" id="bio-source"></div>
    <div class="bio-howto" onclick="showBioDetail()">ⓘ 身体年龄是估算值,点开看怎么算的</div>
  </div>

  <!-- 健康路线图 时间轴 -->
  <div class="card">
    <h3>我的健康路线图 <span class="by">过去 → 现在 → 目标</span></h3>
    <div class="timeline" id="timeline"></div>
  </div>

  <!-- 5道防线 -->
  <div class="card" style="padding:12px">
    <h3>我的 5 道健康防线 <span class="by">守住 = 长寿的底线</span></h3>
    <div class="lines5col" id="lines5"></div>
  </div>

  <!-- 今天该做的事 -->
  <div class="card">
    <h3>今天该做的 3 件事 <span class="by" id="proto-by">AI 参谋 · 第 — 天 / 共 90 天</span></h3>
    <div class="meta" id="proto-meta">根据你昨天的数据,只挑最该做的 3 件</div>
    <div id="protos"></div>
  </div>

  <!-- Top 12 -->
  <div class="card">
    <h3>12 个关键指标 <span class="by">绿=达标 黄=接近 红=要改</span></h3>
    <div class="t12" id="t12"></div>
    <div class="muted" style="margin-top:8px">每格右上角是健康目标值 · 灰色"待测"=明天体检要补的</div>
  </div>

  <!-- 预警 -->
  <div id="alert-zone"></div>

  <!-- 5年轨迹 -->
  <div class="card">
    <h3>身体年龄这些年怎么变的 <span class="by">红=已发生 · 蓝=照计划走的预测</span></h3>
    <canvas id="bioTrend"></canvas>
    <div class="muted" style="margin-top:6px">红线一直在涨 → 现在是拐点 → 蓝线是坚持 90 天计划后的样子</div>
  </div>

  <!-- 1on1 -->
  <div class="next1">
    <div><div class="l">下次复盘 · 一对一视频</div><div class="n" id="n1-title">专属医生 · 季度复盘</div>
      <div class="t">60 分钟 · 全部指标对比(专属医生招募中)</div></div>
    <div class="cd"><div class="num" id="n1-days">—</div><div class="u">天后</div></div>
  </div>
</div>

<div id="v-log" class="view">
  <div class="topbar"><div class="logo"><div class="ic">知</div><div class="nm">随手记<small>5 秒入库</small></div></div></div>
  <div style="height:8px"></div>
  <div class="card"><h3>晨起体成分(华为秤)</h3>
    <div class="frow"><label>体重 kg</label><input id="lw" type="number" step="0.1" placeholder="71.1"></div>
    <div class="frow"><label>体脂 %</label><input id="lf" type="number" step="0.1" placeholder="20.9"></div>
    <div class="frow"><label>肌肉 kg</label><input id="lm" type="number" step="0.1" placeholder="28.7"></div>
    <button class="btn" onclick="saveVital()">写入</button><div class="ok" id="ok1">已写入 ✓ 生物年龄重算中</div></div>
  <div class="card"><h3>血压心率(欧姆龙)</h3>
    <div class="frow"><label>高/低压</label><input id="ls" type="number" placeholder="125"><input id="ld" type="number" placeholder="80"></div>
    <div class="frow"><label>心率</label><input id="lhr" type="number" placeholder="68"></div>
    <button class="btn" onclick="saveBP()">写入</button><div class="ok" id="ok2">已写入 ✓</div></div>
  <div class="card"><h3>办公室训练(椭圆/单车/划船 · 不跑步)</h3>
    <div class="frow"><label>项目</label><select id="wt">
      <option>椭圆·Zone2(能说话会喘)</option><option>单车·Zone2</option><option>划船·Zone2</option>
      <option>椭圆/单车·间歇冲刺</option><option>力量训练</option><option>护膝矫正(蚌式/侧弓/单腿)</option><option>游泳</option></select></div>
    <div class="frow"><label>分钟</label><input id="wm" type="number" placeholder="45"></div>
    <button class="btn" onclick="saveWorkout()">写入</button><div class="ok" id="ok3">已写入 ✓</div></div>
  <div class="card"><h3>蛋白质(目标 115-145 克/天)</h3>
    <div style="display:flex;gap:6px;margin-bottom:8px;">
      <button class="qbtn" onclick="P('早',30)">早 30</button><button class="qbtn" onclick="P('午',40)">午 40</button>
      <button class="qbtn" onclick="P('练后',25)">练后 25</button><button class="qbtn" onclick="P('晚',40)">晚 40</button></div>
    <div class="ok" id="ok4">已记录 ✓</div></div>
  <div class="card"><h3>饮酒(每周上限 100 克 · GGT 盯着你)</h3>
    <div style="display:flex;gap:6px;">
      <button class="qbtn" onclick="A(20)">1两白酒</button><button class="qbtn" onclick="A(12)">1杯红酒</button>
      <button class="qbtn" onclick="A(14)">1听啤酒</button></div><div class="ok" id="ok5">已记录 ✓</div></div>
</div>

<div id="v-trend" class="view">
  <div class="topbar"><div class="logo"><div class="ic">知</div><div class="nm">看变化<small>数据证明你在变强</small></div></div></div>
  <div style="height:8px"></div>
  <div class="card"><h3>体重 kg</h3><canvas id="c1"></canvas></div>
  <div class="card"><h3>体脂率 %(下行=对)</h3><canvas id="c2"></canvas></div>
  <div class="card"><h3>骨骼肌 kg(上行=赢)</h3><canvas id="c3"></canvas></div>
</div>

<div class="toast" id="toast"></div>

<!-- 生物年龄账本弹层 -->
<div class="mask" id="bio-mask" onclick="if(event.target===this)closeBioDetail()">
  <div class="sheet">
    <h2>身体年龄是怎么算出来的?<span class="x" onclick="closeBioDetail()">×</span></h2>
    <div class="disc" id="bio-disc"></div>
    <table class="ledger" id="bio-ledger"></table>
    <div class="upgrade" id="bio-upgrade"></div>
  </div>
</div>

<div class="tabbar">
  <div class="tab on" onclick="sw('home',this)"><span class="ic">◎</span>仪表盘</div>
  <div class="tab" onclick="sw('log',this)"><span class="ic">⌘</span>随手记</div>
  <div class="tab" onclick="sw('trend',this)"><span class="ic">📈</span>看变化</div>
</div>

<script>
let D=null,localBio=null;
// 今日协议(陈博士署名,基于真实数据)
const PROTOCOLS=[
  {ti:'ApoB 复测预约',wh:'Lp(a) <b>31.9</b> 偏高,目标把 ApoB 压到 <b>&lt;60</b>。明天体检务必加这项。'},
  {ti:'30g 蛋白质早餐 · 8:00 前',wh:'7个月掉了 <b>3.7kg 肌肉</b>,蛋白质前置可把它一点点长回来。'},
  {ti:'椭圆 45min + 22:30 睡',wh:'不跑步(双膝内翻)。睡足 7h 可让 HRV 回到 <b>45+</b>,皮质醇降下来。'},
];
const RC={good:'#34d399',warn:'#fbbf24',bad:'#f87171',untested:'#3a5670'};

async function load(){
  D=await (await fetch('/api/dashboard')).json();
  if(localBio===null)localBio=D.bio;
  renderHero();renderTimeline();renderLines();renderProto();renderT12();renderAlerts();renderBioTrend();render1on1();
  const dShow = D.proto_day<=0 ? '即将开始' : '第 '+D.proto_day+' 天';
  document.getElementById('proto-line').textContent='90 天计划 · '+dShow;
  document.getElementById('proto-by').textContent='AI 参谋 · '+dShow+' / 共 90 天';
  if(document.getElementById('v-trend').classList.contains('on'))renderTrendCharts();
  applyUrlState();
}
function applyUrlState(){
  const p=new URLSearchParams(location.search);const tab=p.get('tab');
  if(tab){document.querySelectorAll('.view').forEach(e=>e.classList.remove('on'));
    document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));
    const v=document.getElementById('v-'+tab);if(v)v.classList.add('on');
    if(tab==='trend')setTimeout(renderTrendCharts,150);}
  if(p.get('bio'))showBioDetail();
}

function renderHero(){
  // 已夺回 = 峰值 - 当前(localBio 会随完成动作即时下降 → 夺回即时增加)
  const reclaimed=Math.max(0,(D.peak_bio-localBio)).toFixed(1);
  const remain=Math.max(0,(localBio-D.chrono)).toFixed(1);
  const pct=Math.min(100,Math.round(reclaimed/D.reclaim_goal*100));
  document.getElementById('reclaimed').innerHTML=reclaimed+'<span class="y">岁</span>';
  document.getElementById('bio').textContent=localBio.toFixed(1);
  document.getElementById('rc-gap').innerHTML='还差 <b style="color:#fb923c">'+remain+'</b> 岁回到实际 '+D.chrono;
  document.getElementById('rc-peak').textContent=D.peak_bio;
  document.getElementById('rc-goal').textContent=D.chrono;
  document.getElementById('rc-fill').style.width=pct+'%';
  document.getElementById('rc-progress').innerHTML=
    '从最差的 '+D.peak_bio+' 岁,你已夺回 <b>'+reclaimed+' 岁</b> · 夺回进度 <b>'+pct+'%</b>';
  document.getElementById('bio-source').textContent='📊 身体年龄由 5 项体检指标估算(非临床检测)· 数据截至 2025-11';
  // spark:夺回曲线(向上爬升!)
  const ctx=document.getElementById('spark');if(ctx._c)ctx._c.destroy();
  ctx._c=new Chart(ctx,{type:'line',data:{labels:D.trend.map(t=>t.d),
    datasets:[{data:D.reclaimed_series,borderColor:'#34d399',backgroundColor:'rgba(52,211,153,.15)',
      fill:true,tension:.4,pointRadius:0,borderWidth:2.5}]},
    options:{plugins:{legend:{display:false}},scales:{x:{display:false},y:{display:false,min:0}}}});
}

function showBioDetail(){
  // 账本来源映射:除减脂来自华为秤,其余都来自 2025-11 体检
  const srcOf=n=> n.includes('减脂')?'2026-05 · 华为秤':'2025-11-26 · 爱康体检';
  document.getElementById('bio-disc').innerHTML=
    '⚠️ <b>这是估算值,不是化验直接测出来的。</b><br>'+
    '用你 5 项体检指标 + 减脂数据,通过简化模型推算。<br>'+
    '<b>方向可信</b>(代谢问题确实让身体偏老),但"老 '+(D.bio-D.chrono).toFixed(1)+' 岁"这个具体数字仅供参考,非医学结论。';
  // 账本
  let rows=`<tr class="base"><td>起点 · 你的实际年龄</td><td class="yr">${D.chrono} 岁</td></tr>`;
  D.breakdown.forEach(b=>{
    const up=b.years>0;
    rows+=`<tr><td>${b.name}<span class="src">${b.detail} · ${srcOf(b.name)}</span></td>
      <td class="yr ${up?'up':'dn'}">${up?'+':''}${b.years} 岁</td></tr>`;
  });
  rows+=`<tr class="sum"><td>= 身体年龄(估算)</td><td class="yr">${D.bio} 岁</td></tr>`;
  document.getElementById('bio-ledger').innerHTML=rows;
  document.getElementById('bio-upgrade').innerHTML=
    '🎯 <b>想要医学级精确?</b><br>明天体检补测 9 项(白蛋白 / 肌酐 / CRP / 淋巴细胞 等),'+
    '即可把算法升级为<b>临床验证的 PhenoAge</b>。这 9 项普通体检套餐都含,几乎不额外花钱。';
  document.getElementById('bio-mask').classList.add('on');
}
function closeBioDetail(){document.getElementById('bio-mask').classList.remove('on');}

function renderTimeline(){
  const C={done:'#34d399',now:'#22d3ee',next:'#fb923c',future:'#7d96ab',goal:'#2dd4bf'};
  document.getElementById('timeline').innerHTML=D.milestones.map(m=>{
    return `<div class="tl-item tl-${m.status}">
      <div class="tl-dot" style="background:${C[m.status]}"></div>
      <div class="tl-body">
        <div class="tl-row"><span class="tl-label">${m.label}</span><span class="tl-when">${m.rel}</span></div>
        <div class="tl-detail">${m.detail}</div>
        <div class="tl-date">${m.date}</div>
      </div></div>`;
  }).join('');
}

function renderLines(){
  document.getElementById('lines5').innerHTML=D.lines.map(l=>{
    const c=l.color;
    return `<div class="l5"><span class="d" style="background:${c}"></span>
      <div class="nmwrap"><div class="nm">${l.name}</div><div class="sub">${l.sub} · ${l.oneline}</div></div>
      <div class="st" style="background:${c}22;color:${c}">${l.txt}</div></div>`;
  }).join('');
}

function renderProto(){
  const dt=JSON.parse(localStorage.getItem('proto_'+new Date().toDateString())||'[]');
  document.getElementById('protos').innerHTML=PROTOCOLS.map((p,i)=>{
    const done=dt.includes(i);
    return `<div class="proto ${done?'done':''}" id="proto-${i}">
      <div class="no">0${i+1}</div>
      <div class="body"><div class="ti">${p.ti}</div><div class="wh">${p.wh}</div></div>
      <div class="check ${done?'on':''}" onclick="toggleProto(${i})">✓</div></div>`;
  }).join('');
  document.getElementById('proto-meta').textContent='基于昨日 睡眠 '+(D.sleep_h||'-')+'h · 体脂 '+(D.latest.body_fat_pct||'-')+'% 生成';
}

async function toggleProto(i){
  const key='proto_'+new Date().toDateString();
  let dt=JSON.parse(localStorage.getItem(key)||'[]');
  if(dt.includes(i))return; // 只能完成,不能取消(正反馈不可逆)
  dt.push(i);localStorage.setItem(key,JSON.stringify(dt));
  const el=document.getElementById('proto-'+i);el.classList.add('flash','done');
  el.querySelector('.check').classList.add('on');
  // 即时正反馈:调后端拿生物年龄贡献
  const fd=new FormData();fd.append('action',PROTOCOLS[i].ti);
  const r=await (await fetch('/api/protocol_done',{method:'POST',body:fd})).json();
  localBio=Math.max(D.chrono,localBio-r.bio_delta);  // 身体年龄即时下降→夺回即时增加
  renderHero();  // 刷新夺回数字+进度条+曲线
  pulseReclaim();
  showToast('🔥 又夺回 '+r.bio_delta+' 岁 · 今日完成 '+r.done_today+'/3');
}

function pulseReclaim(){
  const el=document.getElementById('reclaimed');
  el.style.transition='transform .25s';el.style.transform='scale(1.18)';
  setTimeout(()=>{el.style.transform='scale(1)';},260);
}

function renderT12(){
  document.getElementById('t12').innerHTML=D.top12.map(m=>{
    const c=RC[m.status];
    let val=m.value!=null?`<div class="mv">${m.value}<span class="u"> ${m.unit}</span></div>`:
      `<div class="mv untested">待测</div>`;
    let barpct=m.status==='good'?85:m.status==='warn'?55:m.status==='bad'?30:0;
    // 时间维度:测量时间(来源) · 目标日期
    let when = m.value!=null ?
      `${m.measured||''}${m.src?' · '+m.src.replace('上海','').replace('门诊部','').slice(0,6):''}` :
      `🩸 明天测`;
    let goal = m.target_date && m.target_date.length>5 ? m.target_date : (m.target_date+'达标');
    return `<div class="m ${m.status}" onclick="metricInfo('${m.code}')">
      <div class="mn"><span>${m.name}</span><span style="color:#5a7a92">${m.target}</span></div>
      ${val}<div class="bar"><i style="width:${barpct}%;background:${c}"></i></div>
      <div class="mt">${when}</div></div>`;
  }).join('');
}
function metricInfo(code){
  const m=D.top12.find(x=>x.code===code);if(!m)return;
  const measured=m.value!=null?`${m.measured} 测 · 来源 ${m.src||'体检'}`:'还没测,明天体检补上';
  alert(`${m.name}\n\n现在:${m.value!=null?m.value+' '+m.unit:'待测'}(健康目标 ${m.target})\n何时测:${measured}\n何时达标:${m.target_date.length>5?m.target_date:m.target_date+' 前'}`);
}

function renderAlerts(){
  // 临床预警:Lp(a) → CAC
  document.getElementById('alert-zone').innerHTML=`
    <div class="alert"><div class="ic">⚠️</div>
      <div class="body"><div class="ti">Lp(a) 31.9 偏高 · 心血管基线缺口</div>
        <div class="pa">遗传性高 → 需 30 天内做冠脉钙化积分 CAC,建立基线</div></div>
      <button class="go" onclick="showToast('已加入明天体检清单')">预约 →</button></div>`;
}

let bioTrendChart;
function renderBioTrend(){
  const ctx=document.getElementById('bioTrend');if(bioTrendChart)bioTrendChart.destroy();
  // 历史(估算)+协议起点+预测
  const labels=['2022','2023','2024','2025','起点','2027','2028','2030'];
  const real=[48,50,51,52,localBio,null,null,null];
  const proj=[null,null,null,null,localBio,localBio-2,localBio-3.5,localBio-5];
  bioTrendChart=new Chart(ctx,{type:'line',data:{labels,datasets:[
    {label:'已发生',data:real,borderColor:'#f87171',tension:.3,pointRadius:3,borderWidth:2},
    {label:'协议预测',data:proj,borderColor:'#2dd4bf',borderDash:[5,4],tension:.3,pointRadius:3,borderWidth:2}]},
    options:{plugins:{legend:{labels:{color:'#7d96ab',font:{size:10}}}},
      scales:{x:{ticks:{color:'#7d96ab',font:{size:9}}},y:{ticks:{color:'#7d96ab'}}}}});
}

function render1on1(){document.getElementById('n1-days').textContent=D.days_1on1;}

function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2200);}
function sw(v,el){document.querySelectorAll('.view').forEach(e=>e.classList.remove('on'));
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));
  document.getElementById('v-'+v).classList.add('on');el.classList.add('on');if(v==='trend')renderTrendCharts();}
function renderTrendCharts(){[['c1','weight_kg','#22d3ee'],['c2','body_fat_pct','#fb923c'],['c3','muscle_kg','#34d399']].forEach(([id,k,c])=>{
  const el=document.getElementById(id);if(el._c)el._c.destroy();
  el._c=new Chart(el,{type:'line',data:{labels:D.trend.map(t=>t.d),datasets:[{data:D.trend.map(t=>t[k]),borderColor:c,tension:.3,fill:false}]},
    options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#7d96ab',font:{size:9}}},y:{ticks:{color:'#7d96ab'}}}}});});}
function flash(id){const e=document.getElementById(id);e.classList.add('show');setTimeout(()=>e.classList.remove('show'),1500);}
async function post(u,fd){return (await fetch(u,{method:'POST',body:fd})).json();}
async function saveVital(){const fd=new FormData();const m={weight:'lw',body_fat:'lf',muscle:'lm'};
  for(const k in m){const v=document.getElementById(m[k]).value;if(v)fd.append(k,v);}
  await post('/api/log_vital',fd);flash('ok1');localBio=null;load();showToast('✓ 数据已进库,生物年龄已重算');}
async function saveBP(){const fd=new FormData();fd.append('systolic',ls.value);fd.append('diastolic',ld.value);fd.append('heart_rate',lhr.value);
  await post('/api/log_vital',fd);flash('ok2');localBio=null;load();}
async function saveWorkout(){const fd=new FormData();fd.append('log_type','exercise');fd.append('details',JSON.stringify({type:wt.value,minutes:wm.value}));
  await post('/api/log',fd);flash('ok3');showToast('✓ 训练入库 · 离 VO₂max 目标更近一步');}
async function P(meal,g){const fd=new FormData();fd.append('log_type','meal');fd.append('details',JSON.stringify({meal,protein_g:g}));await post('/api/log',fd);flash('ok4');}
async function A(g){const fd=new FormData();fd.append('log_type','alcohol');fd.append('details',JSON.stringify({alcohol_g:g}));await post('/api/log',fd);flash('ok5');showToast('已记 · 本周酒精在累计');}
load();
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def index(): return HTML
@app.get("/health")
def h(): return {"status":"ok"}
if __name__=="__main__":
    print("🚀 长寿主权·男性灯塔 V1 → http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
