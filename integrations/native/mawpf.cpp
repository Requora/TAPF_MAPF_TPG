// This wrapper exports upstream robot states without implementing path search.
#include <lacam.hpp>
#include <fstream>
#include <iomanip>

// 中文: main 读取地图, 起点和终点, 调用 MAWPF 项目中的 LaCAM 路径搜索算法, 再把机器人状态写入文件.
// 每个状态包含位置, 朝向, 线速度和角速度, Python 适配器用这些真实结果生成本仓库的移动步骤.
// 本入口直接选择起止状态, 避开上游命令行程序遗漏角速度维度的索引问题; 路径搜索仍由上游算法完成.
// English: main reads the map, start and goal, calls the MAWPF project's LaCAM path-search algorithm,
// and writes robot states to a file. Each state contains position, heading, linear speed and angular speed;
// the Python adapter uses these actual results to produce this repository's movement steps.
// This entry point selects states directly to avoid the upstream command-line index's missing angular-speed dimension;
// the upstream algorithm still performs the search.
int main(int argc, char** argv) {
    if (argc != 6) return 2;
    Graph graph(argv[1], 2, 1, 1);
    const int start_x = std::stoi(argv[3]), goal_x = std::stoi(argv[4]);
    Vertex* start = nullptr;
    Vertex* goal = nullptr;
    for (auto vertex : graph.V) {
        if (vertex->y != 0 || vertex->dir != 0 || vertex->speed != 0 || vertex->omega != 0) continue;
        if (vertex->x == start_x) start = vertex;
        if (vertex->x == goal_x) goal = vertex;
    }
    if (!start || !goal) return 2;
    // 中文: 上面的循环按状态属性选择顶点, 因为上游命令行程序的 U 索引没有包含 omega(角速度)维度.
    // English: The loop above selects vertices by state attributes because the upstream command-line U index omits omega (angular speed).
    Instance instance(2, 1, 1, &graph, Config{start}, Config{goal}, 1);
    instance.delete_graph_after_used = false;
    Deadline deadline(std::stod(argv[5]) * 1000);
    auto [solution, elapsed, ratio] = solve(instance, Algorithm::LACAM, 0, &deadline, 0);
    if (solution.empty()) return 3;
    if (!is_feasible_solution(instance, solution, 0)) return 4;
    std::ofstream output(argv[2]);
    output << std::setprecision(17);
    for (const auto& state : solution) {
        const auto vertex = state[0];
        output << vertex->x << ' ' << vertex->y << ' ' << vertex->dir << ' '
               << vertex->speed << ' ' << vertex->omega << '\n';
    }
    return output.good() ? 0 : 5;
}
