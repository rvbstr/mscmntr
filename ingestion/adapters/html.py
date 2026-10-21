import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates
from ingestion.models import direct_url,event_type


def discover_links(html,url,limit=4):
    soup=BeautifulSoup(html,'html.parser'); links=[]
    for anchor in soup.select('a[href]'):
        target=urljoin(url,anchor['href']); p=urlsplit(target)
        if p.hostname != urlsplit(url).hostname or p.scheme not in ('http','https') or not p.path.strip('/'): continue
        if p.path.rstrip('/') == urlsplit(url).path.rstrip('/'): continue
        language = urlsplit(url).path.strip('/').split('/')[0]
        other = p.path.strip('/').split('/')[0]
        if language in ('ru','en') and other in ('ru','en') and language != other: continue
        if re.search(r'\.(jpg|png|webp|pdf|mp4|zip|svg)$',p.path,re.I): continue
        label=anchor.get_text(' ',strip=True)
        dated=False
        for parent in list(anchor.parents)[:4]:
            if parent.name in ('body','html','main','header','footer','nav'):break
            surrounding=parent.get_text(' ',strip=True)
            if len(surrounding)>1200:break
            if re.search(r'20\d{2}|\d{1,2}/\d{1,2}/2\d\b',surrounding) and re.search(r'выстав|exhibition|вернисаж',surrounding,re.I):dated=True;break
        if re.search(r'(exhibition|event|vystav|afisha|schedule|calendar|/news/|/programme?/|/projects?/|/gallery/)',p.path,re.I) or re.search(r'афиша|расписание|выставки|события|текущий проект|календарь',label,re.I) or dated:
            if re.search(r'/artists?/|/participants?/|/contacts?/?$|/about/?$|/museum/|/authors?/|/shop/|/product/|/cart/?$|/checkout/?$|/katalog/?$|/catalog/?$',p.path,re.I):continue
            if target not in [x[0] for x in links]:
                score=4 if re.search(r'афиша|расписание|текущ|события|календарь|current|schedule|calendar',label,re.I) else (2 if direct_url(target) else 0)
                if re.search(r'[-/]en(?:/|#|$)',p.path) and re.search('[а-яА-Я]',soup.get_text(' ',strip=True)[:2000]):score-=2
                links.append((target,score))
    return [url for url,_ in sorted(links,key=lambda x:-x[1])][:limit]


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
