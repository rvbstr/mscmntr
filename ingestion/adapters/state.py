"""Extract explicit calendar fields from JSON APIs and hydrated page state."""
import json
import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from ingestion.adapters.structured import _iso
from ingestion.models import direct_url,event_type,normalized_title
from ingestion.dates import extract_dates
import chompjs
from ingestion.adapters.advanced import _first_days

START=('startDate','dateStart','start_date','startsAt','date_from','dateFrom','date_begin','start_at')
END=('endDate','dateEnd','end_date','endsAt','date_to','dateTo','date_end','end_at')


def parse_state(data,url):
    found=[]
    def text(value):
        if isinstance(value,dict):return text(value.get('ru') or value.get('rendered') or value.get('title'))
        if value in ('null','undefined'):return None
        return value if isinstance(value,str) else None
    def walk(node):
        if isinstance(node,list):
            for child in node:walk(child)
        elif isinstance(node,dict):
            start=next((node[k] for k in START if isinstance(node.get(k),str)),None)
            translation=node.get('translation') if isinstance(node.get('translation'),dict) else {}
            title=text(node.get('titleRu')) or text(node.get('nameRu')) or text(node.get('title')) or text(node.get('name')) or text(translation.get('title'))
            if start and title:
                day,clock=_iso(start);finish=next((node[k] for k in END if isinstance(node.get(k),str)),None);end,endclock=_iso(finish)
                if not day:day=extract_dates(start)['start_date']
                if finish and not end:end=extract_dates(finish)['start_date']
                target=node.get('url') or node.get('href') or node.get('permalink') or node.get('link')
                if isinstance(target,dict):target=target.get('url')
                path=node.get('fullPath') or node.get('path')
                if not target and isinstance(path,str):target=path
                target=urljoin(url,target) if isinstance(target,str) else url
                kind=event_type(' '.join(str(node.get(k) or '') for k in ('eventType','event_type','type','subtype','category'))+' '+title)
                if kind=='other' and re.search(r'/exhibitions?/|/visit/gallery/',urlsplit(target).path):kind='exhibition'
                if kind=='other' and end and node.get('isCurrent') is not None:kind='exhibition'
                # Exhibition CMS timestamps often contain an arbitrary clock, not a session.
                if kind=='exhibition':
                    if re.match(r'^20\d{2}-\d{2}-\d{2}',start):day=start[:10]
                    if finish and re.match(r'^20\d{2}-\d{2}-\d{2}',finish):end=finish[:10]
                # A long programme interval is not an individual tour or workshop.
                if kind not in ('exhibition','other') and day and end and day!=end:day=None
                if day and kind!='other' and direct_url(target):
                    artist=text(node.get('artistNameRu')) or text(node.get('artistName'))
                    if artist and artist not in title:title=artist+'. '+title
                    found.append(dict(title=BeautifulSoup(title,'html.parser').get_text(' ',strip=True),event_type=kind,
                        primary_url=target,start_date=day,end_date=end,start_time=None if kind=='exhibition' else clock,
                        end_time=None if kind=='exhibition' else endclock,confidence='embedded_calendar',date_basis='explicit_api_fields',
                        date_evidence=f'{start}'+(f' — {finish}' if finish else ''),title_basis='event_heading'))
            for child in node.values():
                if isinstance(child,(dict,list)):walk(child)
    walk(data)
    return list({(e['primary_url'],e['start_date'],e.get('start_time'),e['event_type'],normalized_title(e['title'])):e for e in found}.values())


def decode_nuxt(script):
    """Decode Nuxt's literal argument table; do not evaluate JavaScript."""
    match=re.search(r'window\.__NUXT__\s*=\s*\(function\(([^)]*)\)\s*\{return\s*(\{[\s\S]*\})\}\(([\s\S]*)\)\);?\s*$',script)
    if not match:return None
    try:
        names=[n.strip() for n in match[1].split(',')]
        values=json.loads('['+match[3]+']')
        if len(names)!=len(values):return None
        mapping=dict(zip(names,values))
        chunks=re.split(r'("(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27)',match[2])
        for index in range(0,len(chunks),2):
            chunks[index]=re.sub(r'(?<=[\[:,])\s*([A-Za-z_$][\w$]*)\s*(?=[,}\]])',lambda m:json.dumps(mapping[m[1]],ensure_ascii=False) if m[1] in mapping else m[0],chunks[index])
        data=chompjs.parse_js_object(''.join(chunks))
        def normalize(node):
            if isinstance(node,dict):return {k:normalize(v) for k,v in node.items()}
            if isinstance(node,list):return [normalize(v) for v in node]
            if node=='null' or node=='undefined':return None
            if node=='true':return True
            if node=='false':return False
            return node
        return normalize(data)
    except (ValueError,TypeError,KeyError):return None


def parse_embedded(html,url):
    soup=BeautifulSoup(html,'html.parser');events=[]
    for script in soup.select('script#__NEXT_DATA__,script#source-state-json,script[type="application/json"]'):
        try:events+=parse_state(json.loads(script.string or script.get_text()),url)
        except (ValueError,TypeError):continue
    for script in soup.select('script:not([src])'):
        source=script.string or script.get_text()
        if 'window.__NUXT__' in source:
            decoded=decode_nuxt(source)
            if decoded:events+=parse_state(decoded,url)
    return _first_days(events)
