from pathlib import Path
from bs4 import BeautifulSoup
from ingestion.adapters.advanced import parse_advanced, russian_version
from ingestion.adapters import discover_links
from ingestion.run import refresh

FIX = Path(__file__).parent/'fixtures'
URL = 'https://xl.gallery/ru/exhibition/10-26-287'


def test_real_xl_detail_extracts_period_separately_from_biography_years():
    events=parse_advanced((FIX/'xl-exhibition-real.html').read_text(),URL)
    exhibition,opening=events
    assert exhibition['title']=='Сапожников Сергей. 10 - 26'
    assert (exhibition['start_date'],exhibition['end_date'])==('2026-10-20','2026-11-28')
    assert '2010' in exhibition['description']
    assert exhibition.get('review_status')!='tentative'
    assert opening['event_type']=='opening' and opening['start_date']=='2026-10-20'
    assert opening['start_time'] is None and opening['review_status']=='tentative'
    assert opening['date_basis']=='exhibition_start' and opening['uncertainties']
    assert 'XL Gallery 1993' not in exhibition['description']


def test_xl_home_is_a_discovery_page_and_is_not_a_single_event():
    html=(FIX/'xl-home-real.html').read_text()
    assert parse_advanced(html,'https://xl.gallery/ru/')==[]
    links=discover_links(html,'https://xl.gallery/ru/',3)
    assert links[0]==URL and len(links)==3
    assert all('/ru/exhibition/' in link for link in links)


def test_language_switch_and_index_navigation_do_not_consume_the_page_budget():
    html='<html lang="en"><a href="/ru/">ru</a><a href="/en/exhibitions">Exhibitions</a><a href="/en/exhibition/next">Next</a><a href="/ru/exhibition/next">Русский</a></html>'
    assert russian_version(html,'https://xl.gallery/en/')=='https://xl.gallery/ru/'
    assert discover_links(html,'https://xl.gallery/en/',1)==['https://xl.gallery/en/exhibition/next']
    assert russian_version('<html lang="ru"><a href="https://other.example/">ru</a></html>',URL) is None


def test_microdata_and_rdfa_event_fields_are_parsed_without_a_site_adapter():
    html='''<div itemscope itemtype="https://schema.org/ExhibitionEvent"><span itemprop="name">Выставка</span><meta itemprop="startDate" content="2026-10-20"><meta itemprop="endDate" content="2026-11-28"></div>'''
    events=parse_advanced(html,'https://example.org/exhibition/test')
    assert len(events)==2 and events[0]['confidence']=='rich_metadata'
    assert events[0]['event_type']=='exhibition' and events[0]['end_date']=='2026-11-28'
    assert events[1]['review_status']=='tentative'


def test_fallback_does_not_date_an_event_from_footer_or_author_biography():
    html='<main><h1>Новая выставка</h1><p>Автор родился в 1984 году. Работы созданы в 2010 и 2026 годах.</p><div class="date">20 октября — 28 ноября</div></main><footer>2026</footer>'
    assert parse_advanced(html,URL)==[]
    assert parse_advanced(html.replace('20 октября — 28 ноября','October 20 - November 28, 2026'),URL)[0]['start_date']=='2026-10-20'
    assert parse_advanced(html.replace('20 октября — 28 ноября','20 октября — 28 ноября, 2026'),URL.replace('/exhibition/','/artist/'))==[]


def test_source_refresh_discovers_xl_from_english_redirect_and_keeps_opening_uncertainty():
    home=(FIX/'xl-home-real.html').read_text();detail=(FIX/'xl-exhibition-real.html').read_text()
    class Pages:
        def fetch(self,url):
            if url=='https://xl.gallery/': return '<html lang="en"><a href="/ru/">ru</a></html>','https://xl.gallery/en/'
            if url=='https://xl.gallery/ru/': return home,url
            assert url==URL
            return detail,url
    catalog={'metadata':{'updated_on':'2026-10-19'},'institutions':[{'institution_id':'A','name':'XL','monitor_state':'monitor'}],
        'sources':[{'source_id':'S','url':'https://xl.gallery/','platform':'website','institution_ids':['A']}],
        'institution_sources':[{'source_id':'S','institution_id':'A','role':'announcements'}]}
    overrides={'publication_policy':'include_tentative','manual_events':[],'corrections':{},'duplicates':{},'suppress':[],'priorities':{},'disabled_sources':[],'parser_rules':{}}
    feed,review=refresh(catalog,overrides,{'events':[],'sources':[]},Pages(),max_pages=1)
    assert not review and len(feed['events'])==2
    assert next(e for e in feed['events'] if e['event_type']=='opening')['review_status']=='tentative'
    assert feed['sources'][0]['adapter']=='trafilatura_extruct'
    assert feed['sources'][0]['detected_events']==1 and feed['sources'][0]['tentative_events']==1


def test_full_rdfa_schema_type_and_timestamp_are_supported():
    html='''<div vocab="https://schema.org/" typeof="ExhibitionEvent"><span property="name">10–26</span><meta property="startDate" content="2026-10-20T18:00:00+03:00"><meta property="endDate" content="2026-11-28"></div>'''
    exhibition,opening=parse_advanced(html,URL)
    assert exhibition['event_type']=='exhibition' and exhibition['start_time']=='18:00'
    assert opening['event_type']=='opening' and opening['start_time']=='18:00'


def test_an_explicit_vernissage_is_not_replaced_by_an_inferred_first_day():
    html='''<main><h1>Проект</h1><div class="event-date">20 октября — 28 ноября, 2026</div><div class="event-date">Вернисаж 20 октября в 19:00</div><p>Реальная выставка современного искусства.</p></main>'''
    exhibition,opening=parse_advanced(html,URL)
    assert exhibition['event_type']=='exhibition'
    assert opening['event_type']=='opening' and opening['start_time']=='19:00'
    assert opening.get('review_status')!='tentative'


def test_homepage_microdata_is_accepted_only_with_an_individual_event_url():
    html='''<div itemscope itemtype="https://schema.org/ExhibitionEvent"><span itemprop="name">Выставка</span><meta itemprop="startDate" content="2026-10-20"><link itemprop="url" href="/exhibition/test"></div>'''
    events=parse_advanced(html,'https://example.org/')
    assert len(events)==2 and all(e['primary_url']=='https://example.org/exhibition/test' for e in events)
    assert parse_advanced(html.replace('<link itemprop="url" href="/exhibition/test">',''),'https://example.org/')==[]
