"""Strict parser for the small YAML subset used by .factory/policy.yaml.

Supported: nested maps (2+ space indent), lists of scalars, `key:` blocks,
empty `[]` / `{}`, quoted and bare strings, ints, floats, booleans, comments.
Anything else raises YamlError. The repo does not depend on PyYAML, and a
policy that parses differently from what its author meant must be an error.
"""
from __future__ import annotations

import json
import re


class YamlError(ValueError):
    pass


_INT = re.compile(r"^-?\d+$")
_FLOAT = re.compile(r"^-?\d+\.\d+$")


def _strip_comment(text: str) -> str:
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == "\\" and quote == '"':
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i]
    return text


def _scalar(raw: str, lineno: int):
    raw = raw.strip()
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    if raw[0] in "[{":
        raise YamlError(f"line {lineno}: flow collections are not supported")
    if raw[0] == '"':
        try:
            val = json.loads(raw)
        except ValueError:
            raise YamlError(f"line {lineno}: bad double-quoted string") from None
        if not isinstance(val, str):
            raise YamlError(f"line {lineno}: bad double-quoted string")
        return val
    if raw[0] == "'":
        if len(raw) < 2 or raw[-1] != "'":
            raise YamlError(f"line {lineno}: unterminated string")
        return raw[1:-1].replace("''", "'")
    if raw in ("true", "false"):
        return raw == "true"
    if _INT.match(raw):
        return int(raw)
    if _FLOAT.match(raw):
        return float(raw)
    if raw[0] in "*&!|>%@`":
        raise YamlError(f"line {lineno}: bare scalar starts with reserved character; quote it")
    return raw


def _lines(text: str):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if "\t" in line[: len(line) - len(line.lstrip())]:
            raise YamlError(f"line {n}: tabs are not allowed for indentation")
        body = _strip_comment(line).rstrip()
        if not body.strip():
            continue
        out.append((len(body) - len(body.lstrip(" ")), body.strip(), n))
    return out


def _block(lines, i, indent):
    ind, body, n = lines[i]
    if ind != indent:
        raise YamlError(f"line {n}: unexpected indentation")
    if body == "-" or body.startswith("- "):
        return _list(lines, i, indent)
    return _map(lines, i, indent)


def _list(lines, i, indent):
    items = []
    while i < len(lines):
        ind, body, n = lines[i]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError(f"line {n}: unexpected indentation")
        if not (body == "-" or body.startswith("- ")):
            raise YamlError(f"line {n}: mixed list and map")
        rest = body[1:].strip()
        if not rest:
            raise YamlError(f"line {n}: empty list item")
        if re.match(r'^[^"\'\s][^:]*:(\s|$)', rest):
            raise YamlError(f"line {n}: maps inside lists are not supported")
        items.append(_scalar(rest, n))
        i += 1
    return items, i


def _map(lines, i, indent):
    out = {}
    while i < len(lines):
        ind, body, n = lines[i]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError(f"line {n}: unexpected indentation")
        if body.startswith("- ") or body == "-":
            raise YamlError(f"line {n}: mixed list and map")
        m = re.match(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$", body)
        if not m:
            raise YamlError(f"line {n}: expected 'key: value'")
        key, rest = m.group(1), m.group(2)
        if key in out:
            raise YamlError(f"line {n}: duplicate key {key!r}")
        i += 1
        if rest is not None and rest.strip():
            out[key] = _scalar(rest, n)
            continue
        if i >= len(lines) or lines[i][0] <= indent:
            raise YamlError(f"line {n}: key {key!r} has no value")
        out[key], i = _block(lines, i, lines[i][0])
    return out, i


def parse(text: str):
    lines = _lines(text)
    if not lines:
        raise YamlError("empty document")
    value, i = _block(lines, 0, lines[0][0])
    if i != len(lines):
        raise YamlError(f"line {lines[i][2]}: unexpected content")
    return value
