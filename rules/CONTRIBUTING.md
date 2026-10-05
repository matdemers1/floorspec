# Contributing a rule

Rule packs are the part of Floorspec most exposed to two risks: copying a code publisher's text,
and claiming more than a rule can know. These rules exist for both. Read them before your first
rule; the build enforces what it can, and your certification covers the rest.

The format itself — files, members, fixtures, the build — is in [README.md](README.md).

## 1. Never copy, never scrape

- **Never copy a code's text.** No sentence, clause, table, figure, list or definition from the
  ICC, NFPA, IAPMO, ANSI or any other publisher — not verbatim, not lightly edited, not
  machine-translated, not rearranged. That holds for a rule's title and paraphrase, exception
  notes, provenance notes and coverage notes, and for issues, pull requests and commit messages.
- **Never reproduce a table.** A threshold enters a pack as an individual value in a rule's test,
  with its citation and provenance. A table's values are not transcribed into a pack, a fixture
  or prose, even in your own layout.
- **Never scrape.** Do not scrape, crawl, bulk-download, or use any automated extraction against
  the ICC or NFPA code viewers or any other publisher's site (FLR-REQ-106). That includes scripts,
  browser automation, download managers, and AI agents or tools told to fetch or read viewer
  pages. A person reads the section in a browser; nothing else touches the viewer.
- **No second-hand text.** Sites that republish code text are not a source either. Read the
  publisher's own free public viewer, or a copy you lawfully hold.
- A viewer link in a rule is a link for readers. Nothing in this repository fetches it, and the
  lint fails any script that names a viewer host.

## 2. The certification

Every rule's provenance names you and this certification:

```json
"certifiedBy": "Your Name",
"certification": "original-paraphrase-v1"
```

By setting those two members on a rule, you certify, as of `original-paraphrase-v1`:

1. The rule's title, paraphrase, exception notes and notes are my own original wording.
2. I did not copy, closely imitate, rearrange or machine-translate any part of the code's text,
   and I did not reproduce any table, figure or list from it.
3. I read the cited section myself, by the method the rule records, and did not obtain it by
   scraping, bulk download or any automated extraction.
4. The numeric thresholds are individual values I read in that section, entered in the rule's
   tests; they are not a transcribed table.
5. If a tool helped me draft the wording, I did not give it the code's text, and I have read the
   result and take it as my own.
6. I license my contribution to the rule packs under the Creative Commons Attribution 4.0
   International licence (CC BY 4.0), and have the right to do so.

The schema refuses a rule without `certifiedBy` and this exact `certification`, so CI checks that
every rule carries it. If the wording of this section changes, its version changes too, and new
rules name the new version.

## 3. Verifying a rule

1. Open the cited section in the **publisher's free public viewer**, in your own browser, by hand.
   The hosts a link may use are in [viewers.json](viewers.json); adding one is a maintainer's
   decision, in a pull request of its own.
2. Read the section, then close it. Write the paraphrase from your understanding, not with the
   text beside you: what the requirement applies to, what it asks, how the rule measures it, and
   what the rule does not check.
3. Enter each threshold as a value in Floorspec's units (lengths in 1/1280 mm, Core §2.1; areas in
   square base units), and say in the paraphrase what it is in plain units.
4. Record the provenance: `verifiedBy`, `verifiedOn` (the day you read it), `edition` (the cited
   edition — the build refuses another), and `method` — `freePublicViewer` or `ownedCopy`.
5. Set `citation.link` to the section in the viewer.
6. Add fixtures: a document the rule finds nothing in, and one it flags, with the subjects it
   flags. A rule on a deferred measure gets a deferred fixture instead.
7. Add or update the manifest's coverage entry for the section: `addressed`, `partial` with a note
   on what is left out, or `notAddressed` — with `needs` when what is missing is data Floorspec
   Core does not have yet.
8. Run `pnpm packs`, and commit the generated files with your change.

Re-verifying a rule later — against the same edition — updates `verifiedBy` and `verifiedOn`.

