#!/usr/bin/env python3
"""Sleduje změny letáků na zadaných URL a notifikuje přes Slack."""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK', '')
STATE_FILE = 'state.json'
URLS_FILE = 'urls.json'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36'
    )
}


def fetch_page(url: str) -> tuple[str, str]:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.url, resp.text


def extract_signals(final_url: str, html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')

    title = soup.find('title')
    title = title.get_text(strip=True) if title else ''

    og: dict[str, str] = {}
    for prop in ('og:title', 'og:description', 'og:url', 'og:image'):
        tag = soup.find('meta', property=prop)
        og[prop] = tag.get('content', '') if tag else ''

    # Publitas vkládá publication ID do JS dat na stránce
    pub_id = ''
    for pattern in [
        r'"publicationId"\s*:\s*"([^"]+)"',
        r'"publication_id"\s*:\s*"([^"]+)"',
        r'letaky\.makro\.cz/[^"\']+/([a-z0-9]{5,12})',
    ]:
        if m := re.search(pattern, html):
            pub_id = m.group(1)
            break

    return {
        'final_url': final_url,
        'title': title,
        'og_title': og['og:title'],
        'og_desc': og['og:description'],
        'og_url': og['og:url'],
        'og_image': og['og:image'],
        'pub_id': pub_id,
    }


def fingerprint(signals: dict) -> str:
    key = '|'.join([
        signals['final_url'],
        signals['title'],
        signals['og_title'],
        signals['og_url'],
        signals['og_image'],
        signals['pub_id'],
    ])
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def post_slack(text: str):
    if not SLACK_WEBHOOK:
        print('  [WARN] SLACK_WEBHOOK není nastaven')
        return
    resp = requests.post(SLACK_WEBHOOK, json={'text': text}, timeout=10)
    resp.raise_for_status()
    print('  Slack notifikace odeslána')


def notify_init(url: str, signals: dict):
    label = signals['og_title'] or signals['title'] or url
    post_slack(
        f"👀 *Začínám sledovat leták*\n"
        f"*URL:* {url}\n"
        f"*Aktuální leták:* {label}\n"
        f"*Odkaz:* {signals['final_url']}"
    )


def notify_change(url: str, old: dict, new: dict):
    old_title = old.get('og_title') or old.get('title') or '?'
    new_title = new['og_title'] or new['title'] or '?'
    post_slack(
        f"🆕 *Nový leták Makro!*\n"
        f"*Sledovaná URL:* {url}\n"
        f"*Starý leták:* {old_title}\n"
        f"*Nový leták:* {new_title}\n"
        f"*Odkaz:* {new['final_url']}"
    )


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write('\n')


def load_urls() -> list[str]:
    with open(URLS_FILE) as f:
        data = json.load(f)
    return data.get('urls', [])


def save_urls(urls: list[str]):
    with open(URLS_FILE, 'w') as f:
        json.dump({'urls': urls}, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    urls = load_urls()
    if not urls:
        print('Žádné URL v urls.json')
        sys.exit(0)

    state = load_state()
    remaining_urls = list(urls)

    for url in urls:
        print(f'Kontroluji: {url}')
        try:
            final_url, html = fetch_page(url)
            signals = extract_signals(final_url, html)
            fp = fingerprint(signals)
        except Exception as e:
            print(f'  [ERROR] {e}')
            continue

        stored = state.get(url)
        label = signals['og_title'] or signals['title'] or final_url

        if stored is None:
            print(f'  [INIT] Ukládám výchozí stav: {label}')
            notify_init(url, signals)
            state[url] = {**signals, 'fingerprint': fp,
                          'saved_at': datetime.now(timezone.utc).isoformat()}
        elif fp != stored.get('fingerprint'):
            print(f'  [ZMĚNA] Detekován nový leták: {label}')
            notify_change(url, stored, signals)
            remaining_urls.remove(url)
            print(f'  URL odebrána ze sledování.')
            state[url] = {**signals, 'fingerprint': fp,
                          'saved_at': datetime.now(timezone.utc).isoformat()}
        else:
            print(f'  [OK] Beze změny: {label}')

    save_state(state)
    save_urls(remaining_urls)


if __name__ == '__main__':
    main()
