#!/usr/bin/env python3
"""Check the deployed Pages URL, including gallery images and the custom 404."""
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAGES = [
    ("/", "Книга"),
    ("/contents/", "Алфавитный указатель"),
    ("/conclusion/", "Заключение"),
    ("/sections/a/", "Раздел"),
    ("/sections/p/", "Раздел"),
    ("/sections/ya/", "Раздел"),
    ("/exhibitions/akrostih/", "акростих"),
    ("/exhibitions/horovod/", "хоровод"),
    ("/exhibitions/yarmarka-literaturnaya/", "ярмарка"),
    ("/assets/site.css", "--accent"),
]
IMAGES = ["/images/stories/exhibition/horovod/horovod1.jpg",
          "/images/stories/exhibition/horovod/thumbs/60x60/horovod1.jpg"]
UNKNOWN = "/this-page-does-not-exist-12345/"


def check(get):
    failures = []
    for path, needle in PAGES + [("/404.html", "Страница не найдена"), (UNKNOWN, "Страница не найдена")]:
        status, body = get(path)
        expected = 404 if path == UNKNOWN else 200
        if status != expected or needle not in body.decode("utf-8", "replace"):
            failures.append(f"{path}: HTTP {status}, expected {expected} with {needle!r}")
    for path in IMAGES:
        status, body = get(path)
        if status != 200 or not body.startswith(b"\xff\xd8") or len(body) < 2000:
            failures.append(f"{path}: expected a JPEG image, received HTTP {status}, {len(body)} bytes")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="URL returned by the Pages deployment")
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--delay", type=float, default=10)
    args = parser.parse_args()
    base = args.base.rstrip("/")
    url = urllib.parse.urlsplit(base)
    if url.scheme != "https" or not url.netloc or url.query or url.fragment or args.attempts < 1 or args.delay < 0:
        parser.error("base must be an HTTPS URL; attempts >= 1 and delay >= 0")

    def get(path):
        request = urllib.request.Request(base + path, headers={"User-Agent": "glossary-smoke/2.0"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    for attempt in range(args.attempts):
        try:
            failures = check(get)
        except (OSError, urllib.error.URLError) as exc:
            failures = [str(exc)]
        if not failures:
            print(f"Published site passed {len(PAGES) + len(IMAGES) + 2} HTTPS checks: {base}/")
            return 0
        print(f"Attempt {attempt + 1}: " + "; ".join(failures))
        if attempt + 1 < args.attempts:
            time.sleep(args.delay)
    return 1


if __name__ == "__main__":
    sys.exit(main())
