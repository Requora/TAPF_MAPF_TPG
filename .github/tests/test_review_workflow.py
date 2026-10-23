"""Workflow tests enforce isolation between PR test code and model credentials.
本测试约束 PR 测试代码与模型凭据的隔离, 防止未来配置回退.
"""
from pathlib import Path
import unittest
import yaml


class WorkflowIsolationTests(unittest.TestCase):
    """WorkflowIsolationTests checks the credential boundary rather than model internals.
    WorkflowIsolationTests 检查凭据边界, 避免 PR 代码进入持有密钥的执行环境.
    """
    def test_review_uses_pinned_source_on_a_separate_runner(self):
        """This test requires read-only tests and an immutable review-runtime checkout.
        本测试要求只读测试权限和不可变审查源码版本, 防止执行未经固定的 PR 源码.
        """
        workflow = yaml.safe_load((Path(__file__).parents[1] / 'workflows/deepseek-review.yml').read_text())
        tests = workflow['jobs']['transport-tests']
        review = workflow['jobs']['review']
        self.assertEqual(tests['permissions'], {'contents':'read'})
        self.assertNotIn('secrets.', str(tests))
        self.assertEqual(review['needs'], 'transport-tests')
        checkout = review['steps'][0]
        self.assertTrue(checkout['uses'].startswith('actions/checkout@'))
        self.assertRegex(checkout['with']['ref'], r'^[0-9a-f]{40}$')
        self.assertFalse(checkout['with']['persist-credentials'])
        self.assertEqual(len(review['steps']), 2)
