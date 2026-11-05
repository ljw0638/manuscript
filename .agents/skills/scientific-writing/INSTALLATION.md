# Scientific Writing installation

Source: https://github.com/Boom5426/Nature-Paper-Skills
Commit: 00ecc183dddc5aba23462c1d547d250836122962
Installed: skills/core/scientific-writing/SKILL.md and all seven original references.
Additional static dependencies: paper-workflow/references/section-contracts.md and section-evidence.md, bundled in references/. References in SKILL.md, imrad_structure.md and editor-first-impression.md now resolve locally. Original YAML metadata is unchanged. These are the only modified upstream files; project-local integration notes were appended to SKILL.md.

## Licenses

LICENSE (MIT), LICENSE-APACHE, NOTICE and ATTRIBUTION.md are preserved verbatim. The LaTeX layout reference incorporates Apache-2.0 material; see the upstream notices. Those repository-wide notices mention components that are not installed here.

## Extensions not installed

- paper-workflow: only its two static reference files are bundled, not its Skill.
- nature-figure: optional schematic generation; its script and openrouter-image-generation.md are absent. The example command cannot run here. Requires its own plotting backend or authorized OPENROUTER_API_KEY when separately installed.
- write-scientific-manuscript: semantic and paragraph workflows; section-logic.md is not bundled.
- anti-defensive-writing: specialist revision guidance.
- figure-planner: figure planning and legend rules.
- nature-portfolio-playbook: journal-specific checks.
- conference-paper-writing: conference-specific structure.
- manuscript-optimizer: claim architecture review.
- claim-source-verification: source verification workflow.
- results-section-revision: results revision workflow.
- stats-reporting-audit: statistical audits; figure-statistics.md is not bundled.
- data-availability: specialist availability statements.

These are optional companion workflows referenced by the skill or bundled section contracts, not claims of installed functionality. Use the local scientific-writing references for standalone work and disclose unperformed specialist checks.
The evidence notes cite the upstream scripts/section_corpus.py for provenance; that corpus/audit script is not installed and its reported counts were not independently reproduced.
No packages or API keys are needed to read and use the writing guidance. Rendering LaTeX or generating figures requires separately chosen tools; neither was installed or tested here. No manuscript, experiment results or bibliography was generated.
