from pathlib import Path
import pytest
from ingestion.adapters.social import SocialPost,parse_post
from ingestion.adapters.telegram import parse_preview
from ingestion.extraction import extract
from ingestion.http import SourceError
from ingestion.linked import LinkedResolver
from ingestion.models import complete_event,deduplicate,preserve_event_ids
from ingestion.run import refresh

FIX=Path(__file__).parent/'fixtures'
URL='https://art.hse.ru/news/7306'
TEXT='«алеа»: презентация альбома Софии Ивановой\n21 октября София Иванова представит альбом «алеа».\nИнтерактивный перформанс в пространстве «Склад №3».\n21 октября, 20:00–23:00. Москва, Малая Семёновская улица, 5, стр. 2.'
POST=SocialPost(TEXT,'https://t.me/hsedesign/18565','2026-10-19T18:10:34+00:00','telegram','test_fixture','hsedesign',(URL+'?utm_source=tg',))


class Transport:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def fetch(self,url):
        self.calls.append(url)
        result=self.pages[url]
        if isinstance(result,Exception):raise result
        return result,url


def resolve(client,post=POST):return LinkedResolver(client).resolve(post,*parse_post(post))


def test_actual_hse_news_uses_event_schedule_instead_of_publication_day():
    events,adapter=extract((FIX/'hse-alea-real.html').read_text(),URL)
    assert adapter=='institution' and len(events)==1
    event=events[0]
    assert event['title']=='Презентация альбома студентки ШД Софии Ивановой «алеа»'
    assert (event['start_date'],event['start_time'],event['end_time'])==('2026-10-21','20:00','23:00')
    assert event['venue_name']=='Склад №3' and 'Малая Семёновская' in event['address']
    assert event['end_date'] is None
    earlier_publication=(FIX/'hse-alea-real.html').read_text().replace('21 октября 2026','19 октября 2026')
    assert extract(earlier_publication,URL)[0][0]['start_date']=='2026-10-21'


def test_telegram_link_replaces_a_weak_title_and_preserves_both_sources():
    client=Transport({URL:(FIX/'hse-alea-real.html').read_text()})
    events,reason,issues,pages=resolve(client)
    assert not reason and not issues and client.calls==[URL]
    item=events[0]
    assert item['primary_url']==URL and item['origin_post_url']==POST.url
    assert item['start_time']=='20:00' and 'полноформатного альбома' in item['description']
    completed=complete_event(item,{'institution_id':'A','name':'Галерея','tags':[]},{'source_id':'TG','platform':'telegram'},'2026-10-21T12:00:00Z')
    assert {e['url'] for e in completed['evidence']}=={URL,POST.url}
    assert all(e.get('checked_at') for e in completed['evidence'])


@pytest.mark.parametrize('change',[
    lambda h:h.replace('21 октября','22 октября'),
    lambda h:h.replace('Презентация альбома студентки ШД Софии Ивановой «алеа»','Кураторская экскурсия по музею'),
])
def test_a_different_date_or_subject_does_not_replace_the_telegram_event(change):
    client=Transport({URL:change((FIX/'hse-alea-real.html').read_text())})
    original,reason=parse_post(POST)
    actual,actual_reason,issues,_=resolve(client)
    assert actual==original and actual_reason==reason and issues


def test_link_failure_preserves_the_original_parse():
    actual,reason,issues,_=resolve(Transport({URL:SourceError('HTTP 403','blocked')}))
    assert (actual,reason)==parse_post(POST)
    assert issues[0]['status']=='blocked'


def test_bounded_following_and_shared_cache():
    client=Transport({URL:(FIX/'hse-alea-real.html').read_text()});resolver=LinkedResolver(client,max_pages=1)
    resolver.resolve(POST,*parse_post(POST));resolver.resolve(POST,*parse_post(POST))
    assert client.calls==[URL]
    different=SocialPost(TEXT,POST.url,POST.published_at,'telegram','test_fixture','hsedesign',('https://example.org/event/another',))
    _,_,issues,_=resolver.resolve(different,*parse_post(different))
    assert len(client.calls)==1 and 'лимит' in issues[0]['reason']


