# Contributing to Floorspec

## Normative statements
Every normative statement uses RFC 2119 / RFC 8174 keywords and carries a stable ID
(e.g. `{#FS-CORE-5.2.1 MUST}`). A MUST without a conformance test fails CI.

## Extensions
Propose an extension by pull request under `registry/<PREFIX>_<name>/`, using the extension
template (add `?template=extension.md` to the pull request's URL): a Proposal is its entry and a
written rationale, `proposal.md`. Lifecycle: Proposal → Draft → Release Candidate → Ratified, one
step per pull request. A Draft adds a specification, a schema at a versioned URL and a conformance
suite covering every MUST; a Release Candidate an implementation with evidence of passing the
suite; Ratified two independent implementations with evidence. `pnpm registry:check` runs the gates
CI runs; [registry/README.md](registry/README.md) has the rules, the evidence format and who decides.

## Rule packs — read this before contributing a rule
**The full rules, the certification every rule carries, and the checklist are in
[rules/CONTRIBUTING.md](rules/CONTRIBUTING.md); the format is in [rules/README.md](rules/README.md).** In short:

- **Never copy code text.** No sentences, no tables, no figures from ICC, NFPA, IAPMO, ANSI or any
  other publisher. Write your own paraphrase.
- **Cite precisely:** code, edition, section, and a link to the publisher's free viewer.
- **Never scrape** a code publisher's website or use automated extraction against it.
- Numeric thresholds go in as individual values with provenance (who verified, against which
  edition, when).
- Every rule names you and the certification `original-paraphrase-v1`: by submitting it you certify
  that its paraphrase is your original work. `pnpm packs` must pass.
