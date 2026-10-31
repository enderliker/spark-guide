#!/usr/bin/env python3
"""Static site generator for the Spark guide.

No third-party dependencies: Markdown, syntax highlighting and the site shell
are all implemented here. Run ``python3 build.py`` and the site is written to
``dist/``.  Content lives in ``content/<section>/<page>.md`` and the navigation
order is the ``NAV`` table below.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

SITE = {
    "title": "Spark Guide",
    "short": "Spark",
    "tagline": "The friendly guide to the Spark programming language",
    "description": (
        "A hands-on guide to Spark: an interpreted, dynamically typed language "
        "with classes, closures, coroutines and networking, written from scratch in C11."
    ),
    "version": "0.1.0",
    "repo": "https://github.com/enderliker/spark",
    "license": "MIT",
    "last_updated": "October 31, 2026",
}

NAV = [
    {
        "title": "Getting Started",
        "slug": "getting-started",
        "items": [
            {
                "slug": "introduction",
                "title": "Introduction",
                "description": "What Spark is, what makes it different, and how this guide is organized.",
            },
            {
                "slug": "installation",
                "title": "Installation",
                "description": "Build the interpreter from source on Linux, macOS or WSL and run your first command.",
            },
            {
                "slug": "first-program",
                "title": "Your First Program",
                "description": "Write, run and take apart a small Spark program line by line.",
            },
        ],
    },
    {
        "title": "Guide",
        "slug": "guide",
        "items": [
            {
                "slug": "variables-and-scope",
                "title": "Variables and Scope",
                "description": "Declare variables and constants, shadow names and understand blocks.",
            },
            {
                "slug": "types-and-values",
                "title": "Types and Values",
                "description": "The value model: nil, booleans, integers, floats, strings, arrays, maps and functions.",
            },
            {
                "slug": "operators",
                "title": "Operators",
                "description": "Arithmetic, comparison, logic, bitwise, slicing and the full precedence table.",
            },
            {
                "slug": "control-flow",
                "title": "Control Flow",
                "description": "Conditionals, loops, switch, labels and for-in iteration.",
            },
            {
                "slug": "functions-and-closures",
                "title": "Functions and Closures",
                "description": "First-class functions, lambdas, defaults, varargs, spread and captured variables.",
            },
            {
                "slug": "arrays",
                "title": "Arrays",
                "description": "Array literals, indexing, slicing, spread and the collection helpers.",
            },
            {
                "slug": "maps",
                "title": "Maps",
                "description": "Maps as records, keys of any type, and method call sugar.",
            },
            {
                "slug": "strings",
                "title": "Strings",
                "description": "UTF-8 text, interpolation, escapes, indexing, slicing and efficient building.",
            },
            {
                "slug": "classes-and-objects",
                "title": "Classes and Objects",
                "description": "Fields, methods, init, inheritance, super, statics and operator overloading.",
            },
            {
                "slug": "errors-and-exceptions",
                "title": "Errors and Exceptions",
                "description": "Diagnostics, error categories, throw, try, catch, finally and exit codes.",
            },
            {
                "slug": "modules",
                "title": "Modules",
                "description": "Split a program across files with import, caching and cycle detection.",
            },
            {
                "slug": "coroutines-and-channels",
                "title": "Coroutines and Channels",
                "description": "Cooperative concurrency with spawn, yield, join and channels.",
            },
        ],
    },
    {
        "title": "Standard Library",
        "slug": "stdlib",
        "items": [
            {
                "slug": "overview",
                "title": "Overview",
                "description": "How the standard library is organized and how method call syntax works.",
            },
            {
                "slug": "text",
                "title": "Text",
                "description": "Every string helper in the standard library, with edge cases.",
            },
            {
                "slug": "collections",
                "title": "Collections",
                "description": "Array and map natives, iteration and the higher-order helpers.",
            },
            {
                "slug": "numbers-and-math",
                "title": "Numbers and Math",
                "description": "Conversion, rounding, trigonometry and the two numeric types.",
            },
            {
                "slug": "files-and-system",
                "title": "Files, System and Data",
                "description": "File I/O, processes, environment, JSON, regular expressions and time.",
            },
        ],
    },
    {
        "title": "Networking",
        "slug": "networking",
        "items": [
            {
                "slug": "sockets",
                "title": "Sockets and Timeouts",
                "description": "TCP and UDP sockets, name resolution, deadlines and the coroutine scheduler.",
            },
            {
                "slug": "tls",
                "title": "TLS",
                "description": "Encrypted sockets with mandatory certificate and host-name verification.",
            },
            {
                "slug": "http-client",
                "title": "HTTP Client",
                "description": "http_get and friends: redirects, chunked bodies and explicit limits.",
            },
            {
                "slug": "http-server",
                "title": "HTTP Server",
                "description": "Build an HTTP server in pure Spark with lib/http.spark.",
            },
            {
                "slug": "websockets",
                "title": "WebSockets",
                "description": "RFC 6455 clients over ws:// and wss://, with frames, ping/pong and close.",
            },
        ],
    },
    {
        "title": "Tooling",
        "slug": "tooling",
        "items": [
            {
                "slug": "command-line",
                "title": "Command Line and REPL",
                "description": "Every CLI option, exit code and the interactive REPL.",
            },
            {
                "slug": "debugger",
                "title": "Debugger",
                "description": "Breakpoints, stepping, locals and stack traces with --debug.",
            },
            {
                "slug": "formatter-and-linter",
                "title": "Formatter and Linter",
                "description": "Canonical formatting and static warnings for unused code and shadowing.",
            },
            {
                "slug": "bytecode",
                "title": "Bytecode and Precompilation",
                "description": "Inspect bytecode with --dump and ship programs as .sparkc files.",
            },
        ],
    },
    {
        "title": "Under the Hood",
        "slug": "internals",
        "items": [
            {
                "slug": "architecture",
                "title": "Architecture",
                "description": "Lexer, parser, compiler, VM and the shape of the source tree.",
            },
            {
                "slug": "bytecode-and-dispatch",
                "title": "Bytecode and Dispatch",
                "description": "The instruction set, superinstructions and the hot/cold interpreter loop.",
            },
            {
                "slug": "garbage-collector",
                "title": "Garbage Collector",
                "description": "Mark and sweep, roots, adaptive thresholds and GC-safe natives.",
            },
            {
                "slug": "limits-and-performance",
                "title": "Limits and Performance",
                "description": "Hard limits, benchmark methodology and where time goes.",
            },
        ],
    },
    {
        "title": "Appendix",
        "slug": "appendix",
        "items": [
            {
                "slug": "examples",
                "title": "Example Gallery",
                "description": "Runnable programs from the repository, with commentary.",
            },
            {
                "slug": "roadmap",
                "title": "Project Status and Roadmap",
                "description": "What 0.1.0 covers and what is lined up for 0.2.",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Page list
# ---------------------------------------------------------------------------


def build_page_list():
    pages = []
    for section in NAV:
        for item in section["items"]:
            pages.append(
                {
                    "section": section["title"],
                    "section_slug": section["slug"],
                    "slug": item["slug"],
                    "title": item["title"],
                    "description": item["description"],
                    "src": CONTENT / section["slug"] / (item["slug"] + ".md"),
                    "url": f"{section['slug']}/{item['slug']}.html",
                }
            )
    return pages


PAGES = build_page_list()
PAGE_BY_URL = {p["url"]: p for p in PAGES}


# ---------------------------------------------------------------------------
# Escaping and small helpers
# ---------------------------------------------------------------------------


def escape(text):
    return html.escape(text, quote=True)


def strip_inline(text):
    """Plain text for search, ids and table-of-contents labels."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    return text.strip()


