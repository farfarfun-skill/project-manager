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
"""


def write_readme(workspace: Path, content: str, name: str = "README.md") -> None:
    (workspace / name).write_text(content, encoding="utf-8")


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

    def test_placeholder_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README + "\nTODO: write more docs.\n")
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "readme.placeholder" for item in report["findings"]))

    def test_too_short_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, "# tiny\n\nshort.\n")
            report = analyze(workspace, check_topics_flag=False)
            self.assertEqual("block", report["decision"])
            self.assertTrue(any(item["code"] == "readme.too_short" for item in report["findings"]))

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

    def test_insufficient_topics_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            data = {"description": "A demo project.", "repositoryTopics": [{"name": "python"}]}
            with patch("scripts.github_repo_checker.resolve_repo_slug", return_value="acme/demo-project"), \
                 patch("scripts.github_repo_checker.run_gh_repo_view", return_value=data):
                report = analyze(workspace, check_topics_flag=True)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "repo.topics_insufficient" for item in report["findings"]))

    def test_missing_description_revises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            data = {"description": "", "repositoryTopics": [{"name": "python"}, {"name": "cli"}, {"name": "etl"}]}
            with patch("scripts.github_repo_checker.resolve_repo_slug", return_value="acme/demo-project"), \
                 patch("scripts.github_repo_checker.run_gh_repo_view", return_value=data):
                report = analyze(workspace, check_topics_flag=True)
            self.assertEqual("revise", report["decision"])
            self.assertTrue(any(item["code"] == "repo.description_missing" for item in report["findings"]))

    def test_full_metadata_allows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            write_readme(workspace, VALID_README)
            data = {
                "description": "A demo project.",
                "repositoryTopics": [{"name": "python"}, {"name": "cli"}, {"name": "etl"}],
            }
            with patch("scripts.github_repo_checker.resolve_repo_slug", return_value="acme/demo-project"), \
                 patch("scripts.github_repo_checker.run_gh_repo_view", return_value=data):
                report = analyze(workspace, check_topics_flag=True)
            self.assertEqual("allow", report["decision"])


if __name__ == "__main__":
    unittest.main()
