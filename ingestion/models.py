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
            found.update(event, event_id=original_id, evidence=list(evidence.values()), first_detected_at=first)
        else: result.append(dict(event))
    return result


def event_type(text):
    text=text.lower()
    for kind,pattern in [('opening',r'вернисаж|открытие'),('performance',r'перформанс'),('talk',r'лекци|дискусси|встреча'),('screening',r'кинопоказ|показ фильма|кинопрограмм'),('tour',r'экскурси|медиаторск|медиаци|\bтур\b'),('workshop',r'мастер.класс|воркшоп'),('festival',r'фестивал|ярмарк'),('exhibition',r'выставк|экспозици')]:
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
