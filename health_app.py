"""
健康知己 · 长寿主权 · 男性灯塔 V1(Bloomberg × Tesla 座舱风格)
设计内核:数据证明你在变强 + Claude Code 式即时正反馈
启动:python3 health_app.py  →  http://localhost:8000
"""
import psycopg2, psycopg2.extras, psycopg2.pool, json, math
from datetime import datetime, date, timedelta
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, os
from contextlib import closing, contextmanager
from dotenv import load_dotenv
load_dotenv()

# 数据库凭据从环境变量读取(本地配 .env,生产配环境变量) — 绝不硬编码进代码
# keepalives_*:内网/VPN 会静默掐掉空闲 TCP 连接,连接池复用旧连接时会踩 "server closed
# the connection unexpectedly";开 TCP keepalive 让空闲连接保活,避免复用到僵死连接。
DB = dict(host=os.getenv('DB_HOST','127.0.0.1'), port=int(os.getenv('DB_PORT','35433')),
          user=os.getenv('DB_USER','postgres'), password=os.getenv('DB_PASSWORD',''),
          dbname=os.getenv('DB_NAME','health'),
          connect_timeout=5, keepalives=1, keepalives_idle=30,
          keepalives_interval=10, keepalives_count=5)

# 连接池:原来每个请求都新建连接(内网冷握手 ~150ms/次),dashboard 一次页面要打好几个
# 接口→握手成本翻几倍,这是"查询慢"的主因之一。改用常驻连接池复用热连接,握手成本一次性
# 摊掉。注意:这里只改连接管理,不动任何一条 SQL 语义,查询结果与之前完全一致。
_POOL = psycopg2.pool.ThreadedConnectionPool(
    1, 16, **DB, cursor_factory=psycopg2.extras.RealDictCursor)

@contextmanager
def conn():
    """从连接池借一个热连接;正常归还,出错则丢弃(防止把损坏连接还回池里污染下一次)。"""
    c = _POOL.getconn()
    try:
        c.autocommit = True
        yield c
    except Exception:
        _POOL.putconn(c, close=True)
        raise
    else:
        _POOL.putconn(c)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
PID_NAME = '蒋德铭'
PROTOCOL_START = date(2026, 6, 15)   # 12 周协议起点
CHRONO_BIRTH = date(1980, 4, 25)

def get_pid(pid=None):
    with conn() as c, c.cursor() as cur:
        if pid:
            cur.execute("SELECT person_id FROM person WHERE person_id=%s", (pid,))
        else:
            cur.execute("SELECT person_id FROM person WHERE name=%s", (PID_NAME,))
        r = cur.fetchone(); return r['person_id'] if r else None

def get_person(pid):
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT name,birth_date FROM person WHERE person_id=%s", (pid,))
        return cur.fetchone()

def chrono_age(birth=None):
    b = birth or CHRONO_BIRTH
    return round((date.today() - b).days / 365.25, 1)

