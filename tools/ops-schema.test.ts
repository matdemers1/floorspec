import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { formatErrors, OPS_VERSIONS, requestValidator, validateText, type OpsVersion } from './schema.ts';

/**
 * The Ops request schemas against tools/fixtures/ops-requests.json (Ops 0.1, as published) and
 * tools/fixtures/ops-requests-0.2.json (Ops 0.2) - the same cases that
 * tools/oracle/test_ops_request.py runs through the oracle's request check of each draft, so that
 * the two agree on what FS-OPS-001 rejects. A 0.2 case marked `new` uses a form Ops 0.2 adds, so
 * the Ops 0.1 schema rejects it whatever 0.2 says of it.
 */
interface Case {
  name: string;
  malformed: boolean;
  new?: boolean;
  new03?: boolean;
  request: unknown;
}
// Ops 0.3's requests have Ops 0.2's shape and may add an element to Core 0.3's `roofs` (Ops 0.4): its cases are
// 0.2's, with "unknown collection" naming a name that is still reserved and a case adding a roof.
const FIXTURES: Record<OpsVersion, string> = { '0.1': 'ops-requests.json', '0.2': 'ops-requests-0.2.json', '0.3': 'ops-requests-0.3.json' };
const load = (v: OpsVersion) => JSON.parse(readFileSync(join(import.meta.dirname, 'fixtures', FIXTURES[v]), 'utf8')) as Case[];
const validators = Object.fromEntries(OPS_VERSIONS.map((v) => [v, requestValidator(undefined, v)]));

for (const v of OPS_VERSIONS)
  for (const c of load(v))
    test(`ops ${v} request: ${c.name} is ${c.malformed ? 'malformed' : 'well formed'}`, () => {
      const validate = validators[v]!;
      const valid = validate(c.request) as boolean;
      assert.equal(valid, !c.malformed, valid ? 'the schema accepts it' : formatErrors(validate.errors ?? []).join('\n'));
    });

for (const c of load('0.2').filter((x) => x.new))
  test(`ops 0.1 request: ${c.name} is malformed, since only 0.2 has that form`, () => {
    assert.equal(validators['0.1']!(c.request), false);
  });

for (const v of OPS_VERSIONS) {
  test(`ops ${v} request: a length written 2.0 is not an integer`, () => {
    const validate = validators[v]!;
    const r = validateText('{ "batch": [{ "op": "moveWall", "wall": "W1", "by": 2.0 }] }', validate);
    assert.equal(r.valid, false);
    assert.equal(validateText('{ "batch": [{ "op": "moveWall", "wall": "W1", "by": 2 }] }', validate).valid, true);
  });

  test(`ops ${v} request: a value may be any JSON, including numbers with fractions`, () => {
    assert.equal(validateText('{ "batch": [{ "op": "setProperty", "id": "R1", "path": "/extras/k", "value": 1.0 }] }', validators[v]!).valid, true);
  });
}

test('ops 0.2 request: an area written 1.5 is not an integer, but "1.5 m2" is an area', () => {
  const validate = validators['0.2']!;
  assert.equal(validateText('{ "batch": [{ "op": "addProgramItem", "function": "bedroom", "minArea": 1.5 }] }', validate).valid, false);
  assert.equal(validateText('{ "batch": [{ "op": "addProgramItem", "function": "bedroom", "minArea": "1.5 m2" }] }', validate).valid, true);
});

for (const c of load('0.3').filter((x) => x.new03))
  test(`ops 0.2 request: ${c.name} is malformed, since only 0.3 has that form`, () => {
    assert.equal(validators['0.2']!(c.request), false);
  });
