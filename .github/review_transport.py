"""This adapter keeps PR-Agent review logic but owns one observable OpenRouter attempt.
本适配器保留 PR-Agent 审查逻辑, 直接管理一次可观察的 OpenRouter 请求.
"""
import asyncio
import json
import os
import tempfile
import httpx

API = 'https://openrouter.ai/api/v1'
MODEL = 'deepseek/deepseek-v4.1-flash-1017'
_review_attempted = False


class ReviewStream:
    """ReviewStream collects SSE response state so network orchestration stays readable.
    ReviewStream 集中保存 SSE 事件流状态, 让网络主流程不混入解析和完整性规则.
    """
    def __init__(self, audit):
        """__init__ separates visible text from audit metadata to keep reasoning private.
        __init__ 将正文与审计元数据分开保存, 避免推理内容进入日志或发布结果.
        """
        self.audit = audit
        self.text = []
        self.finish = None
        self.done = False

    def accept(self, line):
        """accept consumes one SSE data line and identifies the stream completion marker.
        accept 消费一行 SSE 数据并识别结束标记, 让读取循环只负责推进事件流.
        """
        if not line.startswith('data:'):
            return
        value = line[5:].strip()
        if value == '[DONE]':
            self.done = True
            return
        chunk = json.loads(value)
        self.record_metadata(chunk)
        self.check_error(chunk)
        for choice in chunk.get('choices', []):
            self.finish = choice.get('finish_reason') or self.finish
            self.text.append(choice.get('delta', {}).get('content') or '')
        if self.finish:
            self.audit['finish_reason'] = self.finish

    def record_metadata(self, chunk):
        """record_metadata retains supplied identifiers and usage without inventing missing evidence.
        record_metadata 保留上游提供的标识和用量, 不推测缺失证据且不记录推理正文.
        """
        if chunk.get('id'):
            self.audit['generation_id'] = chunk['id']
        if chunk.get('provider'):
            self.audit['provider'] = chunk['provider']
        if chunk.get('usage'):
            self.audit['usage'] = chunk['usage']

    def check_error(self, chunk):
        """check_error rejects provider errors after metadata is recorded for diagnosis.
        check_error 在元数据记录后拒绝供应商错误, 保留诊断证据并阻止发布失败内容.
        """
        error = chunk.get('error')
        if error:
            self.audit['error_code'] = error.get('code')
            self.audit['provider'] = error.get('metadata', {}).get('provider_name', self.audit.get('provider'))
            raise RuntimeError(f'OpenRouter stream error {self.audit["error_code"]}')

    def result(self):
        """result requires a complete nonempty answer before returning publishable review text.
        result 要求正文非空且正常完整结束, 防止截断或断流结果进入审查发布阶段.
        """
        content = ''.join(self.text)
        if not self.done or self.finish != 'stop' or not content.strip():
            raise RuntimeError(f'Incomplete review: done={self.done}, finish={self.finish}, visible_chars={len(content)}')
        self.audit['visible_chars'] = len(content)
        return content, self.finish


def check_response(response, audit):
    """check_response records HTTP evidence and rejects failures before SSE processing.
    check_response 记录 HTTP 响应证据并提前拒绝错误, 避免把错误页解析成 SSE 事件.
    """
    audit['http_status'] = response.status_code
    audit['request_id'] = response.headers.get('x-request-id')
    if response.is_error:
        audit['error_code'] = response.status_code
        raise RuntimeError(f'OpenRouter HTTP {response.status_code}')


async def request_review(client, system, user, audit, deadline=600):
    """request_review owns one bounded HTTP stream; ReviewStream owns parsing and validation.
    request_review 管理单次有时限的 HTTP 流, 将解析与校验交给 ReviewStream 以保持主流程清晰.
    """
    payload = {'model': MODEL, 'messages': [{'role':'system', 'content':system}, {'role':'user', 'content':user}],
               'max_tokens':65536, 'reasoning':{'effort':'low'}, 'stream':True,
               'stream_options':{'include_usage':True},
               'provider':{'ignore':['ionstream'], 'require_parameters':True}}
    stream = ReviewStream(audit)
    async with asyncio.timeout(deadline):
        async with client.stream('POST', API+'/chat/completions', json=payload) as response:
            check_response(response, audit)
            async for line in response.aiter_lines():
                stream.accept(line)
                if stream.done:
                    break
    return stream.result()


async def chat_completion(self, model, system, user, temperature=0.2, img_path=None):
    """chat_completion permits one attempt per process and logs metadata without prompts or secrets.
    chat_completion 限制每进程一次请求并只记录元数据, 防止新实例绕过限制且不输出提示词或密钥.
    """
    global _review_attempted
    if model != 'openai/'+MODEL or img_path is not None:
        raise ValueError('This review adapter only supports the configured text model')
    if _review_attempted:
        raise RuntimeError('Only one model attempt is allowed per review')
    _review_attempted = True
    audit = {'model':MODEL, 'attempt':1, 'deadline_s':600, 'status':'failed'}
    try:
        async with httpx.AsyncClient(headers={'Authorization':'Bearer '+os.environ['OPENAI_KEY']}, timeout=600) as client:
            result = await request_review(client, system, user, audit)
        audit['status'] = 'completed'
        return result
    finally:
        print('REVIEW_AUDIT '+json.dumps(audit), flush=True)


def prepare_dispatch():
    """prepare_dispatch resolves a requested same-repository PR without executing its source.
    prepare_dispatch 解析手动指定的同仓库 PR 且不执行其源码, 便于独立验证修复.
    """
    if os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        return
    repo = os.environ['GITHUB_REPOSITORY']
    number = int(os.environ['REVIEW_PR_NUMBER'])
    response = httpx.get(f'https://api.github.com/repos/{repo}/pulls/{number}',
                         headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN']}, timeout=30)
    response.raise_for_status()
    pr = response.json()
    if pr['state'] != 'open' or pr['head']['repo']['full_name'] != repo:
        raise ValueError('Manual review requires an open same-repository PR')
    event = {'action':'opened', 'pull_request':pr, 'repository':{'full_name':repo}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as stream:
        json.dump(event, stream)
    os.environ['GITHUB_EVENT_NAME'] = 'pull_request'
    os.environ['GITHUB_EVENT_PATH'] = stream.name
    print(f'Review target: {repo}#{number} head={pr["head"]["sha"]}', flush=True)


def main():
    """main patches the pinned PR-Agent transport before its normal runner imports review tools.
    main 在固定版本 PR-Agent 加载审查工具前替换传输入口, 保留原有解析与评论功能.
    """
    from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
    LiteLLMAIHandler.chat_completion = chat_completion
    prepare_dispatch()
    from pr_agent.servers.github_action_runner import main as run
    run()


if __name__ == '__main__':
    main()
