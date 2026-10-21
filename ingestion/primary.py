"""Keep discovery aggregators separate from an institution's own announcements."""
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
from ingestion.models import canonical_url, direct_url

AGGREGATOR_DOMAINS={'ewert.ru','afisha.ru'}
PRIMARY_REASON='Нужен первоисточник институции; агрегатор используется только для поиска.'


def is_aggregator(url):
    host=(urlsplit(url or '').hostname or '').lower()
    return any(host==domain or host.endswith('.'+domain) for domain in AGGREGATOR_DOMAINS)


def source_authority(catalog,source,institution):
    if is_aggregator(source['url']):return 'aggregator'
    relations=[r for r in catalog.get('institution_sources',[]) if r['source_id']==source['source_id'] and r['institution_id']==institution['institution_id']]
    if any(r.get('officiality')=='partner' for r in relations):return 'partner'
    if any(r.get('officiality') in ('official','editor_approved') for r in relations):return 'official'
    host=urlsplit(source['url']).hostname
    if host and host==urlsplit(institution.get('evidence_url') or '').hostname:return 'official'
    return 'unknown'


def official_links(html,url,catalog):
    hosts={urlsplit(s['url']).hostname for s in catalog['sources'] if s['platform']=='website' and not is_aggregator(s['url'])}
    result=[]
    for anchor in BeautifulSoup(html,'html.parser').select('a[href]'):
        target=urljoin(url,anchor['href'])
        if urlsplit(target).hostname in hosts and direct_url(target) and canonical_url(target) not in result:
            result.append(canonical_url(target))
    return result


def require_primary_sources(events,review):
    kept=[]
    existing={canonical_url((r.get('candidate') or {}).get('primary_url') or '') for r in review}
    for event in events:
        if not is_aggregator(event.get('primary_url')) and event.get('source_authority')!='aggregator':
            kept.append(event);continue
        if canonical_url(event['primary_url']) not in existing:
            review.append({'source_id':event.get('source_id'),'candidate':dict(event),'reason':PRIMARY_REASON,
                'link_status':event.get('link_status'),'link_checked_at':event.get('link_checked_at')})
            existing.add(canonical_url(event['primary_url']))
    return kept,review
