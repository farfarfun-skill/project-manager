#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path

USAGE_SECTION_RE = re.compile(
    r"^#{2,3}\s*.*(install|安装|quick start|快速开始|usage|使用|getting started).*$",
    re.IGNORECASE | re.MULTILINE,
)
PLACEHOLDER_RE = re.compile(
    r"\bTODO\b|\bTBD\b|lorem ipsum|coming soon|<repo-name>|<your-repo>",
    re.IGNORECASE,
)
BADGE_LINE_RE = re.compile(r"^\s*(\[!\[|<img\b)", re.IGNORECASE)
MIN_README_LENGTH = 200
MIN_DESCRIPTION_LENGTH = 20
MIN_TOPICS = 3


def finding(severity: str, code: str, path: str, message: str) -> dict:
    return {"severity": severity, "code": code, "path": path, "message": message}


def find_readme(workspace: Path) -> Path | None:
    canonical = workspace / "README.md"
    if canonical.is_file():
        return canonical
    for candidate in workspace.glob("[Rr][Ee][Aa][Dd][Mm][Ee].[Mm][Dd]"):
        if candidate.is_file():
            return candidate
    return None


def check_readme(workspace: Path, findings: list[dict], passes: list[str]) -> None:
    readme = find_readme(workspace)
    if readme is None:
        findings.append(finding("block", "readme.missing", "README.md", "仓库根目录缺少 README.md。"))
        return
    relative = readme.relative_to(workspace).as_posix()
    if readme.name != "README.md":
        findings.append(finding(
            "revise", "readme.case", relative,
            "README 文件名大小写不规范，GitHub 惯例要求使用 README.md。",
        ))

    text = readme.read_text(encoding="utf-8", errors="replace")
    if len(text.strip()) < MIN_README_LENGTH:
        findings.append(finding("block", "readme.too_short", relative, "README 内容过短，不足以说明项目。"))
        return

    lines = text.splitlines()
    non_blank = [line for line in lines if line.strip()]
    if not non_blank or not non_blank[0].startswith("# "):
        findings.append(finding("block", "readme.title_missing", relative, "README 必须以一级标题 `# ` 开头。"))
    else:
        passes.append(f"README 标题存在：{relative}")

    description_found = False
    for line in non_blank[1:]:
        if line.startswith("#"):
            break
        if BADGE_LINE_RE.match(line):
            continue
        if len(line.strip()) >= MIN_DESCRIPTION_LENGTH:
            description_found = True
            break
    if description_found:
        passes.append(f"README 简介段落存在：{relative}")
    else:
        findings.append(finding(
            "revise", "readme.description_missing", relative,
            "标题后未找到非徽章的简介段落，建议补充一段项目定位说明。",
        ))

    if USAGE_SECTION_RE.search(text):
        passes.append(f"README 包含安装/使用章节：{relative}")
    else:
        findings.append(finding(
            "revise", "readme.usage_section_missing", relative,
            "未找到安装或快速开始类章节标题（Install/安装/Quick Start/快速开始/Usage/使用）。",
        ))

    placeholder = PLACEHOLDER_RE.search(text)
    if placeholder:
        findings.append(finding(
            "block", "readme.placeholder", relative,
            f"README 中残留占位符文本：{placeholder.group(0)!r}，请替换为真实内容。",
        ))


def run_gh_repo_view(slug: str) -> dict:
    result = subprocess.run(
        ["gh", "repo", "view", slug, "--json", "description,repositoryTopics"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gh repo view failed")
    return json.loads(result.stdout)


def resolve_repo_slug(workspace: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(workspace), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    return match.group(1) if match else None


def check_topics(workspace: Path, findings: list[dict], passes: list[str]) -> None:
    slug = resolve_repo_slug(workspace)
    if slug is None:
        findings.append(finding(
            "block", "repo.metadata_unavailable", "origin",
            "无法从 git remote origin 解析出 GitHub owner/repo。",
        ))
        return

    try:
        data = run_gh_repo_view(slug)
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        findings.append(finding(
            "block", "repo.metadata_unavailable", slug,
            f"无法通过 gh 查询仓库元数据：{error}",
        ))
        return

    description = (data.get("description") or "").strip()
    if description:
        passes.append(f"GitHub 仓库描述已设置：{slug}")
    else:
        findings.append(finding("revise", "repo.description_missing", slug, "GitHub 仓库描述为空，建议补充一句话简介。"))

    topics = data.get("repositoryTopics") or []
    topic_names = [item.get("name", item) if isinstance(item, dict) else item for item in topics]
    if len(topic_names) >= MIN_TOPICS:
        passes.append(f"GitHub Topics 数量充足：{slug}（{len(topic_names)} 个）")
    else:
        findings.append(finding(
            "revise", "repo.topics_insufficient", slug,
            f"GitHub Topics 数量不足（当前 {len(topic_names)} 个，建议至少 {MIN_TOPICS} 个）。",
        ))


def analyze(workspace: Path, check_topics_flag: bool) -> dict:
    findings: list[dict] = []
    passes: list[str] = []
    check_readme(workspace, findings, passes)
    if check_topics_flag:
        check_topics(workspace, findings, passes)

    decision = "allow"
    if any(item["severity"] == "block" for item in findings):
        decision = "block"
    elif findings:
        decision = "revise"
    return {"decision": decision, "passes": passes, "findings": findings}


def render_text(report: dict) -> str:
    lines = [f"decision: {report['decision']}"]
    lines.extend(f"PASS: {item}" for item in report["passes"])
    for item in report["findings"]:
        lines.append(f"{item['severity'].upper()}: {item['path']} - {item['message']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="审计仓库的 README 结构与 GitHub Topics/描述。")
    parser.add_argument("--workspace", default=".", help="仓库根目录")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--fail-on", choices=("revise", "block"))
    parser.add_argument("--check-topics", action="store_true", help="额外通过 gh 查询 GitHub 仓库描述和 Topics")
    args = parser.parse_args()

    report = analyze(Path(args.workspace).resolve(), args.check_topics)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render_text(report))

    if args.fail_on == "revise" and report["decision"] in {"revise", "block"}:
        return 1
    if args.fail_on == "block" and report["decision"] == "block":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
