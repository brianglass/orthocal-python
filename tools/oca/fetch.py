"""Shared fetching for the oca.org harvests.

oca.org has no API, and no interstitial of the kind goarch.org sits behind.
Its robots.txt allows everything we touch (it disallows only two unrelated
paths) and asks for `Crawl-delay: 10`, which DELAY honours. Every page is
cached on disk, so re-running a harvest costs nothing after the first pass --
which matters a great deal at ten seconds a request.

One trap: oca.org 403s some user agents on a keyword match. A UA containing
the word "harvester" is refused; `python-urllib/3.14` is refused; the honest
self-identifying string below is served fine. That filter is a crude keyword
block, not the site's access policy -- robots.txt is the policy, and it says
yes. Identify yourself properly rather than impersonating a browser.
"""
import hashlib
import os
import time
import urllib.request

CACHE = 'data/oca_raw/_cache'
DELAY = 10.0    # seconds; oca.org's robots.txt asks for Crawl-delay: 10
UA = 'orthocal-bot/1.0 (+https://orthocal.info)'

_last = [0.0]


def get(url, cache=True):
    """Fetch a URL, caching the body on disk. Returns str, or None on 404."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + '.html')

    if cache and os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read() or None

    wait = DELAY - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)

    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            body = ''
        else:
            raise
    finally:
        _last[0] = time.time()

    with open(path, 'w', encoding='utf-8') as f:
        f.write(body)
    return body or None
