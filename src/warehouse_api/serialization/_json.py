"""中文: 该模块在共享数据契约和 JSON 结构间转换, 以便保存与重放. 解码器检查类型注解; 编码器接受数据类和 JSON 兼容值. 两个方向均不检查标识, 数量业务规则, 几何或停车安全.

English: This module converts shared contracts to and from JSON shapes for persistence and replay. Decoding checks annotations; encoding accepts dataclasses and JSON-compatible values. Neither direction checks identifiers, quantity business rules, geometry or stopping safety.
"""
from __future__ import annotations

import dataclasses as dc
import json
import types
import typing as t

from . import _validation as validation


# 中文: to_data 将模块间共享的数据契约递归复制成 JSON 支持的字典, 数组和标量, 使保存结果不会共享或修改输入中的可变容器.
# English: to_data recursively copies inter-module data contracts into JSON-compatible dictionaries,
# arrays and scalars so saved output neither shares nor mutates input containers.
def to_data(value):
    """to_data returns fresh JSON-compatible containers without changing the input."""
    validation.validate_encoding(value)
    if dc.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_data(getattr(value, f.name)) for f in dc.fields(value)}
    if isinstance(value, (tuple, list)):
        return [to_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_data(item) for key, item in value.items()}
    return value


# 中文: _matches_union_member 根据外层数据结构和 Literal 固定标签值判断联合类型的候选分支, 为后续递归解码保留精确字段错误, 避免通过捕获异常猜测类型.
# English: _matches_union_member checks a union candidate using the outer data shape and fixed Literal
# tag values so later recursive decoding retains precise field errors without guessing types through
# caught exceptions.
def _matches_union_member(cls, data):
    """_matches_union_member checks outer shape and Literal tags; decoding checks nested values."""
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


# 中文: from_data 按类型注解递归恢复模块间共享的数据契约, 并用 path 标记错误所在字段, 使结构错误在读取入口暴露, 避免错误数据进入求解器.
# English: from_data recursively restores inter-module data contracts from type annotations and uses path
# to identify failing fields so malformed shapes fail at the read boundary before reaching solvers.
def from_data(cls, data, path="$"):
    """from_data decodes contract shapes and propagates errors, including native float overflow."""
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


# 中文: dumps 将数据写成便于检查的严格 JSON 文本, 并拒绝非有限数和会丢失含义的字典键, 使保存后的实验输入可以忠实重放.
# English: dumps writes inspectable strict JSON and rejects nonfinite numbers and dictionary keys that
# would lose meaning so persisted experiment inputs can be replayed faithfully.
def dumps(value) -> str:
    """dumps encodes JSON-compatible data and rejects non-finite numbers and lossy keys."""
    return json.dumps(to_data(value), ensure_ascii=False, allow_nan=False, indent=2)


# 中文: loads 解析严格 JSON 并恢复指定的数据契约, 同时拒绝重复字段名和非有限数, 防止输入文件通过覆盖字段隐藏错误.
# English: loads parses strict JSON and restores the requested data contract while rejecting duplicate
# field names and nonfinite numbers so overwritten fields cannot conceal invalid input.
def loads(cls, text: str):
    """loads parses and decodes JSON while rejecting duplicate keys and non-finite constants."""
    data = json.loads(text, parse_constant=validation.reject_constant,
                      object_pairs_hook=validation.unique_object)
    return from_data(cls, data)
