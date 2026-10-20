"""中文: 本模块比较真实上游的目标分配与联合搜索, 为仓库适配前的研究保留可重放证据.

English: This module compares real upstream goal assignment and joint search, retaining replayable evidence before warehouse adaptation.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
from itertools import permutations
import json
from pathlib import Path

from warehouse_api.native_process import run_native
from ._validation import check_schedule


# 中文: scenario 定义双机器人会车口样例, 让相同独立距离的两种分配暴露不同的冲突代价.
# English: scenario defines a two-robot passing-bay case so equal independent-distance assignments expose different conflict costs.
def scenario() -> dict:
    return {
        "map": {"dimensions": [5, 2], "obstacles": [[0, 1], [1, 1], [3, 1], [4, 1]]},
        "agents": [
            {"name": "agent0", "start": [0, 0], "potentialGoals": [[3, 0], [4, 0]]},
            {"name": "agent1", "start": [1, 0], "potentialGoals": [[3, 0], [4, 0]]},
        ],
    }


# 中文: invoke 运行一个原生程序并读取 YAML 输出, 复用进程证据和超时边界以避免接受旧结果.
# English: invoke runs one native executable and reads YAML output, reusing process evidence and timeouts to avoid stale results.
def invoke(binary: Path, source: Path, output: Path, budget_s: float) -> dict:
    import yaml  # Optional research dependency; normal package tests do not need PyYAML.

    command = [str(binary.resolve()), "-i", str(source.resolve()), "-o", str(output.resolve())]
    failure = run_native(command, output, budget_s=budget_s, request_id=output.stem)
    if failure is not None:
        raise RuntimeError(f"{failure.code}: {failure.message}")
    return yaml.safe_load(output.read_text())


# 中文: compare 枚举这个双目标样例的全部分配并运行 CBS, 再比较联合 CBS-TA, 使结论不依赖分配器的平局顺序.
# CBS 为固定目标的冲突搜索, CBS-TA 同时搜索目标分配; 本函数要求空证据目录以隔离重跑, 不产生仓库 ExecutableProposal.
# English: compare runs CBS for every assignment in this two-goal case and compares joint CBS-TA, avoiding dependence on assignment tie order.
# CBS searches fixed-goal routes; CBS-TA also searches assignments. This function requires an empty evidence directory to isolate reruns and produces no warehouse ExecutableProposal.
def compare(binaries: Path, directory: Path, budget_s: float = 10) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise FileExistsError("comparison requires an empty evidence directory")
    case = scenario()
    source = directory / "joint-input.json"
    source.write_text(json.dumps(case, indent=2))
    costs = directory / "costs.txt"
    costs.write_text("agent0->goal0:3\nagent0->goal1:4\nagent1->goal0:2\nagent1->goal1:3\n")
    assignment = invoke(binaries / "assignment", costs, directory / "assignment.yaml", budget_s)
    goals = case["agents"][0]["potentialGoals"]
    mapping = assignment["assignment"]
    if set(mapping) != {"agent0", "agent1"} or set(mapping.values()) != {"goal0", "goal1"} or assignment["cost"] != 6:
        raise ValueError("upstream assignment is not a complete minimum-distance matching")
    fixed = []
    for index, targets in enumerate(permutations(goals)):
        problem = deepcopy(case)
        for agent, target in zip(problem["agents"], targets):
            agent["goal"] = target
            agent["potentialGoals"] = [target]
        input_path = directory / f"fixed-{index}-input.json"
        input_path.write_text(json.dumps(problem, indent=2))
        output = invoke(binaries / "cbs", input_path, directory / f"fixed-{index}.yaml", budget_s)
        output["goals"] = check_schedule(problem, output)
        fixed.append(output)
    joint = invoke(binaries / "cbs_ta", source, directory / "joint.yaml", budget_s)
    joint["goals"] = check_schedule(case, joint)
    if joint["statistics"]["cost"] != min(row["statistics"]["cost"] for row in fixed):
        raise ValueError("joint search did not match the enumerated fixed-assignment optimum")
    selected = [goals[int(mapping[agent["name"]][-1])] for agent in case["agents"]]
    baseline = next(row for row in fixed if row["goals"] == selected)
    result = {
        "case": case, "assignment": assignment, "selected_baseline": baseline, "fixed": fixed, "joint": joint,
        "scope": "Discrete point robots only; no warehouse actions, continuous safety, TPG or Runtime.",
        "budget_s_per_call": budget_s, "seed": None,
        "upstream": json.loads((binaries / "provenance.json").read_text()),
        "binary_sha256": {name: sha256((binaries / name).read_bytes()).hexdigest()
                          for name in ("assignment", "cbs", "cbs_ta")},
    }
    (directory / "comparison.json").write_text(json.dumps(result, indent=2))
    template = Path(__file__).with_name("replay.html").read_text()
    (directory / "replay.html").write_text(template.replace("__EVIDENCE__", json.dumps(result).replace("<", "\\u003c")))
    return result


# 中文: main 提供可复现的命令入口并输出实际代价, 让用户快速找到完整输入, 日志和重放.
# English: main provides a reproducible command and prints actual costs so users can quickly locate inputs, logs and replay.
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binaries", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget", type=float, default=10, help="wall-clock seconds per native call")
    args = parser.parse_args()
    result = compare(args.binaries, args.output, args.budget)
    print(json.dumps({"fixed_costs": [row["statistics"]["cost"] for row in result["fixed"]],
                      "selected_baseline_cost": result["selected_baseline"]["statistics"]["cost"],
                      "joint_cost": result["joint"]["statistics"]["cost"], "evidence": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
