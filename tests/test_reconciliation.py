from copy import deepcopy
from pathlib import Path
from ingestion.adapters.telegram import parse_preview
from ingestion.adapters.social import parse_post, SocialPost
from ingestion.adapters.hse import parse_hse
from ingestion.models import deduplicate, preserve_event_ids, complete_event, link_parents
from ingestion.provisional import tentative_post
from ingestion.run import refresh
from ingestion.audit import duplicate_pairs

FIX=Path(__file__).parent/'fixtures'
URL='https://art.hse.ru/gallery/what_have_you_done_for_hip-hop_at_your_age'
TITLE='Что ты сделал для хип-хопа в свои годы'


def event(**kw):
    return dict(dict(event_id='A',institution_id='HSE',title=TITLE,event_type='exhibition',
        start_date='2026-10-20',end_date=None,start_time=None,primary_url=URL,
        evidence=[],review_status='verified'),**kw)


def test_real_hse_heading_period_opening_and_address():
    events=parse_hse((FIX/'hse-exhibition-real.html').read_text(),URL)
    exhibition,opening=events
    assert exhibition['title']==TITLE
    assert (exhibition['start_date'],exhibition['end_date'])==('2026-10-20','2026-12-01')
    assert (opening['start_date'],opening['start_time'])==('2026-10-20','19:00')
    assert 'Сыромятнический' in exhibition['address']
    assert parse_hse((FIX/'hse-exhibition-real.html').read_text(),'https://art.hse.ru/gallery')==[]


def test_real_unquoted_telegram_title_and_preserved_hyperlinks():
    posts=parse_preview((FIX/'hse-telegram-real.html').read_text(),'hseartgallery')
    post=next(p for p in posts if p.url.endswith('/4748'))
    assert any(u.startswith(URL+'?utm_source=tg&') for u in post.related_urls)
    parsed,reason=parse_post(post)
    assert not parsed and 'период' in reason
    result=tentative_post(dict(description=post.text,published_at=post.published_at,primary_url=post.url,related_urls=list(post.related_urls)))
    assert result[0]['title']==TITLE+'?'
    assert result[0]['related_urls']==list(post.related_urls)


def test_social_unquoted_heading_with_explicit_exhibition_range():
    post=SocialPost('Что ты сделал для хип-хопа в свои годы?\n⚡️\nВыставка\n20 октября — 1 декабря 2026',
        'https://t.me/example/1','2026-10-15T12:00:00Z','telegram','test','example')
    events,reason=parse_post(post)
    assert reason is None and events[0]['title']==TITLE+'?'
    assert events[0]['event_type']=='exhibition'


def test_nested_quotes_and_title_after_date_do_not_truncate_a_lecture_title():
    title='Не только «Третий Рим»: идеи, которые связывали с именем старца Филофея'
    posts=[SocialPost('18 октября в Галерее пройдёт лекция Ильи Вевюрко\n«'+name+'».\nУчастие бесплатное',
        f'https://t.me/solyankagallery/{n}','2026-10-15T12:00:00Z','telegram','test','solyankagallery')
        for n,name in enumerate([title,title.replace('«Третий Рим»','"Третий Рим"')])]
    events=[parse_post(p)[0][0] for p in posts]
    assert events[0]['title']=='«'+title+'»'
    assert events[1]['title']=='«'+title.replace('«Третий Рим»','"Третий Рим"')+'»'
    completed=[complete_event(e,{'institution_id':'SOL','name':'Солянка'},
        {'source_id':'TG','platform':'telegram'},'2026-10-19T12:00:00Z') for e in events]
    assert len(deduplicate(completed))==1
    assert len(duplicate_pairs(completed))==1


