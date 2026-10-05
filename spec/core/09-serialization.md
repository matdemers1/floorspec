# 9. Serialization

## 9.1 Encoding

A Floorspec document is a JSON text (RFC 8259) encoded in UTF-8.

A document MUST be a well-formed JSON text in UTF-8, without a byte order mark. {#FS-CORE-9.1.1 MUST}

An object in a document MUST NOT contain the same member name twice. {#FS-CORE-9.1.2 MUST NOT}

A string in a document MUST NOT contain an unpaired surrogate, whether literally or as a `\u` escape. {#FS-CORE-9.1.3 MUST NOT}

A surrogate code point encoded directly in UTF-8 is ill-formed UTF-8 and so breaks 9.1.1
(`FS-JSON-001`); 9.1.3 is about `\u` escapes. The last two rules are those of I-JSON (RFC 7493). Many JSON parsers silently keep the last of two
duplicate members; a Floorspec reader has to notice them, because two readers that keep different
copies would read two different buildings from one file.

Numbers in core members are integers (chapter 2). Extension data and `extras` may contain any JSON
number; the canonical form writes it as RFC 8785 does.

## 9.2 Canonical form

Every Floorspec document has exactly one **canonical form**: a byte sequence that every
conformant canonicalizer produces for it, whatever the formatting, member order or omitted
defaults of the input. Canonical form is what is stored, hashed, diffed and exported, so two tools
that agree on a model agree on its bytes (FLR-REQ-018).

The canonical form of a document is produced in two steps.

1. **Omit constant defaults.** Working from the innermost objects outwards, remove every member
   that this specification gives a constant default (1.5) and whose value equals that default —
   including a collection or object that has become empty, if its default is `{}`, and an array
   that has become empty, if its default is `[]`. Members with a derived default, and typed
   properties (8.2), are never removed. Write every declaration object in `extensionsUsed` that
   has no `schema` member as its version string (12.1). The content of extension data — including
   the extension elements in it (12.5) — and of `extras` is never changed; an `extensions` or
   `extras` member is removed only when it is `{}`.
2. **Write.** Serialize the result as JSON with these rules, which are exactly those of
   ECMAScript's `JSON.stringify(value, null, 2)` applied to a value whose object members have been
   sorted, followed by one line feed:
   - object members are sorted by member name, comparing names as sequences of UTF-16 code units,
     as RFC 8785 §3.2.3 does;
   - each member and each array element is on its own line, indented by two spaces per level of
     nesting, and an object member is written as its name, a colon, one space and its value;
   - an empty object is written `{}` and an empty array `[]`;
   - strings are written as RFC 8785 §3.2.2.2 writes them, and numbers as RFC 8785 §3.2.2.3
     writes them;
   - line endings are a single line feed (U+000A), with one after the final `}` and no trailing
     whitespace anywhere.

A canonicalizer MUST produce exactly the canonical form of every valid document it is given. {#FS-CORE-9.2.1 MUST}

Canonicalization MUST NOT change what a document means: the canonical form of a document has the same derived values as the document. {#FS-CORE-9.2.2 MUST NOT}

> [!example] Before and after
> An input with `"justification": "center"` on a wall, an empty `"extras": {}` and members in any
> order canonicalizes to a document with neither member and with every object's members in sorted
> order. An input with `"sill": 0` on an opening keeps it, because `sill` is a typed property.

## 9.3 Content hash

A document's **content hash** identifies its content: equal canonical forms, equal hashes. It is
the SHA-256 digest (FIPS 180-4) of the UTF-8 bytes of the RFC 8785 serialization of the document
after step 1 of 9.2, written as 64 lowercase hexadecimal digits.

A deriver MUST compute a document's content hash as this section defines it. {#FS-CORE-9.3.1 MUST}

The hash is taken over the compact RFC 8785 serialization rather than the indented canonical form
so that any RFC 8785 library computes it; the two carry the same content, and the hash changes
exactly when the canonical form does.

## 9.4 Files

A document stored as a file has the extension `.floorspec.json`. The media type, pending
registration, is `application/vnd.floorspec+json`. The directory that holds the file is the
document's package, where the files of its assets are found by their paths (18.4). A packaged form
in one file, a ZIP archive holding `model.json` and its assets, is defined in a later draft.
