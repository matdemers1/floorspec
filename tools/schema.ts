/**
 * The normative JSON Schemas (FLR-ADR-006), loaded into ajv: Floorspec Core's document schemas -
 * the schema tier (tier 3, FS-SCH-001) of chapter 10 and nothing else - for each draft (0.1, 0.2
 * and 0.3), Floorspec Ops's apply-request schemas (0.1, 0.2 and 0.3), whose rejections are
 * FS-OPS-001, and the registry entry schema (Core 0.2, 12.2). Used by `pnpm schema:check` and its
 * tests.
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { Ajv2020, type ErrorObject, type ValidateFunction } from 'ajv/dist/2020.js';

/** The Core drafts this repository publishes, oldest first. */
export const CORE_VERSIONS = ['0.1', '0.2', '0.3'] as const;
export type CoreVersion = (typeof CORE_VERSIONS)[number];
/** The draft the spec text in spec/core/ is. */
export const CURRENT_CORE: CoreVersion = '0.3';

export const coreSchemaBase = (v: CoreVersion) => `https://d3cloud.io/floorspec/schema/core/${v}/`;
export const coreRootId = (v: CoreVersion) => `${coreSchemaBase(v)}floorspec.schema.json`;
export const coreSchemaDir = (v: CoreVersion) => join(import.meta.dirname, '..', 'schema', 'core', v);

export const SCHEMA_BASE = coreSchemaBase('0.1');
export const ROOT_ID = coreRootId('0.1');
export const schemaDir = coreSchemaDir('0.1');

export const REGISTRY_ID = 'https://d3cloud.io/floorspec/schema/registry/0.1/extension.schema.json';
export const registrySchemaDir = join(import.meta.dirname, '..', 'schema', 'registry', '0.1');

/** The Ops drafts this repository publishes, oldest first. */
export const OPS_VERSIONS = ['0.1', '0.2', '0.3'] as const;
export type OpsVersion = (typeof OPS_VERSIONS)[number];
/** The draft the spec text in spec/ops/ is. */
export const CURRENT_OPS: OpsVersion = '0.3';
/** The Core draft each Ops draft operates on: its document A is valid under that draft's reader. */
export const OPS_CORE: Record<OpsVersion, CoreVersion> = { '0.1': '0.1', '0.2': '0.2', '0.3': '0.3' };
/** The Ops request schemas, schema/ops/<v>/, oldest first. */
export const OPS_SCHEMA_VERSIONS = ['0.1', '0.2', '0.3'] as const;
export type OpsSchemaVersion = (typeof OPS_SCHEMA_VERSIONS)[number];
/** The request schema each Ops draft's requests match: Ops 0.3's is 0.2's with addElement into Core 0.3's `roofs` and `stairs` (Ops 0.4). */
export const OPS_SCHEMA: Record<OpsVersion, OpsSchemaVersion> = { '0.1': '0.1', '0.2': '0.2', '0.3': '0.3' };

export const opsSchemaBase = (v: OpsSchemaVersion) => `https://d3cloud.io/floorspec/schema/ops/${v}/`;
export const opsRootId = (v: OpsSchemaVersion) => `${opsSchemaBase(v)}request.schema.json`;
export const opsSchemaDirOf = (v: OpsSchemaVersion) => join(import.meta.dirname, '..', 'schema', 'ops', v);

export const OPS_SCHEMA_BASE = opsSchemaBase('0.1');
export const OPS_ROOT_ID = opsRootId('0.1');
export const opsSchemaDir = opsSchemaDirOf('0.1');

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

export interface SchemaFile {
  file: string;
  id: string;
  schema: Record<string, Json>;
}

/** Every `*.schema.json` file of one directory (Core 0.1 by default), sorted by file name. */
export function loadSchemaFiles(dir = schemaDir): SchemaFile[] {
  return readdirSync(dir)
    .filter((f) => f.endsWith('.schema.json'))
    .sort()
    .map((file) => {
      const schema = JSON.parse(readFileSync(join(dir, file), 'utf8')) as Record<string, Json>;
      return { file, id: String(schema.$id), schema };
    });
}