def slugify(text):
    text = strip_inline(text).lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-") or "section"


def resolve_link(target, current_url):
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("//"):
        return target
    if target.startswith("#"):
        return target
    frag = ""
    if "#" in target:
        target, frag = target.split("#", 1)
        frag = "#" + frag
    if target.startswith("@"):
        path = target[1:]
        if not path.endswith(".html"):
            path += ".html"
        base = os.path.dirname(current_url)
        rel = os.path.relpath(path, base or ".")
        rel = rel.replace(os.sep, "/")
        return rel + frag
    return target + frag


# ---------------------------------------------------------------------------
# Syntax highlighting
# ---------------------------------------------------------------------------

SPARK_KEYWORDS = {
    "var", "const", "fn", "if", "else", "while", "for", "in", "return",
    "break", "continue", "do", "switch", "case", "default", "and", "or",
    "not", "import", "try", "catch", "finally", "throw", "class", "new",
    "extends", "static", "super", "instanceof", "yield",
}
SPARK_CONSTANTS = {"true", "false", "nil"}
SPARK_NATIVES = {
    "print", "str", "num", "int", "float", "is_int", "is_nan", "type", "len",
    "assert", "copy", "isinstance", "is_a", "gc", "clock", "time", "sleep",
    "abs", "floor", "ceil", "round", "sqrt", "pow", "sin", "cos", "log",
    "exp", "min", "max", "sum", "substr", "split", "join", "trim", "upper",
    "lower", "repeat", "replace", "starts_with", "ends_with", "contains",
    "index_of", "chr", "ord", "pad_start", "pad_end", "push", "pop", "insert",
    "remove", "reverse", "fill", "slice", "range", "has", "del", "keys",
    "values", "clear", "merge", "get", "map", "filter", "reduce", "each",
    "any", "all", "enumerate", "zip", "sort", "sort_by", "input", "read_file",
    "write_file", "append_file", "file_exists", "open", "read_line", "read",
    "write", "close", "eof", "list_dir", "mkdir", "exec", "env", "exit",
    "rand", "randint", "srand", "to_json", "from_json", "regex_match",
    "regex_find", "regex_replace", "string_builder", "sb_append",
    "sb_to_string", "sb_len", "sb_clear", "spawn", "channel", "tcp_connect",
    "tls_connect", "ws_connect", "tcp_listen", "udp_bind", "net_select",
    "net_hostname", "url_parse", "url_encode", "url_decode", "parse_query",
    "http_get", "http_post", "http_put", "http_delete", "http_request",
}

