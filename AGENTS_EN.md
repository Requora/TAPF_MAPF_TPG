# Development rules

[中文](AGENTS.md) | [English](AGENTS_EN.md) | [한국어](AGENTS_KO.md)

<!-- doc-sync: agents / 2026-10-19-r2 -->

## Make results easy to understand and verify

- Keep replies within about 300 characters where possible. Lead with the result. Expand when requested.
- Help people understand and verify results quickly. Avoid unnecessary long text.
- Use a style close to 80% ASD-STE100: short sentences, consistent terms, clear references, and technical precision.
- Prefer diagrams for structure, processes, and timing; prefer interactive single-step demos for dynamic algorithms.
- Show real execution traces, key decisions, and failures in research and debugging. Label teaching simplifications.
- After substantial autonomous work, provide summaries, comparisons, and traceable details. Add visuals only when they improve understanding.
- Core principle: Spend computation to save human cognition.
- During ongoing work, report the current work and its reason at least every 5 minutes; follow shorter intervals when required.
- Use English punctuation in documents, comments, field descriptions, and replies.

## Project scope

- Follow `warehouse_api_v0_7/warehouse_api_v0_7_visual_EN.md` and its English type catalog.
- Do not implement simulators, native backends, scene assets, or IPC in this work. Retain backend boundary types.
- Separate orders, assignment, shared compiler, MAPF, TPG, joint solving,
  validation, Runtime, and central execution. Communicate through public Request/Result types and Protocols.
- Use `src/warehouse_api/contracts.py` as the shared contract. Do not introduce incompatible DTOs.
- Reuse existing GitHub implementations for the MAPF and TPG algorithm cores. Implement adapters here.
- Record upstream URLs, commits, licenses, build steps, supported scope, and real execution evidence.
- Research task assignment. Order generation may be implemented here; random generation must be reproducible by seed.
- Use an existing TAPF implementation to test replacement of assignment and pathfinding together; retain separate replacement options.
- Keep native upstream objects out of the public API. Return `UNSUPPORTED` for constraints that cannot be represented.
- Candidate computations must not mutate inputs or live records. Only Runtime atomically publishes complete proposals.
- Type checks, discrete collision-free routes, and fixture passes do not replace continuous geometry and stopping validation.

## Small PRs and the merge gate

- Complete one minimal, independently reviewable change, then submit a PR.
- Each PR changes at most 500 effective code lines, counting additions plus deletions against the target branch, including tests and scripts.
- Documentation and configuration changes do not count toward 500; report them separately. Do not evade the limit through compressed code, generated code, or bulk vendoring.
- Prefer keeping raw changed code lines within 500 as well.
- Before submission, run appropriate checks and report results, code line counts, and unverified items.
- After submission, wait for user review. Only fix review feedback on the current PR.
- After the user merges the PR, confirm the remote merge and update the base before starting the next step.
- Do not merge, enable auto-merge, start later PR work, or stack dependent branches in advance.

## Development logs and synchronized translations

- Add or update a log in `docs/development/` for every PR.
- Record scope, key decisions, source versions, verification commands and results, failures, PR links, and the next step.
- Distinguish planned work, defined interfaces, fixture validation, and verified native integration.
- Provide Chinese, English, and Korean project documents. Update all three in the same PR; new documents also need all three versions.
- Use the same `doc-sync` revision, section order, technical facts, and verification status, with links between versions.
- Delegate document checks to a subagent using model `gpt-6.1-sol` with `low` reasoning effort. Check language parity, English punctuation, links, and technical facts; the primary agent reviews and addresses findings.
- `AGENTS.md` is the instruction entry point; `AGENTS_EN.md` and `AGENTS_KO.md` are synchronized translations.
- Preserve the supplied `warehouse_api_v0_7/` reference bundle; do not add it wholesale with `git add .`.
- See `docs/development/ROADMAP.md` for the current stage and incremental sequence.