def test_website_and_two_linked_posts_become_one_exhibition_with_all_evidence():
    website=event(end_date='2026-12-01',source_platform='website',title_basis='event_heading',evidence=[{'url':URL}])
    a=event(event_id='B',title='открывается выставка',review_status='tentative',title_is_tentative=True,
        primary_url='https://t.me/hseartgallery/4748',related_urls=[URL+'?utm_source=tg'],evidence=[{'url':'https://t.me/hseartgallery/4748'}])
    b=event(event_id='C',title='Они никогда не были в одном месте',review_status='tentative',title_is_tentative=True,
        primary_url='https://t.me/hseartgallery/4757',related_urls=[URL],evidence=[{'url':'https://t.me/hseartgallery/4757'}])
    for items in [[website,a,b],[a,b,website]]:
        result=deduplicate(deepcopy(items))
        assert len(result)==1
        merged=result[0]
        assert merged['title']==TITLE and merged['end_date']=='2026-12-01'
        assert merged['review_status']=='verified'
        assert len(merged['evidence'])==3
        assert set(merged.get('merged_event_ids',[])+[merged['event_id']])=={'A','B','C'}
        assert deduplicate(deepcopy(result))==result


def test_unknown_opening_time_merges_with_explicit_but_different_sessions_do_not():
    a=event(event_type='opening',review_status='tentative',start_time=None)
    b=event(event_type='opening',event_id='B',start_time='19:00')
    result=deduplicate([a,b])
    assert len(result)==1 and result[0]['start_time']=='19:00'
    assert len(deduplicate([event(event_type='tour',start_time='13:00'),event(event_type='tour',event_id='B',start_time='17:00')]))==2
    assert len(deduplicate([event(event_id='X',event_type='opening',start_time='19:00'),event(event_id='Y',event_type='opening',start_time='20:00'),event(event_id='Z',event_type='opening')]))==3
    from itertools import permutations
    sessions=[event(event_id='X',event_type='opening',start_time='19:00'),event(event_id='Y',event_type='opening',start_time='20:00'),event(event_id='Z',event_type='opening')]
    for order in permutations(sessions):
        assert len(deduplicate(deepcopy(order)))==3
        assert not duplicate_pairs(order)


def test_same_day_or_shared_programme_link_is_not_sufficient_to_merge_named_events():
    a=event(title='Керамика',related_urls=['https://example.org/programme'])
    b=event(event_id='B',title='Музыка',related_urls=['https://example.org/programme'])
    assert len(deduplicate([a,b]))==2
    assert len(deduplicate([a,event(event_id='B',title='Музыка')]))==2
    assert len(deduplicate([a,event(event_id='B',institution_id='OTHER',title='Керамика')]))==2
    assert len(deduplicate([a,event(event_id='B',title='Керамика',event_type='opening')]))==2
    assert len(deduplicate([event(title='Открытие нового мира'),event(event_id='B',title='Нового мира',primary_url='https://example.org/events/other')]))==2


def test_closing_reminders_do_not_create_a_new_exhibition_each_publication_day():
    a=event(event_id='A',date_basis='publication_bound',start_date='2026-10-12',end_date='2026-10-25',review_status='tentative')
    b=event(event_id='B',date_basis='publication_bound',start_date='2026-10-18',end_date='2026-10-25',review_status='tentative')
    result=deduplicate([a,b])
    assert len(result)==1 and result[0]['start_date']=='2026-10-12'
    confirmed=event(event_id='C',date_basis='explicit_date_block',start_date='2026-09-01',end_date='2026-10-25')
    result=deduplicate([b,confirmed])
    assert len(result)==1 and result[0]['start_date']=='2026-09-01'
    assert len(deduplicate([confirmed,event(event_id='D',start_date='2026-10-18',end_date='2026-10-25',date_basis='explicit_date_block')]))==2


def test_old_shared_ids_survive_a_corrected_title_and_multiple_sources():
    old=event(event_id='OLD',title='открывается выставка',primary_url='https://t.me/hseartgallery/4748',first_detected_at='2026-10-17T00:00:00Z')
    fresh=event(event_id='NEW',evidence=[{'url':old['primary_url']},{'url':URL}],first_detected_at='2026-10-19T00:00:00Z')
    result=preserve_event_ids([fresh],[old])[0]
    assert result['event_id']=='OLD' and 'NEW' in result['merged_event_ids']
    assert result['first_detected_at']=='2026-10-17T00:00:00Z'


