"""Shared helpers: resilient HTTP with on-disk caching and Hebrew name keys."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests

from . import config


def log(msg: str) -> None:
    print(f"[pipeline] {msg}", file=sys.stderr, flush=True)


def http_get(url: str, *, cache: Path, params: dict | None = None,
             binary: bool = False, retries: int = 3) -> Optional[bytes]:
    """GET ``url`` and cache the body at ``cache``.

    Returns the freshly fetched body on success. On any network failure, falls
    back to the cached copy if one exists (returning it), else returns None.
    This is what makes the pipeline runnable offline / in restricted sandboxes:
    the data simply refreshes wherever egress is allowed (e.g. GitHub Actions).
    """
    cache.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": config.USER_AGENT}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers,
                                timeout=config.HTTP_TIMEOUT)
            resp.raise_for_status()
            body = resp.content
            cache.write_bytes(body)
            log(f"fetched {url} -> {cache.name} ({len(body)} bytes)")
            return body
        except Exception as exc:  # noqa: BLE001 - we intentionally degrade
            last_err = exc
            time.sleep(min(2 ** attempt, 8))
    if cache.exists():
        log(f"WARN unreachable {url} ({last_err}); using cached {cache.name}")
        return cache.read_bytes()
    log(f"WARN unreachable {url} ({last_err}); no cache, skipping")
    return None


def ckan_datastore_search(resource_id: str, *, cache: Path,
                          limit: int = 100000) -> Optional[list[dict]]:
    """Pull all records of a data.gov.il CKAN datastore resource as dict rows."""
    url = f"{config.DATAGOV_BASE}/datastore_search"
    body = http_get(url, cache=cache,
                    params={"resource_id": resource_id, "limit": limit})
    if not body:
        return None
    try:
        payload = json.loads(body)
        return payload["result"]["records"]
    except Exception as exc:  # noqa: BLE001
        log(f"WARN bad CKAN payload for {resource_id}: {exc}")
        return None


# --- Hebrew locality-name normalisation (the join key across Israeli sources) -

_HE_PUNCT = re.compile(r"[֑-ׇ\"'`׳״.\-()]+")
_WS = re.compile(r"\s+")

# Common spelling variants seen between Peace Now, CBS and the elections files.
_HE_ALIASES = {
    "מודיעין עילית": "מודיעין עלית",
    "ביתר עילית": "ביתר עלית",
    "מעלה אדומים": "מעלה אדמים",
    "אלקנה": "אלקנה",
}


def he_key(name: str | None) -> str:
    """Normalise a Hebrew locality name to a stable join key."""
    if not name or (isinstance(name, float)):
        return ""
    s = str(name).strip()
    s = _HE_ALIASES.get(s, s)
    s = _HE_PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s
