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
        """This test requires isolated credentials and matching tested/runtime adapter bytes.
        本测试要求凭据隔离及受测/运行适配器内容一致, 防止固定版本偏离受测行为.
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
        pinned = next(step for step in tests['steps'] if step.get('name') == 'Checkout review runtime')
        self.assertEqual(pinned['with']['ref'], checkout['with']['ref'])
        self.assertEqual(pinned['with']['path'], '.review-runtime')
        self.assertFalse(pinned['with']['persist-credentials'])
        self.assertIn({'name':'Require tested and executed adapter equality',
                       'run':'cmp .github/review_transport.py .review-runtime/.github/review_transport.py'}, tests['steps'])
