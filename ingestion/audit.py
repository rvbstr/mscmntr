"""Check the published calendar for duplicates without conflating separate sessions."""
import argparse
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from ingestion.models import same_event


def duplicate_pairs(events):
    pairs=[]
    for a,b in combinations(events,2):
        if not same_event(a,b): continue
        if a.get('start_time')!=b.get('start_time'):
            unknown=a if not a.get('start_time') else b
            clocks={e.get('start_time') for e in events if e.get('start_time') and same_event(unknown,e)}
            if len(clocks)>1: continue
        pairs.append({'event_ids':[a['event_id'],b['event_id']],
            'titles':[a['title'],b['title']], 'urls':[a.get('primary_url'),b.get('primary_url')]})
    return pairs


def main():
    parser=argparse.ArgumentParser(description='Проверка календаря на повторные события')
    parser.add_argument('path',nargs='?',type=Path,default=Path('public/data/events.json'))
    args=parser.parse_args()
    events=json.loads(args.path.read_text())['events']
    ids=Counter(e['event_id'] for e in events)
    result={'events':len(events),'repeated_ids':[k for k,n in ids.items() if n>1],
        'duplicate_pairs':duplicate_pairs(events)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(bool(result['repeated_ids'] or result['duplicate_pairs']))


if __name__=='__main__':raise SystemExit(main())
