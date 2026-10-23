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


async def request_review(client, system, user, audit, deadline=600):
    """request_review streams one bounded request and rejects upstream errors or partial text.
    request_review 在总时限内仅请求一次, 拒绝上游错误和不完整正文以防错误发布.
    """
    payload = {'model': MODEL, 'messages': [{'role':'system', 'content':system}, {'role':'user', 'content':user}],
               'max_tokens':65536, 'reasoning':{'effort':'low'}, 'stream':True,
               'stream_options':{'include_usage':True},
               'provider':{'ignore':['ionstream'], 'require_parameters':True}}
    text, finish, done = [], None, False
    async with asyncio.timeout(deadline):
        async with client.stream('POST', API+'/chat/completions', json=payload) as response:
            audit['http_status'] = response.status_code
            audit['request_id'] = response.headers.get('x-request-id')
            if response.is_error:
                audit['error_code'] = response.status_code
                raise RuntimeError(f'OpenRouter HTTP {response.status_code}')
            async for line in response.aiter_lines():
                if not line.startswith('data:'):
                    continue
                value = line[5:].strip()
                if value == '[DONE]':
                    done = True
                    break
                chunk = json.loads(value)
                if chunk.get('id'):
                    audit['generation_id'] = chunk['id']
                if chunk.get('provider'):
                    audit['provider'] = chunk['provider']
                if chunk.get('usage'):
                    audit['usage'] = chunk['usage']
                if chunk.get('error'):
                    error = chunk['error']
                    audit['error_code'] = error.get('code')
                    audit['provider'] = error.get('metadata', {}).get('provider_name', audit.get('provider'))
                    raise RuntimeError(f'OpenRouter stream error {audit["error_code"]}')
                for choice in chunk.get('choices', []):
                    if choice.get('finish_reason'):
                        finish = choice['finish_reason']
                        audit['finish_reason'] = finish
                    text.append(choice.get('delta', {}).get('content') or '')
    content = ''.join(text)
    if not done or finish != 'stop' or not content.strip():
        raise RuntimeError(f'Incomplete review: done={done}, finish={finish}, visible_chars={len(content)}')
    audit['visible_chars'] = len(content)
    return content, finish


async def chat_completion(self, model, system, user, temperature=0.2, img_path=None):
    """chat_completion replaces the retrying transport and logs metadata without prompts or secrets.
    chat_completion 替换含重试的传输入口并只记录元数据, 保留诊断证据且不输出提示词或密钥.
    """
    if model != 'openai/'+MODEL or img_path is not None:
        raise ValueError('This review adapter only supports the configured text model')
    if self._review_attempted:
        raise RuntimeError('Only one model attempt is allowed per review')
    self._review_attempted = True
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
    LiteLLMAIHandler._review_attempted = False
    LiteLLMAIHandler.chat_completion = chat_completion
    prepare_dispatch()
    from pr_agent.servers.github_action_runner import main as run
    run()


if __name__ == '__main__':
    main()
