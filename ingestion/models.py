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
        return bool(path) and path.lower() not in {'ru','en','events','exhibitions','calendar','news','ru/events','ru/exhibitions','ru/news','about','events.html','index.html','programme','ru/programme'}
    except ValueError: return False


def normalized_title(title):
    return re.sub(r'[^\w]+',' ',unicodedata.normalize('NFKC',title).casefold().replace('ё','е')).strip()


def stable_id(event):
    key='|'.join(str(event.get(k) or '') for k in ('institution_id','title','event_type','start_date','start_time'))
    return 'EV_'+hashlib.sha256(key.encode()).hexdigest()[:18].upper()


def deduplicate(events):
    result=[]
    for event in events:
        found=None
        for other in result:
            same=all(event.get(k)==other.get(k) for k in ('institution_id','start_date','event_type','start_time'))
            if not same: continue
            a,b=normalized_title(event['title']),normalized_title(other['title'])
            if event.get('event_type')=='opening':
                a=re.sub(r'^(?:вернисаж|открытие)\s+','',a); b=re.sub(r'^(?:вернисаж|открытие)\s+','',b)
            if a==b or (min(len(a),len(b))>18 and SequenceMatcher(None,a,b).ratio()>=0.97):
                found=other; break
        if found:
            evidence={canonical_url(x['url']):x for x in found.get('evidence',[])}
            evidence.update({canonical_url(x['url']):x for x in event.get('evidence',[])})
            first=found.get('first_detected_at') or event.get('first_detected_at')
            original_id=found['event_id']
            # A provisional reparse cannot downgrade an already confirmed event.
            replace = event.get('review_status') != 'tentative' or found.get('review_status') == 'tentative'
            if replace:
                if event.get('review_status') != 'tentative':
                    for field in ('uncertainties', 'venue_is_tentative', 'publication_basis', 'title_is_tentative'):
                        found.pop(field, None)
                found.update(event)
            found.update(event_id=original_id, evidence=list(evidence.values()), first_detected_at=first)
        else: result.append(dict(event))
    return result


def event_type(text):
    text=text.lower()
    for kind,pattern in [('opening',r'вернисаж|открытие'),('performance',r'перформанс'),('talk',r'лекци|дискусси|встреча|паблик[ -]?ток|круглый стол|диалог|обсуждени|бесед'),('screening',r'кинопоказ|показ фильма|кинопрограмм'),('tour',r'экскурси|медиаторск|медиаци|\bтур\b'),('workshop',r'мастер.класс|воркшоп'),('festival',r'фестивал|ярмарк'),('exhibition',r'выставк|экспозици')]:
        if re.search(pattern,text): return kind
    return 'other'


def link_parents(events):
    """Resolve exhibition IDs after deduplication without retaining dangling seed IDs."""
    by_id={e['event_id']:e for e in events}
    def title(e):
        value=normalized_title(e['title'])
        return re.sub(r'^(?:вернисаж|открытие)\s+','',value) if e['event_type']=='opening' else value
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


def complete_event(candidate,institution,source,timestamp):
    e=dict(candidate)
    if not e.get('geography_scope'):
        locations=institution.get('locations',[])
        address=e.get('address') or ''
        scopes={l.get('geography_scope') for l in locations if l.get('geography_scope')}
        exact=next((l for l in locations if l.get('city') and l['city'].casefold() in address.casefold()),None)
        if exact:e['geography_scope']=exact.get('geography_scope');e['city']=exact.get('city')
        elif len(scopes)==1:e['geography_scope']=next(iter(scopes))
    e.update(institution_id=institution['institution_id'],venue_name=institution['name'],source_id=source['source_id'],
             source_platform=source['platform'],timezone='Europe/Moscow',review_status=candidate.get('review_status','verified'),last_seen_at=timestamp,
             last_updated_at=timestamp,first_detected_at=e.get('first_detected_at') or timestamp,
             tags=institution.get('tags',[]),link_status='available',link_checked_at=timestamp)
    e['event_id']=e.get('event_id') or stable_id(e)
    e['evidence']=[{'url':e['primary_url'],'source_id':source['source_id'],'checked_at':timestamp,'status':'available','verification_method':candidate.get('verification_method','http')}]
    e['date_precision']='minute' if e.get('start_time') else 'date'
    return e