_SPARK_TOKEN_RE = re.compile(
    r"""
      (?P<comment>//[^\n]*|/\*.*?\*/)
    | (?P<multistring>\"\"\".*?\"\"\")
    | (?P<string>\"(?:\\.|[^\"\\\n])*\")
    | (?P<number>0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+
                 |(?:\d[\d_]*\.?[\d_]*|\.[\d_]+)(?:[eE][+-]?[\d_]+)?)
    | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<op>\.\.\.|\*\*|//|==|!=|<=|>=|&&|\|\||\?\?=|\?\?|\?\.|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|\+\+|--|<<|>>|=>|[-+*/%<>=!&|^~?:])
    | (?P<punct>[.,;(){}\[\]])
    | (?P<space>\s+)
    | (?P<other>.)
    """,
    re.S | re.X,
)


def _span(cls, text):
    return f'<span class="{cls}">{escape(text)}</span>'


def _highlight_string(raw):
    """Colour a Spark string literal, highlighting ${...} sections."""
    parts = []
    i = 0
    n = len(raw)
    plain = []
    while i < n:
        if raw.startswith("${", i):
            j = i + 2
            depth = 1
            while j < n and depth:
                ch = raw[j]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                j += 1
            if depth == 0:
                if plain:
                    parts.append(escape("".join(plain)))
                    plain = []
                inner = raw[i + 2 : j - 1]
                parts.append(
                    '<span class="tok-interp">${'
                    + _highlight_spark(inner, inline=True)
                    + "}</span>"
                )
                i = j
                continue
        plain.append(raw[i])
        i += 1
    if plain:
        parts.append(escape("".join(plain)))
    return '<span class="tok-string">' + "".join(parts) + "</span>"


def _highlight_spark(code, inline=False):
    out = []
    prev_keyword = None
    prev_punct = ""
    matches = list(_SPARK_TOKEN_RE.finditer(code))
    for index, match in enumerate(matches):
        kind = match.lastgroup
        text = match.group()
        if kind == "space":
            out.append(text)
            prev_punct = ""
            continue
        if kind == "comment":
            out.append(_span("tok-comment", text))
            prev_keyword = None
            prev_punct = ""
            continue
        if kind in ("string", "multistring"):
            out.append(_highlight_string(text))
            prev_keyword = None
            prev_punct = ""
            continue
        if kind == "number":
            out.append(_span("tok-number", text))
            prev_keyword = None
            prev_punct = ""
            continue
        if kind == "ident":
            following = code[match.end() :].lstrip()
            is_call = following.startswith("(")
            if text in SPARK_CONSTANTS:
                cls = "tok-const"
            elif text in SPARK_KEYWORDS:
                cls = "tok-keyword"
            elif text == "self":
                cls = "tok-self"
            elif prev_keyword in ("fn",):
                cls = "tok-funcdef"
            elif prev_keyword in ("class", "new", "extends"):
                cls = "tok-class"
            elif text in SPARK_NATIVES:
                cls = "tok-native"
            elif prev_punct == ".":
                cls = "tok-method" if is_call else "tok-prop"
            elif is_call:
                cls = "tok-func"
            else:
                cls = "tok-ident"
            out.append(_span(cls, text))
            prev_keyword = text if text in SPARK_KEYWORDS else None
            prev_punct = ""
            continue
        if kind == "op":
            out.append(_span("tok-op", text))
            prev_punct = text
            prev_keyword = None
            continue
        if kind == "punct":
            out.append(_span("tok-punct", text))
            prev_punct = text
            prev_keyword = None
            continue
        out.append(escape(text))
        prev_punct = ""
        prev_keyword = None
    return "".join(out)


_BASH_TOKEN_RE = re.compile(
    r"""
      (?P<comment>\#[^\n]*)
    | (?P<string>\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*")
    | (?P<var>\$[A-Za-z_][A-Za-z0-9_]*|\$\{[^}]+\})
    | (?P<number>\b\d+(?:\.\d+)?\b)
    | (?P<flag>(?<=\s)--?[A-Za-z][\w-]*)
    | (?P<op>\|\||&&|>>|<<|[|&;<>])
    | (?P<word>[^\s|&;<>]+)
    | (?P<space>\s+)
    """,
    re.X,
)


def _highlight_bash(code):
    out = []
    at_command = True
    for match in _BASH_TOKEN_RE.finditer(code):
        kind = match.lastgroup
        text = match.group()
        if kind == "space":
            out.append(text)
            continue
        if kind == "comment":
            out.append(_span("tok-comment", text))
            continue
        if kind == "string":
            out.append(_span("tok-string", text))
            at_command = False
            continue
        if kind == "var":
            out.append(_span("tok-var", text))
            at_command = False
            continue
        if kind == "number":
            out.append(_span("tok-number", text))
            continue
        if kind == "flag":
            out.append(_span("tok-attr", text))
            continue
        if kind == "op":
            out.append(_span("tok-op", text))
            at_command = True
            continue
        cls = "tok-command" if at_command else "tok-ident"
        out.append(_span(cls, text))
        at_command = False
    return "".join(out)


