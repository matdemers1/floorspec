<!--
An extension registry pull request (registry/README.md, "Lifecycle"). One extension per pull request,
and one step per pull request: a new extension or version as a Proposal or a Draft, or one version
moved forward one status. Keep the section for the step you are taking and delete the others.
The Registry workflow (tools/registry-gates.ts, `pnpm registry:check`) checks everything marked (CI).
Open this template with ?template=extension.md on the pull request URL.
-->

## Extension

- Name: `<NAME>` <!-- FS_ official, EXT_ multi-implementer, or a reserved vendor prefix of 2-8 capitals or digits -->
- Version: `x.y.z`
- Step: <!-- new Proposal | new Draft | Proposal → Draft | Draft → Release Candidate | Release Candidate → Ratified | new version -->
- Related issue or discussion:

## Proposal (a name reserved)

- [ ] `registry/<NAME>/extension.json`, `"status": "proposal"`, matching the registry entry schema, its `schema` the URL the schema will be published at (CI)
- [ ] `registry/<NAME>/proposal.md`: what it describes, why it is not Core or an existing extension, who means to implement it (CI: present)
- [ ] a row in `registry/README.md`'s table for its prefix, with its version and status (CI)
- [ ] the name is free: no other entry, and not a prefix reserved to someone else

## Draft (specified and changing)

- [ ] `registry/<NAME>/spec.md`: chapter 1 gives conformance, data and units; every `MUST` and `MUST NOT` tagged `{#FS-<CODE>-n.n.n MUST}` in a code no other specification uses (CI: `pnpm statements`)
- [ ] its 1.1 table's `Version` and `Status` rows are the entry's (CI)
- [ ] the schema in `registry/<NAME>/`, its `$id` the entry's `schema`, a URL with a `/<version>/` segment (CI: `pnpm schema:check`, registry gates)
- [ ] the suite `conformance/ext/<NAME>/<version>/` covers every mandatory statement (CI: `pnpm coverage`, registry gates)
- [ ] for an official `FS_` extension: an oracle module in `tools/oracle/ext/` and the suite declared in `tools/oracle/ext_author.py`, reproduced with 0 differences (CI: `python -m tools.oracle.regenerate`)
- [ ] it never changes what Core data means (Core §12.7), and every kind it adds carries a fallback

## Release Candidate (frozen unless implementations find a problem)

- [ ] at least one implementation in the entry's `implementations`, each with evidence in `registry/<NAME>/evidence/<slug>.json` of a run that passed every test of this version's suite (CI)
- [ ] the evidence names the commit of this repository whose suite it ran, and the suite has not changed since (CI: a warning when it has)
- [ ] the conformance oracle is not evidence: it wrote the suite's expected outputs
- [ ] or: an owner's decision recorded in `registry/exceptions.json`, with the condition that ends it (CI)
- [ ] the specification's status banner and 1.1 table say Release Candidate

## Ratified (stable)

- [ ] two or more implementations listed, each with evidence of passing the suite as it is now (CI)
- [ ] two of them independent: different `maintainer`s, and neither names the other in `sharesCodeWith` (CI) — say here how they were written independently:
- [ ] a run of each is public: a CI run linked as `run`, or a report committed beside the evidence
- [ ] after this merges, the schema files, the suite and every entry member but `implementations` are frozen (CI); a change is a new version
- [ ] the schema is published at its URL on the spec site, byte for byte

## Checks

- [ ] `pnpm statements && pnpm schema:check && pnpm coverage && pnpm registry:check`
- [ ] `python3.13 -m tools.oracle.regenerate` (official extensions)
- [ ] a step other than one forward needs a maintainer to add the `registry-maintainer` label, with the reason here:
