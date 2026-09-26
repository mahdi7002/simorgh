# SIMORGH AI WORK CONTRACT

**Effective:** 2026-09-26

This contract governs AI collaboration on the SIMORGH/MOTHER work currently described by
the project map.

## Authorized work, in order

1. Review, test, and commit the existing Mother changes already present:
   - resource_manager.py
   - project_auditor.py
   - workspace_inspector.py
   - capability_assessment.py
   - git_observer.py
   - problem_memory.py
   - repository_config.py
   - workspace_capsule.py
   - corresponding tests

2. Fix foreign-project interpreter resolution:
   - core/mother/ai_work_log_contract.py
   - core/mother/project_auditor.py

3. Inspect and report backend binary provenance and active model/backend state.

4. Audit sibling workspaces only after item 2 is trustworthy.

## Explicitly not authorized

Do not start new architectural modules such as:

- Scheduler
- Model Arena
- Task Executor
- AI Work Ledger
- new autonomous orchestration layers

Do not reset, delete, merge, rebase, or overwrite project state merely to make repositories
look similar.

Do not treat Git state as proof of live runtime state.

Do not treat Mother/Gemma or any other AI as the final truth arbiter.

## Evidence contract

For every significant claim use:

```text
CLAIM -> EVIDENCE -> VERIFICATION -> DECISION
```

Use only these status labels:

```text
VERIFIED
CLAIMED
NOT VERIFIED
NOT AVAILABLE
CONFLICT
```

A `CLAIMED` fact must not be rewritten as `VERIFIED` without a new direct check.

## Unplanned work contract

If work outside this scope occurs:

```text
[UNPLANNED] <description>
```

and add a record to:

```text
docs/MOTHER_DEVELOPER_WORKSPACE_MATRIX.md
```

with:

```text
authorized: no
reason: <reason>
```

## Git safety gate

Before destructive or state-changing operations, record:

```bash
git status --short --branch
git diff --stat
git diff
git ls-files --others --exclude-standard
git rev-parse HEAD
git rev-parse origin/main
git worktree list 2>/dev/null || true
```

Human authorization is the final apply boundary.

## Continuation rule

When entering a new session:

1. Read `docs/PROJECT_MAP.md`.
2. Inspect live Git state.
3. Verify worktree topology.
4. Read governance/security documents.
5. Run the model-free smoke test.
6. Use the target project's own environment for its tests.
7. Report evidence and uncertainty before proposing changes.

Do not make Mahdi reconstruct the project history when it is already recorded in Git and
the project's evidence stores.
