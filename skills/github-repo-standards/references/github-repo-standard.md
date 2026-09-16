# GitHub Repo Standard

## README Structure

- Start the file with a single `# ` title line. It is the first thing GitHub renders and the first thing a newcomer reads.
- Follow the title directly with a description paragraph, before the next heading: at least 20 characters of prose, not a badge row (`[![...`) or an image tag.
- Include at least one install or usage section, matched case-insensitively against: `install`, `安装`, `quick start`, `快速开始`, `usage`, `使用`, `getting started`.
- Never leave placeholder text in a published README: `TODO`, `TBD`, `lorem ipsum`, `coming soon`, or a literal `<repo-name>`-style placeholder. Replace it with real content or remove the section.
- Keep the README substantial enough to orient a reader — treat anything under ~200 characters as effectively empty.

## GitHub Discoverability Metadata

These live on the repository itself, not in a file, and require `gh repo view` to inspect:

- Set a repository description (the one-liner shown under the repo name and in search results). Leaving it empty makes the repo unsearchable by intent.
- Set at least 3 Topics. Topics drive GitHub's topic-browse and search ranking; GitHub already enforces their lowercase kebab-case format, so this standard only checks that enough of them exist.

## Out Of Scope

LICENSE, `.gitignore`, CI badges, CONTRIBUTING, and CODEOWNERS are not covered here. Internal file placement and naming are governed by `project-structure-governance`.
