"""Shape checks and strict JSON hooks used by the contract codec."""
import dataclasses as dc
import math


def validate_encoding(value):
    if dc.is_dataclass(value) and not isinstance(value, type):
        return
    if isinstance(value, (tuple, list)):
        return
    if isinstance(value, dict):
        if any(type(key) is not str for key in value):
            raise ValueError("JSON object keys must be strings")
        return
    if type(value) is float and not math.isfinite(value):
        raise ValueError("NaN and Infinity are not allowed")
    if value is not None and type(value) not in (str, int, float, bool):
        raise TypeError(f"Unsupported JSON type: {type(value).__name__}")


def validate_union(matches, path):
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one union shape, matched {len(matches)}")


def validate_literal(args, data, path):
    if not any(type(data) is type(item) and data == item for item in args):
        raise ValueError(f"{path}: expected one of {args!r}")


def validate_array(args, data, path):
    if len(args) != 2 or args[1] is not Ellipsis:
        raise TypeError(f"{path}: only homogeneous tuple arrays are supported")
    if not isinstance(data, (list, tuple)):
        raise ValueError(f"{path}: expected an array")


def validate_object(fields, data, path):
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")
    if any(type(key) is not str for key in data):
        raise ValueError(f"{path}: object keys must be strings")
    unknown = set(data) - set(fields)
    if unknown:
        raise ValueError(f"{path}: unknown fields {sorted(unknown)}")


def validate_default(field, path):
    if field.default is dc.MISSING and field.default_factory is dc.MISSING:
        raise ValueError(f"{path}: missing required field")


def decode_scalar(cls, data, path):
    """Check scalar types and preserve native float conversion overflow."""
    if cls is type(None):
        if data is not None:
            raise ValueError(f"{path}: expected null")
        return None
    if cls is float:
        if type(data) not in (int, float):
            raise ValueError(f"{path}: expected a finite number")
        value = float(data)
        if not math.isfinite(value):
            raise ValueError(f"{path}: expected a finite number")
        return value
    if cls in (str, int, bool):
        if type(data) is not cls:
            raise ValueError(f"{path}: expected {cls.__name__}")
        return data
    raise TypeError(f"{path}: unsupported annotation {cls}")


def reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result
