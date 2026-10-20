// Export speedSolver actions without stepping or implementing a simulator.
#include <generate_graph.h>
#include <speed_solver.h>
#include <iomanip>

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
