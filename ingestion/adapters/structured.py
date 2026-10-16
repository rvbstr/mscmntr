import json
from datetime import datetime
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates
from ingestion.models import event_type


def _iso(value):
    if not isinstance(value,str): return None,None
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo:
            from zoneinfo import ZoneInfo
            dt=dt.astimezone(ZoneInfo('Europe/Moscow'))
        return dt.date().isoformat(), dt.strftime('%H:%M') if 'T' in value else None
    except ValueError: return None,None


def parse_jsonld(html, url):
    soup=BeautifulSoup(html,'html.parser'); found=[]
    def walk(node):
        if isinstance(node,list):
            for n in node: walk(n)
        elif isinstance(node,dict):
            types=node.get('@type',[]); types=[types] if isinstance(types,str) else types
            if any(t.split('/')[-1].endswith('Event') for t in types):
                start,time=_iso(node.get('startDate')); end,endtime=_iso(node.get('endDate'))
                if start and isinstance(node.get('name'),str):
                    loc=node.get('location') or {}; loc=loc[0] if isinstance(loc,list) and loc else loc
                    address=loc.get('address') if isinstance(loc,dict) else None
                    if isinstance(address,dict): address=', '.join(str(address[k]) for k in ('streetAddress','addressLocality') if address.get(k))
                    description=BeautifulSoup(str(node.get('description') or ''),'html.parser').get_text(' ',strip=True)[:700]
                    found.append(dict(title=node['name'].strip(),start_date=start,start_time=time,end_date=end,end_time=endtime,
                                      event_type='exhibition' if 'ExhibitionEvent' in types else event_type(' '.join(types)+' '+node['name']),
                                      description=description,primary_url=urljoin(url,node.get('url') or url),address=address,
                                      published_at=node.get('datePublished'),confidence='structured',date_precision='minute' if time else 'date'))
            for k,v in node.items():
                if k not in ('@context',): walk(v)
    for script in soup.find_all('script',type='application/ld+json'):
        try: walk(json.loads(script.string or script.get_text()))
        except (json.JSONDecodeError,TypeError): continue
    return found


def parse_feed(xml,url):
    try: root=ET.fromstring(xml)
    except ET.ParseError: return []
    ns={'a':'http://www.w3.org/2005/Atom'}; found=[]
    for item in list(root.findall('.//item'))+list(root.findall('.//a:entry',ns)):
        def text(tag):
            el=item.find(tag)
            if el is None: el=item.find('a:'+tag,ns)
            return ''.join(el.itertext()).strip() if el is not None else ''
        title=text('title'); link=text('link')
        if not link:
            el=item.find('a:link',ns); link=el.get('href','') if el is not None else ''
        description=BeautifulSoup(text('description') or text('content') or text('summary'),'html.parser').get_text(' ',strip=True)
        dates=extract_dates(title+' '+description)
        if title and link and dates['start_date']:
            found.append(dict(title=title,primary_url=urljoin(url,link),description=description[:700],event_type=event_type(title+' '+description),
                              published_at=text('pubDate') or text('published') or None,confidence='feed',**dates))
    return found
