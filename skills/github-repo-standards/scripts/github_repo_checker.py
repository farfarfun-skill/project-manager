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
ORG_SECTION_RE = re.compile(
    r"^#{2,3}\s*.*(组织|organization|关于我们|about us).*$",
    re.IGNORECASE | re.MULTILINE,
)
# 未定制的模板残留，没有歧义，命中即 block。保留大小写不敏感：`Lorem Ipsum` 同样是残留。
PLACEHOLDER_RE = re.compile(r"lorem ipsum|coming soon|<repo-name>|<your-repo>", re.IGNORECASE)
# TODO/TBD 有歧义：既可能是没写完的坑，也可能是真实存在的东西的名字（仓库 `todo-list`、
# 文档 `docs/TODO.md`），还可能是一个照常维护的路线图小节标题。所以收窄三道：
# 只认全大写（占位符语义本来就靠大写表达，`todo-list` 这种小写标识符不算）；代码、链接、
# 裸 URL 里的放过（指向的是真实存在的东西）；只认行首标记位，前面只允许 `#`/`-`/`>`/emoji
# 这类装饰，`## 📋 TODO` 算，句子中间提到 TODO 不算。命中按 revise 报而不是 block。
TODO_MARKER_RE = re.compile(r"^[^A-Za-z一-鿿]*(TODO|TBD)\b", re.MULTILINE)
FENCED_CODE_RE = re.compile(r"^ {0,3}(```|~~~).*?(?:^ {0,3}\1|\Z)", re.MULTILINE | re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]\n]*\]\(\s*[^)\s]*(?:\s+\"[^\"]*\")?\s*\)")
AUTOLINK_RE = re.compile(r"<?https?://\S+>?")
BADGE_LINE_RE = re.compile(r"^\s*(\[!\[|<img\b)", re.IGNORECASE)
CJK_RE = re.compile(r"[一-鿿]")
MIN_README_LENGTH = 200
MIN_DESCRIPTION_LENGTH = 20
MIN_TOPICS = 5
REQUIRED_DEFAULT_BRANCH = "master"
DEFAULT_BRANCH_CODE = "repo.default_branch"


def finding(severity: str, code: str, path: str, message: str) -> dict:
    return {"severity": severity, "code": code, "path": path, "message": message}


def blank_out(pattern: re.Pattern[str], text: str) -> str:
    """把匹配到的片段换成等长空白，换行保留。

    不直接删掉是为了让后续匹配的位置、行号和行首锚点仍然对应原文。
    """
    return pattern.sub(lambda match: re.sub(r"[^\n]", " ", match.group(0)), text)


def find_placeholder(text: str) -> str | None:
    """返回 README 里第一个模板占位符，没有则 None。

    只豁免行内代码——介绍本规范的 README 得能引用这些写法本身。代码块不豁免：
    `git clone .../<repo-name>.git` 正是未定制模板最典型的残留位置。
    """
    outside_fences = blank_out(FENCED_CODE_RE, text)
    chunks = [blank_out(INLINE_CODE_RE, outside_fences)]
    chunks.extend(match.group(0) for match in FENCED_CODE_RE.finditer(text))
    for chunk in chunks:
        match = PLACEHOLDER_RE.search(chunk)
        if match:
            return match.group(0)
    return None


def find_todo_marker(text: str) -> str | None:
    """返回 README 散文里第一个 TODO/TBD 标记，没有则 None。"""
    prose = text
    for pattern in (FENCED_CODE_RE, INLINE_CODE_RE, MARKDOWN_LINK_RE, AUTOLINK_RE):
        prose = blank_out(pattern, prose)
    match = TODO_MARKER_RE.search(prose)
    return match.group(1) if match else None


