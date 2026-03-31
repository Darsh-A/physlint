from __future__ import annotations

import ast
import pathlib

import lsprotocol.types as types
from pygls.lsp.server import LanguageServer

from physlint import engine
from physlint.config import Config, load_config
from physlint.dimensions import dims_to_str
from physlint.symbols import SymbolTable

_SEVERITY: dict[str, types.DiagnosticSeverity] = {
    "UNIT_MISMATCH": types.DiagnosticSeverity.Error,
    "UNIT_CONFLICT": types.DiagnosticSeverity.Error,
    "SCALE_MISMATCH": types.DiagnosticSeverity.Warning,
    "SCALE_CONFLICT": types.DiagnosticSeverity.Warning,
    "UNIT_UNKNOWN": types.DiagnosticSeverity.Information,
    "UNIT_INFERRED": types.DiagnosticSeverity.Hint,
}

server = LanguageServer("physlint", "v0.1.0")

_config: Config = Config()
_doc_symbols: dict[str, SymbolTable] = {}


def _to_lsp(d: engine.Diagnostic) -> types.Diagnostic:
    pos = types.Position(line=d.line - 1, character=d.col)
    return types.Diagnostic(
        range=types.Range(start=pos, end=pos),
        severity=_SEVERITY.get(d.code, types.DiagnosticSeverity.Warning),
        code=d.code,
        source="physlint",
        message=d.message,
    )


def _validate(uri: str, source: str) -> None:
    try:
        diags, symbols = engine.analyze_with_symbols(source, _config)
    except SyntaxError:
        return
    _doc_symbols[uri] = symbols
    server.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(uri=uri, diagnostics=[_to_lsp(d) for d in diags])
    )


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: types.DidOpenTextDocumentParams) -> None:
    _validate(params.text_document.uri, params.text_document.text)


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: types.DidChangeTextDocumentParams) -> None:
    doc = server.workspace.get_text_document(params.text_document.uri)
    _validate(params.text_document.uri, doc.source)


@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def did_save(params: types.DidSaveTextDocumentParams) -> None:
    doc = server.workspace.get_text_document(params.text_document.uri)
    _validate(params.text_document.uri, doc.source)


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(params: types.HoverParams) -> types.Hover | None:
    uri = params.text_document.uri
    symbols = _doc_symbols.get(uri)
    if symbols is None:
        return None

    doc = server.workspace.get_text_document(uri)
    line, col = params.position.line, params.position.character

    try:
        tree = ast.parse(doc.source)
    except SyntaxError:
        return None

    name = _name_at(tree, line + 1, col)
    if name is None:
        return None

    unit = symbols.get(name)
    if unit is None:
        return None

    text = f"**physlint**: `{name}` has unit **{dims_to_str(unit)}**"
    if unit.scale != 1.0:
        text += f" (scale: {unit.scale})"
    return types.Hover(
        contents=types.MarkupContent(kind=types.MarkupKind.Markdown, value=text)
    )


@server.feature(types.INITIALIZED)
def on_initialized(params: types.InitializedParams) -> None:
    _reload_config()


@server.feature(types.WORKSPACE_DID_CHANGE_CONFIGURATION)
def on_config_change(params: types.DidChangeConfigurationParams) -> None:
    _reload_config()
    for uri in list(_doc_symbols):
        doc = server.workspace.get_text_document(uri)
        _validate(uri, doc.source)


def _reload_config() -> None:
    global _config
    folders = server.workspace.folders
    if folders:
        root = next(iter(folders.values())).uri.replace("file://", "")
        cfg_path = pathlib.Path(root) / "physlint.toml"
    else:
        cfg_path = None
    _config = load_config(cfg_path)


def _name_at(tree: ast.Module, lineno: int, col: int) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.lineno == lineno and node.col_offset <= col < node.col_offset + len(node.id):
                return node.id
    return None


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