def compute_bio_age(labs, vital, chrono=None):
    """可解释生物年龄:实际年龄 + Σ指标惩罚 - 改善奖励"""
    base = chrono if chrono is not None else chrono_age()
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
    # Lp(a):两次口径不同(mg/dL vs mg/L)存疑,不计入身体年龄,待 nmol/L 确认
    # 动脉硬化硬终点:颈动脉内中膜增厚 + 冠脉钙化(真实血管结构改变)
    if 'CIMT' in labs:
        v = labs['CIMT']['value_numeric']
        if v >= 1.0: add('动脉硬化·颈动脉+冠脉', min((v-1.0)/0.2*0.8+0.8, 2.5), f'颈动脉IMT {v}mm + 冠脉钙化,血管已硬化')
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
def dash(pid: int = None):
    with conn() as c, c.cursor() as cur:
        # person_id + name + birth_date 一次查出(原 get_pid + get_person 是两次独立连接的查询,
        # 这里合并为块内一条,结果与原来逐字段等价)。语义对齐:命中取真实 person_id,否则 None。
        if pid:
            cur.execute("SELECT person_id,name,birth_date FROM person WHERE person_id=%s",(pid,))
        else:
            cur.execute("SELECT person_id,name,birth_date FROM person WHERE name=%s",(PID_NAME,))
        person = cur.fetchone()
        pid = person['person_id'] if person else None          # 同 get_pid
        pname = person['name'] if person else PID_NAME          # 同 get_person 的回落
        chrono = chrono_age(person['birth_date'] if person else None)
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
        # 今日已完成动作数:改为从下方"近14天分组统计"(_hmap)里取当天值,省一次查询,结果等价
        # 当前在服用的药(长期处方)
        cur.execute("""SELECT drug_name,dose,frequency,reason,start_date FROM medication
                       WHERE person_id=%s AND status='active' ORDER BY start_date DESC NULLS LAST""",(pid,))
        meds=[{'name':m['drug_name'],'dose':m['dose'],'freq':m['frequency'],
               'why':m['reason'] or '','since':(m['start_date'].isoformat() if m['start_date'] else '')} for m in cur.fetchall()]
        # 吃药打卡:今日是否已服 + 连续天数
        cur.execute("""SELECT DISTINCT log_date FROM lifestyle_log WHERE person_id=%s
             AND log_type='med_taken' ORDER BY log_date DESC LIMIT 90""",(pid,))
        _mdset=set(r['log_date'] for r in cur.fetchall())
        med_taken_today=date.today() in _mdset
        med_streak=0; _mcd=date.today()
        if _mcd not in _mdset and (_mcd-timedelta(days=1)) in _mdset: _mcd=_mcd-timedelta(days=1)
        while _mcd in _mdset: med_streak+=1; _mcd=_mcd-timedelta(days=1)
        # 冠脉CTA血管示意图(数据驱动:仅当该 person 有 CTA 示意图)
        cur.execute("""SELECT findings_text, structured_data->>'schematic_svg' AS svg_path
                       FROM imaging_result WHERE person_id=%s AND modality LIKE '冠脉CTA%%'
                       AND structured_data->>'schematic_svg' IS NOT NULL
                       ORDER BY examined_at DESC LIMIT 1""",(pid,))
        _hc=cur.fetchone(); heart_cta=None
        if _hc and _hc.get('svg_path'):
            _root=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..'))
            _svg=None
            try:
                with open(os.path.join(_root,_hc['svg_path']),encoding='utf-8') as _f:_svg=_f.read()
            except Exception:_svg=None
            heart_cta={'findings':_hc['findings_text'],'svg':_svg}
        # 今天3件事 v2:微行动(此刻可做)+ 快变量真实反馈绑定
        if pname=='蒋德铭':
            # 自动验证"餐后走":分钟级步数滑窗,找最佳15分钟窗口步数
            cur.execute("""SELECT start_time st, value_numeric v FROM wearable_metric WHERE person_id=%s
                 AND metric_code='steps' AND start_time::date=%s ORDER BY start_time""",(pid,date.today()))
            _pts=[(r['st'],float(r['v'])) for r in cur.fetchall()]; _best=0
            for _i in range(len(_pts)):
                _s=0
                for _t,_v in _pts[_i:]:
                    if (_t-_pts[_i][0]).total_seconds()<=900: _s+=_v
                    else: break
                _best=max(_best,_s)
            _walked=_best>=1200
            _vtext=('✅ 手表已确认 · 最佳15分钟走了 %d 步'%_best if _walked else
                    ('⏳ 差一点 · 目前最佳15分钟 %d 步(目标1200)'%_best if _best>0 else '⏳ 还没看到你走路的数据'))
            protocols=[
              {'ti':'餐后立刻走 15 分钟','wh':'削血糖峰最有效。走完看代谢驾驶舱——血糖会真的更平。','fb':'glucose','line':'代谢','auto':True,'verified':_walked,'vtext':_vtext},
              {'ti':'今天滴酒不沾','wh':'GGT 97 还偏高。戒一晚,明早静息心率通常更低。','fb':'resting_hr','line':'肝·心血管'},
              {'ti':'30g 蛋白早餐 · 8点前','wh':'肌肉合成窗口。蛋白前置,长回偏低的骨骼肌。','fb':'protein','line':'肌骨'},
            ]
        else:
            cur.execute("""SELECT a.title ti,a.detail_md wh FROM intervention_action a
                 JOIN intervention_plan p ON p.plan_id=a.plan_id WHERE p.person_id=%s
                 ORDER BY a.action_id LIMIT 3""",(pid,))
            protocols=[{'ti':r['ti'],'wh':(r['wh'] or '')[:100],'fb':'generic','line':''} for r in cur.fetchall()]
            if not protocols: protocols=[{'ti':'完善你的健康数据','wh':'录入体检 / 连接设备,系统才能为你定制每日行动','fb':'generic','line':''}]
        # 连胜 streak:连续完成天数(怕断的心理)
        cur.execute("""SELECT DISTINCT log_date FROM lifestyle_log WHERE person_id=%s
             AND log_type='protocol_done' ORDER BY log_date DESC LIMIT 90""",(pid,))
        _dset=set(r['log_date'] for r in cur.fetchall())
        streak=0; _cd=date.today()
        if _cd not in _dset and (_cd-timedelta(days=1)) in _dset: _cd=_cd-timedelta(days=1)
        while _cd in _dset: streak+=1; _cd=_cd-timedelta(days=1)
        # 完成历史日历(近14天每天完成件数)——回答"已完成的任务哪里看"
        cur.execute("""SELECT log_date d, count(*) n FROM lifestyle_log WHERE person_id=%s
             AND log_type='protocol_done' AND log_date >= %s GROUP BY log_date""",(pid,(date.today()-timedelta(days=13))))
        _hmap={str(r['d']):r['n'] for r in cur.fetchall()}
        done_history=[{'d':str(date.today()-timedelta(days=13-i)),'n':_hmap.get(str(date.today()-timedelta(days=13-i)),0)} for i in range(14)]
        done=_hmap.get(str(date.today()),0)   # 今日已完成动作数(等价于原单独 COUNT 查询)
        # 预警:从该人的 ai_insight 动态取
        cur.execute("""SELECT title ti,content_md pa FROM ai_insight WHERE person_id=%s
             AND severity IN ('warning','urgent','critical') ORDER BY generated_at DESC LIMIT 1""",(pid,))
        _al=cur.fetchone(); alert=({'ti':_al['ti'],'pa':(_al['pa'] or '')[:170]} if _al else None)
        # 里程碑:从该人的 report 动态取
        cur.execute("""SELECT report_date::text rd,report_type rt,summary_md sm FROM report
             WHERE person_id=%s ORDER BY report_date""",(pid,)); reports=cur.fetchall()
        # 代谢驾驶舱:近14天每日活动聚合(步数/活动消耗/静息心率)
        cur.execute("""SELECT start_time::date d,
             round(avg(value_numeric) FILTER (WHERE metric_code='resting_hr')) rhr,
             round(sum(value_numeric) FILTER (WHERE metric_code='steps')) steps,
             round(sum(value_numeric) FILTER (WHERE metric_code='active_kcal')) kcal
           FROM wearable_metric WHERE person_id=%s AND metric_code IN ('resting_hr','steps','active_kcal')
             AND start_time >= %s GROUP BY d ORDER BY d""",(pid,(date.today()-timedelta(days=13))))
        metab_daily=[{'d':str(r['d']),
                      'rhr':float(r['rhr']) if r['rhr'] is not None else None,
                      'steps':int(r['steps']) if r['steps'] is not None else None,
                      'kcal':int(r['kcal']) if r['kcal'] is not None else None} for r in cur.fetchall()]
        # 近24h血糖逐点(CGM)
        cur.execute("""SELECT start_time,value_numeric FROM wearable_metric
           WHERE person_id=%s AND metric_code IN ('cgm_glucose','blood_glucose')
             AND start_time >= %s ORDER BY start_time""",(pid,(date.today()-timedelta(days=1))))
        gluc=[{'t':r['start_time'].strftime('%H:%M'),'v':float(r['value_numeric'])} for r in cur.fetchall()]

    # 合并:血压取最近血压记录,体重取最新体成分(减脂奖励才生效)
    merged = dict(bp) if bp else {}
    if latest and latest.get('weight_kg'): merged['weight_kg'] = latest['weight_kg']
    bio, breakdown = compute_bio_age(labs, merged, chrono)
    # 夺回年龄(正向反馈核心):峰值bio - 当前bio = 已夺回
    weights=[float(t['weight_kg']) for t in trend if t.get('weight_kg')]
    reclaimed_series=[round(min((83.4-w)*0.18,2.2),2) for w in weights]  # 每月夺回(向上)
    reclaimed=reclaimed_series[-1] if reclaimed_series else 0.0
    peak_bio=round(bio+reclaimed,1)                 # 最差时的身体年龄
    reclaim_goal=round(peak_bio-chrono,1)     # 总共要夺回多少才回到实际年龄
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
      'LPA':(((labs['LPA']['value_numeric']/10 if labs['LPA'].get('unit')=='mg/L' else labs['LPA']['value_numeric']) if 'LPA' in labs else None),
             ago(labs['LPA']['measured_at']) if 'LPA' in labs else None,
             labs['LPA']['src'] if 'LPA' in labs else None),
      'HBA1C':(labs.get('HBA1C',{}).get('value_numeric'),
               ago(labs['HBA1C']['measured_at']) if 'HBA1C' in labs else None,
               labs.get('HBA1C',{}).get('src')),
      'BP':(float(bp['systolic']) if bp else None,
            ago(bp['measured_at']) if bp else None,'爱康体检'),
    }
    # 目标达成日期:需用药的远一点,其余 12 周复检日
    TARGET_DATE={'APOB':'12/31','LPA':'待nmol/L确认','HBA1C':'9/13','default':'9/13'}
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
    if pname=='蒋德铭':
        milestones=[
          {'date':'2025-11-26','rel':rel(date(2025,11,26)),'label':'上次体检(基线)',
           'detail':'LDL-C 4.35 / GGT 124 / 中度脂肪肝','status':'done'},
          {'date':'2026-06-05','rel':rel(date(2026,6,5)),'label':'本次体检 · 7个月成果',
           'detail':'✅ 脂肪肝逆转 / LDL→3.54 / 血糖回正 / 减重10.7kg　⚠️ 查出颈动脉增厚+冠脉钙化','status':'done'},
          {'date':today.strftime('%Y-%m-%d'),'rel':'现在','label':f'身体年龄 {bio} 岁',
           'detail':f'比实际老 {round(bio-chrono,1)} 岁','status':'now'},
          {'date':'2026-06-22','rel':rel(date(2026,6,22)),'label':'中山医院·张峰主任门诊',
           'detail':'评估他汀 / 冠脉钙化积分CAC / Lp(a) 测 nmol/L','status':'next'},
          {'date':'2026-08-05','rel':rel(date(2026,8,5)),'label':'第 8 周复查',
           'detail':'看 LDL / GGT 下降幅度','status':'future'},
          {'date':'2026-09-13','rel':rel(date(2026,9,13)),'label':'第 12 周全面复检',
           'detail':'🎯 LDL-C<1.8 / GGT<60 / 内脏脂肪↓ / 肌肉↑','status':'goal'},
        ]
    else:
        milestones=[]
        for rp in reports:
            d0=date.fromisoformat(rp['rd'])
            milestones.append({'date':rp['rd'],'rel':rel(d0),
              'label':{'annual_physical':'体检','specialized':'专项检查','followup':'复查','self_assessment':'自评'}.get(rp['rt'],'检查记录'),
              'detail':((rp['sm'] or '')[:50] or '检查记录'),'status':'done'})
        milestones.append({'date':today.strftime('%Y-%m-%d'),'rel':'现在','label':f'身体年龄 {bio} 岁',
           'detail':f'比实际{"老" if bio>=chrono else "年轻"} {abs(round(bio-chrono,1))} 岁','status':'now'})
    if pname=='蒋德铭':
        bio_based_on='基于 2026-06-05 爱康体检 + 体成分数据'
    else:
        _rds=[rp['rd'] for rp in reports] if reports else []
        bio_based_on=(f'基于 {max(_rds)} 体检数据' if _rds else '基于已录入的体检数据')
    gvals=[x['v'] for x in gluc]
    # ===== M1 归因(诚实·当下时间):只说真实数据支撑的,样本小时如实标注 =====
    attribution=[]
    _sd=[d for d in metab_daily if d.get('steps')]
    _rhrs=[d['rhr'] for d in metab_daily if d.get('rhr')]
    if _sd:
        _mx=max(_sd,key=lambda d:d['steps'])
        if _mx['steps']>=3000 and _rhrs:
            attribution.append(f"📈 活动在爬升:步数最高到 {_mx['steps']} 步({_mx['d'][5:]})。活跃的日子,静息心率稳在 {int(min(_rhrs))}–{int(max(_rhrs))} 次(越低=心脏越省力)。")
    if gvals:
        _tir=round(100*sum(1 for v in gvals if 3.9<=v<=7.8)/len(gvals))
        attribution.append(f"🩸 今日血糖平均 {round(sum(gvals)/len(gvals),1)}、目标内 {_tir}%——刚开始记录,多戴几天就能看出哪顿饭让血糖飙。")
    _ndays=len([d for d in metab_daily if d.get('steps') or d.get('rhr')])
    attr_note=f"基于近 {_ndays} 天设备数据 · 初步观察,样本还小,规律会越积越准(不下因果结论)"
    metabolic={'fbg':labs.get('FBG',{}).get('value_numeric'),'hba1c':labs.get('HBA1C',{}).get('value_numeric'),
               'cgm_status':('CGM 已连接 · 实时血糖在更新' if gvals else ('CGM 传感器 6/4 到期已摘 · 贴新片可看实时血糖' if pname=='蒋德铭' else '未接入实时血糖(CGM)数据')),
               'daily':metab_daily,'sleep_h':slp_h,'glucose':gluc[-288:],
               'gluc_latest':gvals[-1] if gvals else None,
               'gluc_ok':((3.9<=gvals[-1]<=7.8) if gvals else None),
               'gluc_at':(gluc[-1]['t'] if gluc else None),
               'gluc_avg':round(sum(gvals)/len(gvals),1) if gvals else None,
               'gluc_tir':round(100*sum(1 for v in gvals if 3.9<=v<=7.8)/len(gvals)) if gvals else None,
               'attribution':attribution,'attr_note':attr_note,
               'rhr':next((d['rhr'] for d in reversed(metab_daily) if d and d.get('rhr')),None),
               'steps_today':next((d['steps'] for d in reversed(metab_daily) if d and d.get('steps')),None),
               'weight':(float(latest['weight_kg']) if latest and latest.get('weight_kg') else None),
               'body_fat':(float(latest['body_fat_pct']) if latest and latest.get('body_fat_pct') else None)}
    return {'name':pname,'chrono':chrono,'bio':bio,'breakdown':breakdown,
            'protocols':protocols,'alert':alert,'meds':meds,'heart_cta':heart_cta,
            'med_taken_today':med_taken_today,'med_streak':med_streak,
            'reclaimed':reclaimed,'peak_bio':peak_bio,'reclaim_goal':reclaim_goal,
            'reclaim_pct':reclaim_pct,'reclaimed_series':reclaimed_series,
            'bio_based_on':bio_based_on,'metabolic':metabolic,'milestones':milestones,
            'latest':latest,'bp':bp,'trend':trend,'sleep_h':slp_h,'risk':risk,
            'lines':[{'key':k,'name':n,'sub':s,
                      'lvl':(risk or {}).get(k),
                      'txt':RISK_TXT.get((risk or {}).get(k)) or '待评估',
                      'color':RISK_COLOR.get((risk or {}).get(k)) or RISK_COLOR[None],
                      'oneline':RISK_ONELINE.get((risk or {}).get(k) or 'None')} for k,n,s in LINES],
            'top12':top12,'proto_day':proto_day,'done_today':done,'streak':streak,'done_history':done_history,
            'days_1on1':days_1on1,'now':datetime.now().isoformat()}

