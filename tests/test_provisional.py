import json
from copy import deepcopy
from pathlib import Path
from ingestion.import_catalog import ROOT, import_data
from ingestion.models import deduplicate
from ingestion.provisional import tentative_post, publish_snapshot
from ingestion.run import refresh


def candidate(text):
    return {'description':text, 'published_at':'2026-10-13T09:00:00+00:00', 'primary_url':'https://t.me/testgallery/1'}


def catalog():
    return {'metadata':{'updated_on':'2026-10-19'}, 'institutions':[{'institution_id':'A','name':'Галерея','monitor_state':'monitor','locations':[{'address':'Москва, Основная улица, 1','geography_scope':'moscow'}]}],
        'sources':[{'source_id':'S','platform':'telegram','url':'https://t.me/testgallery','institution_ids':['A'],'roles':['announcements']}], 'institution_sources':[]}


def overrides():
    return {'publication_policy':'include_tentative','manual_events':[], 'corrections':{},'suppress':[], 'duplicates':{},'priorities':{},'disabled_sources':[],'parser_rules':{}}


def test_removed_institution_does_not_return_after_workbook_import(tmp_path):
    (tmp_path/'catalog').mkdir()
    config=tmp_path/'additional.json'
    config.write_text(json.dumps({'updated_on':'2026-10-19','excluded_institution_ids':['WATCH02']}))
    c=import_data(ROOT/'catalog/original.json',ROOT/'catalog/original.xlsx',tmp_path,config)
    assert len(c['institutions'])==92
    assert not any(i['institution_id']=='WATCH02' for i in c['institutions'])
    assert not any(r['institution_id']=='WATCH02' for r in c['institution_sources'])
    assert not any('WATCH02' in s['institution_ids'] for s in c['sources'])
    assert 'SRC_D07A59447D5C4E' not in {s['source_id'] for s in c['sources']}
    assert 'SRC_0D538B01F0C28F' in {s['source_id'] for s in c['sources']}  # shared source survives
    assert len(json.loads((tmp_path/'catalog/normalized.json').read_text())['institutions'])==93


def test_closing_notice_records_publication_bound_without_claiming_opening():
    events=tentative_post(candidate('Выставка «След»\nПредставлена до 15 ноября\nМосква, улица Мира, 7'))
    assert len(events)==1
    e=events[0]
    assert e['start_date']=='2026-10-13' and e['end_date']=='2026-11-15'
    assert e['date_basis']=='publication_bound'
    assert any('Дата открытия не указана' in note for note in e['uncertainties'])


def test_street_numbers_and_quoted_artwork_ratios_do_not_become_dates():
    events=tentative_post(candidate('Лекция «3/4»\n20 октября в 19:00\n4-й Сыромятнический пер., 1/8 с.9'))
    assert len(events)==1 and events[0]['start_date']=='2026-10-20'
    assert events[0]['title']=='3/4'


def test_multi_date_programme_has_one_honest_range_without_neighbouring_clocks():
    events=tentative_post(candidate('Программа лекций\n20 октября в 19:00\nДискуссия\n22 октября в 18:00'))
    assert len(events)==1
    e=events[0]
    assert (e['start_date'],e['end_date'],e['start_time'])==('2026-10-20','2026-10-22',None)
    assert e['event_type']=='other' and e['title'].startswith('Программа:')


def test_undated_news_birthdays_and_explicit_foreign_events_are_not_invented():
    for text in ['На выставке появились новые работы', '12 сентября — день рождения художника. Выставка работ', 'В венской Альбертине 30 октября откроется выставка «HER STORY»']:
        assert tentative_post(candidate(text))==[]


def snapshot():
    row={'source_id':'S','candidate':{'title':'Событие','start_date':'2026-10-22','event_type':'talk','primary_url':'https://t.me/testgallery/1'},'reason':'Место требует уточнения','link_status':'broken'}
    return {'metadata':{'last_successful_update':'2026-10-17T12:00:00+00:00'}, 'events':[], 'sources':[{'source_id':'S','status':'partial','last_successful_check':'2026-10-17T12:00:00+00:00'}], 'review':[row]}


def test_snapshot_publishes_with_uncertainty_and_preserves_actual_check_timestamp():
    previous=snapshot();feed,review=publish_snapshot(catalog(),overrides(),previous,'2026-10-19T10:00:00+00:00')
    assert not review and len(feed['events'])==1
    e=feed['events'][0]
    assert e['review_status']=='tentative' and e['venue_is_tentative']
    assert not e.get('address')
    assert e['link_status']=='broken' and e['link_checked_at']=='2026-10-17T12:00:00+00:00'
    assert feed['metadata']['last_successful_update']==previous['metadata']['last_successful_update']
    again,_=publish_snapshot(catalog(),overrides(),{**feed,'review':review},'2026-10-19T11:00:00+00:00')
    assert len(again['events'])==1 and again['events'][0]['event_id']==e['event_id']


def test_confirmed_record_wins_over_tentative_reparse_and_clears_old_warnings():
    confirmed={'event_id':'V','institution_id':'A','title':'Событие','start_date':'2026-10-22','event_type':'talk','review_status':'verified','evidence':[]}
    tentative={**confirmed,'event_id':'T','review_status':'tentative','uncertainties':['Неясная дата'],'venue_is_tentative':True}
    for items in [[deepcopy(confirmed),deepcopy(tentative)],[deepcopy(tentative),deepcopy(confirmed)]]:
        result=deduplicate(items)
        assert len(result)==1 and result[0]['review_status']=='verified'
        assert 'uncertainties' not in result[0] and 'venue_is_tentative' not in result[0]


def test_scheduled_refresh_honours_policy_and_removes_deleted_owner_records():
    class NoNetwork:
        def fetch(self,url): raise AssertionError('Not selected for a network refresh')
    previous=snapshot()
    previous['events']=[{'institution_id':'REMOVED','event_id':'REMOVED','evidence':[]}]
    feed,review=refresh(catalog(),overrides(),previous,NoNetwork(),only=['OTHER'])
    assert len(feed['events'])==1 and feed['events'][0]['review_status']=='tentative'
    assert not review and feed['metadata']['tentative_count']==1
    strict={**overrides(),'publication_policy':'verified_only'}
    feed,review=refresh(catalog(),strict,previous,NoNetwork(),only=['OTHER'])
    assert not feed['events'] and len(review)==1


def test_numeric_date_with_trailing_dot_and_dotted_clock_remain_calendar_dates():
    for text, day in [('Воркшоп «Моя планета»\nВремя:\n24.10.,13:00 – 15:30.','2026-10-24'),
                      ('Выставка «СТЕПЕНЬ КАСАНИЯ»\n16 октября пятница 16.00-20.30 (кураторская экскурсия)','2026-10-16')]:
        events=tentative_post(candidate(text))
        assert len(events)==1 and events[0]['start_date']==day


def test_a_dated_public_talk_is_separated_from_giveaway_rules():
    text='Разыгрываем билеты на открытие выставки\nПобедители — во вторник!\n21 октября открывают серию встреч с музыкантами\n21 октября, 19:00–21:00\nСамокатная 4'
    events=tentative_post(candidate(text))
    assert len(events)==1 and events[0]['start_date']=='2026-10-21'
    assert events[0]['event_type']=='talk'
