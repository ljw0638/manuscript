# Web of Science Starter retrieval

Use this integration for authorized bibliographic searches, followed by evidence-based
research-gap analysis. The executable helper uses Python 3.10+ standard-library modules;
no SDK or third-party package is required.

## Credentials and network

Configure the HTTP secret `WOS_API_KEY` in the Codex environment, scoped to
`api.clarivate.com`. The helper reads the environment binding and supplies it through
the documented `X-ApiKey` header. Never put credentials in CLI arguments, query strings,
source code, test fixtures, logs, reports or commits. Do not dump request headers.

Codex may expose a placeholder instead of the raw secret. Keep the inherited HTTPS
proxy and CA trust so that the proxy can substitute the configured secret. A placeholder
does not establish invalid authentication; test the actual endpoint. A missing binding,
CONNECT denial, TLS/transport failure, API 401/403 and API 429 are separate outcomes.
Do not turn off certificate verification, bypass network policy, or repeatedly retry an
unchanged authentication failure. The helper rejects redirects to avoid forwarding
authentication to an unexpected destination.

Supplemental destinations are `api.semanticscholar.org`, `api.openalex.org` and
`api.crossref.org`. API access and quota must be checked independently for each source.

## Official Starter API contract

The [official Clarivate Documents API documentation](https://github.com/clarivate/wosstarter_python_client/blob/master/docs/DocumentsApi.md)
and [official client README](https://github.com/clarivate/wosstarter_python_client/blob/master/README.md)
describe:

```text
GET https://api.clarivate.com/apis/wos-starter/v1/documents
db=WOS
q=TS=(soil aggregate stability)
limit=3
page=1
```

URL-encode the parameters. `WOS` selects Web of Science Core Collection; `TS` searches
the Topic fields (title, abstract, author keywords and Keywords Plus). The unquoted query
uses the API's topic search semantics; it is not an exact-phrase claim. For an exact
phrase use the explicit advanced query `TS=("soil aggregate stability")`. The helper
accepts a topic and wraps it in `TS=(...)`; use valid, deliberate search syntax.

The documented page limit is 1–50. The helper defaults to 3, fetches only page 1 and
never starts a bulk export. A three-record connectivity check is not a comprehensive
landscape search, citation ranking, trend analysis or demonstration of a research gap.

| Meaning | Response field |
| --- | --- |
| Query total, not downloaded sample size | `metadata.total` |
| Returned documents | `hits[]` |
| Source identifier | `hits[].uid` |
| Title | `hits[].title` |
| DOI, if supplied | `hits[].identifiers.doi` |
| Publication year | `hits[].source.publishYear` |
| Core Collection citation count | `hits[].citations[]` where `db == "WOS"`, field `count` |

The citation schema is documented in
[DocumentCitationsInner](https://github.com/clarivate/wosstarter_python_client/blob/master/docs/DocumentCitationsInner.md).
Access to citation fields can depend on subscription. Keep missing counts as `null`,
distinct from a supplied zero. Counts are database-specific snapshots, not a universal
measure; do not replace missing WOS counts with a Crossref/S2/OpenAlex count.

## Run and interpret

From `/workspace/manuscript`:

```bash
python3 .agents/skills/research-gap/scripts/literature_search.py \
  --topic 'soil aggregate stability' --sources wos --limit 3

python3 .agents/skills/research-gap/scripts/literature_search.py \
  --topic 'soil aggregate stability' --sources wos s2 openalex crossref --limit 3
```

Standard output contains normalized JSON. `records` is the deduplicated sample, not
the query total. Each record keeps source entries with original fields, provider ID,
query, retrieval time and citation database/count. Conflicting values remain available
in those entries for review. Inspect `sources` for each provider's status, total and
returned count, and `complete` for partial failure. Exit status is nonzero when any
selected source fails; independently successful records are still returned.

DOI matching removes known prefixes, decodes DOI URL paths and folds case. DOI-less
records stay distinct across providers; title similarity is not proof of identity.
Never manufacture a DOI or reference to fill a missing field. Crossref results may
include figure/component metadata; inspect source type before calling an item a paper.

The helper makes bounded retries for 429, selected transient gateway/service errors
and transport failures. It respects Retry-After seconds/date values and stops when
the requested delay exceeds its wait budget. It never retries 401/403 automatically.
Use the actual response headers/account plan for quotas, not a universal assumed rate.
Run sources sequentially and request only the metadata needed for the task.

## Research-gap evidence and data use

Use retrieved metadata to identify candidate questions. Establish trends with appropriate
year queries/grouping, and methodological/thematic/population gaps with actual authorized
abstracts or methods, rather than title-only inference. Starter documents do not supply
full text or abstracts. Preserve query dates, source coverage, failures and sampling in
the final analysis. A rate-limited source is unavailable evidence, not an empty field.

Clarivate's official client identifies its licence as
[Clarivate Content as a Service Licence](https://github.com/clarivate/wosstarter_python_client/blob/master/pyproject.toml).
The API data are not thereby open-licensed. Follow the applicable institutional
subscription, API plan and Clarivate terms for retention, export, attribution and sharing;
do not infer full-text access or unrestricted redistribution. Consult the
[official Starter subscription portal](https://developer.clarivate.com/apis/wos-starter)
for current terms and entitlements; no unsupported legal clause or fixed quota is asserted
here. Attribute the provider in analysis and limit collection to the authorized purpose.

Do not commit live Clarivate response payloads, exported records or credentials to a
public PR. Tests use synthetic fixtures only. Temporary live validation results are
kept outside the checkout; public test success does not confer redistribution rights.
