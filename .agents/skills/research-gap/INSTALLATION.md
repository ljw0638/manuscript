# Research Gap installation

Source: https://github.com/cocoafun/paperskills
Commit: 99e7a2ff93ec025697ee8aaf51ddea9d3573cb24
Files: skills/paperskills-core/research-gap/SKILL.md and assets/report-template.md.
Original YAML metadata is unchanged. Local changes: resolve the template inside this skill, clarify typography and Codex integration. No entire source checkout is included.

## License declaration

The upstream README declares `MIT` under License, and registry/skills.json declares `MIT` for research-gap. No LICENSE/COPYING file was present in the inspected source revision. This records the upstream declaration without inventing a copyright holder or license text. Obtaining a complete upstream copyright/license notice remains outstanding.

## Runtime dependencies and limits

No Python or Node packages are needed to read this skill. Actual literature analysis needs authorized HTTPS access to api.semanticscholar.org and api.openalex.org, current API authentication/quota where required, and verified retrieved records. This installation does not supply credentials or establish API readiness.
HTML reports use the bundled CSS; Google Fonts (fonts.googleapis.com / fonts.gstatic.com) are optional and have local fallbacks. Interactive trends require Chart.js (for example cdn.jsdelivr.net); it is not bundled. For offline reports provide a local chart asset or static chart from actual data and document the deviation. No report or live literature analysis was executed during installation.
`lit-search` is not installed. No other paperskills skills were copied. Report opening remains subject to explicit user confirmation as the upstream workflow requires.