_JSON_TOKEN_RE = re.compile(
    r'"(?:\\.|[^"\\])*"|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[{}[\],:]'
)


def _highlight_json(code):
    out = []
    pos = 0
    for match in _JSON_TOKEN_RE.finditer(code):
        out.append(escape(code[pos : match.start()]))
        text = match.group()
        if text.startswith('"'):
            rest = code[match.end() :].lstrip()
            cls = "tok-prop" if rest.startswith(":") else "tok-string"
            out.append(_span(cls, text))
        elif text in ("true", "false", "null"):
            out.append(_span("tok-const", text))
        elif text[0] in "{}[],:":
            out.append(_span("tok-punct", text))
        else:
            out.append(_span("tok-number", text))
        pos = match.end()
    out.append(escape(code[pos:]))
    return "".join(out)


_C_TOKEN_RE = re.compile(
    r"""
      (?P<comment>//[^\n]*|/\*.*?\*/)
    | (?P<pp>\#\s*\w+)
    | (?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
    | (?P<number>\b(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?)\b)
    | (?P<ident>[A-Za-z_]\w*)
    | (?P<punct>[^\sA-Za-z0-9_])
    | (?P<space>\s+)
    """,
    re.S | re.X,
)
C_KEYWORDS = {
    "if", "else", "for", "while", "do", "switch", "case", "default", "break",
    "continue", "return", "goto", "sizeof", "typedef", "struct", "union",
    "enum", "static", "extern", "const", "unsigned", "signed", "void", "int",
    "char", "short", "long", "float", "double", "bool", "true", "false",
    "NULL", "inline", "register", "volatile", "restrict",
}


def _highlight_c(code):
    out = []
    for match in _C_TOKEN_RE.finditer(code):
        kind = match.lastgroup
        text = match.group()
        if kind == "space":
            out.append(text)
        elif kind == "comment":
            out.append(_span("tok-comment", text))
        elif kind == "pp":
            out.append(_span("tok-keyword", text))
        elif kind == "string":
            out.append(_span("tok-string", text))
        elif kind == "number":
            out.append(_span("tok-number", text))
        elif kind == "ident":
            cls = "tok-keyword" if text in C_KEYWORDS else "tok-ident"
            out.append(_span(cls, text))
        else:
            out.append(_span("tok-punct", text))
    return "".join(out)


def highlight(code, lang):
    lang = (lang or "text").lower()
    if lang in ("spark", "sparkl"):
        return _highlight_spark(code)
    if lang in ("bash", "sh", "shell", "console"):
        return _highlight_bash(code)
    if lang == "json":
        return _highlight_json(code)
    if lang in ("c", "h"):
        return _highlight_c(code)
    return escape(code)


COPY_ICON = (
    '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">'
    '<path fill="none" stroke="currentColor" stroke-width="2" '
    'd="M9 9h10v10H9zM5 15V5h10"/></svg>'
)


def code_block(code, lang):
    label = lang or "text"
    if label == "sparkl":
        label = "spark"
    body = highlight(code, lang)
    return (
        '<div class="code-block">'
        '<div class="code-block__bar">'
        f'<span class="code-lang">{escape(label)}</span>'
        '<button class="copy-btn" type="button" aria-label="Copy code">'
        f"{COPY_ICON}<span>Copy</span></button>"
        "</div>"
        f'<pre class="language-{escape(label)}"><code>{body}</code></pre>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

_CONTAINER_RE = re.compile(r"^:::\s*(\w+)\s*(.*)$")
_FENCE_RE = re.compile(r"^(\s*)```([\w+-]*)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")
_HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_SEP_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)


def _is_block_start(line, next_line=""):
    stripped = line.strip()
    if not stripped:
        return True
    if _FENCE_RE.match(line) or _CONTAINER_RE.match(stripped):
        return True
    if _HEADING_RE.match(line) or _HR_RE.match(line):
        return True
    if _LIST_RE.match(line):
        return True
    if stripped.startswith(">"):
        return True
    if "|" in line and _TABLE_SEP_RE.match(next_line):
        return True
    return False


def _split_table_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells = re.split(r"(?<!\\)\|", line)
    return [cell.strip().replace("\\|", "|") for cell in cells]


