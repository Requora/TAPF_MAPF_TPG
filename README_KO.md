# TAPF / MAPF / TPG

[中文](README_ZH.md) | [English](README.md) | [한국어](README_KO.md)

<!-- doc-sync: readme / 2026-10-19-r2 -->

Warehouse API 0.7 영문 명세를 따르는 모듈형 창고 계획 시스템이다.
현재는 공통 계약만 제공한다. 계획기 어댑터와 Runtime은 아직 구현하지 않았다.

Python 3.10+:

```bash
python -m pip install .
python -c 'from warehouse_api.contracts import API_VERSION; print(API_VERSION)'
```

계약 패키지 실행에는 Python 표준 라이브러리만 필요하다. 설치에는 setuptools를 사용한다.
타입은 `warehouse_api.contracts`에서 가져온다.

사용자가 제공한 `warehouse_api_v0_7/`는 로컬 참고 문서 묶음이다.
패키지 설치에 필요하지 않으며 이 PR에 전체를 추가하지 않는다.
계약 파일은 기존 API를 유지한다. review 과정에서 필드 설명의 문장 부호를 통일했다.
원본과 현재 파일의 해시는 개발 기록에 있다.
백엔드 경계 타입은 유지한다. 시뮬레이터 구현은 이번 범위에 포함하지 않는다.

- [모듈 경계와 단계별 계획](docs/development/ROADMAP_KO.md)
- [첫 PR: 출처와 검증](docs/development/0001-contract-foundation_KO.md)
- [개발 및 review 규칙](AGENTS_KO.md)