/**
 * `format: "uri"` (RFC 3986): an absolute URI — a scheme, a colon, and only the characters RFC
 * 3986 allows, with every `%` starting a percent-encoding. ajv ships no formats of its own; in
 * JSON Schema 2020-12 `format` is an annotation, and the `pattern` beside it is what every
 * validator checks.
 */
const URI = /^[A-Za-z][A-Za-z0-9+.-]*:(?:[A-Za-z0-9\-._~!$&'()*+,;=:@/?#[\]]|%[0-9A-Fa-f]{2})*$/;
export const isUri = (s: string) => URI.test(s) && URL.canParse(s);

export function createAjv(files = loadSchemaFiles()) {
  // Strict mode, except strictRequired: it rejects the standard "exactly one of" idiom
  // (`oneOf: [{ required: [a] }, { required: [b] }]`, 8.6.1). undefinedRequired() checks the same
  // thing while allowing a branch to name its parent's properties.
  const ajv = new Ajv2020({ strict: true, strictRequired: false, allErrors: true });
  ajv.addFormat('uri', isUri);
  for (const f of files) ajv.addSchema(f.schema, f.id);
  return ajv;
}

export function rootValidator(ajv = createAjv(), id = ROOT_ID): ValidateFunction {
  const validate = ajv.getSchema(id);
  if (!validate) throw new Error(`schema ${id} is not loaded`);
  return validate;
}

/** The validator of one Core draft's document schema. */
export function coreValidator(v: CoreVersion, ajv = createAjv(loadSchemaFiles(coreSchemaDir(v)))): ValidateFunction {
  return rootValidator(ajv, coreRootId(v));
}

/** The validator of a registry entry (Core 0.2, 12.2). */
export function registryValidator(ajv = createAjv(loadSchemaFiles(registrySchemaDir))): ValidateFunction {
  return rootValidator(ajv, REGISTRY_ID);
}

/**
 * The schema tier of a reader of one Core draft (by default the newest of `validators`), which reads
 * every earlier draft too (FS-CORE-1.2.6 of 0.3, 1.2.4 of 0.2): a document that declares a draft
 * the reader implements is checked against that draft's schema, and every other document against
 * the reader's own.
 */
export function versionedValidator(
  validators: Partial<Record<CoreVersion, ValidateFunction>>,
  reader: CoreVersion = CORE_VERSIONS.filter((v) => validators[v]).at(-1)!,
): ValidateFunction {
  const implemented = CORE_VERSIONS.slice(0, CORE_VERSIONS.indexOf(reader) + 1);
  const pick = (doc: unknown) => {
    const declared = doc !== null && typeof doc === 'object' && !Array.isArray(doc) ? (doc as Record<string, unknown>).floorspec : undefined;
    const v = implemented.find((x) => x === declared) ?? reader;
    const f = validators[v];
    if (!f) throw new Error(`no validator for Core ${v}`);
    return f;
  };
  const f = ((doc: unknown) => {
    const v = pick(doc);
    const ok = v(doc) as boolean;
    f.errors = v.errors;
    return ok;
  }) as unknown as ValidateFunction;
  return f;
}

/** The validator of a Floorspec Ops apply request, of one draft (0.1 by default), with that draft's request schema. */
export function requestValidator(ajv?: Ajv2020, v: OpsVersion = '0.1'): ValidateFunction {
  const id = opsRootId(OPS_SCHEMA[v]);
  const validate = (ajv ?? createAjv(loadSchemaFiles(opsSchemaDirOf(OPS_SCHEMA[v])))).getSchema(id);
  if (!validate) throw new Error(`schema ${id} is not loaded`);
  return validate;
}

/**
 * Parses a JSON text as the schema tier sees it. Every length and angle in a Floorspec document is
 * a JSON integer, written without a fraction or an exponent (2.1, 2.4); JSON Schema only sees the
 * parsed number, for which `1.0` is an integer. So every number written with a fraction or an
 * exponent becomes NaN, which fails every `type` in the schema and passes only where any JSON is
 * allowed — inside `extras` and extension data, where any JSON number is valid (9.1). Core 0.1 has
 * no member whose value may be a non-integer number, so this loses nothing.
 */
export function parseForSchema(text: string): unknown {
  return JSON.parse(text, function (this: unknown, _key: string, value: unknown, context?: { source?: string }) {
    if (typeof value !== 'number') return value;
    if (context?.source === undefined) throw new Error('this runtime lacks JSON.parse source text access (Node >= 22)');
    return /[.eE]/.test(context.source) ? Number.NaN : value;
  });
}

export interface SchemaResult {
  valid: boolean;
  errors: ErrorObject[];
}

/** Applies a Core schema (0.1 by default) to a JSON text that is already known to be well formed (9.1). */
export function validateText(text: string, validate = rootValidator()): SchemaResult {
  const valid = validate(parseForSchema(text)) as boolean;
  return { valid, errors: valid ? [] : [...(validate.errors ?? [])] };
}

/** Every subschema carrying a `default`, as `<file>#<JSON Pointer>` → the default. */
export function defaults(files = loadSchemaFiles()): Map<string, { id: string; pointer: string; value: Json }> {
  const found = new Map<string, { id: string; pointer: string; value: Json }>();
  const esc = (k: string) => k.replaceAll('~', '~0').replaceAll('/', '~1');
  // Members whose value maps names to subschemas: a key there is a name, never a keyword.
  const MAPS = ['properties', 'patternProperties', '$defs', 'dependentSchemas'];
  const walk = (file: SchemaFile, node: Json, pointer: string, isMap = false) => {
    if (Array.isArray(node)) node.forEach((n, i) => walk(file, n, `${pointer}/${i}`));
    else if (node !== null && typeof node === 'object') {
      if (!isMap && 'default' in node) found.set(`${file.file}#${pointer}`, { id: file.id, pointer, value: node.default! });
      for (const [k, v] of Object.entries(node)) {
        // In a schema, `default`, `const`, `enum` and `examples` hold instances, not subschemas.
        if (!isMap && ['default', 'const', 'enum', 'examples'].includes(k)) continue;
        walk(file, v, `${pointer}/${esc(k)}`, !isMap && MAPS.includes(k));
      }
    }
  };
  for (const f of files) walk(f, f.schema, '');
  return found;
}

/**
 * Every `required` name that its schema does not declare in `properties` — or, for a branch of
 * `oneOf`, `anyOf` or `allOf`, that the schema owning the branch does not declare. A typo there
 * would make a member impossible to supply, since every object is closed.
 */
export function undefinedRequired(files = loadSchemaFiles()): string[] {
  const found: string[] = [];
  const props = (n: Json | undefined) =>
    n !== null && typeof n === 'object' && !Array.isArray(n) && n.properties && typeof n.properties === 'object'
      ? Object.keys(n.properties)
      : [];
  const walk = (file: SchemaFile, node: Json, pointer: string, owner: Json | undefined) => {
    if (node === null || typeof node !== 'object') return;
    if (Array.isArray(node)) return node.forEach((n, i) => walk(file, n, `${pointer}/${i}`, owner));
    if (Array.isArray(node.required)) {
      const known = new Set([...props(node), ...props(owner)]);
      for (const r of node.required) if (!known.has(String(r))) found.push(`${file.file}#${pointer}: required "${r}" is not a declared property`);
    }
    for (const [k, v] of Object.entries(node)) {
      if (['default', 'const', 'enum', 'examples', 'required'].includes(k)) continue;
      if (['oneOf', 'anyOf', 'allOf'].includes(k)) walk(file, v, `${pointer}/${k}`, node);
      else if (['properties', 'patternProperties', '$defs', 'dependentSchemas'].includes(k) && v !== null && typeof v === 'object' && !Array.isArray(v))
        for (const [name, sub] of Object.entries(v)) walk(file, sub, `${pointer}/${k}/${name}`, undefined);
      else walk(file, v, `${pointer}/${k}`, undefined);
    }
  };
  for (const f of files) walk(f, f.schema, '', undefined);
  return found;
}

export const formatErrors = (errors: ErrorObject[]) =>
  errors.map((e) => `${e.instancePath || '/'} ${e.message ?? e.keyword}${e.params ? ` ${JSON.stringify(e.params)}` : ''}`);

export interface SuiteResult {
  checked: number;
  skipped: number;
  problems: string[];
}

/**
 * Checks the schema against a conformance suite directory (conformance/core/0.1 or 0.2). For every
 * test whose input is well-formed JSON and whose expected diagnostics have no FS-CFG-, FS-JSON- or
 * FS-DOC- code, the schema must reject the input when the expected diagnostics are exactly
 * [FS-SCH-001], and accept it otherwise. A test's registry.json - the known extensions of Core 0.2,
 * 12.2 - must match the registry entry schema, unless the test expects [FS-CFG-001]. A suite that
 * does not exist yet has no tests.
 */
export function checkSuite(suite: string, validate = rootValidator(), base = suite, validateEntry?: ValidateFunction): SuiteResult {
  const result: SuiteResult = { checked: 0, skipped: 0, problems: [] };
  const dirs = (dir: string): string[] => {
    if (!existsSync(dir)) return [];
    const out: string[] = [];
    for (const entry of readdirSync(dir).sort()) {
      const p = join(dir, entry);
      if (statSync(p).isDirectory()) out.push(...dirs(p));
      else if (entry === 'test.json') out.push(dir);
    }
    return out;
  };
  for (const dir of dirs(suite)) {
    const name = relative(base, dir) || '.';
    const inputPath = join(dir, 'input.json');
    const expectedPath = join(dir, 'expected.json');
    if (!existsSync(inputPath) || !existsSync(expectedPath)) {
      result.problems.push(`${name}: has test.json but no ${existsSync(inputPath) ? 'expected.json' : 'input.json'}`);
      continue;
    }
    let codes: string[];
    try {
      const expected = JSON.parse(readFileSync(expectedPath, 'utf8')) as { diagnostics?: { code?: unknown }[] };
      if (!Array.isArray(expected.diagnostics)) throw new Error('"diagnostics" is not an array');
      codes = expected.diagnostics.map((d) => String(d.code));
    } catch (e) {
      result.problems.push(`${name}: expected.json: ${(e as Error).message}`);
      continue;
    }
    const registryPath = join(dir, 'registry.json');
    if (existsSync(registryPath) && !codes.includes('FS-CFG-001')) {
      if (!validateEntry) result.problems.push(`${name}: has registry.json, which this suite does not take`);
      else {
        const entries = JSON.parse(readFileSync(registryPath, 'utf8')) as unknown;
        if (!Array.isArray(entries)) result.problems.push(`${name}: registry.json is not an array of registry entries`);
        else
          entries.forEach((e, i) => {
            if (!validateEntry(e))
              result.problems.push(`${name}: registry.json entry ${i} does not match the registry entry schema:\n    ${formatErrors(validateEntry.errors ?? []).join('\n    ')}`);
          });
      }
    }
    if (codes.some((c) => c.startsWith('FS-JSON-') || c.startsWith('FS-DOC-') || c.startsWith('FS-CFG-'))) {
      result.skipped++;
      continue;
    }
    const text = readFileSync(inputPath, 'utf8');
    try {
      JSON.parse(text);
    } catch {
      result.problems.push(`${name}: input.json is not well-formed JSON, but no FS-JSON- diagnostic is expected`);
      continue;
    }
    const mustReject = codes.length === 1 && codes[0] === 'FS-SCH-001';
    const { valid, errors } = validateText(text, validate);
    result.checked++;
    if (mustReject && valid) result.problems.push(`${name}: expects [FS-SCH-001], but the schema accepts the input`);
    if (!mustReject && !valid)
      result.problems.push(`${name}: expects [${codes.join(', ')}], but the schema rejects the input:\n    ${formatErrors(errors).join('\n    ')}`);
  }
  return result;
}

/**
 * Checks an Ops request schema against its Ops conformance suite (conformance/ops/<v>). For every
 * test, the schema must reject request.json - which may not even be JSON - exactly when the
 * expected diagnostics are [FS-OPS-001], and accept it otherwise. And document A, input.json, must
 * match the Core schema in every test that does not expect FS-OPS-002 (A is valid there).
 */
export function checkOpsSuite(suite: string, validateRequest = requestValidator(), validateDocument = rootValidator(), base = suite): SuiteResult {
  const result: SuiteResult = { checked: 0, skipped: 0, problems: [] };
  const dirs = (dir: string): string[] => {
    if (!existsSync(dir)) return [];
    const out: string[] = [];
    for (const entry of readdirSync(dir).sort()) {
      const p = join(dir, entry);
      if (statSync(p).isDirectory()) out.push(...dirs(p));
      else if (entry === 'test.json') out.push(dir);
    }
    return out;
  };
  for (const dir of dirs(suite)) {
    const name = relative(base, dir) || '.';
    const missing = ['input.json', 'request.json', 'expected.json'].filter((f) => !existsSync(join(dir, f)));
    if (missing.length) {
      result.problems.push(`${name}: has test.json but no ${missing.join(', ')}`);
      continue;
    }
    let codes: string[];
    try {
      const expected = JSON.parse(readFileSync(join(dir, 'expected.json'), 'utf8')) as { diagnostics?: { code?: unknown }[] };
      if (!Array.isArray(expected.diagnostics)) throw new Error('"diagnostics" is not an array');
      codes = expected.diagnostics.map((d) => String(d.code));
    } catch (e) {
      result.problems.push(`${name}: expected.json: ${(e as Error).message}`);
      continue;
    }
    const mustReject = codes.length === 1 && codes[0] === 'FS-OPS-001';
    let request: SchemaResult;
    try {
      request = validateText(readFileSync(join(dir, 'request.json'), 'utf8'), validateRequest);
    } catch {
      request = { valid: false, errors: [] };
    }
    result.checked++;
    if (mustReject && request.valid) result.problems.push(`${name}: expects [FS-OPS-001], but the request schema accepts the request`);
    if (!mustReject && !request.valid)
      result.problems.push(`${name}: expects [${codes.join(', ')}], but the request schema rejects the request:\n    ${formatErrors(request.errors).join('\n    ')}`);
    if (!codes.includes('FS-OPS-002')) {
      const document = validateText(readFileSync(join(dir, 'input.json'), 'utf8'), validateDocument);
      if (!document.valid)
        result.problems.push(`${name}: document A must be valid, but the Core schema rejects it:\n    ${formatErrors(document.errors).join('\n    ')}`);
    }
  }
  return result;
}

/**
 * The official and registered extensions that have a schema of their own: registry/<NAME>/ holds
 * the registry entry (extension.json) and the schema (`*.schema.json`) whose `$id` is the entry's
 * `schema` URL. Their suites are conformance/ext/<NAME>/<version>/.
 */
export interface ExtensionSchema {
  name: string;
  version: string;
  dir: string;
  entry: Record<string, Json>;
  files: SchemaFile[];
}

export function extensionSchemas(root = join(import.meta.dirname, '..')): ExtensionSchema[] {
  const dir = join(root, 'registry');
  if (!existsSync(dir)) return [];
  const out: ExtensionSchema[] = [];
  for (const name of readdirSync(dir).sort()) {
    const d = join(dir, name);
    if (!statSync(d).isDirectory() || !existsSync(join(d, 'extension.json'))) continue;
    const entry = JSON.parse(readFileSync(join(d, 'extension.json'), 'utf8')) as Record<string, Json>;
    out.push({ name, version: String(entry.version), dir: d, entry, files: loadSchemaFiles(d) });
  }
  return out;
}

/** Every test directory (one holding test.json) under a suite. */
export function testDirs(dir: string): string[] {
  if (!existsSync(dir)) return [];
  const out: string[] = [];
  for (const entry of readdirSync(dir).sort()) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...testDirs(p));
    else if (entry === 'test.json') out.push(dir);
  }
  return out;
}

