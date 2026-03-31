from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from physlint.config import Config
from physlint.dimensions import DIMENSIONLESS, Unit, dims_to_str
from physlint.parser import parse_unit
from physlint.symbols import SymbolTable

_COMMENT_RE = re.compile(r"#\s*(.+)$")


@dataclass
class Diagnostic:
    line: int
    col: int
    code: str
    message: str


class _Analyzer(ast.NodeVisitor):
    def __init__(self, source: str, config: Config) -> None:
        self._lines = source.splitlines()
        self._config = config
        self._symbols = SymbolTable()
        self._diagnostics: list[Diagnostic] = []

    @property
    def diagnostics(self) -> list[Diagnostic]:
        return self._diagnostics

    @property
    def symbols(self) -> SymbolTable:
        return self._symbols

    def _emit(self, node: ast.AST, code: str, message: str) -> None:
        if code in self._config.ignore_rules:
            return
        self._diagnostics.append(Diagnostic(
            line=node.lineno,
            col=node.col_offset,
            code=code,
            message=message,
        ))

    def _extract_comment_unit(self, lineno: int) -> Unit | None:
        if lineno < 1 or lineno > len(self._lines):
            return None
        m = _COMMENT_RE.search(self._lines[lineno - 1])
        if m is None:
            return None
        return parse_unit(m.group(1).strip())

    def _should_ignore(self, name: str) -> bool:
        return any(name.startswith(p) for p in self._config.ignore_prefix)

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            self.generic_visit(node)
            return

        name = node.targets[0].id
        if self._should_ignore(name):
            self.generic_visit(node)
            return

        annotation_unit = self._extract_comment_unit(node.lineno)
        inferred_unit = self._eval_expr(node.value)

        if annotation_unit is not None and inferred_unit is not None:
            if inferred_unit != DIMENSIONLESS:
                if not annotation_unit.compatible_dims(inferred_unit):
                    self._emit(node, "UNIT_CONFLICT",
                               f"{name}: annotated as {dims_to_str(annotation_unit)} "
                               f"but expression yields {dims_to_str(inferred_unit)}")
                elif self._config.strict_scale and not annotation_unit.compatible(inferred_unit):
                    self._emit(node, "SCALE_CONFLICT",
                               f"{name}: annotated scale {annotation_unit.scale} "
                               f"but expression yields scale {inferred_unit.scale}")
            self._symbols.set(name, annotation_unit)
        elif annotation_unit is not None:
            self._symbols.set(name, annotation_unit)
        elif inferred_unit is not None and inferred_unit != DIMENSIONLESS:
            self._symbols.set(name, inferred_unit)
            self._emit(node, "UNIT_INFERRED",
                       f"{name} → {dims_to_str(inferred_unit)} (inferred)")

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if not isinstance(node.target, ast.Name):
            self.generic_visit(node)
            return

        name = node.target.id
        if self._should_ignore(name):
            self.generic_visit(node)
            return

        unit: Unit | None = None
        if isinstance(node.annotation, ast.Constant) and isinstance(node.annotation.value, str):
            unit = parse_unit(node.annotation.value)

        inferred_unit: Unit | None = None
        if node.value is not None:
            inferred_unit = self._eval_expr(node.value)

        if unit is not None and inferred_unit is not None:
            if inferred_unit != DIMENSIONLESS:
                if not unit.compatible_dims(inferred_unit):
                    self._emit(node, "UNIT_CONFLICT",
                               f"{name}: annotated as {dims_to_str(unit)} "
                               f"but expression yields {dims_to_str(inferred_unit)}")
                elif self._config.strict_scale and not unit.compatible(inferred_unit):
                    self._emit(node, "SCALE_CONFLICT",
                               f"{name}: annotated scale {unit.scale} "
                               f"but expression yields scale {inferred_unit.scale}")

        if unit is not None:
            self._symbols.set(name, unit)
        elif inferred_unit is not None and inferred_unit != DIMENSIONLESS:
            self._symbols.set(name, inferred_unit)
            self._emit(node, "UNIT_INFERRED",
                       f"{name} → {dims_to_str(inferred_unit)} (inferred)")

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        saved: dict[str, Unit | None] = {}

        for arg in node.args.args:
            ann = arg.annotation
            if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
                unit = parse_unit(ann.value)
                if unit is not None:
                    saved[arg.arg] = self._symbols.get(arg.arg)
                    self._symbols.set(arg.arg, unit)

        ret_ann = node.returns
        if isinstance(ret_ann, ast.Constant) and isinstance(ret_ann.value, str):
            ret_unit = parse_unit(ret_ann.value)
            if ret_unit is not None:
                saved["__return__"] = self._symbols.get("__return__")
                self._symbols.set("__return__", ret_unit)

        self.generic_visit(node)

        for name, prev in saved.items():
            if prev is None:
                self._symbols.remove(name)
            else:
                self._symbols.set(name, prev)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _eval_expr(self, node: ast.expr) -> Unit | None:
        if isinstance(node, ast.BinOp):
            return self._eval_binop(node)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return self._eval_expr(node.operand)
        if isinstance(node, ast.Name):
            return self._symbols.get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return DIMENSIONLESS
        if isinstance(node, ast.Call):
            return self._eval_call(node)
        return None

    def _eval_binop(self, node: ast.BinOp) -> Unit | None:
        left = self._eval_expr(node.left)
        right = self._eval_expr(node.right)

        if isinstance(node.op, (ast.Add, ast.Sub)):
            if left is None or right is None:
                return left or right
            if not left.compatible_dims(right):
                verb = "add" if isinstance(node.op, ast.Add) else "subtract"
                self._emit(node, "UNIT_MISMATCH",
                           f"cannot {verb} {dims_to_str(left)} and {dims_to_str(right)}")
                return left
            if self._config.strict_scale and not left.compatible(right):
                self._emit(node, "SCALE_MISMATCH",
                           f"scale mismatch: {left.scale} vs {right.scale}")
            return left

        if isinstance(node.op, ast.Mult):
            return left * right if left is not None and right is not None else None

        if isinstance(node.op, (ast.Div, ast.FloorDiv)):
            return left / right if left is not None and right is not None else None

        if isinstance(node.op, ast.Pow) and left is not None:
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):
                return left ** node.right.value
            if (isinstance(node.right, ast.UnaryOp)
                    and isinstance(node.right.op, ast.USub)
                    and isinstance(node.right.operand, ast.Constant)
                    and isinstance(node.right.operand.value, int)):
                return left ** (-node.right.operand.value)

        return None

    def _eval_call(self, node: ast.Call) -> Unit | None:
        if isinstance(node.func, ast.Name):
            if self._symbols.has(node.func.id):
                return self._symbols.get(node.func.id)
            ret = self._symbols.get("__return__")
            return ret if ret else None
        return None


def analyze(source: str, config: Config | None = None) -> list[Diagnostic]:
    if config is None:
        config = Config()
    analyzer = _Analyzer(source, config)
    analyzer.visit(ast.parse(source))
    return analyzer.diagnostics


def analyze_with_symbols(
    source: str, config: Config | None = None,
) -> tuple[list[Diagnostic], SymbolTable]:
    if config is None:
        config = Config()
    analyzer = _Analyzer(source, config)
    analyzer.visit(ast.parse(source))
    return analyzer.diagnostics, analyzer.symbols
