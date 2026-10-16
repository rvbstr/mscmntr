"""Scoped public-post parsing shared by Telegram and authorized Instagram sources."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo
from ingestion.dates import extract_dates
from ingestion.models import event_type


@dataclass(frozen=True)
class SocialPost:
    text: str
    url: str
    published_at: str
    platform: str
    verification: str
    owner: str


@dataclass
class SocialCollection:
    posts: list[SocialPost]
    adapter: str
    note: str | None = None
    # Offline exports supply review evidence, not a live availability check.
    live: bool = True


DATE_MARKER = re.compile(r'(?<!\d)\d{1,2}(?:[./](?:1[0-2]|0?[1-9])(?:[./]20\d{2})?|\s+(?:янв|фев|мар|апр|ма[йя]|ию[нл]|авг|сен|окт|ноя|дек))',re.I)
EVENT_WORD = re.compile(r'выставк|вернисаж|открыти[ея]|перформанс|лекци|дискусси|медиаци|кинопоказ|показ\s+фильма|экскурси|медиаторск|мастер.класс|фестивал|ярмарк|воркшоп',re.I)
TIME_MARKER = re.compile(r'(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)')
GENERIC_HEADING = re.compile(r'^(?:персональная|групповая|коллективная|новая|открытие|экспозиция)?\s*(?:выставка|выставки|вернисаж|перформанс|лекция|дискуссия|кинопоказ|фестиваль|медиация по выставке)\s*[:.!—–-]?$',re.I)


def _heading(lines, first_date):
    header=lines[:first_date+1]
    for n,line in enumerate(header):
        quoted=re.search(r'[«“"]([^»”"\n]{2,150})[»”"]',line)
        if quoted and EVENT_WORD.search(line[:quoted.start()]): return quoted.group(0)
        if GENERIC_HEADING.fullmatch(line) and n+1<len(header):
            following=header[n+1]
            if len(following)<=160 and not EVENT_WORD.fullmatch(following):return following
    return None


def parse_post(post: SocialPost):
    """Return candidates plus an optional editorial-review reason; never guess a headline."""
    lines=[re.sub(r'\s+',' ',line).strip() for line in post.text.splitlines() if line.strip()]
    if not EVENT_WORD.search(' '.join(lines[:10])):return [],None
    date_indices=[n for n,line in enumerate(lines[:14]) if DATE_MARKER.search(line) and not re.search(r'адрес|улица|проспект|переулок|^Москва[, ]|^Балашиха[, ]',line,re.I)]
    if not date_indices:return [],None
    # Closing-only notices and artist biographies do not establish a start date.
    if any(re.search(r'участни[кц].*выставки',line,re.I) for line in lines[:4]):return [],None
    if re.search(r'(?:принял[аи]? участие|участвует|участвуют)\s+в\s+выставк',' '.join(lines[:4]),re.I):
        return [],'Анонс участия художника: нужно уточнить название и площадку события'
    scope_indices=sorted(set(date_indices+[n for n,line in enumerate(lines[:16]) if TIME_MARKER.search(line) and any(abs(n-d)<=2 for d in date_indices)]))
    scoped=' '.join(lines[n] for n in scope_indices)
    explicit_year=bool(re.search(r'20\d{2}',scoped))
    try: published=datetime.fromisoformat(post.published_at.replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Moscow'))
    except (ValueError,TypeError):return [],'Нужна дата публикации для проверки контекста дат'
    options=[None] if explicit_year else [published.year,published.year+1,published.year-1]
    dates=None
    for year in options:
        candidate=extract_dates(scoped,year)
        if not candidate['start_date']:continue
        day=datetime.fromisoformat(candidate['start_date']).date()
        if explicit_year or published.date()-timedelta(days=14)<=day<=published.date()+timedelta(days=180):
            dates=candidate;break
    if not dates:return [],'Дата начала не определена однозначно'
    # Multiple unrelated dated items belong in review, not a single invented range.
    primary_lines=[lines[n] for n in date_indices if not re.search(r'вернисаж|открыти[ея]',lines[n],re.I)]
    unique=set()
    for line in primary_lines:
        parsed=extract_dates(line,int(dates['start_date'][:4]))
        if parsed['start_date']:unique.add((parsed['start_date'],parsed['end_date']))
        if not parsed['end_date']:
            for match in DATE_MARKER.finditer(line):
                individual=extract_dates(match.group(),int(dates['start_date'][:4]))
                if individual['start_date']:unique.add((individual['start_date'],None))
    if len(unique)>1:return [],'В публикации несколько дат; нужна разбивка на события'
    title=_heading(lines,date_indices[0])
    if not title:return [],'Не удалось выделить название события из текста публикации'
    if not dates['start_time']:
        time=TIME_MARKER.search(scoped)
        if time:dates['start_time']=time.group()
    for n in date_indices:
        if re.search(r'вернисаж|открыти[ея]',lines[n],re.I):
            opening=extract_dates(lines[n],int(dates['start_date'][:4]));clock=TIME_MARKER.search(lines[n])
            if opening['start_date']:dates['opening_date']=opening['start_date'];dates['opening_time']=clock.group() if clock else opening['start_time']
    header=' '.join(lines[:date_indices[0]+1])
    kind='exhibition' if dates['end_date'] and re.search(r'выставк',header,re.I) else event_type(header)
    if kind=='other':return [],'Нужно уточнить тип события'
    address=next((re.sub(r'^Адрес\s*:\s*','',line,flags=re.I) for line in lines if re.search(r'^(?:Адрес\s*:|(?:📍\s*)?(?:Россия,\s*)?(?:Москва|Балашиха)[,\s])|(?:^|\s)ул\.\s|улица|проспект|переулок',line,re.I) and re.search(r'\d',line)),None)
    if address:address=address.removeprefix('📍').strip()
    geography=None;city=None
    if address:
        if re.search(r'\bМосква\b',address,re.I):geography='moscow';city='Москва'
        elif re.search(r'\bБалашиха\b',address,re.I):geography='moscow_region';city='Балашиха'
        else:
            city_match=re.search(r',\s*([А-ЯЁ][а-яё]+(?:-[А-ЯЁ]?[а-яё]+| [А-ЯЁ][а-яё]+)?)$',address) or re.match(r'^([А-ЯЁ][а-яё]+(?:-[А-ЯЁ]?[а-яё]+| [А-ЯЁ][а-яё]+)?),',address)
            if city_match and city_match[1] not in ('Россия','Улица','Проспект'):
                return [],'Событие за пределами Москвы и Подмосковья: '+city_match[1]
    excerpt=[]
    for line in lines[max(date_indices)+1:]:
        if address and address in line:break
        if len(line)>45 and not line.startswith(('@','http')):excerpt.append(line)
        if len(' '.join(excerpt))>=350:break
    base=dict(title=title,primary_url=post.url,published_at=post.published_at,
              description=' '.join(excerpt)[:500],confidence='social_scoped',
              date_basis='explicit_year' if explicit_year else 'publication_context',
              verification_method=post.verification,address=address,geography_scope=geography,city=city)
    result=[dict(base,event_type=kind,start_date=dates['start_date'],end_date=dates['end_date'],
                 start_time=None if kind=='exhibition' else dates['start_time'])]
    if dates['opening_date'] and kind=='exhibition':
        result.append(dict(base,event_type='opening',start_date=dates['opening_date'],start_time=dates['opening_time'],end_date=None))
    return result,None
