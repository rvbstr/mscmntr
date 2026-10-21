import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from ingestion.http import Client,SourceError
from ingestion.adapters.state import decode_nuxt,parse_embedded,parse_state
from ingestion.extraction import extract,collect_website
from ingestion.adapters.html import discover_links
from ingestion.adapters.telegram import collect_preview
from ingestion.adapters.public_api import mmoma_calendar


def test_public_robots_policy_records_exclusion_without_discarding_public_page():
    client=Client(delay=0,robots_policy='public');client._safe=Mock()
    client._get=Mock(side_effect=[('User-agent: *\nDisallow: /','https://example.org/robots.txt'),('public event','https://example.org/events')])
    assert client.fetch('https://example.org/events')[0]=='public event'
    assert client.access_notes['https://example.org/events']=={'robots':'disallowed','policy':'public'}
    strict=Client(delay=0,robots_policy='respect');strict._safe=Mock();strict._get=Mock(return_value=('User-agent: *\nDisallow: /','https://example.org/robots.txt'))
    with pytest.raises(SourceError,match='robots.txt'):strict.fetch('https://example.org/events')
    assert strict._get.call_count==1


def test_unavailable_robots_does_not_hide_a_public_page_or_override_http_denial():
    client=Client(delay=0,robots_policy='public');client._safe=Mock()
    client._get=Mock(side_effect=[SourceError('robots timeout'),('event','https://example.org/event')])
    assert client.fetch('https://example.org/event')[0]=='event'
    assert client.access_notes['https://example.org/event']['robots']=='unavailable'
    client._get=Mock(side_effect=SourceError('HTTP 403','blocked'))
    with pytest.raises(SourceError,match='403'):client.fetch('https://example.org/other')


def test_nuxt_argument_table_is_decoded_without_executing_code():
    script='window.__NUXT__=(function(a,b,c){return {data:[{title:a,dateStart:b,dateEnd:c,isCurrent:true,path:"/exhibitions/67"}],error:null}}("Проект","2026-09-12T23:30:17.000Z","2026-10-31T20:30:00.000Z"));'
    state=decode_nuxt(script)
    event=parse_state(state,'https://example.org/')[0]
    assert event['title']=='Проект'
    assert (event['start_date'],event['end_date'],event['start_time'])==('2026-09-12','2026-10-31',None)
    assert decode_nuxt('window.__NUXT__=(function(a){return {title:a}}(fetch("https://example.org")));') is None


def test_embedded_calendar_requires_event_dates_not_publication_timestamps():
    data=[{'title':'Анонс','datePublished':'2026-10-20','path':'/events/a'}, {'title':'Лекция','startDate':'2026-10-21T16:00:00Z','path':'/events/b'}]
    e=parse_embedded('<script type="application/json">'+json.dumps(data)+'</script>','https://example.org/')
    assert len(e)==1 and e[0]['start_time']=='19:00'


def test_nonsemantic_detail_and_nested_date_spans_do_not_require_article():
    h='<html><head><title>Sans quitter la chambre</title></head><body><div class="title">Sans quitter la chambre</div><div><span>September 12, 2026</span> - <span>October 31, 2026</span></div></body></html>'
    events,adapter=extract(h,'https://example.org/exhibitions/67')
    assert adapter=='extruct_trafilatura' and events[0]['start_date']=='2026-09-12'
    assert events[0]['end_date']=='2026-10-31'


def test_wordpress_card_with_short_year_and_arbitrary_slug():
    h='<article class="elementor-post"><h3><a href="/zhivya-zhivi/">Живя, живи!</a></h3><p><b>Джон Р. Пеппер</b><br><i>21/10/26 – 29/11/26</i></p><p>Выставка фотографии</p></article>'
    events,adapter=extract(h,'https://example.org/')
    assert adapter=='programme_cards' and events[0]['start_date']=='2026-10-21'
    assert events[0]['end_date']=='2026-11-29'
    assert discover_links(h,'https://example.org/',1)==['https://example.org/zhivya-zhivi/']