/**
 * The elements of a document that may carry extension data (Core 1.6), as `[collection, data]` for
 * every one whose `extensions` has a member `name`: the core collections, program items (`items`),
 * option sets and options.
 */
export function elementExtensionData(doc: unknown, name: string): [string, unknown][] {
  const out: [string, unknown][] = [];
  if (doc === null || typeof doc !== 'object') return out;
  const d = doc as Record<string, unknown>;
  const program = d.program as { items?: unknown } | undefined;
  const collections: [string, unknown][] = [
    ...['buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'rooms', 'slabs', 'types', 'materials',
      'assets', 'roofs', 'stairs', 'optionSets', 'options'].map((c) => [c, d[c]] as [string, unknown]),
    ['items', program && typeof program === 'object' ? program.items : undefined],
  ];
  for (const [c, elements] of collections) {
    if (elements === null || typeof elements !== 'object') continue;
    for (const el of Object.values(elements as Record<string, unknown>)) {
      const x = (el as { extensions?: Record<string, unknown> } | null)?.extensions;
      if (x && typeof x === 'object' && name in x) out.push([c, x[name]]);
    }
  }
  return out;
}

/**
 * Checks an extension's schema against its suite: the schema rejects the extension's data exactly
 * in the tests that expect `[FS-<CODE>-SCH-001]` alone, and accepts it in every valid test that
 * derives the extension's values (where the extension was evaluated). The data is the top-level
 * data, and - for an extension whose schema has `#/$defs/coreElements` (FS_structural), given as
 * `validateOn` - the data on every element, checked as `{ <collection>: data }` against that
 * definition. An Ops test's request must match the Ops 0.2 request schema - Ops 0.3's when its
 * document declares "0.3".
 */
