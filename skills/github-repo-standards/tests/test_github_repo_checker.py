import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.github_repo_checker import analyze

VALID_README = """# demo-project

demo-project turns raw sensor exports into normalized time-series records for downstream analytics.

## Install

```bash
pip install demo-project
```

## Usage

```bash
demo-project run --input data.csv
```

## 关于组织

本仓库属于 [acme](https://github.com/acme) 组织，该组织维护数据采集与分析方向的工具链。
"""


README_WITHOUT_ORG_SECTION = VALID_README.split("## 关于组织")[0]

# 规范钉死的组织介绍区块写法：标题是 `## 关于 <组织名>`，正文给出组织主页链接。
SPEC_ORG_BLOCK = """---

## 关于 acme

[acme](https://github.com/acme) 是一个专注于实用工具库的开源组织，涵盖数据采集、分析与开发工具链等方向。

- 🏠 组织主页：<https://github.com/acme>
- 📧 联系：acme@example.com

本项目基于 [MIT](LICENSE) 协议开源。
"""


FULL_METADATA = {
    "defaultBranchRef": {"name": "master"},
    "description": "把原始传感器导出转换为规范化时序记录的示例项目。",
    "repositoryTopics": [{"name": name} for name in ("python", "cli", "etl", "sensors", "time-series")],
}


def write_readme(workspace: Path, content: str, name: str = "README.md") -> None:
    (workspace / name).write_text(content, encoding="utf-8")


def init_repo(workspace: Path, branch: str) -> None:
    subprocess.run(["git", "init", "-b", branch, str(workspace)], check=True, capture_output=True)


