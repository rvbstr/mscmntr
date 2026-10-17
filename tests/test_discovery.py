import json
from pathlib import Path
import pytest
from ingestion.discover_telegram import channel_url, extract_links
from ingestion.import_catalog import ROOT, import_data
from ingestion.run import refresh


@pytest.mark.parametrize('url,expected', [
    ('https://t.me/Gallery_Name/123?single', 'https://t.me/gallery_name'),
    ('https://tg.me/Gallery_Name', 'https://t.me/gallery_name'),
    ('https://telegram.me/s/Gallery_Name/12', 'https://t.me/gallery_name'),
    ('tg://resolve?domain=Gallery_Name', 'https://t.me/gallery_name'),
    ('//t.me/Gallery_Name', 'https://t.me/gallery_name'),
    ('https://t.me/share/url?url=https://example.org', None),
    ('https://t.me/+private_invite', None),
    ('https://t.me/gallery_contact_bot', None),
    ('https://t.me.evil.example/gallery_name', None),
    ('javascript:alert(1)', None),
])
def test_public_channel_urls_exclude_share_invites_bots_and_other_hosts(url, expected):
    assert channel_url(url) == expected


def test_discovery_reads_footer_and_json_without_truncating_invalid_usernames():
    html = '<footer><a href="https://t.me/Gallery_Name">Наш канал</a></footer><script>{"social":"https:\\/\\/t.me\\/second_gallery","broken":"https://t.me/sample-art"}</script>'
    links = extract_links(html, 'https://example.org/')
    assert {r['url'] for r in links} == {'https://t.me/gallery_name', 'https://t.me/second_gallery'}
    assert next(r for r in links if r['url'].endswith('gallery_name'))['anchor'] == 'Наш канал'
    assert all(r['page_url'] == 'https://example.org/' for r in links)


def supplement(tmp_path, url='https://t.me/new_test_gallery', owner='MSK068'):
    p = tmp_path / 'additional.json'
    p.write_text(json.dumps({'updated_on': '2026-10-17', 'sources': [{'source_id': 'NEW_TG', 'platform': 'telegram', 'url': url}],
        'institution_sources': [{'institution_id': owner, 'source_id': 'NEW_TG', 'role': 'announcements', 'officiality': 'official_link', 'identity_evidence_url': 'https://ivanygallery.com/', 'identity_checked_on': '2026-10-17'}]}))
    return p


def test_additive_import_preserves_original_workbook_and_relationships(tmp_path):
    (tmp_path / 'catalog').mkdir()
    catalog = import_data(ROOT / 'catalog/original.json', ROOT / 'catalog/original.xlsx', tmp_path, supplement(tmp_path))
    assert len(catalog['institutions']) == 93
    assert len(catalog['sources']) == 144
    assert len(catalog['institution_sources']) == 165
    assert catalog['metadata']['counts']['sources'] == 144
    assert catalog['metadata']['additional_sources_count'] == 1
    assert 'NEW_TG' in next(i for i in catalog['institutions'] if i['institution_id'] == 'MSK068')['source_ids']
    normalized = json.loads((tmp_path / 'catalog/normalized.json').read_text())
    assert len(normalized['sources']) == 143
    assert len(normalized['institution_sources']) == 164
    assert 'additional_sources_sha256' in catalog['import_provenance']


def test_additive_import_rejects_telegram_alias_duplicate_and_unknown_owner(tmp_path):
    (tmp_path / 'catalog').mkdir()
    with pytest.raises(ValueError, match='URL'):
        import_data(ROOT / 'catalog/original.json', ROOT / 'catalog/original.xlsx', tmp_path, supplement(tmp_path, 'https://tg.me/IVANYGALLERY'))
    with pytest.raises(ValueError, match='связь'):
        import_data(ROOT / 'catalog/original.json', ROOT / 'catalog/original.xlsx', tmp_path, supplement(tmp_path, owner='UNKNOWN'))


def test_archive_channel_is_not_requested():
    class NoNetwork:
        def fetch(self, url):
            raise AssertionError('Archived source must not be fetched')
    catalog = {'metadata': {'updated_on': '2026-10-17'}, 'institutions': [{'institution_id': 'A', 'name': 'Архив', 'monitor_state': 'watchlist', 'monitoring_priority': 'normal', 'tags': []}],
        'sources': [{'source_id': 'S', 'url': 'https://t.me/test_archive', 'platform': 'telegram', 'institution_ids': ['A'], 'collection_enabled': False, 'collection_disabled_reason': 'Институт закрыт'}], 'institution_sources': []}
    overrides = {'priorities': {}, 'disabled_sources': [], 'manual_events': [], 'corrections': {}, 'suppress': [], 'duplicates': {}, 'parser_rules': {}}
    feed, review = refresh(catalog, overrides, {'events': [], 'sources': []}, NoNetwork())
    assert not feed['events'] and not review
    assert feed['sources'][0]['status'] == 'disabled'
    assert feed['sources'][0]['error'] == 'Институт закрыт'


def test_unconfirmed_identity_never_publishes_even_if_relation_is_wrongly_enabled():
    class Preview:
        def fetch(self, url):
            return (Path(__file__).parent / 'fixtures/telegram-real.html').read_text(), url
    catalog = {'metadata': {'updated_on': '2026-10-17'}, 'institutions': [{'institution_id': 'A', 'name': 'Галерея', 'monitor_state': 'monitor', 'monitoring_priority': 'normal', 'tags': []}],
        'sources': [{'source_id': 'S', 'url': 'https://t.me/ivanygallery', 'platform': 'telegram', 'institution_ids': ['A'], 'requires_identity_confirmation': True}],
        'institution_sources': [{'institution_id': 'A', 'source_id': 'S', 'role': 'announcements'}]}
    overrides = {'priorities': {}, 'disabled_sources': [], 'manual_events': [], 'corrections': {}, 'suppress': [], 'duplicates': {}, 'parser_rules': {}}
    feed, review = refresh(catalog, overrides, {'events': [], 'sources': []}, Preview())
    assert not feed['events']
    assert len(review) == 3
    assert feed['sources'][0]['status'] == 'review'
    assert feed['sources'][0]['posts_seen'] == 2


def test_multi_city_channel_requires_explicit_location_before_publication():
    class Preview:
        def fetch(self, url):
            html = (Path(__file__).parent / 'fixtures/telegram-real.html').read_text()
            assert 'Москва' in html
            return html.replace('Москва', ''), url
    catalog = {'metadata': {'updated_on': '2026-10-17'}, 'institutions': [{'institution_id': 'A', 'name': 'Галерея', 'monitor_state': 'monitor', 'monitoring_priority': 'normal', 'tags': []}],
        'sources': [{'source_id': 'S', 'url': 'https://t.me/ivanygallery', 'platform': 'telegram', 'institution_ids': ['A'], 'requires_location_confirmation': True}],
        'institution_sources': [{'institution_id': 'A', 'source_id': 'S', 'role': 'announcements'}]}
    overrides = {'priorities': {}, 'disabled_sources': [], 'manual_events': [], 'corrections': {}, 'suppress': [], 'duplicates': {}, 'parser_rules': {}}
    feed, review = refresh(catalog, overrides, {'events': [], 'sources': []}, Preview())
    assert len(feed['events']) == 2
    assert all(e['geography_scope'] == 'moscow_region' for e in feed['events'])
    assert len(review) == 1
