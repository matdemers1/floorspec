# Rule packs

A **rule pack** is versioned data, licensed CC BY 4.0: a set of advisory rules, each citing one
section of one edition of a building code, with the contributor's own paraphrase, a link to the
publisher's free public viewer, and a record of who verified it, against which edition, when, and
whether a licensed professional has reviewed it (FLR-ADR-011). A pack never contains a code's
text, tables or figures, and nothing in this repository ever scrapes or fetches a code viewer.

Floorspec findings are advisory. They are not a plan review, and the authority having jurisdiction
decides.

- **Contributing a rule:** read [CONTRIBUTING.md](CONTRIBUTING.md) first. Every rule carries your
  certification that its wording is your own.
- **What each pack covers:** [COVERAGE.md](COVERAGE.md) across every published pack, and
  `<pack>/generated/COVERAGE.md` for one.
- **What an evaluator reads:** the pack object of Floorspec Rules chapter 2
  ([spec/rules/02-packs.md](../spec/rules/02-packs.md)), built from the files described here.

> [!note] Status
> The pack format is 0.x Draft, like Floorspec Rules 0.2, whose packs it builds. `example/` is the only pack so far; it
> cites the synthetic codes `TEST-CODE` and `TEST-ELEC`, which stand for no real code.

## Layout

```text
rules/
  README.md               this file
  CONTRIBUTING.md         the contributor rules and the certification
  viewers.json            the publishers' free public viewers a citation may link to
  COVERAGE.md             the coverage matrix of every non-synthetic pack (generated)
  coverage.json           the same matrix as JSON (generated)
  <pack>/
    pack.json             the manifest
    documents/<doc>.json  Floorspec documents fixtures share (optional)
    rules/<RULE-ID>/
      rule.json           one rule
      fixtures/<slug>/
        expect.json       what the rule does on the fixture's document
        document.json     the document, unless expect.json names a shared one
    generated/            written by `pnpm packs`; never edit by hand
      pack.json           the pack object an evaluator reads (canonical JSON)
      coverage.json       this pack's coverage matrix
      COVERAGE.md         the same, as Markdown
```

The directory name is the pack's `name`; a rule's directory name is its rule ID (Floorspec Rules
2.1). Each file has a schema in [`schema/rules/0.2/`](../schema/rules/0.2/), the current draft's:

| File | Schema |
|---|---|
| `pack.json` | `pack-manifest.schema.json` |
| `rules/<ID>/rule.json` | `pack-rule.schema.json` |
| `fixtures/<slug>/expect.json` | `pack-fixture.schema.json` |
| `generated/pack.json` | `pack.schema.json`, the evaluator's, unchanged |

## The manifest

| Member | Required | Meaning |
|---|---|---|
| `floorspecRules` | yes | `"0.2"`: a pack targets the current draft, and an evaluator of one draft reads no other's packs (Floorspec Rules 2.1) |
| `name`, `version`, `title`, `description` | all but `description` | as the pack object's (Floorspec Rules 2.1); `version` is Semantic Versioning |
| `license` | yes | `"CC-BY-4.0"`, always |
| `attribution` | yes | the attribution a reuser gives: who made the pack, its name and version, where it is published |
| `jurisdiction` | yes | where the pack is meant to apply, in words |
| `editions` | yes | every `{ code, edition, title? }` a rule or coverage entry cites, and no other |
| `maintainers` | yes | `{ name, url? }`: who answers for the pack |
| `synthetic` | no | `true` for an example or test pack citing only `TEST-` codes; left out of `COVERAGE.md` |
| `domains` | yes | `{ id, title }`: the subject areas the matrix summarises by — egress, receptacles |
| `coverage` | yes | Floorspec Rules 2.4's entries, each with its `domain` and, for what waits on data Core lacks, `needs`: the deferred measures (Rules 4.8) it waits on |
| `extras` | no | as Core §1.7; never a `packFormat` member |

## A rule

`rule.json` is the evaluator's rule record (Floorspec Rules chapter 3) with two differences:
`citation.link` — the **viewer link** — is required, and `provenance` is the full record.

