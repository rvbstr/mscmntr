"""HSE gallery: event headings, breadcrumb periods and the visitor information block."""
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates
from ingestion.models import event_type


def parse_hse(html, url, context=None):
    if re.match(r'^/news/\d+/?$',urlsplit(url).path):return parse_news(html,url,context)
    if not re.match(r'^/gallery/[^/]+/?$', urlsplit(url).path): return []
    soup=BeautifulSoup(html,'html.parser')
    headings=[n.get_text(' ',strip=True) for n in soup.select('h1')]
    titles=[re.sub(r'^Выставка\s+', '', h, flags=re.I).strip('«»“”" ') for h in headings if re.match(r'^Выставка\s+[«“"]',h,re.I)]
    if len(set(titles)) != 1: return []
    periods=[]
    for node in soup.select('.breadcrumbs__item'):
        text=node.get_text(' ',strip=True)
        dates=extract_dates(text)
        if dates['start_date'] and dates['end_date']: periods.append((dates,text))
    if len({(d['start_date'],d['end_date']) for d,_ in periods}) != 1: return []
    dates,date_text=periods[0]
    lead=soup.select_one('p.lead')
    base=dict(title=titles[0],title_basis='event_heading',event_type='exhibition',primary_url=url,
        description=lead.get_text(' ',strip=True)[:700] if lead else '',
        start_date=dates['start_date'],end_date=dates['end_date'],start_time=None,
        confidence='institution_html',date_basis='explicit_date_block',date_evidence=date_text)
    visitor=next((n for n in soup.select('.page-edi') if n.find('strong',string=re.compile(r'^Открытие\s*$'))),None)
    opening=None
    if visitor:
        # Work only inside the visit block, not participant biographies or course adverts.
        for strong in visitor.select('strong'):
            if strong.get_text(' ',strip=True) != 'Открытие': continue
            parts=[]
            for sibling in strong.next_siblings:
                if getattr(sibling,'name',None) in ('br','strong'): break
                parts.append(sibling.get_text(' ',strip=True) if hasattr(sibling,'get_text') else str(sibling))
            opening=extract_dates('Открытие '+' '.join(parts),int(dates['start_date'][:4]))
        address=next((line.strip() for line in visitor.get_text('\n',strip=True).splitlines() if re.search(r'улица|переулок|проспект|\bул\.',line,re.I) and re.search(r'\d',line)),None)
        if address: base['address']=address
    result=[base]
    if opening and opening['opening_date']:
        result.append(dict(base,event_type='opening',start_date=opening['opening_date'],end_date=None,
            start_time=opening['opening_time'],date_evidence='Открытие '+' '.join(parts)))
    return result


def parse_news(html,url,context=None):
    soup=BeautifulSoup(html,'html.parser');heading=soup.select_one('h1');lead=soup.select_one('.page-edi .lead')
    if heading is None or lead is None:return []
    blocks=soup.select('.page-edi');lines=list(dict.fromkeys(
        [p.get_text(' ',strip=True) for block in blocks for p in block.select('p')]+
        [line.strip() for block in blocks for line in block.get_text('\n',strip=True).splitlines() if line.strip()]))
    # A news publication timestamp is not an event day. Only the actual schedule
    # paragraph supplies the day; the breadcrumb can supply its missing year.
    years=set(re.findall(r'\b20\d{2}\b',' '.join(n.get_text(' ',strip=True) for n in soup.select('.breadcrumbs__item'))))
    year=int(next(iter(years))) if len(years)==1 else (context or {}).get('reference_year')
    schedules=[]
    for text in lines:
        clock=re.search(r'(?<!\d)(?:с\s*)?((?:[01]?\d|2[0-3]):[0-5]\d)\s*(?:до|[–—-])\s*((?:[01]?\d|2[0-3]):[0-5]\d)',text)
        dates=extract_dates(text,year)
        if clock and dates['start_date']:schedules.append((dates,text,clock))
    if len({(d['start_date'],c[1],c[2]) for d,_,c in schedules})!=1:return []
    dates,text,clock=schedules[0]
    title=heading.get_text(' ',strip=True);description=lead.get_text(' ',strip=True)
    kind=event_type(title+' '+description)
    if kind in ('other','exhibition','opening'):return []
    address=next((re.sub(r'^Адрес\s*:\s*','',v,flags=re.I) for v in lines if re.match(r'^Адрес\s*:',v,re.I)),None)
    venue=re.search(r'пространств[ое]\s+[«"]([^»"]+)[»"]',description+' '+(address or ''),re.I)
    return [dict(title=title,title_basis='event_heading',event_type=kind,description=description,primary_url=url,
        start_date=dates['start_date'],end_date=None,start_time=clock[1].zfill(5),end_time=clock[2].zfill(5),
        address=address,venue_name=venue[1] if venue else None,confidence='institution_html',date_basis='explicit_schedule',date_evidence=text)]
