"""中文: 该模块提供数据结构检查和严格 JSON 解析回调, 使契约编解码器能够拒绝歧义或有损输入.

English: This module supplies shape checks and strict JSON parser callbacks so the contract codec can reject ambiguous or lossy input.
"""
import dataclasses as dc
import math


# 中文: validate_encoding 检查当前值是否为可编码的容器或标量, 在递归转换前拒绝不支持的对象和会丢失含义的键, 使保存数据可以可靠重放.
# English: validate_encoding checks whether the current value is an encodable container or scalar and
# rejects unsupported objects and lossy keys before recursive conversion so saved data can be replayed
# reliably.
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


# 中文: validate_union 要求数据恰好匹配联合类型的一个候选分支, 并用 path 指出失败字段, 避免解码器在无匹配或有歧义时任意选择类型.
# English: validate_union requires exactly one matching union candidate and uses path to identify the
# failing field so the decoder cannot choose arbitrarily when matches are absent or ambiguous.
def validate_union(matches, path):
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one union shape, matched {len(matches)}")


# 中文: validate_literal 同时核对 Literal 固定标签的类型和值, 使动作类型等标签严格匹配声明, 防止 True 和 1 这类相等值被误认为同一标签.
# English: validate_literal checks both the type and value of fixed Literal tags so action discriminators
# and other tags match their declarations without confusing equal values such as True and 1.
def validate_literal(args, data, path):
    if not any(type(data) is type(item) and data == item for item in args):
        raise ValueError(f"{path}: expected one of {args!r}")


# 中文: validate_array 要求数组数据对应所有元素同型的 tuple 注解, 让解码器明确每个元素的恢复类型, 并对未支持的元组结构直接报错.
# English: validate_array requires array data and a tuple annotation with one common element type so the
# decoder knows how to restore every element and rejects unsupported tuple structures directly.
def validate_array(args, data, path):
    if len(args) != 2 or args[1] is not Ellipsis:
        raise TypeError(f"{path}: only homogeneous tuple arrays are supported")
    if not isinstance(data, (list, tuple)):
        raise ValueError(f"{path}: expected an array")


# 中文: validate_object 检查字典结构, 字符串键和已声明字段, 使数据契约变更或字段拼写错误显式失败, 避免解码器静默丢弃未知字段.
# English: validate_object checks dictionary shape, string keys and declared fields so contract changes
# or misspelled fields fail explicitly instead of being silently discarded by the decoder.
def validate_object(fields, data, path):
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")
    if any(type(key) is not str for key in data):
        raise ValueError(f"{path}: object keys must be strings")
    unknown = set(data) - set(fields)
    if unknown:
        raise ValueError(f"{path}: unknown fields {sorted(unknown)}")


# 中文: validate_default 仅允许具有声明默认值的字段缺省, 使解码器区分字段可取 None 和字段可以省略, 避免凭空补入默认值.
# English: validate_default permits omission only when a field declares a default so the decoder
# distinguishes nullable values from omittable fields instead of inventing defaults.
def validate_default(field, path):
    if field.default is dc.MISSING and field.default_factory is dc.MISSING:
        raise ValueError(f"{path}: missing required field")


# 中文: decode_scalar 按声明类型恢复单个数值, 字符串, 布尔值或空值, 并保留原始浮点溢出异常, 防止隐式类型转换掩盖错误输入.
# English: decode_scalar restores one number, string, boolean or null according to its declared type and
# preserves native floating-point overflow errors so implicit coercion cannot conceal malformed input.
def decode_scalar(cls, data, path):
    """decode_scalar checks scalar types and preserves native float conversion overflow."""
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


# 中文: reject_constant 作为 JSON 解析回调拒绝 NaN 和 Infinity 等非有限数, 让读取在数据进入时间或几何计算前失败.
# English: reject_constant serves as a JSON parser callback that rejects nonfinite numbers such as NaN
# and Infinity so reading fails before those values reach timing or geometry calculations.
def reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


# 中文: unique_object 从 JSON 键值对构造字典时拒绝重复字段名, 防止解析器用新值覆盖旧值, 使冲突输入保留明确错误.
# English: unique_object rejects duplicate field names while constructing a dictionary from JSON key-
# value pairs so the parser cannot overwrite conflicting input without an explicit error.
def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result
