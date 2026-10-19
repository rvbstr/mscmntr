"""Run a partial-failure-safe refresh. Public JSON never contains test fixtures."""
import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from ingestion.import_catalog import ROOT
from ingestion.http import Client, SourceError
from ingestion.adapters import parse_jsonld, parse_feed, parse_html, discover_links
from ingestion.adapters.advanced import parse_advanced, russian_version
from ingestion.adapters.social import parse_post
from ingestion.adapters.telegram import collect_telegram
from ingestion.adapters.instagram import collect_instagram, configured_instagram_api
from ingestion.adapters.institutions import parse_institution, institution_links
from ingestion.models import canonical_url, direct_url, stable_id, deduplicate, link_parents, event_signature, TYPES, valid_event, complete_event
from ingestion.editorial import load_overrides, apply_overrides


def now_iso(): return datetime.now(timezone.utc).isoformat(timespec='seconds')


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False,encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n'); tmp=f.name
    os.replace(tmp,path)


def due(metadata,now=None):
    last=metadata.get('last_completed_refresh')
    if not last: return True
    try: return ((now or datetime.now(timezone.utc))-datetime.fromisoformat(last)).total_seconds()>=72*3600
    except (ValueError,TypeError): return True


def seed_candidates(catalog,client,source,institution):
    """Use catalog URLs for discovery; re-extract content instead of publishing examples."""
    urls={seed['verification_url'] for seed in catalog.get('seed_events',[])
          if seed['institution_id']==institution['institution_id']
          and urlsplit(seed['verification_url']).hostname==urlsplit(source['url']).hostname}
    result=[]
    for url in sorted(urls):
        html,final=client.fetch(url)
        result.extend(parse_jsonld(html,final) or parse_institution(html,final))
    return result


