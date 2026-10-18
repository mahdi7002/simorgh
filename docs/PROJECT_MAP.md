# SIMORGH PROJECT MAP
## Canonical public onboarding map

**Date:** 2026-09-26

This document is the public, Git-readable entry point for understanding and running SIMORGH.
It is intentionally portable: it does not contain secrets, live process state, or private
machine paths.

> `KNOWN != INFERRED`  
> `CLAIMED != VERIFIED`  
> `TRACEABLE != TRUE`  
> `PROVENANCE > elegance`

## 1. What SIMORGH is

SIMORGH is an open-source, offline-first, human-accountable AI/knowledge system.

Core principles:

- Proposal != Command
- Known != Inferred
- Provider != Authority
- User-owned memory
- Local-first execution
- Explicit human gate for governed mutation
- Evidence and provenance are first-class
- No silent autonomous self-modification

See also:

- `docs/GOVERNANCE.md`
- `docs/SECURITY_PROVENANCE_BASELINE.md`
- `docs/AGENT_FABRIC.md`
- `docs/PROJECT_MEMORY.md`

## 2. Public repository topology

The current public repository contains the main SIMORGH implementation, including:

```text
agents/
app/
compliance/
config/
core/
dashboard/
data/
demo/
docs/
governance/
knowledge/
memory/
models/
packaging/
scripts/
tests/
.github/
```

Important areas:

```text
core/memory.py
core/memory_journal.py
core/model_manager.py
core/local_backend.py
core/orchestration/
core/tools/
core/engine/memory_graph.py
core/engine/knowledge_graph.py
core/engine/mental_model.py
core/engine/world_model.py
core/project_scanner.py
agents/
models/catalog.json
```

## 3. Public repo vs local workspaces

`~/simorgh` is the main SIMORGH application workspace.

SIMORGH MOTHER is a separate developer-workspace continuity/observation project and is
not part of the public SIMORGH repository at this time.

Do not infer Mother source code, runtime state, or local uncommitted changes from the
public repository.

A local checkout may also contain sibling workspaces such as an agent-lab or sync
workspace. Their relationship must be established with live Git commands, not assumed.

## 4. First-run path for a new AI or developer

Clone:

```bash
git clone https://github.com/mahdi7002/simorgh.git
cd simorgh
```

Inspect before changing:

```bash
git status --short --branch
git rev-parse --show-toplevel
git rev-parse --git-dir
git log --oneline -n 20 --decorate
git remote -v
```

Run the model-free smoke test:

```bash
python3 demo/simorgh_minimal.py --test
```

Developer environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -c "import main; print('OK', len(main.app.routes))"
python main.py
```

In another terminal:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/personas
curl -s -X POST http://127.0.0.1:8000/chat -d "query=سلام&agent=hakim"
```

The application must not pretend a model response exists when no model is available.
Where a matching source exists, the deterministic local knowledge path may still work.

## 5. Verification contract

A technical claim should be represented as:

```text
CLAIM
  -> EVIDENCE
  -> VERIFICATION
  -> DECISION
```

Status vocabulary:

```text
VERIFIED
CLAIMED
NOT VERIFIED
NOT AVAILABLE
CONFLICT
```

An AI statement is not evidence merely because it sounds certain.

For tests and audits:

```text
NO_TESTS          != FAIL
ENVIRONMENT_ERROR != CODE_FAILURE
NO_CHECK_DEFINED  != BROKEN
```

A project must not be labelled broken without project-specific evidence.

## 6. Project-boundary rule

When inspecting a workspace, classify entities independently from authorship.

Structural classification may include:

```text
REPOSITORY
PROJECT
NESTED_PROJECT
COMPONENT
EXAMPLE
TEST_FIXTURE
VENDOR
ARTIFACT
ARCHIVE
UNKNOWN
```

Contribution provenance may include:

```text
USER_ORIGINAL
CLAUDE_CONTRIBUTED
CHATGPT_CONTRIBUTED
MULTI_AI
USER_PLUS_AI
IMPORTED
UNKNOWN
```

Do not use a build file alone, such as a `CMakeLists.txt`, to declare every directory a
separate project.

## 7. Git and runtime are different evidence layers

Git can describe source, history, tests, documentation, and committed decisions.

Git does not automatically prove:

- current processes
- current model server state
- RAM state
- uncommitted changes
- private runtime configuration
- secrets
- large local datasets not represented in the repository

Never commit secrets to make a project look complete.

For live-state checks, run the project's own diagnostic commands and record their output
and provenance.

## 8. Change-control boundary

The governing flow is:

```text
OBSERVE
  -> CAPTURE EVIDENCE
  -> CLASSIFY
  -> REVIEW
  -> TEST
  -> HUMAN AUTHORIZATION
  -> COMMIT
  -> VERIFY
  -> HANDOFF
```

No agent should silently convert a proposal into canonical project state.

## 9. Current Mother scope

Mother's current authorized work remains limited to:

1. Review/test/commit the existing Mother workspace files already present:
   `resource_manager.py`,
   `project_auditor.py`,
   `workspace_inspector.py`,
   `capability_assessment.py`,
   `git_observer.py`,
   `problem_memory.py`,
   `repository_config.py`,
   `workspace_capsule.py`, and their tests.

2. Fix foreign-project interpreter resolution so the target project's own interpreter is
   used when available.

3. Inspect and report backend binary provenance and active backend/model state.

4. Independently audit sibling workspaces only after the interpreter-resolution path is
   trustworthy.

New Scheduler, Model Arena, Task Executor, AI Work Ledger, or comparable architectural
modules are not authorized yet.

## 10. Unplanned work

Work outside the authorized scope must be traceable.

Commit message:

```text
[UNPLANNED] <description>
```

Record the reason in:

```text
docs/MOTHER_DEVELOPER_WORKSPACE_MATRIX.md
```

with:

```text
authorized: no
reason: <why it happened>
```

This records provenance; it is not an automatic acceptance or rejection.

## 11. Destructive-operation gate

Before reset, clean, delete, merge, rebase, overwrite, force-push, or equivalent state
changes, capture:

```bash
git status --short --branch
git diff --stat
git diff
git ls-files --others --exclude-standard
git rev-parse HEAD
git rev-parse origin/main
git worktree list 2>/dev/null || true
```

Do not perform a destructive operation solely because another AI recommended it.

## 12. Continuity target

The long-term project map should let a new AI answer:

```text
WHAT
WHY
HOW
RELATION
EVIDENCE
WHAT CHANGED
WHY IT CHANGED
WHO/WHAT CONTRIBUTED
```

The durable map belongs in Git. Large or volatile live evidence belongs in the appropriate
runtime/evidence store.

The project's human remains the final authority.
