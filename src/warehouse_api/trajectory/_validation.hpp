#pragma once
#include <array>
#include <cmath>
#include <stdexcept>
#include <vector>
// 中文: Row 是内部曲线编码, 依次存储时间, x/y/未折返朝向及对应速度; 不作为公共 DTO.
// English: Row privately encodes time, x/y/unwrapped yaw and corresponding velocities; it is not a public DTO.
using Row = std::array<double, 7>;
using Rows = std::vector<Row>;

// 中文: check_rows 集中检查有限节点和正时间间隔, 使原生快照只接收合法曲线结构.
// English: check_rows centralizes finite-knot and positive-interval checks so native snapshots contain valid curve structures.
inline void check_rows(const Rows& rows) {
    if (rows.empty()) throw std::invalid_argument("Empty curve");
    for (size_t i = 0; i < rows.size(); ++i) {
        for (double value : rows[i])
            if (!std::isfinite(value)) throw std::invalid_argument("Non-finite knot");
        if (i && (!(rows[i][0] > rows[i-1][0]) || !std::isfinite(rows[i][0]-rows[i-1][0])))
            throw std::invalid_argument("Invalid interval");
    }
}
// 中文: check_time 拒绝范围外查询, 仅让精确零速终点延伸, 防止错误外推.
// English: check_time rejects uncovered queries and extends only exactly stopped endpoints to prevent extrapolation.
inline void check_time(const Rows& rows, double t) {
    const auto& last = rows.back();
    if (!std::isfinite(t) || t < rows.front()[0]
        || (t > last[0] && (last[4] != 0 || last[5] != 0 || last[6] != 0)))
        throw std::invalid_argument("Time not covered");
}
// 中文: check_slice 检查切片覆盖范围与正时长, 防止生成无效执行区间.
// English: check_slice validates slice coverage and positive duration to prevent invalid execution intervals.
inline void check_slice(const Rows& rows, double a, double b) {
    check_time(rows, a);
    check_time(rows, b);
    if (!(b > a) || !std::isfinite(b-a)) throw std::invalid_argument("Invalid slice interval");
}
