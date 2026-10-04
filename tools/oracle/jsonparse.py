"""Strict JSON parsing for Floorspec documents (9.1).

RFC 8259 grammar exactly, UTF-8 without a byte order mark, plus the two I-JSON rules Floorspec
adopts: no duplicate member names (FS-JSON-002) and no unpaired surrogates (FS-JSON-003).

Numbers: a token with no fraction and no exponent is a Python ``int``; any other number token is a
Python ``float`` (correctly rounded to the nearest IEEE 754 double, as RFC 8785 reads it). Keeping
the two apart is what lets the schema tier tell ``1`` from ``1.0`` and ``1e0`` (2.1.1).
"""

from __future__ import annotations

import re

JSON_001 = 'FS-JSON-001'
JSON_002 = 'FS-JSON-002'
JSON_003 = 'FS-JSON-003'

_NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?')
_WS = ' \t\n\r'


class Malformed(Exception):
    """The input is not a well-formed UTF-8 JSON text (FS-JSON-001)."""


class _Parser:
    def __init__(self, text: str):
        self.s = text
        self.i = 0
        self.flags: list[str] = []

    def ws(self) -> None:
        s, i = self.s, self.i
        while i < len(s) and s[i] in _WS:
            i += 1
        self.i = i

    def fail(self, why: str):
        raise Malformed(f'{why} at offset {self.i}')

    def value(self):
        self.ws()
        if self.i >= len(self.s):
            self.fail('unexpected end')
        c = self.s[self.i]
        if c == '{':
            return self.obj()
        if c == '[':
            return self.arr()
        if c == '"':
            return self.string()
        for lit, v in (('true', True), ('false', False), ('null', None)):
            if self.s.startswith(lit, self.i):
                self.i += len(lit)
                return v
        m = _NUMBER.match(self.s, self.i)
        if not m or m.end() == self.i:
            self.fail('unexpected character')
        self.i = m.end()
        tok = m.group(0)
        if m.group(1) is None and m.group(2) is None:
            return int(tok)
        return float(tok)

    def obj(self):
        self.i += 1
        out: dict = {}
        self.ws()
        if self.s.startswith('}', self.i):
            self.i += 1
            return out
        while True:
            self.ws()
            if not self.s.startswith('"', self.i):
                self.fail('expected a member name')
            k = self.string()
            self.ws()
            if not self.s.startswith(':', self.i):
                self.fail('expected ":"')
            self.i += 1
            v = self.value()
            if k in out:
                self.flags.append(JSON_002)
            out[k] = v
            self.ws()
            if self.s.startswith(',', self.i):
                self.i += 1
                continue
            if self.s.startswith('}', self.i):
                self.i += 1
                return out
            self.fail('expected "," or "}"')

    def arr(self):
        self.i += 1
        out: list = []
        self.ws()
        if self.s.startswith(']', self.i):
            self.i += 1
            return out
        while True:
            out.append(self.value())
            self.ws()
            if self.s.startswith(',', self.i):
                self.i += 1
                continue
            if self.s.startswith(']', self.i):
                self.i += 1
                return out
            self.fail('expected "," or "]"')

    def hex4(self) -> int:
        h = self.s[self.i:self.i + 4]
        if len(h) != 4 or any(c not in '0123456789abcdefABCDEF' for c in h):
            self.fail('bad \\u escape')
        self.i += 4
        return int(h, 16)

    def string(self) -> str:
        self.i += 1
        s = self.s
        out: list[str] = []
        while True:
            if self.i >= len(s):
                self.fail('unterminated string')
            c = s[self.i]
            if c == '"':
                self.i += 1
                return ''.join(out)
            if ord(c) < 0x20:
                self.fail('control character in string')
            if c != '\\':
                out.append(c)
                self.i += 1
                continue
            self.i += 1
            if self.i >= len(s):
                self.fail('unterminated escape')
            e = s[self.i]
            self.i += 1
            simple = {'"': '"', '\\': '\\', '/': '/', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}
            if e in simple:
                out.append(simple[e])
                continue
            if e != 'u':
                self.fail('bad escape')
            u = self.hex4()
            if 0xD800 <= u <= 0xDBFF:
                if s.startswith('\\u', self.i):
                    save = self.i
                    self.i += 2
                    lo = self.hex4()
                    if 0xDC00 <= lo <= 0xDFFF:
                        out.append(chr(0x10000 + ((u - 0xD800) << 10) + (lo - 0xDC00)))
                        continue
                    self.i = save
                self.flags.append(JSON_003)
                out.append(chr(u))
            elif 0xDC00 <= u <= 0xDFFF:
                self.flags.append(JSON_003)
                out.append(chr(u))
            else:
                out.append(chr(u))


def parse(data: bytes):
    """Parse a document's bytes.

    Returns ``(value, codes)``: ``codes`` is the sorted list of FS-JSON-002 / FS-JSON-003 codes
    found, one per occurrence. Raises :class:`Malformed` for FS-JSON-001.
    """
    if data.startswith(b'\xef\xbb\xbf'):
        raise Malformed('byte order mark')
    try:
        text = data.decode('utf-8', 'strict')
    except UnicodeDecodeError as e:
        raise Malformed(f'not UTF-8: {e}') from None
    p = _Parser(text)
    v = p.value()
    p.ws()
    if p.i != len(text):
        p.fail('trailing characters')
    return v, sorted(p.flags)
