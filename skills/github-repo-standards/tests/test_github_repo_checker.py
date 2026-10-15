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
