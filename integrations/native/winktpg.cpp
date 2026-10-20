// This wrapper exports speedSolver actions without running a simulator.
#include <generate_graph.h>
#include <speed_solver.h>
#include <iomanip>

// 中文: main 读取已经选定的直线路线, 调用 WinkTPG 的 speedSolver 为机器人计算各段移动的时间和速度.
// 本入口将每段移动的开始时间, 耗时, 初速和末速写入文件, 让 Python 适配器根据真实上游输出构造运动曲线.
// simEnv 在这里仅保存求解器所需的初始状态; 本入口不推进仿真时间, 也不执行机器人动作.
// English: main reads the selected straight route and calls WinkTPG's speedSolver to compute timing and speeds.
// This entry point writes each movement's start time, duration, initial speed and final speed so the Python adapter
// can construct motion curves from actual upstream output. simEnv only stores the initial state needed by the solver;
// this entry point neither advances simulated time nor executes robot actions.
int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::ifstream input(argv[1]);
    auto paths = std::make_shared<Paths>();
    paths->emplace_back();
    int x;
    while (input >> x) paths->front().emplace_back(Location{x, 0}, E, paths->front().size());
    if (paths->front().size() < 2) return 2;
    auto graph = construct_graph(paths);
    std::vector<std::pair<Location, orient>> starts{{paths->front().front().loc, E}};
    std::vector<std::pair<Location, orient>> goals{{paths->front().back().loc, E}};
    auto state = std::make_shared<simEnv>(1, starts, goals, paths->front().size(), 10, 1, 0, 0, 0.01);
    state->plan_time_limit = std::stod(argv[3]);
    speedSolver solver(1, graph, state);
    std::vector<std::vector<action>> actions;
    if (!solver.solve(actions)) return 3;
    if (actions.size() != 1 || actions[0].size() + 1 != paths->front().size()) return 4;
    std::ofstream output(argv[2]);
    output << std::setprecision(17);
    for (const auto& action : actions[0]) {
        if (action.rotate) return 4;
        output << action.start_t << ' ' << action.cost << ' '
               << action.v_s << ' ' << action.v_g << '\n';
    }
    return output.good() ? 0 : 5;
}
