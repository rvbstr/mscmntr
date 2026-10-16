import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest
from ingestion.dates import extract_dates
from ingestion.models import canonical_url,direct_url,deduplicate,event_type
from ingestion.import_catalog import ROOT,platform,import_data
from ingestion.run import due,refresh,valid_event
from ingestion.http import SourceError
from ingestion.adapters import parse_jsonld,parse_html,parse_feed
from ingestion.editorial import load_overrides,apply_overrides

FIX=Path(__file__).parent/'fixtures'

@pytest.mark.parametrize('text,start,end',[('17–21 октября 2026','2026-10-17','2026-10-21'),('с 10 октября по 3 декабря 2026','2026-10-10','2026-12-03'),('24 октября 2026','2026-10-24',None),('до 15 ноября 2026',None,'2026-11-15'),('17.10.2026','2026-10-17',None),('17.10–21.11.2026','2026-10-17','2026-11-21'),('17.10.2026 — 21.11.2026','2026-10-17','2026-11-21'),('2026-10-17','2026-10-17',None),('31 февраля 2026',None,None),('с 20 декабря 2026 по 8 января','2026-12-20','2027-01-08')])
def test_russian_dates(text,start,end):
 d=extract_dates(text); assert d['start_date']==start; assert d['end_date']==end

def test_no_year_no_guessed_event(): assert extract_dates('Открытие 24 октября')['start_date'] is None

def test_opening():
 d=extract_dates('17–21 октября 2026. Вернисаж — 17 октября, 18:00'); assert d['opening_date']=='2026-10-17';assert d['opening_time']=='18:00'

@pytest.mark.parametrize('url,expected',[('https://example.org/',False),('https://example.org/exhibitions',False),('https://example.org/exhibitions/material',True),('https://t.me/channel',False),('https://t.me/channel/143',True),('https://instagram.com/profile/',False),('https://instagram.com/p/abc',True),('javascript:alert(1)',False)])
def test_direct(url,expected): assert direct_url(url)==expected

def test_url_canonicalization(): assert canonical_url('https://EXAMPLE.org/events/a/?utm_source=abc&id=1#x')=='https://example.org/events/a?id=1'

@pytest.mark.parametrize('url,expected',[('https://t.me/a','telegram'),('https://tg.me/a','telegram'),('https://vk.com/wall1','vk'),('https://www.instagram.com/a','instagram'),('https://example.org/feed','rss')])
def test_mapping(url,expected): assert platform(url)==expected

def test_structured_fixture():
 events=parse_jsonld((FIX/'event.html').read_text(),'https://example.org/events')
 assert len(events)==1; e=events[0];assert e['start_time']=='18:00';assert e['description']=='Тест & данные';assert e['event_type']=='exhibition'; assert valid_event(e)

def test_html_fixture_opening_and_exhibition():
 events=parse_html((FIX/'event.html').read_text(),'https://example.org/exhibitions/material',{'event_type':'exhibition'})
 assert len(events)==2;assert events[0]['end_date']=='2026-11-21';assert events[1]['event_type']=='opening';assert events[1]['start_time']=='18:00'

def test_no_index_date_contamination():
 assert parse_html('<h1>Афиша</h1><footer>17 октября 2026</footer>','https://example.org/events')==[]

def test_feed_requires_event_not_publication_date():
 events=parse_feed((FIX/'feed.xml').read_text(),'https://example.org/feed')
 assert len(events)==1;assert events[0]['start_date']=='2026-10-18';assert events[0]['start_time']=='19:30'

def test_dedup_preserves_evidence_and_unrelated_events():
 a=dict(event_id='a',institution_id='A',title='МАТЕРИЯ',event_type='exhibition',start_date='2026-10-17',evidence=[{'url':'https://a.org/one'}],first_detected_at='2026-10-01T00:00:00Z')
 b=dict(a,event_id='b',title='Материя',evidence=[{'url':'https://a.org/two'}],first_detected_at='2026-10-02T00:00:00Z')
 c=dict(a,event_id='c',start_date='2026-11-17');d=dict(a,event_id='d',institution_id='B')
 result=deduplicate([a,b,c,d]);assert len(result)==3;assert result[0]['event_id']=='a';assert len(result[0]['evidence'])==2;assert result[0]['first_detected_at']==a['first_detected_at']

def test_72h_across_month():
 last=datetime(2026,10,30,10,tzinfo=timezone.utc); meta={'last_completed_refresh':last.isoformat()}
 assert not due(meta,last+timedelta(hours=71,minutes=59));assert due(meta,last+timedelta(hours=72))

