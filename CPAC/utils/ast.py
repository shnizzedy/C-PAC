# Copyright (C) 2025  C-PAC Developers

# This file is part of C-PAC.

# C-PAC is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# C-PAC is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with C-PAC. If not, see <https://www.gnu.org/licenses/>.
"""Abstract syntax tree (AST) utilities for C-PAC."""

import ast
from typing import Any


class DirectlySetResources(ast.NodeVisitor):
    """Gather resources directly set (rather than in NodeBlocks)."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        super().__init__()
        self._context: dict[str, Any] = {}
        self._history: dict[str, list[Any]] = {}
        self.resources: dict[str, list[str]] = {}

    @property
    def context(self) -> dict[str, Any]:
        """Return the context."""
        return self._context

    @context.setter
    def context(self, value: tuple[str, Any]) -> None:
        """Set the context."""
        key, _value = value
        self._context[key] = _value
        if key not in self._history:
            self._history[key] = []
        self._history[key].append(_value)

    def ast_to_str(self, abstract: ast.AST) -> str:
        """Return a string representation of an AST."""
        if isinstance(abstract, ast.FormattedValue):
            value_id = getattr(abstract.value, "id", self.ast_to_str(abstract.value))
            if value_id in self.context:
                value = self.context[value_id]
                if isinstance(value, ast.AST):
                    if hasattr(value, "values"):
                        for subvalue in getattr(value, "values", []):
                            if hasattr(subvalue, "value"):
                                if (
                                    self.ast_to_str(
                                        getattr(subvalue, "value", subvalue)
                                    )
                                    == value_id
                                ):
                                    value = self.ast_to_str(self._history[value_id][-2])
            else:
                value = value_id
            if isinstance(value, ast.AST):
                value = self.ast_to_str(value)
            return value
        if isinstance(abstract, ast.Call):
            _func = getattr(abstract, "func")
            if hasattr(_func, "attr") and bool(getattr(_func, "attr", False)):
                if hasattr(_func, "value") and hasattr(_func.value, "id"):
                    _func = ".".join([_func.value.id, _func.attr])
                else:
                    _func = self.ast_to_str(_func)
            return (
                f"{_func}({', '.join(self.ast_to_str(arg) for arg in abstract.args)})"
            )
        if hasattr(abstract, "values"):
            return "".join(
                self.ast_to_str(value) for value in getattr(abstract, "values")
            )
        if hasattr(abstract, "value"):
            value = getattr(abstract, "value")
            if isinstance(value, ast.AST):
                return self.ast_to_str(value)
            if isinstance(value, str):
                return value
        if hasattr(abstract, "id"):
            return getattr(abstract, "id")
        return str(abstract)

    # def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
    #     """Visit a function definition."""
    #     self._process_function_args(node)
    #     self.generic_visit(node)

    # def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
    #     """Visit an async function definition."""
    #     self._process_function_args(node)
    #     self.generic_visit(node)

    # def visit_Assign(self, node: ast.Assign) -> None:
    #     """Visit an assignment."""
    #     for target in node.targets:
    #         if isinstance(target, ast.Name):
    #             self.context = target.id, node.value
    #     self.generic_visit(node)

    # def visit_Subscript(self, node: ast.Subscript) -> None:
    #     """Visit a subscript."""
    #     if isinstance(node.value, ast.AST):
    #         self.visit(node.value)
    #     self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Visit a for loop."""
        if isinstance(node.iter, ast.Call) and isinstance(
            node.iter.func, ast.Attribute
        ):
            if node.iter.func.attr == "items":
                # Extract the dictionary name
                dict_name = node.iter.func.value.id

                # Process the loop body for set_data calls
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        func_call = stmt.value
                        if isinstance(func_call.func, ast.Attribute):
                            if func_call.func.attr == "set_data":
                                # Extract arguments of the set_data call
                                args = func_call.args
                                if len(args) > 5:  # Ensure enough arguments
                                    key = args[0].id  # The dictionary key
                                    generated_name = args[5].value  # Generated string
                                    self.pairings.append((key, generated_name))

        # Continue visiting the rest of the tree
        self.generic_visit(node)
        # elts_id = getattr(getattr(node.target, "elts", [None])[0], "id", "")
        # if (
        #     hasattr(node.iter, "func")
        #     and hasattr(node.iter.func, "attr")
        #     and node.iter.func.attr == "items"
        #     and elts_id == "key"
        # ):
        #     try:
        #         self.context = (
        #             elts_id,
        #             self.ast_to_str(
        #                 self.context[
        #                     getattr(
        #                         node.iter.func.value,
        #                         "id",
        #                         self.ast_to_str(node.iter.func),
        #                     )
        #                 ]
        #             ),
        #         )
        #     except (AttributeError, KeyError):
        #         return
        # self.context = self.ast_to_str(node.target), self.ast_to_str(node.iter)
        # self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit a function call."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "set_data":
            if hasattr(node.args[0], "value"):
                resource: str = getattr(node.args[0], "value")
            elif hasattr(node.args[0], "id"):
                resource_id = str(getattr(node.args[0], "id", ""))
                resource = self.context.get(resource_id, resource_id)
                if hasattr(resource, "values"):
                    _r_parts = []
                    for part in getattr(resource, "values", []):
                        if hasattr(part, "id"):
                            _r_parts.append(
                                self.context.get(part.id, self.ast_to_str(part.id))
                            )
                        else:
                            _formatted = self.ast_to_str(part)
                            if (
                                _formatted == resource_id
                                and len(self._history.get(resource_id, [])) > 1
                            ):
                                _formatted = f"{{{self.ast_to_str(self._history[resource_id][-2])}}}"
                            _r_parts.append(_formatted)
                    resource = "".join(_r_parts)
                if isinstance(resource, ast.Call):
                    resource_id: str = getattr(
                        getattr(resource.func, "value", ""),
                        "id",
                        self.ast_to_str(resource),
                    )
                    if resource_id in self.context:
                        resource_id = self.context[resource_id]
                        if isinstance(resource_id, ast.AST):
                            resource_id = self.ast_to_str(resource_id)
                        resource_id = f"{{{resource_id}}}"
                    resource = f"{resource_id}.{getattr(resource.func, 'attr', resource_id)}({', '.join(self.ast_to_str(arg) for arg in resource.args)})"
            else:
                return
            if not isinstance(resource, str):
                return
                # resource = self.ast_to_str(resource)
                # if resource in self.context:
                #     resource = self.context[resource]
            if resource not in self.resources:
                self.resources[resource] = []
            self.resources[resource].append(self.ast_to_str(node.args[5]))
            breakpoint()
        self.generic_visit(node)

    # def _process_function_args(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
    #     """Process function arguments."""
    #     for arg in node.args.args:
    #         self.context = arg.arg, f"{node.name} parameter: {arg.arg}"
