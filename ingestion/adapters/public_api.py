"""Public read-only API discovery for calendars with empty server-rendered lists."""
import json
from urllib.parse import urlencode,urljoin,urlsplit
from ingestion.dates import extract_dates
from ingestion.models import event_type
from ingestion.http import SourceError

VENUES={'музейсидура':'Музей Вадима Сидура · ММОМА','петровка25':'ММОМА, Петровка, 25','гоголевский10':'ММОМА, Гоголевский бульвар, 10','ермолаевский17':'ММОМА, Ермолаевский переулок, 17','музейналбандяна':'Музей-мастерская Д. А. Налбандяна · ММОМА'}


def mmoma_calendar(url,client):
    """Resolve current list IDs from the site's own API, rather than hard-coding them."""
    if urlsplit(url).hostname!='mmoma.ru' or urlsplit(url).path.rstrip('/') not in ('/visit/events','/visit/gallery'):return [],[],[]
    events=[];links=[];pages=[]
    for path in ['/visit/gallery','/visit/events']:
        endpoint='https://mmoma.ru/api/page?'+urlencode({'path':path,'lang':'ru'})
        raw,_=client.fetch(endpoint)
        try:page=json.loads(raw);identifier=page['id']
        except (ValueError,TypeError,KeyError):raise SourceError('API ММОМА: не найден идентификатор календаря','review')
        if not isinstance(identifier,int):raise SourceError('API ММОМА: неверный идентификатор','review')
        endpoint=f'https://mmoma.ru/api/page/{identifier}/children?lang=ru'
        raw,_=client.fetch(endpoint)
        try:items=json.loads(raw)
        except ValueError:raise SourceError('API ММОМА: неверный JSON','review')
        if not isinstance(items,list):raise SourceError('API ММОМА: изменился формат календаря','review')
        count=0;event_types={}
        for item in items:
            target=(item.get('redirectPage') or {}).get('path') or item.get('path')
            if not isinstance(target,str) or not target.startswith('/'):continue
            target=urljoin(url,target);links.append(target)
            start=extract_dates(item.get('periodStart') or item.get('date') or '')['start_date']
            end=extract_dates(item.get('periodEnd') or '')['start_date']
            tags=[t.get('title','') for t in item.get('tags',[])]
            kind='exhibition' if path.endswith('/gallery') else event_type(' '.join(tags)+' '+item.get('title','')+' '+(item.get('announcement') or ''))
            if path.endswith('/events') and kind=='exhibition':kind='other'
            event_types[target]=kind
            # A course interval is not a schedule of its separate sessions.
            if not start or (kind!='exhibition' and end and start!=end):continue
            event=dict(title=item['title'],event_type=kind,primary_url=target,start_date=start,end_date=end if kind=='exhibition' else None,
                start_time=None,confidence='institution_public_api',source_authority='official',title_basis='event_heading',date_basis='explicit_api_fields',
                date_evidence=f"{item.get('periodStart')} — {item.get('periodEnd')}",api_url=endpoint)
            venue=next((VENUES[t] for t in tags if t in VENUES),None)
            if venue:event['venue_name']=venue
            events.append(event);count+=1
        pages.append({'url':endpoint,'adapter':'mmoma_public_api','events':count,'items':len(items),'event_types':event_types})
    return events,links,pages
