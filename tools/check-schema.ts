/**
 * Checks the normative JSON Schemas of Floorspec Core 0.1 (FLR-T-1.5) and 0.2, Floorspec Ops 0.1
 * (FLR-T-2.1) and 0.2, and the extension registry entry (Core 0.2, 12.2), FLR-ADR-006:
 *
 *   1. every schema file compiles under ajv's strict mode, and every `required` name is declared;
 *   2. every `default` validates against the subschema it sits in;
 *   3. each Core schema agrees with its suite: for every test whose input is well-formed JSON and
 *      whose expected diagnostics have no FS-CFG-, FS-JSON- or FS-DOC- code, the schema rejects the
 *      input when the expected diagnostics are exactly [FS-SCH-001], and accepts it otherwise. The
 *      0.2 suite is checked as a 0.2 reader checks it - a document declaring "0.1" against 0.1's
 *      schema (FS-CORE-1.2.4) - and its registry.json files against the registry entry schema;
 *   4. each Ops request schema agrees with its suite: it rejects a test's request exactly when the
 *      expected diagnostics are [FS-OPS-001]; and every document A that a test treats as valid
 *      matches the Core schema of the draft that Ops draft operates on - Ops 0.1's documents
 *      Core 0.1's, Ops 0.2's as a Core 0.2 reader checks them (a "0.1" document against 0.1's).
 *
 *   5. every extension in registry/ - its entry, its schema, and its suite (conformance/ext/), as
 *      checkExtensionSuite says;
 *   6. the Floorspec Rules schemas (schema/rules/<v>/) - the default profile of spec/rules 10.6 matches
 *      the profile schema, and the Rules suite (conformance/rules/<v>/) agrees with them, as
 *      checkRulesSuite says.
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
  checkExtensionSuite,
  checkRulesSuite,
  defaultProfile,
  extensionSchemas,
  RULES_VERSIONS,
  rulesSchemaDir,
  rulesValidators,
  formatErrors,
  loadSchemaFiles,
  OPS_CORE,
  OPS_VERSIONS,
  opsSchemaDirOf,
  requestValidator,
  rootValidator,
  undefinedRequired,
  type SchemaFile,
} from './schema.ts';
import { extensionSpecs } from './statements.ts';

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
const opsAjv = Object.fromEntries(OPS_VERSIONS.map((v) => [v, compile(`ops/${v}`, loadSchemaFiles(opsSchemaDirOf(v)))]));
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

// 4. The Ops suites: requests against their draft's request schema, documents A against the Core
// schema of the draft it operates on.
for (const v of OPS_VERSIONS) {
  const core = OPS_CORE[v] === '0.1' ? cores['0.1'] : versionedValidator(cores);
  const ops = checkOpsSuite(join(root, 'conformance', 'ops', v), requestValidator(opsAjv[v], v), core, root);
  problems.push(...ops.problems);
  console.log(`schema: ops/${v}: ${ops.checked} conformance request${ops.checked === 1 ? '' : 's'} checked against the request schema`);
}

// 5. Every extension in registry/ (registry/<NAME>/): its entry matches the registry entry schema,
// its schema compiles and is the one the entry names, and its suite (conformance/ext/<NAME>/<v>/)
// agrees with it - documents with Core 0.2's schema, registry.json with the entry schema, the
// extension's data with its own schema, Ops requests with Ops 0.2's.
const CODES = Object.fromEntries(extensionSpecs(root).specs.map((x) => [x.name, x.code]));
for (const x of extensionSchemas(root)) {
  if (!registry(x.entry)) problems.push(`registry/${x.name}/extension.json does not match the registry entry schema:\n    ${formatErrors(registry.errors ?? []).join('\n    ')}`);
  const own = x.files.find((f) => f.id === x.entry.schema);
  if (!own) {
    problems.push(`registry/${x.name}: no schema file has the $id ${String(x.entry.schema)} that its entry names`);
    continue;
  }
  const ajv = compile(`registry/${x.name}`, x.files);
  const validateData = ajv.getSchema(own.id)!;
  const suiteDir = join(root, 'conformance', 'ext', x.name, x.version);
  const docs = checkSuite(suiteDir, versionedValidator(cores), root, registry);
  problems.push(...docs.problems);
  const code = CODES[x.name];
  if (!code) {
    problems.push(`registry/${x.name}: has no spec.md, so its statement and diagnostic code is not known`);
    continue;
  }
  const data = checkExtensionSuite(suiteDir, x.name, code, validateData, requestValidator(opsAjv['0.2'], '0.2'), root);
  problems.push(...data.problems);
  console.log(`schema: ${x.name} ${x.version}: ${docs.checked} documents checked against Core's schema, ${data.checked} against the extension's or Ops's`);
}

// 6. Floorspec Rules: its schemas, the default profile of 10.6, and its suite.
for (const v of RULES_VERSIONS) {
  const rv = rulesValidators(compile(`rules/${v}`, loadSchemaFiles(rulesSchemaDir(v))), v);
  const profile0 = defaultProfile(root);
  if (!rv.profile(profile0)) problems.push(`spec/rules/10-profiles.md: the default profile does not match the profile schema:\n    ${formatErrors(rv.profile.errors ?? []).join('\n    ')}`);
  const rules = checkRulesSuite(join(root, 'conformance', 'rules', v), rv, versionedValidator(cores), registry, profile0, root);
  problems.push(...rules.problems);
  console.log(`schema: rules/${v}: ${rules.checked} conformance tests checked against the request, profile, pack, report and Core schemas`);
}

if (problems.length) fail();
console.log('schema check passed');