export function checkExtensionSuite(suite: string, name: string, code: string, validateData: ValidateFunction,
  validateRequest: ValidateFunction, base = suite, validateRequest03: ValidateFunction = validateRequest,
  validateOn?: ValidateFunction): SuiteResult {
  const result: SuiteResult = { checked: 0, skipped: 0, problems: [] };
  for (const dir of testDirs(suite)) {
    const rel = relative(base, dir) || '.';
    const expected = JSON.parse(readFileSync(join(dir, 'expected.json'), 'utf8')) as {
      valid?: boolean; diagnostics?: { code?: unknown }[]; derived?: { extensions?: Record<string, unknown> };
    };
    const codes = (expected.diagnostics ?? []).map((d) => String(d.code));
    if (existsSync(join(dir, 'request.json'))) {
      // Ops 0.2, or Ops 0.3 for a document declaring "0.3", as the suite's Core reader is chosen.
      const v03 = (parseForSchema(readFileSync(join(dir, 'input.json'), 'utf8')) as { floorspec?: unknown } | null)?.floorspec === '0.3';
      const request = validateText(readFileSync(join(dir, 'request.json'), 'utf8'), v03 ? validateRequest03 : validateRequest);
      if (!request.valid) result.problems.push(`${rel}: the Ops ${v03 ? '0.3' : '0.2'} request schema rejects request.json:\n    ${formatErrors(request.errors).join('\n    ')}`);
      result.checked++;
      continue;
    }
    const mustReject = codes.length === 1 && codes[0] === `FS-${code}-SCH-001`;
    const evaluated = expected.valid === true && expected.derived?.extensions !== undefined && name in expected.derived.extensions;
    if (!mustReject && !evaluated) {
      result.skipped++;
      continue;
    }
    const doc = parseForSchema(readFileSync(join(dir, 'input.json'), 'utf8')) as { extensions?: Record<string, unknown> };
    const data = doc.extensions?.[name] ?? {};
    let valid = validateData(data) as boolean;
    let errors = validateData.errors ?? [];
    if (valid && validateOn)
      for (const [c, x] of elementExtensionData(doc, name))
        if (!(validateOn({ [c]: x }) as boolean)) {
          valid = false;
          errors = validateOn.errors ?? [];
          break;
        }
    result.checked++;
    if (mustReject && valid) result.problems.push(`${rel}: expects [FS-${code}-SCH-001], but the ${name} schema accepts its data`);
    if (evaluated && !valid)
      result.problems.push(`${rel}: ${name} is evaluated and the test is valid, but the ${name} schema rejects its data:\n    ${formatErrors(errors).join('\n    ')}`);
  }
  return result;
}

