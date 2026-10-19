import json
from jsonschema import Draft202012Validator, FormatChecker


def load_overrides(path, catalog):
    data=json.loads(path.read_text()); schema=json.loads(path.with_name('overrides.schema.json').read_text())
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)
    institutions={i['institution_id'] for i in catalog['institutions']}; sources={s['source_id'] for s in catalog['sources']}
    unknown=(set(data['priorities'])-institutions)|(set(data['disabled_sources'])-sources)
    if unknown: raise ValueError('Неизвестные ID в правках: '+', '.join(sorted(unknown)))
    if any(e['institution_id'] not in institutions for e in data['manual_events']): raise ValueError('Неизвестное пространство в ручном событии')
    ids=[e['event_id'] for e in data['manual_events']]
    if len(ids)!=len(set(ids)): raise ValueError('Повторный ID ручного события')
    for start in data['duplicates']:
        seen=set(); node=start
        while node in data['duplicates']:
            if node in seen: raise ValueError('Циклическое объединение событий')
            seen.add(node); node=data['duplicates'][node]
        if start in data['suppress'] or node in data['suppress']: raise ValueError('Конфликт объединения и скрытия')
    return data


def apply_overrides(events, overrides):
    events={e['event_id']:dict(e) for e in events}
    for eid,changes in overrides['corrections'].items():
        if eid not in events: raise ValueError(f'Исправление отсутствующего события: {eid}')
        events[eid].update(changes)
    for old,new in overrides['duplicates'].items():
        if new not in events: raise ValueError('Объединение с отсутствующим основным событием')
        if old not in events: continue  # A previously merged alias is an idempotent no-op.
        # Resolve chains before transferring evidence.
        target=new
        while target in overrides['duplicates']: target=overrides['duplicates'][target]
        events[target]['evidence']=list({x['url']:x for x in events[target].get('evidence',[])+events[old].get('evidence',[])}.values())
        aliases=set(events[target].get('merged_event_ids',[])+events[old].get('merged_event_ids',[])+[old])
        aliases.discard(target)
        events[target]['merged_event_ids']=sorted(aliases)
    return [e for eid,e in events.items() if eid not in overrides['suppress'] and eid not in overrides['duplicates']]
