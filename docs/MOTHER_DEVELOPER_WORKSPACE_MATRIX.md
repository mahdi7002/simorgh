# SIMORGH MOTHER: Developer Workspace Capability Matrix

This document records the capability families Mother intentionally combines.

| Capability | Existing ecosystem pattern | Mother implementation direction |
|---|---|---|
| Source reproducibility | Git, GitHub Codespaces | Git identity, refs, bundle |
| Environment definition | Dev Containers, Coder templates, Cloud Workstations | Detect and report `.devcontainer`, container, runtime contracts |
| Reproducible toolchains | Nix Flakes, mise, Devbox, Flox | Detect contracts and host availability |
| Fast workspace provisioning | Coder prebuilt workspaces, Codespaces prebuilds, Daytona snapshots | Cache metadata; capsules for explicit heavy capture |
| Local/remote execution | JetBrains Remote Development, Coder, StackBlitz | Explicit executor selection |
| Test-driven repair | Aider, coding agents, GitHub Copilot agents, Junie | Audit -> evidence -> repair attempt -> retest |
| Multi-project visibility | Workspace platforms and IDE portals | `audit-system` project discovery + health ledger |
| Recovery | Daytona snapshots + Git artifacts | Mother Capsule: bundle + index + staged/unstaged patches + untracked archive |
| Human control | Agent permission/review flows | No mutation or execution without explicit repair/run permission |
| Provenance | Git history and agent session traces | Every finding should carry path, command, output, and state |

## Core invariant

`repository URL` is a source identity, not a complete machine/workspace snapshot.

A complete recovery unit is:

`repository URL + Mother Capsule + execution contract + host facts`

## Safety invariant

Mother may inspect broadly, but execution and source mutation are explicit operations.
Unknown projects must be reported as unknown rather than guessed healthy.
