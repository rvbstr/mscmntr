from pathlib import Path
from ingestion.adapters.gallery1112 import parse_1112,current_project

FIX=Path(__file__).parent/'fixtures'
URL='https://11-12gallery.com/exhibitions/nepolnoe-sobranie-sochinenij/'


def test_current_project_missing_year_is_labelled_and_its_first_day_is_an_opening():
    html=(FIX/'gallery1112-real.html').read_text()
    context={'current_project_url':URL,'observed_on':'2026-10-20'}
    exhibition,opening=parse_1112(html,URL,context)
    assert exhibition['title']=='Дамир Муратов. Неполное собрание сочинений'
    assert exhibition['start_date']=='2026-10-20' and exhibition['end_date']=='2026-12-05'
    assert opening['event_type']=='opening' and opening['start_date']=='2026-10-20'
    assert opening['start_time'] is None and opening['review_status']=='tentative'
    assert any('Год' in note for note in opening['uncertainties'])
    assert any('время вернисажа' in note for note in opening['uncertainties'])
    assert current_project(f'<a href="{URL}">текущий проект</a>','https://11-12gallery.com/')==URL


def test_archive_or_stale_current_project_does_not_gain_a_year_from_the_clock():
    html=(FIX/'gallery1112-real.html').read_text()
    assert parse_1112(html,URL)==[]
    assert parse_1112(html,URL,{'current_project_url':URL,'observed_on':'2026-04-01'})==[]
    assert parse_1112(html,URL,{'current_project_url':'https://11-12gallery.com/exhibitions/other/','observed_on':'2026-10-20'})==[]