/** The Floorspec Rules drafts this repository publishes, oldest first. */
export const RULES_VERSIONS = ['0.1'] as const;
export type RulesVersion = (typeof RULES_VERSIONS)[number];
/** The draft the spec text in spec/rules/ is. */
export const CURRENT_RULES: RulesVersion = '0.1';

export const rulesSchemaBase = (v: RulesVersion) => `https://d3cloud.io/floorspec/schema/rules/${v}/`;
export const rulesId = (v: RulesVersion, name: string) => `${rulesSchemaBase(v)}${name}.schema.json`;
export const rulesSchemaDir = (v: RulesVersion) => join(import.meta.dirname, '..', 'schema', 'rules', v);

/** The validators of one Rules draft: the evaluation request, a pack, a profile, a report, and a measure result. */
export interface RulesValidators {
  request: ValidateFunction;
  pack: ValidateFunction;
  profile: ValidateFunction;
  report: ValidateFunction;
  measureResult: ValidateFunction;
}

export function rulesValidators(ajv = createAjv(loadSchemaFiles(rulesSchemaDir('0.1'))), v: RulesVersion = '0.1'): RulesValidators {
  const get = (id: string) => {
    const f = ajv.getSchema(id);
    if (!f) throw new Error(`schema ${id} is not loaded`);
    return f;
  };
  return {
    request: get(rulesId(v, 'request')),
    pack: get(rulesId(v, 'pack')),
    profile: get(rulesId(v, 'profile')),
    report: get(rulesId(v, 'report')),
    measureResult: get(`${rulesId(v, 'finding')}#/$defs/measureResult`),
  };
}