def test_import_all_relationships(tmp_path):
 (tmp_path/'catalog').mkdir();c=import_data(ROOT/'catalog/original.json',ROOT/'catalog/original.xlsx',tmp_path)
 assert len(c['institutions'])==93;assert len(c['sources'])==143;assert len(c['institution_sources'])==164
 normalized=json.loads((tmp_path/'catalog/normalized.json').read_text());assert len(normalized['aliases'])==19;assert len(normalized['event_evidence'])==2
 assert next(i for i in c['institutions'] if i['institution_id']=='MSK068')['independent']
 assert 'seed_events' not in json.loads((tmp_path/'public/data/catalog.json').read_text())

class FixtureClient:
 def fetch(self,url):
  if 'broken' in url: raise SourceError('Заблокировано тестовым транспортом','blocked')
  return (FIX/'event.html').read_text(),url


def mini_catalog():
 return {'metadata':{'updated_on':'2026-10-16'},'institutions':[{'institution_id':'A','name':'Тестовая институция','monitor_state':'monitor','monitoring_priority':'normal','tags':[]}],
 'sources':[{'source_id':'S1','url':'https://example.org/one','platform':'website','institution_ids':['A']},{'source_id':'S2','url':'https://example.org/broken','platform':'website','institution_ids':['A']}],
 'institution_sources':[{'source_id':'S1','institution_id':'A','role':'announcements'},{'source_id':'S2','institution_id':'A','role':'announcements'}]}

def empty_overrides():return {'manual_events':[],'corrections':{},'suppress':[],'duplicates':{},'priorities':{},'disabled_sources':[],'parser_rules':{}}

def test_partial_failure_integration_and_repeatability():
 c=mini_catalog();feed,review=refresh(c,empty_overrides(),{'events':[],'sources':[]},FixtureClient(),max_pages=0)
 assert len(feed['events'])==1;assert {s['status'] for s in feed['sources']}=={'working','blocked'};assert feed['metadata']['partial']
 second,_=refresh(c,empty_overrides(),feed,FixtureClient(),max_pages=0);assert len(second['events'])==1
 assert second['events'][0]['event_id']==feed['events'][0]['event_id'];assert second['events'][0]['first_detected_at']==feed['events'][0]['first_detected_at'];assert all(s['new_events']==0 for s in second['sources'])

def test_all_failed_keeps_previous_data():
 class Broken:
  def fetch(self,url):raise SourceError('Нет доступа','blocked')
 c=mini_catalog();valid,_=refresh(c,empty_overrides(),{'events':[],'sources':[]},FixtureClient(),max_pages=0)
 failed,_=refresh(c,empty_overrides(),valid,Broken(),max_pages=0)
 assert failed['events']==valid['events'];assert failed['metadata']['last_successful_update']==valid['metadata']['last_successful_update'];assert failed['metadata']['successful_sources_this_run']==0

def test_overrides_suppression_and_conflict():
 o=empty_overrides();o['suppress']=['a'];assert not apply_overrides([{'event_id':'a'}],o)
 o['corrections']={'missing':{'title':'Не существует'}}
 with pytest.raises(ValueError):apply_overrides([],o)

def test_live_override_schema():
 catalog=json.loads((ROOT/'catalog/catalog.json').read_text());load_overrides(ROOT/'editorial/overrides.json',catalog)


def test_distinct_sessions_not_merged():
 a=dict(event_id='a',institution_id='A',title='Тур',event_type='tour',start_date='2026-10-17',start_time='13:00')
 b=dict(a,event_id='b',start_time='17:00')
 assert len(deduplicate([a,b]))==2


def test_real_source_snapshots():
 from ingestion.adapters.institutions import parse_ges2,parse_prpr,parse_cube
 ges=parse_ges2((FIX/'ges2-real.html').read_text(),'https://ges-2.org/calendar')
 assert any(e['title']=='ТинаНаД' and e['start_time']=='19:00' for e in ges)
 assert any(e['title']=='Принцип серийности' and e['event_type']=='exhibition' and e['end_date']=='2026-11-04' for e in ges)
 # A recurring tour must have distinct explicit sessions, not an invented multi-month interval.
 tours=[e for e in ges if e['title']=='Натюрморт. Портрет. Пейзаж. После жанра' and e['event_type']=='tour']
 assert {e['start_time'] for e in tours}=={'13:00','17:00'}
 prpr=parse_prpr((FIX/'prpr-real.html').read_text(),'https://prpr312.ru/zhivopis-for-anya')
 assert len(prpr)==2;assert prpr[0]['end_date']=='2026-10-21';assert prpr[1]['start_time']=='18:00'
 cube=parse_cube((FIX/'cube-real.html').read_text(),'https://cube.moscow/personalnaya-vystavka-marii-dzhonas-farel-yudol-put-k-istochniku/')
 assert len(cube)==1;assert cube[0]['start_date']=='2026-10-07';assert cube[0]['end_date']=='2026-11-01'


