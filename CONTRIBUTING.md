# Contributing to Floorspec

## Normative statements
Every normative statement uses RFC 2119 / RFC 8174 keywords and carries a stable ID
(e.g. `{#FS-CORE-5.2.1 MUST}`). A MUST without a conformance test fails CI.

## Extensions
Propose an extension by pull request under `registry/<PREFIX>_<name>/` with a schema, conformance
files and a description. Lifecycle: Proposal → Draft → Release Candidate → Ratified. Ratification
requires two independent implementations passing the extension's conformance tests.

## Rule packs — read this before contributing a rule
- **Never copy code text.** No sentences, no tables, no figures from ICC, NFPA, IAPMO, ANSI or any
  other publisher. Write your own paraphrase.
- **Cite precisely:** code, edition, section, and a link to the publisher's free viewer.
- **Never scrape** a code publisher's website or use automated extraction against it.
- Numeric thresholds go in as individual values with provenance (who verified, against which
  edition, when).
- By submitting a rule you certify that its paraphrase is your original work.