def refresh(catalog,overrides,previous,client,only=None,max_pages=3,social_options=None):
    social_options=social_options or {}
    instagram_api=social_options.get('instagram_api')
    timestamp=now_iso(); institutions={i['institution_id']:dict(i) for i in catalog['institutions']}
    for iid,priority in overrides['priorities'].items(): institutions[iid]['monitoring_priority']=priority
    old_health={h['source_id']:h for h in previous.get('sources',[])}
    old_events=[dict(e,evidence=[dict(x) for x in e.get('evidence',[])]) for e in previous.get('events',[]) if e['institution_id'] in institutions and (overrides.get('publication_policy')=='include_tentative' or e.get('review_status')!='tentative')]; candidates=[]; review=[]; reports=[]; successful=0; checked_successfully=set(); refreshed_urls=set()
    priorities={'high':0,'normal':1,'low':2}
    sources=sorted(catalog['sources'],key=lambda s:min([priorities.get(institutions[i].get('monitoring_priority'),1) for i in s['institution_ids']] or [1]))
    for source in sources:
        sid=source['source_id']; old=old_health.get(sid,{})
        report={**old,'source_id':sid,'status':old.get('status','review'),'last_attempted_at':old.get('last_attempted_at'),
                'last_successful_extraction':old.get('last_successful_extraction'),'new_events':0,'detected_events':old.get('detected_events',0),'error':old.get('error')}
        linked=[institutions[i] for i in source['institution_ids']]
        if only and sid not in only:
            reports.append(report); continue
        if source.get('collection_enabled') is False or sid in overrides['disabled_sources'] or all(i['monitor_state'] in ('excluded','discovery') for i in linked):
            report.update(status='disabled',error=source.get('collection_disabled_reason') or 'Источник сохранён в каталоге; автоматический сбор отключён'); reports.append(report); continue
        if source['platform'] in ('vk','linkhub'):
            report.update(status='manual',error='Автоматический доступ не настроен. Используйте оригинал и редакционные записи.'); reports.append(report); continue
        report['last_attempted_at']=now_iso()
        report['detected_events']=0
        try:
            extracted=[]; page_errors=[]; review_start=len(review); collection=None; social_verified=set()
            if source['platform'] in ('telegram','instagram'):
                if source['platform']=='telegram':
                    collection=collect_telegram(source['url'],client,limit=social_options.get('limit',20))
                else:
                    if instagram_api is None:instagram_api=configured_instagram_api()
                    collection=collect_instagram(source['url'],instagram_api,social_options.get('instagram_export_dir') or os.environ.get('INSTAGRAM_EXPORT_DIR',str(ROOT/'.local/instagram')),limit=social_options.get('limit',20))
                report.update(adapter=collection.adapter,posts_seen=len(collection.posts))
                if collection.live:
                    social_verified={post.url for post in collection.posts}
                    refreshed_urls.update(social_verified)
                for post in collection.posts:
                    parsed,reason=parse_post(post)
                    if reason:review.append({'source_id':sid,'candidate':{'primary_url':post.url,'published_at':post.published_at,'description':post.text[:16000]},'reason':reason})
                    if collection.live:extracted.extend(parsed)
                    else:
                        for item in parsed:review.append({'source_id':sid,'candidate':item,'reason':collection.note})
            else:
                html,url=client.fetch(source['url'])
                localized=russian_version(html,url) if source['platform']=='website' else None
                if localized: html,url=client.fetch(localized)
                if source['platform']=='rss' or html.lstrip().startswith(('<?xml','<rss','<feed')):
                    extracted=parse_feed(html,url)
                else:
                    rule=overrides['parser_rules'].get(sid) or overrides['parser_rules'].get(urlsplit(url).hostname) or source.get('parser_config') or {}
                    if isinstance(rule,str):rule=json.loads(rule)
                    extracted=parse_jsonld(html,url) or parse_institution(html,url) or parse_html(html,url,rule) or parse_advanced(html,url)
                    links=list(dict.fromkeys(institution_links(html,url,max_pages)+discover_links(html,url,max_pages)))[:max_pages]
                    for link in links:
                        try:
                            body,final=client.fetch(link);extracted.extend(parse_jsonld(body,final) or parse_institution(body,final) or parse_html(body,final,rule) or parse_advanced(body,final))
                        except SourceError as exc:page_errors.append(str(exc))
            if any(e.get('confidence') in ('readable_html','rich_metadata','inferred_opening') for e in extracted): report['adapter']='trafilatura_extruct'
            successful+=1; checked_successfully.add(sid); accepted=[]; seen=set()
            # Ambiguous shared website ownership is sent for editorial attribution.
            relevant=[i for i in linked if any(r['institution_id']==i['institution_id'] and r['source_id']==sid and r.get('role')=='announcements' for r in catalog['institution_sources'])]
            for item in extracted:
                if source.get('requires_identity_confirmation'):
                    review.append({'source_id':sid,'candidate':item,'reason':'Принадлежность канала требует внешнего подтверждения; автоматическая атрибуция отключена'}); continue
                if source.get('requires_location_confirmation') and item.get('geography_scope') not in ('moscow','moscow_region'):
                    review.append({'source_id':sid,'candidate':item,'reason':'Канал публикует события разных городов; нужно подтверждение московской площадки'}); continue
                if item.get('review_status')=='tentative' and overrides.get('publication_policy')!='include_tentative':
                    review.append({'source_id':sid,'candidate':item,'reason':'Первый день выставки: время и формат открытия требуют уточнения'}); continue
                if not valid_event(item):
                    review.append({'source_id':sid,'candidate':item,'reason':'Нужны точная дата и отдельная страница события'}); continue
                owners=relevant
                if len(owners)!=1:
                    # Canonical event/source relationships can resolve a dedicated evidence URL.
                    owners=[i for i in linked if any(seed['institution_id']==i['institution_id']
                            and canonical_url(seed['verification_url'])==canonical_url(item['primary_url'])
                            and event_signature(seed)==event_signature(dict(item,institution_id=i['institution_id']))
                            for seed in catalog.get('seed_events',[]))]
                if len(owners)!=1:
                    review.append({'source_id':sid,'candidate':item,'reason':'Нужно уточнить связь события с пространством'}); continue
                try:
                    if item['primary_url'] not in social_verified:client.fetch(item['primary_url'])
                    event=complete_event(item,owners[0],source,timestamp)
                    if event['event_id'] not in seen: accepted.append(event); seen.add(event['event_id'])
                except SourceError as exc:
                    for old_event in old_events:
                        if canonical_url(old_event['primary_url'])==canonical_url(item['primary_url']):
                            old_event.update(link_status=exc.status,link_checked_at=now_iso())
                            for evidence in old_event.get('evidence',[]):
                                if canonical_url(evidence['url'])==canonical_url(item['primary_url']):evidence.update(status=exc.status,checked_at=now_iso())
                    review.append({'source_id':sid,'candidate':item,'reason':str(exc),'link_status':exc.status})
            if len(relevant)==1 and not accepted and source['platform'] not in ('telegram','instagram'):
                try:
                    for item in seed_candidates(catalog,client,source,relevant[0]):
                        event=complete_event(item,relevant[0],source,timestamp)
                        if event['event_id'] not in seen: accepted.append(event); seen.add(event['event_id'])
                except SourceError as exc:
                    review.append({'source_id':sid,'reason':'Повторная проверка примера: '+str(exc)})
            old_keys={event_signature(e) for e in old_events}
            new=sum(event_signature(e) not in old_keys for e in accepted)
            incomplete=bool(page_errors or len(review)>review_start)
            report.update(status='working' if accepted and not incomplete else 'partial',last_successful_check=timestamp,detected_events=sum(e.get('review_status')!='tentative' for e in accepted),new_events=new,
                          error=('Часть страниц или кандидатов требует проверки. Подтверждённые события сохранены.' if incomplete else None) if accepted else 'Страница доступна; подтверждённые события не извлечены. Нужен точный адаптер или редакционная проверка.')
            if collection and not collection.live:report.update(status='review',last_successful_check=old.get('last_successful_check'),error=collection.note)
            elif collection and source.get('requires_identity_confirmation'):report.update(status='review',error='Публичная лента прочитана; принадлежность канала требует внешнего подтверждения. События отправляются на проверку.')
            elif collection and not accepted:report['error']='Публикации прочитаны; подтверждённые анонсы не извлечены. Неоднозначные записи отправлены на проверку.'
            if accepted: report['last_successful_extraction']=timestamp
            candidates.extend(accepted)
        except SourceError as exc:
            report.update(status=exc.status,error=str(exc))
            if not exc.attempted:report['last_attempted_at']=old.get('last_attempted_at')
        except Exception as exc:
            report.update(status='review',error='Ошибка адаптера: '+type(exc).__name__)
        reports.append(report)
        print(f"{sid} {report['status']}: {report.get('detected_events',0)}",flush=True)
    for item in overrides['manual_events']:
        source={'source_id':'EDITORIAL','platform':'editorial'}
        if not valid_event(item): raise ValueError('Неверное ручное событие: '+item['event_id'])
        try:
            client.fetch(item['primary_url']); candidates.append(complete_event(item,institutions[item['institution_id']],source,timestamp))
        except SourceError as exc:
            if item.get('editor_verified_at'):
                event=complete_event(item,institutions[item['institution_id']],source,timestamp)
                event.update(link_status=exc.status,link_checked_at=timestamp,confidence='editorial',verified_at=item['editor_verified_at'])
                event['evidence'][0]['status']=exc.status; candidates.append(event)
            else: review.append({'candidate':item,'reason':str(exc)})
    old_events=[e for e in old_events if not (e.get('review_status')=='tentative' and e['primary_url'] in refreshed_urls)]
    merged=deduplicate(old_events+candidates)
    # Preserve first-discovery times, update change timestamps only for substantive changes.
    by_id={e['event_id']:e for e in old_events}
    for e in merged:
        old=by_id.get(e['event_id'])
        if old and all(old.get(k)==e.get(k) for k in ('title','start_date','end_date','start_time','description','primary_url')):
            e['last_updated_at']=old.get('last_updated_at',timestamp)
    for eid,changes in overrides['corrections'].items():
        if changes.get('primary_url') and any(e['event_id']==eid and e['primary_url']!=changes['primary_url'] for e in merged):
            try: client.fetch(changes['primary_url'])
            except SourceError as exc: raise ValueError(f'Исправленный первоисточник {eid} не подтверждён: {exc}')
    # Keep unresolved candidates when their source could not be checked this run.
    checked=checked_successfully
    retained=[r for r in previous.get('review',[]) if r.get('source_id') not in checked and r.get('source_id') in {s['source_id'] for s in sources}]
    review=list({json.dumps(r,ensure_ascii=False,sort_keys=True):r for r in retained+review}.values())
    if overrides.get('publication_policy') == 'include_tentative':
        from ingestion.provisional import publish_review
        tentative, review = publish_review(catalog, review, reports, timestamp)
        merged = deduplicate(merged + tentative)
    merged=apply_overrides(merged,overrides)
    if any(not valid_event(e) for e in merged): raise ValueError('Правки создали событие с неверной датой или ссылкой')
    merged.sort(key=lambda e:(e['start_date'],e.get('start_time') or '23:59',e['title']))
    merged=link_parents(merged)
    from ingestion.provisional import annotate_reports
    annotate_reports(reports, merged)
    completed=now_iso()
    previous_meta=previous.get('metadata',{})
    metadata={**previous_meta,'schema_version':'1.0','timezone':'Europe/Moscow','last_attempted_refresh':timestamp,
              'last_completed_refresh':completed if not only else previous_meta.get('last_completed_refresh'),
              'last_successful_update':completed if successful else previous_meta.get('last_successful_update'),
              'generated_at':completed,'catalog_updated_on':catalog['metadata']['updated_on'],
              'source_count':len(sources),'successful_sources_this_run':successful,'event_count':len(merged),
              'review_count':len(review),'publication_policy':overrides.get('publication_policy','verified_only'),'tentative_count':sum(e.get('review_status')=='tentative' for e in merged),'partial':any(s['status'] not in ('working','disabled') for s in reports),
              'run_status':'partial' if successful else 'blocked','refresh_interval_hours':72,
              'scan_options':{'child_pages_per_source':max_pages,'source_ids':only or None}}
    reports.sort(key=lambda s:s['source_id'])
    return {'metadata':metadata,'events':merged,'sources':reports},review


