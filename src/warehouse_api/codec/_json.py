"""JSON shape conversion for shared contracts, not business or safety validation.

Decoding checks annotations. Encoding accepts dataclasses and JSON-compatible
values. Neither direction checks IDs, quantities, geometry, or stopping safety.
"""
from __future__ import annotations

import dataclasses as dc
import json
import types
import typing as t

from . import _validation as validation


def to_data(value):
    """Return fresh JSON-compatible containers without changing the input."""
    validation.validate_encoding(value)
    if dc.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_data(getattr(value, f.name)) for f in dc.fields(value)}
    if isinstance(value, (tuple, list)):
        return [to_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_data(item) for key, item in value.items()}
    return value


def _matches_union_member(cls, data):
    """Select by outer shape and Literal tags; decoding checks nested values."""
    if isinstance(cls, type) and dc.is_dataclass(cls):
        if not isinstance(data, dict):
            return False
        fields = {field.name: field for field in dc.fields(cls)}
        required = {name for name, field in fields.items()
                    if field.default is dc.MISSING and field.default_factory is dc.MISSING}
        if not required <= data.keys() <= fields.keys():
            return False
        hints = t.get_type_hints(cls)
        return all(t.get_origin(hints[name]) is not t.Literal or
                   any(type(value) is type(tag) and value == tag
                       for tag in t.get_args(hints[name]))
                   for name, value in data.items())
    if t.get_origin(cls) is tuple:
        return isinstance(data, (list, tuple))
    if cls is float:
        return type(data) in (int, float)
    return type(data) is cls


def from_data(cls, data, path="$"):
    """Decode contract shapes; errors propagate, including native float overflow."""
    origin, args = t.get_origin(cls), t.get_args(cls)
    if origin in (t.Union, types.UnionType):
        matches = [member for member in args if _matches_union_member(member, data)]
        validation.validate_union(matches, path)
        return from_data(matches[0], data, path)
    if origin is t.Literal:
        validation.validate_literal(args, data, path)
        return data
    if origin is tuple:
        validation.validate_array(args, data, path)
        return tuple(from_data(args[0], item, f"{path}[{i}]")
                     for i, item in enumerate(data))
    if isinstance(cls, type) and dc.is_dataclass(cls):
        fields = {field.name: field for field in dc.fields(cls)}
        validation.validate_object(fields, data, path)
        hints = t.get_type_hints(cls)
        values = {}
        for name, field in fields.items():
            if name not in data:
                validation.validate_default(field, f"{path}.{name}")
                continue
            values[name] = from_data(hints[name], data[name], f"{path}.{name}")
        return cls(**values)
    return validation.decode_scalar(cls, data, path)


def dumps(value) -> str:
    """Encode JSON-compatible data, rejecting non-finite numbers and lossy keys."""
    return json.dumps(to_data(value), ensure_ascii=False, allow_nan=False, indent=2)


def loads(cls, text: str):
    """Parse and decode JSON, rejecting duplicate keys and non-finite constants."""
    data = json.loads(text, parse_constant=validation.reject_constant,
                      object_pairs_hook=validation.unique_object)
    return from_data(cls, data)
