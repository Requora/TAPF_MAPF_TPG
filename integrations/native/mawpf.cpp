// Export actual upstream states. The wrapper implements no path search.
#include <lacam.hpp>
#include <fstream>
#include <iomanip>

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
    // Avoid the upstream CLI's old U indexing, which omits the omega dimension.
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
