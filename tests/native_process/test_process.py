import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from warehouse_api.native_process import run_native


class ProcessTests(unittest.TestCase):
    def test_real_process_timeout_records_failure(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "result.txt"
            result = run_native([sys.executable, "-c", "import time; time.sleep(10)"], output,
                                budget_s=0.05, request_id="timeout")
            self.assertEqual(result.code, "TIMEOUT")
            record = json.loads(output.with_suffix(".run.json").read_text())
            self.assertTrue(record["timed_out"])
            self.assertIsNone(record["exit_code"])

    def test_exit_zero_cannot_reuse_an_old_output(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "result.txt"
            output.write_text("stale result")
            result = run_native([sys.executable, "-c", "pass"], output,
                                budget_s=5, request_id="missing-output")
            self.assertEqual(result.code, "BACKEND_ERROR")
            self.assertFalse(output.exists())
