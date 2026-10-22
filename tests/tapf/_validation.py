"""中文: 本模块独立检查实验的离散路线, 不承担仓库连续几何验证.

English: This module independently checks experimental discrete routes, not warehouse continuous geometry.
"""
from itertools import combinations


# 中文: check_schedule 核对格点运动, 目标和持续占用, 让实验不会只信任求解器报告的代价.
# English: check_schedule checks grid motion, goals and retained occupancy so the experiment does not merely trust solver costs.
def check_schedule(case: dict, output: dict) -> list[list[int]]:
    agents = case["agents"]
    schedule = output["schedule"]
    if set(schedule) != {agent["name"] for agent in agents}:
        raise ValueError("schedule must contain exactly the input agents")
    width, height = case["map"]["dimensions"]
    obstacles = case["map"]["obstacles"]
    routes = []
    for agent in agents:
        rows = schedule[agent["name"]]
        if not rows or [row["t"] for row in rows] != list(range(len(rows))):
            raise ValueError("route times must start at zero and advance by one")
        route = [[row["x"], row["y"]] for row in rows]
        if route[0] != agent["start"] or route[-1] not in agent["potentialGoals"]:
            raise ValueError("route start or goal is invalid")
        for x, y in route:
            if not isinstance(x, int) or not isinstance(y, int) or not (0 <= x < width and 0 <= y < height) or [x, y] in obstacles:
                raise ValueError("route cell is invalid or blocked")
        for a, b in zip(route, route[1:]):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1:
                raise ValueError("route must move to a neighbor or wait")
        routes.append(route)
    horizon = max(map(len, routes))
    held = [route + [route[-1]] * (horizon - len(route)) for route in routes]
    for first, second in combinations(held, 2):
        for tick in range(horizon):
            if first[tick] == second[tick]:
                raise ValueError(f"vertex conflict at tick {tick}, including terminal occupancy")
            if tick and first[tick - 1] == second[tick] and second[tick - 1] == first[tick]:
                raise ValueError(f"edge swap at tick {tick}")
    if output["statistics"]["cost"] != sum(len(route) - 1 for route in routes):
        raise ValueError("reported cost differs from sum of route arrival times")
    if output["statistics"]["makespan"] != horizon - 1:
        raise ValueError("reported makespan differs from latest arrival")
    return [route[-1] for route in routes]
