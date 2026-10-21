from datetime import datetime,timezone
import json
from pathlib import Path
import pytest
from ingestion.adapters.social import SocialPost,parse_post
from ingestion.adapters.telegram import parse_preview,collect_preview,telegram_identity
from ingestion.adapters.instagram import InstagramAPI,collect_instagram,collect_exports
from ingestion.http import SourceError
from ingestion.run import refresh

FIX=Path(__file__).parent/'fixtures'


def post(text,date='2026-10-13T09:34:37+00:00',platform='telegram'):
    return SocialPost(text,'https://t.me/ivanygallery/346' if platform=='telegram' else 'https://www.instagram.com/p/TESTPOST/',date,platform,'test_fixture','ivanygallery')


def test_real_telegram_preview_dates_and_opening():
    posts=parse_preview((FIX/'telegram-real.html').read_text(),'ivanygallery')
    assert len(posts)==2
    exhibition,_=parse_post(posts[0]);upcoming,reason=parse_post(posts[1])
    assert exhibition[0]['title']=='GIANTS';assert exhibition[0]['end_date']=='2026-10-11'
    assert reason is None;assert len(upcoming)==2
    assert upcoming[0]['title']=='ХЛЕБА';assert upcoming[0]['start_date']=='2026-10-17';assert upcoming[0]['end_date']=='2026-11-01'
    assert upcoming[1]['event_type']=='opening';assert upcoming[1]['start_time']=='18:00'
    assert upcoming[0]['address']=='Балашиха, Керамическая, 1с9'
    assert upcoming[0]['date_basis']=='publication_context'
    assert all(e['primary_url']=='https://t.me/ivanygallery/346' for e in upcoming)


def test_public_post_identity_and_no_forwarded_attribution():
    assert telegram_identity('https://tg.me/ivanygallery')==('ivanygallery',None)
    assert telegram_identity('https://t.me/s/ivanygallery/346')==('ivanygallery',346)
    with pytest.raises(SourceError):telegram_identity('https://t.me/+private-invite')
    html='<div class="tgme_widget_message" data-post="ivanygallery/1"><span class="tgme_widget_message_forwarded_from">Другая площадка</span><div class="tgme_widget_message_text">Выставка</div><time datetime="2026-10-13T00:00:00Z"/></div>'
    assert parse_preview(html,'ivanygallery')==[]


def test_biographies_and_closing_dates_do_not_invent_events():
    events,reason=parse_post(post('Анна\nучастница выставки\nРабота 2024\nУспейте до 17.10'))
    assert events==[]
    events,reason=parse_post(post('Выставка\nНазвание\nдо 17 октября 2026'))
    assert events==[];assert reason


def test_year_rollover_uses_post_context():
    events,reason=parse_post(post('Выставка\nЗима\n10.01 — 15.01','2026-12-28T12:00:00Z'))
    assert not reason;assert events[0]['start_date']=='2027-01-10';assert events[0]['end_date']=='2027-01-15'


def test_multiple_distinct_dates_go_to_review():
    events,reason=parse_post(post('Выставка\nНазвание\n17.10.2026\n24.10.2026'))
    assert not events;assert 'несколько дат' in reason


def test_artist_year_does_not_override_announcement_year():
    events,reason=parse_post(post('Персональная выставка\nНазвание\n17.10 — 21.10\nХудожник родился в 1985 году.'))
    assert events[0]['start_date']=='2026-10-17'


class Response:
    def __init__(self,data,status=200):self.data=data;self.status_code=status
    def json(self):return self.data
class Session:
    def __init__(self,response):self.response=response;self.calls=[]
    def get(self,url,**kwargs):self.calls.append((url,kwargs));return self.response


def test_official_instagram_api_never_scrapes_profiles_or_embeds_token_in_url():
    session=Session(Response({'business_discovery':{'username':'ivanygallery','media':{'data':[{'id':'1','caption':'Выставка\nНазвание\n17.10 — 21.10','permalink':'https://www.instagram.com/p/TESTPOST/','timestamp':'2026-10-13T12:00:00+0000'}]}}}))
    collection=InstagramAPI('test-token','12345',session=session).collect('ivanygallery')
    assert collection.live;assert len(collection.posts)==1
    url,kwargs=session.calls[0];assert url=='https://graph.facebook.com/v24.0/12345';assert 'test-token' not in url
    assert kwargs['headers']['Authorization']=='Bearer test-token';assert 'access_token' not in kwargs['params']
    events,reason=parse_post(collection.posts[0]);assert not reason;assert len(events)==1;assert events[0]['title']=='Название';assert events[0]['verification_method']=='instagram_official_api'


def test_instagram_rate_limit_stops_without_retry_or_error_secret_leak():
    session=Session(Response({'error':{'code':4,'message':'private account token=should-not-persist'}},429))
    with pytest.raises(SourceError) as error:InstagramAPI('test-token','12345',session=session).collect('ivanygallery')
    assert error.value.status=='blocked';assert len(session.calls)==1;assert 'should-not-persist' not in str(error.value)


def test_own_account_token_cannot_collect_another_profile():
    session=Session(Response({}))
    api=InstagramAPI('test-token','12345',mode='own_account',account_username='my_account',session=session)
    with pytest.raises(SourceError):api.collect('ivanygallery')
    assert not session.calls


def test_missing_instagram_access_is_truthful_and_does_not_attempt_login(monkeypatch,tmp_path):
    with pytest.raises(SourceError) as e:collect_instagram('https://instagram.com/ivanygallery/',export_root=tmp_path)
    assert e.value.status=='manual';assert not e.value.attempted


