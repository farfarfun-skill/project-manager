# GitHub Repo Standards

用于审计仓库对外门面的 Codex skill：README 结构是否完整，以及 GitHub 仓库描述、Topics 是否有利于检索和理解。

## 功能

- 检查 README 是否有一级标题、非徽章的简介段落、安装/使用类章节。
- 检查 README 是否残留占位符文本或内容过短。
- 可选：通过 `gh repo view` 检查仓库描述和 Topics 数量（需要 `gh` 已登录，且默认不开启，避免影响 CI）。

## 快速开始

```bash
python3 scripts/github_repo_checker.py --workspace /path/to/repo --fail-on revise
python3 scripts/github_repo_checker.py --workspace /path/to/repo --check-topics --fail-on revise
```

## 文档

- [Skill 使用说明](SKILL.md)
- [GitHub 仓库规范](references/github-repo-standard.md)
