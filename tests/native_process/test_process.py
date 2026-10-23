import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from warehouse_api.native_process import run_native


# 中文: ProcessTests 测试类验证真实子进程边界的超时和输出新鲜度, 防止进程失败时错误接受旧文件结果.
# English: ProcessTests tests real subprocess timeout and output freshness so failed execution cannot accidentally
# accept an old result file.
class ProcessTests(unittest.TestCase):
    # 中文: 本测试让原生程序在指定目录写辅助文件, 防止上游调试输出污染调用者的工作目录.
    # English: This test runs a native process in a chosen directory so upstream debug output cannot pollute the caller's working directory.
    def test_working_directory_contains_native_side_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "result.txt"
            original = Path.cwd()
            command = [sys.executable, "-c",
                       "from pathlib import Path; Path('result.txt').write_text('ok'); "
                       "Path('debug.dot').write_text(str(Path.cwd()))"]
            result = run_native(command, output, budget_s=5, request_id="directory", cwd=root)
            self.assertIsNone(result)
            self.assertEqual((root / "debug.dot").read_text(), str(root))
            self.assertEqual(Path.cwd(), original)
            self.assertEqual(json.loads(output.with_suffix(".run.json").read_text())["cwd"], str(root))

    # 中文: 本测试拒绝 cwd 配合相对输出路径, 防止父子进程读取不同文件或删除调用者的旧证据.
    # English: This test rejects relative output with cwd so parent and child cannot use different files or delete caller evidence.
    def test_cwd_requires_absolute_output_before_any_side_effect(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "result.txt"
            output.write_text("caller evidence")
            child = root / "child"
            child.mkdir()
            relative_output = Path(os.path.relpath(output))
            command = [sys.executable, "-c", "from pathlib import Path; Path('started').touch()"]
            with self.assertRaisesRegex(ValueError, "absolute output.*cwd"):
                run_native(command, relative_output, budget_s=5, request_id="relative", cwd=child)
            self.assertEqual(output.read_text(), "caller evidence")
            self.assertEqual(list(child.iterdir()), [])
            self.assertFalse(output.with_suffix(".stdout").exists())
            self.assertFalse(output.with_suffix(".run.json").exists())

    # 中文: 本测试运行会超时的真实休眠进程, 检查 TIMEOUT 和证据, 确认进程边界实际生效而非仅模拟返回码.
    # English: This test runs a real sleeping child and inspects TIMEOUT evidence so process enforcement is
    # checked rather than merely mocked.
    def test_real_process_timeout_records_failure(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "result.txt"
            result = run_native([sys.executable, "-c", "import time; time.sleep(10)"], output,
                                budget_s=0.05, request_id="timeout")
            self.assertEqual(result.code, "TIMEOUT")
            record = json.loads(output.with_suffix(".run.json").read_text())
            self.assertTrue(record["timed_out"])
            self.assertIsNone(record["exit_code"])

    # 中文: 本测试预置旧输出再运行不产出文件的成功进程, 验证旧文件被移除, 防止 exit 0 伪装成新方案.
    # English: This test preloads stale output and runs a successful child that writes nothing so exit zero
    # cannot disguise an old plan as a new result.
    def test_exit_zero_cannot_reuse_an_old_output(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "result.txt"
            output.write_text("stale result")
            result = run_native([sys.executable, "-c", "pass"], output,
                                budget_s=5, request_id="missing-output")
            self.assertEqual(result.code, "BACKEND_ERROR")
            self.assertFalse(output.exists())
