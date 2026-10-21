"""Follow bounded announcement/registration links explicitly shared in a post."""
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from ingestion.adapters.social import EVENT_WORD, foreign_event_location
from ingestion.extraction import extract
from ingestion.http import SourceError
from ingestion.models import canonical_url, direct_url, normalized_title, valid_event
from ingestion.primary import is_aggregator

SOCIAL_HOSTS={'t.me','tg.me','telegram.me','instagram.com','www.instagram.com','vk.com','vk.ru','youtube.com','www.youtube.com','youtu.be'}
GENERIC={'выставка','открытие','лекция','регистрация','билеты','событие','проект','вечер','приглашаем','концерт','презентация'}
BOOKING_HOSTS={'timepad.ru','qtickets.ru','nethouse.events','eventbrite.com','ticketscloud.com'}


def booking(url):
    host=urlsplit(url).hostname or ''
    return any(host==h or host.endswith('.'+h) for h in BOOKING_HOSTS)


def followable(url):
    try:
        host=(urlsplit(url).hostname or '').lower()
        path=urlsplit(url).path
        return direct_url(url) and host not in SOCIAL_HOSTS and not is_aggregator(url) and not re.search(r'/(?:artists?|people|xudozhniki|account|portfolio|products?|maps)(?:/|$)|\.(?:pdf|jpe?g|png|gif|mp4|zip|docx?)$',path,re.I)
    except ValueError:return False


def same_subject(event,post,baseline):
    def stem(word):return word[:5] if len(word)>5 else word
    generic={stem(w) for w in GENERIC}
    def words(text):return {stem(w) for w in normalized_title(text).split() if len(w)>3 and stem(w) not in generic}
    if len(words(event['title']) & words(post.text))<2 and not any(
            normalized_title(e['title'])==normalized_title(event['title']) and len(normalized_title(event['title']))>=5 for e in baseline):return False
    # A shared link alone is insufficient: a digest can mention many projects.
    if baseline and not any(e['start_date']==event['start_date'] for e in baseline):return False
    return True


class LinkedResolver:
    def __init__(self,client,max_pages=12):
        self.client=client;self.remaining=max_pages;self.cache={}

    def fetch(self,url):
        url=canonical_url(url)
        if url in self.cache:return self.cache[url]
        if self.remaining<=0:raise SourceError('Достигнут лимит связанных страниц для канала','partial',attempted=False)
        self.remaining-=1
        try:
            body,final=self.client.fetch(url)
            if not followable(final):raise SourceError('Ссылка перенаправляет на общую страницу или неподходящий источник','review')
            result=(body,canonical_url(final),datetime.now(timezone.utc).isoformat(timespec='seconds'))
            self.cache[url]=result;return result
        except SourceError as exc:
            self.cache[url]=exc;raise

    def resolve(self,post,parsed,reason):
        if not post.related_urls or not EVENT_WORD.search(post.text) or foreign_event_location(post.text):return parsed,reason,[],[]
        from ingestion.provisional import tentative_post
        raw={'primary_url':post.url,'description':post.text,'published_at':post.published_at,'related_urls':list(post.related_urls)}
        baseline=parsed or tentative_post(raw)
        if not baseline:return parsed,reason,[],[]
        queue=sorted(dict.fromkeys(canonical_url(u) for u in post.related_urls if followable(u)),key=booking)[:2]
        registrations={canonical_url(u) for u in post.related_urls if followable(u) and (booking(u) or re.search(r'/(?:forms?|register|registration)(?:/|$)',urlsplit(u).path,re.I))}
        pages=[];issues=[];resolved=[];seen=set();registration=next(iter(registrations)) if len(registrations)==1 else None
        while queue and len(seen)<3:
            target=queue.pop(0)
            if target in seen:continue
            seen.add(target)
            try:
                fetched=self.fetch(target)
                if isinstance(fetched,SourceError):raise fetched
                html,final,checked=fetched
                candidates,adapter=extract(html,final,{'reference_year':int(baseline[0]['start_date'][:4])})
                matches=[e for e in candidates if valid_event(e) and e.get('confidence')!='inferred_opening' and same_subject(e,post,baseline)]
                pages.append({'url':final,'origin_post_url':post.url,'adapter':adapter,'matched_events':len(matches),'checked_at':checked})
                if not matches:
                    issues.append({'url':final,'reason':'Связанная страница не подтверждает название и дату этого события'})
                    continue
                # Ambiguous schedules need their own session attribution.
                if len(matches)>1:continue
                event=matches[0]
                old=next((e for e in baseline if e['event_type']==event['event_type'] and e['start_date']==event['start_date']),{})
                item={**old,**event,'origin_post_url':post.url,'linked_verified_at':checked,'verification_method':'linked_public_page',
                    'published_at':post.published_at,'related_urls':list(dict.fromkeys([canonical_url(u) for u in post.related_urls]+[post.url])),
                    'evidence':[{'url':post.url,'status':'available','checked_at':checked,'verification_method':post.verification,
                        'title':post.text.splitlines()[0][:250],'start_date':event['start_date']}]}
                for key in ('title_is_tentative','uncertainties','review_status','event_id','merged_event_ids'):item.pop(key,None)
                if event.get('review_status'):item['review_status']=event['review_status'];item['uncertainties']=event.get('uncertainties',[])
                resolved.append(item)
                soup=BeautifulSoup(html,'html.parser')
                root=soup.select_one('article,main,[role="main"],.page-body') or soup.body
                for a in root.select('a[href]') if root else []:
                    href=canonical_url(urljoin(final,a['href']))
                    if followable(href) and re.search(r'регистрац|зарегистр|купить билет|register|tickets',a.get_text(' ',strip=True),re.I):
                        registration=href
                        if href not in seen and href not in queue:queue.append(href)
                        break
            except SourceError as exc:issues.append({'url':target,'status':exc.status,'reason':str(exc)})
            except (ValueError,TypeError,KeyError):issues.append({'url':target,'status':'review','reason':'Не удалось разобрать связанную страницу'})
        if not resolved:return parsed,reason,issues,pages
        # Prefer an institution announcement to a booking service, retaining the
        # latter as a registration link rather than a second calendar event.
        best=next((e for e in resolved if not booking(e['primary_url'])),resolved[0])
        if registration and registration!=best['primary_url']:best['registration_url']=registration
        for item in resolved:
            if item is best:continue
            if item['start_date']==best['start_date'] and item['event_type']==best['event_type']:
                best['evidence'].append({'url':item['primary_url'],'status':'available','checked_at':item['linked_verified_at'],
                    'title':item['title'],'start_date':item['start_date'],'verification_method':'linked_public_page'})
        kept=[e for e in parsed if len(parsed)>1 and e['event_type']!=best['event_type']]
        return [best]+kept,None,issues,pages
