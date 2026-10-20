"""Explicitly labelled, opt-in publication of incomplete event announcements."""
from datetime import datetime
import re
from zoneinfo import ZoneInfo
from difflib import SequenceMatcher
from ingestion.adapters.social import DATE_MARKER, EVENT_WORD, TIME_MARKER, _heading
from ingestion.dates import extract_dates, MONTH
from ingestion.models import complete_event, valid_event, deduplicate, link_parents, event_type, preserve_event_ids
from ingestion.editorial import apply_overrides
from ingestion.primary import is_aggregator, require_primary_sources


def _title(text, fallback):
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    first_date=next((n for n,line in enumerate(lines) if DATE_MARKER.search(line)),len(lines)-1)
    heading=_heading(lines,first_date)
    if heading: return heading.strip('«»“”" ')
    flat = re.sub(r'\s+', ' ', text).strip()
    match = re.search(r'(?:выставк\w*|экскурси\w*|лекци\w*|дискусси\w*|воркшоп\w*|мастер.класс\w*)[^«“"]{0,100}[«“"]([^»”"]{3,150})[»”"]', flat, re.I)
    if match: return match[1].strip()
    return re.sub(r'^[\W_]+', '', fallback).strip()[:150]


def tentative_post(candidate):
    """Keep the actual date text and record every inference; do not date undated news."""
    text = candidate.get('description') or ''
    flat = re.sub(r'\s+', ' ', text)
    if not EVENT_WORD.search(text): return []
    if re.search(r'день рождения', ' '.join(text.splitlines()[:4]), re.I): return []
    if re.search(r'розыгрыш|разыгрыва', ' '.join(text.splitlines()[:4]), re.I):
        # Giveaway rules are not events; a separately dated public programme can be.
        parts = text.splitlines()
        first_date = next((n for n, line in enumerate(parts) if DATE_MARKER.search(line) and re.search(r'встреч|разговор|лекци|открывают', ' '.join(parts[n:n+4]), re.I)), None)
        if first_date is None: return []
        text = '\n'.join(parts[first_date:])
        flat = re.sub(r'\s+', ' ', text)
    # Explicit non-Moscow announcements do not become Moscow events by inference.
    if re.search(r'венск\w* Альбертин|в (?:Екатеринбурге|Петербурге|Нижнем Новгороде|Ташкенте)|в столичной Галерее изобразительного искусства Узбекистана', flat, re.I): return []
    try: published = datetime.fromisoformat(candidate['published_at'].replace('Z', '+00:00')).astimezone(ZoneInfo('Europe/Moscow')).date()
    except (KeyError, ValueError, TypeError): return []
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines() if line.strip()]
    address = next((line.removeprefix('📍').strip() for line in lines if re.search(r'(?i)(?:^адрес|^Москва[, ]|^Балашиха[, ]|улица|\bул\.|проспект|переулок|\bпер\.)', line) and re.search(r'\d', line) and len(line) < 220), None)
    results = []
    for n, line in enumerate(lines):
        date_text = re.sub(r'[«“"][^»”"]*[»”"]', '', line)
        if not DATE_MARKER.search(date_text): continue
        if re.search(r'родил|скончал|день рождения|прошлого года|адрес|улица|проспект|переулок|\bул[.,]|\bпер[.,]|строение|\bстр\.|^Москва[, ]|^Балашиха[, ]', line, re.I): continue
        # Use only a date line, never years from the rest of a biography.
        date_text = re.sub(r'(?<!\d)(\d{1,2}[./]\d{1,2})\.(?=[,\s]|$)', r'\1', date_text)
        if re.search(MONTH, date_text, re.I):
            date_text = re.sub(r'(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d', '', date_text)
        variants = [date_text]
        dates_list = re.search(rf'(?<!\d)((?:\d{{1,2}}\s*(?:,|и)\s*)+\d{{1,2}})\s+({MONTH})(?:\s+(20\d{{2}}))?', date_text, re.I)
        if dates_list:
            variants = [f'{day} {dates_list[2]} {dates_list[3] or published.year}' for day in re.findall(r'\d{1,2}', dates_list[1])]
        for variant in variants:
            dates = extract_dates(variant, published.year)
            start, end = dates['start_date'], dates['end_date']
            if not re.search(r'20\d{2}', variant):
                # December announcements can refer to the following January.
                if start and (published - datetime.fromisoformat(start).date()).days > 180:
                    start = extract_dates(variant, published.year + 1)['start_date']
                if end and not start and (published - datetime.fromisoformat(end).date()).days > 180:
                    end = extract_dates(variant, published.year + 1)['end_date']
            notes = ['Дата и программа извлечены из неоднозначной публикации; уточните их в оригинальном анонсе.']
            basis = 'publication_context'
            if not start and end:
                # This is a documented lower bound, not a claimed opening date.
                start = min(published.isoformat(), end)
                basis = 'publication_bound'
                notes.append('Дата открытия не указана: начало показа в календаре — дата публикации анонса (или известная дата завершения, если она раньше).')
            if not start: continue
            if int(start[:4]) < 2000: continue
            context = ' '.join(lines[max(0, n-3):min(len(lines), n+3)])
            heading = next((value for value in reversed(lines[:n+1]) if EVENT_WORD.search(value) and not DATE_MARKER.search(value)), lines[0])
            kind = event_type(context)
            if kind == 'other': kind = event_type(flat)
            if kind == 'other' and re.search(r'встреч|разговор', context, re.I): kind = 'talk'
            if kind == 'other': continue
            title = _title(text, next((value for value in lines if EVENT_WORD.search(value)), heading))
            if not title or len(title) < 3: continue
            clock = TIME_MARKER.search(' '.join(lines[n:min(len(lines), n+2)]))
            if kind == 'exhibition' and not end:
                notes.append('Полный период выставки не указан; в календаре отмечена только дата из публикации.')
            if not re.search(r'20\d{2}', variant): notes.append('Год предположительно определён по дате публикации.')
            item = dict(candidate, title=title, event_type=kind, start_date=start, end_date=end,
                start_time=(clock.group().zfill(5) if clock and kind != 'exhibition' else None),
                address=address, date_basis=basis, uncertainties=notes,
                title_is_tentative=True, title_basis='post_heading' if (_heading(lines, n) or '').strip('«»“”" ') == title else 'fallback')
            if address and re.search(r'\bМосква\b', address, re.I): item.update(geography_scope='moscow', city='Москва')
            elif address and re.search(r'\bБалашиха\b', address, re.I): item.update(geography_scope='moscow_region', city='Балашиха')
            results.append(item)
    # A digest is published as one programme, rather than assigning a heading or
    # a clock from a neighbouring item to every day mentioned in the post.
    unique = {(e['start_date'], e.get('end_date')) for e in results}
    if len(unique) > 1:
        start = min(e['start_date'] for e in results)
        end = max(e.get('end_date') or e['start_date'] for e in results)
        first = results[0]
        first.update(title='Программа: ' + first['title'], event_type='other', start_date=start,
            end_date=end if end != start else None, start_time=None,
            uncertainties=['В анонсе несколько дат и мероприятий: в календаре показан общий период программы. Даты отдельных пунктов и места уточняйте по оригиналу.'])
        return [first]
    return results[:1]