class MarkdownRenderer:
    def __init__(self, current_url):
        self.current_url = current_url
        self.toc = []
        self.used_ids = set()
        self.heading_count = 0

    def unique_id(self, text):
        base = slugify(text)
        candidate = base
        counter = 2
        while candidate in self.used_ids:
            candidate = f"{base}-{counter}"
            counter += 1
        self.used_ids.add(candidate)
        return candidate

    # -- inline ---------------------------------------------------------
    def inline(self, text):
        placeholders = []

        def code_repl(match):
            placeholders.append(
                f'<code class="inline-code">{escape(match.group(1))}</code>'
            )
            return f"\x00{len(placeholders) - 1}\x00"

        text = re.sub(r"`([^`]+)`", code_repl, text)
        text = escape(text)

        def link_repl(match):
            label = match.group(1)
            target = match.group(2)
            href = resolve_link(target, self.current_url)
            external = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href))
            extra = ' target="_blank" rel="noopener noreferrer"' if external else ""
            return f'<a href="{href}"{extra}>{label}</a>'

        text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link_repl, text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        text = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", text)

        for index, replacement in enumerate(placeholders):
            text = text.replace(f"\x00{index}\x00", replacement)
        return text

    # -- blocks ---------------------------------------------------------
    def convert(self, text):
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return "\n".join(self.blocks(lines))

    def blocks(self, lines):
        out = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue

            fence = _FENCE_RE.match(line)
            if fence:
                lang = fence.group(2)
                i += 1
                buffer = []
                while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                    buffer.append(lines[i])
                    i += 1
                i += 1
                out.append(code_block("\n".join(buffer), lang))
                continue

            container = _CONTAINER_RE.match(line.strip())
            if container:
                kind = container.group(1).lower()
                title = container.group(2).strip()
                i += 1
                buffer = []
                while i < n and not re.match(r"^\s*:::\s*$", lines[i]):
                    buffer.append(lines[i])
                    i += 1
                i += 1
                inner = "\n".join(self.blocks(buffer))
                out.append(self.container(kind, title, inner))
                continue

            heading = _HEADING_RE.match(line)
            if heading:
                level = len(heading.group(1))
                raw = heading.group(2)
                ident = self.unique_id(raw)
                label = self.inline(raw)
                if level <= 2:
                    self.toc.append(
                        {"id": ident, "text": strip_inline(raw), "level": 2}
                    )
                elif level == 3:
                    self.toc.append(
                        {"id": ident, "text": strip_inline(raw), "level": 3}
                    )
                out.append(
                    f'<h{level} id="{ident}">'
                    f'<a class="header-anchor" href="#{ident}" aria-hidden="true">#</a>'
                    f"{label}</h{level}>"
                )
                i += 1
                continue

            if _HR_RE.match(line):
                out.append("<hr>")
                i += 1
                continue

            if "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
                table, i = self.table(lines, i)
                out.append(table)
                continue

            if line.lstrip().startswith(">"):
                buffer = []
                while i < n and lines[i].lstrip().startswith(">"):
                    buffer.append(re.sub(r"^\s*>\s?", "", lines[i]))
                    i += 1
                out.append(f"<blockquote>{self.blocks(buffer)}</blockquote>")
                continue

            if _LIST_RE.match(line):
                listing, i = self.list_block(lines, i)
                out.append(listing)
                continue

            buffer = []
            while i < n and lines[i].strip():
                if buffer and _is_block_start(lines[i], lines[i + 1] if i + 1 < n else ""):
                    break
                buffer.append(lines[i].strip())
                i += 1
            out.append(f"<p>{self.inline(' '.join(buffer))}</p>")
        return out

    def container(self, kind, title, inner):
        classes = {
            "tip": "tip",
            "note": "tip",
            "info": "tip",
            "warning": "warning",
            "warn": "warning",
            "danger": "danger",
            "error": "danger",
            "details": "details",
        }
        css = classes.get(kind, "tip")
        if css == "details":
            summary = title or "Details"
            return (
                f'<details class="custom-block details"><summary>{self.inline(summary)}</summary>'
                f"{inner}</details>"
            )
        heading = f'<p class="custom-block-title">{self.inline(title)}</p>' if title else ""
        return f'<div class="custom-block {css}">{heading}{inner}</div>'

    def table(self, lines, i):
        header = _split_table_row(lines[i])
        separators = _split_table_row(lines[i + 1])
        aligns = []
        for sep in separators:
            sep = sep.strip()
            if sep.startswith(":") and sep.endswith(":"):
                aligns.append("center")
            elif sep.endswith(":"):
                aligns.append("right")
            else:
                aligns.append("left")
        i += 2
        rows = []
        while i < len(lines) and lines[i].strip() and "|" in lines[i]:
            rows.append(_split_table_row(lines[i]))
            i += 1
        head_cells = "".join(
            f'<th style="text-align:{aligns[idx] if idx < len(aligns) else "left"}">'
            f"{self.inline(cell)}</th>"
            for idx, cell in enumerate(header)
        )
        body_rows = []
        for row in rows:
            cells = []
            for idx, cell in enumerate(row):
                align = aligns[idx] if idx < len(aligns) else "left"
                cells.append(f'<td style="text-align:{align}">{self.inline(cell)}</td>')
            body_rows.append("<tr>" + "".join(cells) + "</tr>")
        return (
            '<div class="table-wrapper"><table><thead><tr>'
            + head_cells
            + "</tr></thead><tbody>"
            + "".join(body_rows)
            + "</tbody></table></div>"
        ), i

    def list_block(self, lines, i):
        first = _LIST_RE.match(lines[i])
        base_indent = len(first.group(1))
        ordered = first.group(2).endswith(".")
        items = []
        n = len(lines)
        while i < n:
            match = _LIST_RE.match(lines[i])
            if not match:
                break
            indent = len(match.group(1))
            if indent != base_indent:
                break
            if match.group(2).endswith(".") != ordered:
                break
            item_lines = [match.group(3)]
            i += 1
            while i < n:
                candidate = lines[i]
                if not candidate.strip():
                    lookahead = i + 1
                    while lookahead < n and not lines[lookahead].strip():
                        lookahead += 1
                    if (
                        lookahead < n
                        and len(lines[lookahead]) - len(lines[lookahead].lstrip())
                        > base_indent
                    ):
                        item_lines.append("")
                        i += 1
                        continue
                    break
                candidate_indent = len(candidate) - len(candidate.lstrip())
                if candidate_indent > base_indent:
                    strip = min(len(candidate), base_indent + 2)
                    item_lines.append(candidate[strip:])
                    i += 1
                    continue
                break
            items.append("\n".join(self.blocks(item_lines)))
        tag = "ol" if ordered else "ul"
        body = "".join(f"<li>{item}</li>" for item in items)
        return f"<{tag}>{body}</{tag}>", i