| `provenance` member | Required | Meaning |
|---|---|---|
| `verifiedBy`, `verifiedOn`, `edition` | yes | who checked the rule against the cited section, when, and against which edition — the cited one |
| `method` | yes | `freePublicViewer` (read by a person in the publisher's free public viewer), `ownedCopy` (read in a copy the verifier lawfully holds) or `synthetic` (a synthetic pack) |
| `certifiedBy` | yes | the contributor who wrote the wording and certifies it |
| `certification` | yes | `"original-paraphrase-v1"`: the certification of [CONTRIBUTING.md](CONTRIBUTING.md), by version |
| `review` | yes | `{ "status": "unreviewed" }`, or the **reviewed badge** `{ "status": "reviewed", by, on, credential, scope? }` from a licensed professional (FLR-REQ-104, FLR-REQ-164) |
| `note` | no | anything the verifier wants a reader to know |
| `lintOverrides` | no | a heuristic lint finding a reviewer accepted: `{ check, reviewer, on, note }` |

Thresholds are individual integer values in the rule's tests, in Floorspec's units (lengths in
1/1280 mm, areas in square base units) — never a table.

## Fixtures

Every rule has fixtures: Floorspec documents and what the rule is expected to do on them.

| `outcome` | Expects |
|---|---|
| `pass` | the rule is evaluated, has at least one subject (or exactly `subjects`), and no finding |
| `fail` | the rule is evaluated, and its findings are on exactly the subjects in `findings` |
| `deferred` | the rule uses a deferred measure and is not evaluated (`FS-RULES-008`) |

A rule needs a passing and a failing fixture; a rule on a deferred measure needs a deferred one
instead. `extensions` limits the official extensions the evaluator knows (default: all of
`registry/`). The build evaluates every fixture with the oracle (`tools/oracle/rules`, through
`tools/pack_fixtures.py`) under a profile that adopts the rule's cited edition, and fails on any
difference. When the reference implementation's engine lands, it runs the same fixtures.

## Building

```sh
pnpm packs             # schemas, lint, assembly, fixtures, matrices; writes generated/ and COVERAGE.md
pnpm packs:check       # the same, writing nothing; fails if a generated file differs (CI)
pnpm lint:rules        # the lint alone
pnpm coverage:matrix   # the matrices alone (--check to compare)
```

The oracle runs under `$FLOORSPEC_PYTHON`, else `python3.13`, else `python3`; `--skip-fixtures`
builds without it. Assembly is deterministic: the same files give the same bytes.

What the evaluator's pack object has no member for travels in `extras.packFormat`, which an
evaluator ignores:

| On disk | In `generated/pack.json` |
|---|---|
| `citation.link` | `citation.link` |
| `provenance.verifiedBy`, `verifiedOn`, `edition`, `note` | the same |
| `provenance.review` reviewed: `by`, `on`, `credential` | `provenance.reviewed` — the badge an evaluator carries |
| `provenance.review` unreviewed | no `provenance.reviewed`; `extras.packFormat.review` is `"unreviewed"` |
| `provenance.method`, `certifiedBy`, `certification`, review `scope`, `lintOverrides` | the rule's `extras.packFormat` |
| manifest `attribution`, `jurisdiction`, `editions`, `maintainers`, `synthetic`, `domains` | the pack's `extras.packFormat` |
| coverage entry `domain`, `needs` | `extras.packFormat.coverage`, by the entry's index |

## The coverage matrix

The matrix lists every coverage entry a pack declares — code × edition × section — with the rules
that check it, their reviewed badges and verification dates, and a status:

| Status | When |
|---|---|
| covered | declared `addressed`, and every rule within it is evaluated |
| partial | declared `partial`; or `addressed` with some of its rules on deferred measures |
| deferred (needs data) | every rule within it uses a deferred measure, or it is declared `notAddressed` with `needs` — the measures are named |
| not covered | declared `notAddressed`, waiting on nothing named |

A rule belongs to the most specific entry its section falls within (`R310` holds `R310.2.1`). The
matrix also summarises each domain: sections by status, rules, how many are reviewed, and the
oldest and newest verification. A section a pack does not list is one it does not check: the
matrix is how a reader tells "no finding" from "not checked" (FLR-REQ-096).

## Lint

`pnpm lint:rules` (and every build) checks what the schemas cannot. These never yield:
`assurance` (the pattern of Rules 2.5, in every text of the pack), `paraphrase-length` (40–1200
characters, at least 8 words), `viewer-host` (https, a host in `viewers.json` that publishes the
cited code; `example.org` or `example.com` in a synthetic pack), `provenance` (the verified edition
is the cited one; method `synthetic` exactly in a synthetic pack), `edition-declared`,
`synthetic-code` (`TEST-` codes exactly in synthetic packs), `coverage`, `fixtures`,
`stale-override`, and `no-automation` (no script under `tools/`, `rules/` or `.github/` names a
viewer host).

These are heuristics, and a reviewer may accept a finding with a note in `lintOverrides`:
`advice-wording` (pass, satisfies, conforms, approved, guaranteed), `verbatim-shall`,
`verbatim-quote` (a quoted span of six words or more), `verbatim-sections` (three or more section
numbers), `verbatim-table` (a pipe, a tab, a line starting with a number, or six or more numbers),
`verbatim-structure` (an "Exception:" label, numbered items) and `verbatim-sentence` (more than 50
words). No heuristic can prove wording original — the certification does — but they catch the
common accidents. `tools/lint-rules.ts` documents each.

## Versions

A pack's `version` is Semantic Versioning: a patch release for re-verification, corrected wording
and new fixtures; a minor release for new rules or coverage; a major release when a rule is removed
or what it checks changes. A rule cites one edition: a new edition of a code is new rules, often in
a new pack version, never an edit of the old edition's rules.

## Related

FLR-ADR-011 (code rules as cited data), FLR-ADR-026 (Floorspec Rules 0.1), FLR-REQ-094,
FLR-REQ-095, FLR-REQ-096, FLR-REQ-104, FLR-REQ-106, FLR-REQ-163, FLR-REQ-164, FLR-T-6.3.
