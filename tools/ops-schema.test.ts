import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { formatErrors, requestValidator, validateText } from './schema.ts';

/**
 * The Ops 0.1 request schema against tools/fixtures/ops-requests.json - the same cases that
 * tools/oracle/test_ops_request.py runs through the oracle's request check, so that the two
 * agree on what FS-OPS-001 rejects.
 */
const validate = requestValidator();
const cases = JSON.parse(readFileSync(join(import.meta.dirname, 'fixtures', 'ops-requests.json'), 'utf8')) as {
  name: string;
  malformed: boolean;
  request: unknown;
}[];

for (const c of cases)
  test(`ops request: ${c.name} is ${c.malformed ? 'malformed' : 'well formed'}`, () => {
    const valid = validate(c.request) as boolean;
    assert.equal(valid, !c.malformed, valid ? 'the schema accepts it' : formatErrors(validate.errors ?? []).join('\n'));
  });

test('ops request: a length written 2.0 is not an integer', () => {
  const r = validateText('{ "batch": [{ "op": "moveWall", "wall": "W1", "by": 2.0 }] }', validate);
  assert.equal(r.valid, false);
  assert.equal(validateText('{ "batch": [{ "op": "moveWall", "wall": "W1", "by": 2 }] }', validate).valid, true);
});

test('ops request: a value may be any JSON, including numbers with fractions', () => {
  assert.equal(validateText('{ "batch": [{ "op": "setProperty", "id": "R1", "path": "/extras/k", "value": 1.0 }] }', validate).valid, true);
});