@app.post("/api/protocol_done")
def protocol_done(action: str = Form(...), fb: str = Form('generic')):
    """完成一条微行动 → 真实快变量反馈(替代假岁数)+ 连胜"""
    pid=get_pid(); today=date.today().isoformat(); feedback=''
    with conn() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO lifestyle_log(person_id,log_date,log_type,details_json)
                       VALUES(%s,%s,'protocol_done',%s)""",(pid,today,json.dumps({'action':action,'fb':fb},ensure_ascii=False)))
        cur.execute("""SELECT COUNT(*) n FROM lifestyle_log WHERE person_id=%s AND log_date=%s
                       AND log_type='protocol_done'""",(pid,today)); n=cur.fetchone()['n']
        # 真实快变量反馈(不再编造岁数)
        if fb=='glucose':
            cur.execute("""SELECT round(avg(value_numeric),1) a,
                 round(100.0*count(*) FILTER (WHERE value_numeric BETWEEN 3.9 AND 7.8)/NULLIF(count(*),0)) tir,
                 round(max(value_numeric),1) mx FROM wearable_metric WHERE person_id=%s
                 AND metric_code IN ('cgm_glucose','blood_glucose') AND start_time::date=%s""",(pid,date.today()))
            g=cur.fetchone()
            feedback=(f"🩸 今天血糖均值 {g['a']}、目标内 {g['tir']}%、峰值才 {g['mx']} — 走路真在帮你削峰" if g and g['a'] else "🩸 走完了!贴上 CGM 就能看到这次把血糖压了多少")
        elif fb=='resting_hr':
            cur.execute("""SELECT round(avg(value_numeric)) r FROM wearable_metric WHERE person_id=%s
                 AND metric_code='resting_hr' AND start_time>=%s""",(pid,(date.today()-timedelta(days=3))))
            r=cur.fetchone()
            feedback=(f"❤️ 近3天静息心率约 {int(r['r'])} 次 · 戒酒次日通常更低,明早再看" if r and r['r'] else "❤️ 戒住了!明早静息心率会替你打分")
        elif fb=='protein':
            feedback="💪 记下了!蛋白前置=肌肉合成窗口开着,长回骨骼肌的关键一步"
        else:
            feedback="✅ 完成!坚持就是在给身体做功"
        cur.execute("""SELECT DISTINCT log_date FROM lifestyle_log WHERE person_id=%s
             AND log_type='protocol_done' ORDER BY log_date DESC LIMIT 90""",(pid,))
        _dset=set(rr['log_date'] for rr in cur.fetchall())
        streak=0; _cd=date.today()
        while _cd in _dset: streak+=1; _cd=_cd-timedelta(days=1)
    return {'status':'ok','done_today':n,'streak':streak,'feedback':feedback}

@app.post("/api/med_taken")
def med_taken():
    pid=get_pid(); today=date.today()
    with conn() as c, c.cursor() as cur:
        cur.execute("""SELECT COUNT(*) n FROM lifestyle_log WHERE person_id=%s
                       AND log_date=%s AND log_type='med_taken'""",(pid,today))
        if not cur.fetchone()['n']:
            cur.execute("""INSERT INTO lifestyle_log(person_id,log_date,log_type,details_json)
                           VALUES(%s,%s,'med_taken',%s)""",(pid,today,json.dumps({'src':'tap'},ensure_ascii=False)))
        cur.execute("""SELECT DISTINCT log_date FROM lifestyle_log WHERE person_id=%s
             AND log_type='med_taken' ORDER BY log_date DESC LIMIT 90""",(pid,))
        _s=set(r['log_date'] for r in cur.fetchall()); streak=0; cd=today
        while cd in _s: streak+=1; cd=cd-timedelta(days=1)
    return {'taken_today':True,'streak':streak}

@app.post("/api/log_vital")
def log_vital(weight: float = Form(None), body_fat: float = Form(None), muscle: float = Form(None),
              systolic: int = Form(None), diastolic: int = Form(None), heart_rate: int = Form(None)):
    pid=get_pid()
    with conn() as c, c.cursor() as cur:
        bmi=round(weight/1.73**2,2) if weight else None
        cur.execute("""INSERT INTO vital_sign(person_id,measured_at,weight_kg,bmi,body_fat_pct,muscle_kg,
                       systolic,diastolic,heart_rate,measure_context) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'home')""",
                    (pid,datetime.now(),weight,bmi,body_fat,muscle,systolic,diastolic,heart_rate))
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

# ============ 设备数据自动接入(苹果健康/快捷指令/Health Auto Export → PG) ============
INGEST_TOKEN = os.getenv('INGEST_TOKEN', 'jdm2026')
# 指标名 → (目标表, 字段/metric_code, 默认设备)。键尽量覆盖苹果健康常见命名
METRIC_MAP = {
  # —— 时序数据 → wearable_metric ——
  'heart_rate':('wearable','heart_rate','apple_watch'),
  'resting_heart_rate':('wearable','resting_hr','apple_watch'),
  'heart_rate_variability':('wearable','hrv','apple_watch'),'hrv':('wearable','hrv','apple_watch'),
  'blood_glucose':('wearable','cgm_glucose','cgm'),'cgm_glucose':('wearable','cgm_glucose','cgm'),'glucose':('wearable','cgm_glucose','cgm'),
  'step_count':('wearable','steps','apple_watch'),'steps':('wearable','steps','apple_watch'),
  'sleep_analysis':('wearable','sleep_total_min','apple_watch'),'sleep':('wearable','sleep_total_min','apple_watch'),
  'active_energy':('wearable','active_kcal','apple_watch'),
  'vo2_max':('wearable','vo2max','apple_watch'),'vo2max':('wearable','vo2max','apple_watch'),
  'oxygen_saturation':('wearable','spo2','huawei_watch'),'blood_oxygen':('wearable','spo2','huawei_watch'),
  'respiratory_rate':('wearable','resp_rate','apple_watch'),
  # —— 体征 → vital_sign 字段 ——
  'body_mass':('vital','weight_kg',None),'weight':('vital','weight_kg',None),
  'body_fat_percentage':('vital','body_fat_pct',None),'body_fat':('vital','body_fat_pct',None),
  'lean_body_mass':('vital','muscle_kg',None),'muscle':('vital','muscle_kg',None),
  'blood_pressure_systolic':('vital','systolic',None),'systolic':('vital','systolic',None),
  'blood_pressure_diastolic':('vital','diastolic',None),'diastolic':('vital','diastolic',None),
  'body_temperature':('vital','temperature_c',None),'waist':('vital','waist_cm',None),
  # —— Health Auto Export 专有命名别名 ——
  'weight_body_mass':('vital','weight_kg',None),
  'blood_oxygen_saturation':('wearable','spo2','apple_watch'),
  'walking_heart_rate_average':('wearable','heart_rate','apple_watch'),
  'apple_exercise_time':('wearable','exercise_min','apple_watch'),
  'walking_asymmetry_percentage':('wearable','walk_asymmetry','apple_watch'),
  'walking_speed':('wearable','walk_speed','apple_watch'),
  'walking_step_length':('wearable','step_length','apple_watch'),
  'walking_double_support_percentage':('wearable','double_support','apple_watch'),
  'flights_climbed':('wearable','flights','apple_watch'),
  'distance_walking_running':('wearable','distance_m','apple_watch'),
  'basal_energy_burned':('wearable','basal_kcal','apple_watch'),
  'apple_stand_time':('wearable','stand_min','apple_watch'),
}
def _parse_ts(s):
    if not s: return datetime.now()
    s=str(s).replace('Z','').replace('T',' ').strip()[:19]
    for f in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M','%Y-%m-%d'):
        try: return datetime.strptime(s,f)
        except: pass
    try: return datetime.fromisoformat(s)
    except: return datetime.now()

@app.post("/api/ingest")
async def ingest(req: Request):
    """统一设备数据入口。body: {token, samples:[{metric,value,unit,ts}]}"""
    raw = await req.body()
    try:
        with open('/tmp/ingest.log','a') as _f:
            _f.write(f"[{datetime.now()}] from={req.client.host if req.client else '?'} len={len(raw)} ct={req.headers.get('content-type')} query={dict(req.query_params)}\n{raw[:700]!r}\n---\n")
    except Exception: pass
    try: body = json.loads(raw) if raw else {}
    except Exception: return {'ok':False,'error':'body must be JSON'}
    token = (body.get('token') if isinstance(body,dict) else None) or req.headers.get('x-ingest-token') or req.query_params.get('token')
    if token != INGEST_TOKEN: return {'ok':False,'error':'invalid or missing token'}
    pid = get_pid()
    # 兼容 Health Auto Export 嵌套格式;睡眠点取 totalSleep(小时→分钟)
    if isinstance(body,dict) and isinstance(body.get('data'),dict) and 'metrics' in body['data']:
        samples=[]
        for met in body['data'].get('metrics',[]):
            nm=met.get('name'); un=met.get('units')
            for pt in (met.get('data') or []):
                if not isinstance(pt,dict): continue
                v=pt.get('qty', pt.get('Avg', pt.get('avg')))
                if v is None and pt.get('totalSleep') is not None: v=float(pt['totalSleep'])*60
                if v is not None: samples.append({'metric':nm,'value':v,'ts':pt.get('date'),'device':pt.get('source'),'unit':un})
    else:
        samples = body.get('samples') or body.get('data') or []
        if isinstance(samples,dict): samples=[samples]
    # —— 解析并分流到内存(为批量插入做准备)——
    recv=len(samples); ins=skip=0; errs=[]; unmapped=set()
    wear=[]; vitals=[]
    for s in samples:
        if not isinstance(s,dict): skip+=1; continue
        metric=str(s.get('metric') or s.get('type') or s.get('name') or '').lower().strip()
        m=METRIC_MAP.get(metric)
        if m is None: skip+=1; unmapped.add(metric); continue
        raw=s.get('value', s.get('qty', s.get('v')))
        if raw is None and s.get('totalSleep') is not None: raw=float(s['totalSleep'])*60
        if raw is None: skip+=1; continue
        try: val=float(raw)
        except Exception: skip+=1; continue
        ts=_parse_ts(s.get('ts') or s.get('start') or s.get('date') or s.get('time'))
        tgt,field,dev=m
        if tgt=='wearable': wear.append((s.get('device') or dev or 'apple_health', field, ts, val))
        else: vitals.append((field, ts, val))
    with conn() as c, c.cursor() as cur:
        # —— wearable:同批去重 + 一次查已存在 + 批量插入(避免逐条慢导致超时)——
        if wear:
            seen=set(); uniq=[]
            for dev,code,ts,val in wear:
                k=(code,ts)
                if k in seen: continue
                seen.add(k); uniq.append((dev,code,ts,val))
            codes=list({code for _,code,_,_ in uniq})
            cur.execute("SELECT metric_code,start_time FROM wearable_metric WHERE person_id=%s AND metric_code=ANY(%s)",(pid,codes))
            exist=set((r['metric_code'],r['start_time']) for r in cur.fetchall())
            todo=[(pid,dev,code,ts,val) for dev,code,ts,val in uniq if (code,ts) not in exist]
            if todo:
                psycopg2.extras.execute_values(cur,"INSERT INTO wearable_metric(person_id,device_type,metric_code,start_time,value_numeric) VALUES %s",todo,page_size=500)
                ins+=len(todo)
            skip+=len(wear)-len(todo)
        # —— vital:逐条 upsert(同时刻多字段合并,量小)——
        for field,ts,val in vitals:
            try:
                cur.execute("SELECT id FROM vital_sign WHERE person_id=%s AND measured_at=%s",(pid,ts))
                row=cur.fetchone()
                if row: cur.execute(f"UPDATE vital_sign SET {field}=%s WHERE id=%s",(val,row['id']))
                elif field=='weight_kg': cur.execute("INSERT INTO vital_sign(person_id,measured_at,weight_kg,bmi,measure_context) VALUES(%s,%s,%s,%s,'wearable')",(pid,ts,val,round(val/1.725**2,2)))
                else: cur.execute(f"INSERT INTO vital_sign(person_id,measured_at,{field},measure_context) VALUES(%s,%s,%s,'wearable')",(pid,ts,val))
                ins+=1
            except Exception as e: skip+=1; errs.append(str(e)[:50])
    try:
        names=sorted({(s.get('metric') or s.get('type') or s.get('name') or '') for s in samples if isinstance(s,dict)})
        with open('/tmp/ingest.log','a') as _f: _f.write(f"  >> 本次指标清单: {names}\n  >> 未识别(跳过): {sorted(unmapped)} | 入库={ins}\n")
    except Exception: pass
    return {'ok':True,'received':recv,'inserted':ins,'skipped':skip,'unmapped':sorted(unmapped),'errors':errs[:6]}

@app.get("/api/ingest/help")
def ingest_help():
    return {'endpoint':'POST /api/ingest','auth':'body.token 或 header X-Ingest-Token',
      'example':{'token':INGEST_TOKEN,'samples':[
        {'metric':'cgm_glucose','value':6.5,'unit':'mmol/L','ts':'2026-06-08 07:00:00'},
        {'metric':'heart_rate','value':65,'ts':'2026-06-08 07:00:00'},
        {'metric':'weight','value':70.6,'ts':'2026-06-08 07:00:00'},
        {'metric':'body_fat','value':20.8,'ts':'2026-06-08 07:00:00'}]},
      'supported_metrics':sorted(set(METRIC_MAP.keys()))}

# ============ 事件触发引擎(规则层:有事才推,不规律=不习惯化) ============
def build_events(pid=None, debug=False):
    pid = get_pid(pid); today = date.today(); evs=[]; checks=[]
    person = get_person(pid); pname = person['name'] if person else PID_NAME
    with conn() as c, c.cursor() as cur:
        # R1 静息心率:连续3天高于基线(警) / 创近两周新低(喜)
        cur.execute("""SELECT start_time::date d, round(avg(value_numeric)) v FROM wearable_metric
            WHERE person_id=%s AND metric_code='resting_hr' AND start_time>=%s GROUP BY d ORDER BY d""",
            (pid, today-timedelta(days=14)))
        rh=[(x['d'],float(x['v'])) for x in cur.fetchall()]
        if len(rh)>=5:
            base=sum(v for _,v in rh[:-3])/len(rh[:-3]); last3=rh[-3:]
            fired=all(v>base+1 for _,v in last3)
            checks.append({'rule':'R1a 静息连续偏高','fired':fired,
                'why':f'最近3天 {[int(v) for _,v in last3]} vs 基线 {round(base)}(需全部>基线+1)'})
            if fired:
                evs.append({'sev':'warn','emoji':'❤️','title':f'静息心率连续 3 天高于基线',
                    'detail':f'{", ".join(str(int(v)) for _,v in last3)} vs 基线 {round(base)} — 可能是恢复不足/饮酒/压力,今晚早睡'})
            prevmin=min(v for _,v in rh[:-1]); fired2=rh[-1][1]<prevmin
            checks.append({'rule':'R1b 静息创新低','fired':fired2,
                'why':f'今天 {int(rh[-1][1])} vs 此前最低 {int(prevmin)}(需更低)'})
            if fired2:
                evs.append({'sev':'good','emoji':'🏆','title':'静息心率创近两周新低',
                    'detail':f'今天 {int(rh[-1][1])},此前最低 {int(prevmin)} — 心脏更省力了,训练在起效'})
        else:
            checks.append({'rule':'R1 静息心率','fired':False,'why':f'数据只有 {len(rh)} 天,需≥5 天'})
        # R2 血糖:创记录以来最高峰(带时点,提示归因)
        cur.execute("""SELECT max(value_numeric) m FROM wearable_metric WHERE person_id=%s
            AND metric_code IN ('cgm_glucose','blood_glucose') AND start_time::date<%s""",(pid,today))
        r=cur.fetchone(); prevmax=float(r['m']) if r and r['m'] else None
        cur.execute("""SELECT value_numeric v,start_time t FROM wearable_metric WHERE person_id=%s
            AND metric_code IN ('cgm_glucose','blood_glucose') AND start_time::date=%s
            ORDER BY value_numeric DESC LIMIT 1""",(pid,today))
        r=cur.fetchone()
        if r and prevmax:
            fired=float(r['v'])>prevmax
            checks.append({'rule':'R2 血糖新高','fired':fired,
                'why':f'今日峰值 {float(r["v"]):.1f}({r["t"].strftime("%H:%M")}) vs 历史最高 {prevmax:.1f}'})
            if fired:
                evs.append({'sev':'warn','emoji':'🩸','title':f'血糖出现记录以来最高峰 {float(r["v"]):.1f}',
                    'detail':f'发生在 {r["t"].strftime("%H:%M")} — 回想那顿吃了什么?下次先菜后饭+餐后走15分钟'})
        else:
            checks.append({'rule':'R2 血糖新高','fired':False,'why':'今日或历史血糖数据不足'})
        # R3 连胜将断(18点后 + 今日未完成)
        cur.execute("""SELECT DISTINCT log_date FROM lifestyle_log WHERE person_id=%s
             AND log_type='protocol_done' ORDER BY log_date DESC LIMIT 90""",(pid,))
        dset=set(x['log_date'] for x in cur.fetchall())
        streak=0; cd=today-timedelta(days=1)
        while cd in dset: streak+=1; cd=cd-timedelta(days=1)
        hour=datetime.now().hour
        fired=streak>=2 and today not in dset and hour>=18
        checks.append({'rule':'R3 连胜将断','fired':fired,
            'why':f'昨止连胜 {streak} 天 / 今日完成:{"是" if today in dset else "否"} / 现在 {hour} 点(需≥18)'})
        if fired:
            evs.append({'sev':'warn','emoji':'⏰','title':f'🔥 连胜 {streak} 天,今晚要断了',
                'detail':'今天一件还没完成 — 24 点前补一件,别让纪录清零'})
        # R4 开奖倒计时(蒋德铭专属节点)
        if pname=='蒋德铭':
            for tgt,label,note in [
                (date(2026,6,22),'中山医院·张峰主任门诊','带:6-5体检报告+面诊清单+CGM报告,空腹前往'),
                (date(2026,8,5),'第8周复查·GGT开奖','戒酒坚持中,每多戒一天都在改善开奖结果')]:
                dleft=(tgt-today).days
                fired=dleft in (14,12,10,7,5,3,1,0)
                checks.append({'rule':f'R4 {label}','fired':fired,'why':f'还有 {dleft} 天(节点日:14/12/10/7/5/3/1/0)'})
                if fired:
                    evs.append({'sev':'info','emoji':'🎰',
                        'title':(label+('就是今天!' if dleft==0 else f'还有 {dleft} 天')),'detail':note})
    out={'events':evs,'count':len(evs)}
    if debug: out['checks']=checks
    return out

@app.get("/api/events")
def api_events(pid: int = None, debug: int = 0):
    return build_events(pid, debug=bool(debug))

# ============ 每日身体简报(WHOOP式:一个决策级分数 + 一句今天怎么过) ============
def build_briefing(pid=None):
    pid = get_pid(pid)
    person = get_person(pid); pname = person['name'] if person else PID_NAME
    today = date.today()
    with conn() as c, c.cursor() as cur:
        # 昨晚睡眠
        cur.execute("""SELECT value_numeric v FROM wearable_metric WHERE person_id=%s
            AND metric_code='sleep_total_min' AND start_time>=%s ORDER BY start_time DESC LIMIT 1""",
            (pid, today-timedelta(days=2)))
        r=cur.fetchone(); sleep_h = round(float(r['v'])/60,1) if r else None
        # 静息心率:最近一天 vs 前7天基线
        cur.execute("""SELECT start_time::date d, avg(value_numeric) v FROM wearable_metric
            WHERE person_id=%s AND metric_code='resting_hr' AND start_time>=%s GROUP BY d ORDER BY d""",
            (pid, today-timedelta(days=8)))
        rh=[(x['d'],float(x['v'])) for x in cur.fetchall()]
        rhr_last = round(rh[-1][1]) if rh else None
        rhr_base = round(sum(v for _,v in rh[:-1])/len(rh[:-1])) if len(rh)>1 else None
        # 昨日步数
        cur.execute("""SELECT round(sum(value_numeric)) s FROM wearable_metric WHERE person_id=%s
            AND metric_code='steps' AND start_time::date=%s""",(pid, today-timedelta(days=1)))
        r=cur.fetchone(); steps_y = int(r['s']) if r and r['s'] else None
        # 近24h血糖
        cur.execute("""SELECT count(*) n, round(avg(value_numeric),1) a,
             round(100.0*count(*) FILTER (WHERE value_numeric BETWEEN 3.9 AND 7.8)/NULLIF(count(*),0)) tir
             FROM wearable_metric WHERE person_id=%s AND metric_code IN ('cgm_glucose','blood_glucose')
             AND start_time>=%s""",(pid, today-timedelta(days=1)))
        g=cur.fetchone()
        gluc_tir = int(g['tir']) if g and g['n'] else None
        gluc_avg = float(g['a']) if g and g['n'] else None
        # 连胜
        cur.execute("""SELECT DISTINCT log_date FROM lifestyle_log WHERE person_id=%s
             AND log_type='protocol_done' ORDER BY log_date DESC LIMIT 90""",(pid,))
        _dset=set(rr['log_date'] for rr in cur.fetchall())
        streak=0; _cd=today
        if _cd not in _dset and (_cd-timedelta(days=1)) in _dset: _cd=_cd-timedelta(days=1)
        while _cd in _dset: streak+=1; _cd=_cd-timedelta(days=1)
    # —— 可解释评分:只用真实存在的信号,缺什么如实说 ——
    comp=[]
    if sleep_h is not None:
        s=100 if 7<=sleep_h<=8.5 else (75 if 6<=sleep_h<7 or 8.5<sleep_h<=9.5 else 50)
        comp.append({'k':'睡眠','s':s,'d':f'昨晚 {sleep_h}h'+('' if s==100 else ' 偏少' if sleep_h<7 else ' 偏多')})
    if gluc_tir is not None:
        s=100 if gluc_tir>=90 else (75 if gluc_tir>=70 else 50)
        comp.append({'k':'血糖','s':s,'d':f'TIR {gluc_tir}% · 均值 {gluc_avg}'})
    if rhr_last is not None and rhr_base:
        s=100 if rhr_last<=rhr_base else (70 if rhr_last<=rhr_base+3 else 45)
        comp.append({'k':'恢复','s':s,'d':f'静息 {rhr_last}(基线 {rhr_base})'+('↓ 好' if rhr_last<rhr_base else '' if rhr_last==rhr_base else '↑ 留意')})
    if steps_y is not None:
        s=100 if steps_y>=6000 else (70 if steps_y>=3000 else 45)
        comp.append({'k':'活动','s':s,'d':f'昨日 {steps_y} 步'})
    score = round(sum(x['s'] for x in comp)/len(comp)) if comp else None
    # —— 一句今天怎么过(规则:盯最弱项 + 连胜钩子)——
    if not comp:
        advice='还没有设备数据 · 连接手表/血糖仪后,每天早上给你一句"今天怎么过"'
    else:
        weakest=min(comp,key=lambda x:x['s'])
        if weakest['s']>=90:
            advice='状态在线:适合安排力量训练或重要决策日'
        elif weakest['k']=='睡眠':
            advice='昨晚没睡够:今天别排高强度训练,午后补 20 分钟,晚上 22:30 前睡'
        elif weakest['k']=='恢复':
            advice='静息心率偏高,身体在恢复:今天以走路为主,别硬练'
        elif weakest['k']=='活动':
            advice='昨天动得少:今天把"餐后走 15 分钟"补上,手表会自动确认'
        else:
            advice='血糖波动偏大:今天主食减半、先菜后饭、餐后走 15 分钟'
        if streak>0: advice += f'(🔥连胜 {streak} 天,别断)'
    events = build_events(pid).get('events',[])
    return {'name':pname,'date':today.strftime('%m/%d'),'weekday':'周'+'一二三四五六日'[today.weekday()],
            'score':score,'parts':comp,'advice':advice,'streak':streak,'events':events}

@app.get("/api/briefing")
def api_briefing(pid: int = None):
    return build_briefing(pid)

@app.get("/briefing", response_class=PlainTextResponse)
def briefing_text(pid: int = None):
    """纯文本简报:给 iOS 快捷指令每天定时拉取并弹通知"""
    b = build_briefing(pid)
    head = f"🧭 {b['date']} {b['weekday']} · {b['name']}"
    ev_lines = ''.join(f"\n⚡ {e['emoji']} {e['title']} — {e['detail']}" for e in b.get('events',[])[:2])
    if b['score'] is not None:
        head += f" · 状态 {b['score']}/100"
        body = ' | '.join(f"{p['k']} {p['d']}" for p in b['parts'])
        return f"{head}{ev_lines}\n{body}\n👉 {b['advice']}"
    return f"{head}{ev_lines}\n{b['advice']}"

# ============ 教练驾驶舱(真人教练 × 数据系统:今天该找谁、说什么) ============
def make_coach_draft(name, b, first_proto=None):
    """基于真实数据生成教练话术草稿(教练可改后发企微)"""
    sur = name[0] if name else ''
    lines=[]
    evs=b.get('events',[])
    warns=[e for e in evs if e['sev']=='warn']
    goods=[e for e in evs if e['sev']=='good']
    infos=[e for e in evs if e['sev']=='info']
    if not b.get('parts'):
        l=f"{name},你的方案我这边盯着呢。"
        if first_proto: l+=f"这周重点先把「{first_proto}」做起来,"
        l+="另外建议把手表/体脂秤连上,数据进来我才能实时帮你盯——有任何不舒服随时找我。"
        return l
    if warns:
        w=warns[0]
        lines.append(f"{name},我看到你{w['title']}({w['detail'].split('—')[0].strip()})——{w['detail'].split('—')[-1].strip() if '—' in w['detail'] else '今天注意调整'}。")
    else:
        weakest=min(b['parts'],key=lambda x:x['s']) if b['parts'] else None
        if weakest and weakest['s']<75:
            tips={'睡眠':'今晚 22:30 前睡,明早数据会还你一个好分数','活动':'今天把餐后 15 分钟走起来,手表会自动记','恢复':'今天以走路为主别硬练,身体在恢复','血糖':'今天主食减半、先菜后饭'}
            lines.append(f"{name},看到你{weakest['d']},{tips.get(weakest['k'],'今天注意调整')}。")
        else:
            lines.append(f"{name},今天状态 {b['score']} 分,数据都在线,保持。")
    if goods: lines.append(f"另外{goods[0]['title']}——{goods[0]['detail'].split('—')[-1].strip()},给你点赞👍")
    if infos: lines.append(f"提醒:{infos[0]['title']},{infos[0]['detail']}")
    if b.get('streak',0)>=2: lines.append(f"你已经连胜 {b['streak']} 天了,今天别断🔥")
    return ' '.join(lines)

@app.get("/api/coach")
def api_coach():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT person_id,name FROM person ORDER BY person_id")
        persons=[(r['person_id'],r['name']) for r in cur.fetchall()]
        protos={}
        cur.execute("""SELECT p.person_id,min(a.title) t FROM intervention_action a
            JOIN intervention_plan p ON p.plan_id=a.plan_id GROUP BY p.person_id""")
        for r in cur.fetchall(): protos[r['person_id']]=r['t']
    students=[]
    for pid,name in persons:
        b=build_briefing(pid)
        evs=b.get('events',[])
        warn=sum(1 for e in evs if e['sev']=='warn')
        if warn: pr,ptxt=0,'🔴 今天必须找'
        elif b['score'] is not None and b['score']<70: pr,ptxt=1,'🟡 建议关注'
        elif not b['parts']: pr,ptxt=2,'⚪ 无设备数据'
        else: pr,ptxt=3,'🟢 正常·轻触达'
        students.append({'pid':pid,'name':name,'score':b['score'],'parts':b['parts'],
            'events':evs,'streak':b['streak'],'priority':pr,'ptxt':ptxt,
            'draft':make_coach_draft(name,b,protos.get(pid))})
    students.sort(key=lambda s:s['priority'])
    return {'date':date.today().strftime('%m/%d'),'students':students}

COACH_HTML = r"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>教练驾驶舱 · 健康知己</title>
<style>
body{margin:0;background:#091420;color:#e8f0f7;font-family:-apple-system,"PingFang SC",sans-serif;padding:16px}
.hd{font-size:19px;font-weight:800;margin-bottom:3px}
.sub{font-size:12px;color:#7d96ab;margin-bottom:16px}
.stu{background:#0e2236;border:1px solid #1b3a52;border-radius:14px;padding:14px 16px;margin-bottom:14px}
.top{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.nm{font-size:16px;font-weight:800}
.sc{font-size:13px;color:#7d96ab}
.pr{margin-left:auto;font-size:11.5px;font-weight:700;padding:3px 10px;border-radius:8px;background:#0a1828;border:1px solid #1b3a52}
.ev{margin:6px 0;padding:7px 10px;background:rgba(0,0,0,.25);border-left:3px solid #fb923c;border-radius:0 8px 8px 0;font-size:12px;color:#c9d6e2}
.ev.good{border-color:#34d399}.ev.info{border-color:#22d3ee}
.chips{display:flex;gap:5px;flex-wrap:wrap;margin:7px 0}
.chip{font-size:10.5px;color:#9db8cc;background:#0a1828;border:1px solid #1b3a52;border-radius:7px;padding:2px 8px}
.draft{background:#0a1f30;border:1px dashed #2a4a66;border-radius:10px;padding:10px 12px;font-size:13px;line-height:1.65;color:#d5e3ef;margin-top:8px}
.dl{font-size:10.5px;color:#22d3ee;letter-spacing:1px;margin-bottom:4px}
.btns{display:flex;gap:8px;margin-top:8px}
.btn{flex:none;font-size:12px;font-weight:700;color:#091420;background:#22d3ee;border:none;border-radius:8px;padding:7px 14px;cursor:pointer}
.btn2{background:#1b3a52;color:#9db8cc}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#34d399;color:#06281b;font-size:13px;font-weight:700;padding:9px 18px;border-radius:10px;opacity:0;transition:.3s;pointer-events:none}
.toast.on{opacity:1}
</style></head><body>
<div class="hd">🎯 教练驾驶舱</div>
<div class="sub" id="sub">加载中…</div>
<div id="list"></div>
<div class="toast" id="toast">已复制,去企微粘贴发送</div>
<script>
async function load(){
  const d=await (await fetch('/api/coach')).json();
  document.getElementById('sub').textContent=d.date+' · 共 '+d.students.length+' 名学员 · 按今日优先级排序';
  document.getElementById('list').innerHTML=d.students.map(s=>{
    const evs=(s.events||[]).map(e=>'<div class="ev '+e.sev+'">⚡ '+e.emoji+' '+e.title+' — '+e.detail+'</div>').join('');
    const chips=(s.parts||[]).map(p=>'<span class="chip">'+p.k+' '+p.d+'</span>').join('');
    return '<div class="stu">'+
      '<div class="top"><span class="nm">'+s.name+'</span>'+
      (s.score!=null?'<span class="sc">状态 '+s.score+'/100'+(s.streak?' · 🔥'+s.streak+'天':'')+'</span>':'<span class="sc">无数据</span>')+
      '<span class="pr">'+s.ptxt+'</span></div>'+
      evs+(chips?'<div class="chips">'+chips+'</div>':'')+
      '<div class="draft"><div class="dl">✉️ 话术草稿(改一改再发,加你的人味)</div>'+s.draft+'</div>'+
      '<div class="btns"><button class="btn" onclick="cp(this)" data-t="'+s.draft.replace(/"/g,'&quot;')+'">复制话术</button>'+
      '<button class="btn btn2" onclick="location.href=\'/?pid='+s.pid+'\'">看他的仪表盘</button></div>'+
    '</div>';
  }).join('');
}
function cp(el){navigator.clipboard.writeText(el.dataset.t).then(()=>{
  const t=document.getElementById('toast');t.classList.add('on');setTimeout(()=>t.classList.remove('on'),1800);});}
load();
</script></body></html>"""

