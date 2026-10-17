"""Public programme cards and embedded state, scoped to explicit dated sessions."""
import json
from html import unescape
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates
from ingestion.models import event_type


def next_state(soup):
    script = soup.find('script', id='__NEXT_DATA__')
    try:
        return json.loads(script.string)['props']['pageProps'] if script else {}
    except (ValueError, KeyError, TypeError):
        return {}


def card_dates(text):
    # Zotov writes explicit years as 26/27. Expand only years in a dated field.
    text = re.sub(r'(\b\d{1,2}\.\d{1,2}\.)(\d{2})(?!\d)', r'\g<1>20\2', text)
    dates = extract_dates(text)
    clock = re.search(r'(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)', text)
    if clock:
        dates['start_time'] = f'{int(clock[1]):02}:{clock[2]}'
    return dates


def card_event(title, date_text, url, kind, description=''):
    dates = card_dates(date_text)
    if not title or title.endswith(('...', '…')) or not dates['start_date']:
        return []
    # A months-long lecture series is not a continuous lecture or guessed sessions.
    if dates['end_date'] and dates['end_date'] != dates['start_date'] and kind != 'exhibition':
        return []
    return [dict(title=title, primary_url=url, event_type=kind,
                 description=description[:500], confidence='institution_html',
                 start_date=dates['start_date'], end_date=dates['end_date'],
                 start_time=None if kind == 'exhibition' else dates['start_time'])]


def parse_ruarts(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    result = []
    for card in soup.select('a[href]'):
        target = urljoin(url, card['href'])
        if urlsplit(target).hostname != 'ruarts.foundation' or not re.fullmatch(r'/ru/(?:events|projects)/[^/]+/\d+/?', urlsplit(target).path):
            continue
        title, date = card.select_one('.title'), card.select_one('.date')
        if title is None or date is None:
            continue
        desc, label = card.select_one('.desc'), card.select_one('.type')
        title = title.get_text(' ', strip=True)
        description = desc.get_text(' ', strip=True) if desc else ''
        kind = event_type(title + ' ' + description)
        # A masterclass mentioning a conversation is still a masterclass.
        section = urlsplit(target).path.strip('/').split('/')[2]
        if section == 'masterclass':
            kind = 'workshop'
        if kind == 'other' and label:
            kind = event_type(label.get_text(' ', strip=True))
        result.extend(card_event(title, date.get_text(' ', strip=True), target, kind, description))
    return result


def parse_zotov(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    result = []
    for card in soup.select('.catalog-card__info[href]'):
        target = urljoin(url, card['href'])
        if urlsplit(target).hostname != 'centrezotov.ru' or not re.fullmatch(r'/events/(?:[^/]+/)+', urlsplit(target).path):
            continue
        title, date, label = card.select_one('.catalog-card__sub'), card.select_one('.catalog-card__date'), card.select_one('.catalog-card__tag')
        if title is None or date is None or label is None:
            continue
        kind = event_type(label.get_text(' ', strip=True))
        if kind == 'other':
            continue
        result.extend(card_event(title.get_text(' ', strip=True), date.get_text(' ', strip=True), target, kind))
    return result


def parse_garage(html, url):
    state = next_state(BeautifulSoup(html, 'html.parser')).get('initialState', {})
    pools = [state.get('mainCalendar', {}), state.get('calendarEvents', {}).get('timeRanges', {})]
    result = []
    for pool in pools:
        for row in pool.get('timeRanges', {}).values():
            attrs = row.get('attributes', {})
            event = pool.get('events', {}).get(str(attrs.get('eventId')), {})
            details = event.get('attributes', {})
            title = unescape(attrs.get('title') or details.get('title') or '').strip()
            slug = details.get('slug')
            if not title or not slug or not re.fullmatch(r'[A-Za-z0-9_-]+', slug):
                continue
            kind_ref = (row.get('relationships', {}).get('kind', {}).get('data') or
                        event.get('relationships', {}).get('kind', {}).get('data') or {})
            label = pool.get('filterValues', {}).get(str(kind_ref.get('id')), {}).get('attributes', {}).get('title', '')
            kind = event_type(title)
            if kind == 'other':
                kind = event_type(label)
            try:
                start = datetime.fromtimestamp(attrs['startsAt'], ZoneInfo('Europe/Moscow'))
                end = datetime.fromtimestamp(attrs['endsAt'], ZoneInfo('Europe/Moscow'))
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
            # Recurrence bounds aren't a session; don't invent all-day multi-month tours.
            if end < start or (start.date() != end.date() and kind != 'exhibition'):
                continue
            description = BeautifulSoup(details.get('lead') or '', 'html.parser').get_text(' ', strip=True)
            result.append(dict(title=title, primary_url=urljoin('https://garagemca.org/event/', slug),
                               event_type=kind, description=description[:500], confidence='institution_structured',
                               start_date=start.date().isoformat(), end_date=end.date().isoformat() if kind == 'exhibition' else None,
                               start_time=None if attrs.get('wholeDay') or kind == 'exhibition' else start.strftime('%H:%M'),
                               end_time=None if attrs.get('wholeDay') or kind == 'exhibition' else end.strftime('%H:%M')))
    return result
