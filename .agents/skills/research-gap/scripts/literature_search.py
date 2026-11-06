#!/usr/bin/env python3
"""Fetch one literature page per selected provider without inventing records."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
import re
import time
from urllib import error, parse, request


ENDPOINTS = {
    "wos": "https://api.clarivate.com/apis/wos-starter/v1/documents",
    "s2": "https://api.semanticscholar.org/graph/v1/paper/search",
    "openalex": "https://api.openalex.org/works",
    "crossref": "https://api.crossref.org/works",
}
RETRYABLE = {429, 502, 503, 504}


class _SearchError(Exception):
    """A deliberately sanitized provider failure, safe to include in JSON."""


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A credential-bearing request must never be forwarded to another URL.
        return None


def normalize_doi(value):
    """Normalize DOI spellings without guessing or trimming suffix punctuation."""
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    candidate = re.sub(r"^doi:\s*", "", candidate, flags=re.I)
    try:
        resolver = parse.urlsplit(candidate)
        if (resolver.scheme.lower() in ("http", "https")
                and resolver.hostname in ("doi.org", "dx.doi.org")):
            # Resolver tracking/fragment is not DOI content; encoded punctuation
            # inside the path remains part of the suffix after decoding.
            candidate = resolver.path.removeprefix("/")
        candidate = parse.unquote(candidate, errors="strict").strip()
    except (ValueError, UnicodeError):
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in candidate):
        return None
    if not re.fullmatch(r"10\.\d{4,9}/[^\s<>]+", candidate):
        return None
    return candidate.lower()


def _text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _integer(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _dict(value):
    return value if isinstance(value, dict) else {}


def _map_record(provider, item, query, retrieved_at):
    """Map actual provider metadata; absent information remains null."""
    if not isinstance(item, dict):
        raise _SearchError("Invalid response: a document is not an object")
    if provider == "wos":
        title = _text(item.get("title"))
        raw_doi = _dict(item.get("identifiers")).get("doi")
        year = _integer(_dict(item.get("source")).get("publishYear"))
        identifier = _text(item.get("uid")) or _text(item.get("id"))
        citations = item.get("citations", [])
        count = next((_integer(c.get("count")) for c in citations
                      if isinstance(c, dict) and c.get("db") == "WOS"), None) \
            if isinstance(citations, list) else None
        database = "WOS"
    elif provider == "s2":
        title = _text(item.get("title"))
        raw_doi = _dict(item.get("externalIds")).get("DOI")
        year = _integer(item.get("year"))
        identifier = _text(item.get("paperId"))
        count, database = _integer(item.get("citationCount")), "Semantic Scholar"
    elif provider == "openalex":
        title = _text(item.get("title"))
        raw_doi = item.get("doi")
        year = _integer(item.get("publication_year"))
        identifier = _text(item.get("id"))
        count, database = _integer(item.get("cited_by_count")), "OpenAlex"
    elif provider == "crossref":
        titles = item.get("title", [])
        title = _text(titles[0]) if isinstance(titles, list) and titles else None
        raw_doi = item.get("DOI")
        dates = _dict(item.get("published")).get("date-parts", [])
        first = dates[0] if isinstance(dates, list) and dates else []
        year = _integer(first[0]) if isinstance(first, list) and first else None
        identifier = normalize_doi(raw_doi)
        count = _integer(item.get("is-referenced-by-count"))
        database = "Crossref"
    else:
        raise ValueError("Unsupported provider")
    doi = normalize_doi(raw_doi)
    if not any((title, identifier, doi)):
        raise _SearchError("Invalid response: document has no bibliographic identity")
    provenance = {
        "provider": provider, "id": identifier, "title": title, "doi": doi,
        "raw_doi": raw_doi, "year": year, "citation_count": count,
        "citation_database": database, "query": query, "retrieved_at": retrieved_at,
    }
    if provider == "crossref":
        # Crossref indexes books, datasets and other works as well as articles.
        provenance["type"] = _text(item.get("type"))
    elif provider == "wos":
        provenance["types"] = item.get("types")
        provenance["source_types"] = item.get("sourceTypes")
    return {"doi": doi, "title": title, "year": year, "sources": [provenance]}


def _extract_page(provider, data, query, retrieved_at):
    if not isinstance(data, dict):
        raise _SearchError("Invalid response: expected a JSON object")
    if provider == "wos":
        items = data.get("hits")
        total = _dict(data.get("metadata")).get("total")
    elif provider == "s2":
        items, total = data.get("data"), data.get("total")
    elif provider == "openalex":
        items = data.get("results")
        total = _dict(data.get("meta")).get("count")
    elif provider == "crossref":
        message = _dict(data.get("message"))
        items, total = message.get("items"), message.get("total-results")
    else:
        raise ValueError("Unsupported provider")
    if not isinstance(items, list):
        raise _SearchError("Invalid response: document list is missing")
    return ([_map_record(provider, item, query, retrieved_at) for item in items],
            _integer(total))


def merge_records(records):
    """Merge DOI/source-ID matches, including later bridges between groups."""
    merged = []
    for record in records:
        incoming = deepcopy(record)
        incoming["doi"] = normalize_doi(incoming.get("doi"))
        incoming.setdefault("sources", [])
        matches = []
        # Recheck until stable: a DOI-less source-ID match can reveal a DOI
        # already present in another group. Conflicting explicit DOIs never merge.
        changed = True
        while changed:
            changed = False
            ids = {(s.get("provider"), s.get("id")) for s in incoming["sources"]
                   if s.get("provider") and s.get("id")}
            for index, existing in enumerate(merged):
                if index in matches:
                    continue
                same_doi = incoming["doi"] and incoming["doi"] == existing.get("doi")
                conflicting = (incoming["doi"] and existing.get("doi")
                               and incoming["doi"] != existing["doi"])
                existing_ids = {(s.get("provider"), s.get("id"))
                                for s in existing["sources"]
                                if s.get("provider") and s.get("id")}
                if not same_doi and (conflicting or not ids & existing_ids):
                    continue
                matches.append(index)
                if not incoming["doi"]:
                    incoming["doi"] = existing.get("doi")
                incoming["sources"].extend(s for s in existing["sources"]
                                           if s not in incoming["sources"])
                changed = True
        if not matches:
            merged.append(incoming)
            continue
        first = min(matches)
        # Keep the earliest selected provider's fields; preserve conflicts in sources.
        combined = deepcopy(merged[first])
        combined["doi"] = incoming["doi"]
        for other in [merged[i] for i in sorted(matches)] + [incoming]:
            for key in ("title", "year"):
                if combined.get(key) is None or combined.get(key) == "":
                    combined[key] = other.get(key)
            for source in other["sources"]:
                if source not in combined["sources"]:
                    combined["sources"].append(source)
        merged[first] = combined
        for index in sorted((i for i in matches if i != first), reverse=True):
            del merged[index]
    return merged


def _retry_delay(headers, attempt, now):
    value = headers.get("Retry-After") if headers else None
    if value is not None:
        value = str(value).strip()
        if value.isdigit():
            return int(value)
        try:
            target = parsedate_to_datetime(value)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            return max(0, (target - now()).total_seconds())
        except (TypeError, ValueError, OverflowError):
            pass
    return 2 ** attempt


def _request_json(url, headers, *, opener, sleep, now, max_retries,
                  max_wait, timeout):
    for attempt in range(max_retries + 1):
        try:
            req = request.Request(url, headers=headers, method="GET")
            with opener(req, timeout=timeout) as response:
                payload = response.read()
            try:
                return json.loads(payload)
            except (ValueError, UnicodeError):
                raise _SearchError("Invalid JSON response") from None
        except error.HTTPError as exc:
            code, response_headers = exc.code, exc.headers
            exc.close()
            if code in RETRYABLE and attempt < max_retries:
                delay = _retry_delay(response_headers, attempt, now)
                if delay > max_wait:
                    raise _SearchError(
                        f"HTTP {code}: Retry-After exceeds the permitted wait; stopped") from None
                sleep(delay)
                continue
            detail = "; redirects are disabled" if 300 <= code < 400 else ""
            raise _SearchError(f"HTTP {code}{detail}") from None
        except (error.URLError, TimeoutError, OSError):
            # Raw exceptions may include URLs, headers or injected credentials.
            if attempt < max_retries:
                delay = 2 ** attempt
                if delay <= max_wait:
                    sleep(delay)
                    continue
            raise _SearchError("HTTPS transport failed") from None


def _provider_request(provider, topic, limit, environ):
    headers = {"Accept": "application/json", "User-Agent": "manuscript-research-gap/1"}
    query = topic
    if provider == "wos":
        key = environ.get("WOS_API_KEY")
        if not isinstance(key, str) or not key.strip():
            raise _SearchError("WOS_API_KEY is missing")
        if any(ord(char) < 33 or ord(char) > 126 for char in key):
            raise _SearchError("WOS_API_KEY must be a single ASCII token")
        headers["X-ApiKey"] = key
        query = f"TS=({topic})"
        params = {"db": "WOS", "q": query, "limit": limit, "page": 1}
    elif provider == "s2":
        params = {"query": topic, "limit": limit,
                  "fields": "title,year,citationCount,externalIds"}
    elif provider == "openalex":
        params = {"search": topic, "per-page": limit, "page": 1}
    else:
        params = {"query.bibliographic": topic, "rows": limit, "offset": 0}
    return ENDPOINTS[provider] + "?" + parse.urlencode(params), headers, query


def search(topic, sources=("wos",), limit=3, *, opener=None, sleep=time.sleep,
           now=None, max_retries=2, max_wait=60, timeout=30, environ=None):
    """Return one page/provider, separate totals, provenance and explicit failures.

    Inject opener(Request, timeout=...), sleep(seconds), and now()->aware datetime
    for offline tests. Optional supplemental providers currently use public access.
    """
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic must be a nonempty string")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("limit must be an integer from 1 to 50")
    if isinstance(sources, str):
        sources = (sources,)
    sources = tuple(dict.fromkeys(sources))
    if not sources or any(source not in ENDPOINTS for source in sources):
        raise ValueError("sources must select wos, s2, openalex or crossref")
    if (isinstance(max_retries, bool) or not isinstance(max_retries, int)
            or not 0 <= max_retries <= 2):
        raise ValueError("max_retries must be 0, 1 or 2")
    if not isinstance(max_wait, (int, float)) or not 0 <= max_wait <= 60:
        raise ValueError("max_wait must be between 0 and 60 seconds")
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
        raise ValueError("timeout must be positive and at most 60 seconds")
    now = now or (lambda: datetime.now(timezone.utc))
    environ = os.environ if environ is None else environ
    if opener is None:
        opener = request.build_opener(_NoRedirect()).open
    output = {"query": topic, "records": [], "sources": {}, "complete": True}
    for provider in sources:
        status = {"status": "error", "total": None, "returned": 0, "error": None}
        try:
            url, headers, query = _provider_request(provider, topic, limit, environ)
            data = _request_json(url, headers, opener=opener, sleep=sleep,
                                 now=now, max_retries=max_retries,
                                 max_wait=max_wait, timeout=timeout)
            records, total = _extract_page(provider, data, query, now().isoformat())
            output["records"].extend(records)
            status.update(status="ok", total=total, returned=len(records))
        except _SearchError as exc:
            status["error"] = str(exc)
            output["complete"] = False
        output["sources"][provider] = status
    output["records"] = merge_records(output["records"])
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--sources", nargs="+", choices=tuple(ENDPOINTS), default=["wos"])
    parser.add_argument("--limit", type=int, choices=range(1, 51), default=3,
                        metavar="1..50")
    args = parser.parse_args(argv)
    if not args.topic.strip():
        parser.error("--topic must not be empty")
    result = search(args.topic, args.sources, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
