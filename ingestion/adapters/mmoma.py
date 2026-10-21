"""Read MMOMA's scoped exhibition header; opening hours are not a vernissage."""
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates
from ingestion.models import event_type
from datetime import date


def parse_mmoma(html,url,context=None):
    if urlsplit(url).path.startswith('/visit/events/'):return parse_mmoma_sessions(html,url,context)
    if not re.match(r'^/visit/gallery/[^/]+(?:/description)?/?$',urlsplit(url).path):return []
    soup=BeautifulSoup(html,'html.parser');root=soup.select_one('main')
    if root is None:return []
    heading=root.select_one('h1');venue=root.select_one('h3 a[href*="/know/building/"]')
    if heading is None or venue is None:return []
    periods=[]
    for node in root.select('div,time'):
        text=node.get_text(' ',strip=True)
        if re.fullmatch(r'\d{2}\.\d{2}\.20\d{2}\s*[-–—]\s*\d{2}\.\d{2}\.20\d{2}',text):
            periods.append((extract_dates(text),text))
    if len({(d['start_date'],d['end_date']) for d,_ in periods})!=1:return []
    dates,text=periods[0]
    if not dates['start_date'] or not dates['end_date']:return []
    return [dict(title=' '.join(heading.get_text(' ',strip=True).split()),title_basis='event_heading',
        event_type='exhibition',primary_url=url,start_date=dates['start_date'],end_date=dates['end_date'],start_time=None,
        venue_name=venue.get_text(' ',strip=True).title()+(' · ММОМА' if 'sidur' in venue.get('href','') else ''),date_basis='explicit_date_block',date_evidence=text,
        source_authority='official',confidence='institution_html')]


def parse_mmoma_sessions(html,url,context=None):
    soup=BeautifulSoup(html,'html.parser');root=soup.select_one('main')
    if root is None:return []
    h=root.select_one('h1');venue=root.select_one('h3 a[href*="/know/building/"]')
    if h is None:return []
    lines=[re.sub(r'\s+',' ',s).strip() for s in root.get_text('\n',strip=True).splitlines() if s.strip()]
    period=next((extract_dates(s) for s in lines[:30] if re.fullmatch(r'\d{1,2}\.\d{1,2}\s*[-–—]\s*\d{1,2}\.\d{1,2}\.20\d{2}',s)),None)
    if not period or not period['start_date']:return []
    found=[]
    for index,line in enumerate(lines):
        m=re.fullmatch(r'(\d{1,2})[.](\d{1,2})(?:[.](20\d{2}))?\s*\|\s*([0-2]?\d:[0-5]\d)(?:\s*[—–-]\s*([0-2]?\d:[0-5]\d))?',line)
        if not m:continue
        try:day=date(int(m[3] or period['start_date'][:4]),int(m[2]),int(m[1])).isoformat()
        except ValueError:continue
        if not period['start_date']<=day<=(period['end_date'] or period['start_date']):continue
        title=lines[index+1] if index+1<len(lines) else ''
        if not 3<len(title)<230:continue
        label=lines[index+2] if index+2<len(lines) else ''
        kind=event_type(label+' '+title)
        hint=(context or {}).get('event_types',{}).get(url)
        if kind in ('other','exhibition') and hint and hint!='exhibition':kind=hint
        if kind=='exhibition':kind='other'
        if re.search(r'тур с экспертом',label,re.I):kind='tour'
        event=dict(title=title,title_basis='event_heading',event_type=kind,primary_url=url,start_date=day,end_date=None,start_time=m[4].zfill(5),end_time=m[5],
            date_basis='explicit_session',date_evidence=line,confidence='institution_html',source_authority='official')
        if venue:event['venue_name']=venue.get_text(' ',strip=True).title()
        found.append(event)
    return found
