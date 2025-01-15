#!/usr/bin/env python
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
"""Inspect inputs and outputs for NodeBlockFunctions."""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
import ast
from dataclasses import dataclass, field
import importlib
from importlib.resources import files
import inspect
from itertools import chain
import os
from pathlib import Path
from typing import Any, cast, Iterable, Optional
from unittest.mock import patch

from traits.trait_errors import TraitError
import yaml

from CPAC.pipeline.nodeblock import NodeBlockFunction
from CPAC.utils.monitoring import UTLOGGER
from CPAC.utils.outputs import Outputs


def import_nodeblock_functions(
    package_name: str, exclude: Optional[list[str]] = None
) -> list[NodeBlockFunction]:
    """
    Import all functions with the @nodeblock decorator from all modules and submodules in a package.

    Parameters
    ----------
    package_name
        The name of the package to import from.

    exclude
        A list of module names to exclude from the import.
    """
    if exclude is None:
        exclude = []
    functions: list[NodeBlockFunction] = []
    package = importlib.import_module(package_name)
    package_path = package.__path__[0]  # Path to the package directory

    for root, _, package_files in os.walk(package_path):
        for file in package_files:
            if file.endswith(".py") and file != "__init__.py":
                # Get the module path
                rel_path = os.path.relpath(os.path.join(root, file), package_path)
                module_name = f"{package_name}.{rel_path[:-3].replace(os.sep, '.')}"
                if module_name in exclude:
                    continue

                # Import the module
                try:
                    with patch.dict(
                        "sys.modules", {exclusion: None for exclusion in exclude}
                    ):
                        module = importlib.import_module(module_name)
                except (ImportError, TraitError, ValueError) as e:
                    UTLOGGER.debug(f"Failed to import {module_name}: {e}")
                    continue
                # Extract nodeblock-decorated functions from the module
                for _name, obj in inspect.getmembers(
                    module, predicate=lambda obj: isinstance(obj, NodeBlockFunction)
                ):
                    functions.append(obj)

    return functions


@dataclass
class ResourceSourceList:
    """A list of resource sources without duplicates."""

    sources: list[str] = field(default_factory=list)

    def __add__(self, other: "str | list[str] | ResourceSourceList") -> list[str]:
        """Add a list of sources to the list."""
        if isinstance(other, str):
            other = [other]
        new_set = {*self.sources, *other}
        return sorted(new_set, key=str.casefold)

    def __contains__(self, item: str) -> bool:
        """Check if a source is in the list."""
        return item in self.sources

    def __delitem__(self, key: int) -> None:
        """Delete a source by index."""
        del self.sources[key]

    def __eq__(self, value: Any) -> bool:
        """Check if the lists of sources are the same."""
        return set(self) == set(value)

    def __getitem__(self, item: int) -> str:
        """Get a source by index."""
        return self.sources[item]

    def __hash__(self) -> int:
        """Get the hash of the list of sources."""
        return hash(self.sources)

    def __iadd__(
        self, other: "str | list[str] | ResourceSourceList"
    ) -> "ResourceSourceList":
        """Add a list of sources to the list."""
        self.sources = self + other
        return self

    def __iter__(self):
        """Iterate over the sources."""
        return iter(self.sources)

    def __len__(self) -> int:
        """Get the number of sources."""
        return len(self.sources)

    def __repr__(self) -> str:
        """Get the reproducable string representation of the sources."""
        return f"ResourceSourceList({(self.sources)})"

    def __reversed__(self) -> list[str]:
        """Get the sources reversed."""
        return list(reversed(self.sources))

    def __setitem__(self, key: int, value: str) -> None:
        """Set a source by index."""
        self.sources[key] = value

    def __sorted__(self) -> list[str]:
        """Get the sources sorted."""
        return sorted(self.sources, key=str.casefold)

    def __str__(self) -> str:
        """Get the string representation of the sources."""
        return str(self.sources)