def test_discovery_can_reach_calendar_index_and_then_detail():
    pages={'https://example.org/':'<a href="/exhibitions">Выставки</a>',
        'https://example.org/exhibitions':'<a href="/exhibitions/now">Проект</a>',
        'https://example.org/exhibitions/now':'<main><h1>Проект</h1><div class="date">20 октября — 28 ноября 2026</div></main>'}
    class Transport:
        def fetch(self,url):return pages[url],url
    events,seen,issues,_,_=collect_website({'url':'https://example.org/','platform':'website'},Transport(),max_pages=2)
    assert events[0]['start_date']=='2026-10-20' and len(seen)==3 and not issues


def test_telegram_pagination_uses_oldest_widget_even_when_it_has_no_text():
    def widget(number,body=''):
        return f'<div class="tgme_widget_message" data-post="channel/{number}"><time datetime="2026-10-20T10:00:00Z"></time>'+ (f'<div class="tgme_widget_message_text">{body}</div>' if body else '')+'</div>'
    class Transport:
        def __init__(self):self.urls=[]
        def fetch(self,url):
            self.urls.append(url)
            return (widget(100,'Первый')+widget(99) if len(self.urls)==1 else widget(98,'Второй')+widget(97)),url
    client=Transport();result=collect_preview('https://t.me/channel',client,limit=40,pages=2)
    assert client.urls==['https://t.me/s/channel','https://t.me/s/channel?before=99']
    assert [p.url for p in result.posts]==['https://t.me/channel/100','https://t.me/channel/98']


def test_mmoma_reads_current_parent_calendar_and_keeps_course_intervals_out_of_sessions():
    class Transport:
        def fetch(self,url):
            if '/api/page?' in url:return json.dumps({'id':19 if '%2Fgallery' in url else 24}),url
            records=[{'title':'Карта мифа','periodStart':'16.04.2026','periodEnd':'28.03.2027','path':'/visit/gallery/map','redirectPage':{'path':'/visit/gallery/map/description'},'tags':[{'title':'музейсидура'}]}] if '/19/' in url else [{'title':'Лекции','periodStart':'04.10.2026','periodEnd':'14.11.2026','path':'/visit/events/lectures','tags':[]}]
            return json.dumps(records),url
    events,links,pages=mmoma_calendar('https://mmoma.ru/visit/events',Transport())
    assert len(events)==1 and events[0]['end_date']=='2027-03-28'
    assert events[0]['venue_name']=='Музей Вадима Сидура · ММОМА'
    assert len(links)==2 and len(pages)==2


def test_real_mmoma_course_yields_individual_lectures_and_tour():
    html=(Path(__file__).parent/'fixtures/mmoma-lectures-real.html').read_text()
    events,adapter=extract(html,'https://mmoma.ru/visit/events/luzhniki70_lectures/description')
    assert adapter=='institution' and len(events)==6
    assert any(e['start_date']=='2026-10-25' and e['start_time']=='13:00' and e['event_type']=='talk' and e['title']=='Искусство и спорт — связь сквозь эпохи' for e in events)
    assert any(e['start_date']=='2026-10-23' and e['event_type']=='tour' and e['start_time']=='19:00' for e in events)
    assert all(e['end_date'] is None for e in events)


def test_real_mamm_separately_wrapped_digits_and_punctuation():
    html=(Path(__file__).parent/'fixtures/mamm-schlegel-real.html').read_text()
    exhibition,opening=extract(html,'https://mamm.art/exhibitions/2026/shlegel/')[0]
    assert (exhibition['start_date'],exhibition['end_date'])==('2026-09-23','2026-11-29')
    assert 'Шлегель' in exhibition['title'] and opening['review_status']=='tentative'


