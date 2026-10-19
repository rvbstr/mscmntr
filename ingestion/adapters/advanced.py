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
            uncertainties=['Отмечен первый день работы выставки. Отдельное время вернисажа на сайте не указано.' if not event.get('start_time') else 'Отмечены дата и время начала выставки из разметки сайта; отдельный вернисаж не подтверждён.']))
    return result


def _dates(text):
    # Normalize English date labels as well as Russian ones, but never use article
    # publication metadata or biography years to supply a missing event year.
    months = [('January','января'),('February','февраля'),('March','марта'),('April','апреля'),('May','мая'),('June','июня'),('July','июля'),('August','августа'),('September','сентября'),('October','октября'),('November','ноября'),('December','декабря')]
    for en, ru in months:
        month = rf'(?:{en}|{en[:3]}\.?)'
        text = re.sub(rf'\b{month}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b', rf'\1 {ru}', text, flags=re.I)
        text = re.sub(rf'\b{month}\b', ru, text, flags=re.I)
    return extract_dates(text)


def parse_advanced(html, url):
    metadata = extruct.extract(html, base_url=url, syntaxes=['microdata', 'rdfa'], uniform=True, errors='ignore')
    nodes = [_schema(n) for values in metadata.values() for n in values]
    encoded = json.dumps(nodes, ensure_ascii=False).replace('</', '<\\/')
    structured = [event for event in parse_jsonld(f'<script type="application/ld+json">{encoded}</script>', url) if direct_url(event['primary_url'])]
    if structured:
        for event in structured: event['confidence'] = 'rich_metadata'
        return _first_days(structured)
    if not direct_url(url): return []
    if not re.search(r'/(?:exhibitions?|events?|vystav[^/]*|programme|projects?)/', urlsplit(url).path, re.I): return []
    soup = BeautifulSoup(html, 'html.parser')
    for node in soup.select('script,style,nav,footer,[role="navigation"]'): node.decompose()
    root = soup.select_one('article,main,[role="main"],.page-body')
    if root is None: return []
    headings = list(dict.fromkeys(n.get_text(' ', strip=True) for n in root.select('h1') if n.get_text(strip=True)))
    if len(headings) != 1: return []
    # Read compact event-date fields; a whole article can contain many unrelated years.
    blocks = root.select('time,[data-event-date],[class*="date"],[class*="period"],[class*="duration"],.dt')
    if not blocks: blocks = [n for n in root.select('p,div,span') if not n.find(['p','div']) and len(n.get_text(' ',strip=True)) <= 180]
    periods = []
    opening_text = []
    for node in blocks:
        text = node.get('datetime') or node.get_text(' ', strip=True)
        if len(text) > 180: continue
        parsed = _dates(text)
        if re.search(r'вернисаж|открыти[ея]|opening', text, re.I): opening_text.append(text); continue
        if parsed['start_date']: periods.append((parsed, text))
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
    base = dict(title=title, event_type=kind, primary_url=url, description=description,
        start_date=dates['start_date'], end_date=dates['end_date'], start_time=None if kind=='exhibition' else dates['start_time'],
        confidence='readable_html', date_basis='explicit_date_block', verification_method='trafilatura_scoped_dom', date_evidence=date_text)
    events = [base]
    for text in opening_text:
        date = _dates(text + ' ' + dates['start_date'][:4])
        if date['start_date']:
            events.append(dict(base, event_type='opening', start_date=date['opening_date'] or date['start_date'], start_time=date['opening_time'] or date['start_time'], end_date=None))
    return _first_days(events)
