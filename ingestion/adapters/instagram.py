"""Official Graph API and offline Instaloader exports. No anonymous profile scraping."""
import os
from pathlib import Path
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ingestion.http import SourceError
from ingestion.adapters.social import SocialPost,SocialCollection


class InstagramAPI:
    def __init__(self,token,account_id,version='v24.0',mode='business_discovery',account_username='',session=None):
        if not re.fullmatch(r'\d{1,25}',account_id):raise SourceError('Неверный INSTAGRAM_ACCOUNT_ID','review')
        if not re.fullmatch(r'v\d{1,2}\.\d',version):raise SourceError('Неверная версия Instagram API','review')
        if mode not in ('business_discovery','own_account'):raise SourceError('Неверный режим Instagram API','review')
        self.token=token;self.account_id=account_id;self.version=version;self.mode=mode;self.account_username=account_username
        self.session=session or requests.Session();self.last_request=0
        if session is None:self.session.mount('https://',HTTPAdapter(max_retries=Retry(total=1,backoff_factor=1,status_forcelist=[500,502,503,504],allowed_methods=['GET'])))

    def collect(self,username,limit=20):
        if not re.fullmatch(r'[A-Za-z0-9_.]{1,30}',username):raise SourceError('Неверное имя Инстаграм-профиля','review')
        if self.mode=='own_account':
            if username.casefold()!=self.account_username.casefold():raise SourceError('Токен собственной учётной записи не даёт доступ к этому профилю','manual')
            host='graph.instagram.com';path=f'{self.account_id}/media'
            params={'fields':'id,caption,permalink,timestamp','limit':min(limit,20)}
        else:
            host='graph.facebook.com';path=self.account_id
            fields=f'business_discovery.username({username}){{username,media.limit({min(limit,20)}){{id,caption,permalink,timestamp}}}}'
            params={'fields':fields}
        wait=1-(time.monotonic()-self.last_request)
        if wait>0:time.sleep(wait)
        self.last_request=time.monotonic()
        try:
            response=self.session.get(f'https://{host}/{self.version}/{path}',params=params,
                                      headers={'Authorization':'Bearer '+self.token},timeout=15)
        except requests.RequestException:raise SourceError('Не удалось соединиться с официальным Instagram API')
        if response.status_code>=500:raise SourceError('Официальный Instagram API временно недоступен')
        try:data=response.json()
        except ValueError:raise SourceError('Instagram API вернул неподдерживаемый ответ','review')
        if response.status_code==429 or data.get('error',{}).get('code') in (4,17,32,613):raise SourceError('Instagram API ограничил частоту запросов; повтор отложен','blocked')
        if response.status_code>=400 or 'error' in data:
            # Meta errors may contain account details; persist a redacted explanation only.
            raise SourceError('Instagram API отклонил доступ. Проверьте срок токена, тип аккаунта и разрешения приложения.','manual')
        if self.mode=='business_discovery':
            account=data.get('business_discovery') or {}
            if account.get('username','').casefold()!=username.casefold():raise SourceError('Профиль не подтверждён через Business Discovery','manual')
            rows=account.get('media',{}).get('data',[])
        else:rows=data.get('data',[])
        posts=[]
        for row in rows[:limit]:
            url=row.get('permalink','');p=urlsplit(url)
            if p.scheme!='https' or p.hostname not in ('www.instagram.com','instagram.com') or not re.match(r'^/(p|reel)/[A-Za-z0-9_-]+/?$',p.path):continue
            if row.get('caption') and row.get('timestamp'):
                posts.append(SocialPost(row['caption'],url,row['timestamp'],'instagram','instagram_official_api',username))
        return SocialCollection(posts,'instagram_official_api')


def instagram_username(url):
    p=urlsplit(url);parts=p.path.strip('/').split('/')
    if p.hostname not in ('instagram.com','www.instagram.com') or not parts or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}',parts[0]) or parts[0] in ('p','reel','stories'):
        raise SourceError('Для API нужен адрес профиля из каталога','review')
    return parts[0]


def collect_exports(root,username,limit=20):
    # This function never fetches Instagram: it parses locally supplied authorized exports.
    try:
        import instaloader
    except ImportError:raise SourceError('Для чтения экспортов установите requirements-social.txt','manual')
    directory=Path(root)/username
    if not directory.is_dir():raise SourceError('Для этого профиля нет локального разрешённого экспорта','manual')
    files=sorted([*directory.glob('*.json'),*directory.glob('*.json.xz')])[-100:]
    loader=instaloader.Instaloader(download_pictures=False,download_videos=False,download_video_thumbnails=False,download_geotags=False,download_comments=False,save_metadata=False,quiet=True,max_connection_attempts=1)
    # A serialized field missing from an export must not trigger hidden network access.
    def no_network(*args,**kwargs):raise SourceError('Экспорт неполный: сетевое дополнение данных отключено','review')
    loader.context.get_json=no_network;loader.context.graphql_query=no_network
    posts=[]
    for filename in files:
        try:
            post=instaloader.load_structure_from_file(loader.context,str(filename))
            if not isinstance(post,instaloader.Post):continue
            node=post._node
            owner=(node.get('owner') or {}).get('username')
            if not owner or owner.casefold()!=username.casefold():continue
            if not all(k in node for k in ('shortcode','taken_at_timestamp','edge_media_to_caption')):continue
            posts.append(SocialPost(post.caption or '',f'https://www.instagram.com/p/{post.shortcode}/',
                                    datetime.fromtimestamp(node['taken_at_timestamp'],timezone.utc).isoformat(),'instagram','instaloader_export',username))
        except SourceError:raise
        except (ValueError,KeyError,TypeError,instaloader.exceptions.InstaloaderException):continue
    return SocialCollection(posts[-limit:],'instaloader_export','Публикации прочитаны из локального экспорта; нужна редакционная проверка ссылок.',live=False)


def collect_instagram(url,api=None,export_root=None,limit=20):
    username=instagram_username(url)
    if api:return api.collect(username,limit)
    if export_root and (Path(export_root)/username).is_dir():return collect_exports(export_root,username,limit)
    raise SourceError('Нужен разрешённый Instagram API (токен и ID профессионального аккаунта) или локальный экспорт Instaloader. Анонимный сбор отключён правилами платформы.','manual',attempted=False)


def configured_instagram_api():
    token=os.environ.get('INSTAGRAM_ACCESS_TOKEN');account=os.environ.get('INSTAGRAM_ACCOUNT_ID')
    if not token or not account:return None
    return InstagramAPI(token,account,os.environ.get('INSTAGRAM_GRAPH_VERSION','v24.0'),
                        os.environ.get('INSTAGRAM_API_MODE','business_discovery'),os.environ.get('INSTAGRAM_ACCOUNT_USERNAME',''))
