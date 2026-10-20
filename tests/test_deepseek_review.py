"""Exercise the embedded workflow with fake APIs, without a provider key."""
import base64
import copy
from pathlib import Path
import textwrap
import unittest


def workflow_namespace():
    text = Path('.github/workflows/deepseek-review.yml').read_text()
    block = text.split("          python - <<'PY'\n", 1)[1].rsplit('          PY', 1)[0]
    namespace = {'__name__': 'workflow_test'}
    exec(compile(textwrap.dedent(block), '<deepseek-workflow>', 'exec'), namespace)
    return namespace


class DeepSeekReviewTests(unittest.TestCase):
    def setUp(self):
        self.ns = workflow_namespace()
        self.pr = {'number': 7, 'head': {'sha': 'head', 'repo': {'full_name': 'owner/repo'}},
                   'base': {'sha': 'base'}, 'state': 'open', 'changed_files': 1}
        self.event = {'pull_request': copy.deepcopy(self.pr)}
        self.env = {'DEEPSEEK_API_KEY': 'fake', 'GITHUB_REPOSITORY': 'owner/repo',
                    'GITHUB_TOKEN': 'fake', 'DEEPSEEK_MODEL': 'deepseek-flash', 'GITHUB_RUN_ID': '1'}
        self.files = [{'filename': 'code.py', 'status': 'modified', 'patch': '@@ -1 +1 @@\n-old\n+new'}]
        self.result = {'model': 'deepseek-flash', 'choices': [
            {'finish_reason': 'stop', 'message': {'content': 'Finding in code.py:1. @someone'}}]}
        self.previous = []
        self.published = []
        self.stale = False
        self.calls = []
        self.ns['api'] = self.api

    def api(self, url, token, payload=None):
        self.calls.append(url)
        if url.endswith('/chat/completions'):
            self.assertIn('code.py', payload['messages'][1]['content'])
            if self.stale:
                self.pr['head']['sha'] = 'new-head'
            return self.result
        if url.endswith('/reviews'):
            self.published.append(payload)
            return {'html_url': 'https://github.com/review'}
        if '/reviews?' in url:
            return self.previous
        if '/files?' in url:
            return self.files
        if '/contents/' in url:
            return {'content': base64.b64encode(b'Project context').decode()}
        return copy.deepcopy(self.pr)

    def test_complete_review_is_attached_to_head_without_approval(self):
        self.ns['review'](self.event, self.env)
        self.assertEqual(len(self.published), 1)
        self.assertEqual(self.published[0]['commit_id'], 'head')
        self.assertEqual(self.published[0]['event'], 'COMMENT')
        self.assertNotIn('@someone', self.published[0]['body'])
        self.assertIn('no tests executed', self.published[0]['body'])

    def test_missing_key_and_fork_fail_before_any_api_call(self):
        for env, event in (({**self.env, 'DEEPSEEK_API_KEY': ''}, self.event),
                           (self.env, {'pull_request': {**self.pr, 'head': {
                               'sha': 'head', 'repo': {'full_name': 'fork/repo'}}}})):
            with self.assertRaises(ValueError):
                self.ns['review'](event, env)
            self.assertEqual(self.calls, [])

    def test_stale_or_truncated_review_is_never_published(self):
        for stale, finish in ((True, 'stop'), (False, 'length')):
            self.setUp()
            self.stale = stale
            self.result['choices'][0]['finish_reason'] = finish
            with self.assertRaises(ValueError):
                self.ns['review'](self.event, self.env)
            self.assertEqual(self.published, [])

    def test_duplicate_review_skips_provider(self):
        self.previous = [{'body': '<!-- deepseek-review:head:base:deepseek-flash -->',
                          'user': {'type': 'Bot'}}]
        self.ns['review'](self.event, self.env)
        self.assertEqual(len(self.calls), 1)

    def test_missing_files_and_oversized_input_fail_before_provider(self):
        for changes, patch in ((2, 'patch'), (1, 'x' * 160001)):
            self.setUp()
            self.pr['changed_files'] = changes
            self.files[0]['patch'] = patch
            with self.assertRaises(ValueError):
                self.ns['review'](self.event, self.env)
            self.assertFalse(any('/chat/completions' in url for url in self.calls))