# ---------------------------------------------------------------------------
# Site shell
# ---------------------------------------------------------------------------

def logo_lockup():
    """Inline the provided wordmark so its ink can follow the site theme."""
    svg = (ASSETS / "logo" / "spark-logo.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)
    svg = re.sub(r"<style>.*?</style>", "", svg, flags=re.S)
    svg = re.sub(r'<title id="t">.*?</title>', "", svg, flags=re.S)
    svg = re.sub(r'<desc id="d">.*?</desc>', "", svg, flags=re.S)
    svg = svg.replace(' xmlns:c2pa="http://c2pa.org/manifest"', "")
    svg = svg.replace('width="920" height="320" ', "")
    svg = svg.replace('role="img" aria-labelledby="t d"', 'aria-hidden="true" focusable="false"')
    return svg

SUN_ICON = (
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/>'
    '<path stroke="currentColor" stroke-width="2" d="M12 2v2M12 20v2M2 12h2M20 12h2'
    'M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>'
)
MOON_ICON = (
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">'
    '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" '
    'fill="none" stroke="currentColor" stroke-width="2"/></svg>'
)
SEARCH_ICON = (
    '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">'
    '<circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/>'
    '<path stroke="currentColor" stroke-width="2" d="m16 16 5 5"/></svg>'
)
MENU_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">'
    '<path stroke="currentColor" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>'
)


def rel_root(current_url):
    depth = current_url.count("/")
    return "../" * depth


def nav_html(current_url, root):
    parts = ['<nav class="sidebar-nav" aria-label="Guide navigation">']
    for section in NAV:
        active_section = any(
            f"{section['slug']}/{item['slug']}.html" == current_url
            for item in section["items"]
        )
        parts.append(
            f'<p class="sidebar-section{" is-active" if active_section else ""}">'
            f"{escape(section['title'])}</p><ul>"
        )
        for item in section["items"]:
            url = f"{section['slug']}/{item['slug']}.html"
            active = " class=\"active\"" if url == current_url else ""
            parts.append(
                f'<li><a href="{root}{url}"{active}>{escape(item["title"])}</a></li>'
            )
        parts.append("</ul>")
    parts.append("</nav>")
    return "".join(parts)


def toc_html(toc, root):
    if not toc:
        return ""
    parts = [
        '<aside class="toc" aria-label="Table of contents"><div class="toc-inner">',
        '<p class="toc-title">On this page</p><ul class="toc-list">',
    ]
    for entry in toc:
        cls = "toc-level-3" if entry["level"] == 3 else "toc-level-2"
        parts.append(
            f'<li class="{cls}"><a href="#{entry["id"]}">'
            f'{escape(entry["text"])}</a></li>'
        )
    parts.append("</ul></div></aside>")
    return "".join(parts)


def page_shell(
    *,
    title,
    description,
    current_url,
    body_html,
    toc=None,
    prev=None,
    next_=None,
    body_class="",
    root=None,
):
    if root is None:
        root = rel_root(current_url)
    full_title = f"{title} | {SITE['title']}" if title else SITE["title"]
    toc = toc or []
    nav = nav_html(current_url, root)

    prev_next = ""
    if prev or next_:
        links = ['<nav class="page-nav" aria-label="Page navigation">']
        if prev:
            links.append(
                f'<a class="page-nav__link prev" href="{root}{prev["url"]}">'
                '<span class="page-nav__label">&larr; Previous</span>'
                f'<span class="page-nav__title">{escape(prev["title"])}</span></a>'
            )
        else:
            links.append("<span></span>")
        if next_:
            links.append(
                f'<a class="page-nav__link next" href="{root}{next_["url"]}">'
                '<span class="page-nav__label">Next &rarr;</span>'
                f'<span class="page-nav__title">{escape(next_["title"])}</span></a>'
            )
        links.append("</nav>")
        prev_next = "".join(links)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(full_title)}</title>
