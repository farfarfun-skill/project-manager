---
name: github-repo-standards
description: Audit a repository's GitHub-facing presentation — default branch naming (`master`), README structure (title, description paragraph, install/usage section, organization section, no template placeholder text, minimum length) and discoverability metadata (Chinese repository description and at least 5 Topics via `gh repo view`). Use when Codex needs to review or fix a README before publishing, or verify a public repo's default branch, Topics and description are set for discoverability. Use project-structure-governance instead for internal file placement and naming.
---

# GitHub Repo Standards

Judge whether a repository's public-facing surface — its README and GitHub Topics/description — gives a newcomer enough to understand and install the project. Do not judge product correctness or internal file layout; those belong to other checkers.

## Audit A Repository

Run from this skill directory:

```bash
python3 scripts/github_repo_checker.py --workspace /path/to/repo --fail-on revise
```

This checks `README.md` plus the default branch: the README needs an `# ` title, a non-badge description paragraph near the top, an install/usage section, an organization section (`## 关于 <org>`, `## 关于组织`, `## Organization`, `## About Us` …) plus the bare organization homepage `https://github.com/<owner>` somewhere in the README — a repository URL under that owner does not satisfy it — no leftover template placeholder (`lorem ipsum`, `coming soon`, `<repo-name>`, `<your-repo>`), and a sane minimum length; an upper-case `TODO`/`TBD` marker at the start of a line outside code and links is reported at `revise` rather than `block`, because a published `## TODO` roadmap is legitimate; the default branch must be `master`, inferred from the local clone (`origin/HEAD`, else the presence of a `master` branch, else the current branch) and skipped outside a git repository. It never touches the network.

Add `--check-topics` to also verify the repository's GitHub-side default branch, description and Topics through `gh repo view`:

```bash
python3 scripts/github_repo_checker.py --workspace /path/to/repo --check-topics --fail-on revise
```

This requires `gh` to be installed and authenticated, and the workspace's `origin` remote to point at GitHub. Only run it when that is available; omit the flag for a purely local, CI-safe check.

Use `--format json` for machine consumption.

## Apply The Standard

Read [github-repo-standard.md](references/github-repo-standard.md) before writing or fixing a README, or before deciding what to put in a repository's description/Topics.

## Return Results

Return `allow`, `revise`, or `block`, the passed checks, and the missing or weak items with concrete repair actions (e.g. which section to add, which placeholder to remove). Do not claim the README is well-written from a passing structural check; state that coverage is limited to structure and discoverability metadata.
