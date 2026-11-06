---
name: research-gap
description: Analyze research gaps using Web of Science Starter API, supplemented by Semantic Scholar, OpenAlex trends, and Crossref metadata. Deduplicate DOI records, preserve source evidence, and generate an HTML report without inventing references.
---

Analyze research gaps for "$ARGUMENTS".

## MAIN FLOW

```
Main Session — coordination
  │
  ├── STEP 1: Subagent → comprehensive literature search + trend data
  ├── STEP 2: Subagent → identify gaps from landscape data
  └── STEP 3: Report subagent → HTML gap analysis report
```

## STEP 1: Literature Landscape (subagent)

Read [Web of Science Starter integration](references/wos-starter.md) before
retrieval. Use Web of Science Core Collection when the user has authorized API
access; retain Semantic Scholar, OpenAlex, and Crossref as supplemental sources.
Do not require a WOS subscription for tasks explicitly using only public sources.

The local Python helper performs a bounded, single-page search, DOI deduplication,
source tagging, and rate-limit handling. From the repository root:

```bash
python3 .agents/skills/research-gap/scripts/literature_search.py \
  --topic 'soil aggregate stability' --sources wos --limit 3
```

For a small cross-source sample, explicitly select
`--sources wos s2 openalex crossref`. Inspect the JSON `complete` flag and every
entry in `sources`; a failed source leaves other records available but produces a
nonzero exit status. The helper uses `WOS_API_KEY` from the environment; never
print the key, authentication headers, or a process environment dump. It preserves
the inherited HTTPS proxy and TLS verification. Do not use a generic web-fetch
tool that cannot safely supply the required authentication.

Launch subagent:

```
TASK: Map the research landscape for "{topic}".

Generate 5 search queries:
1. Core topic (exact)
2. Broader field
3. Methodology-focused
4. Application-focused
5. "{topic} challenges OR future OR limitations"

### Web of Science Starter — Core Collection
GET https://api.clarivate.com/apis/wos-starter/v1/documents
Parameters: db=WOS, q=TS=({query}), limit=3, page=1 (URL-encode parameters).
Authentication: WOS_API_KEY environment binding, using the documented API-key header.
Use the helper; choose a deliberate record/request budget before expanding queries.
Record uid, title, identifiers.doi, source.publishYear and citations[db=WOS].count.
Missing DOI/year/citation fields remain null; an explicit citation count of 0 is valid.
Starter metadata does not supply abstracts/full text for thematic gap inference.

### Semantic Scholar — recent + highly cited
For each query:
WebFetch: https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=40&fields=title,authors,year,venue,citationCount,externalIds,abstract,fieldsOfStudy&year=2019-2026

### Crossref — complementary DOI and publication metadata
GET https://api.crossref.org/works?query={query}&rows=3
Use DOI, title, published.date-parts and is-referenced-by-count with Crossref provenance.
Check record type: a keyword search may return datasets, figures or other components.
Crossref metadata is not a substitute for abstracts, article methods, or WOS coverage.

### OpenAlex — publication trends over time
WebFetch: https://api.openalex.org/works?search={core_query}&group_by=publication_year&mailto=paperskills@example.com

### OpenAlex — concept trends
WebFetch: https://api.openalex.org/concepts?search={topic}&mailto=paperskills@example.com

### OpenAlex — recent vs old comparison
Recent: https://api.openalex.org/works?search={topic}&filter=publication_year:2023-2026&per_page=20&sort=cited_by_count:desc&mailto=paperskills@example.com
Old: https://api.openalex.org/works?search={topic}&filter=publication_year:2010-2015&per_page=20&sort=cited_by_count:desc&mailto=paperskills@example.com

COLLECT:
- Paper count per year (2010-2026)
- Top 30 papers by citations (all time)
- Top 20 papers from last 2 years
- Top venues
- Key authors (most papers + most cited)
- Related concepts/subfields
- Abstracts of top 30 papers (for theme extraction)

NORMALIZE AND AUDIT:
- Normalize DOI case, doi:/doi.org prefixes and URL encoding before deduplication.
- Merge the same DOI across sources but retain every source ID, query, retrieval time,
  original bibliographic fields and that source's citation count/database.
- Missing or invalid DOI stays null. Do not silently merge DOI-less papers by title.
- Keep source-specific query totals separate from retrieved/deduplicated sample counts.
- Do not sum citation counts or overlapping provider totals; flag field conflicts.
- Missing/failed responses and a small single-page sample do not prove a literature gap.
```

## STEP 2: Gap Identification (subagent)

Launch subagent with landscape data:

```
TASK: Identify research gaps.

LANDSCAPE DATA:
{output from step 1}

EVIDENCE CHECK:
- Cite retrieved source IDs/DOIs for each claim and distinguish verified observations
  from candidate questions that require further retrieval.
- Use abstracts/methods only when actually retrieved and authorized. WOS Starter
  titles and keywords alone cannot establish a methodological or population gap.
- Disclose failed sources, sampling, query/date ranges and incomplete coverage.
- Never interpret an API error, missing field, or absence from 3 hits as zero literature.

ANALYZE:

### A. Temporal Gaps
- Topics studied 5+ years ago but NOT recently revisited
- Declining publication count despite unresolved questions
- Emerging topics with <5 papers

### B. Methodological Gaps
- Mostly theoretical → empirical gap
- Mostly quantitative → qualitative gap
- Mostly single-country → comparative gap
- No meta-analyses/reviews → synthesis gap

### C. Thematic Gaps
- Extract themes from top paper abstracts
- Find theme COMBINATIONS that don't appear
  (e.g., "fairness + NLP" has 200 papers, "fairness + speech" has 3)
- Disconnected clusters that should connect

### D. Application Gaps
- Theory exists but no applied/practical studies
- Applied in one domain but not another

### E. Population/Context Gaps
- Geographic: studied in US/EU but not elsewhere?
- Demographic: adults but not children?
- Domain: medicine but not law?

### F. Contradictions
- Opposing findings on same question
- Unresolved theoretical debates

OUTPUT per gap:
- Gap description (1-2 sentences)
- Evidence: what exists vs. what's missing (with paper counts)
- Suggested research question
- Feasibility: data availability, method needed
- Impact: high/medium/low
- Priority: 1 (most promising) to 3 (niche)
```

