"""Extract dates only from a scoped announcement, never from a whole index."""
import re
from datetime import date

MONTHS = {'января':1,'февраля':2,'марта':3,'апреля':4,'мая':5,'июня':6,
          'июля':7,'августа':8,'сентября':9,'октября':10,'ноября':11,'декабря':12}
MONTH = '(?:'+'|'.join(MONTHS)+')'


def extract_dates(text, year=None):
    text = re.sub(r'\s+', ' ', text.lower().replace('\xa0',' '))
    # Year must be in the announcement or explicitly supplied by a parser/editor.
    years = re.findall(r'\b(20\d{2})\b', text)
    if not year and len(set(years)) == 1: year = int(years[0])
    start = end = opening = time = opening_time = None
    def make(d, m, y):
        try: return date(int(y or year), int(m), int(d)).isoformat() if y or year else None
        except (ValueError, TypeError): return None
    same = re.search(rf'(\d{{1,2}})\s*[–—-]\s*(\d{{1,2}})\s+({MONTH})(?:\s+(20\d{{2}}))?', text)
    span = re.search(rf'(?:с\s+)?(\d{{1,2}})\s+({MONTH})(?:\s+(20\d{{2}}))?\s*(?:по|до|[–—-])\s*(\d{{1,2}})\s+({MONTH})(?:\s+(20\d{{2}}))?', text)
    numeric_range = re.search(r'(?<!\d)(\d{1,2})[./](\d{1,2})(?:[./](20\d{2}))?\s*[–—-]\s*(\d{1,2})[./](\d{1,2})[./](20\d{2})(?!\d)',text)
    numeric = re.search(r'(?<!\d)(\d{1,2})[./](\d{1,2})[./](20\d{2})(?!\d)', text)
    iso = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', text)
    if span:
        a,m,y,b,n,z = span.groups()
        start, end = make(a,MONTHS[m],y or year), make(b,MONTHS[n],z or year)
        if start and end and end < start and not z: end = make(b,MONTHS[n],int(start[:4])+1)
    elif same:
        a,b,m,y=same.groups(); start,end=make(a,MONTHS[m],y),make(b,MONTHS[m],y)
    elif numeric_range:
        a,m,y,b,n,z=numeric_range.groups();start,end=make(a,m,y or z),make(b,n,z)
    elif numeric: start=make(*numeric.groups())
    elif iso:
        try: start=date.fromisoformat(iso[1]).isoformat()
        except ValueError: pass
    else:
        single=re.search(rf'(?<!\d)(\d{{1,2}})\s+({MONTH})(?:\s+(20\d{{2}}))?', text)
        if single:
            d,m,y=single.groups()
            if re.search(r'\bдо\s*$', text[:single.start()]): end=make(d,MONTHS[m],y)
            else: start=make(d,MONTHS[m],y)
    op=re.search(rf'(?:открыти[ея]|вернисаж)\s*[:—–-]?\s*(\d{{1,2}})\s+({MONTH})(?:\s+(20\d{{2}}))?(?:\s*(?:года|г\.)?\s*(?:[,в]|начало в)*\s*([0-2]?\d[:.]\d{{2}}))?', text)
    if op:
        d,m,y,t=op.groups(); opening=make(d,MONTHS[m],y); opening_time=t.replace('.',':') if t else None
    tm=re.search(r'\b(?:в|начало\s+в)\s+([01]?\d|2[0-3])[:.]([0-5]\d)', text)
    if tm: time=f'{int(tm[1]):02}:{tm[2]}'
    return {'start_date':start,'end_date':end,'start_time':time,'opening_date':opening,'opening_time':opening_time}