def git_output(workspace: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


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

    check_org_section(workspace, text, relative, findings, passes)

    placeholder = find_placeholder(text)
    if placeholder:
        findings.append(finding(
            "block", "readme.placeholder", relative,
            f"README 中残留模板占位符：{placeholder!r}，请替换为真实内容。",
        ))

    todo_marker = find_todo_marker(text)
    if todo_marker:
        findings.append(finding(
            "revise", "readme.todo_marker", relative,
            f"README 中有 {todo_marker!r} 标记，请确认它是对外维护的路线图而不是没写完的段落。",
        ))


def check_org_section(workspace: Path, text: str, relative: str, findings: list[dict], passes: list[str]) -> None:
    """README 必须介绍所属组织：既要有组织章节，也要给出组织主页链接。"""
    if not ORG_SECTION_RE.search(text):
        findings.append(finding(
            "revise", "readme.org_section_missing", relative,
            "README 缺少组织介绍章节（如 `## 关于组织`），请补充所属组织的定位与仓库在其中的位置。",
        ))
        return

    slug = resolve_repo_slug(workspace)
    owner = slug.split("/", 1)[0] if slug else None
    if owner and f"github.com/{owner}" not in text:
        findings.append(finding(
            "revise", "readme.org_link_missing", relative,
            f"组织介绍未链接到组织主页 https://github.com/{owner}，请补充链接。",
        ))
        return
    passes.append(f"README 包含组织介绍：{relative}")


def detect_default_branch(workspace: Path) -> str | None:
    """本地推断默认分支：origin/HEAD 优先，其次看 master 是否存在，最后回退到当前分支。"""
    origin_head = git_output(workspace, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if origin_head:
        return origin_head.split("/", 1)[1] if "/" in origin_head else origin_head
    refs = git_output(workspace, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes/origin")
    branches = set(refs.splitlines()) if refs else set()
    if REQUIRED_DEFAULT_BRANCH in branches or f"origin/{REQUIRED_DEFAULT_BRANCH}" in branches:
        return REQUIRED_DEFAULT_BRANCH
    return git_output(workspace, "symbolic-ref", "--short", "HEAD")  # 游离 HEAD 时返回 None，跳过


def judge_default_branch(branch: str, path: str, findings: list[dict], passes: list[str]) -> None:
    if branch == REQUIRED_DEFAULT_BRANCH:
        passes.append(f"默认分支为 {REQUIRED_DEFAULT_BRANCH}：{path}")
        return
    findings.append(finding(
        "block", DEFAULT_BRANCH_CODE, path,
        f"默认分支为 {branch!r}，规范要求主分支必须命名为 {REQUIRED_DEFAULT_BRANCH}。",
    ))


def check_default_branch(workspace: Path, findings: list[dict], passes: list[str]) -> None:
    """本地分支检查，仅在没有 gh 权威结论时使用。"""
    if git_output(workspace, "rev-parse", "--git-dir") is None:
        return  # 不是 git 仓库，跳过分支检查
    branch = detect_default_branch(workspace)
    if branch is None:
        return
    judge_default_branch(branch, "HEAD", findings, passes)


def run_gh_repo_view(slug: str) -> dict:
    result = subprocess.run(
        ["gh", "repo", "view", slug, "--json", "defaultBranchRef,description,repositoryTopics"],
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


def check_topics(workspace: Path, findings: list[dict], passes: list[str]) -> bool:
    """查询 GitHub 侧元数据。返回是否已拿到权威数据（拿到则默认分支由此判定）。"""
    slug = resolve_repo_slug(workspace)
    if slug is None:
        findings.append(finding(
            "block", "repo.metadata_unavailable", "origin",
            "无法从 git remote origin 解析出 GitHub owner/repo。",
        ))
        return False

    try:
        data = run_gh_repo_view(slug)
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        findings.append(finding(
            "block", "repo.metadata_unavailable", slug,
            f"无法通过 gh 查询仓库元数据：{error}",
        ))
        return False

    branch_ref = data.get("defaultBranchRef") or {}
    branch = branch_ref.get("name") if isinstance(branch_ref, dict) else branch_ref
    if branch:
        judge_default_branch(branch, slug, findings, passes)

    description = (data.get("description") or "").strip()
    if not description:
        findings.append(finding("revise", "repo.description_missing", slug, "GitHub 仓库描述为空，建议补充一句话中文简介。"))
    elif not CJK_RE.search(description):
        findings.append(finding(
            "revise", "repo.description_language", slug,
            "GitHub 仓库描述未使用中文，规范要求描述以中文书写。",
        ))
    else:
        passes.append(f"GitHub 仓库描述已设置且为中文：{slug}")

    topics = data.get("repositoryTopics") or []
    topic_names = [item.get("name", item) if isinstance(item, dict) else item for item in topics]
    if len(topic_names) >= MIN_TOPICS:
        passes.append(f"GitHub Topics 数量充足：{slug}（{len(topic_names)} 个）")
    else:
        findings.append(finding(
            "revise", "repo.topics_insufficient", slug,
            f"GitHub Topics 数量不足（当前 {len(topic_names)} 个，规范要求至少 {MIN_TOPICS} 个）。",
        ))
    return True


def analyze(workspace: Path, check_topics_flag: bool) -> dict:
    findings: list[dict] = []
    passes: list[str] = []
    check_readme(workspace, findings, passes)
    judged_remotely = check_topics(workspace, findings, passes) if check_topics_flag else False
    if not judged_remotely:
        check_default_branch(workspace, findings, passes)

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
