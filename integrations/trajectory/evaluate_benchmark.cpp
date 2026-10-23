// 中文: 本实验比较有效段内查询, 不是生产 API; Knot 的字段为时间, x/y/未折返朝向, 三轴速度.
// English: This experiment compares valid interior queries, not a production API; Knot stores time, x/y/unwrapped yaw and three velocities.
#include <array>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using Knot = std::array<double, 7>;
using Curve = std::vector<Knot>;

// 中文: check 检查全部有限值与递增时间, 保留 Python 基准的每次输入校验成本.
// English: check validates all finite values and increasing times to retain Python's per-call validation cost.
void check(const Curve& curve) {
    if (curve.empty()) throw std::invalid_argument("Empty curve");
    for (size_t i = 0; i < curve.size(); ++i) {
        for (double value : curve[i])
            if (!std::isfinite(value)) throw std::invalid_argument("Non-finite knot");
        if (i && (!(curve[i][0] > curve[i-1][0]) || !std::isfinite(curve[i][0] - curve[i-1][0])))
            throw std::invalid_argument("Invalid interval");
    }
}

// 中文: evaluate 逐段查找并计算三轴 Hermite 状态, 仅接受本实验的段内时间, 避免暗示完整 API 支持.
// English: evaluate scans intervals and computes three-axis Hermite states, accepting only experiment interior times without claiming full API support.
Knot evaluate(const Curve& curve, double time) {
    check(curve);
    if (!std::isfinite(time) || time < curve.front()[0] || time >= curve.back()[0])
        throw std::invalid_argument("Interior query required");
    for (size_t i = 1; i < curve.size(); ++i) {
        const auto &a = curve[i-1], &b = curve[i];
        if (time == a[0]) return a;
        if (time >= b[0]) continue;
        const double h = b[0] - a[0], u = (time - a[0])/h;
        Knot result{time};
        for (size_t axis = 1; axis <= 3; ++axis) {
            result[axis] = (2*u*u*u-3*u*u+1)*a[axis] + (u*u*u-2*u*u+u)*h*a[axis+3]
                         + (-2*u*u*u+3*u*u)*b[axis] + (u*u*u-u*u)*h*b[axis+3];
            result[axis+3] = ((6*u*u-6*u)*a[axis]+(-6*u*u+6*u)*b[axis])/h
                          + (3*u*u-4*u+1)*a[axis+3]+(3*u*u-2*u)*b[axis+3];
        }
        for (double value : result)
            if (!std::isfinite(value)) throw std::invalid_argument("Non-finite output");
        return result;
    }
    throw std::invalid_argument("Uncovered time");
}

// 中文: main 创建独立车队, 预热三帧后测十五帧, 校验全部输出以防优化器删除计算; 建模和校验结果不计时.
// English: main builds separate fleet curves, warms three frames and measures fifteen, checking all outputs to prevent dead-code removal; setup and result checks are untimed.
int main(int argc, char** argv) {
    // 中文: main 先验证独立三次曲线的段内状态, 防止匀速样本掩盖公式错误.
    // English: main first checks an independent cubic interior state so constant-speed samples cannot hide formula errors.
    const Curve proof{{0, 0, 0, 6, 0, 0, 0}, {2, 8, 8, 14, 12, 8, 12}};
    const Knot actual = evaluate(proof, 0.5), expected{0.5, 0.125, 0.5, 6.125, 0.75, 2, 0.75};
    for (size_t i = 0; i < expected.size(); ++i)
        if (std::abs(actual[i]-expected[i]) > 1e-12) return 4;
    if (argc != 4) return 2;
    const int robots = std::stoi(argv[1]), knots = std::stoi(argv[2]), hz = std::stoi(argv[3]);
    if (robots < 1 || knots < 4 || hz < 10) return 2;
    std::vector<Curve> fleet(robots, Curve(knots));
    for (int robot = 0; robot < robots; ++robot)
        for (int i = 0; i < knots; ++i) fleet[robot][i] = Knot{double(i), double(i), double(robot), 0, 1, 0, 0};
    std::cout << std::setprecision(17);
    for (int repeat = 0; repeat <= 5; ++repeat) {
        for (int frame = 0; frame < 3; ++frame) {
            const double time = (knots-1)/2.0 + 0.125 + double(frame)/hz;
            const auto start = std::chrono::steady_clock::now();
            Curve output;
            for (const auto& curve : fleet) output.push_back(evaluate(curve, time));
            const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now()-start).count();
            for (int robot = 0; robot < robots; ++robot) {
                const Knot expected{time, time, double(robot), 0, 1, 0, 0};
                for (size_t i = 0; i < expected.size(); ++i)
                    if (std::abs(output[robot][i]-expected[i]) > 1e-9) return 3;
            }
            if (repeat) std::cout << ms << '\n';
        }
    }
}