<meta name="description" content="{escape(description)}">
<meta property="og:title" content="{escape(full_title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:type" content="website">
<link rel="icon" type="image/svg+xml" href="{root}assets/logo/spark-icon.svg">
<link rel="stylesheet" href="{root}assets/css/style.css">
<script>
(function () {{
  try {{
    var stored = localStorage.getItem('spark-theme');
    if (stored === 'light' || stored === 'dark') {{
      document.documentElement.setAttribute('data-theme', stored);
    }}
  }} catch (e) {{}}
}})();
</script>
</head>
<body class="{body_class}">
<a class="skip-link" href="#main">Skip to content</a>
<header class="navbar">
  <button class="icon-btn menu-toggle" id="menu-toggle" type="button"
          aria-label="Toggle navigation" aria-expanded="false">{MENU_ICON}</button>
  <a class="brand" href="{root}index.html">
    <img class="brand-mark" src="{root}assets/logo/spark-icon.svg" alt=""
         width="30" height="30">
    <span class="brand-name">Spark</span>
    <span class="brand-suffix">Guide</span>
  </a>
  <div class="navbar-links">
    <a href="{root}getting-started/introduction.html">Guide</a>
    <a href="{root}stdlib/overview.html">Reference</a>
    <a class="navbar-github" href="{SITE['repo']}" target="_blank" rel="noopener noreferrer">GitHub</a>
  </div>
  <div class="search" id="search">
    <span class="search-icon">{SEARCH_ICON}</span>
    <input id="search-input" type="search" placeholder="Search the guide"
           autocomplete="off" spellcheck="false" aria-label="Search the guide"
           aria-expanded="false" aria-controls="search-results">
    <kbd class="search-kbd">Ctrl K</kbd>
    <div class="search-results" id="search-results" hidden></div>
  </div>
  <button class="icon-btn theme-toggle" id="theme-toggle" type="button"
          aria-label="Toggle color theme">
    <span class="theme-icon theme-icon--dark">{SUN_ICON}</span>
    <span class="theme-icon theme-icon--light">{MOON_ICON}</span>
  </button>
</header>
<div class="backdrop" id="backdrop" hidden></div>
<div class="layout">
  <aside class="sidebar" id="sidebar">{nav}</aside>
  <main class="content" id="main">
    <article class="content-inner">
{body_html}
{prev_next}
<footer class="page-footer">
  <p>Spark Guide documents Spark {SITE['version']}. Text and code are released
  under the {escape(SITE['license'])} License; the logo is excluded.</p>
  <p class="page-footer__meta">Last updated {escape(SITE['last_updated'])}.
  Spark is <a href="{SITE['repo']}" target="_blank" rel="noopener noreferrer">open source</a>.</p>
</footer>
    </article>
  </main>
  {toc_html(toc, root)}