class ReadmeChecksTests(unittest.TestCase):
    def test_missing_readme_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = analyze(Path(temp_dir), check_topics_flag=False)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "readme.missing" for item in report["findings"]))

    def test_valid_readme_allows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("allow", report["decision"])
            self.assertEqual([], report["findings"])

    def test_missing_title_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README.replace("# demo-project", "demo-project", 1))
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "readme.title_missing" for item in report["findings"]))

    def test_missing_description_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            content = (
                "# demo-project\n\n"
                "## Install\n\npip install demo-project\n\n"
                "## Usage\n\ndemo-project run\n\n"
                "This trailing paragraph only exists to pad the README content past the minimum length threshold that the checker enforces for this particular test case.\n"
            )
            write_readme(workspace, content)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "readme.description_missing" for item in report["findings"]))

    def test_missing_usage_section_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            content = VALID_README.split("## Install")[0] + (
                "This paragraph exists only to pad the README past the minimum length threshold for tests.\n"
            )
            write_readme(workspace, content)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "readme.usage_section_missing" for item in report["findings"]))

    def assert_readme_clean(self, extra: str) -> None:
        """README 追加这段内容后不应产生任何问题。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README + extra)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual([], report["findings"])

    def assert_placeholder_blocks(self, extra: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README + extra)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "readme.placeholder" for item in report["findings"]))

    def assert_todo_marker_revises(self, extra: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README + extra)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "readme.todo_marker" for item in report["findings"]))

    def test_todo_list_tracking_link_is_clean(self) -> None:
        """本组织惯例：README 链到 todo-list 仓库跟踪需求，不是「README 没写完」。"""
        self.assert_readme_clean(
            "\n需求与缺陷在 [farfarfun/todo-list](https://github.com/farfarfun/todo-list/issues) 跟踪。\n"
        )

    def test_lowercase_todo_identifier_is_clean(self) -> None:
        """占位符语义靠大写表达，行首的小写标识符不该命中。"""
        self.assert_readme_clean("\ntodo-list 仓库负责汇总本仓库的待办事项。\n")

    def test_uppercase_todo_in_link_is_clean(self) -> None:
        """链接文字和链接目标都指向真实存在的文档。"""
        self.assert_readme_clean("\n已知待优化项见 [docs/TODO.md](docs/TODO.md)。\n")

    def test_uppercase_todo_in_inline_code_is_clean(self) -> None:
        self.assert_readme_clean("\n待办清单维护在 `docs/TODO.md` 里。\n")

    def test_uppercase_todo_in_bare_url_is_clean(self) -> None:
        self.assert_readme_clean("\n看板：https://github.com/acme/TODO-board/projects/1\n")

    def test_uppercase_todo_in_code_block_is_clean(self) -> None:
        """代码示例里的 TODO 注释是示例的一部分，不是 README 的坑。"""
        self.assert_readme_clean("\n```python\n# TODO: 这里留给调用方扩展\npass\n```\n")

    def test_uppercase_todo_mid_sentence_is_clean(self) -> None:
        """只有行首标记位才是占位符，句子中间提到 TODO 是在讲这件事本身。"""
        self.assert_readme_clean("\nAll TODO items are tracked in the issue tracker, not in this file.\n")

    def test_todo_heading_revises(self) -> None:
        """`## TODO` 当路线图小节是常见写法，值得确认但不该拦住发布。"""
        self.assert_todo_marker_revises("\n## TODO\n\n- 补充性能基准\n")

    def test_todo_prose_marker_revises(self) -> None:
        self.assert_todo_marker_revises("\nTODO: write more docs.\n")

    def test_template_placeholder_in_code_block_blocks(self) -> None:
        """代码块不豁免：未定制的模板最常残留在安装命令里。"""
        self.assert_placeholder_blocks(
            "\n```bash\ngit clone https://github.com/acme/<repo-name>.git\ncd <repo-name>\n```\n"
        )

    def test_template_placeholder_in_prose_blocks(self) -> None:
        self.assert_placeholder_blocks("\n把 <your-repo> 替换成你自己的仓库名。\n")

    def test_coming_soon_blocks(self) -> None:
        """这几个词没有歧义，大小写都算残留。"""
        self.assert_placeholder_blocks("\n## Benchmarks\n\nComing soon.\n")

    def test_lorem_ipsum_blocks(self) -> None:
        self.assert_placeholder_blocks("\nLorem ipsum dolor sit amet, consectetur adipiscing elit.\n")

    def test_template_placeholder_in_inline_code_is_clean(self) -> None:
        """只有讨论这个写法本身时才会把它写进行内代码。"""
        self.assert_readme_clean("\n检查器会拦下 README 里残留的 `<repo-name>` 字样。\n")

    def test_too_short_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, "# tiny\n\nshort.\n")
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "readme.too_short" for item in report["findings"]))

    def test_missing_org_section_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README.split("## 关于组织")[0])
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "readme.org_section_missing" for item in report["findings"]))

    def test_org_section_without_link_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README.replace("[acme](https://github.com/acme) ", ""))
            with patch("scripts.github_repo_checker.resolve_repo_slug", return_value="acme/demo-project"):
                report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "readme.org_link_missing" for item in report["findings"]))

    def analyze_org_section(self, section: str, slug: str = "acme/demo-project") -> dict:
        """把给定的组织介绍段落接在 README 末尾，按 slug 的 owner 判定。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, README_WITHOUT_ORG_SECTION + section)
            with patch("scripts.github_repo_checker.resolve_repo_slug", return_value=slug):
                return analyze(workspace, check_topics_flag=False)

    def assert_org_code(self, section: str, code: str | None, slug: str = "acme/demo-project") -> None:
        report = self.analyze_org_section(section, slug)
        org_codes = [item["code"] for item in report["findings"] if item["code"].startswith("readme.org")]
        self.assertEqual([code] if code else [], org_codes)

    def test_spec_org_block_is_clean(self) -> None:
        """规范要求逐字复制的区块：标题 `## 关于 <组织名>`，不含「组织」二字也要认。"""
        self.assert_org_code(SPEC_ORG_BLOCK, None)

    def test_legacy_org_heading_is_clean(self) -> None:
        """旧写法 `## 关于组织` 仍然合规，不逼已经写好的仓库返工。"""
        self.assert_org_code(
            "## 关于组织\n\n本仓库属于 [acme](https://github.com/acme) 组织，该组织维护数据方向的工具链。\n",
            None,
        )

    def test_org_heading_named_after_owning_org_is_clean(self) -> None:
        """子组织仓库用自己的组织名写标题和链接。"""
        self.assert_org_code(
            "## 关于 acme-drive\n\n本仓库属于 [acme-drive](https://github.com/acme-drive)，负责网盘方向。\n",
            None,
            slug="acme-drive/demo-project",
        )

    def test_org_section_pointing_at_other_org_revises(self) -> None:
        """标题写对了但链接指向别的组织：是链接缺失，不是章节缺失。"""
        self.assert_org_code(SPEC_ORG_BLOCK, "readme.org_link_missing", slug="acme-drive/demo-project")

    def test_org_section_with_only_repo_link_revises(self) -> None:
        """组织主页链接不能用本仓库或兄弟仓库的地址顶替。"""
        self.assert_org_code(
            "## 关于 acme\n\n本仓库属于 acme，另见 [acme/other-repo](https://github.com/acme/other-repo)。\n",
            "readme.org_link_missing",
        )

    def test_sibling_repo_links_without_org_section_revises(self) -> None:
        """只有兄弟仓库链接、没有组织章节：报章节缺失，不该因为凑巧含 owner 子串而通过。"""
        self.assert_org_code(
            "## 相关仓库\n\n```bash\ngit clone https://github.com/acme/demo-project.git\n```\n\n"
            "数据源见 [acme/other-repo](https://github.com/acme/other-repo)。\n",
            "readme.org_section_missing",
        )

    def test_functional_heading_mentioning_organization_revises(self) -> None:
        """功能标题里凑巧出现 `organization`，正文也有组织主页链接，仍然不算组织介绍。"""
        self.assert_org_code(
            "## Sync organization forks & mirror to Gitee\n\n"
            "同步 [acme](https://github.com/acme) 下所有 fork，无需手动触发。\n",
            "readme.org_section_missing",
        )

    def test_lowercase_filename_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README, name="readme.md")
            report = analyze(workspace, check_topics_flag=False)
            self.assertTrue(any(item["code"] == "readme.case" for item in report["findings"]))