def test_catalog_url_discovery_reextracts_without_duplicate_opening():
 from ingestion.run import seed_candidates,complete_event
 c=json.loads((ROOT/'catalog/catalog.json').read_text());i=next(i for i in c['institutions'] if i['institution_id']=='WATCH05');s=next(s for s in c['sources'] if s['url']=='https://prpr312.ru/')
 class RealSnapshot:
  def fetch(self,url):return (FIX/'prpr-real.html').read_text(),url
 candidates=seed_candidates(c,RealSnapshot(),s,i)
 assert len(candidates)==2;assert all(e['title']=='«Живопись для Ани»' for e in candidates)
 first=[complete_event(e,i,s,'2026-10-16T10:00:00Z') for e in candidates]
 second=[complete_event(e,i,s,'2026-10-16T11:00:00Z') for e in candidates]
 assert len(deduplicate(first+second))==2

def test_review_queue_survives_failed_recheck():
 class Broken:
  def fetch(self,url):raise SourceError('Нет доступа','blocked')
 item={'source_id':'S1','reason':'Нужна проверка','candidate':{'title':'Неизвлечённый анонс'}}
 feed,review=refresh(mini_catalog(),empty_overrides(),{'events':[],'sources':[],'review':[item]},Broken(),max_pages=0)
 assert review==[item];assert feed['metadata']['review_count']==1


def test_opening_prefix_dedup_is_cautious():
 a=dict(event_id='a',institution_id='A',title='«Живопись для Ани»',event_type='opening',start_date='2026-10-17',start_time='18:00')
 b=dict(a,event_id='b',title='Вернисаж: Живопись для Ани')
 assert len(deduplicate([a,b]))==1
 assert len(deduplicate([a,dict(b,event_type='exhibition')]))==2


def test_duplicate_overrides_are_repeatable():
 o=empty_overrides();o['duplicates']={'b':'a'}
 first=apply_overrides([{'event_id':'a','evidence':[{'url':'https://a.org/1'}]},{'event_id':'b','evidence':[{'url':'https://a.org/2'}]}],o)
 second=apply_overrides(first,o);assert first==second;assert len(second[0]['evidence'])==2


def test_parent_ids_remain_valid_after_deduplication():
 from ingestion.models import link_parents
 exhibition=dict(event_id='canonical',institution_id='A',title='Живопись',event_type='exhibition',start_date='2026-10-17',end_date='2026-10-21')
 opening=dict(event_id='opening',institution_id='A',title='Вернисаж: Живопись',event_type='opening',start_date='2026-10-17',parent_event_id='removed-seed')
 result=link_parents([exhibition,opening]);assert result[1]['parent_event_id']=='canonical'
 other=dict(opening,event_id='different',institution_id='B',parent_event_id='removed-seed')
 assert not link_parents([exhibition,other])[1].get('parent_event_id')


def test_new_count_ignores_title_typography_changes():
 from ingestion.models import event_signature
 a=dict(institution_id='A',title='«Живопись для Ани»',event_type='opening',start_date='2026-10-17',start_time='18:00')
 assert event_signature(a)==event_signature(dict(a,title='Вернисаж: ЖИВОПИСЬ ДЛЯ АНИ'))


def test_canonical_event_relationship_attributes_dedicated_evidence_page():
 c=json.loads((ROOT/'catalog/catalog.json').read_text())
 class RealSnapshot:
  def fetch(self,url):return (FIX/'prpr-real.html').read_text(),url
 f,r=refresh(c,empty_overrides(),{'events':[],'sources':[]},RealSnapshot(),only=['SRC_A18D2528A881B6'],max_pages=0)
 assert len(f['events'])==2;assert all(e['institution_id']=='WATCH05' for e in f['events']);assert not r
 assert all(e['confidence']=='institution_html' for e in f['events'])
