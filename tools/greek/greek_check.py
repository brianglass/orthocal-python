import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import asyncio, django, os, json, glob, re, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import Day

BOOKS={'MATTHEW':'MATT','ST. MATTHEW':'MATT','MARK':'MARK','ST. MARK':'MARK','LUKE':'LUKE','ST. LUKE':'LUKE',
       'JOHN':'JOHN','ST. JOHN':'JOHN','ST. JOHN.':'JOHN'}
def canon(s):
    s=s.upper().replace('.',':').replace('ST: ','ST. ')
    m=re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$',s)
    if not m: return None
    book={'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    rest=re.sub(r'[^0-9:]','',m.group(3))
    return (book, rest)
def firstref(s):
    c=canon(s)
    if not c: return None
    m=re.search(r'(\d+)[:.](\d+)', s)
    return (c[0], int(m.group(1)), int(m.group(2))) if m else (c[0],0,0)

data={}
for f in glob.glob('data/antiochian_raw/*.json'):
    d=json.load(open(f)); data[d['originalCalendarDate']]=d

def pascha(y):
    a,b,c=y%4,y%7,y%19; d=(19*c+15)%30; e=(2*a+4*b-d+34)%7
    return datetime.date(y,(d+e+114)//31,((d+e+114)%31)+2)+datetime.timedelta(days=13)

async def main():
    for year in (2019,2021,2022,2023,2024,2025,2026):
        tri=pascha(year)-datetime.timedelta(days=70)
        cur=datetime.date(year,1,14); rows=[]
        while cur<=tri:
            k=cur.isoformat()
            if k in data:
                day=Day(cur.year,cur.month,cur.day,tradition='greek'); await day.ainitialize()
                rs=await day.aget_readings()
                got=[r.pericope.sdisplay for r in rs if r.source=='Gospel']
                want=data[k]['reading2Title']
                w=firstref(want); hit=any(firstref(g) and firstref(g)[0]==w[0] and firstref(g)[1]==w[1] and abs(firstref(g)[2]-w[2])<=2 for g in got)
                rows.append((k,cur.strftime('%a'),hit,want,got,data[k]['feastDayTitle']))
            cur+=datetime.timedelta(days=1)
        bad=[r for r in rows if not r[2]]
        print(f'\n=== {year}: {len(rows)} days checked, {len(bad)} WRONG ===')
        for k,wd,_,want,got,t in bad:
            print(f'  {k} {wd}  want={want:<26} app={got}   [{t[:34]}]')
asyncio.run(main())