def test_instaloader_exports_are_offline_and_require_review(tmp_path,monkeypatch):
    def no_requests(*args,**kwargs):raise AssertionError('Offline exports must never issue HTTP requests')
    monkeypatch.setattr('requests.sessions.Session.request',no_requests)
    folder=tmp_path/'ivanygallery';folder.mkdir()
    data={'instaloader':{'node_type':'Post','version':'4.15.4'},'node':{'__typename':'GraphImage','id':'12345','shortcode':'TESTPOST','is_video':False,'owner':{'id':'777','username':'ivanygallery'},'taken_at_timestamp':int(datetime(2026,10,13,tzinfo=timezone.utc).timestamp()),'edge_media_to_caption':{'edges':[{'node':{'text':'Персональная выставка\nНазвание\n17.10 — 21.10'}}]}}}
    (folder/'post.json').write_text(json.dumps(data))
    collection=collect_exports(tmp_path,'ivanygallery')
    assert len(collection.posts)==1;assert not collection.live;assert collection.adapter=='instaloader_export'
    events,_=parse_post(collection.posts[0]);assert len(events)==1


def test_telegram_ingestion_integration_and_repeatability():
    catalog={'metadata':{'updated_on':'2026-10-16'},'institutions':[{'institution_id':'A','name':'Иваний','monitor_state':'monitor','monitoring_priority':'high','tags':['artist_run']}],
        'sources':[{'source_id':'T1','url':'https://t.me/ivanygallery','platform':'telegram','institution_ids':['A']}],
        'institution_sources':[{'source_id':'T1','institution_id':'A','role':'announcements'}]}
    overrides={'manual_events':[],'corrections':{},'suppress':[],'duplicates':{},'priorities':{},'disabled_sources':[],'parser_rules':{}}
    class Client:
        def __init__(self):self.requests=[]
        def fetch(self,url):
            self.requests.append(url)
            if url!='https://t.me/s/ivanygallery':raise SourceError('Связанная страница недоступна в тестовом транспорте')
            return (FIX/'telegram-real.html').read_text(),url
    client=Client();first,review=refresh(catalog,overrides,{'events':[],'sources':[]},client)
    assert len(first['events'])==3;assert first['sources'][0]['posts_seen']==2;assert first['sources'][0]['status']=='working'
    assert all(e['source_platform']=='telegram' for e in first['events']);assert client.requests.count('https://t.me/s/ivanygallery')==1
    second,_=refresh(catalog,overrides,first,Client());assert len(second['events'])==3;assert second['sources'][0]['new_events']==0
    opening=next(e for e in second['events'] if e['event_type']=='opening');assert opening['parent_event_id'] in {e['event_id'] for e in second['events']}


def test_actual_announcement_edge_cases_reach_review_instead_of_wrong_calendar():
    rows=json.loads((FIX/'social-audit-real.json').read_text())
    results={row['url']:parse_post(SocialPost(**row)) for row in rows}
    assert results['https://t.me/zaykaspace/271'][0]==[]
    assert 'несколько дат' in results['https://t.me/zaykaspace/271'][1]
    assert results['https://t.me/ProstranstvoProstranstv/29'][0]==[]
    assert 'Екатеринбург' in results['https://t.me/piranesilab/2309'][1]
    dni=results['https://t.me/dniculture/534'][0][0]
    assert dni['title']=='«визуальный шум»';assert dni['event_type']=='tour';assert dni['start_time']=='18:00'
    arendt=results['https://t.me/Arendt_and_Co/477'][0][0];assert arendt['start_time']=='19:00'
    assert results['https://t.me/triumphgallery/4346'][0]==[]
    assert 'участия' in results['https://t.me/triumphgallery/4346'][1]
    fusion=results['https://t.me/piranesilab/2328'][0][0]
    assert fusion['title']=='«Фузия»';assert fusion['start_date']=='2026-09-10';assert fusion['end_date']=='2026-10-25'


def test_inline_quoted_event_heading_and_date_are_supported():
    events,reason=parse_post(post('Открытие выставки «Название» 17 октября 2026 в 18:00'))
    assert not reason;assert events[0]['title']=='«Название»';assert events[0]['start_time']=='18:00'


def test_telethon_missing_authorization_never_starts_login(monkeypatch):
    from ingestion.adapters.telegram import collect_telegram
    monkeypatch.setenv('TELEGRAM_MODE','api')
    for name in ('TELEGRAM_API_ID','TELEGRAM_API_HASH','TELEGRAM_SESSION'):monkeypatch.delenv(name,raising=False)
    with pytest.raises(SourceError) as e:collect_telegram('https://t.me/ivanygallery',object())
    assert e.value.status=='manual';assert not e.value.attempted


def test_expanded_real_channel_posts_do_not_publish_promotions_or_artwork_ratios():
    rows=json.loads((FIX/'telegram-expanded-real.json').read_text())
    results={row['url']:parse_post(SocialPost(**row)) for row in rows}
    for url in ['https://t.me/galleryfineart/1179','https://t.me/hseartgallery/4750','https://t.me/rostokino_gallery/2042','https://t.me/khodynkagallery/2608']:
        assert results[url][0]==[]
    assert results['https://t.me/khodynkagallery/2589'][0][0]['event_type']=='workshop'
    assert results['https://t.me/khodynkagallery/2591'][0][0]['event_type']=='screening'
    assert results['https://t.me/khodynkagallery/2599'][0][0]['event_type']=='screening'
    mamm=results['https://t.me/multimediaartmuseum/6974'][0][0]
    assert (mamm['event_type'],mamm['start_date'],mamm['start_time'])==('talk','2026-10-21','19:30')


def test_generic_heading_does_not_treat_date_as_event_title():
    events,reason=parse_post(post('Выставка\n17 октября 2026'))
    assert not events;assert reason