class DirectlySetResources(ast.NodeVisitor):
    """Gather resources directly set (rather than in NodeBlocks)."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        super().__init__()
        self._context: dict[str, Any] = {}
        self._history: dict[str, list[Any]] = {}
        self.resources: dict[str, ResourceSourceList] = {}

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

    def assign_resource(self, resource: str, value: str) -> None:
        """Assign a value to a resource."""
        if resource not in self.resources:
            self.resources[resource] = ResourceSourceList()
        self.resources[resource] += value

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

    def resolve_fstring(self, fstring_node: ast.AST, context: dict[str, str]) -> str:
        """Resolve an f-string into a template with placeholders."""
        parts = []
        for part in fstring_node.values:
            if isinstance(part, ast.Constant):
                parts.append(part.value)
            elif isinstance(part, ast.FormattedValue):
                if isinstance(part.value, ast.Name):
                    parts.append(context.get(part.value.id, f"{{{part.value.id}}}"))
        return "".join(parts)

    def visit_Assign(self, node) -> None:
        """Visit an assignment."""
        if isinstance(node.value, ast.Dict):
            for key, value in dict(
                zip(
                    [self.ast_to_str(k) for k in node.value.keys],
                    [
                        self.ast_to_str(v.elts[0] if isinstance(v, ast.Tuple) else v)
                        for v in node.value.values
                    ],
                )
            ).items():
                self.context = str(key), str(value)

    def visit_For(self, node) -> None:
        """Visit for loops."""
        if isinstance(node.iter, ast.Call) and isinstance(
            node.iter.func, ast.Attribute
        ):
            if (
                node.iter.func.attr == "items"
                and self.ast_to_str(node.iter.func) in self.context
            ):
                # Extract the dictionary being iterated
                dictionary = self.context

                # Process the loop body for set_data calls
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        func_call = stmt.value
                        if (
                            isinstance(func_call.func, ast.Attribute)
                            and func_call.func.attr == "set_data"
                        ):
                            # Extract arguments of the set_data call
                            args = func_call.args
                            if len(args) > 5 and isinstance(args[5], ast.JoinedStr):
                                # Resolve the interpolated string
                                literal_string = self.resolve_fstring(
                                    args[5], {"key": list(dictionary.keys())}
                                )
                                for key in dictionary.keys():
                                    self.pairings.append(
                                        (key, literal_string.format(key=key))
                                    )
        self.generic_visit(node)

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
                breakpoint()
                return
                # resource = self.ast_to_str(resource)
                # if resource in self.context:
                #     resource = self.context[resource]
            self.assign_resource(resource, self.ast_to_str(node.args[5]))
            # breakpoint()
        self.generic_visit(node)


@dataclass
class ResourceIO:
    """NodeBlockFunctions that use a resource for IO."""

    name: str
    """The name of the resource."""
    output_from: ResourceSourceList | list[str] = field(
        default_factory=ResourceSourceList
    )
    """The functions that output the resource."""
    output_to: ResourceSourceList | list[str] = field(
        default_factory=ResourceSourceList
    )
    """The subdirectory the resource is output to."""
    input_for: ResourceSourceList | list[str] = field(
        default_factory=ResourceSourceList
    )
    """The functions that use the resource as input."""

    def __post_init__(self) -> None:
        """Handle optionals."""
        if isinstance(self.output_from, list):
            self.output_from = ResourceSourceList(self.output_from)
        if isinstance(self.output_to, list):
            self.output_to = ResourceSourceList(self.output_to)
        if isinstance(self.input_for, list):
            self.input_for = ResourceSourceList(self.input_for)

    def __str__(self) -> str:
        """Return string representation for ResourceIO instance."""
        return f"{{{self.name}: {{'input_for': {self.input_for!s}, 'output_from': {self.output_from!s}}}}})"

    def as_dict(self) -> dict[str, list[str]]:
        """Return the ResourceIO as a built-in dictionary type."""
        return {
            k: v
            for k, v in {
                "input_for": [str(source) for source in self.input_for],
                "output_from": [str(source) for source in self.output_from],
                "output_to": [str(source) for source in self.output_to],
            }.items()
            if v
        }


def cli_parser() -> Namespace:
    """Parse command line argument."""
    parser = ArgumentParser(
        description="Inventory resources for C-PAC NodeBlockFunctions.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        help="The output file to write the inventory to.",
        type=Path,
        default=Path("resource_inventory.yaml"),
    )
    return parser.parse_args()


def _flatten_io(io: list[Iterable]) -> list[str]:
    """Given a list of strings or iterables thereof, flatten the list to all strings."""
    if all(isinstance(resource, str) for resource in io):
        return cast(list[str], io)
    while not all(isinstance(resource, str) for resource in io):
        io = list(
            chain.from_iterable(
                [
                    resource if not isinstance(resource, str) else [resource]
                    for resource in io
                ]
            )
        )
    return cast(list[str], io)


def find_directly_set_resources(package_name: str) -> dict[str, ResourceSourceList]:
    """Find all resources set explicitly via :pyy:method:`~CPAC.pipeline.engine.ResourcePool.set_data`.

    Parameters
    ----------
    package_name
        The name of the package to search for resources.

    Returns
    -------
    dict
        A dictionary containing the name of the resource and the name of the functions that set it.
    """
    resources: dict[str, ResourceSourceList] = {}
    for dirpath, _, filenames in os.walk(str(files(package_name))):
        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, "r", encoding="utf-8") as file:
                    tree = ast.parse(file.read(), filename=filepath)
                    directly_set = DirectlySetResources()
                    directly_set.visit(tree)
                    for resource in directly_set.resources:
                        if resource not in resources:
                            resources[resource] = ResourceSourceList()
                        resources[resource] += directly_set.resources[resource]
    return resources


def resource_inventory(package: str = "CPAC") -> dict[str, ResourceIO]:
    """Gather all inputs and outputs for a list of NodeBlockFunctions."""
    from CPAC.pipeline.engine import template_dataframe

    resources: dict[str, ResourceIO] = {}
    # Node block function inputs and outputs
    for nbf in import_nodeblock_functions(
        package,
        [
            # No nodeblock functions in these modules that dynamically isntall torch
            "CPAC.unet.__init__",
            "CPAC.unet._torch",
        ],
    ):
        nbf_name = f"{nbf.__module__}.{nbf.__qualname__}"
        if hasattr(nbf, "inputs"):
            for nbf_input in _flatten_io(cast(list[Iterable], nbf.inputs)):
                if nbf_input:
                    if nbf_input not in resources:
                        resources[nbf_input] = ResourceIO(
                            nbf_input, input_for=[nbf_name]
                        )
                    else:
                        resources[nbf_input].input_for += nbf_name
        if hasattr(nbf, "outputs"):
            for nbf_output in _flatten_io(cast(list[Iterable], nbf.outputs)):
                if nbf_output:
                    if nbf_output not in resources:
                        resources[nbf_output] = ResourceIO(
                            nbf_output, output_from=[nbf_name]
                        )
                    else:
                        resources[nbf_output].output_from += nbf_name
    # Template resources set from pipeline config
    templates_from_config_df = template_dataframe()
    for _, row in templates_from_config_df.iterrows():
        output_from = f"pipeline configuration: {row.Pipeline_Config_Entry}"
        if row.Key not in resources:
            resources[row.Key] = ResourceIO(row.Key, output_from=[output_from])
        else:
            resources[row.Key].output_from += output_from
    # Hard-coded resources
    for resource, functions in find_directly_set_resources(package).items():
        if resource not in resources:
            resources[resource] = ResourceIO(resource, output_from=functions)
        else:
            resources[resource].output_from += functions
    # breakpoint()
    # Outputs
    for _, row in Outputs.reference.iterrows():
        if row.Resource not in resources:
            resources[row.Resource] = ResourceIO(
                row.Resource, output_to=[row["Sub-Directory"]]
            )
        else:
            resources[row.Resource].output_to += row["Sub-Directory"]
    return dict(sorted(resources.items(), key=lambda item: item[0].casefold()))


def dump_inventory_to_yaml(inventory: dict[str, ResourceIO]) -> str:
    """Dump NodeBlock Interfaces to a YAML string."""
    return yaml.dump(
        {key: value.as_dict() for key, value in inventory.items()}, sort_keys=False
    )


def main() -> None:
    """Save the NodeBlock inventory to a file."""
    args = cli_parser()
    with args.output.open("w") as file:
        file.write(dump_inventory_to_yaml(resource_inventory("CPAC")))


if __name__ == "__main__":
    main()