## 4. Writing the paraphrase

- Say what the requirement **asks**, never that a design meets it. A pack is advice: the assurance
  pattern of Floorspec Rules 2.5 (*complies*, *compliant*, *meets code*, *up to code*, *code
  approved* and their kin) fails the build in any text of a pack, and so does grading wording such
  as *passes*, *satisfies* or *conforms* unless a reviewer accepts it.
- Plain words. "Shall" is the code's word; write "needs", "is at least", "has".
- No quotation marks around the code's words, no section-number chains, no numbered lists or
  "Exception:" labels copied from the code's structure, no tables.
- 40 to 1200 characters, at least 8 words; one requirement per rule.
- Name what the rule cannot see: "it measures the rough opening, not the net clear opening".

## 5. Reviewed badges

A **reviewed badge** records that a licensed professional reviewed the rule (FLR-REQ-104):

```json
"review": { "status": "reviewed", "by": "Their Name", "on": "2026-10-05",
            "credential": "Licensed architect (ME)", "scope": "The paraphrase, thresholds and fixtures." }
```

- **Who:** a person licensed for the domain — an architect or engineer, a licensed trade
  (electrician, plumber, mechanical) for their trade's rules, or a code official. `credential`
  names the licence and where it is held.
- **What:** they read the rule against the cited section and confirm its citation, paraphrase,
  thresholds, applicability, exceptions and fixtures. `scope` says what they looked at.
- **How it is recorded:** the reviewer adds the badge in a pull request themselves, or a
  maintainer adds it from the reviewer's written confirmation, kept with the pull request. A
  contributor never adds a badge for their own review unless they hold the credential.
- **When it lapses:** any change to what a rule checks — its citation, applicability, selection,
  requirement, exceptions, or the substance of its paraphrase — sets `review` back to
  `{ "status": "unreviewed" }` in the same change. Wording fixes and re-verification do not.
- Every other rule is marked `{ "status": "unreviewed" }` (FLR-REQ-164). A badge is not a
  guarantee: findings stay advisory, and the authority having jurisdiction decides.

## 6. Lint overrides

The verbatim heuristics are deliberately strict, and sometimes wrong — a defined term may need a
code's word. A reviewer other than the rule's contributor reads the flagged text against the
viewer and, if the wording is original, records:

```json
"lintOverrides": [{ "check": "verbatim-shall", "reviewer": "Their Name", "on": "2026-10-05",
                    "note": "Why the wording is ours and has to stay." }]
```

Only the heuristics can be overridden — never the assurance pattern, the viewer list, the
provenance or the coverage checks. An override for a check that no longer fires fails the build:
remove it.

## 7. Checklist

- [ ] I read the cited section myself, in the publisher's free public viewer or my own copy; no
      scraping, no automation, no second-hand text.
- [ ] The title, paraphrase and notes are my own wording, written without the text beside me.
- [ ] No quotation, table, figure, list or section chain from the code; thresholds are values.
- [ ] `citation` has the code, edition, section and the viewer `link`.
- [ ] `provenance` has `verifiedBy`, `verifiedOn`, `edition` (the cited one), `method`,
      `certifiedBy`, `"certification": "original-paraphrase-v1"`, and `review`.
- [ ] `review` is `unreviewed`, or a badge from a licensed professional with their credential.
- [ ] A passing and a failing fixture (or a deferred one).
- [ ] The manifest's coverage says what is checked, partly checked, and not checked.
- [ ] No text says a design complies with or meets a code.
- [ ] `pnpm packs` passes, and the generated files are committed.

## 8. Licence

Rule packs, including `viewers.json`, are licensed CC BY 4.0 ([LICENSE-SPEC](../LICENSE-SPEC)).
The tooling that builds and checks them is Apache-2.0 ([LICENSE](../LICENSE)). A pack licenses its
own data — citations, thresholds as individual values, and its contributors' paraphrases — never a
code's text, which is not in a pack to license.
