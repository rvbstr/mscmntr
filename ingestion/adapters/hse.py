"""HSE gallery: event headings, breadcrumb periods and the visitor information block."""
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates


def parse_hse(html, url):
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
