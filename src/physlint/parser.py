from __future__ import annotations

import re

from physlint.dimensions import DIMENSIONLESS, Unit

_TOKEN_RE = re.compile(
    r"""
    (?P<NUMBER>[+-]?\d+)
    | (?P<STARSTAR>\*\*)
    | (?P<STAR>\*)
    | (?P<SLASH>/)
    | (?P<CARET>\^)
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<NAME>[a-zA-ZΩμÅ°]+)
    | (?P<WS>\s+)
    """,
    re.VERBOSE,
)

_Token = tuple[str, str]


def _tokenize(s: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if m is None:
            return []
        pos = m.end()
        if m.lastgroup == "WS":
            continue
        tokens.append((m.lastgroup, m.group()))  # type: ignore[arg-type]
    return tokens


class _Parser:
    # expr = term (('*' | '/') term)*
    # term = atom (('^' | '**') integer)?
    # atom = '(' expr ')' | '1' | NAME

    def __init__(self, tokens: list[_Token], resolving: set[str] | None) -> None:
        self._tokens = tokens
        self._pos = 0
        self._resolving = resolving

    def _peek(self) -> _Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> _Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, kind: str) -> _Token | None:
        tok = self._peek()
        if tok is not None and tok[0] == kind:
            return self._advance()
        return None

    def parse(self) -> Unit | None:
        result = self._expr()
        if result is None or self._pos != len(self._tokens):
            return None
        return result

    def _expr(self) -> Unit | None:
        left = self._term()
        if left is None:
            return None
        while True:
            tok = self._peek()
            if tok is None:
                break
            if tok[0] == "STAR":
                self._advance()
                right = self._term()
                if right is None:
                    return None
                left = left * right
            elif tok[0] == "SLASH":
                self._advance()
                right = self._term()
                if right is None:
                    return None
                left = left / right
            else:
                break
        return left

    def _term(self) -> Unit | None:
        base = self._atom()
        if base is None:
            return None
        tok = self._peek()
        if tok is not None and tok[0] in ("CARET", "STARSTAR"):
            self._advance()
            exp_tok = self._peek()
            if exp_tok is None or exp_tok[0] != "NUMBER":
                return None
            self._advance()
            base = base ** int(exp_tok[1])
        return base

    def _atom(self) -> Unit | None:
        tok = self._peek()
        if tok is None:
            return None
        if tok[0] == "LPAREN":
            self._advance()
            inner = self._expr()
            if inner is None:
                return None
            if self._expect("RPAREN") is None:
                return None
            return inner
        if tok[0] == "NUMBER" and tok[1] == "1":
            self._advance()
            return DIMENSIONLESS
        if tok[0] == "NAME":
            self._advance()
            from physlint.units import resolve
            return resolve(tok[1], self._resolving)
        return None


def parse_unit(s: str, *, _resolving: set[str] | None = None) -> Unit | None:
    s = s.strip()
    if not s:
        return None
    tokens = _tokenize(s)
    if not tokens:
        return None
    return _Parser(tokens, _resolving).parse()