/** The default profile (Rules 10.6), as the JSON block of spec/rules/10-profiles.md under "## 10.6" gives it. */
export function defaultProfile(root = join(import.meta.dirname, '..')): unknown {
  const md = readFileSync(join(root, 'spec', 'rules', '10-profiles.md'), 'utf8');
  const section = md.split(/^## 10\.6 /m)[1] ?? '';
  const block = /```json\n([\s\S]*?)\n```/.exec(section);
  if (!block) throw new Error('spec/rules/10-profiles.md: no JSON block under 10.6');
  return JSON.parse(block[1]!);
}

/**
 * Whether a JSON text has an object with two members of one name (Core 9.1.2). JSON.parse keeps the
 * last of them silently, so a request that is malformed only because of one is found here.
 */
export function hasDuplicateMember(text: string): boolean {
  let i = 0;
  let dup = false;
  const ws = () => {
    while (i < text.length && ' \t\n\r'.includes(text[i]!)) i++;
  };
  const str = (): string => {
    const start = i;
    i++;
    while (text[i] !== '"') i += text[i] === '\\' ? 2 : 1;
    i++;
    return JSON.parse(text.slice(start, i)) as string;
  };
  const value = (): void => {
    ws();
    const c = text[i];
    if (c === '{') {
      i++;
      const seen = new Set<string>();
      ws();
      if (text[i] === '}') return void i++;
      for (;;) {
        ws();
        const k = str();
        if (seen.has(k)) dup = true;
        seen.add(k);
        ws();
        i++; // :
        value();
        ws();
        if (text[i++] === '}') return;
      }
    } else if (c === '[') {
      i++;
      ws();
      if (text[i] === ']') return void i++;
      for (;;) {
        value();
        ws();
        if (text[i++] === ']') return;
      }
    } else if (c === '"') str();
    else while (i < text.length && !',]} \t\n\r'.includes(text[i]!)) i++;
  };
  value();
  return dup;
}

/**
 * Checks the Rules schemas against the Rules suite (conformance/rules/<v>). For a report test, with
 * the diagnostics of expected.json: the request schema rejects request.json exactly when FS-RULES-001
 * is expected (a request that is not JSON, or has a duplicate member, needs no schema to be
 * malformed); unless FS-RULES-001 is, the profile schema accepts the request's profile - or the
 * default profile - whenever FS-RULES-002 is not expected; unless one of FS-RULES-001 to 003 is, the
 * pack schema rejects each pack exactly when FS-RULES-004 names its index; the document matches the
 * Core schema whenever the evaluation reached it and FS-RULES-003 is not expected; and expected.json
 * matches the report schema. For a measure test, every result matches the measure result definition
 * and the document matches the Core schema. Every registry.json matches the registry entry schema.
 */
export function checkRulesSuite(suite: string, rv: RulesValidators, validateDocument: ValidateFunction,
  validateEntry: ValidateFunction, profile0: unknown, base = suite): SuiteResult {
  const result: SuiteResult = { checked: 0, skipped: 0, problems: [] };
  for (const dir of testDirs(suite)) {
    const rel = relative(base, dir) || '.';
    const read = (f: string) => readFileSync(join(dir, f), 'utf8');
    const has = (f: string) => existsSync(join(dir, f));
    if (has('registry.json'))
      (JSON.parse(read('registry.json')) as unknown[]).forEach((e, i) => {
        if (!validateEntry(e)) result.problems.push(`${rel}: registry.json entry ${i} does not match the registry entry schema`);
      });
    const expected = JSON.parse(read('expected.json')) as { diagnostics?: { code: string; packIndex?: number }[]; results?: unknown[] };
    const document = () => {
      const d = validateText(read('input.json'), validateDocument);
      if (!d.valid) result.problems.push(`${rel}: the document does not match the Core schema:\n    ${formatErrors(d.errors).join('\n    ')}`);
    };
    result.checked++;
    if (has('measures.json')) {
      for (const [i, r] of (expected.results ?? []).entries())
        if (!rv.measureResult(r)) result.problems.push(`${rel}: result ${i} does not match the measure result definition:\n    ${formatErrors(rv.measureResult.errors ?? []).join('\n    ')}`);
      document();
      continue;
    }
    if (!rv.report(expected)) result.problems.push(`${rel}: expected.json does not match the report schema:\n    ${formatErrors(rv.report.errors ?? []).join('\n    ')}`);
    const codes = (expected.diagnostics ?? []).map((d) => d.code);
    const text = read('request.json');
    let request: unknown;
    try {
      request = parseForSchema(text);
    } catch {
      if (!codes.includes('FS-RULES-001')) result.problems.push(`${rel}: request.json is not JSON, but FS-RULES-001 is not expected`);
      continue;
    }
    const requestOk = (rv.request(request) as boolean) && !hasDuplicateMember(text);
    if (codes.includes('FS-RULES-001') === requestOk)
      result.problems.push(`${rel}: the request schema ${requestOk ? 'accepts' : 'rejects'} request.json, and FS-RULES-001 is ${requestOk ? '' : 'not '}expected`);
    if (codes.includes('FS-RULES-001')) continue;
    const r = request as { profile?: unknown; packs: unknown[] };
    const profile = r.profile === undefined ? profile0 : r.profile;
    if (!codes.includes('FS-RULES-002') && !rv.profile(profile))
      result.problems.push(`${rel}: FS-RULES-002 is not expected, but the profile schema rejects the profile:\n    ${formatErrors(rv.profile.errors ?? []).join('\n    ')}`);
    if (codes.includes('FS-RULES-002')) continue;
    if (!codes.includes('FS-RULES-003')) document();
    if (codes.includes('FS-RULES-003')) continue;
    const bad = new Set((expected.diagnostics ?? []).filter((d) => d.code === 'FS-RULES-004').map((d) => d.packIndex));
    r.packs.forEach((p, i) => {
      const ok = rv.pack(p) as boolean;
      if (ok === bad.has(i))
        result.problems.push(`${rel}: the pack schema ${ok ? 'accepts' : 'rejects'} pack ${i}, and FS-RULES-004 is ${ok ? '' : 'not '}expected for it` +
          (ok ? '' : `:\n    ${formatErrors(rv.pack.errors ?? []).join('\n    ')}`));
    });
  }
  return result;
}
