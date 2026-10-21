"""Reproducible live audit of every source and institution, including disabled ones."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from hashlib import sha256
import json
import time
from pathlib import Path
from urllib.parse import urlsplit
from ingestion.http import Client,SourceError
from ingestion.adapters.telegram import collect_telegram
from ingestion.adapters.instagram import collect_instagram
from ingestion.adapters.social import parse_post
from ingestion.provisional import tentative_post
from ingestion.run import atomic_json
from ingestion.models import valid_event
from ingestion.extraction import collect_website
from ingestion.render import render_page
from zoneinfo import ZoneInfo


class AuditClient(Client):
    def __init__(self,cache,timeout=10,reuse=False):
        super().__init__(timeout=timeout,delay=.5,retries=0)
        self.folder=cache;self.folder.mkdir(parents=True,exist_ok=True);self.reuse=reuse
    def fetch(self,url):
        key=self.folder/sha256(url.encode()).hexdigest()
        if self.reuse and key.with_suffix('.error').exists() and not key.with_suffix('.json').exists():
            failure=json.loads(key.with_suffix('.error').read_text())
            if (datetime.now(timezone.utc)-datetime.fromisoformat(failure['checked_at'])).total_seconds()<3600:raise SourceError(failure['error'],failure['status'],failure['attempted'])
        if self.reuse and key.with_suffix('.json').exists():
            meta=json.loads(key.with_suffix('.json').read_text())
            self.access_notes[url]=meta.get('access',{})
            self.resolved[urlsplit(url).hostname]=time.monotonic()
            self.resolved[urlsplit(meta['final_url']).hostname]=time.monotonic()
            return key.with_suffix('.html').read_text(),meta['final_url']
        try:html,final=super().fetch(url)
        except SourceError as exc:
            key.with_suffix('.error').write_text(json.dumps({'url':url,'error':str(exc),'status':exc.status,'attempted':exc.attempted,'checked_at':datetime.now(timezone.utc).isoformat()}))
            raise
        key.with_suffix('.html').write_text(html)
        key.with_suffix('.json').write_text(json.dumps({'url':url,'final_url':final,'access':self.access_notes.get(url,{}),'checked_at':datetime.now(timezone.utc).isoformat()}))
        return html,final

    def render(self,url):
        key=self.folder/('render-'+sha256(url.encode()).hexdigest())
        if self.reuse and key.with_suffix('.json').exists():
            meta=json.loads(key.with_suffix('.json').read_text());return key.with_suffix('.html').read_text(),meta['final_url']
        html,final=render_page(url)
        key.with_suffix('.html').write_text(html);key.with_suffix('.json').write_text(json.dumps({'url':url,'final_url':final}))
        return html,final


def audit_source(source,client,rules,max_pages):
    row={'source_id':source['source_id'],'url':source['url'],'platform':source['platform'],'institution_ids':source['institution_ids'],
        'publication_enabled':source.get('collection_enabled') is not False and not source.get('requires_identity_confirmation'),
        'checked_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'pages':[],'events':[],'issues':[]}
    try:
        if source['platform'] in ('telegram','instagram'):
            collection=collect_telegram(source['url'],client,limit=40,pages=2) if source['platform']=='telegram' else collect_instagram(source['url'])
            row.update(adapter=collection.adapter,posts_seen=len(collection.posts))
            for post in collection.posts:
                events,reason=parse_post(post)
                if reason:
                    candidate={'description':post.text,'primary_url':post.url,'published_at':post.published_at,'related_urls':list(post.related_urls)}
                    events+=tentative_post(candidate)
                    row['issues'].append({'url':post.url,'reason':reason})
                row['events']+=events
            row['status']='extracted' if row['events'] else 'no_events'
            return row
        rule=rules.get(source['source_id']) or rules.get(urlsplit(source['url']).hostname) or source.get('parser_config') or {}
        if isinstance(rule,str):rule=json.loads(rule)
        events,pages,issues,html,url=collect_website(source,client,rule,max_pages,datetime.now(ZoneInfo('Europe/Moscow')).date().isoformat())
        row.update(events=events,pages=pages,issues=issues,final_url=url,access=client.access_notes.get(source['url'],{}))
        row['events']=[e for e in row['events'] if valid_event(e)]
        row['status']='extracted' if row['events'] else 'no_events'
    except SourceError as exc:row.update(status=exc.status,error=str(exc),attempted=exc.attempted)
    except Exception as exc:row.update(status='parser_error',error=type(exc).__name__)
    return row


def run(catalog,rules,folder,workers=6,max_pages=3,reuse=False):
    groups=defaultdict(list)
    for source in catalog['sources']:groups[urlsplit(source['url']).hostname].append(source)
    rows=[]
    def group(sources):
        client=AuditClient(folder/'cache',reuse=reuse)
        return [audit_source(s,client,rules,max_pages) for s in sources]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(group,sources) for sources in groups.values()]
        for future in as_completed(futures):
            batch=future.result();rows+=batch
            for r in batch:print(f"{r['source_id']} {r['status']} {len(r['events'])} {r['url']}",flush=True)
            atomic_json(folder/'progress.json',{'completed':len(rows),'total':len(catalog['sources']),'sources':rows})
    rows.sort(key=lambda r:r['source_id'])
    institutions=[]
    for i in catalog['institutions']:
        linked=[r for r in rows if i['institution_id'] in r['institution_ids']]
        institutions.append({'institution_id':i['institution_id'],'name':i['name'],'source_ids':[r['source_id'] for r in linked],
            'sources_with_events':sum(bool(r['events']) for r in linked),'readable_sources':sum(r['status'] in ('extracted','no_events') for r in linked),
            'issues':[{'source_id':r['source_id'],'status':r['status'],'error':r.get('error')} for r in linked if not r['events']]})
    report={'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'source_count':len(rows),'institution_count':len(institutions),
        'statuses':dict(Counter(r['status'] for r in rows)),'institutions':institutions,'sources':rows}
    atomic_json(folder/'coverage.json',report)
    print(json.dumps({'statuses':report['statuses'],'institutions_with_extraction':sum(i['sources_with_events']>0 for i in institutions)},ensure_ascii=False),flush=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,default=Path('.local/source-audit'));p.add_argument('--workers',type=int,default=6)
    p.add_argument('--max-pages',type=int,default=6);p.add_argument('--reuse',action='store_true');p.add_argument('--publish',action='store_true');args=p.parse_args()
    catalog=json.loads(Path('catalog/catalog.json').read_text())
    report=run(catalog,json.loads(Path('editorial/overrides.json').read_text())['parser_rules'],args.folder,args.workers,args.max_pages,args.reuse)
    if args.publish:publish_report(report,catalog,json.loads(Path('public/data/events.json').read_text()),Path.cwd())



def publish_report(report,catalog,feed,root):
    """Publish a compact audit, without mistaking raw candidates for venue coverage."""
    import csv
    import io
    from ingestion.primary import is_aggregator
    by_id={i['institution_id']:i for i in catalog['institutions']}
    source_map={s['source_id']:s for s in catalog['sources']}
    health={s['source_id']:s for s in feed['sources']}
    rows=[]
    for original in report['sources']:
        row={k:v for k,v in original.items() if k!='events'}
        source=source_map[row['source_id']]
        document=source['url']
        if source['platform']=='telegram':
            from ingestion.adapters.telegram import telegram_identity
            try:
                channel,post=telegram_identity(document);document='https://t.me/s/'+channel+(f'/{post}' if post else '')
            except SourceError:document=None
        cached=root/'.local/source-audit/cache'/(sha256(document.encode()).hexdigest()+'.html') if document else None
        row['document_fetched_at']=datetime.fromtimestamp(cached.stat().st_mtime,timezone.utc).isoformat(timespec='seconds') if cached and cached.exists() else None
        row.update(candidate_count=len(original.get('events',[])),roles=source.get('roles',[]),
            aggregator=is_aggregator(source['url']),publication_status=health.get(row['source_id'],{}).get('status'),
            published_event_count=sum(e.get('source_id')==row['source_id'] or any(x.get('source_id')==row['source_id'] for x in e.get('evidence',[])) for e in feed['events']))
        row['publication_enabled']=row.get('publication_enabled',True) and row['publication_status']!='disabled'
        rows.append(row)
    institutions=[]
    for i in catalog['institutions']:
        linked=[r for r in rows if i['institution_id'] in r['institution_ids']]
        events=[e for e in feed['events'] if e['institution_id']==i['institution_id']]
        institutions.append({'institution_id':i['institution_id'],'name':i['name'],'monitor_state':i['monitor_state'],
            'sources':len(linked),'readable_sources':sum(r['status'] in ('extracted','no_events') for r in linked),
            'sources_with_candidates':sum(r['candidate_count']>0 and not r['aggregator'] for r in linked),
            'published_events':len(events),'current_or_upcoming_events':sum((e.get('end_date') or e['start_date'])>=datetime.now(ZoneInfo('Europe/Moscow')).date().isoformat() for e in events)})
    data={'generated_at':report['generated_at'],'source_count':len(rows),'institution_count':len(institutions),'statuses':dict(Counter(r['status'] for r in rows)),
        'scope':'Все URL каталога; до 6 дочерних страниц сайта на глубину 2, все текущие ссылки публичного API ММОМА (до 40), до 2 страниц Telegram. Архивы сайтов старше 90 дней не добавляются как новые события. Найденные кандидаты не означают подтверждённую московскую площадку.',
        'institutions':institutions,'sources':rows}
    atomic_json(root/'public/data/coverage.json',data)
    output=io.StringIO();writer=csv.writer(output,lineterminator='\n')
    writer.writerow(['source_id','площадки','URL','платформа','статус чтения','парсеры','проверено страниц','кандидатов','событий в афише','статус публикации','ошибка / замечания','проверено UTC','документ загружен UTC'])
    for r in rows:
        adapters=sorted({p['adapter'] for p in r['pages'] if p.get('adapter')}|({r['adapter']} if r.get('adapter') else set()))
        writer.writerow([r['source_id'],'; '.join(by_id[i]['name'] for i in r['institution_ids']),r['url'],r['platform'],r['status'],', '.join(adapters),len(r['pages']),r['candidate_count'],r['published_event_count'],r['publication_status'],r.get('error') or '; '.join(dict.fromkeys(x['reason'] for x in r['issues']))[:1200],r['checked_at'],r.get('document_fetched_at')])
    (root/'public/data/coverage.csv').write_text('\ufeff'+output.getvalue())
    labels={'extracted':'Есть кандидаты','no_events':'Анонсы не распознаны','manual':'Нужен API / экспорт','blocked':'Ограничен доступ','unavailable':'Нет соединения','review':'Нужна проверка','partial':'Прочитано частично','broken':'Страница удалена','parser_error':'Ошибка адаптера'}
    text=['# Аудит источников и площадок · 20 октября 2026','',f"Проверены **{len(rows)} источников и {len(institutions)} площадки**. Время завершения: {report['generated_at']}.",'',data['scope'],'','Это аудит извлечения, а не гарантия полноты афиши. Повторный разбор использует реальные сетевые ответы этого аудита; время загрузки документа хранится отдельно от времени разбора в CSV/JSON. Ноль кандидатов означает, что парсер не распознал анонс; это не доказательство отсутствия программы. Кандидаты иностранных, архивных и агрегаторских страниц не считаются подтверждением московского события. Настройки исключённых площадок и проверки принадлежности сохраняются.','', '## Методы','', '- JSON-LD, Microdata/RDFa (Extruct), RSS/Atom; специализированные адаптеры институций.', '- ChompJS: безопасный разбор Nuxt и JavaScript-литералов без исполнения кода; JSON встроенных календарей.', '- Trafilatura и Beautiful Soup: нестандартные заголовки, компактные даты, карточки программ, двухзначные годы.', '- Публичный API ММОМА: календарь выставок и событий, затем страницы отдельных программ и расписания сеансов.', '- Chromium/Playwright: выполнение JavaScript после неудачного чтения HTML и состояния страницы.', '- Telegram: две страницы публичной ленты, до 40 текстовых постов; API Telethon остаётся опцией.', '', 'Публичные страницы читаются в режиме `ROBOTS_POLICY=public`: robots.txt фиксируется в журнале, но его исключения не прекращают чтение. Сохраняются интервалы запросов, TLS и реальные HTTP-ошибки. `ROBOTS_POLICY=respect` включает прежнее поведение. Instagram без настроенного API остаётся ручным источником.','', '## Результаты чтения','', '| Результат | Источников |','|---|---:|']
    text += [f"| {labels.get(k,k)} | {v} |" for k,v in sorted(data['statuses'].items())]
    text+=['','## Все площадки','','«Кандидаты» — число собственных источников с извлечёнными данными; «Афиша» — реально опубликованные события, включая сохранённые предыдущими сборами.','','| Площадка | Источников | Прочитано | Кандидаты | Афиша | Сейчас / впереди |','|---|---:|---:|---:|---:|---:|']
    text += [f"| {i['name'].replace('|','/')} (`{i['institution_id']}`) | {i['sources']} | {i['readable_sources']} | {i['sources_with_candidates']} | {i['published_events']} | {i['current_or_upcoming_events']} |" for i in institutions]
    text+=['','## Все источники','','Полные ошибки и страницы: [JSON](../public/data/coverage.json). Таблица для проверки и фильтрации: [CSV](../public/data/coverage.csv).','','| Источник | Результат | Парсер | Кандидатов |','|---|---|---|---:|']
    for r in rows:
        adapters=sorted({p['adapter'] for p in r['pages'] if p.get('adapter')}|({r['adapter']} if r.get('adapter') else set()))
        text.append(f"| [{r['url']}]({r['url']}) | {labels.get(r['status'],r['status'])} | {', '.join(adapters) or '—'} | {r['candidate_count']} |")
    (root/'docs/source-coverage-2026-10-20.md').write_text('\n'.join(text)+'\n')
    return data


if __name__=='__main__':main()
