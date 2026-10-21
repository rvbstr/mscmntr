"""Optional JavaScript rendering for publicly accessible institution pages."""
import json
import os
from pathlib import Path
import subprocess
from ingestion.http import SourceError


def render_page(url,timeout=22):
    root=Path(__file__).resolve().parents[1]
    if os.environ.get('ENABLE_BROWSER_RENDERING','1')=='0':raise SourceError('Выполнение JavaScript отключено','manual',attempted=False)
    try:
        result=subprocess.run(['node',str(root/'scripts/render-source.mjs'),url,str(timeout*1000)],cwd=root,capture_output=True,text=True,timeout=timeout+10)
    except (OSError,subprocess.TimeoutExpired):raise SourceError('Браузерный сбор не завершён в отведённое время','partial')
    if result.returncode:
        if 'Executable doesn\'t exist' in result.stderr:raise SourceError('Для JavaScript-источника нужен Chromium: npx playwright install chromium','manual',attempted=False)
        if 'HTTP 403' in result.stderr or 'HTTP 401' in result.stderr:raise SourceError('Браузер получил ограничение доступа','blocked')
        raise SourceError('Не удалось прочитать публичную страницу через Chromium','partial')
    try:data=json.loads(result.stdout)
    except ValueError:raise SourceError('Браузер вернул неверный формат','review')
    return data['html'],data['url']