def main():
    p=argparse.ArgumentParser(description='Проверка публичных источников афиши')
    p.add_argument('--publish-review',action='store_true',help='Опубликовать текущую очередь без сетевого сбора'); p.add_argument('--scheduled',action='store_true'); p.add_argument('--source',action='append')
    p.add_argument('--social-posts',type=int,default=20);p.add_argument('--instagram-export-dir',type=Path);p.add_argument('--max-pages',type=int,default=3); p.add_argument('--timeout',type=int,default=12)
    args=p.parse_args()
    catalog_path=ROOT/'catalog/catalog.json'
    if not catalog_path.exists():
        print('Каталог отсутствует. Выполните python -m ingestion.import_catalog'); return 2
    catalog=json.loads(catalog_path.read_text()); output=ROOT/'public/data/events.json'
    previous=json.loads(output.read_text()) if output.exists() else {'metadata':{},'events':[],'sources':[]}
    review_path=ROOT/'public/data/review.json'
    if review_path.exists(): previous['review']=json.loads(review_path.read_text()).get('items',[])
    if args.scheduled and not due(previous.get('metadata',{})):
        print('72 часа ещё не прошли; данные сохранены без изменений.'); return 0
    overrides=load_overrides(ROOT/'editorial/overrides.json',catalog)
    if args.publish_review:
        from ingestion.provisional import publish_snapshot
        feed,review=publish_snapshot(catalog,overrides,previous,now_iso())
    else:
        feed,review=refresh(catalog,overrides,previous,Client(timeout=args.timeout),args.source,args.max_pages,{'limit':max(1,min(args.social_posts,50)),'instagram_export_dir':args.instagram_export_dir})
    public_catalog={k:v for k,v in catalog.items() if k!='seed_events'}
    public_catalog['institutions']=[dict(i,monitoring_priority=overrides['priorities'].get(i['institution_id'],i['monitoring_priority'])) for i in catalog['institutions']]
    atomic_json(ROOT/'public/data/catalog.json',public_catalog)
    atomic_json(output,feed); atomic_json(ROOT/'public/data/review.json',{'generated_at':now_iso(),'items':review})
    summary={'metadata':feed['metadata'],'statuses':{s:sum(r['status']==s for r in feed['sources']) for s in {r['status'] for r in feed['sources']}}}
    atomic_json(ROOT/'public/data/report.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    # Visible, actionable failure if no fetch succeeded. Existing data stays intact.
    return 0 if args.publish_review or feed['metadata']['successful_sources_this_run'] else 2

if __name__=='__main__': raise SystemExit(main())
