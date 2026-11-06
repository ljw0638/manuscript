"""Offline tests. All records, DOIs and credentials below are synthetic fixtures."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/literature_search.py"
SPEC = importlib.util.spec_from_file_location("literature_search", SCRIPT)
api = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = api
SPEC.loader.exec_module(api)

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
FAKE_KEY = "synthetic-not-a-real-api-key"
ENV = {"WOS_API_KEY": FAKE_KEY}
DOI = "10.1234/synthetic-example"


def wos_record(**updates):
    record = {
        "uid": "WOS:SYNTHETIC-1",
        "title": "Synthetic WOS title",
        "identifiers": {"doi": "10.1234/SYNTHETIC-EXAMPLE"},
        "source": {"publishYear": 2024},
        "citations": [{"db": "OTHER", "count": 999}, {"db": "WOS", "count": 0}],
    }
    record.update(updates)
    return record


def wos_page(*records):
    return {"metadata": {"total": 80, "page": 1, "limit": 3}, "hits": list(records)}


def s2_page():
    return {
        "total": 60,
        "data": [{"paperId": "synthetic-s2-1", "title": "Synthetic S2 title",
                  "externalIds": {"DOI": "doi:10.1234/synthetic-example"},
                  "year": 2023, "citationCount": 4}],
    }


def openalex_page():
    return {
        "meta": {"count": 50},
        "results": [{"id": "https://openalex.org/WSYNTHETIC1", "title": "Synthetic OA title",
                     "doi": "https://doi.org/10.1234/SYNTHETIC-EXAMPLE",
                     "publication_year": 2022, "cited_by_count": 5}],
    }


def crossref_page():
    return {
        "status": "ok", "message-type": "work-list",
        "message": {"total-results": 40, "items": [
            {"DOI": "10.1234/synthetic-example", "title": ["Synthetic Crossref title"],
             "published": {"date-parts": [[2021, 7]]}, "is-referenced-by-count": 6,
             "type": "journal-article"},
        ]},
    }


class Response:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200
        self.headers = {}

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Transport:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, *, timeout):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return Response(outcome)


def http_error(code, retry_after=None, reason="Synthetic HTTP failure"):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return HTTPError("https://api.clarivate.com/synthetic", code, reason, headers, io.BytesIO(b"{}"))


def search_with(transport, sources=("wos",), **kwargs):
    return api.search("synthetic topic", sources=sources, limit=3, opener=transport,
                      environ=ENV, now=lambda: NOW, **kwargs)


class DOIAndProvenanceTests(unittest.TestCase):
    def test_doi_prefix_case_and_percent_encoded_path(self):
        variants = [DOI, "  DOI:10.1234/SYNTHETIC-EXAMPLE  ",
                    "https://doi.org/10.1234/SYNTHETIC-EXAMPLE",
                    "http://dx.doi.org/10.1234/synthetic-example",
                    "https://doi.org/10.1234%2Fsynthetic-example"]
        for value in variants:
            with self.subTest(value=value):
                self.assertEqual(api.normalize_doi(value), DOI)

    def test_missing_or_invalid_doi_is_not_invented(self):
        for value in (None, "", "not-a-doi", "10.1234/invalid whitespace", "https://example.org/a"):
            with self.subTest(value=value):
                self.assertIsNone(api.normalize_doi(value))

    def test_valid_suffix_punctuation_is_preserved(self):
        self.assertEqual(api.normalize_doi("10.1234/SYNTHETIC(1)."), "10.1234/synthetic(1).")

    def test_doi_resolver_tracking_query_and_fragment_are_not_part_of_doi(self):
        self.assertEqual(
            api.normalize_doi("https://doi.org/10.1234/example?utm_source=x#ref"),
            "10.1234/example",
        )

    def test_encoded_doi_suffix_separators_are_preserved_and_merge_with_bare_doi(self):
        resolver = "https://doi.org/10.1234/foo%3Fbar%23baz?utm_source=x#ref"
        bare_doi = "10.1234/foo?bar#baz"
        self.assertEqual(api.normalize_doi(resolver), bare_doi)
        self.assertEqual(api.normalize_doi(bare_doi), bare_doi)
        s2 = s2_page()
        s2["data"][0]["externalIds"]["DOI"] = bare_doi
        result = search_with(Transport(wos_page(wos_record(identifiers={"doi": resolver})), s2),
                             sources=("wos", "s2"))
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["doi"], bare_doi)
        self.assertEqual({source["provider"] for source in result["records"][0]["sources"]},
                         {"wos", "s2"})

    def test_four_sources_merge_doi_but_keep_counts_titles_and_totals_separate(self):
        transport = Transport(wos_page(wos_record()), s2_page(), openalex_page(), crossref_page())
        result = search_with(transport, sources=("wos", "s2", "openalex", "crossref"))
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["records"]), 1)
        record = result["records"][0]
        self.assertEqual(record["doi"], DOI)
        sources = {source["provider"]: source for source in record["sources"]}
        self.assertEqual(set(sources), {"wos", "s2", "openalex", "crossref"})
        self.assertEqual({name: source["citation_count"] for name, source in sources.items()},
                         {"wos": 0, "s2": 4, "openalex": 5, "crossref": 6})
        self.assertEqual(sources["wos"]["citation_database"], "WOS")
        self.assertEqual(len({source["title"] for source in sources.values()}), 4)
        for source in sources.values():
            for field in ("id", "query", "retrieved_at", "year"):
                self.assertTrue(source[field], field)
        self.assertEqual({name: status["total"] for name, status in result["sources"].items()},
                         {"wos": 80, "s2": 60, "openalex": 50, "crossref": 40})

    def test_doi_less_records_with_identical_titles_are_not_fuzzy_merged(self):
        records = [wos_record(uid="WOS:SYNTHETIC-A", identifiers={}),
                   wos_record(uid="WOS:SYNTHETIC-B", identifiers={})]
        result = search_with(Transport(wos_page(*records)))
        self.assertEqual(len(result["records"]), 2)
        self.assertTrue(all(record["doi"] is None for record in result["records"]))

    def test_duplicate_source_id_without_doi_can_be_merged(self):
        result = search_with(Transport(wos_page(wos_record(identifiers={}), wos_record(identifiers={}))))
        self.assertEqual(len(result["records"]), 1)

    def test_later_doi_can_bridge_existing_source_id_and_doi_clusters(self):
        def record(provider, source_id, doi):
            return {"doi": doi, "title": "Synthetic shared work", "year": 2024,
                    "sources": [{"provider": provider, "id": source_id, "doi": doi,
                                 "title": "Synthetic shared work", "year": 2024,
                                 "citation_count": None, "citation_database": provider,
                                 "query": "synthetic topic", "retrieved_at": NOW.isoformat()}]}
        records = [record("wos", "WOS:SYNTHETIC-1", DOI),
                   record("s2", "synthetic-s2-1", None),
                   record("s2", "synthetic-s2-1", DOI)]
        merged = api.merge_records(records)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["doi"], DOI)
        self.assertEqual({(source["provider"], source["id"]) for source in merged[0]["sources"]},
                         {("wos", "WOS:SYNTHETIC-1"), ("s2", "synthetic-s2-1")})

    def test_source_id_is_scoped_to_its_provider_without_doi(self):
        shared_id = "synthetic-id-1"
        records = [{"doi": None, "title": "Synthetic title", "year": 2024,
                    "sources": [{"provider": provider, "id": shared_id}]}
                   for provider in ("wos", "s2")]
        self.assertEqual(len(api.merge_records(records)), 2)

    def test_conflicting_explicit_dois_are_not_merged_by_source_id(self):
        records = [{"doi": doi, "title": "Synthetic title", "year": 2024,
                    "sources": [{"provider": "wos", "id": "WOS:SYNTHETIC-1", "doi": doi}]}
                   for doi in (DOI, "10.1234/synthetic-other")]
        merged = api.merge_records(records)
        self.assertEqual(len(merged), 2)
        self.assertEqual({record["doi"] for record in merged},
                         {DOI, "10.1234/synthetic-other"})


class ProviderMappingTests(unittest.TestCase):
    def test_wos_core_collection_query_and_mapping(self):
        transport = Transport(wos_page(wos_record()))
        result = search_with(transport)
        request = transport.requests[0]
        parsed = urlsplit(request.full_url)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "api.clarivate.com")
        self.assertEqual(parsed.path, "/apis/wos-starter/v1/documents")
        query = parse_qs(parsed.query)
        self.assertEqual(query["db"], ["WOS"])
        self.assertEqual(query["q"], ["TS=(synthetic topic)"])
        self.assertEqual(query["limit"], ["3"])
        self.assertEqual(query["page"], ["1"])
        self.assertEqual(request.get_header("X-apikey"), FAKE_KEY)
        self.assertNotIn(FAKE_KEY, request.full_url)
        record = result["records"][0]
        self.assertEqual(record["year"], 2024)
        self.assertEqual(record["sources"][0]["citation_count"], 0)

    def test_absent_wos_count_and_doi_remain_unknown(self):
        result = search_with(Transport(wos_page(wos_record(identifiers={}, citations=[]))))
        record = result["records"][0]
        self.assertIsNone(record["doi"])
        self.assertIsNone(record["sources"][0]["citation_count"])

    def test_supplemental_provider_years_and_counts(self):
        for provider, payload, year, count in [
            ("s2", s2_page(), 2023, 4), ("openalex", openalex_page(), 2022, 5),
            ("crossref", crossref_page(), 2021, 6),
        ]:
            with self.subTest(provider=provider):
                transport = Transport(payload)
                result = search_with(transport, sources=(provider,))
                self.assertTrue(result["complete"])
                self.assertEqual(result["records"][0]["year"], year)
                self.assertEqual(result["records"][0]["sources"][0]["citation_count"], count)
                self.assertIsNone(transport.requests[0].get_header("X-apikey"))

    def test_record_types_and_original_doi_are_available_for_evidence_review(self):
        wos = wos_page(wos_record(types=["Article"], sourceTypes=["Journal"]))
        result = search_with(Transport(wos))
        source = result["records"][0]["sources"][0]
        self.assertEqual(source["types"], ["Article"])
        self.assertEqual(source["source_types"], ["Journal"])
        self.assertEqual(source["raw_doi"], "10.1234/SYNTHETIC-EXAMPLE")
        crossref = crossref_page()
        crossref["message"]["items"][0]["type"] = "component"
        result = search_with(Transport(crossref), sources=("crossref",))
        self.assertEqual(result["records"][0]["sources"][0]["type"], "component")

    def test_empty_success_is_distinct_from_failed_source(self):
        result = search_with(Transport(wos_page()))
        self.assertTrue(result["complete"])
        self.assertEqual(result["records"], [])
        self.assertEqual(result["sources"]["wos"]["status"], "ok")
        self.assertEqual(result["sources"]["wos"]["returned"], 0)

    def test_malformed_api_payload_is_not_a_passing_empty_result(self):
        for payload in ({"message": "Synthetic malformed response"},
                        {"metadata": {"total": 1}, "hits": {}},
                        {"metadata": {"total": 1}, "hits": [None]}):
            with self.subTest(payload=payload):
                result = search_with(Transport(payload))
                self.assertFalse(result["complete"])
                self.assertEqual(result["sources"]["wos"]["status"], "error")
                self.assertEqual(result["records"], [])

    def test_objects_without_bibliographic_identity_are_not_literature_records(self):
        pages = {
            "wos": lambda item: {"metadata": {"total": 1}, "hits": [item]},
            "s2": lambda item: {"total": 1, "data": [item]},
            "openalex": lambda item: {"meta": {"count": 1}, "results": [item]},
            "crossref": lambda item: {"message": {"total-results": 1, "items": [item]}},
        }
        metadata_only = {
            "wos": {"source": {"publishYear": 2024}, "citations": [{"db": "WOS", "count": 5}]},
            "s2": {"year": 2024, "citationCount": 5},
            "openalex": {"publication_year": 2024, "cited_by_count": 5},
            "crossref": {"published": {"date-parts": [[2024]]}, "is-referenced-by-count": 5},
        }
        for provider, page in pages.items():
            for item in ({}, metadata_only[provider]):
                with self.subTest(provider=provider, item=item):
                    result = search_with(Transport(page(item)), sources=(provider,))
                    self.assertFalse(result["complete"])
                    self.assertEqual(result["sources"][provider]["status"], "error")
                    self.assertEqual(result["records"], [])


class RetryAndFailureTests(unittest.TestCase):
    def test_retry_after_seconds_is_honored(self):
        transport = Transport(http_error(429, "4"), wos_page(wos_record()))
        delays = []
        result = search_with(transport, sleep=delays.append)
        self.assertTrue(result["complete"])
        self.assertEqual(delays, [4])
        self.assertEqual(len(transport.requests), 2)

    def test_retry_after_http_date_is_honored(self):
        retry_at = format_datetime(NOW + timedelta(seconds=7), usegmt=True)
        transport = Transport(http_error(429, retry_at), wos_page(wos_record()))
        delays = []
        result = search_with(transport, sleep=delays.append)
        self.assertTrue(result["complete"])
        self.assertEqual(delays, [7])

    def test_quota_wait_above_cap_stops_without_early_retry(self):
        transport = Transport(http_error(429, "120"))
        delays = []
        result = search_with(transport, sleep=delays.append, max_wait=30)
        self.assertFalse(result["complete"])
        self.assertEqual(delays, [])
        self.assertEqual(len(transport.requests), 1)

    def test_rate_limit_retries_are_bounded(self):
        transport = Transport(http_error(429), http_error(429), http_error(429))
        delays = []
        result = search_with(transport, sleep=delays.append, max_retries=2)
        self.assertFalse(result["complete"])
        self.assertEqual(len(transport.requests), 3)
        self.assertEqual(len(delays), 2)
        self.assertTrue(all(0 <= delay <= 60 for delay in delays))

    def test_transient_service_error_can_recover(self):
        transport = Transport(http_error(503), wos_page(wos_record()))
        delays = []
        result = search_with(transport, sleep=delays.append)
        self.assertTrue(result["complete"])
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(len(delays), 1)

    def test_authentication_errors_are_not_retried_and_do_not_echo_secret(self):
        for code in (401, 403):
            with self.subTest(code=code):
                transport = Transport(http_error(code, reason="Synthetic reason " + FAKE_KEY))
                delays = []
                result = search_with(transport, sleep=delays.append)
                self.assertFalse(result["complete"])
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(delays, [])
                self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_missing_key_is_reported_without_requesting_wos(self):
        transport = Transport()
        result = api.search("synthetic topic", opener=transport, environ={}, now=lambda: NOW)
        self.assertFalse(result["complete"])
        self.assertEqual(transport.requests, [])
        self.assertEqual(result["records"], [])

    def test_malformed_key_is_rejected_without_echo_or_request(self):
        for suffix in ("\n", "\r\nInjected: value", "\x01", "\x7f", "é", " "):
            with self.subTest(suffix=repr(suffix)):
                transport = Transport()
                result = api.search("synthetic topic", opener=transport,
                                    environ={"WOS_API_KEY": FAKE_KEY + suffix},
                                    now=lambda: NOW)
                self.assertFalse(result["complete"])
                self.assertEqual(transport.requests, [])
                self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_transport_error_does_not_echo_secret(self):
        transport = Transport(URLError("Synthetic proxy failure " + FAKE_KEY))
        result = search_with(transport, max_retries=0)
        self.assertFalse(result["complete"])
        self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_partial_failure_preserves_records_and_coverage_status(self):
        transport = Transport(http_error(429), crossref_page())
        result = search_with(transport, sources=("wos", "crossref"), max_retries=0)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["sources"]["wos"]["status"], "error")
        self.assertIsNone(result["sources"]["wos"]["total"])
        self.assertEqual(result["sources"]["crossref"]["status"], "ok")

    def test_redirect_handler_refuses_cross_host_forwarding(self):
        request = Request("https://api.clarivate.com/synthetic", headers={"X-ApiKey": FAKE_KEY})
        redirected = api._NoRedirect().redirect_request(
            request, None, 302, "Found", {}, "https://other.example/collect")
        self.assertIsNone(redirected)

    def test_default_transport_installs_redirect_rejection(self):
        transport = Transport(wos_page(wos_record()))
        with mock.patch.object(api.request, "build_opener") as build:
            build.return_value.open = transport
            result = api.search("synthetic topic", environ=ENV, now=lambda: NOW)
        self.assertTrue(result["complete"])
        self.assertIsInstance(build.call_args.args[0], api._NoRedirect)

    def test_redirect_error_is_not_retried(self):
        transport = Transport(http_error(302))
        result = search_with(transport)
        self.assertFalse(result["complete"])
        self.assertEqual(len(transport.requests), 1)


class CLITests(unittest.TestCase):
    def test_cli_partial_failure_outputs_json_and_exits_nonzero(self):
        result = search_with(Transport(http_error(429), crossref_page()),
                             sources=("wos", "crossref"), max_retries=0)
        output = io.StringIO()
        with mock.patch.object(api, "search", return_value=result), contextlib.redirect_stdout(output):
            exit_code = api.main(["--topic", "synthetic topic", "--sources", "wos", "crossref"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(output.getvalue()), result)
        self.assertNotIn(FAKE_KEY, output.getvalue())

    def test_cli_success_exits_zero(self):
        result = search_with(Transport(wos_page(wos_record())))
        output = io.StringIO()
        with mock.patch.object(api, "search", return_value=result), contextlib.redirect_stdout(output):
            self.assertEqual(api.main(["--topic", "synthetic topic"]), 0)
        self.assertEqual(json.loads(output.getvalue())["records"][0]["doi"], DOI)

    def test_cli_rejects_limit_outside_single_page_bound(self):
        for limit in ("0", "51"):
            with self.subTest(limit=limit), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    api.main(["--topic", "synthetic topic", "--limit", limit])
                self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
