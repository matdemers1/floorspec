/**
 * Checks the normative JSON Schemas of Floorspec Core 0.1 (FLR-T-1.5) and 0.2, Floorspec Ops 0.1
 * (FLR-T-2.1) and the extension registry entry (Core 0.2, 12.2), FLR-ADR-006:
 *
 *   1. every schema file compiles under ajv's strict mode, and every `required` name is declared;
 *   2. every `default` validates against the subschema it sits in;
 *   3. each Core schema agrees with its suite: for every test whose input is well-formed JSON and
 *      whose expected diagnostics have no FS-CFG-, FS-JSON- or FS-DOC- code, the schema rejects the
 *      input when the expected diagnostics are exactly [FS-SCH-001], and accepts it otherwise. The
 *      0.2 suite is checked as a 0.2 reader checks it - a document declaring "0.1" against 0.1's
 *      schema (FS-CORE-1.2.4) - and its registry.json files against the registry entry schema;
 *   4. the Ops request schema agrees with the Ops suite: it rejects a test's request exactly when
 *      the expected diagnostics are [FS-OPS-001]; and every document A that a test treats as valid
 *      matches the Core schema.
 *
 *   pnpm schema:check
 */
import { join } from 'node:path';
import {
  CORE_VERSIONS,
  checkOpsSuite,
  checkSuite,
  coreRootId,
  coreSchemaDir,
  createAjv,
  REGISTRY_ID,
  registrySchemaDir,
  versionedValidator,
  defaults,
  formatErrors,
  loadSchemaFiles,
  opsSchemaDir,
  requestValidator,
  rootValidator,
  undefinedRequired,
  type SchemaFile,
} from './schema.ts';

const root = join(import.meta.dirname, '..');
const problems: string[] = [];

function fail(): never {
  for (const p of problems) console.error(p);
  console.error(`schema check failed: ${problems.length} problem${problems.length === 1 ? '' : 's'}`);
  process.exit(1);
}

function compile(label: string, files: SchemaFile[]) {
  // 1. Compile every file. addSchema only registers a file; getSchema compiles it, resolving every $ref.
  const ajv = createAjv(files);
  for (const f of files) {
    try {
      ajv.getSchema(f.id);
    } catch (e) {
      problems.push(`${label}/${f.file}: does not compile: ${(e as Error).message}`);
    }
  }
  problems.push(...undefinedRequired(files).map((p) => `${label}/${p}`));
  if (problems.length) fail();
  console.log(`schema: ${label}: ${files.length} files compiled`);

  // 2. Every default is valid against its own subschema.
  const found = defaults(files);
  for (const [where, d] of found) {
    try {
      const validate = ajv.compile({ $ref: `${d.id}#${d.pointer}` });
      if (!validate(d.value))
        problems.push(`${label}/${where}: default ${JSON.stringify(d.value)} is invalid: ${formatErrors(validate.errors ?? []).join('; ')}`);
    } catch (e) {
      problems.push(`${label}/${where}: cannot check its default: ${(e as Error).message}`);
    }
  }
  console.log(`schema: ${label}: ${found.size} defaults checked`);
  return ajv;
}

const cores = Object.fromEntries(
  CORE_VERSIONS.map((v) => [v, rootValidator(compile(`core/${v}`, loadSchemaFiles(coreSchemaDir(v))), coreRootId(v))]),
) as Record<(typeof CORE_VERSIONS)[number], ReturnType<typeof rootValidator>>;
const opsAjv = compile('ops', loadSchemaFiles(opsSchemaDir));
const registry = rootValidator(compile('registry/0.1', loadSchemaFiles(registrySchemaDir)), REGISTRY_ID);

// 3. The Core suites: 0.1 as a 0.1 reader checks it, 0.2 as a 0.2 reader does.
for (const v of CORE_VERSIONS) {
  const validate = v === '0.1' ? cores['0.1'] : versionedValidator(cores);
  const suite = checkSuite(join(root, 'conformance', 'core', v), validate, root, v === '0.1' ? undefined : registry);
  problems.push(...suite.problems);
  console.log(
    `schema: core/${v}: ${suite.checked} conformance test${suite.checked === 1 ? '' : 's'} checked against the schema, ` +
      `${suite.skipped} configuration-, parser- or document-tier test${suite.skipped === 1 ? '' : 's'} skipped`,
  );
}

// 4. The Ops suite: requests against the request schema, documents A against the Core 0.1 schema.
const ops = checkOpsSuite(join(root, 'conformance', 'ops', '0.1'), requestValidator(opsAjv), cores['0.1'], root);
problems.push(...ops.problems);
console.log(`schema: ops: ${ops.checked} conformance request${ops.checked === 1 ? '' : 's'} checked against the request schema`);

if (problems.length) fail();
console.log('schema check passed');
