# Project research-writing skills

Codex project-local skills live in this directory. Invoke `$good-story`, `$research-gap` or `$scientific-writing` in a task with the relevant source material. Existing checkouts are isolated per cloud task; reuse this checkout and do not create a worktree unless explicitly requested. No package installation or service startup is needed for these Markdown skills. New cloud tasks must include the merged Git revision (or the PR branch) to reuse this installation.

| Skill | Installed resources | Source revision |
| --- | --- | --- |
| [Good Story](good-story/SKILL.md) | Existing installation preserved, all 44 upstream files | Rimagination/good-story `978c44d977c6934f82923570ddfa0b7b0ef755c3` |
| [Research Gap](research-gap/SKILL.md) | Skill and local shared HTML report template | cocoafun/paperskills `99e7a2ff93ec025697ee8aaf51ddea9d3573cb24` |
| [Scientific Writing](scientific-writing/SKILL.md) | Skill, seven original references, two static section-contract references and license notices | Boom5426/Nature-Paper-Skills `00ecc183dddc5aba23462c1d547d250836122962` |

Only targeted skill resources are installed for the two new skills; no source repository or nested Git checkout is included. Good Story's existing files were not overwritten or removed.

See [Research Gap installation notes](research-gap/INSTALLATION.md) for API access, optional report assets and the missing upstream full license notice. See [Scientific Writing installation notes](scientific-writing/INSTALLATION.md) for the complete list of uninstalled companion skills. A bundled reference from another skill does not install that skill.

## Validation and limits

All three SKILL.md files exist and their YAML parses with nonempty name and description. New skills retain upstream frontmatter verbatim. Installed Markdown links and local resource paths resolve. Good Story's 44 files match the previous local main commit byte-for-byte. The optional nature-figure reference is explicitly excluded from installed-resource claims.

These checks establish local file integrity, not successful live API analysis, an end-to-end writing evaluation, figure generation or LaTeX rendering. Good Story's PowerShell validation scripts were not run because PowerShell is unavailable. Research Gap needs authorized literature API access at execution time; credentials and quotas have not been verified. Its template specifies different fonts from the old SKILL.md wording; the local integration note makes the bundled template authoritative.

Use verified user materials and retrieved sources. Never invent paper counts, references, experiments or results; missing evidence must remain explicit. Example citations and results in upstream instructional text are illustrative, not verified sources for a manuscript. No research report or manuscript was generated during this installation.
