from pathlib import Path
from ingestion.adapters.institutions import parse_institution, institution_links
from ingestion.adapters.programmes import card_dates, card_event
from ingestion.models import event_type

FIX = Path(__file__).parent / 'fixtures'


def embedded(name):
    return '<script id="__NEXT_DATA__" type="application/json">' + (FIX / name).read_text() + '</script>'


def test_ruarts_lectures_have_explicit_dates_times_and_direct_links():
    events = parse_institution((FIX / 'ruarts-programme-real.html').read_text(), 'https://ruarts.foundation/ru/')
    talk = next(e for e in events if e['primary_url'].endswith('/lecture/119'))
    assert talk['title'] == '«Между идеей и отпечатком»'
    assert (talk['event_type'], talk['start_date'], talk['start_time']) == ('talk', '2026-10-24', '16:00')
    assert any(e['start_date'] == '2026-10-31' and e['event_type'] == 'talk' for e in events)
    assert not any(e['title'].endswith(('...', '…')) for e in events)
    assert next(e for e in events if e['primary_url'].endswith('/masterclass/106'))['event_type'] == 'workshop'


def test_zotov_classifies_dialogues_without_relying_on_the_title():
    events = parse_institution((FIX / 'zotov-programme-real.html').read_text(), 'https://centrezotov.ru/events/')
    talk = next(e for e in events if e['title'] == 'Синди Шерман. Искусство перевоплощения')
    assert (talk['event_type'], talk['start_date'], talk['start_time']) == ('talk', '2026-10-22', '20:00')
    dialogue = next(e for e in events if e['title'] == 'Паблик-ток «Вкус как наследие»')
    assert (dialogue['event_type'], dialogue['start_date'], dialogue['start_time']) == ('talk', '2026-10-18', '15:00')
    assert not any(e['end_date'] for e in events)


def test_garage_uses_session_times_in_moscow_not_recurrence_bounds():
    events = parse_institution(embedded('garage-programme-real.json'), 'https://garagemca.org/')
    talks = [e for e in events if 'реставратором' in e['title']]
    assert len(talks) == 1
    assert (talks[0]['event_type'], talks[0]['start_date'], talks[0]['start_time']) == ('talk', '2026-10-17', '12:00')
    assert any(e['event_type'] == 'talk' and e['start_date'] == '2026-10-22' for e in events)
    assert not any('&nbsp;' in e['title'] for e in events)
    assert not any('сокращенная экскурсия' in e['title'] for e in events)
    assert all(e['end_date'] is None for e in events)


def test_ges2_recognizes_beseda_and_respects_session_subtype_override():
    html = embedded('ges2-programme-real.json')
    events = parse_institution(html, 'https://ges-2.org/calendar')
    assert not any('<em>' in e['title'] for e in events)
    assert any(e['title'] == 'Натюрморт. Портрет. Пейзаж. Техники исполнения' and e['event_type'] == 'talk' for e in events)
    assert any('День белой трости' in e['title'] and e['event_type'] == 'workshop' for e in events)
    links = institution_links(html, 'https://ges-2.org/calendar', 3)
    assert links == ['https://ges-2.org/calendar?date=2026-10-18', 'https://ges-2.org/calendar?date=2026-10-19', 'https://ges-2.org/calendar?date=2026-10-22']
    assert not institution_links(html, 'https://ges-2.org/calendar', 0)


def test_programme_hubs_are_discovered_before_individual_pages():
    assert institution_links('', 'https://ruarts.foundation/ru/', 1) == ['https://ruarts.foundation/ru/events']
    assert institution_links('', 'https://centrezotov.ru/', 1) == ['https://centrezotov.ru/events/']
    assert institution_links('', 'https://garagemca.org/', 1) == ['https://garagemca.org/calendar']


def test_explicit_short_years_do_not_create_ambiguous_lecture_ranges():
    assert card_dates('22.10.26 / 20:00')['start_date'] == '2026-10-22'
    assert card_dates('22.10 / 20:00')['start_date'] is None
    assert not card_event('Курс лекций', '22.10.26 — 22.11.26', 'https://example.org/course', 'talk')
    assert all(event_type(text) == 'talk' for text in ['Беседа', 'Диалог', 'Паблик-ток', 'Круглый стол'])
