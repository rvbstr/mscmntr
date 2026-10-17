"""Discover public Telegram links; candidates require editorial attribution before import."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urljoin, urlsplit
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ingestion.http import Client, SourceError
from ingestion.import_catalog import ROOT
from ingestion.adapters.telegram import parse_preview

RESERVED = {'share', 'joinchat', 'iv', 'addstickers', 'addemoji', 'addtheme', 'proxy', 'socks', 'login', 'c', 's'}


def channel_url(value):
    value = unescape(value).replace('\\/', '/').strip()
    if value.startswith('tg://resolve?'):
        username = parse_qs(urlsplit(value).query).get('domain', [''])[0]
    else:
        if value.startswith('//'):
            value = 'https:' + value
        p = urlsplit(value)
        if p.scheme not in ('https', 'http') or p.hostname not in ('t.me', 'tg.me', 'telegram.me', 'www.t.me'):
            return None
        parts = p.path.strip('/').split('/')
        if parts[0] == 's':
            parts = parts[1:]
        username = parts[0] if parts else ''
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{3,31}', username) or username.lower() in RESERVED:
        return None
    if username.lower().endswith('bot'):
        return None
    return 'https://t.me/' + username.lower()


def extract_links(html, page_url):
    soup = BeautifulSoup(html, 'html.parser')
    result = {}
    for a in soup.select('a[href]'):
        target = channel_url(a['href'])
        if target:
            result[target] = {'url': target, 'page_url': page_url,
                              'anchor': a.get_text(' ', strip=True)[:150],
                              'context': a.parent.get_text(' ', strip=True)[:400]}
    # JSON/JS-rendered social navigation often escapes slashes in its embedded state.
    scripts = '\n'.join(script.get_text() for script in soup.select('script'))
    for raw in re.findall(r'https?://(?:t\.me|tg\.me|telegram\.me)/[A-Za-z][A-Za-z0-9_]{3,31}(?![A-Za-z0-9_.-])(?:/\d+)?', unescape(scripts).replace('\\/', '/')):
        target = channel_url(raw)
        if target and target not in result:
            result[target] = {'url': target, 'page_url': page_url, 'anchor': '', 'context': 'Встроенная ссылка страницы'}
    return list(result.values())


def scan_host(sources, cache_dir, max_pages=4, timeout=8, refresh=False):
    client = Client(timeout=timeout)
    client.session.mount('https://', HTTPAdapter(max_retries=Retry(total=1, backoff_factor=1, status_forcelist=[500, 502, 503, 504], allowed_methods=['GET'])))
    urls = list(dict.fromkeys(s['url'] for s in sources))
    p = urlsplit(urls[0])
    root = f'{p.scheme}://{p.netloc}/'
    queue = list(dict.fromkeys([root] + urls))
    pages, links = [], []
    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if any(x['url'] == url for x in pages):
            continue
        cache = cache_dir / (sha256(url.encode()).hexdigest() + '.json')
        if cache.exists() and not refresh:
            record = json.loads(cache.read_text())
        else:
            try:
                html, final = client.fetch(url)
                record = {'url': url, 'final_url': final, 'html': html, 'checked_at': datetime.now(timezone.utc).isoformat()}
            except SourceError as exc:
                record = {'url': url, 'error': str(exc), 'status': exc.status, 'checked_at': datetime.now(timezone.utc).isoformat()}
            cache.write_text(json.dumps(record, ensure_ascii=False))
        if 'html' not in record:
            pages.append(record)
            continue
        html = record['html']; final = record['final_url']
        found = extract_links(html, final)
        links.extend(dict(x, checked_at=record['checked_at']) for x in found)
        pages.append({k: v for k, v in record.items() if k != 'html'})
        soup = BeautifulSoup(html, 'html.parser')
        contacts = []
        for a in soup.select('a[href]'):
            target = urljoin(final, a['href']); path = urlsplit(target)
            if path.hostname != urlsplit(final).hostname or path.fragment:
                continue
            if re.search(r'контакт|о нас|о галерее|contact|about', a.get_text(' ', strip=True) + ' ' + path.path, re.I):
                contacts.append(target)
        queue = list(dict.fromkeys(contacts + queue))
        # A root social link normally suffices; also inspect one dedicated source page
        # if the catalog points to a resident or a specific institution's subpage.
        if found and url == root and not any('/residents/' in x or '/galleries/' in x or '/institutions/' in x for x in urls):
            break
    return {'host': p.hostname, 'source_ids': [s['source_id'] for s in sources],
            'institution_ids': sorted({i for s in sources for i in s['institution_ids']}),
            'pages': pages, 'candidates': list({(x['url'], x['page_url']): x for x in links}.values())}


def verify_channels(channels, output, cache_dir, timeout=8, refresh=False):
    """Check public previews once per channel; cached evidence retains its real timestamp."""
    rows = json.loads(output.read_text()) if output.exists() else {}
    cache_dir.mkdir(parents=True, exist_ok=True)
    client = Client(timeout=timeout)
    client.session.mount('https://', HTTPAdapter(max_retries=Retry(total=1, status_forcelist=[500, 502, 503, 504], allowed_methods=['GET'])))
    for url in sorted(set(channels)):
        if url in rows and not refresh:
            continue
        username = url.rsplit('/', 1)[1]
        row = {'url': url, 'checked_at': datetime.now(timezone.utc).isoformat()}
        try:
            html, final = client.fetch('https://t.me/s/' + username)
            (cache_dir / (username + '.html')).write_text(html)
            soup = BeautifulSoup(html, 'html.parser'); posts = parse_preview(html, username, limit=20)
            title = soup.select_one('.tgme_channel_info_header_title,.tgme_page_title')
            description = soup.select_one('.tgme_channel_info_description,.tgme_page_description')
            row.update(title=title.get_text(' ', strip=True) if title else '',
                       description=description.get_text(' ', strip=True) if description else '',
                       posts_seen=len(posts), latest_post_at=max([p.published_at for p in posts], default=None),
                       sample=[{'url': p.url, 'text': p.text[:450]} for p in posts[-2:]],
                       status='readable' if posts else 'no_readable_posts')
        except SourceError as exc:
            row.update(status=exc.status, error=str(exc))
        rows[url] = row
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
        print(username, row['status'], row.get('posts_seen'), row.get('title', ''), flush=True)
    return rows


def main():
    parser = argparse.ArgumentParser(description='Поиск Telegram-ссылок на сайтах каталога без автоматической атрибуции')
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--max-pages', type=int, default=4)
    parser.add_argument('--timeout', type=int, default=8)
    parser.add_argument('--output', type=Path, default=ROOT / '.local/discovery/telegram-candidates.json')
    parser.add_argument('--verify-only', action='store_true', help='Проверить Telegram-кандидаты из готового отчёта, не обходя сайты')
    parser.add_argument('--refresh', action='store_true', help='Выполнить свежие запросы вместо повторного использования локальных снимков')
    args = parser.parse_args()
    cache = ROOT / '.local/discovery/pages'; cache.mkdir(parents=True, exist_ok=True)
    if args.verify_only:
        found = json.loads(args.output.read_text())
        urls = {x['url'] for h in found['hosts'] for x in h['candidates']}
        urls.update(x['url'] for x in found.get('manual_candidates', []))
        verify_channels(urls, ROOT / '.local/discovery/telegram-verification.json', ROOT / '.local/discovery/telegram', args.timeout, args.refresh)
        return
    catalog = json.loads((ROOT / 'catalog/catalog.json').read_text())
    groups = {}
    for source in catalog['sources']:
        if source['platform'] == 'website':
            groups.setdefault(urlsplit(source['url']).hostname, []).append(source)
    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 10))) as pool:
        tasks = {pool.submit(scan_host, rows, cache, args.max_pages, args.timeout, args.refresh): host for host, rows in groups.items()}
        for task in as_completed(tasks):
            result = task.result(); results.append(result)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps({'checked_at': datetime.now(timezone.utc).isoformat(), 'hosts': sorted(results, key=lambda x: x['host'])}, ensure_ascii=False, indent=2) + '\n')
            print(f"{result['host']}: страниц {len(result['pages'])}, ссылок {len(result['candidates'])}", flush=True)
    print(f'Проверено доменов: {len(results)}. Кандидаты: {args.output}')


if __name__ == '__main__':
    main()