def test_reparsing_does_not_lose_evidence_from_an_earlier_merge():
    old=event(evidence=[{'url':'https://t.me/channel/1'},{'url':URL}],merged_event_ids=['OLD_ALIAS'])
    fresh=event(event_id='NEW',evidence=[{'url':URL,'title':TITLE}])
    result=preserve_event_ids([fresh],[old])[0]
    assert len(result['evidence'])==2 and 'OLD_ALIAS' in result['merged_event_ids']


def test_tentative_title_does_not_become_an_empty_standalone_quote():
    text='Москва. 20 октября в 19:30\nЛекция:\n«\nЖенское дело. Истории художниц от Ренессанса до Эпохи Модерна»\n20 октября в 19:30'
    result=tentative_post(dict(description=text,published_at='2026-10-14T09:54:48Z',primary_url='https://t.me/murmurespace/3308'))
    assert result[0]['title']=='Женское дело. Истории художниц от Ренессанса до Эпохи Модерна'


def test_complete_evidence_keeps_source_title_and_date_for_comparison():
    result=complete_event(event(title_basis='event_heading',date_evidence='20 октября — 1 декабря 2026'),
        {'institution_id':'HSE','name':'HSE'},{'source_id':'SITE','platform':'website'},'2026-10-19T12:00:00Z')
    proof=result['evidence'][0]
    assert proof['title']==TITLE and proof['start_date']=='2026-10-20'
    assert proof['date_evidence']=='20 октября — 1 декабря 2026'


def test_actual_site_and_channel_refresh_merge_and_remain_repeatable():
    c={'metadata':{'updated_on':'2026-10-19'},'institutions':[{'institution_id':'HSE','name':'HSE','monitor_state':'monitor'}],
        'sources':[{'source_id':'SITE','platform':'website','url':'https://art.hse.ru/gallery','institution_ids':['HSE']},
            {'source_id':'TG','platform':'telegram','url':'https://t.me/hseartgallery','institution_ids':['HSE']}],
        'institution_sources':[{'source_id':s,'institution_id':'HSE','role':'announcements'} for s in ('SITE','TG')]}
    class Client:
        def fetch(self,url):
            if url=='https://art.hse.ru/gallery':return f'<a href="{URL}">Выставка</a>',url
            if url=='https://t.me/s/hseartgallery':return (FIX/'hse-telegram-real.html').read_text(),url
            if url==URL:return (FIX/'hse-exhibition-real.html').read_text(),url
            raise AssertionError(url)
    overrides=dict(manual_events=[],corrections={},suppress=[],duplicates={},priorities={},disabled_sources=[],parser_rules={},publication_policy='include_tentative')
    old=event(event_id='OLD',title='открывается выставка',primary_url='https://t.me/hseartgallery/4748',
        review_status='tentative',title_is_tentative=True,source_id='TG',first_detected_at='2026-10-17T00:00:00Z')
    first,review=refresh(c,overrides,{'events':[old]},Client(),max_pages=1)
    exhibitions=[e for e in first['events'] if e['event_type']=='exhibition']
    assert len(exhibitions)==1
    assert exhibitions[0]['event_id']=='OLD'
    assert exhibitions[0]['title']==TITLE and len(exhibitions[0]['evidence'])==3
    opening=next(e for e in first['events'] if e['event_type']=='opening')
    assert opening['parent_event_id']=='OLD' and opening['start_time']=='19:00'
    second,_=refresh(c,overrides,{**first,'review':review},Client(),max_pages=1)
    assert {e['event_id'] for e in first['events']}=={e['event_id'] for e in second['events']}
    assert len([e for e in second['events'] if e['event_type']=='exhibition'])==1