def test_dns_validation_is_reused_and_private_addresses_are_still_rejected(monkeypatch):
    import socket
    lookup=Mock(return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',0))])
    monkeypatch.setattr(socket,'getaddrinfo',lookup)
    client=Client(delay=0);client._safe('https://example.org/a');client._safe('https://example.org/b')
    assert lookup.call_count==1
    lookup.return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.0.0.1',0))]
    with pytest.raises(SourceError,match='Непубличный'):client._safe('https://private.example.org/a')


def test_afisha_recommendations_cannot_become_a_gallerys_primary_events():
    from ingestion.primary import require_primary_sources
    event={'primary_url':'https://www.afisha.ru/exhibition/example/','event_id':'A','source_id':'S'}
    events,review=require_primary_sources([event],[])
    assert events==[] and len(review)==1 and 'первоисточник' in review[0]['reason']


def test_proxy_dns_can_resolve_public_names_when_local_dns_times_out(monkeypatch):
    import ingestion.http as transport
    future=Mock();future.result.side_effect=transport.TimeoutError()
    monkeypatch.setattr(transport.DNS_POOL,'submit',Mock(return_value=future))
    monkeypatch.setattr(transport.requests.utils,'get_environ_proxies',lambda url:{'https':'http://environment-proxy'})
    Client()._safe('https://example.org/event')
    with pytest.raises(SourceError,match='Непубличный'):Client()._safe('http://127.0.0.1/event')
    monkeypatch.setattr(transport.requests.utils,'get_environ_proxies',lambda url:{})
    with pytest.raises(SourceError,match='таймаут DNS'):Client()._safe('https://example.org/event')


def test_a_programme_interval_cannot_become_an_exhibition_or_a_continuous_tour():
    h='<article><h3><a href="/summer-programme/">Мастерская «Куб»</a></h3><div class="date">17 октября — 19 декабря 2026</div></article>'
    assert extract(h,'https://example.org/')[0]==[]
    tour=h.replace('Мастерская «Куб»','Экскурсии по выставке').replace('/summer-programme/','/tours/')
    assert extract(tour,'https://example.org/')[0]==[]


def test_posting_date_in_a_wordpress_card_is_not_the_lecture_date():
    h='<article><h3><a href="/lecture/">Лекция о выставке</a></h3><div class="posted-on"><time><span>20 октября 2026</span></time></div></article>'
    assert extract(h,'https://example.org/')[0]==[]


def test_old_event_ids_survive_an_exhibition_without_an_end_date_on_another_day():
    from ingestion.models import preserve_event_ids
    old={'event_id':'OLD','institution_id':'A','event_type':'exhibition','title':'Проект','start_date':'2026-10-20','primary_url':'https://example.org/exhibitions/a'}
    a=dict(old,event_id='NEW');b=dict(old,event_id='OTHER',start_date='2026-10-21')
    result=preserve_event_ids([a,b],[old])
    assert result[0]['event_id']=='OLD' and result[1]['event_id']=='OTHER'


def test_generic_section_heading_uses_the_actual_og_event_title():
    h='<meta property="og:title" content="OMNIA MUTANTUR"><main><h1>Проекты</h1><h2>OMNIA MUTANTUR</h2><div class="date">1 октября — 30 ноября 2026</div></main>'
    e=extract(h,'https://example.org/exhibitions/79')[0]
    assert e[0]['title']=='OMNIA MUTANTUR'


def test_archival_film_screening_at_mmoma_is_not_an_exhibition_opening():
    h='<main><h1>Показ архивного фильма: художник Александр Панкин</h1><div class="date">22.10 — 22.10.2026</div><p>Архив выставки в музее</p></main>'
    events=extract(h,'https://mmoma.ru/visit/events/film/description')[0]
    assert len(events)==1 and events[0]['event_type']=='screening'


def test_a_london_fair_post_is_not_assigned_to_the_moscow_channel_owner():
    from ingestion.adapters.social import SocialPost,parse_post
    from ingestion.provisional import tentative_post
    text='С 14 по 18 октября в лондонском Риджентс-парке пройдут Frieze London и Frieze Masters — две ярмарки.'
    post=SocialPost(text,'https://t.me/channel/1','2026-10-10T12:00:00Z','telegram','telegram_public_preview','channel')
    events,reason=parse_post(post)
    assert events==[] and 'за пределами Москвы' in reason
    assert tentative_post({'description':text,'primary_url':post.url,'published_at':post.published_at})==[]


def test_flat_exhibition_announcement_keeps_title_and_period_instead_of_a_two_week_opening():
    from ingestion.provisional import tentative_post
    result=tentative_post({'description':'Саша Лемиш персональная выставка ХЛЕБА 17.10 — 01.11 вернисаж 17.10 в 18:00 Проект изучает ограничение средств выражения.',
        'primary_url':'https://t.me/channel/1','published_at':'2026-10-17T10:00:00Z'})
    assert result[0]['title']=='ХЛЕБА' and result[0]['event_type']=='exhibition'
    assert result[0]['end_date']=='2026-11-01'
    assert len(result)==2
    assert (result[1]['event_type'],result[1]['start_date'],result[1]['end_date'],result[1]['start_time'])==('opening','2026-10-17',None,'18:00')


def test_legacy_opening_range_keeps_the_opening_id_and_separate_exhibition():
    from ingestion.models import normalize_openings,deduplicate,link_parents
    old={'event_id':'EV_472C9AC7CA5F6FA8A2','institution_id':'MSK068','title':'ХЛЕБА','event_type':'opening',
        'start_date':'2026-10-17','end_date':'2026-11-01','start_time':'18:00','description':'Персональная выставка Саши Лемиша',
        'primary_url':'https://t.me/ivanygallery/348'}
    events=link_parents(deduplicate(normalize_openings([old])))
    opening=next(e for e in events if e['event_type']=='opening')
    exhibition=next(e for e in events if e['event_type']=='exhibition')
    assert opening['event_id']==old['event_id'] and opening['end_date'] is None
    assert opening['start_time']=='18:00' and opening['parent_event_id']==exhibition['event_id']
    assert exhibition['end_date']=='2026-11-01' and exhibition['start_time'] is None
    assert normalize_openings(events)==events


def test_opening_merge_cannot_restore_an_exhibition_range():
    from ingestion.models import deduplicate
    opening={'event_id':'ONE','institution_id':'VENUE','title':'Открытие выставки «Проект»','event_type':'opening',
        'start_date':'2026-10-17','end_date':None,'primary_url':'https://example.org/events/project'}
    merged=deduplicate([opening,dict(opening,event_id='OLD',end_date='2026-11-01')])
    assert len(merged)==1 and merged[0]['end_date'] is None


def test_mmoma_workshop_sessions_use_api_type_instead_of_incidental_exhibition_word():
    from ingestion.adapters.mmoma import parse_mmoma
    url='https://mmoma.ru/visit/events/workshop/description'
    h='<main><h1>Творческие занятия</h1><p>25.10-15.11.2026</p><p>25.10 | 12:30 — 14:30</p><h2>Придумываем героев</h2><p>Занятие на выставке</p></main>'
    events=parse_mmoma(h,url,{'event_types':{url:'workshop'}})
    assert len(events)==1 and events[0]['event_type']=='workshop'


def test_paris_exhibition_opening_in_news_is_not_a_moscow_event():
    from ingestion.adapters.social import foreign_event_location
    assert foreign_event_location('В парижской Bourse de Commerce открылась Remember Me — выставка фотографии.')


def test_legacy_recurrence_bounds_become_a_programme_without_changing_saved_id():
    from ingestion.run import programme_period
    old={'event_id':'OLD','title':'Экскурсии','event_type':'tour','start_date':'2026-09-17','end_date':'2027-02-20','start_time':'12:00'}
    result=programme_period(old,7)
    assert result['event_id']=='OLD' and result['event_type']=='other' and result['start_time'] is None
    assert result['review_status']=='tentative' and result['source_title']=='Экскурсии'
    weekend=dict(old,event_type='workshop',start_date='2026-10-10',end_date='2026-10-11')
    assert programme_period(weekend,7)==weekend
    assert programme_period(dict(old,title=''))['title']==''


def test_conflicting_official_calendar_and_detail_dates_are_marked_tentative(monkeypatch):
    import ingestion.extraction as module
    url='https://mmoma.ru/visit/gallery/project/description'
    api={'title':'Проект','event_type':'exhibition','primary_url':url,'start_date':'2026-09-03','end_date':'2026-11-15','confidence':'institution_public_api'}
    monkeypatch.setattr(module,'mmoma_calendar',lambda *a:([api],[url],[]))
    class Transport:
        def fetch(self,target):
            html='<main><h1>Проект</h1><h3><a href="/know/building/petrovka">ПЕТРОВКА 25</a></h3><div>03.09.2025 — 15.11.2026</div></main>' if target==url else '<main></main>'
            return html,target
    events,*_=module.collect_website({'url':'https://mmoma.ru/visit/events','platform':'website'},Transport(),max_pages=1,observed_on='2026-10-20')
    assert len(events)==1 and events[0]['start_date']=='2025-09-03'
    assert events[0]['review_status']=='tentative' and 'официальном календаре' in events[0]['uncertainties'][0]
