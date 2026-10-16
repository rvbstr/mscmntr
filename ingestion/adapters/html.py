import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates
from ingestion.models import direct_url,event_type


def discover_links(html,url,limit=4):
    soup=BeautifulSoup(html,'html.parser'); links=[]
    for anchor in soup.select('a[href]'):
        target=urljoin(url,anchor['href']); p=urlsplit(target)
        if p.hostname != urlsplit(url).hostname or not direct_url(target): continue
        if re.search(r'\.(jpg|png|webp|pdf|mp4|zip|svg)$',p.path,re.I): continue
        if re.search(r'(exhibition|event|vystavk|vystav|afisha|/news/|/programme/|/projects/)',p.path,re.I):
            if target not in links: links.append(target)
    return links[:limit]


def parse_html(html,url,config=None):
    """Only explicit rules or a single article with a scoped date field are accepted."""
    config=config or {}; soup=BeautifulSoup(html,'html.parser')
    for n in soup.select('script,style,nav,footer,header'): n.decompose()
    root=soup.select_one(config.get('root','article'))
    if root is None: return []
    title_el=root.select_one(config.get('title','h1'))
    dates_el=root.select_one(config.get('dates','[data-event-date], .event-date, .exhibition-date, time'))
    if not title_el or not dates_el: return []
    title=title_el.get_text(' ',strip=True)
    date_text=dates_el.get('datetime') or dates_el.get_text(' ',strip=True)
    dates=extract_dates(date_text,config.get('year'))
    if not dates['start_date']: return []
    description_el=root.select_one(config.get('description','.event-description, .exhibition-description'))
    description=description_el.get_text(' ',strip=True)[:700] if description_el else ''
    kind=config.get('event_type') or event_type(title+' '+description)
    if kind=='exhibition' and dates.get('end_date'): dates['start_time']=None
    events=[dict(title=title,primary_url=url,event_type=kind,description=description,confidence='scoped_html',**dates)]
    if dates.get('opening_date') and kind=='exhibition':
        events.append(dict(title=title,primary_url=url,event_type='opening',start_date=dates['opening_date'],start_time=dates.get('opening_time'),
                           end_date=None,description=description,confidence='scoped_html',parent_key=title))
    return events
