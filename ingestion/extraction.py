"""Shared static, embedded-state and browser extraction for audit and publication."""
import re
from datetime import date,timedelta
from collections import deque
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from ingestion.adapters import parse_jsonld,parse_feed,parse_html,discover_links
from ingestion.adapters.advanced import parse_advanced,russian_version,_dates,_first_days,publication_field
from ingestion.adapters.institutions import parse_institution,institution_links
from ingestion.adapters.state import parse_embedded
from ingestion.adapters.gallery1112 import current_project
from ingestion.http import SourceError
from ingestion.models import direct_url,event_type,normalized_title
from ingestion.render import render_page
from ingestion.adapters.public_api import mmoma_calendar


def parse_cards(html,url):
    """Read dated programme cards with a real detail link; ignore publication dates."""
    from urllib.parse import urljoin
    soup=BeautifulSoup(html,'html.parser');result=[]
    for node in soup.select('article,[class*="card"],.post,[class*="entry"],[class*="event-item"],.t-rec,a:has([class*="date"]):has([class*="title"])'):
        text=node.get_text(' ',strip=True)
        if len(text)>2200 or not re.search(r'20\d{2}|\d{1,2}/\d{1,2}/2\d\b',text):continue
        heading=node.select_one('h1,h2,h3,[class*="title"]')
        if not heading:continue
        title=heading.get_text(' ',strip=True)
        if normalized_title(title) in ('current exhibition','выставки','события','афиша','exhibitions','events','programme','upcoming exhibitions'):continue
        if not 3<len(title)<220 or re.search(r'/(?:artists?|museum|product)/',urlsplit(url).path):continue
        targets=[]
        for a in ([node] if node.name=='a' and node.get('href') else [])+node.select('a[href]'):
            target=urljoin(url,a['href'])
            if direct_url(target) and urlsplit(target).hostname==urlsplit(url).hostname and not re.search(r'/(?:artists?|authors?|museum|product)/|\.(?:jpg|pdf|png)$',urlsplit(target).path,re.I):targets.append(target)
        targets=list(dict.fromkeys(targets))
        if len(targets)!=1:continue
        dates=[]
        for field in node.select('time,[class*="date"],[class*="period"],p,span,div,i,em'):
            value=field.get_text(' ',strip=True)
            if len(value)>150 or publication_field(field):continue
            d=_dates(value)
            if d['start_date']:dates.append((d,value))
        ranges={(d['start_date'],d['end_date']) for d,_ in dates if d['end_date']}
        kind=event_type(title+' '+text[:160])
        if len(ranges)==1:
            start,end=next(iter(ranges))
            if kind=='other':
                if re.search(r'/exhibitions?/|выставк|exhibition',targets[0]+' '+text+' '+' '.join(node.get('class',[])),re.I):kind='exhibition'
                else:continue
            if start!=end and kind not in ('exhibition','festival'):continue
            chosen=next((d,v) for d,v in dates if (d['start_date'],d['end_date'])==(start,end))
        elif not ranges and kind not in ('other','exhibition') and len({d['start_date'] for d,_ in dates})==1:chosen=dates[0]
        else:continue
        d,evidence=chosen
        result.append(dict(title=title,event_type=kind,primary_url=targets[0],start_date=d['start_date'],end_date=d['end_date'],
            start_time=None if kind=='exhibition' else d['start_time'],confidence='programme_card',date_basis='explicit_date_block',date_evidence=evidence,title_basis='event_heading'))
    return _first_days(list({(e['primary_url'],e['start_date'],e['event_type'],normalized_title(e['title'])):e for e in result}.values()))


def extract(html,url,context=None,rule=None):
    for name,parser in [('jsonld',lambda:parse_jsonld(html,url) if 'ld+json' in html else []),('institution',lambda:parse_institution(html,url,context)),
        ('scoped_html',lambda:parse_html(html,url,rule) if rule or re.search(r'<article\b',html,re.I) else []),('embedded_calendar',lambda:parse_embedded(html,url) if re.search(r'__NUXT__|__NEXT_DATA__|application/json|source-state-json',html) else []),
        ('extruct_trafilatura',lambda:parse_advanced(html,url,context)),('programme_cards',lambda:parse_cards(html,url) if urlsplit(url).hostname not in {'ges-2.org','garagemca.org','ruarts.foundation','centrezotov.ru','art.hse.ru','mmoma.ru','11-12gallery.com'} else [])]:
        events=parser()
        if events:return events,name
    return [],None


