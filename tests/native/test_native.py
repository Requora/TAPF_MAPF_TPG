"""Exercise real binaries and exact Hermite kinematics, not collision-safety claims."""
from dataclasses import replace
import json
import os
from pathlib import Path
import unittest

from .replay import run, scenario
from warehouse_api.allocation import SingleShelfAllocator
from warehouse_api.contracts import ExecutableProposal, Failure, RobotSpec


# 中文: NativeSubsetTests 测试类无需原生程序即可检查分配器的拒绝条件. 这些测试让库存不足和多机器人限制在缺少集成环境时仍可验证.
# English: NativeSubsetTests checks subset rejection without native binaries so stock infeasibility and multi-robot
# limits remain visible even without an integration environment.
class NativeSubsetTests(unittest.TestCase):
    # 中文: 本测试分别触发库存无解和多车不支持, 防止适配器静默忽略约束后继续规划.
    # English: This test triggers stock infeasibility and unsupported multi-robot input so adapters cannot
    # silently ignore constraints and continue planning.
    def test_infeasible_stock_and_multiple_robots_are_explicit_failures(self):
        _, model, request = scenario(stock=0)
        self.assertEqual(SingleShelfAllocator(model).allocate(request.assignment).code, "NO_PLAN")
        model = replace(model, robots=model.robots + (RobotSpec("B", model.robots[0].footprint),))
        self.assertEqual(SingleShelfAllocator(model).allocate(request.assignment).code, "UNSUPPORTED")


# 中文: NativeChainTests 测试类用实际编译的上游程序验证受支持的规划链. 原生执行证据不同于使用固定替身输出的 fixture 测试, 运动学检查也不证明无碰撞.
# English: NativeChainTests exercises the supported chain with real upstream binaries, separating native evidence from
# fixed-output test doubles, and kinematic checks from collision proofs.
@unittest.skipUnless(os.environ.get("WAREHOUSE_NATIVE_BIN"), "set WAREHOUSE_NATIVE_BIN for real upstream integration")
class NativeChainTests(unittest.TestCase):
    # 中文: run_chain 方法运行真实规划链, 核对阶段顺序和六次原生命令成功. 多个案例复用这些断言, 防止替身或未运行的程序冒充成功结果.
    # English: run_chain runs the real chain and checks stages plus six successful native calls so shared
    # assertions cannot pass with doubles or unexecuted binaries.
    def run_chain(self, **parameters):
        evidence = run(Path(os.environ["WAREHOUSE_NATIVE_BIN"]), **parameters)
        result = evidence["result"]
        self.assertIsInstance(result, ExecutableProposal)
        self.assertEqual([row[0] for row in evidence["trace"]], ["allocation", "compilation", "mapf", "tpg"])
        for stage in ("mapf", "tpg"):
            records = [json.loads(value) for name, value in evidence["native_evidence"][stage].items()
                       if name.endswith(".run.json")]
            self.assertEqual(len(records), 3)
            self.assertTrue(all(row["exit_code"] == 0 and not row["timed_out"] for row in records))
        return evidence, result

    # 中文: 本测试用解析公式检查静止动作和 Hermite 曲线的速度与加速度极值. Hermite 曲线用相邻位置和速度确定段内运动. 本测试还核对动作引用, 离散时间步 tick 对齐和终速, 防止端点检查漏掉段内违规.
    # English: This test analytically checks action holds and speed/acceleration extrema on Hermite curves.
    # Each curve derives motion from adjacent positions and velocities. The test also checks action references,
    # discrete timestep (tick) alignment and final speed so endpoint checks cannot miss interval violations.
    def test_real_chain_preserves_actions_and_exact_kinematic_bounds(self):
        evidence, proposal = self.run_chain()
        segment = proposal.motion.common_prefix[0]
        jobs = evidence["trace"][1][2]
        self.assertEqual([item.step for item in segment.actions], [item.step for item in jobs[0].actions])
        for scheduled, action in zip(segment.actions, jobs[0].actions):
            self.assertAlmostEqual(scheduled.start_s / 0.1, round(scheduled.start_s / 0.1))
            holds = [(a, b) for a, b in zip(segment.knots, segment.knots[1:])
                     if abs(a.time_s - scheduled.start_s) < 1e-8]
            self.assertEqual(len(holds), 1)
            a, b = holds[0]
            self.assertAlmostEqual(b.time_s - a.time_s, action.duration_s)
            self.assertEqual(a.pose, b.pose)
            self.assertEqual(a.velocity.vx_mps, 0)
        for left, right in zip(segment.knots, segment.knots[1:]):
            dt = right.time_s - left.time_s
            self.assertGreater(dt, 0)
            x0, x1 = left.pose.x_m, right.pose.x_m
            v0, v1 = left.velocity.vx_mps, right.velocity.vx_mps
            a = 2*x0 - 2*x1 + dt*(v0 + v1)
            b = -3*x0 + 3*x1 - dt*(2*v0 + v1)
            c = dt*v0
            candidates = [0, 1]
            if abs(a) > 1e-10 and 0 < -b/(3*a) < 1:
                candidates.append(-b/(3*a))
            for s in candidates:
                speed = (3*a*s*s + 2*b*s + c)/dt
                self.assertGreaterEqual(speed, -1e-8)
                self.assertLessEqual(speed, 2 + 1e-8)
            for s in (0, 1):
                self.assertLessEqual(abs((6*a*s + 2*b)/(dt*dt)), 1 + 1e-8)
        last = segment.knots[-1]
        self.assertEqual(last.pose.x_m, 5)
        self.assertEqual(last.velocity.vx_mps, 0)
        self.assertEqual(proposal.motion.stop_tail[0].knots[0], last)
        self.assertEqual(proposal.motion.stop_tail[0].knots[-1].pose, last.pose)

    # 中文: 本测试改变数量和目的地并比较原生输出, 证明分配, 编译和路径确实联动, 避免固定输出冒充端到端运行.
    # English: This test changes quantities and destinations and compares native output so fixed responses
    # cannot masquerade as end-to-end propagation.
    def test_changed_orders_and_destinations_change_real_outputs(self):
        first_evidence, first = self.run_chain()
        changed_evidence, changed = self.run_chain(quantity=3, stock=3, station=4, destination=8)
        self.assertEqual(changed.task_delta.tasks[0].steps[1].picks[0].quantity, 3)
        self.assertEqual(first_evidence["trace"][1][2][0].actions[1].duration_s, 0.3)
        self.assertEqual(changed_evidence["trace"][1][2][0].actions[1].duration_s, 0.7)
        self.assertEqual(changed.motion.common_prefix[0].knots[-1].pose.x_m, 8)
        self.assertNotEqual(first_evidence["native_evidence"]["mapf"]["leg-2.txt"],
                            changed_evidence["native_evidence"]["mapf"]["leg-2.txt"])
        self.assertGreater(changed.motion.common_prefix[0].knots[-1].time_s,
                           first.motion.common_prefix[0].knots[-1].time_s)

    # 中文: 本测试让库存不足请求停在分配层, 检查没有原生证据, 保证已知失败不会浪费后续求解预算.
    # English: This test stops an insufficient-stock request at allocation and checks that no native evidence
    # exists so known failure does not consume downstream solver budget.
    def test_rejected_order_never_runs_native_stages(self):
        evidence = run(Path(os.environ["WAREHOUSE_NATIVE_BIN"]), stock=0)
        self.assertIsInstance(evidence["result"], Failure)
        self.assertEqual(evidence["result"].code, "NO_PLAN")
        self.assertEqual(evidence["native_evidence"], {})