def _address(value):
    value = re.sub(r'(?i)\b(?:россия|москва|улица|ул|проспект|пр|переулок|пер|дом|д)\b\.?', '', value)
    return re.sub(r'\W+', '', value.casefold().replace('ё', 'е'))


def _owner(item, source, institutions):
    if item.get('institution_id') in institutions: return institutions[item['institution_id']], False
    # Resolve an aggregator's actual venue from its address before falling back to its catalogue link.
    address = _address(item.get('address') or '')
    if len(address) > 10:
        matches = [i for i in institutions.values() if any(SequenceMatcher(None, address, _address(l.get('address') or '')).ratio() > .88 for l in i.get('locations', []))]
        if len(matches) == 1: return matches[0], False
    linked = [institutions[i] for i in source.get('institution_ids', []) if i in institutions]
    if len(linked) == 1: return linked[0], 'announcements' not in source.get('roles', [])
    return (linked[0], True) if linked else (None, True)


def publish_review(catalog, review, reports, timestamp):
    institutions = {i['institution_id']: i for i in catalog['institutions']}
    sources = {s['source_id']: s for s in catalog['sources']}
    health = {h['source_id']: h for h in reports}
    events, remaining = [], []
    for row in review:
        source = sources.get(row.get('source_id'))
        if not source:
            if not row.get('source_id'): remaining.append(row)
            continue  # Removed institutions and their orphaned sources stay removed.
        candidate = row.get('candidate') or {}
        if is_aggregator(candidate.get('primary_url')):
            remaining.append(row);continue
        if 'за пределами Москвы' in row['reason']:
            remaining.append(row); continue
        items = [candidate] if valid_event(candidate) else tentative_post(candidate)
        published = False
        for item in items:
            if not valid_event(item): continue
            owner, inferred_owner = _owner(item, source, institutions)
            if not owner: continue
            notes = list(item.get('uncertainties') or [row['reason']])
            if inferred_owner:
                notes.append('Связь с площадкой предположительная; адрес события уточняйте в оригинале.')
            if not item.get('address'):
                notes.append('Адрес в анонсе не выделен; место проведения требует уточнения.')
            event = complete_event(item, owner, source, timestamp)
            status = row.get('link_status') or ('available' if source['platform'] in ('telegram', 'instagram') and health.get(source['source_id'], {}).get('last_successful_check') else 'not_checked')
            checked = row['link_checked_at'] if 'link_checked_at' in row else health.get(source['source_id'], {}).get('last_successful_check')
            if status != 'available': notes.append('Доступность ссылки на анонс не подтверждена; проверьте её перед посещением.')
            event.update(review_status='tentative', confidence='tentative', uncertainties=list(dict.fromkeys(notes)),
                venue_is_tentative=inferred_owner or not item.get('address'),
                venue_name=('Площадка уточняется' if inferred_owner else owner['name']),
                link_status=status, link_checked_at=checked,
                evidence=[{**e,'status':status,'checked_at':checked} for e in event['evidence']],
                publication_basis='owner_authorized_tentative')
            events.append(event); published = True
        if not published: remaining.append(row)
    return events, remaining


