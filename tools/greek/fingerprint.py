import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import json, glob, re, os

BOOKS = ['MATTHEW','MARK','LUKE','JOHN','ACTS','ROMANS','CORINTHIANS','GALATIANS','EPHESIANS',
         'PHILIPPIANS','COLOSSIANS','THESSALONIANS','TIMOTHY','TITUS','PHILEMON','HEBREWS',
         'JAMES','PETER','JUDE','REVELATION','GENESIS','ISAIAH','PROVERBS','EXODUS','JOEL',
         'ZECHARIAH','MALACHI','WISDOM','JOB','JONAH','DANIEL','KINGS','SAMUEL','JEREMIAH',
         'EZEKIEL','NUMBERS','DEUTERONOMY','JOSHUA','JUDGES','BARUCH','SIRACH','MICAH',
         'HABAKKUK','ZEPHANIAH','LEVITICUS']
ORD = [('THIRD', '3'), ('SECOND', '2'), ('FIRST', '1'), ('III', '3'), ('II', '2'), ('I', '1')]

def canon(s):
    if not s: return ''
    u = re.sub(r'[^A-Z0-9:; ,\-]', ' ', s.upper().replace('.', ':'))
    book = next((b for b in BOOKS if b in u), '')
    if not book: return ''
    o = ''
    # antiochian.org writes the ordinal AFTER the book ("St. Peter's First
    # Universal Letter"), goarch.org before it ("I Corinthians"), so search
    # the whole citation rather than only the text preceding the book name.
    for word, digit in ORD[:3]:                 # FIRST / SECOND / THIRD
        if re.search(rf'\b{word}\b', u):
            o = digit; break
    if not o:
        m = re.match(r'\s*(I{1,3})\b', u)      # leading roman numeral
        if m:
            o = str(len(m.group(1)))
    m = re.search(r'(\d+):(\d+)', u[u.index(book):])
    if not m: return ''
    return f'{o}{book[:4]}{m.group(1)}:{m.group(2)}'

rows = []
for f in sorted(glob.glob('data/antiochian_raw/*.json')):
    d = json.load(open(f))
    dt = d['originalCalendarDate']
    if not dt.startswith('2026-'): continue
    rows.append(f"{dt[5:].replace('-','')},{canon(d.get('reading1Title',''))},{canon(d.get('reading2Title',''))}")
print(len(rows), 'days')
open('/private/tmp/claude-502/-Users-bglass-src-orthocal-python/43328cf2-479f-4676-af8c-4d8d97fa6002/scratchpad/ant2026.txt','w').write(';'.join(rows))
print('payload chars:', len(';'.join(rows)))
