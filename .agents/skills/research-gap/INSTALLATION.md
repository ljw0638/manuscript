# Research Gap installation

Source: https://github.com/cocoafun/paperskills
Commit: 99e7a2ff93ec025697ee8aaf51ddea9d3573cb24
Files: skills/paperskills-core/research-gap/SKILL.md and assets/report-template.md.
The upstream installation originally preserved its YAML metadata. Local extensions now
update the description and retrieval workflow for Web of Science Starter, Semantic
Scholar, OpenAlex and Crossref; add a standard-library Python helper and offline tests;
and document DOI deduplication, source provenance, retries and data-use limits. The
template remains local, with clarified typography and Codex integration. No entire
source checkout or Clarivate SDK is included.

## License declaration

The upstream README declares `MIT` under License, and registry/skills.json declares `MIT` for research-gap. No LICENSE/COPYING file was present in the inspected source revision. This records the upstream declaration without inventing a copyright holder or license text. Obtaining a complete upstream copyright/license notice remains outstanding.

## Runtime dependencies and limits

No Python or Node packages are needed to read this skill. The executable helper needs
Python 3.10+ and no third-party packages. Actual retrieval needs authorized HTTPS access
to the selected providers: api.clarivate.com, api.semanticscholar.org, api.openalex.org
and api.crossref.org. Web of Science requires a usable WOS_API_KEY environment secret
scoped to api.clarivate.com and a Starter subscription. Credentials are never bundled.
Consult [Web of Science integration](references/wos-starter.md) for official parameters,
response fields, safe proxy-backed authentication and usage terms. API readiness and
quota must be rechecked in the current environment; a prior successful call does not
guarantee future access or unrestricted export. The helper defaults to WOS only, one
page and 3 records; supplemental sources are explicitly selected.

From the repository root, run offline behavior tests with
`python3 -m unittest discover -s .agents/skills/research-gap/tests -v`.
Tests use synthetic data, not licensed Clarivate exports. They do not replace live
authentication/schema validation or a fresh-session research-gap evaluation.
HTML reports use the bundled CSS; Google Fonts (fonts.googleapis.com / fonts.gstatic.com) are optional and have local fallbacks. Interactive trends require Chart.js (for example cdn.jsdelivr.net); it is not bundled. For offline reports provide a local chart asset or static chart from actual data and document the deviation. No report or live literature analysis was executed during installation.
`lit-search` is not installed. No other paperskills skills were copied. Report opening remains subject to explicit user confirmation as the upstream workflow requires.
