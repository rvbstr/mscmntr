from datetime import date
import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TYPES = {'opening','exhibition','performance','talk','screening','tour','workshop','festival','other'}


def canonical_url(url):
    p=urlsplit(url)
    query=urlencode(sorted((k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_') and k not in ('fbclid','gclid','yclid')))
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/',query,''))


def direct_url(url):
    try:
        if any(ord(c)<32 for c in url):return False
        p=urlsplit(url)
        if p.scheme not in ('https','http') or not p.hostname or p.username or p.password: return False
        path=p.path.strip('/')
        if p.hostname in ('t.me','tg.me','telegram.me'): return bool(re.fullmatch(r'(?:s/)?[\w]+/\d+',path))
        if 'instagram.com' in p.hostname: return path.startswith(('p/','reel/'))
        if p.hostname in ('vk.com','vk.ru'): return 'wall' in path or 'wall' in p.query
        if path.split('/')[0].lower() in ('ru','en') and '/' in path: path=path.split('/',1)[1]
        if path.split('/')[-1].lower() in {'events','exhibitions','calendar','afisha','schedule','gallery','news','programme','program','projects','exhibitions-list'}:return False
        return bool(path) and path.lower() not in {'ru','en','events','exhibitions','calendar','news','ru/events','ru/exhibitions','ru/news','about','events.html','index.html','programme','ru/programme'}
    except ValueError: return False


def normalized_title(title):
    return re.sub(r'[^\w]+',' ',unicodedata.normalize('NFKC',title).casefold().replace('ё','е')).strip()


def identity_title(event):
    value=normalized_title(event['title'])
    if event['event_type']=='opening':value=re.sub(r'^(?:открытие|вернисаж)\s+','',value)
    if event['event_type'] in ('exhibition','opening'):
        value=re.sub(r'^(?:(?:персональная|групповая)\s+)?выставк[аи]\s+','',value)
    return value


def _urls(event, related=False):
    urls=[event.get('primary_url')]+[x.get('url') for x in event.get('evidence',[])]
    if related: urls+=event.get('related_urls',[])
    return {canonical_url(u) for u in urls if u and direct_url(u)}


def _same_day_or_period(a,b):
    if a.get('start_date')==b.get('start_date'):return True
    return (a['event_type']=='exhibition' and 'publication_bound' in (a.get('date_basis'),b.get('date_basis'))
        and a.get('end_date') and a.get('end_date')==b.get('end_date')
        and max(a['start_date'],b['start_date'])<=a['end_date'])


def same_event(a,b):
    """Require venue, type and day; explicit different sessions always stay separate."""
    if any(a.get(k)!=b.get(k) for k in ('institution_id','event_type')) or not _same_day_or_period(a,b): return False
    if a.get('start_time') != b.get('start_time'):
        if a.get('start_time') and b.get('start_time'): return False
        if a['event_type'] not in ('exhibition','opening'): return False
    x,y=identity_title(a),identity_title(b)
    if x==y or (min(len(x),len(y))>18 and SequenceMatcher(None,x,y).ratio()>=.97): return True
    # A shared event URL can resolve a fallback/marketing heading, but two named
    # events in a digest are not merged just because they share a programme link.
    shared=(_urls(a)&_urls(b)) or (_urls(a)&_urls(b,True)) or (_urls(b)&_urls(a,True))
    weak=any(e.get('title_is_tentative') or e.get('title_basis')=='fallback' for e in (a,b))
    return bool(shared and (weak or x in y or y in x))


def _quality(event):
    from ingestion.primary import is_aggregator
    authority=0 if is_aggregator(event.get('primary_url')) else {'official':3,'partner':2}.get(event.get('source_authority'),1)
    return (authority,event.get('review_status')!='tentative', not event.get('title_is_tentative'),
        event.get('title_basis') in ('event_heading','post_heading'),
        event.get('source_platform')=='website', bool(event.get('end_date')),bool(event.get('start_time')))


def _merge(found,event):
    evidence={canonical_url(x['url']):dict(x) for x in found.get('evidence',[])}
    for item in event.get('evidence',[]):
        key=canonical_url(item['url']);old=evidence.get(key,{})
        evidence[key]={**old,**item}
    original_id=found['event_id']
    aliases=set(found.get('merged_event_ids',[])+event.get('merged_event_ids',[])+[event['event_id']])
    timestamps=[e.get('first_detected_at') for e in (found,event) if e.get('first_detected_at')]
    related=list(dict.fromkeys(found.get('related_urls',[])+event.get('related_urls',[])))
    winner,other=(event,dict(found)) if _quality(event)>=_quality(found) else (dict(found),event)
    found.clear();found.update(winner)
    if found.get('date_basis')==other.get('date_basis')=='publication_bound':
        found['start_date']=min(found['start_date'],other['start_date'])
    # Fill missing useful facts without downgrading an explicit event record.
    for field in ('end_date','start_time','end_time','address','description'):
        if field!='description' and other.get('review_status')=='tentative' and found.get('review_status')!='tentative': continue
        if not found.get(field) and other.get(field): found[field]=other[field]
    if found.get('review_status')!='tentative':
        for field in ('uncertainties','venue_is_tentative','publication_basis','title_is_tentative'): found.pop(field,None)
    aliases.discard(original_id)
    found.update(event_id=original_id,evidence=list(evidence.values()),related_urls=related)
    if timestamps: found['first_detected_at']=min(timestamps)
    if aliases: found['merged_event_ids']=sorted(aliases)
    found['date_precision']='minute' if found.get('start_time') else 'date'
    if found['event_type']=='opening':found['end_date']=None


def stable_id(event):
    key='|'.join(str(event.get(k) or '') for k in ('institution_id','title','event_type','start_date','start_time'))
    return 'EV_'+hashlib.sha256(key.encode()).hexdigest()[:18].upper()


def deduplicate(events):
    result=[]
    ambiguous={e['event_id'] for e in events if not e.get('start_time') and
        len({other.get('start_time') for other in events if other.get('start_time') and same_event(e,other)})>1}
    for event in events:
        matches=[other for other in result if event['event_id'] not in ambiguous and other['event_id'] not in ambiguous and same_event(event,other)]
        # An undated clock cannot choose between two separately scheduled sessions.
        clocks={e.get('start_time') for e in matches+[event] if e.get('start_time')}
        if matches and len(clocks)<=1:
            found=matches[0]
            _merge(found,event)
            for other in matches[1:]:
                _merge(found,other);result.remove(other)
        else: result.append(dict(event))
    return result


def preserve_event_ids(events,previous):
    """Keep old shared links working when a reparse fixes the headline."""
    # Cache URL sets and compare only records from the same institution/type.
    # Refresh a set after merging evidence so alias handling keeps its semantics.
    from collections import defaultdict
    previous_groups=defaultdict(list);current_groups=defaultdict(list)
    urls={id(e):_urls(e) for e in events+previous}
    for old in previous:previous_groups[(old.get('institution_id'),old.get('event_type'))].append(old)
    for event in events:current_groups[(event.get('institution_id'),event.get('event_type'))].append(event)
    for event in events:
        group=(event.get('institution_id'),event.get('event_type'))
        matches=[old for old in previous_groups[group] if _same_day_or_period(event,old)
            and not (event.get('start_time') and old.get('start_time') and event['start_time']!=old['start_time'])
            and urls[id(event)]&urls[id(old)]]
        if not matches: continue
        # Never transfer one clockless old ID into multiple explicit sessions.
        matches=[old for old in matches if sum(bool(_same_day_or_period(e,old)) and bool(urls[id(e)]&urls[id(old)]) for e in current_groups[group])==1]
        if not matches: continue
        canonical=next((old for old in matches if old['event_id']==event['event_id']),None) or min(matches,key=lambda e:(e.get('first_detected_at') or '',e['event_id']))
        aliases=set(event.get('merged_event_ids',[])+[event['event_id']])
        for old in matches: aliases.update([old['event_id']]+old.get('merged_event_ids',[]))
        event['event_id']=canonical['event_id'];aliases.discard(event['event_id'])
        if aliases:event['merged_event_ids']=sorted(aliases)
        evidence={canonical_url(x['url']):dict(x) for old in matches for x in old.get('evidence',[])}
        evidence.update({canonical_url(x['url']):dict(x) for x in event.get('evidence',[])})
        event['evidence']=list(evidence.values())
        urls[id(event)]=_urls(event)
        timestamps=[e.get('first_detected_at') for e in [event]+matches if e.get('first_detected_at')]
        if timestamps:event['first_detected_at']=min(timestamps)
    return events


def event_type(text):
    text=text.lower()
    for kind,pattern in [('opening',r'вернисаж|открытие'),('performance',r'перформанс|перформатив'),('talk',r'лекци|дискусси|встреча|паблик[ -]?ток|круглый стол|диалог|обсуждени|бесед'),('screening',r'кинопоказ|показ(?:\s+[\w-]+){0,2}\s+фильм|кинопрограмм'),('tour',r'экскурси|медиаторск|медиаци|\bтур\b'),('workshop',r'мастер[\s–—-]?класс|воркшоп'),('festival',r'фестивал|ярмарк'),('exhibition',r'выставк|экспозици')]:
        if re.search(pattern,text): return kind
    return 'other'


def link_parents(events):
    """Resolve exhibition IDs after deduplication without retaining dangling seed IDs."""
    by_id={e['event_id']:e for e in events}
    def title(e):
        return identity_title(e)
    for e in events:
        if e['event_type']!='opening': continue
        old=by_id.get(e.get('parent_event_id'))
        if old and old['event_type']=='exhibition' and old['institution_id']==e['institution_id']: continue
        e.pop('parent_event_id',None)
        parent=next((p for p in events if p['event_type']=='exhibition' and p['institution_id']==e['institution_id'] and title(p)==title(e)
                     and p['start_date']<=e['start_date']<=(p.get('end_date') or p['start_date'])),None)
        if parent:e['parent_event_id']=parent['event_id']
    return events


def event_signature(event):
    title=normalized_title(event['title'])
    if event['event_type']=='opening':title=re.sub(r'^(?:вернисаж|открытие)\s+','',title)
    return (event['institution_id'],title,event['start_date'],event['event_type'],event.get('start_time'))


def valid_event(e):
    try:
        start=date.fromisoformat(e['start_date'])
        if e.get('end_date') and date.fromisoformat(e['end_date'])<start: return False
        if e.get('start_time') and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',e['start_time']): return False
        return bool(e.get('title','').strip()) and e.get('event_type') in TYPES and direct_url(e.get('primary_url',''))
    except (KeyError,ValueError,TypeError): return False


def normalize_openings(events):
    """An opening occupies one day; an announced exhibition keeps its own period."""
    result=[]
    for event in events:
        if event.get('event_type')!='opening' or not event.get('end_date'):
            result.append(event);continue
        end=event['end_date']
        if end>event['start_date'] and re.search(r'выставк|экспозици',event.get('title','')+' '+event.get('description',''),re.I):
            exhibition=dict(event,event_type='exhibition',start_time=None,end_time=None,date_precision='date')
            for key in ('event_id','merged_event_ids','parent_event_id'):exhibition.pop(key,None)
            if event.get('event_id'):exhibition['event_id']=stable_id(exhibition)
            result.append(exhibition)
        result.append(dict(event,end_date=None))
    return result


def complete_event(candidate,institution,source,timestamp):
    e=dict(candidate)
    if e.get('event_type')=='opening':e['end_date']=None
    if not e.get('geography_scope'):
        locations=institution.get('locations',[])
        address=e.get('address') or ''
        scopes={l.get('geography_scope') for l in locations if l.get('geography_scope')}
        exact=next((l for l in locations if l.get('city') and l['city'].casefold() in address.casefold()),None)
        if exact:e['geography_scope']=exact.get('geography_scope');e['city']=exact.get('city')
        elif len(scopes)==1:e['geography_scope']=next(iter(scopes))
    e.update(institution_id=institution['institution_id'],venue_name=candidate.get('venue_name') or institution['name'],source_id=source['source_id'],
             source_platform=source['platform'],timezone='Europe/Moscow',review_status=candidate.get('review_status','verified'),last_seen_at=timestamp,
             last_updated_at=timestamp,first_detected_at=e.get('first_detected_at') or timestamp,
             tags=institution.get('tags',[]),link_status='available',link_checked_at=timestamp)
    e['event_id']=e.get('event_id') or stable_id(e)
    e['evidence']=[{'url':e['primary_url'],'source_id':source['source_id'],'checked_at':timestamp,'status':'available','verification_method':candidate.get('verification_method','http'),
        **{k:e[k] for k in ('title','start_date','end_date','start_time','date_evidence','title_basis') if e.get(k) is not None}}]
    if candidate.get('source_title'):e['evidence'][0]['title']=candidate['source_title']
    e['date_precision']='minute' if e.get('start_time') else 'date'
    return e
