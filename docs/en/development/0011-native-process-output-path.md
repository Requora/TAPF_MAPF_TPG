# Native process output path contract

[中文](../../zh/development/0011-native-process-output-path.md) | [English](../../en/development/0011-native-process-output-path.md)

<!-- doc-sync: native-process-output-path / 2026-10-22-r1 -->

## Scope and decision

PR #10 is merged; remote baseline is `4560d8e`. This increment addresses review r4353910675 about cwd with relative output. run_native requires absolute output when cwd is supplied; otherwise it raises ValueError before deleting files, creating logs or starting a child. Callers own command arguments; the utility does not guess or rewrite paths inside arbitrary commands. Existing adapters use absolute output paths. Module dependencies and warehouse support remain unchanged.

## Validation and failure record

TDD: the new regression first failed because ValueError was not raised, then passed after the entry guard. The test preserves a caller file and checks that rejection retains it, starts no child and creates no logs.

`PYTHONPATH=src python -m unittest discover -s tests -v`: 87 tests, 83 passed and four native tests skipped because their environment was not configured. Ruff, node --check for both JavaScript files and git diff --check passed. The existing absolute-output/cwd test with a real Python child passed. This increment did not rerun MAWPF, WinkTPG or CBS-TA; historical real integration evidence belongs to merged PR #10.

The website updates its snapshot date, merged baseline and current work. The first preview port was occupied; a system-assigned port replaced it. The Sites source helper twice returned Unable to prepare the Site; remote access was unchanged. Final publication and website checks follow below.

## PR and next step

The PR link will be added after creation. This increment only fixes the path contract and waits for user review after submission. Joint warehouse adaptation, continuous validation, Runtime and execution remain unimplemented.

Website check: `web/progress/check.py http://127.0.0.1:37663` passed both languages, both diagrams, 30 module selections, keyboard and mobile checks, with no JS errors. Desktop and mobile screenshots were inspected. Independent gpt-6-luna/low documentation review was performed.
