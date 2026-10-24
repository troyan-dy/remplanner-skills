"""Скачивание скрипта инструментов планировщика с remplanner.ru и сборка каталога."""

import os
import re
import sys
import tempfile
from http.cookiejar import CookieJar
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

from rpkit.catalog_build import build
from rpkit.console import say
from rpkit.paths import CAT_DIR

SITE = "https://remplanner.ru"
SCRIPTS = f"{SITE}/files/js/v2/app"
TOOLS_RE = re.compile(r"planner\.tools___[0-9_]+\.js")
USER_AGENT = "Mozilla/5.0 (rp_catalog.py)"
TIMEOUT_S = 120
UTF8 = "utf-8"


def _get(opener, url, form=None):
    req = Request(url, data=form, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=TIMEOUT_S) as response:
        return response.read()


def _tools_name(html):
    """Имя planner.tools___<ver>.js в странице или None."""
    found = TOOLS_RE.search(html)
    return found.group(0) if found else None


def find_tools_url(opener):
    """Имя planner.tools___<ver>.js есть только в странице редактора. Публичная /planner/ без сессии —
    заставка «Нарисовать чертежи»; её кнопка отправляет форму POST /planner/create/ (create_trigger=1, значение
    ставит front.js), после чего /planner/ отдаёт редактор со списком скриптов. Это создаёт гостевой проект —
    то же, что нажать кнопку в браузере."""
    name = _tools_name(_get(opener, f"{SITE}/planner/").decode(UTF8, "replace"))
    if not name:
        form = urlencode({"create_trigger": "1"}).encode()
        name = _tools_name(_get(opener, f"{SITE}/planner/create/", form).decode(UTF8, "replace"))
    if not name:
        sys.exit(
            "не нашёл planner.tools___<ver>.js на странице редактора. Откройте https://remplanner.ru/planner/ в "
            "браузере, найдите имя в performance.getEntriesByType('resource') и запустите "
            "python3 tools/rp_catalog.py fetch <имя или url>",
        )
    return f"{SCRIPTS}/{name}"


def fetch(arg=None):
    """Скачать скрипт инструментов планировщика (по умолчанию — актуальную версию с сайта) и собрать каталог.
    arg — путь к уже скачанному .js, полный url или имя planner.tools___<ver>.js."""
    if arg and os.path.exists(arg):
        return build(arg)
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    url = _script_url(arg, opener)
    say(f"скачиваю {url}")
    script = _get(opener, url)
    if b"window.global_tools" not in script:
        sys.exit(f"{url}: в файле нет window.global_tools — формат скрипта сменился")
    os.makedirs(CAT_DIR, exist_ok=True)
    _build_downloaded(os.path.basename(urlparse(url).path), script)
    return None


def _build_downloaded(name, script):
    """Собрать каталог из скачанного скрипта: временный файл с тем же именем (оно попадает в source)."""
    with tempfile.TemporaryDirectory() as folder:
        js_path = os.path.join(folder, name)
        with open(js_path, "wb") as target:
            target.write(script)
        build(js_path)


def _script_url(arg, opener):
    if not arg:
        return find_tools_url(opener)
    if arg.startswith("http"):
        return arg
    name = os.path.basename(arg)
    return f"{SCRIPTS}/{name}"
