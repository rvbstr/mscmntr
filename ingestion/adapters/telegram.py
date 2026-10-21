"""Public Telegram previews, with an optional authorized Telethon API transport."""
import asyncio
from html import unescape
from datetime import timezone
import os
import re
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
from ingestion.http import SourceError
from ingestion.adapters.social import SocialPost,SocialCollection


def telegram_identity(url):
    p=urlsplit(url)
    if p.hostname not in ('t.me','tg.me','telegram.me'):raise SourceError('Неверный адрес Телеграм-источника','review')
    parts=p.path.strip('/').split('/')
    if parts and parts[0]=='s':parts=parts[1:]
    if not parts or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{3,31}',parts[0]):raise SourceError('Нужен публичный адрес канала; приглашения не поддерживаются','manual')
    if len(parts)>2 or (len(parts)==2 and not parts[1].isdigit()):raise SourceError('Неподдерживаемый адрес Телеграм-публикации','review')
    return parts[0],int(parts[1]) if len(parts)==2 else None


def parse_preview(html,channel,post_id=None,limit=20):
    soup=BeautifulSoup(html,'html.parser');posts=[]
    for node in soup.select('.tgme_widget_message[data-post]'):
        identifier=node.get('data-post','')
        if not re.fullmatch(re.escape(channel)+r'/\d+',identifier,re.I):continue
        if post_id and identifier.split('/')[-1]!=str(post_id):continue
        # Forwarded posts require attribution review; never assign another venue's event silently.
        if node.select_one('.tgme_widget_message_forwarded_from'):continue
        body=node.select_one('.tgme_widget_message_text');time=node.select_one('time[datetime]')
        if body is None or time is None:continue
        if node.select_one('.tgme_widget_message_service_photo'):continue
        links=tuple(dict.fromkeys(unescape(urljoin('https://t.me/',a['href'])) for a in body.select('a[href]') if urlsplit(urljoin('https://t.me/',a['href'])).scheme in ('http','https')))
        posts.append(SocialPost(body.get_text('\n',strip=True),'https://t.me/'+identifier,time['datetime'],'telegram','telegram_public_preview',channel,links))
    return list({p.url:p for p in posts}.values())[-limit:]


def collect_preview(url,client,limit=20,pages=1):
    channel,post_id=telegram_identity(url)
    preview=f'https://t.me/s/{channel}'+(f'/{post_id}' if post_id else '')
    posts=[];before=None;note=None
    for _ in range(1 if post_id else max(1,min(pages,5))):
        try:html,final=client.fetch(preview+(f'?before={before}' if before else ''))
        except SourceError as exc:
            if not posts:raise
            note='Прочитана часть ленты; следующая страница: '+str(exc)
            break
        posts+=parse_preview(html,channel,post_id,limit)
        posts=list({p.url:p for p in posts}.values())
        ids=[int(n['data-post'].split('/')[-1]) for n in BeautifulSoup(html,'html.parser').select('.tgme_widget_message[data-post]') if re.fullmatch(re.escape(channel)+r'/\d+',n['data-post'],re.I)]
        cursor=min(ids) if ids else None
        if not cursor or cursor==before or len(posts)>=limit:break
        before=cursor
    if not posts:raise SourceError('Публичная лента недоступна или не содержит читаемых публикаций. Возможен сбор через авторизованный API.','partial')
    posts.sort(key=lambda p:int(p.url.rsplit('/',1)[-1]),reverse=True)
    return SocialCollection(posts[:limit],'telegram_public_preview',note=note)


async def _api_posts(channel,post_id,limit):
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.errors import FloodWaitError,ChannelPrivateError,UnauthorizedError
    except ImportError:raise SourceError('Для API установите requirements-social.txt','manual')
    api_id=os.environ.get('TELEGRAM_API_ID');api_hash=os.environ.get('TELEGRAM_API_HASH');session=os.environ.get('TELEGRAM_SESSION')
    if not all((api_id,api_hash,session)):raise SourceError('Для Telethon нужны TELEGRAM_API_ID, TELEGRAM_API_HASH и авторизованная TELEGRAM_SESSION','manual',attempted=False)
    if not api_id.isdigit():raise SourceError('Неверный формат TELEGRAM_API_ID','review')
    try:authorized_session=StringSession(session)
    except ValueError:raise SourceError('Неверный формат авторизованной TELEGRAM_SESSION','manual',attempted=False)
    client=TelegramClient(authorized_session,int(api_id),api_hash,request_retries=0,connection_retries=1,
                          auto_reconnect=False,timeout=12,flood_sleep_threshold=0,receive_updates=False)
    try:
        await client.connect()
        if not await client.is_user_authorized():raise SourceError('Сессия Телеграма не авторизована. Интерактивный вход в сборщике отключён.','manual')
        entity=await client.get_entity(channel)
        # Resolve only publicly named channels, not private invitations or contact histories.
        if not getattr(entity,'username',None) or entity.username.casefold()!=channel.casefold():raise SourceError('Публичное имя канала не подтверждено','review')
        messages=await client.get_messages(entity,ids=[post_id]) if post_id else [m async for m in client.iter_messages(entity,limit=limit)]
        from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
        posts=[]
        for m in messages:
            if not m or not m.message or m.fwd_from: continue
            links=[]
            for entity in m.entities or []:
                if isinstance(entity,MessageEntityTextUrl): links.append(entity.url)
                elif isinstance(entity,MessageEntityUrl):
                    links.append(m.message.encode('utf-16-le')[entity.offset*2:(entity.offset+entity.length)*2].decode('utf-16-le'))
            posts.append(SocialPost(m.message,f'https://t.me/{channel}/{m.id}',m.date.astimezone(timezone.utc).isoformat(),
                'telegram','telegram_authorized_api',channel,tuple(u for u in links if urlsplit(u).scheme in ('http','https'))))
        return posts
    except FloodWaitError:raise SourceError('Телеграм ограничил частоту запросов; сбор остановлен до следующего запуска','blocked')
    except (ChannelPrivateError,UnauthorizedError):raise SourceError('Для канала или сессии недостаточно разрешённого доступа','manual')
    finally:await client.disconnect()


def collect_telegram(url,client,limit=20,pages=1):
    if os.environ.get('TELEGRAM_MODE','preview')!='api':return collect_preview(url,client,limit,pages)
    channel,post_id=telegram_identity(url)
    try:posts=asyncio.run(asyncio.wait_for(_api_posts(channel,post_id,limit),timeout=45))
    except SourceError:raise
    except Exception as exc:raise SourceError('Не удалось прочитать Телеграм API: '+type(exc).__name__)
    return SocialCollection(posts,'telegram_authorized_api')
