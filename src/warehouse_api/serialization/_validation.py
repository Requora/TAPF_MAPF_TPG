"""Shape checks and strict JSON hooks used by the contract codec."""
import dataclasses as dc
import math


# 中文: 限制可编码的数据形状及标量, 在递归转换前排除有损对象, 使序列化结果可可靠重放.
# English: Restrict encodable containers and scalars before conversion so serialization rejects
# lossy objects and produces reliable replay data.
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


# 中文: 要求联合类型恰好匹配一个分支, 避免歧义或无匹配时任意选型, 保留明确字段诊断.
# English: Require exactly one matching union branch so ambiguous or unmatched data is rejected with
# a precise field diagnostic.
def validate_union(matches, path):
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one union shape, matched {len(matches)}")


# 中文: 同时检查标记类型和值, 为动作判别提供严格边界, 防止 True 与 1 等相等值被混为同一标签.
# English: Check both tag type and value so discriminator validation does not confuse equal values
# such as True and 1.
def validate_literal(args, data, path):
    if not any(type(data) is type(item) and data == item for item in args):
        raise ValueError(f"{path}: expected one of {args!r}")


# 中文: 限定支持同质 tuple 数组, 让容器恢复有明确元素类型, 对未实现的注解直接报错.
# English: Restrict decoding to homogeneous tuple arrays so element types are explicit and
# unsupported annotations fail directly.
def validate_array(args, data, path):
    if len(args) != 2 or args[1] is not Ellipsis:
        raise TypeError(f"{path}: only homogeneous tuple arrays are supported")
    if not isinstance(data, (list, tuple)):
        raise ValueError(f"{path}: expected an array")


# 中文: 拒绝非对象, 非字符串键和多余字段, 使契约演进错误可见, 避免悄悄忽略拼错的字段.
# English: Reject nonobjects, nonstring keys and unknown fields so contract drift or misspelled
# fields cannot be silently ignored.
def validate_object(fields, data, path):
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")
    if any(type(key) is not str for key in data):
        raise ValueError(f"{path}: object keys must be strings")
    unknown = set(data) - set(fields)
    if unknown:
        raise ValueError(f"{path}: unknown fields {sorted(unknown)}")


# 中文: 仅允许声明了默认值的字段缺省, 区分可空与可省略, 防止 None 类型被误认为隐含默认值.
# English: Allow omission only for fields with declared defaults so nullable fields are not
# incorrectly treated as optional inputs.
def validate_default(field, path):
    if field.default is dc.MISSING and field.default_factory is dc.MISSING:
        raise ValueError(f"{path}: missing required field")


# 中文: 严格恢复标量并保留原始溢出异常, 避免隐式类型转换掩盖输入错误, 为上层提供可定位失败.
# English: Decode scalars strictly and preserve native overflow errors so implicit coercion cannot
# conceal malformed input.
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


# 中文: 作为 JSON 解析钩子拒绝 NaN/Infinity, 在浮点进入契约前失败, 保护后续时间和几何运算.
# English: Reject NaN and Infinity through the JSON parser hook so nonfinite numbers cannot reach
# contract timing or geometry arithmetic.
def reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


# 中文: 从键值对构造对象时拒绝重复键, 防止解析器默认覆盖旧值, 让冲突输入保留可见诊断.
# English: Reject duplicate keys while constructing JSON objects so the parser cannot silently
# overwrite conflicting input fields.
def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result
