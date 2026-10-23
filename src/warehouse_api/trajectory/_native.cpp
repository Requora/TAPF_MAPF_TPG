#include "_validation.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;

// 中文: Curve 保存独立且只读的已校验节点, 避免每次查询重新转换和检查输入.
// English: Curve owns independent read-only validated knots to avoid repeated input conversion and validation.
class Curve {
    const Rows rows;
public:
    // 中文: Curve 构造函数调用集中校验, 建立后续读取所需的曲线结构前提.
    // English: The Curve constructor calls centralized validation to establish prerequisites for later reads.
    explicit Curve(Rows input) : rows(std::move(input)) { check_rows(rows); }

    // 中文: evaluate 读取原 Hermite 曲线与导数, 保留精确节点和静止终点保持语义.
    // English: evaluate reads the original Hermite curve and derivative, preserving exact knots and stationary terminal holds.
    Row evaluate(double t) const {
        check_time(rows, t);
        if (t >= rows.back()[0]) {
            auto result = rows.back();
            result[0] = t;
            return result;
        }
        for (size_t i = 1; i < rows.size(); ++i) {
            const auto &a = rows[i-1], &b = rows[i];
            if (t == a[0]) return a;
            if (t >= b[0]) continue;
            const double h = b[0]-a[0], u = (t-a[0])/h;
            Row result{t};
            for (size_t axis = 1; axis <= 3; ++axis) {
                result[axis] = (2*u*u*u-3*u*u+1)*a[axis] + (u*u*u-2*u*u+u)*h*a[axis+3]
                             + (-2*u*u*u+3*u*u)*b[axis] + (u*u*u-u*u)*h*b[axis+3];
                result[axis+3] = ((6*u*u-6*u)*a[axis]+(-6*u*u+6*u)*b[axis])/h
                              + (3*u*u-4*u+1)*a[axis+3]+(3*u*u-2*u)*b[axis+3];
            }
            check_rows({result});
            return result;
        }
        throw std::invalid_argument("Time not covered");
    }
    // 中文: slice 保留两端及内部切换节点, 使返回区间保持原曲线而不重新规划.
    // English: slice retains endpoints and internal switches so the returned interval preserves the original curve without replanning.
    Rows slice(double a, double b) const {
        check_slice(rows, a, b);
        Rows result{evaluate(a)};
        for (const auto& row : rows)
            if (a < row[0] && row[0] < b) result.push_back(row);
        result.push_back(evaluate(b));
        return result;
    }
};

// 中文: 原生模块只向 Python 包内部暴露快照与计算入口, 由适配层返回统一契约.
// English: The native module exposes snapshots and computation only inside the Python package; adapters return shared contracts.
PYBIND11_MODULE(_native, module) {
    py::class_<Curve>(module, "Curve")
        .def(py::init<Rows>())
        .def("evaluate", &Curve::evaluate)
        .def("slice", &Curve::slice);
}