@app.get("/coach", response_class=HTMLResponse)
def coach_page(): return COACH_HTML

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
.spark{height:150px;margin-top:14px;}
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

  <!-- 每日身体简报(一个分数 + 一句今天怎么过) -->
  <div id="briefing" style="display:none;background:linear-gradient(135deg,#0e2840,#0c1c2e);border:1px solid #1b3a52;border-radius:14px;padding:14px 16px;margin-bottom:14px"></div>

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

  <!-- 今天该做的 3 件事(行为闭环发动机 · 完成即夺回年龄) -->
  <div class="card">
    <h3>今天该做的 3 件事 <span class="by" id="proto-by">AI 参谋 · 第 — 天 / 共 90 天</span></h3>
    <div class="meta" id="proto-meta">根据你昨天的数据,只挑最该做的 3 件</div>
    <div id="protos"></div>
  </div>

  <!-- 我的用药(长期处方 · 每日依从) -->
  <div class="card" id="meds-card" style="display:none">
    <h3>我的用药 <span class="by">长期处方 · 每天按时吃</span></h3>
    <div id="meds"></div>
  </div>

  <!-- 代谢驾驶舱(核心战场 · 行动的实时反馈) -->
  <div class="card">
    <h3>代谢驾驶舱 <span class="by">你的核心战场 · 血糖 / 活动 / 代谢</span></h3>
    <div id="metab"></div>
    <div id="gluc-wrap" style="display:none;height:140px;margin-top:12px"><canvas id="glucChart"></canvas></div>
    <div style="height:150px;margin-top:12px"><canvas id="metabChart"></canvas></div>
    <div class="muted" id="metab-note" style="margin-top:6px"></div>
    <div id="metab-attr"></div>
  </div>

  <!-- 预警(当前最紧迫 · 驱动行动) -->
  <div id="alert-zone"></div>

  <!-- 5道防线 -->
  <div class="card" style="padding:12px">
    <h3>我的 5 道健康防线 <span class="by">守住 = 长寿的底线</span></h3>
    <div class="lines5col" id="lines5"></div>
  </div>

  <!-- 健康路线图 时间轴 -->
  <div class="card">
    <h3>我的健康路线图 <span class="by">过去 → 现在 → 目标</span></h3>
    <div class="timeline" id="timeline"></div>
  </div>

  <!-- Top 12 -->
  <div class="card">
    <h3>12 个关键指标 <span class="by">绿=达标 黄=接近 红=要改</span></h3>
    <div class="t12" id="t12"></div>
    <div class="muted" style="margin-top:8px">每格右上角是健康目标值 · 灰色"待测"=明天体检要补的</div>
  </div>

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

