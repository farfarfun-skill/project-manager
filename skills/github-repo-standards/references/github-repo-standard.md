# GitHub Repo Standard

## Default Branch

- The default branch must be named `master`. A repository whose default branch is `main` (or anything else) is out of standard: clones and PRs land on the wrong base, and cross-repo tooling that assumes `master` breaks.
- Fix it on the GitHub side (`gh repo edit <slug> --default-branch master`, or rename the branch and push), not by keeping a local alias.
- With `--check-topics` the checker reads GitHub's own `defaultBranchRef`. Without it, it falls back to the local clone: `origin/HEAD` if set, otherwise whether a `master` branch exists, otherwise the current branch. A non-git workspace is skipped.

## README Structure

- Start the file with a single `# ` title line. It is the first thing GitHub renders and the first thing a newcomer reads.
- Follow the title directly with a description paragraph, before the next heading: at least 20 characters of prose, not a badge row (`[![...`) or an image tag.
- Include at least one install or usage section, matched case-insensitively against: `install`, `安装`, `quick start`, `快速开始`, `usage`, `使用`, `getting started`.
- Introduce the owning organization. Add a `##`/`###` section whose heading matches `组织`, `organization`, `关于我们` or `about us` — e.g. `## 关于组织` — saying what the organization does and where this repository sits inside it. It must link to the organization homepage `https://github.com/<owner>`, with `<owner>` taken from the `origin` remote; a repository with no resolvable owner is only checked for the section itself.
- Never leave placeholder text in a published README: `TODO`, `TBD`, `lorem ipsum`, `coming soon`, or a literal `<repo-name>`-style placeholder. Replace it with real content or remove the section.
- Keep the README substantial enough to orient a reader — treat anything under ~200 characters as effectively empty.

## GitHub Discoverability Metadata

These live on the repository itself, not in a file, and require `gh repo view` to inspect:

- Set a repository description (the one-liner shown under the repo name and in search results). Leaving it empty makes the repo unsearchable by intent.
- Write the description in Chinese. These repositories are read by a Chinese-speaking audience first; a description with no CJK characters is out of standard. Latin product names, acronyms and code identifiers may of course stay as they are inside an otherwise Chinese sentence.
- Set at least 5 Topics. Topics drive GitHub's topic-browse and search ranking; GitHub already enforces their lowercase kebab-case format, so this standard only checks that enough of them exist.

## Out Of Scope

LICENSE, `.gitignore`, CI badges, CONTRIBUTING, and CODEOWNERS are not covered here. Internal file placement and naming are governed by `project-structure-governance`.
