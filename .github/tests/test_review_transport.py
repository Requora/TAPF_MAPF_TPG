"""Tests exercise model failures so broken reviews cannot silently pass.
本测试验证模型失败行为, 防止审查错误被当成成功.
"""
import asyncio
import importlib.util
import json
from pathlib import Path
import unittest
import httpx

spec = importlib.util.spec_from_file_location('review_transport', Path(__file__).parents[1] / 'review_transport.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


class ReviewTransportTests(unittest.IsolatedAsyncioTestCase):
    """ReviewTransportTests checks real HTTP serialization and failure boundaries.
    ReviewTransportTests 检查真实 HTTP 编码及失败边界, 确保配置实际生效.
    """
    async def test_provider_error_keeps_evidence_without_retry(self):
        """This test reproduces a reasoning-only stream ending in provider 502.
        本测试复现仅推理输出后供应商返回 502, 防止错误被改写或重试.
        """
        calls, audit = [], {}

        def respond(request):
            """respond returns the observed error shape without exposing prompt text.
            respond 返回观测到的错误结构, 用于验证错误证据保留.
            """
            calls.append(request)
            chunks = [{'id':'gen-test', 'provider':'Ionstream', 'choices':[{'delta':{'reasoning':'hidden'}}]},
                      {'error':{'code':502}, 'usage':{'completion_tokens':360561}}]
            return httpx.Response(200, text=''.join('data: '+json.dumps(c)+'\n\n' for c in chunks))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaisesRegex(RuntimeError, '502'):
                await transport.request_review(client, 'system', 'diff', audit)
        self.assertEqual(len(calls), 1)
        self.assertEqual(audit['generation_id'], 'gen-test')
        self.assertEqual(audit['provider'], 'Ionstream')
        self.assertEqual(audit['usage']['completion_tokens'], 360561)
        self.assertEqual(audit['error_code'], 502)

    async def test_success_sends_routing_and_budget(self):
        """This test checks actual request bytes and returns only complete visible text.
        本测试检查实际请求参数且只返回完整正文, 确保预算和路由生效.
        """
        captured = []

        def respond(request):
            """respond captures settings and emits a complete successful stream.
            respond 捕获参数并发出完整成功事件流, 用于验证正常审查.
            """
            captured.append(json.loads(request.content))
            return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"review"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            self.assertEqual(await transport.request_review(client, 'system', 'diff', {}), ('review', 'stop'))
        body = captured[0]
        self.assertEqual(body['provider'], {'ignore':['ionstream'], 'require_parameters':True})
        self.assertEqual(body['max_tokens'], 65536)
        self.assertEqual(body['reasoning'], {'effort':'low'})
        self.assertTrue(body['stream'])

    async def test_empty_truncated_and_incomplete_streams_fail(self):
        """This test rejects empty answers, truncation and disconnected streams.
        本测试拒绝空正文, 截断及断流, 防止发布不完整审查.
        """
        for body in ('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n',
                     'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":"length"}]}\n\ndata: [DONE]\n\n',
                     'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'):
            with self.subTest(body=body):
                def respond(request):
                    """respond supplies a failed stream to verify publication is blocked.
                    respond 提供失败事件流, 验证不完整内容不会进入发布阶段.
                    """
                    return httpx.Response(200, text=body)
                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    with self.assertRaises(RuntimeError):
                        await transport.request_review(client, 'system', 'diff', {})

    async def test_deadline_cancels_slow_request(self):
        """This test verifies a wall-clock deadline rather than only socket inactivity.
        本测试验证总时限, 避免持续有数据时绕过网络读取超时.
        """
        calls, closed = [], []

        class Trickle(httpx.AsyncByteStream):
            """Trickle emits data continuously so socket activity cannot avoid the total deadline.
            Trickle 持续发送数据, 验证网络活跃不会绕过总时限.
            """
            async def __aiter__(self):
                """__aiter__ emits reasoning chunks without a final answer to simulate a stuck model.
                __aiter__ 只发送推理片段而不结束, 模拟无法输出答案的模型.
                """
                while True:
                    await asyncio.sleep(0.001)
                    yield b'data: {"choices":[{"delta":{"reasoning":"hidden"}}]}\n\n'

            async def aclose(self):
                """aclose records stream cleanup so cancellation cannot leave the response open.
                aclose 记录流关闭, 验证取消时不会遗留未关闭响应.
                """
                closed.append(True)

        def respond(request):
            """respond starts one continuously active response to test deadline cancellation.
            respond 启动一个持续活跃的响应, 用于验证总时限取消.
            """
            calls.append(request)
            return httpx.Response(200, stream=Trickle())

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaises(TimeoutError):
                await transport.request_review(client, 'system', 'diff', {}, deadline=0.01)
        self.assertEqual(len(calls), 1)
        self.assertEqual(closed, [True])

    async def test_http_failure_is_not_retried(self):
        """This test rejects an HTTP-level 502 after exactly one attempt.
        本测试验证 HTTP 层 502 仅调用一次, 防止绕过流内错误保护.
        """
        calls, audit = [], {}

        def respond(request):
            """respond emits an HTTP failure so no partial response is accepted.
            respond 发出 HTTP 错误, 确保失败正文不会被当作审查内容.
            """
            calls.append(request)
            return httpx.Response(502)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaisesRegex(RuntimeError, '502'):
                await transport.request_review(client, 'system', 'diff', audit)
        self.assertEqual(len(calls), 1)
        self.assertEqual(audit['http_status'], 502)

    async def test_handler_blocks_second_attempt_and_logs_metadata(self):
        """This test checks the PR-Agent entrypoint cannot replay a failed call.
        本测试验证 PR-Agent 接入入口无法重复失败调用且会记录证据.
        """
        import contextlib
        import io
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch
        handler, output = SimpleNamespace(_review_attempted=False), io.StringIO()
        call = AsyncMock(side_effect=RuntimeError('provider 502'))
        with patch.dict('os.environ', {'OPENAI_KEY':'test-only'}), patch.object(transport, 'request_review', call):
            with contextlib.redirect_stdout(output):
                with self.assertRaisesRegex(RuntimeError, '502'):
                    await transport.chat_completion(handler, 'openai/'+transport.MODEL, 'private prompt', 'diff')
                with self.assertRaisesRegex(RuntimeError, 'one model attempt'):
                    await transport.chat_completion(handler, 'openai/'+transport.MODEL, 'private prompt', 'diff')
        self.assertEqual(call.await_count, 1)
        self.assertIn('"status": "failed"', output.getvalue())
        self.assertNotIn('test-only', output.getvalue())
        self.assertNotIn('private prompt', output.getvalue())
