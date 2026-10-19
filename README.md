# TAPF / MAPF / TPG

[中文](README_ZH.md) | [English](README.md) | [한국어](README_KO.md)

<!-- doc-sync: readme / 2026-10-19-r2 -->

Modular warehouse planning using the Warehouse API 0.7 English specification.
Current status: shared contracts only. Planner adapters and Runtime are not implemented.

Python 3.10+:

```bash
python -m pip install .
python -c 'from warehouse_api.contracts import API_VERSION; print(API_VERSION)'
```

Runtime use of this contract package needs only the Python standard library.
Installing the package uses setuptools. Import types from `warehouse_api.contracts`.

The user-supplied `warehouse_api_v0_7/` directory is a local reference bundle.
It is not required to install this package and is not included wholesale in this PR.
The contract file preserves the supplied API; field-description punctuation was
normalized during review. See the development log for source and current hashes.
Backend boundary types remain for compatibility; simulator implementation is out of scope.

- [Module boundaries and incremental plan](docs/development/ROADMAP.md)
- [First PR: provenance and verification](docs/development/0001-contract-foundation.md)
- [Development and review rules](AGENTS_EN.md)
