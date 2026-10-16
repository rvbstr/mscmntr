"""Small, inspectable adapters for verified public institutional page structures."""
import json
import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from ingestion.adapters.structured import _iso
from ingestion.dates import extract_dates
from ingestion.models import event_type


def parse_ges2(html,url):
    soup=BeautifulSoup(html,'html.parser');script=soup.find('script',id='__NEXT_DATA__')
    if not script: return []
    try: state=json.loads(script.string)['props']['pageProps']['__APOLLO_STATE__']
    except (KeyError,TypeError,json.JSONDecodeError): return []
    events=[]
    for key,items in state.get('ROOT_QUERY',{}).items():
        if not key.startswith('calendarItems(') or not isinstance(items,list): continue
        for item in items:
            material=state.get((item.get('material') or {}).get('__ref'),{})
            title=item.get('customTitle') or material.get('translation',{}).get('title')
            path=material.get('cardLink') or material.get('ges2FullPath')
            if not title or not path or not item.get('forDate'): continue
            subtype=state.get((material.get('subtype') or {}).get('__ref'),{}).get('title','')
            kind=event_type(subtype+' '+title)
            description=BeautifulSoup(material.get('translation',{}).get('description') or '','html.parser').get_text(' ',strip=True)[:500]
            base=dict(title=title,event_type=kind,description=description,primary_url=urljoin('https://ges-2.org/',path),confidence='institution_structured')
            if kind=='exhibition' and material.get('projectStartsAt'):
                start,_=_iso(material['projectStartsAt']);end,_=_iso(material.get('projectEndsAt'))
                events.append(dict(base,start_date=start,end_date=end,start_time=None))
            else:
                hours=BeautifulSoup(item.get('calendarHours') or '','html.parser').get_text(' ',strip=True)
                sessions=re.findall(r'([0-2]\d:[0-5]\d)\s*[–—-]\s*([0-2]\d:[0-5]\d)',hours)
                if not sessions: continue
                for start,end in sessions:
                    events.append(dict(base,start_date=item['forDate'],end_date=None,start_time=start,end_time=end))
    return events


def parse_prpr(html,url):
    # A separate exhibition page has a heading and a compact, explicit date block.
    if urlsplit(url).path.strip('/') in ('','exhibitions','artists','texts'): return []
    soup=BeautifulSoup(html,'html.parser');root=soup.select_one('section.text-section:has(h1)')
    if not root: return []
    heading=root.select_one('h1');blocks=root.select('h3');dates=None
    for block in blocks:
        parsed=extract_dates(block.get_text(' ',strip=True))
        if parsed['start_date'] and parsed.get('end_date'): dates=parsed;break
    if not dates: return []
    description=blocks[0].get_text(' ',strip=True)[:350] if blocks else ''
    base=dict(title=heading.get_text(' ',strip=True),primary_url=url,event_type='exhibition',description=description,confidence='institution_html')
    events=[dict(base,start_date=dates['start_date'],end_date=dates['end_date'],start_time=None)]
    if dates['opening_date']:
        events.append(dict(base,event_type='opening',start_date=dates['opening_date'],start_time=dates['opening_time'],end_date=None))
    return events


def parse_cube(html,url):
    soup=BeautifulSoup(html,'html.parser')
    root=soup.select_one('.page-container-exhibition')
    heading=soup.select_one('h1.page-title')
    block=soup.select_one('.exhibition-head .exhibition-date')
    if root is None or heading is None or block is None:return []
    dates=extract_dates(block.get_text(' ',strip=True))
    if not dates['start_date'] or not dates['end_date']:return []
    description=next((p.get_text(' ',strip=True) for p in root.select('p') if len(p.get_text())>110),'')[:500]
    return [dict(title=heading.get_text(' ',strip=True),primary_url=url,event_type='exhibition',description=description,confidence='institution_html',start_date=dates['start_date'],end_date=dates['end_date'],start_time=None)]


def parse_institution(html,url):
    host=urlsplit(url).hostname
    if host=='ges-2.org':return parse_ges2(html,url)
    if host=='prpr312.ru':return parse_prpr(html,url)
    if host=='cube.moscow':return parse_cube(html,url)
    return []


def institution_links(html,url,limit=6):
    soup=BeautifulSoup(html,'html.parser');host=urlsplit(url).hostname;result=[]
    for a in soup.select('a[href]'):
        target=urljoin(url,a['href']);p=urlsplit(target)
        if p.hostname!=host or not p.path.strip('/'):continue
        if host=='cube.moscow' and ('vystavka-' in p.path or 'vystavki-' in p.path):result.append(target)
        elif host=='prpr312.ru' and p.path.count('/')<=2 and a.get_text(' ',strip=True) and p.path.strip('/') not in ('exhibitions','artists','reviews','texts','about'):
            result.append(target)
    return list(dict.fromkeys(result))[:limit]
