# PR 1 - 공통 계약과 review 절차

[中文](0001-contract-foundation_ZH.md) | [English](0001-contract-foundation.md) | [한국어](0001-contract-foundation_KO.md)

<!-- doc-sync: foundation / 2026-10-19-r2 -->

날짜: 2026-10-19. 상태: review 수정 준비 완료, 사용자 review와 병합 대기.
브랜치: `feat/api-contract-foundation`. [PR #1](https://github.com/Requora/TAPF_MAPF_TPG/pull/1).

## 범위와 출처

초기 저장소의 `4f0109145ca3fbe3a8130a3cb94c757e2544d17e`에는 README.md와 .gitignore만 있었다.
사용자는 추적되지 않은 `warehouse_api_v0_7/` 참고 묶음을 제공했다.
영문 안내, 타입 정의, 참고 코드, 검증 기록을 읽었다.
참고 묶음은 보존하고 공통 계약만 개발 패키지에 가져온다.

`src/warehouse_api/contracts.py`는 처음에
`warehouse_api_v0_7/package/warehouse_api/contracts.py`에서 복사했다 (445행).
이번 review에서는 중국어 필드 설명의 문장 부호만 영문 부호로 바꿨다.
파일은 이제 원본과 바이트 단위로 같지 않다. API 필드, 기본값, 타입, Protocol은 유지한다.

- 원본 SHA256: `8608f438a78470fae3535dbc0b1180583a7ae83875921bf717251a2518318bbd`.
- 현재 SHA256: `ad02ec8870b84e01389ba8d8ef986038bf4dccb63e295a2cbc92cf0b1e13906a`.

운영 코드는 참고 묶음이 아닌 이 패키지를 가져온다. 패키징 설정, 가져오기 CI,
개발 규칙, 모듈/연구 계획을 추가한다. 백엔드 경계 타입은 유지하고 시뮬레이터는 구현하지 않는다.
네이티브 해결기를 빌드하거나 통합한 상태가 아니다.

## 검증

초기 기준 검사 명령, 저장소 루트에서 실행:

```bash
PYTHONPATH=warehouse_api_v0_7/package python -m unittest discover -s warehouse_api_v0_7/package/tests -v
```

결과: Python 3.14.7에서 38개 통과. 처음 참고 패키지 디렉터리에서는 `python`을 찾지 못했다.
루트 shell과 명시적 PYTHONPATH로 해결했으며, 이 환경 문제 때문에 소스를 변경하지 않았다.

초기에 `python -m pip install /home/yimin/research/TAPF_MAPF_TPG`로 임시 venv에 빌드하고 설치했다.
저장소 밖에서 `python -I`로 설치된 패키지를 불러와 클래스 72개와 주석이 있는 메서드 82개를 해석했다.
이 검사는 참고 묶음이나 소스 경로 가져오기에 의존하지 않았다.

이번 review의 AST 비교에서는 필드 도우미 `F`의 첫 번째 인자만 제외했다.
나머지 AST 노드는 원본과 같았다. 타입 주석 해석도 다시 통과했다.
다음 명령으로 변경된 소스 계약을 사용하여 참고 테스트 38개를 다시 실행했다:

```bash
PYTHONPATH=src python - <<'PYTHON'
from pathlib import Path
import unittest, warehouse_api
warehouse_api.__path__.append(str(Path('warehouse_api_v0_7/package/warehouse_api').resolve()))
suite = unittest.defaultTestLoader.discover('warehouse_api_v0_7/package/tests')
result = unittest.TextTestRunner().run(suite)
raise SystemExit(not result.wasSuccessful())
PYTHON
```

관측 결과: 계약은 `src/warehouse_api/contracts.py`에서 로드했다. 클래스 72개와 주석이 있는 메서드 82개를 해석했고,
테스트 38개가 통과했다. 참고 보조 모듈은 위 패키지 검색 경로에서 제공하며 이 PR에는 포함하지 않는다.

review 전 commit `8d1e4f1`의 Python 3.10 및 3.14 CI가 통과했다:
[run 39304485036](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39304485036).
수정 commit의 CI는 PR 검사 페이지에서 확인한다. 이 테스트는 운영 계획기, Runtime,
연속 충돌 검사, 네이티브 시뮬레이터의 정확성을 증명하지 않는다.

## Review 수정

- `gpt-6.1-sol` 모델과 `low` 추론 강도의 subagent가 문서 12개를 읽기 전용으로 검사했다.
  세 언어의 일치, 문장 부호, 로컬 링크, 수정 표식, 기록된 해시와 행 수에서 문제가 없었다.
  원격 링크와 원본 구현 관련 주장은 다시 검증하지 않았다. AGENTS에 이 문서 검사 위임 방식을 명시했다.
- [세 언어 동기화](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317490698): README, 규칙, 계획, 이 기록에 중국어, 영어, 한국어 버전과 언어 링크, 같은 수정 표식을 추가했다.
- [영문 문장 부호](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317495406): 프로젝트 문서와 계약 필드 설명의 문장 부호를 통일했다. 제공된 참고 묶음은 유지한다.
- [표현 원칙](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317507084): 요청한 여섯 원칙을 AGENTS에 추가했다. 약 80% ASD-STE100, 실제 추적, 교육용 단순화 표시, 이해에 도움이 되는 시각화를 포함한다.
- 사용자가 채팅에서 문서와 설정은 500행 제한에서 제외한다고 명확히 했다. 세 언어 규칙에 반영했다.

main 대비 추가 코드 446행 (계약 445 + 패키지 진입점 1), 삭제 코드 없음.
패키징과 CI 설정은 총 39행이며 별도로 센다. 문서도 별도로 센다.
코드 수에는 주석과 빈 줄도 포함하므로 유효 코드 행 수는 500 미만이다.

## 게시와 다음 단계

SSH push는 성공했지만, 처음 GitHub 연결을 통한 저장소 조회와 PR 생성은 HTTP 404를 반환했다.
인증된 로컬 CLI 대안이 없었다. 사용자가 조직에 커넥터를 설치하고 승인한 뒤 재시도가 성공했고,
2026-10-19에 PR #1을 만들었다. 접근 문제는 해결됐다.

같은 PR에서 이번 수정을 review한다. 후속 개발 단계는 시작하지 않았다.
사용자가 병합한 후 원격 병합 상태를 확인하고 다음 작은 codec/fixture PR만 시작한다.
직접 병합하거나 사용자의 review 스레드를 자동으로 해결 처리하지 않는다.
