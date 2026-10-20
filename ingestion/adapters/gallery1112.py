"""11.12's current project has scoped dates but omits the year."""
from datetime import date, timedelta
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates
from ingestion.models import canonical_url
from ingestion.adapters.advanced import _first_days


def current_project(html,url):
    if urlsplit(url).hostname!='11-12gallery.com':return None
    for a in BeautifulSoup(html,'html.parser').select('a[href]'):
        if a.get_text(' ',strip=True).casefold()=='текущий проект':
            target=urljoin(url,a['href'])
            if urlsplit(target).hostname=='11-12gallery.com' and '/exhibitions/' in urlsplit(target).path:return target
    return None


def parse_1112(html,url,context=None):
    if not re.match(r'^/exhibitions/[^/]+/?$',urlsplit(url).path):return []
    soup=BeautifulSoup(html,'html.parser');root=soup.select_one('section.exhibition')
    if root is None:return []
    title=root.select_one('h1 .exhibition__name');artist=root.select_one('h1 .exhibition__author');block=root.select_one('h2.exhibition__title')
    if title is None or block is None:return []
    text=block.get_text(' ',strip=True);dates=extract_dates(text);inferred=False
    if not dates['start_date']:
        context=context or {}
        if canonical_url(context.get('current_project_url') or '')!=canonical_url(url):return []
        try:observed=date.fromisoformat(context['observed_on'])
        except (KeyError,ValueError):return []
        periods=[]
        for year in (observed.year-1,observed.year,observed.year+1):
            candidate=extract_dates(text,year)
            if not candidate['start_date'] or not candidate['end_date']:continue
            start=date.fromisoformat(candidate['start_date']);end=date.fromisoformat(candidate['end_date'])
            if start<=observed<=end or observed<start<=observed+timedelta(days=45):periods.append(candidate)
        if len(periods)!=1:return []
        dates=periods[0];inferred=True
    if not dates['end_date']:return []
    name=title.get_text(' ',strip=True)
    if artist:name=artist.get_text(' ',strip=True)+'. '+name
    base=dict(title=name,title_basis='event_heading',event_type='exhibition',primary_url=url,start_date=dates['start_date'],
        end_date=dates['end_date'],start_time=None,date_evidence=text,confidence='institution_html',source_authority='official',
        date_basis='current_project_context' if inferred else 'explicit_date_block')
    if inferred:base.update(review_status='tentative',uncertainties=['Год не указан на странице; определён по периоду проекта, отмеченного галереей как текущий.'])
    return _first_days([base])
