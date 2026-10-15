# GitHub Repo Standard

## Default Branch

- The default branch must be named `master`. A repository whose default branch is `main` (or anything else) is out of standard: clones and PRs land on the wrong base, and cross-repo tooling that assumes `master` breaks.
- Fix it on the GitHub side (`gh repo edit <slug> --default-branch master`, or rename the branch and push), not by keeping a local alias.
- With `--check-topics` the checker reads GitHub's own `defaultBranchRef`. Without it, it falls back to the local clone: `origin/HEAD` if set, otherwise whether a `master` branch exists, otherwise the current branch. A non-git workspace is skipped.

## README Structure

- Start the file with a single `# ` title line. It is the first thing GitHub renders and the first thing a newcomer reads.
- Follow the title directly with a description paragraph, before the next heading: at least 20 characters of prose, not a badge row (`[![...`) or an image tag.
- Include at least one install or usage section, matched case-insensitively against: `install`, `安装`, `quick start`, `快速开始`, `usage`, `使用`, `getting started`.
- Introduce the owning organization in a section of its own, saying what the organization does and where this repository sits inside it. Two halves are required, and both are judged on the whole README.
  - **Heading**: a `##`/`###` heading that is itself about the organization. Accepted forms are `## 关于 <org>` (e.g. `## 关于 farfarfun`, the form pinned by the organization's own SPEC), `## 关于组织`, `## 组织介绍`, `## 关于我们`, `## Organization` and `## About <org>`/`## About Us`; leading emoji or numbering decoration is ignored. The heading line is matched end to end, so a feature heading that merely contains the word — `## Sync organization forks & mirror to Gitee` — is not an organization section. Missing heading is reported as `readme.org_section_missing`.
  - **Link**: the README must contain the organization homepage itself, a bare `https://github.com/<owner>` with `<owner>` taken from the `origin` remote. A URL that continues into a repository (`https://github.com/<owner>/<repo>`, including `git clone` lines and sibling-repository links) does not count. Missing link is reported as `readme.org_link_missing` — which is also what a repository gets when its section names some other organization than its own owner. A repository with no resolvable owner is only checked for the heading.
- Never leave template placeholder text in a published README: `lorem ipsum`, `coming soon`, or a literal `<repo-name>`/`<your-repo>` placeholder. These are matched case-insensitively and anywhere in the file, including inside fenced code blocks — an uncustomized `git clone .../<repo-name>.git` is the single most common leftover. Only inline code is exempt, so a README may quote the placeholder while describing this rule. Replace it with real content or remove the section.
- Treat `TODO`/`TBD` as something to confirm, not something to block on. A `## TODO` roadmap section is a legitimate way to publish what is planned, and `todo-list`, `docs/TODO.md` and the like are names of things that really exist. The checker therefore reports these at `revise`, and only when all of the following hold: the word is upper-case (lower-case identifiers such as `todo-list` never match), it sits at the start of a line after at most decoration like `#`, `-`, `>` or an emoji (a mid-sentence mention does not match), and it is outside code blocks, inline code, markdown links and bare URLs. Resolve it by finishing the section or by making clear it is a published roadmap.
- Keep the README substantial enough to orient a reader — treat anything under ~200 characters as effectively empty.

## GitHub Discoverability Metadata

These live on the repository itself, not in a file, and require `gh repo view` to inspect:

- Set a repository description (the one-liner shown under the repo name and in search results). Leaving it empty makes the repo unsearchable by intent.
- Write the description in Chinese. These repositories are read by a Chinese-speaking audience first; a description with no CJK characters is out of standard. Latin product names, acronyms and code identifiers may of course stay as they are inside an otherwise Chinese sentence.
- Set at least 5 Topics. Topics drive GitHub's topic-browse and search ranking; GitHub already enforces their lowercase kebab-case format, so this standard only checks that enough of them exist.

## Out Of Scope

LICENSE, `.gitignore`, CI badges, CONTRIBUTING, and CODEOWNERS are not covered here. Internal file placement and naming are governed by `project-structure-governance`.
