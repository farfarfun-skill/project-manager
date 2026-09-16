---
name: github-repo-standards
description: Audit a repository's GitHub-facing presentation — README structure (title, description paragraph, install/usage section, no placeholder text, minimum length) and discoverability metadata (repository description and Topics via `gh repo view`). Use when Codex needs to review or fix a README before publishing, or verify a public repo's Topics/description are set for discoverability. Use project-structure-governance instead for internal file placement and naming.
---

# GitHub Repo Standards

Judge whether a repository's public-facing surface — its README and GitHub Topics/description — gives a newcomer enough to understand and install the project. Do not judge product correctness or internal file layout; those belong to other checkers.

## Audit A Repository

Run from this skill directory:

```bash
python3 scripts/github_repo_checker.py --workspace /path/to/repo --fail-on revise
```

This checks `README.md` only: it requires an `# ` title, a non-badge description paragraph near the top, an install/usage section, no leftover placeholder text (`TODO`, `TBD`, `Lorem ipsum`, `<repo-name>`, ...), and a sane minimum length. It never touches the network.

Add `--check-topics` to also verify the repository's GitHub-side description and Topics through `gh repo view`:

```bash
python3 scripts/github_repo_checker.py --workspace /path/to/repo --check-topics --fail-on revise
```

This requires `gh` to be installed and authenticated, and the workspace's `origin` remote to point at GitHub. Only run it when that is available; omit the flag for a purely local, CI-safe check.

Use `--format json` for machine consumption.

## Apply The Standard

Read [github-repo-standard.md](references/github-repo-standard.md) before writing or fixing a README, or before deciding what to put in a repository's description/Topics.

## Return Results

Return `allow`, `revise`, or `block`, the passed checks, and the missing or weak items with concrete repair actions (e.g. which section to add, which placeholder to remove). Do not claim the README is well-written from a passing structural check; state that coverage is limited to structure and discoverability metadata.