## STEP 3: HTML Report (report subagent)

```
File: reports/{date}-research-gap-{topic}.html

SECTIONS:
1. Executive Summary — top 5 gaps, prioritized
2. Literature Landscape
   - Chart.js line chart: papers per year
   - Top venues table
   - Key authors table
   - Related concepts as tag cloud
3. Gap Analysis
   - Each gap as a card with evidence, questions, priority badge
   - Color: red=high priority, yellow=medium, blue=niche
4. Suggested Research Questions (numbered)
5. Methodology Notes & Limitations
   - Queries, retrieval dates, per-source totals, sample size, deduplication and failures
   - Provider-specific citation counts and field conflicts; no invented references
   - Clarivate attribution and storage/export/sharing restrictions under the user's licence

After writing the file:
- Return the exact absolute file path to the user
- Ask whether they want it opened
- Only run `open {file_path}` after the user explicitly confirms
```

## STEP 4: Next Actions

- "Deep-dive a specific gap? (/lit-search {gap topic})"
- "Check if a gap was recently addressed?"
- "Draft a research proposal outline for one of these gaps?"

## API REFERENCE

### Web of Science Starter and executable retrieval

See [parameters, field mapping, credentials and usage terms](references/wos-starter.md).
Run offline tests with:

```bash
python3 -m unittest discover -s .agents/skills/research-gap/tests -v
```

The helper defaults to WOS only and 3 records. Supplemental sources
remain opt-in per command; it does not silently paginate or bypass a denied source.

### OpenAlex Group-By (trends)
```
Papers per year: /works?search={topic}&group_by=publication_year
By OA status: /works?search={topic}&group_by=open_access.is_oa
By type: /works?search={topic}&group_by=type
```

### OpenAlex Concepts
```
/concepts?search={topic} → related concepts, works_count, description
```

### Semantic Scholar Recommendations
```
/recommendations/v1/papers/forpaper/{paperId}?limit=20&fields=title,authors,year,citationCount,abstract
```

## ERROR HANDLING
- Network/CONNECT denial: report the blocked destination; do not bypass the proxy.
- Missing WOS_API_KEY: report the missing binding; request secure environment settings,
  not a key value in chat. A platform proxy placeholder is valid when used through its
  configured HTTPS destination; never replace it with an invented credential.
- HTTP 401/403: diagnose authentication/subscription/permission; do not retry unchanged.
- HTTP 429: honor Retry-After (seconds or HTTP date), with bounded retries. If the
  requested wait exceeds the budget, stop rather than retrying too early. The helper
  also bounds retries for transient network errors and HTTP 502/503/504.
- Keep independently successful sources when another fails and report partial coverage.
- Topic too broad (>100K papers): ask user to narrow
- Topic too narrow (0-5 papers): broaden, check spelling
- Trend data gaps: note which years incomplete
- Abstract coverage: not all papers have abstracts in API

## TOKEN BUDGET
- Main: ~3K (coordination)
- Landscape subagent: ~25-40K
- Gap analysis subagent: ~15-25K
- Report subagent: ~10-15K
- Total: ~55-85K (most intensive skill)
- If landscape output too large: summarize before passing to gap analysis

## LANGUAGE

Determine report language:
- If the user explicitly requests a language (e.g., "in Chinese", "用中文"): use that language
- If the manuscript/input is primarily in Chinese: default to Chinese
- Otherwise: default to English

When generating in Chinese:
- Set `<html lang="zh">` on the HTML document
- Write all headings, labels, descriptions, and analysis text in Chinese
- Keep technical terms in original form (DOI, journal names, API names)
- Use Chinese punctuation (，。、；：)
- stat-label text in the stats bar should be Chinese (e.g., "论文总数" not "Total Papers")
- Badge text should be Chinese (e.g., "高优先级" not "HIGH PRIORITY", "方法缺口" not "METHODOLOGICAL GAP")

## REPORT DESIGN
When writing the HTML report, read and follow the design system in `assets/report-template.md` (relative to this SKILL.md) EXACTLY.
Do NOT use Tailwind CDN. Use the custom CSS variables, Crimson Pro font, and academic book aesthetic defined there.

## Project-local Codex integration

Read [INSTALLATION.md](INSTALLATION.md) for source, runtime requirements and limitations.
Resolve `assets/report-template.md` relative to this file. The bundled template is authoritative for typography (Cormorant Garamond / Source Sans 3), superseding the older Crimson Pro mention above.
Use available HTTPS tools when WebFetch is unavailable. Treat `$ARGUMENTS` as the user's supplied topic; `/lit-search` is an optional, uninstalled extension.
Use real retrieved evidence only. Record retrieval dates, queries and coverage; missing or failed API responses do not establish a research gap. Never invent paper counts, citations, results or references. Update the illustrative year ranges for the actual study period. Replace the example mailto with an authorized contact, or omit it; do not claim that address as your identity.
If subagents are unavailable, run the same stages sequentially and report that limitation.