<div class="mask" id="heart-mask" onclick="if(event.target===this)closeHeartDetail()">
  <div class="sheet">
    <h2>冠脉 CTA · 我的血管真实情况<span class="x" onclick="closeHeartDetail()">×</span></h2>
    <div id="heart-svg" style="width:100%;overflow:auto;background:#fff;border-radius:10px"></div>
    <div id="heart-find" style="margin-top:12px;font-size:12.5px;line-height:1.65;color:#9fb4c8"></div>
    <div class="disc" style="margin-top:12px">⚠️ 示意图为科普说明,非真实影像。下方为本人冠脉 CTA(2026-06-11)报告原文。复诊请以医生判读的原始影像为准。</div>
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
  {ti:'预约心内科 + 冠脉钙化积分(CAC)',wh:'体检见 <b>冠脉钙化</b> + 颈动脉增厚,需心内科评估他汀、做 CAC 量化风险。'},
  {ti:'戒酒 + 30g 蛋白质早餐',wh:'GGT <b>97</b> 仍偏高,戒酒可降;蛋白前置帮你长回偏低的肌肉。'},
  {ti:'椭圆 45min + 力量训练 + 22:30 睡',wh:'不跑步(双膝内翻)。力量训练降内脏脂肪(<b>10.5</b>偏高)、增肌。'},
];
const RC={good:'#34d399',warn:'#fbbf24',bad:'#f87171',untested:'#3a5670'};

