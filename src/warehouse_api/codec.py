"""JSON shape conversion for shared contracts, not business or safety validation.

Decoding checks annotations. Encoding accepts dataclasses and JSON-compatible
values. Neither direction checks IDs, quantities, geometry, or stopping safety.
"""
from __future__ import annotations

import dataclasses as dc
import json
import math
import types
import typing as t


def to_data(value):
    """Return fresh JSON-compatible containers without changing the input."""
    if dc.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_data(getattr(value, f.name)) for f in dc.fields(value)}
    if isinstance(value, (tuple, list)):
        return [to_data(item) for item in value]
    if isinstance(value, dict):
        if any(type(key) is not str for key in value):
            raise ValueError("JSON object keys must be strings")
        return {key: to_data(item) for key, item in value.items()}
    if type(value) is float and not math.isfinite(value):
        raise ValueError("NaN and Infinity are not allowed")
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError(f"Unsupported JSON type: {type(value).__name__}")


def from_data(cls, data, path="$"):
    """Decode a contract annotation; malformed values raise ValueError with paths."""
    origin, args = t.get_origin(cls), t.get_args(cls)
    if origin in (t.Union, types.UnionType):
        errors = []
        for member in args:
            try:
                return from_data(member, data, path)
            except ValueError as exc:
                errors.append(str(exc))
        raise ValueError(f"{path}: no union member matched: {errors}")
    if origin is t.Literal:
        if not any(type(data) is type(item) and data == item for item in args):
            raise ValueError(f"{path}: expected one of {args!r}")
        return data
    if origin is tuple:
        if len(args) != 2 or args[1] is not Ellipsis:
            raise TypeError(f"{path}: only homogeneous tuple arrays are supported")
        if not isinstance(data, (list, tuple)):
            raise ValueError(f"{path}: expected an array")
        return tuple(from_data(args[0], item, f"{path}[{i}]")
                     for i, item in enumerate(data))
    if isinstance(cls, type) and dc.is_dataclass(cls):
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected an object")
        if any(type(key) is not str for key in data):
            raise ValueError(f"{path}: object keys must be strings")
        fields = {field.name: field for field in dc.fields(cls)}
        unknown = set(data) - set(fields)
        if unknown:
            raise ValueError(f"{path}: unknown fields {sorted(unknown)}")
        hints = t.get_type_hints(cls)
        values = {}
        for name, field in fields.items():
            if name not in data:
                if field.default is not dc.MISSING or field.default_factory is not dc.MISSING:
                    continue
                raise ValueError(f"{path}.{name}: missing required field")
            values[name] = from_data(hints[name], data[name], f"{path}.{name}")
        return cls(**values)
    if cls is type(None):
        if data is not None:
            raise ValueError(f"{path}: expected null")
        return None
    if cls is float:
        if type(data) not in (int, float):
            raise ValueError(f"{path}: expected a finite number")
        try:
            value = float(data)
        except OverflowError as exc:
            raise ValueError(f"{path}: number exceeds finite float range") from exc
        if not math.isfinite(value):
            raise ValueError(f"{path}: expected a finite number")
        return value
    if cls in (str, int, bool):
        if type(data) is not cls:
            raise ValueError(f"{path}: expected {cls.__name__}")
        return data
    raise TypeError(f"{path}: unsupported annotation {cls}")


def dumps(value) -> str:
    """Encode JSON-compatible data, rejecting non-finite numbers and lossy keys."""
    return json.dumps(to_data(value), ensure_ascii=False, allow_nan=False, indent=2)


def loads(cls, text: str):
    """Parse and decode JSON, rejecting duplicate keys and non-finite constants."""
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    data = json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_object)
    return from_data(cls, data)
