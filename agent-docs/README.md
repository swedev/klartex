# Agent Docs

`agent-docs/` is the persistent working memory for coding agents in this repository.
It stores planning artifacts, decisions, and progress that should survive across sessions.

## Purpose

- Keep implementation context close to the code.
- Make work resumable across agent runs.
- Separate transient chat from durable project decisions.

## Structure

- `main/`:
  - Main-branch context and stable docs for this repository
    - `index.md`: branch-level summary and context file index
    - `project-brief.md`: product/problem summary
    - `tech-context.md`: stack and runtime context
    - `system-patterns.md`: architecture and implementation patterns
- `issue/<issue-number>-<slug>/`:
  - Per-issue execution docs
  - Typical files:
    - `index.md`: issue summary and metadata
    - `plan.md`: implementation plan
    - `progress.md`: execution status/log
  - Templates:
    - `issue/templates/TEMPLATE-index.md`
    - `issue/templates/TEMPLATE-plan.md`
    - `issue/templates/TEMPLATE-progress.md`
- `github/`:
  - GitHub reference data (committed)
    - `info.json`: repository owner, name, and primary branch

## Recommended Workflow

1. Analyze:
   - Review open issues and priorities
   - Run `/sync-github` to refresh cached issue/PR data
2. Plan:
   - Create or update `issue/<number>-<slug>/plan.md`
   - Capture scope, risks, and implementation steps
3. Execute:
   - Implement against the plan
   - Keep `progress.md` current as work proceeds
4. Consolidate:
   - Roll completed work into broader release/context docs
   - Clean up stale issue folders when no longer needed

## Branch Naming Convention

- `main` is the release branch.
- Issue work branches use: `issue/<issue-number>-<slug>`.

## Conventions

- Keep documents concise and factual.
- Use stable paths and file names so automation can find documents.
- Prefer updating status fields over rewriting history.