</div>
<script src="{root}assets/js/search-index.js"></script>
<script src="{root}assets/js/app.js" defer></script>
</body>
</html>
"""




# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

HOME_FEATURES = [
    (
        "{}",
        "Compiled to bytecode",
        "Every program is lexed, parsed into an AST and compiled to a compact "
        "bytecode that runs on a stack virtual machine with fused superinstructions.",
    ),
    (
        "[]",
        "Batteries included",
        "Classes, closures, destructuring, slices, string interpolation, JSON, "
        "regex and a rich standard library. No package manager required.",
    ),
    (
        "⇄",
        "Cooperative concurrency",
        "spawn, yield, join and channels run thousands of logical tasks on one "
        "thread. Blocking socket calls yield only their coroutine.",
    ),
    (
        "://",
        "Networking built in",
        "TCP, UDP, TLS with mandatory verification, an HTTP/1.1 client and "
        "RFC 6455 WebSockets — with explicit timeouts and size limits.",
    ),
    (
        ">_",
        "Real developer tools",
        "REPL, interactive debugger, canonical formatter, linter, bytecode "
        "disassembler and precompiled .sparkc files ship with the interpreter.",
    ),
    (
        "C11",
        "Small enough to read",
        "About 27,000 lines of C11 with one dependency (OpenSSL, for TLS). "
        "The whole pipeline is handwritten and documented.",
    ),
]


def render_home():
    features = "".join(
        f'<div class="feature"><span class="feature-icon" aria-hidden="true">{escape(symbol)}</span>'
        f'<div class="feature-body"><h3>{escape(title)}</h3>'
        f"<p>{escape(text)}</p></div></div>"
        for symbol, title, text in HOME_FEATURES
    )
    sample = code_block(
        """fn fib(n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

for (var i = 0; i < 10; i += 1) {
    print("fib(${i}) =", fib(i));
}""",
        "spark",
    )
    body = f"""
<section class="hero">
  <div class="hero-glow" aria-hidden="true"></div>
  <div class="hero-inner">
    <h1 class="hero-logo">{logo_lockup()}<span class="sr-only">Spark</span></h1>
    <p class="hero-tagline">A small, fast, dynamically typed language with bytecode,
    classes, coroutines and built-in networking — implemented from scratch in C11.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="getting-started/installation.html">Get Started</a>
      <a class="btn btn-secondary" href="getting-started/introduction.html">Read the Guide</a>
    </div>
    <p class="hero-note">Version {SITE['version']}, pre-1.0. MIT licensed.</p>
  </div>
</section>

<section class="home-section home-showcase">
  <div class="showcase-code">{sample}</div>
  <div class="showcase-text">
    <h2>Familiar syntax, unusual reach</h2>
    <p>If you know JavaScript or Python, you can read Spark in minutes. But the
    language ships with the parts most small languages leave out: real classes,
    operator overloading, structured errors, UTF-8 strings and a networking stack
    that suspends coroutines instead of blocking the process.</p>
    <p>The interpreter compiles to bytecode, folds constants, fuses hot
    instructions and runs a mark-and-sweep collector — all in a codebase you can
    sit down and read.</p>
    <a class="text-link" href="getting-started/first-program.html">Start with your first program</a>
  </div>
</section>

<section class="home-section">
  <h2 class="home-heading">Why Spark?</h2>
  <div class="feature-list">{features}</div>
</section>

<section class="home-section home-cta">
  <h2>Ready to write some Spark?</h2>
  <p>Build the interpreter in one command, then work through the guide from
  variables to coroutines and WebSockets.</p>
  <div class="hero-actions">
    <a class="btn btn-primary" href="getting-started/installation.html">Install Spark</a>
    <a class="btn btn-secondary" href="appendix/examples.html">Browse examples</a>
  </div>
</section>
"""
    return page_shell(
        title="",
        description=SITE["description"],
        current_url="index.html",
        body_html=body,
        body_class="home",
    )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

SEARCH_TEXT_LIMIT = 9000


def plain_text(markdown):
    text = re.sub(r"```.*?```", " ", markdown, flags=re.S)
    text = re.sub(r":::\s*\w*", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_|~-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(ASSETS / "css", DIST / "assets" / "css")
    shutil.copytree(ASSETS / "js", DIST / "assets" / "js")
    (DIST / "assets" / "logo").mkdir(parents=True)
    for source in sorted((ASSETS / "logo").glob("*.svg")):
        shutil.copy2(source, DIST / "assets" / "logo" / source.name)

    search_index = []
    missing = []
    link_targets = set()
    built = 0

    for index, page in enumerate(PAGES):
        source = page["src"]
        if not source.exists():
            missing.append(str(source.relative_to(ROOT)))
            continue
        markdown = source.read_text(encoding="utf-8")
        if markdown.startswith("---"):
            # Ignore a frontmatter block if one is present.
            end = markdown.find("\n---", 3)
            if end != -1:
                markdown = markdown[end + 4 :].lstrip("\n")

        renderer = MarkdownRenderer(page["url"])
        content = renderer.convert(markdown)

        for match in re.finditer(r"\]\((@[^)\s]+)\)", markdown):
            target = match.group(1)[1:].split("#")[0]
            if not target.endswith(".html"):
                target += ".html"
            link_targets.add(target)

        body = (
            f'<h1 class="page-title">{escape(page["title"])}</h1>'
            f'<p class="page-description">{escape(page["description"])}</p>'
            f'<div class="page-content">{content}</div>'
        )

        prev_page = PAGES[index - 1] if index > 0 else None
        next_page = PAGES[index + 1] if index + 1 < len(PAGES) else None

        document = page_shell(
            title=page["title"],
            description=page["description"],
            current_url=page["url"],
            body_html=body,
            toc=renderer.toc,
            prev=prev_page,
            next_=next_page,
        )

        destination = DIST / page["url"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(document, encoding="utf-8")
        built += 1

        search_index.append(
            {
                "title": page["title"],
                "section": page["section"],
                "url": page["url"],
                "description": page["description"],
                "headings": [
                    {"id": h["id"], "text": h["text"]} for h in renderer.toc
                ],
                "text": plain_text(markdown)[:SEARCH_TEXT_LIMIT],
            }
        )

    # Home and 404
    (DIST / "index.html").write_text(render_home(), encoding="utf-8")
    not_found = page_shell(
        title="Page not found",
        description="The page you are looking for does not exist.",
        current_url="404.html",
        # Vercel serves this file at whatever URL was requested, so every link
        # and asset must be root-absolute or it breaks at nested depths.
        root="/",
        body_html="""<h1 class="page-title">Page not found</h1>
<p>The page you are looking for does not exist. Try the navigation, or search
the guide with <kbd>Ctrl</kbd> + <kbd>K</kbd>.</p>
<p><a class="btn btn-primary" href="/index.html">Back to the guide</a></p>""",
    )
    (DIST / "404.html").write_text(not_found, encoding="utf-8")

    index_js = "window.SPARK_SEARCH_INDEX = " + json.dumps(
        search_index, ensure_ascii=False, indent=0
    ) + ";\n"
    (DIST / "assets" / "js" / "search-index.js").write_text(
        index_js, encoding="utf-8"
    )

    # Link check
    broken = []
    for target in sorted(link_targets):
        if target in PAGE_BY_URL:
            continue
        if (DIST / target).exists():
            continue
        broken.append(target)

    print(f"Built {built} pages + home + 404 -> {DIST}")
    if broken:
        print("Broken @links:", ", ".join(broken))
    if missing:
        print("Missing content files:")
        for path in missing:
            print("  -", path)
    return 0 if not (broken or missing) else 1


if __name__ == "__main__":
    sys.exit(build())