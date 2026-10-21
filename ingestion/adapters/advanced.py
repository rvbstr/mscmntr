"""Fallback extraction for public event pages without a site-specific adapter."""
import json
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
import extruct
from trafilatura import bare_extraction
from ingestion.adapters.structured import parse_jsonld
from ingestion.dates import extract_dates
from ingestion.models import direct_url, event_type


def russian_version(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    if (soup.html.get('lang', '') if soup.html else '').lower().startswith('ru'): return None
    for node in soup.select('link[hreflang], a[href]'):
        label = node.get_text(' ', strip=True).lower()
        if not (node.get('hreflang', '').lower().startswith('ru') or label in ('ru', 'рус', 'русский')): continue
        target = urljoin(url, node.get('href', ''))
        if urlsplit(target).netloc == urlsplit(url).netloc and target.rstrip('/') != url.rstrip('/'): return target
    return None


def _schema(node):
    if isinstance(node, list): return [_schema(n) for n in node]
    if not isinstance(node, dict): return node
    if '@value' in node: return node['@value']
    result = {}
    for key, value in node.items():
        key = key.rsplit('/', 1)[-1] if key.startswith(('http://schema.org/', 'https://schema.org/')) else key
        value = _schema(value)
        if isinstance(value, list) and len(value) == 1 and key not in ('@graph', '@type'): value = value[0]
        result[key] = value
    return result


def _first_days(events):
    result = list(events)
    for event in events:
        if event['event_type'] != 'exhibition': continue
        if any(e['event_type'] == 'opening' and e['start_date'] == event['start_date'] and e['primary_url'] == event['primary_url'] for e in events): continue
        result.append(dict(event, event_type='opening', end_date=None, start_time=event.get('start_time'), end_time=None,
            review_status='tentative', confidence='inferred_opening', date_basis='exhibition_start',
            uncertainties=list(event.get('uncertainties',[]))+['Отмечен первый день работы выставки. Отдельное время вернисажа на сайте не указано.' if not event.get('start_time') else 'Отмечены дата и время начала выставки из разметки сайта; отдельный вернисаж не подтверждён.']))
    return result


def _dates(text,year=None):
    # Normalize English date labels as well as Russian ones, but never use article
    # publication metadata or biography years to supply a missing event year.
    months = [('January','января'),('February','февраля'),('March','марта'),('April','апреля'),('May','мая'),('June','июня'),('July','июля'),('August','августа'),('September','сентября'),('October','октября'),('November','ноября'),('December','декабря')]
    for en, ru in months:
        month = rf'(?:{en}|{en[:3]}\.?)'
        text = re.sub(rf'\b{month}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b', rf'\1 {ru}', text, flags=re.I)
        text = re.sub(rf'\b{month}\b', ru, text, flags=re.I)
    text=re.sub(r'(?<=\d)\s*\.\s*(?=\d)','.',text)
    text=re.sub(r',\s*(?=20\d{2}\b)',' ',text)
    # Explicit two-digit years in slash-formatted programme dates (e.g. 21/10/26).
    text=re.sub(r'(?<!\d)(\d{1,2})/(\d{1,2})/(2\d)(?!\d)',lambda m:f'{m[1]}/{m[2]}/20{m[3]}',text)
    text=re.sub(r'(\d{1,2}[./]\d{1,2}[./])\s+(20\d{2})',r'\1\2',text)
    text=re.sub(r'^(\d{1,2}\.\d{1,2})\s*/\s*(\d{1,2}\.\d{1,2}(?:\.20\d{2})?)$',r'\1 — \2',text.strip())
    text=re.sub(r'^(\d{1,2}\.\d{1,2}\.20\d{2})\s+(\d{1,2}\.\d{1,2}\.20\d{2})$',r'\1 — \2',text.strip())
    return extract_dates(text,year)


def publication_field(node):
    return any(re.search(r'datePublished|dateModified|published|modified|posted[-_ ]on|post[-_]date|entry[-_]date',str(n.attrs),re.I) for n in [node]+list(node.parents)[:2])


def parse_advanced(html, url, context=None):
    metadata = extruct.extract(html, base_url=url, syntaxes=['microdata', 'rdfa'], uniform=True, errors='ignore') if re.search(r'\s(?:itemtype|typeof|vocab)\s*=|\sitemscope(?:\s|[=>])',html,re.I) else {}
    nodes = [_schema(n) for values in metadata.values() for n in values]
    encoded = json.dumps(nodes, ensure_ascii=False).replace('</', '<\\/')
    structured = [event for event in parse_jsonld(f'<script type="application/ld+json">{encoded}</script>', url) if direct_url(event['primary_url'])]
    if structured:
        for event in structured: event['confidence'] = 'rich_metadata'
        return _first_days(structured)
    if not direct_url(url) or re.search(r'/(?:artists?|authors?|participants?|museum|product)/',urlsplit(url).path,re.I): return []
    soup = BeautifulSoup(html, 'html.parser')
    for node in soup.select('script,style,nav,footer,[role="navigation"]'): node.decompose()
    root = soup.select_one('article,main,[role="main"],.page-body') or soup.body
    if root is None: return []
    headings = list(dict.fromkeys(n.get_text(' ', strip=True) for n in root.select('h1') if n.get_text(strip=True)))
    headings=[h for h in headings if h.casefold() not in {'проекты','о событии','события','выставки','о выставке','программа','projects','about the event'}]
    if not headings:
        metadata_title=soup.select_one('meta[property="og:title"]')
        title=metadata_title.get('content','').strip() if metadata_title else ''
        if not title and soup.title:
            candidate=soup.title.get_text(' ',strip=True)
            if any(n.get_text(' ',strip=True)==candidate for n in root.select('[class*="title"],h2,h3')):title=candidate
        if title and len(title)<200:headings=[title]
    if len(headings) != 1: return []
    # Read compact event-date fields; a whole article can contain many unrelated years.
    blocks = root.select('time,[data-event-date],[class*="date"],[class*="period"],[class*="duration"],.dt')
    fallback=[n for n in root.select('p,div,span,h2,h3') if not n.find(['p','div']) and len(n.get_text(' ',strip=True)) <= 180]
    blocks=list(dict.fromkeys(blocks+fallback))
    periods = []
    opening_text = []
    for node in blocks:
        text = node.get('datetime') or node.get_text(' ', strip=True)
        if len(text) > 180: continue
        if publication_field(node):continue
        calendar_year=re.search(r'/exhibitions?/(20\d{2})/',urlsplit(url).path)
        parsed = _dates(text,int(calendar_year[1]) if calendar_year else (context or {}).get('reference_year'))
        if re.search(r'вернисаж|открыти[ея]|opening', text, re.I): opening_text.append(text); continue
        if parsed['start_date']: periods.append((parsed, text))
    ranges={(d['start_date'],d['end_date']) for d,_ in periods if d['end_date']}
    if len(ranges)==1:
        start,end=next(iter(ranges))
        periods=[(d,t) for d,t in periods if d['end_date'] or d['start_date'] not in (start,end)]
    unique = {(d['start_date'], d['end_date']) for d, _ in periods}
    if len(unique) != 1: return []
    dates, date_text = periods[0]
    document = bare_extraction(html, url=url, with_metadata=True, include_comments=False, include_tables=False, favor_precision=True)
    title = headings[0]
    artist = root.select_one('.page-over-title,[itemprop="creator"]')
    artist_name = artist.get_text(' ', strip=True) if artist else ''
    if artist_name and len(artist_name) < 120 and artist_name not in title: title = f'{artist_name}. {title}'
    description = (document.text if document else '') or ''
    description = ' '.join(line for line in description.splitlines() if line.strip() not in (headings[0], artist_name, date_text))[:500]
    kind = 'exhibition' if re.search(r'/exhibitions?/', urlsplit(url).path) else event_type(title + ' ' + description[:150])
    if kind=='other' and not (re.search(r'/(?:lectures?|workshops?|tours?)/',urlsplit(url).path) or (urlsplit(url).hostname=='mmoma.ru' and '/visit/events/' in urlsplit(url).path)) and dates['end_date'] and re.search(r'выставк|exhibition',root.get_text(' ',strip=True),re.I):kind='exhibition'
    if re.search(r'/learn/lectures/',urlsplit(url).path):kind='talk'
    if kind=='other':return []
    if kind=='exhibition' and not dates['end_date']:return []
    if kind not in ('exhibition','festival') and dates['end_date'] and dates['start_date']!=dates['end_date']:return []
    base = dict(title=title, event_type=kind, primary_url=url, description=description,
        start_date=dates['start_date'], end_date=dates['end_date'], start_time=None if kind=='exhibition' else dates['start_time'],
        confidence='readable_html', date_basis='explicit_date_block', verification_method='trafilatura_scoped_dom', date_evidence=date_text)
    events = [base]
    for text in opening_text:
        date = _dates(text + ' ' + dates['start_date'][:4])
        if date['start_date']:
            events.append(dict(base, event_type='opening', start_date=date['opening_date'] or date['start_date'], start_time=date['opening_time'] or date['start_time'], end_date=None))
    return _first_days(events)