def collect_website(source,client,rule=None,max_pages=6,observed_on=None,browser=True):
    html,url=client.fetch(source['url']);localized=russian_version(html,url)
    if localized:html,url=client.fetch(localized)
    context={'current_project_url':current_project(html,url),'observed_on':observed_on}
    if source['platform']=='rss' or html.lstrip().startswith(('<?xml','<rss','<feed')):
        return parse_feed(html,url),[{'url':url,'adapter':'feed'}],[],html,url
    queue=deque([(url,html,0)]);visited=set();events=[];pages=[];issues=[];rendered=False;page_limit=max_pages
    if urlsplit(url).hostname=='mmoma.ru':
        try:
            events,api_links,api_pages=mmoma_calendar(url,client)
            for page in api_pages:context.setdefault('event_types',{}).update(page.pop('event_types',{}))
            pages+=api_pages
            if max_pages:
                page_limit=max(max_pages,min(len(api_links),40))
                queue.extend((link,None,1) for link in api_links[:40])
        except SourceError as exc:issues.append({'url':url,'status':exc.status,'reason':str(exc)})
    while queue and len(visited)<=page_limit:
        target,body,depth=queue.popleft()
        if target in visited:continue
        visited.add(target)
        try:
            if body is None:body,target=client.fetch(target)
            parsed,adapter=extract(body,target,context,rule)
            # Render a JavaScript shell only after static markup and state have failed.
            if browser and not parsed and not events and not rendered and re.search(r'id=["\'](?:app|__nuxt|__next|root)["\']',body,re.I) and (depth>0 or not discover_links(body,target,1)):
                rendered=True
                try:
                    rendered_body,rendered_url=client.render(target) if hasattr(client,'render') else render_page(target)
                    parsed,adapter=extract(rendered_body,rendered_url,context,rule)
                    if parsed:adapter='chromium:'+str(adapter)
                    body=rendered_body
                except SourceError as exc:issues.append({'url':target,'status':exc.status,'reason':str(exc)})
            if parsed and adapter!='programme_cards':
                for event in parsed:
                    prior=next((e for e in events if e.get('confidence')=='institution_public_api' and e['primary_url']==event['primary_url'] and e['event_type']==event['event_type']),None)
                    if prior and (prior.get('start_date'),prior.get('end_date'))!=(event.get('start_date'),event.get('end_date')):
                        event.update(review_status='tentative',uncertainties=list(event.get('uncertainties',[]))+[f"Даты в официальном календаре ({prior.get('start_date')} — {prior.get('end_date')}) отличаются от страницы события ({event.get('start_date')} — {event.get('end_date')}). Показан период со страницы события; требуется уточнение."])
                keys={(e['primary_url'],e['event_type']) for e in parsed}
                events=[e for e in events if (e['primary_url'],e['event_type']) not in keys]
            if adapter=='programme_cards':
                strong={(e['primary_url'],e['event_type']) for e in events if e.get('confidence')!='programme_card'}
                parsed=[e for e in parsed if (e['primary_url'],e['event_type']) not in strong]
            events+=parsed
            soup=BeautifulSoup(body,'html.parser')
            pages.append({'url':target,'adapter':adapter,'events':len(parsed),'title':soup.title.get_text(' ',strip=True)[:160] if soup.title else ''})
            evidence_article=source.get('roles') and 'announcements' not in source['roles'] and direct_url(source['url']) and len(urlsplit(source['url']).path.strip('/').split('/'))>1 and not re.search(r'/(?:about|contacts?)(?:/|$)',urlsplit(source['url']).path)
            if depth<2 and not evidence_article:
                links=list(dict.fromkeys(institution_links(body,target,max_pages)+discover_links(body,target,max_pages)))
                if depth==0 and re.search(r'/(?:about|contacts?)(?:/|$)',urlsplit(target).path):
                    links.insert(0,urlsplit(target)._replace(path='/',query='',fragment='').geturl())
                for link in links:
                    if link not in visited and link not in [x[0] for x in queue]:queue.append((link,None,depth+1))
        except SourceError as exc:issues.append({'url':target,'status':exc.status,'reason':str(exc)})
    if urlsplit(url).hostname=='mmoma.ru':
        for event in events:
            if event['event_type']=='exhibition' and not urlsplit(event['primary_url']).path.startswith('/visit/gallery/'):
                event['event_type']='other'
        events=_first_days(events)
    if observed_on:
        earliest=(date.fromisoformat(observed_on)-timedelta(days=90)).isoformat()
        events=[e for e in events if (e.get('end_date') or e.get('start_date') or '')>=earliest]
    return events,pages,issues,html,url
