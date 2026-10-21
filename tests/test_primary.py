from copy import deepcopy
from pathlib import Path
from ingestion.adapters.mmoma import parse_mmoma
from ingestion.models import deduplicate
from ingestion.primary import official_links, require_primary_sources, source_authority
from ingestion.provisional import publish_review
from ingestion.run import refresh
from ingestion.http import SourceError

URL='https://mmoma.ru/visit/gallery/cartography_of_myth/description'
FIX=Path(__file__).parent/'fixtures'


def catalog():
    return dict(metadata={'updated_on':'2026-10-20'},institutions=[dict(institution_id='MMOMA',name='ММОМА',monitor_state='monitor',evidence_url='https://mmoma.ru/visit/events')],
        sources=[dict(source_id='SITE',platform='website',url='https://mmoma.ru/visit/events',institution_ids=['MMOMA']),
            dict(source_id='AGG',platform='website',url='https://ewert.ru/exhibition/',institution_ids=['MMOMA'])],
        institution_sources=[dict(source_id=s,institution_id='MMOMA',role='announcements') for s in ('SITE','AGG')])


def overrides():
    return dict(manual_events=[],corrections={},suppress=[],duplicates={},priorities={},disabled_sources=[],parser_rules={},publication_policy='include_tentative')


def event():
    return dict(event_id='SIDUR',institution_id='MMOMA',title='Вадим Сидур. Карта мифа',event_type='exhibition',start_date='2026-04-16',
        end_date='2027-03-27',primary_url='https://ewert.ru/exhibition/sidur',source_id='AGG',review_status='verified',evidence=[{'url':'https://ewert.ru/exhibition/sidur'}])


def test_mmoma_real_header_keeps_full_period_and_does_not_treat_hours_as_opening():
    parsed=parse_mmoma((FIX/'mmoma-sidur-real.html').read_text(),URL)
    assert len(parsed)==1
    assert parsed[0]['start_date']=='2026-04-16' and parsed[0]['end_date']=='2027-03-28'
    assert parsed[0]['start_time'] is None and parsed[0]['event_type']=='exhibition'
    assert parsed[0]['venue_name']=='Музей Вадима Сидура · ММОМА'
    assert parse_mmoma((FIX/'mmoma-sidur-real.html').read_text(),'https://mmoma.ru/visit/gallery')==[]


def test_official_source_wins_over_aggregator_even_when_it_is_parsed_first():
    aggregate=event();official=dict(aggregate,event_id='OFFICIAL',primary_url=URL,end_date='2027-03-28',source_authority='official',evidence=[{'url':URL}])
    for records in [[aggregate,official],[official,aggregate]]:
        merged=deduplicate(deepcopy(records))
        assert len(merged)==1 and merged[0]['primary_url']==URL
        assert merged[0]['end_date']=='2027-03-28' and len(merged[0]['evidence'])==2


def test_aggregator_only_records_go_to_review_and_cannot_be_republished_as_tentative():
    row=event();kept,review=require_primary_sources([row],[])
    assert not kept and len(review)==1
    published,remaining=publish_review(catalog(),review,[],'2026-10-20T10:00:00Z')
    assert not published and remaining==review
    again,review_again=require_primary_sources([row],review)
    assert not again and len(review_again)==1


def test_discovery_links_are_restricted_to_catalogued_non_aggregator_sites():
    html=f'<a href="{URL}?utm_source=agg">Источник</a><a href="https://unknown.example/event">Другое</a><a href="https://ewert.ru/exhibition/another">Ещё</a>'
    assert official_links(html,'https://ewert.ru/',catalog())==[URL]
    assert source_authority(catalog(),catalog()['sources'][0],catalog()['institutions'][0])=='official'
    assert source_authority(catalog(),catalog()['sources'][1],catalog()['institutions'][0])=='aggregator'


def test_editorial_correction_keeps_original_id_fixes_owner_and_preserves_helper_evidence():
    old=event();old['institution_id']='WRONG'
    c=catalog();c['institutions'].append(dict(institution_id='WRONG',name='Другая площадка',monitor_state='monitor'))
    o=overrides();o['manual_events']=[dict(event_id='SIDUR',institution_id='MMOMA',title='Вадим Сидур. Карта мифа',event_type='exhibition',
        primary_url=URL,start_date='2026-04-16',end_date='2027-03-28',venue_name='Музей Вадима Сидура · ММОМА',
        editor_verified_at='2026-10-20T09:00:00Z',verification_method='editorial_public_page',source_authority='official')]
    class Blocked:
        def fetch(self,url):raise SourceError('Сбор запрещён robots.txt','blocked')
    feed,review=refresh(c,o,{'events':[old],'sources':[]},Blocked(),only=['SITE'])
    assert len(feed['events'])==1
    actual=feed['events'][0]
    assert actual['event_id']=='SIDUR' and actual['institution_id']=='MMOMA'
    assert actual['primary_url']==URL and actual['end_date']=='2027-03-28'
    assert actual['venue_name']=='Музей Вадима Сидура · ММОМА'
    assert len(actual['evidence'])==2 and actual['link_status']=='available'
    assert actual['automatic_link_status']=='blocked'
    assert actual['evidence'][0]['verification_method']=='editorial_public_page'
    again,_=refresh(c,o,feed,Blocked(),only=['SITE'])
    assert len(again['events'])==1 and len(again['events'][0]['evidence'])==2