const PID=new URLSearchParams(location.search).get('pid')||'';
async function load(){
  D=await (await fetch('/api/dashboard'+(PID?'?pid='+PID:''))).json();
  try{document.querySelector('.logo .ic').textContent=(D.name||'蒋')[0];
    document.querySelector('.logo .nm').firstChild.textContent=D.name||'';}catch(e){}
  renderBriefing();
  if(localBio===null)localBio=D.bio;
  renderHero();renderTimeline();renderLines();renderMetabolic();renderProto();renderMeds();renderT12();renderAlerts();renderBioTrend();render1on1();
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
function renderMeds(){
  const box=document.getElementById('meds-card'),el=document.getElementById('meds');
  const ms=(D&&D.meds)||[];
  if(!ms.length){box.style.display='none';return;}
  box.style.display='';
  el.innerHTML=ms.map(m=>`
    <div style="padding:11px 0;border-bottom:1px solid #16314a">
      <div style="font-size:15px">💊 <b style="color:#e8f2fb">${m.name}</b>
        <span style="color:#34d399;font-weight:700;margin-left:6px">${m.dose} · ${m.freq}</span></div>
      ${m.since?`<div style="color:#5a7a92;font-size:12px;margin-top:3px">${m.since} 起 · 长期服用</div>`:''}
      ${m.why?`<div title="${(m.why||'').replace(/"/g,'&quot;')}" style="color:#8aa6bf;font-size:12px;margin-top:5px;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${m.why}</div>`:''}
    </div>`).join('')+medCheckHtml();
}
function medCheckHtml(){
  const taken=D.med_taken_today, st=D.med_streak||0;
  if(taken) return `<div style="margin-top:12px;padding:12px;border-radius:10px;background:#0f2e22;border:1px solid #1d5c45;color:#34d399;font-size:13px;text-align:center">✓ 今天已服药${st>0?' · 已连续 <b>'+st+'</b> 天,保持住':''}</div>`;
  return `<div onclick="markMed()" style="margin-top:12px;padding:12px;border-radius:10px;background:#15324c;border:1px solid #2a5580;color:#7fd4f0;font-size:13px;text-align:center;cursor:pointer">● 今晚服药后,点这里打卡${st>0?' · 已连续 '+st+' 天,别断了':''}</div>`;
}
async function markMed(){
  try{await fetch('/api/med_taken',{method:'POST'});}catch(e){}
  if(typeof showToast==='function')showToast('✓ 已记录今天服药');
  load();
}

async function renderBriefing(){
  try{
    const b=await (await fetch('/api/briefing'+(PID?'?pid='+PID:''))).json();
    const el=document.getElementById('briefing'); if(!el)return;
    el.style.display='block';
    const sc=b.score, col=sc==null?'#7d96ab':(sc>=85?'#34d399':sc>=70?'#fbbf24':'#fb923c');
    el.innerHTML=
      '<div style="display:flex;align-items:center;gap:12px">'+
        (sc!=null?'<div style="font-size:34px;font-weight:900;color:'+col+';line-height:1">'+sc+'<span style="font-size:11px;color:#5a7a92"> /100</span></div>':'')+
        '<div style="flex:1;min-width:0">'+
          '<div style="font-size:11px;color:#7d96ab;letter-spacing:1px">🧭 今日身体简报 · '+b.date+' '+b.weekday+'</div>'+
          '<div style="font-size:13.5px;color:#e8f0f7;font-weight:600;margin-top:3px;line-height:1.5">'+b.advice+'</div>'+
        '</div></div>'+
      ((b.events&&b.events.length)?b.events.map(e=>{
        const ec=e.sev==='warn'?'#fb923c':e.sev==='good'?'#34d399':'#22d3ee';
        return '<div style="margin-top:9px;padding:8px 11px;background:rgba(0,0,0,.22);border-left:3px solid '+ec+';border-radius:0 8px 8px 0">'+
          '<div style="font-size:12.5px;font-weight:700;color:'+ec+'">⚡ '+e.emoji+' '+e.title+'</div>'+
          '<div style="font-size:11.5px;color:#9db8cc;margin-top:2px;line-height:1.5">'+e.detail+'</div></div>';
      }).join(''):'')+
      ((b.parts&&b.parts.length)?'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:9px">'+
        b.parts.map(p=>'<span style="font-size:11px;color:#9db8cc;background:#0a1828;border:1px solid #1b3a52;border-radius:8px;padding:3px 9px">'+p.k+' '+p.d+'</span>').join('')+'</div>':'');
  }catch(e){}
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
  document.getElementById('bio-source').textContent='📊 身体年龄由体检指标+血管影像估算(非临床检测)· 数据截至 2026-06';
  // spark:夺回曲线(向上爬升!)+ 完整坐标轴
  const ctx=document.getElementById('spark');if(ctx._c)ctx._c.destroy();
  const mlab=D.trend.map(t=>{const p=t.d.split('-');return p[1]?(+p[1])+'月':t.d;});
  ctx._c=new Chart(ctx,{type:'line',data:{labels:mlab,
    datasets:[{data:D.reclaimed_series,borderColor:'#34d399',backgroundColor:'rgba(52,211,153,.15)',
      fill:true,tension:.4,pointRadius:3,pointBackgroundColor:'#34d399',borderWidth:2.5}]},
    options:{maintainAspectRatio:false,plugins:{legend:{display:false},
      tooltip:{callbacks:{label:c=>'已夺回 '+c.parsed.y+' 岁'}}},
      scales:{
        x:{ticks:{color:'#7d96ab',font:{size:10}},grid:{color:'rgba(125,150,171,.1)'},
           title:{display:true,text:'月份',color:'#5a7a92',font:{size:10}}},
        y:{beginAtZero:true,ticks:{color:'#7d96ab',font:{size:10},callback:v=>v+'岁'},
           grid:{color:'rgba(125,150,171,.1)'},
           title:{display:true,text:'已夺回年龄',color:'#5a7a92',font:{size:10}}}}}});
}

function showBioDetail(){
  // 账本来源映射:除减脂来自华为秤,其余都来自 2025-11 体检
  const srcOf=n=> n.includes('减脂')?'2026-06 · 体脂秤':'2026-06-05 · 爱康体检';
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
function showHeartDetail(){
  if(!D.heart_cta) return;
  document.getElementById('heart-svg').innerHTML=D.heart_cta.svg||'<div style="color:#666;padding:20px">示意图暂不可用</div>';
  const s=document.querySelector('#heart-svg svg'); if(s){s.setAttribute('width','100%');s.removeAttribute('height');}
  document.getElementById('heart-find').textContent=D.heart_cta.findings||'';
  document.getElementById('heart-mask').classList.add('on');
}
function closeHeartDetail(){document.getElementById('heart-mask').classList.remove('on');}

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
    const hb=(l.name==='心血管'&&D.heart_cta)?`<div onclick="event.stopPropagation();showHeartDetail()" style="margin-top:5px;font-size:12px;color:#22d3ee;cursor:pointer">🫀 看冠脉 CTA 示意图 ›</div>`:'';
    return `<div class="l5"><span class="d" style="background:${c}"></span>
      <div class="nmwrap"><div class="nm">${l.name}</div><div class="sub">${l.sub} · ${l.oneline}</div>${hb}</div>
      <div class="st" style="background:${c}22;color:${c}">${l.txt}</div></div>`;
  }).join('');
}
function renderMetabolic(){
  const m=D.metabolic; if(!m) return;
  const fbgOk=m.fbg!=null&&m.fbg<6.1, hbOk=m.hba1c!=null&&m.hba1c<5.7;
  const cells=[['空腹血糖'+(fbgOk?' ✅':''),m.fbg],['糖化 HbA1c'+(hbOk?' ✅':''),m.hba1c],
    ['今日步数',m.steps_today],['静息心率',m.rhr],['睡眠 h',m.sleep_h],['体脂率 %',m.body_fat]];
  // ⏱ 此刻锚:流动的当下(血糖+今日步数+静息) — 解决"和当下时间的关系"
  const gOk=m.gluc_ok, gCol=gOk?'#34d399':(m.gluc_latest!=null?'#fb923c':'#7d96ab');
  const nowBar='<div style="background:linear-gradient(90deg,#0e2236,#0c1c2e);border:1px solid #1b3a52;border-radius:12px;padding:10px 12px;margin-bottom:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">'+
    '<span style="font-size:11px;color:#7d96ab">⏱ 此刻</span>'+
    (m.gluc_latest!=null?'<span style="font-size:20px;font-weight:800;color:'+gCol+'">'+m.gluc_latest+'</span><span style="font-size:11px;color:'+gCol+'">mmol/L'+(gOk?' · 理想区 ✓':'')+(m.gluc_at?' · '+m.gluc_at:'')+'</span>':'<span style="font-size:13px;color:#7d96ab">血糖待连接</span>')+
    '<span style="margin-left:auto;font-size:11px;color:#7d96ab">今天 '+(m.steps_today??'—')+' 步 · 静息 '+(m.rhr??'—')+'</span></div>';
  document.getElementById('metab').innerHTML=nowBar+'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'+
    cells.map(c=>'<div style="background:#0c1c2e;border:1px solid #1b3a52;border-radius:10px;padding:10px 6px;text-align:center">'+
      '<div style="font-size:20px;font-weight:700;color:#e8f0f7">'+(c[1]??'—')+'</div>'+
      '<div style="font-size:11px;color:#7d96ab;margin-top:3px">'+c[0]+'</div></div>').join('')+'</div>';
  // 🔗 归因洞察(行为→指标,诚实初步)
  const attrEl=document.getElementById('metab-attr'), aa=m.attribution||[];
  if(attrEl) attrEl.innerHTML=aa.length?('<div style="margin-top:12px;border-top:1px solid #1b3a52;padding-top:10px">'+
    '<div style="font-size:12px;color:#22d3ee;font-weight:600;margin-bottom:6px">🔗 行为 → 指标 · 系统初步归因</div>'+
    aa.map(x=>'<div style="font-size:12.5px;color:#c9d6e2;line-height:1.55;margin-bottom:5px">'+x+'</div>').join('')+
    '<div style="font-size:10px;color:#5a7a92;margin-top:4px">'+(m.attr_note||'')+'</div></div>'):'';
  const gl=m.glucose||[], gw=document.getElementById('gluc-wrap');
  if(gl.length){ gw.style.display='block';
    document.getElementById('metab-note').textContent='🩸 实时血糖 '+(m.gluc_latest??'—')+' mmol/L · 今日平均 '+(m.gluc_avg??'—')+' · TIR '+(m.gluc_tir??'—')+'%(目标>70%)';
    const gc=document.getElementById('glucChart'); if(gc._c)gc._c.destroy();
    gc._c=new Chart(gc,{type:'line',data:{labels:gl.map(x=>x.t),
      datasets:[{data:gl.map(x=>x.v),borderColor:'#22d3ee',backgroundColor:'rgba(34,211,238,.12)',fill:true,tension:.3,pointRadius:0,borderWidth:2}]},
      options:{maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y+' mmol/L'}}},
        scales:{x:{ticks:{color:'#7d96ab',font:{size:8},maxTicksLimit:6},grid:{display:false}},
          y:{min:3,max:11,ticks:{color:'#7d96ab',font:{size:9}},grid:{color:'rgba(125,150,171,.1)'},
             title:{display:true,text:'血糖 mmol/L · 今日实时曲线',color:'#5a7a92',font:{size:9}}}}}});
  } else { gw.style.display='none'; document.getElementById('metab-note').textContent='🩸 '+(m.cgm_status||''); }
  const d=m.daily||[], ctx=document.getElementById('metabChart'); if(!ctx)return; if(ctx._c)ctx._c.destroy();
  ctx._c=new Chart(ctx,{type:'bar',data:{labels:d.map(x=>{const p=x.d.split('-');return p[1]+'/'+p[2];}),
    datasets:[{data:d.map(x=>x.steps||0),backgroundColor:'rgba(52,211,153,.55)',borderRadius:4}]},
    options:{maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>'步数 '+c.parsed.y}}},
    scales:{x:{ticks:{color:'#7d96ab',font:{size:9}},grid:{display:false}},
      y:{beginAtZero:true,ticks:{color:'#7d96ab',font:{size:9}},grid:{color:'rgba(125,150,171,.1)'},
         title:{display:true,text:'近14天每日步数',color:'#5a7a92',font:{size:9}}}}}});
}

function renderProto(){
  const dt=JSON.parse(localStorage.getItem('proto_'+new Date().toDateString())||'[]');
  document.getElementById('protos').innerHTML=(D.protocols||[]).map((p,i)=>{
    const auto=p.auto, done=auto?p.verified:dt.includes(i);
    const tag=p.line?`<span style="font-size:10px;color:#22d3ee;background:rgba(34,211,238,.12);padding:1px 6px;border-radius:6px;margin-left:6px">守 ${p.line}</span>`:'';
    const badge=auto?'<span style="font-size:9px;color:#34d399;margin-left:5px">⌚自动验证</span>':'';
    const sub=auto?(p.vtext||p.wh):p.wh;
    const chk=auto
      ?`<div class="check ${p.verified?'on':''}" style="cursor:default" title="手表自动验证,不用手动打卡">${p.verified?'✓':'⏳'}</div>`
      :`<div class="check ${done?'on':''}" onclick="toggleProto(${i})">✓</div>`;
    return `<div class="proto ${done?'done':''}" id="proto-${i}">
      <div class="no">0${i+1}</div>
      <div class="body"><div class="ti">${p.ti}${tag}${badge}</div><div class="wh">${sub}</div></div>
      ${chk}</div>`;
  }).join('');
  const st=D.streak||0, hist=D.done_history||[];
  const cal=hist.map(h=>`<span title="${h.d}: 完成${h.n}件" style="display:inline-block;width:13px;height:13px;border-radius:3px;background:${h.n>=3?'#34d399':h.n>0?'#fbbf24':'#21364a'}"></span>`).join('');
  document.getElementById('proto-meta').innerHTML=
    (st>0?'🔥 <b style="color:#fb923c">连胜 '+st+' 天</b>　':'')+
    '<span style="color:#7d96ab">近14天:</span> <span style="display:inline-flex;gap:3px;vertical-align:middle;margin-left:3px">'+cal+'</span>'+
    '<span style="color:#5a7a92;font-size:10px;margin-left:6px">绿=全完成 黄=部分</span>';
}

async function toggleProto(i){
  const key='proto_'+new Date().toDateString();
  let dt=JSON.parse(localStorage.getItem(key)||'[]');
  if(dt.includes(i))return; // 只能完成,不能取消(正反馈不可逆)
  dt.push(i);localStorage.setItem(key,JSON.stringify(dt));
  const el=document.getElementById('proto-'+i);el.classList.add('flash','done');
  el.querySelector('.check').classList.add('on');
  if(navigator.vibrate)navigator.vibrate(60);  // 触觉强刺激
  // 真实快变量反馈(替代假夺回岁数)+ 连胜
  const p=D.protocols[i]||{};
  const fd=new FormData();fd.append('action',p.ti||'');fd.append('fb',p.fb||'generic');
  const r=await (await fetch('/api/protocol_done',{method:'POST',body:fd})).json();
  D.streak=r.streak;
  if(D.done_history&&D.done_history.length){const t=D.done_history[D.done_history.length-1];if(t)t.n=r.done_today;}
  renderProto();
  pulseReclaim();
  showToast((r.feedback||'✅ 完成')+(r.streak?' · 🔥连胜'+r.streak+'天':''));
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
  const a=D.alert;
  document.getElementById('alert-zone').innerHTML=a?`
    <div class="alert"><div class="ic">⚠️</div>
      <div class="body"><div class="ti">${a.ti}</div>
        <div class="pa">${a.pa||''}</div></div></div>`:'';
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
      scales:{
        x:{ticks:{color:'#7d96ab',font:{size:9}},grid:{color:'rgba(125,150,171,.1)'},
           title:{display:true,text:'年份',color:'#5a7a92',font:{size:10}}},
        y:{ticks:{color:'#7d96ab',callback:v=>v+'岁'},grid:{color:'rgba(125,150,171,.1)'},
           title:{display:true,text:'身体年龄',color:'#5a7a92',font:{size:10}}}}}});
}

function render1on1(){document.getElementById('n1-days').textContent=D.days_1on1;}

function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2200);}
function sw(v,el){document.querySelectorAll('.view').forEach(e=>e.classList.remove('on'));
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));
  document.getElementById('v-'+v).classList.add('on');el.classList.add('on');if(v==='trend')renderTrendCharts();}
function renderTrendCharts(){[['c1','weight_kg','#22d3ee','kg'],['c2','body_fat_pct','#fb923c','%'],['c3','muscle_kg','#34d399','kg']].forEach(([id,k,c,u])=>{
  const el=document.getElementById(id);if(el._c)el._c.destroy();
  const ml=D.trend.map(t=>{const p=t.d.split('-');return p[1]?(+p[1])+'月':t.d;});
  el._c=new Chart(el,{type:'line',data:{labels:ml,datasets:[{data:D.trend.map(t=>t[k]),borderColor:c,
    tension:.3,fill:false,pointRadius:3,pointBackgroundColor:c}]},
    options:{plugins:{legend:{display:false}},scales:{
      x:{ticks:{color:'#7d96ab',font:{size:9}},grid:{color:'rgba(125,150,171,.1)'},
         title:{display:true,text:'月份',color:'#5a7a92',font:{size:9}}},
      y:{ticks:{color:'#7d96ab',callback:v=>v+u},grid:{color:'rgba(125,150,171,.1)'}}}}});});}
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
