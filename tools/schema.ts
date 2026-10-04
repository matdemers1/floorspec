/**
 * The normative JSON Schemas (FLR-ADR-006), loaded into ajv: Floorspec Core 0.1's document schema
 * - the schema tier (tier 3, FS-SCH-001) of chapter 10 and nothing else - and Floorspec Ops 0.1's
 * apply-request schema, whose rejections are FS-OPS-001. Used by `pnpm schema:check` and its tests.
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { Ajv2020, type ErrorObject, type ValidateFunction } from 'ajv/dist/2020.js';

export const SCHEMA_BASE = 'https://d3cloud.io/floorspec/schema/core/0.1/';
export const ROOT_ID = `${SCHEMA_BASE}floorspec.schema.json`;
export const schemaDir = join(import.meta.dirname, '..', 'schema', 'core', '0.1');

export const OPS_SCHEMA_BASE = 'https://d3cloud.io/floorspec/schema/ops/0.1/';
export const OPS_ROOT_ID = `${OPS_SCHEMA_BASE}request.schema.json`;
export const opsSchemaDir = join(import.meta.dirname, '..', 'schema', 'ops', '0.1');

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

export interface SchemaFile {
  file: string;
  id: string;
  schema: Record<string, Json>;
}

/** Every `*.schema.json` file of Core 0.1, sorted by file name. */
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

export function rootValidator(ajv = createAjv()): ValidateFunction {
  const validate = ajv.getSchema(ROOT_ID);
  if (!validate) throw new Error(`schema ${ROOT_ID} is not loaded`);
  return validate;
}

/** The validator of a Floorspec Ops 0.1 apply request. */
export function requestValidator(ajv = createAjv(loadSchemaFiles(opsSchemaDir))): ValidateFunction {
  const validate = ajv.getSchema(OPS_ROOT_ID);
  if (!validate) throw new Error(`schema ${OPS_ROOT_ID} is not loaded`);
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

/** Applies the Core 0.1 schema to a JSON text that is already known to be well formed (9.1). */
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
 * Checks the schema against a conformance suite directory (conformance/core/0.1). For every test
 * whose input is well-formed JSON and whose expected diagnostics have no FS-JSON- or FS-DOC- code,
 * the schema must reject the input when the expected diagnostics are exactly [FS-SCH-001], and
 * accept it otherwise. A suite that does not exist yet has no tests.
 */
export function checkSuite(suite: string, validate = rootValidator(), base = suite): SuiteResult {
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
    if (codes.some((c) => c.startsWith('FS-JSON-') || c.startsWith('FS-DOC-'))) {
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
 * Checks the Ops request schema against the Ops conformance suite (conformance/ops/0.1). For every
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
