import ipaddress
import socket
import time
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT='MoscowArtMonitor/1.0 (+https://github.com/rvbstr/mscmntr; public art announcements)'


class SourceError(Exception):
    def __init__(self,message,status='unavailable'):
        super().__init__(message); self.status=status


class Client:
    def __init__(self,delay=1,timeout=12):
        self.session=requests.Session(); self.session.headers['User-Agent']=USER_AGENT
        retry=Retry(total=2,backoff_factor=1,status_forcelist=[429,500,502,503,504],allowed_methods=['GET'],respect_retry_after_header=True)
        self.session.mount('https://',HTTPAdapter(max_retries=retry))
        self.delay=delay; self.delays={}; self.timeout=timeout; self.last={}; self.robots={}; self.cache={}

    def _safe(self,url):
        p=urlsplit(url)
        if p.scheme not in ('https','http') or not p.hostname or p.username or p.password or p.port not in (None,80,443):
            raise SourceError('Неподдерживаемый или небезопасный URL','review')
        try:
            for result in socket.getaddrinfo(p.hostname,None):
                if not ipaddress.ip_address(result[4][0]).is_global: raise SourceError('Непубличный адрес источника','review')
        except socket.gaierror:
            # Proxy-side DNS may resolve domains unavailable to local DNS.
            pass

    def _get(self,url,redirects=0):
        self._safe(url); host=urlsplit(url).netloc
        remaining=self.delays.get(host,self.delay)-(time.monotonic()-self.last.get(host,0))
        if remaining>0: time.sleep(remaining)
        self.last[host]=time.monotonic()
        try:
            with self.session.get(url,timeout=self.timeout,stream=True,allow_redirects=False) as response:
                if response.is_redirect:
                    if redirects>=5: raise SourceError('Слишком много перенаправлений')
                    return self._get(urljoin(url,response.headers['Location']),redirects+1)
                if response.status_code in (401,403,429): raise SourceError(f'Доступ ограничен (HTTP {response.status_code})','blocked')
                if response.status_code in (404,410): raise SourceError(f'Страница не найдена (HTTP {response.status_code})','broken')
                if response.status_code>=400: raise SourceError(f'Ошибка HTTP {response.status_code}')
                content_type=response.headers.get('Content-Type','').lower()
                if content_type and not any(t in content_type for t in ('text/','xml','json','html')):
                    raise SourceError('Источник вернул неподдерживаемый тип содержимого','review')
                data=bytearray()
                for chunk in response.iter_content(32768):
                    data.extend(chunk)
                    if len(data)>2_000_000: raise SourceError('Страница превышает ограничение 2 МБ','review')
                response._content=bytes(data)
                encoding=response.encoding if response.encoding and response.encoding.lower()!='iso-8859-1' else 'utf-8'
                return bytes(data).decode(encoding,errors='replace'),response.url
        except requests.exceptions.ProxyError:
            raise SourceError('Прокси среды ограничил доступ к домену; проверка страницы не выполнена','blocked')
        except requests.RequestException as exc:
            # Never persist proxy URLs, credentials or raw exception representations.
            raise SourceError('Ошибка соединения: '+type(exc).__name__)

    def fetch(self,url):
        if url in self.cache: return self.cache[url]
        p=urlsplit(url); origin=f'{p.scheme}://{p.netloc}'
        if origin not in self.robots:
            robot=RobotFileParser(); robot.set_url(origin+'/robots.txt')
            try:
                body,_=self._get(origin+'/robots.txt'); robot.parse(body.splitlines())
            except SourceError as exc:
                if exc.status=='broken': robot.parse([])
                else:
                    self.robots[origin]=exc; raise
            self.robots[origin]=robot
        robot=self.robots[origin]
        if isinstance(robot,SourceError): raise robot
        if not robot.can_fetch(USER_AGENT,url): raise SourceError('Сбор запрещён robots.txt','blocked')
        crawl=robot.crawl_delay(USER_AGENT) or robot.crawl_delay('*')
        if crawl:
            if float(crawl)>60: raise SourceError('robots.txt требует длинного интервала; нужна отдельная очередь','review')
            self.delays[p.netloc]=max(self.delay,float(crawl))
        result=self._get(url)
        # Check redirect destination policy before accepting its contents.
        if urlsplit(result[1]).netloc != p.netloc and result[1] != url:
            return self.fetch(result[1])
        self.cache[url]=result; return result
