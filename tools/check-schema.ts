/**
 * Checks the normative JSON Schema of Floorspec Core 0.1 (FLR-T-1.5, FLR-ADR-006):
 *
 *   1. every schema file compiles under ajv's strict mode, and every `required` name is declared;
 *   2. every `default` validates against the subschema it sits in;
 *   3. the schema agrees with the conformance suite: for every test whose input is well-formed
 *      JSON and whose expected diagnostics have no FS-JSON- or FS-DOC- code, the schema rejects the
 *      input when the expected diagnostics are exactly [FS-SCH-001], and accepts it otherwise.
 *
 *   pnpm schema:check
 */
import { join } from 'node:path';
import { checkSuite, createAjv, defaults, formatErrors, loadSchemaFiles, rootValidator, undefinedRequired } from './schema.ts';

const root = join(import.meta.dirname, '..');
const problems: string[] = [];

function fail(): never {
  for (const p of problems) console.error(p);
  console.error(`schema check failed: ${problems.length} problem${problems.length === 1 ? '' : 's'}`);
  process.exit(1);
}

// 1. Compile every file. addSchema only registers a file; getSchema compiles it, resolving every $ref.
const files = loadSchemaFiles();
const ajv = createAjv(files);
for (const f of files) {
  try {
    ajv.getSchema(f.id);
  } catch (e) {
    problems.push(`${f.file}: does not compile: ${(e as Error).message}`);
  }
}
problems.push(...undefinedRequired(files));
if (problems.length) fail();
console.log(`schema: ${files.length} files compiled`);

// 2. Every default is valid against its own subschema.
const found = defaults(files);
for (const [where, d] of found) {
  try {
    const validate = ajv.compile({ $ref: `${d.id}#${d.pointer}` });
    if (!validate(d.value))
      problems.push(`${where}: default ${JSON.stringify(d.value)} is invalid: ${formatErrors(validate.errors ?? []).join('; ')}`);
  } catch (e) {
    problems.push(`${where}: cannot check its default: ${(e as Error).message}`);
  }
}
console.log(`schema: ${found.size} defaults checked`);

// 3. The conformance suite.
const suite = checkSuite(join(root, 'conformance', 'core', '0.1'), rootValidator(ajv), root);
problems.push(...suite.problems);
console.log(
  `schema: ${suite.checked} conformance test${suite.checked === 1 ? '' : 's'} checked against the schema, ` +
    `${suite.skipped} parser- or document-tier test${suite.skipped === 1 ? '' : 's'} skipped`,
);

if (problems.length) fail();
console.log('schema check passed');
