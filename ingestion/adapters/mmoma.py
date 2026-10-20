"""Read MMOMA's scoped exhibition header; opening hours are not a vernissage."""
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from ingestion.dates import extract_dates


def parse_mmoma(html,url):
    if not re.match(r'^/visit/gallery/[^/]+(?:/description)?/?$',urlsplit(url).path):return []
    soup=BeautifulSoup(html,'html.parser');root=soup.select_one('main')
    if root is None:return []
    heading=root.select_one('h1');venue=root.select_one('h3 a[href*="/know/building/"]')
    if heading is None or venue is None:return []
    periods=[]
    for node in root.select('div,time'):
        text=node.get_text(' ',strip=True)
        if re.fullmatch(r'\d{2}\.\d{2}\.20\d{2}\s*[-–—]\s*\d{2}\.\d{2}\.20\d{2}',text):
            periods.append((extract_dates(text),text))
    if len({(d['start_date'],d['end_date']) for d,_ in periods})!=1:return []
    dates,text=periods[0]
    if not dates['start_date'] or not dates['end_date']:return []
    return [dict(title=' '.join(heading.get_text(' ',strip=True).split()),title_basis='event_heading',
        event_type='exhibition',primary_url=url,start_date=dates['start_date'],end_date=dates['end_date'],start_time=None,
        venue_name=venue.get_text(' ',strip=True).title(),date_basis='explicit_date_block',date_evidence=text,
        source_authority='official',confidence='institution_html')]