def publish_snapshot(catalog, overrides, previous, timestamp):
    if overrides.get('publication_policy') != 'include_tentative': raise ValueError('Публикация предварительных записей не включена')
    ids = {i['institution_id'] for i in catalog['institutions']}
    source_ids = {s['source_id'] for s in catalog['sources']}
    reports = [h for h in previous.get('sources', []) if h['source_id'] in source_ids]
    raw = {}
    kept = []
    for event in previous.get('events', []):
        if event['institution_id'] not in ids: continue
        if event.get('review_status') == 'tentative' and event.get('title_is_tentative'):
            key = (event['source_id'], event['primary_url'])
            raw[key] = {'source_id':event['source_id'], 'candidate':{k:event[k] for k in ('description','published_at','primary_url','first_detected_at') if k in event},
                'reason':'Неоднозначный анонс; опубликован предварительно', 'link_status':event['link_status'], 'link_checked_at':event.get('link_checked_at')}
            raw[key]['candidate']['related_urls']=event.get('related_urls',[])
        else: kept.append(event)
    added, review = publish_review(catalog, list(raw.values()) + previous.get('review', []), reports, timestamp)
    events = deduplicate(kept + added)
    events = link_parents(apply_overrides(preserve_event_ids(events,previous.get('events',[])),overrides))
    events,review=require_primary_sources(events,review)
    events.sort(key=lambda e:(e['start_date'], e.get('start_time') or '23:59', e['title']))
    annotate_reports(reports, events)
    metadata = {**previous.get('metadata', {}), 'generated_at':timestamp, 'last_editorial_update':timestamp,
        'event_count':len(events), 'source_count':len(source_ids), 'review_count':len(review),
        'publication_policy':overrides['publication_policy'], 'tentative_count':sum(e.get('review_status') == 'tentative' for e in events), 'catalog_updated_on':catalog['metadata']['updated_on']}
    return {'metadata':metadata, 'events':events, 'sources':reports}, review


def annotate_reports(reports, events):
    for report in reports:
        report['tentative_events'] = sum(e.get('review_status') == 'tentative' and e.get('source_id') == report['source_id'] for e in events)
        if report['tentative_events'] and report['status'] in ('working', 'partial', 'review'):
            report.update(status='partial', error='Есть предварительные события; даты и места требуют уточнения по пометкам на карточках.')