class TopicsChecksTests(unittest.TestCase):
    def test_metadata_unavailable_when_gh_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            with patch("scripts.github_repo_checker.resolve_repo_slug", return_value="acme/demo-project"), \
                 patch("scripts.github_repo_checker.run_gh_repo_view", side_effect=RuntimeError("not authenticated")):
                report = analyze(workspace, check_topics_flag=True)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "repo.metadata_unavailable" for item in report["findings"]))

    def analyze_with_metadata(self, workspace: Path, **overrides) -> dict:
        data = {**FULL_METADATA, **overrides}
        with patch("scripts.github_repo_checker.resolve_repo_slug", return_value="acme/demo-project"), \
             patch("scripts.github_repo_checker.run_gh_repo_view", return_value=data):
            return analyze(workspace, check_topics_flag=True)

    def test_four_topics_revise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            topics = FULL_METADATA["repositoryTopics"][:4]
            report = self.analyze_with_metadata(workspace, repositoryTopics=topics)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "repo.topics_insufficient" for item in report["findings"]))

    def test_missing_description_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            report = self.analyze_with_metadata(workspace, description="")
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "repo.description_missing" for item in report["findings"]))

    def test_english_description_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            report = self.analyze_with_metadata(workspace, description="A demo project.")
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "repo.description_language" for item in report["findings"]))

    def test_remote_default_branch_main_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            report = self.analyze_with_metadata(workspace, defaultBranchRef={"name": "main"})
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "repo.default_branch" for item in report["findings"]))

    def test_full_metadata_allows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            report = self.analyze_with_metadata(workspace)
            self.assertEqual("allow", report["decision"])
            self.assertEqual([], report["findings"])


class DefaultBranchChecksTests(unittest.TestCase):
    def test_master_branch_allows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            init_repo(workspace, "master")
            write_readme(workspace, VALID_README)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("allow", report["decision"])

    def test_main_branch_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            init_repo(workspace, "main")
            write_readme(workspace, VALID_README)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "repo.default_branch" for item in report["findings"]))

    def test_non_git_workspace_skips_branch_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("allow", report["decision"])
            self.assertFalse(any("默认分支" in item for item in report["passes"]))


if __name__ == "__main__":
    unittest.main()