def test_registration_link_is_followed_once_without_creating_an_extra_event():
    registration='https://example.timepad.ru/event/123/'
    html='<article><h1>Лекция Софии Ивановой об искусстве</h1><p>21 октября 2026 в 20:00</p><a href="'+registration+'">Регистрация</a></article>'
    reg='<article><h1>Лекция Софии Ивановой об искусстве</h1><p>21 октября 2026 в 20:00</p></article>'
    post=SocialPost('Лекция Софии Ивановой об искусстве\n21 октября 2026 в 20:00',POST.url,POST.published_at,'telegram','test_fixture','hsedesign',('https://example.org/events/lecture',))
    client=Transport({'https://example.org/events/lecture':html,registration.rstrip('/'):reg})
    events,reason,_,_=resolve(client,post)
    assert not reason and len(events)==1
    assert events[0]['primary_url']=='https://example.org/events/lecture'
    assert events[0]['registration_url']==registration.rstrip('/')
    assert len(client.calls)==2


def test_learning_a_clock_from_the_link_keeps_the_old_id_without_a_duplicate():
    item=resolve(Transport({URL:(FIX/'hse-alea-real.html').read_text()}))[0][0]
    old={'event_id':'EV_760D944357DE58630F','institution_id':'A','title':'Неясный заголовок','title_is_tentative':True,
        'title_basis':'fallback','event_type':'performance','start_date':'2026-10-21','start_time':None,'primary_url':POST.url}
    new=complete_event(item,{'institution_id':'A','name':'Галерея','tags':[]},{'source_id':'TG','platform':'telegram'},'2026-10-21T12:00:00Z')
    events=preserve_event_ids(deduplicate([old,new]),[old])
    assert len(events)==1 and events[0]['event_id']==old['event_id'] and events[0]['start_time']=='20:00'


@pytest.mark.parametrize('role',['announcements','community'])
def test_refresh_enriches_links_even_when_social_heading_needs_review(role):
    url='https://t.me/s/hsedesign'
    preview='<div class="tgme_widget_message" data-post="hsedesign/18565"><time datetime="2026-10-19T18:10:34+00:00"></time><div class="tgme_widget_message_text">'+TEXT.replace('\n','<br>')+'<a href="'+URL+'?utm_source=tg">Подробности</a></div></div>'
    client=Transport({url:preview,URL:(FIX/'hse-alea-real.html').read_text()})
    catalog={'metadata':{'updated_on':'2026-10-21'},'institutions':[{'institution_id':'A','name':'Галерея','monitor_state':'monitor','tags':[]}],
        'sources':[{'source_id':'TG','url':'https://t.me/hsedesign','platform':'telegram','institution_ids':['A']}],
        'institution_sources':[{'source_id':'TG','institution_id':'A','role':role}]}
    overrides={'manual_events':[],'corrections':{},'suppress':[],'duplicates':{},'priorities':{},'disabled_sources':[],'parser_rules':{},'publication_policy':'include_tentative'}
    feed,review=refresh(catalog,overrides,{'events':[],'sources':[]},client)
    assert not review and len(feed['events'])==1
    event=feed['events'][0]
    assert event['primary_url']==URL and event['venue_name']=='Склад №3' and event['start_time']=='20:00'
    assert {e['url'] for e in event['evidence']}=={URL,POST.url}
    assert feed['sources'][0]['linked_pages'][0]['matched_events']==1


def test_unsafe_social_or_index_links_are_not_followed():
    client=Transport({});post=SocialPost(TEXT,POST.url,POST.published_at,'telegram','test_fixture','hsedesign',('https://t.me/another/1','https://example.org/events','javascript:alert(1)','https://example.org/image.jpg'))
    resolve(client,post)
    assert not client.calls
