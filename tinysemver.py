#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TinySemVer is a tiny Python script that helps you manage your project's versioning.

This module traces the commit history of a Git repository after the last tag, and based 
on the commit messages, it determines the type of version bump (major, minor, or patch).
On "dry-runs" it simply reports the new version number, but on actual runs, it creates a
a new tag, and optionally pushes it to the repository, also updating the "version file",
the "changelog file", and all other files and RegEx patterns passed as CLI arguments.

Example:

    tinysemver --dry-run --verbose \
        --major-verbs 'breaking,break,major' \
        --minor-verbs 'feature,minor,add,new' \
        --patch-verbs 'fix,patch,bug,improve' \
        --changelog-file 'CHANGELOG.md' \
        --version-file 'VERSION' \
        --update-version-in 'package.json' '"version": "(.*)"' \
        --update-version-in 'CITATION.cff' '^version: (.*)' \
        --update-major-version-in 'include/stringzilla/stringzilla.h' '^#define STRINGZILLA_VERSION_MAJOR (.*)' \
        --update-minor-version-in 'include/stringzilla/stringzilla.h' '^#define STRINGZILLA_VERSION_MINOR (.*)' \
        --update-patch-version-in 'include/stringzilla/stringzilla.h' '^#define STRINGZILLA_VERSION_PATCH (.*)'
    
    Multiple "--update-version-in" arguments can be passed to update multiple files.
    Each of them must be followed by a file path and a RegEx pattern.
    The RegEx pattern must contain a capturing group to extract the version number,
    that will be replaced by the new version number.

By default, the following conventions are used:

    - The repository must be a Git repository.
    - It must contain a "VERSION" and "CHANGELOG.md" files in the root directory.
    - The changelog is append-only - sorted in chronological order.

Setting up a new project:

    $ git init # Initialize a new Git repository
    $ echo "0.1.0" > VERSION # Create a version file
    $ echo "# Changelog" > CHANGELOG.md # Create a changelog file
    $ git add VERSION CHANGELOG.md # Add the files to the repository
    $ git commit -m "Add: Initial files" # Create the first commit
    $ git tag v0.1.0 # Create the first tag

"""
import argparse
import subprocess
import re
import os
from typing import List, Tuple, Literal, Union, Optional
from datetime import datetime
import traceback

SemVer = Tuple[int, int, int]
BumpType = Literal["major", "minor", "patch"]
PathLike = Union[str, os.PathLike]


def get_last_tag(repository_path: PathLike) -> str:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=repository_path,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip().decode("utf-8")


def get_commits_since_tag(repository_path: PathLike, tag: str) -> Tuple[List[str], List[str]]:
    result = subprocess.run(
        ["git", "log", f"{tag}..HEAD", "--pretty=format:%h:%s"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=repository_path,
    )
    if result.returncode != 0:
        return [], []

    lines = result.stdout.strip().decode("utf-8").split("\n")
    hashes = [line.partition(":")[0] for line in lines if line.strip()]
    commits = [line.partition(":")[2] for line in lines if line.strip()]
    return hashes, commits


def parse_version(tag: str) -> SemVer:
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        raise ValueError(f"Tag {tag} is not in a recognized version format")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def commit_starts_with_verb(commit: str, verb: str) -> bool:
    if commit.lower().startswith(verb):
        if len(commit) == len(verb) or commit[len(verb)].isspace() or commit[len(verb)] == ":":
            return True
    return False


def normalize_verbs(verbs: Union[str, List[str]], defaults: List[str]) -> List[str]:
    if isinstance(verbs, str):
        return [verb.strip("\"'") for verb in verbs.split(",")]
    elif verbs is None:
        return defaults
    else:
        return verbs


def group_commits(
    commits: List[str],
    major_verbs: List[str],
    minor_verbs: List[str],
    patch_verbs: List[str],
) -> Tuple[List[str], List[str], List[str]]:
    major_commits = []
    minor_commits = []
    patch_commits = []

    for commit in commits:
        if any(commit_starts_with_verb(commit, verb) for verb in major_verbs):
            major_commits.append(commit)
        if any(commit_starts_with_verb(commit, verb) for verb in minor_verbs):
            minor_commits.append(commit)
        if any(commit_starts_with_verb(commit, verb) for verb in patch_verbs):
            patch_commits.append(commit)

    return major_commits, minor_commits, patch_commits


def bump_version(version: SemVer, bump_type: BumpType) -> SemVer:
    major, minor, patch = version
    if bump_type == "major":
        return major + 1, 0, 0
    elif bump_type == "minor":
        return major, minor + 1, 0
    elif bump_type == "patch":
        return major, minor, patch + 1


def create_tag(
    *,  # enforce keyword-only arguments
    repository_path: PathLike,
    version: SemVer,
    user_name: str,
    user_email: str,
    github_token: Optional[str] = None,
    github_repository: Optional[str] = None,
    push: bool = False,
) -> None:
    tag = f"v{version[0]}.{version[1]}.{version[2]}"
    env = os.environ.copy()
    env["GIT_COMMITTER_NAME"] = user_name
    env["GIT_COMMITTER_EMAIL"] = user_email
    message = f"Release: {tag}"
    subprocess.run(["git", "add", "-A"], cwd=repository_path)
    subprocess.run(["git", "commit", "-m", message], cwd=repository_path, env=env)
    subprocess.run(["git", "tag", "-a", tag, "-m", message], cwd=repository_path, env=env)
    print(f"Created new tag: {tag}")
    if push:
        url = None
        if github_token and github_repository:
            url = f"https://x-access-token:{github_token}@github.com/{github_repository}"
        elif not github_token and not github_repository:
            url = "origin"
        else:
            assert github_repository and not github_token, "You can't provide the GitHub token without the repository"
            url = f"https://github.com/{github_repository}"

        # Pull the latest changes from the remote repository
        # pull_result = subprocess.run(["git", "pull", "--merge", url], cwd=repository_path, env=env)
        # if pull_result.returncode != 0:
        #     raise RuntimeError("Failed to pull the latest changes from the remote repository")

        # Push both commits and the tag
        push_result = subprocess.run(["git", "push", url], cwd=repository_path, env=env)
        if push_result.returncode != 0:
            raise RuntimeError("Failed to push the new commits to the remote repository")

        push_result = subprocess.run(["git", "push", url, "--tag"], cwd=repository_path, env=env)
        if push_result.returncode != 0:
            raise RuntimeError("Failed to push the new tag to the remote repository")
        print(f"Pushed to: {url}")


def patch_with_regex(
    file_path: str,
    regex_pattern: str,
    new_version: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:

    with open(file_path, "r") as file:
        old_content = file.read()

    def replace_first_group(match):
        assert len(match.groups()) == 1, f"Must contain exactly one capturing group in: {regex_pattern} for {file_path}"
        range_to_replace = match.span(1)
        return match.string[: range_to_replace[0]] + new_version + match.string[range_to_replace[1] :]

    # Without using the re.MULTILINE flag,
    # the ^ and $ anchors match the start and end of the whole string.
    regex_pattern = re.compile(regex_pattern, re.MULTILINE)
    matches = list(re.finditer(regex_pattern, old_content))
    new_content = re.sub(regex_pattern, replace_first_group, old_content, 1)

    non_empty_matches = [m for m in matches if len(m.group(0).strip())]
    assert len(non_empty_matches) > 0, f"No matches found in: {file_path}"

    for match in non_empty_matches:
        match_line = old_content.count("\n", 0, match.pos) + 1
        old_slice = match.group(0)
        new_slice = re.sub(regex_pattern, replace_first_group, old_slice, 1)

        if verbose:
            print(f"Will update file: {file_path}:{match_line}")
            print(f"- {old_slice}")
            print(f"+ {new_slice}")

    if not dry_run:
        with open(file_path, "w") as file:
            file.write(new_content)


def bump(
    *,  # enforce keyword-only arguments
    dry_run: bool = False,
    verbose: bool = False,
    major_verbs: List[str] = ["major", "breaking", "break"],
    minor_verbs: List[str] = ["minor", "feature", "add", "new"],
    patch_verbs: List[str] = ["patch", "fix", "bug", "improve", "docs"],
    path: Optional[PathLike] = None,  # takes current directory as default
    changelog_file: Optional[PathLike] = None,  # relative or absolute path to the changelog file
    version_file: Optional[PathLike] = None,  # relative or absolute path to the version file
    update_version_in: Optional[List[Tuple[PathLike, str]]] = None,
    update_major_version_in: Optional[List[Tuple[PathLike, str]]] = None,
    update_minor_version_in: Optional[List[Tuple[PathLike, str]]] = None,
    update_patch_version_in: Optional[List[Tuple[PathLike, str]]] = None,
    git_user_name: str = "TinySemVer",
    git_user_email: str = "tinysemver@ashvardanian.com",
    push: bool = True,
    github_token: Optional[str] = None,
    github_repository: Optional[str] = None,
) -> SemVer:

    repository_path = os.path.abspath(path) if path else os.getcwd()
    assert os.path.isdir(os.path.join(repository_path, ".git")), f"Not a Git repository: {repository_path}"

    def normalize_path(file_path: str) -> str:
        if not file_path or len(file_path) == 0:
            return None
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(repository_path, file_path)

    changelog_file = normalize_path(changelog_file)
    version_file = normalize_path(version_file)
    if update_version_in:
        update_version_in = [(normalize_path(file), pattern) for file, pattern in update_version_in]
    if update_major_version_in:
        update_major_version_in = [(normalize_path(file), pattern) for file, pattern in update_major_version_in]
    if update_minor_version_in:
        update_minor_version_in = [(normalize_path(file), pattern) for file, pattern in update_minor_version_in]
    if update_patch_version_in:
        update_patch_version_in = [(normalize_path(file), pattern) for file, pattern in update_patch_version_in]

    # Let's pull the environment variables from the GitHub Action context
    # https://cli.github.com/manual/gh_help_environment
    if not dry_run:
        github_token = github_token or os.getenv("GH_TOKEN", None)
        assert not github_token or len(github_token) > 0, "GitHub token is empty or missing"
        github_repository = github_repository or os.getenv("GH_REPOSITORY", None)
        assert not github_repository or len(github_repository) > 0, "GitHub repository is empty or missing"
        if github_repository:
            matched_repository = re.match(r"[\w-]*\/[\w-]*", github_repository)
            assert (
                matched_repository and matched_repository.string == github_repository
            ), "GitHub repository must be in the 'owner/repo' format"

    assert not version_file or (
        not os.path.exists(version_file) or os.path.isfile(version_file)
    ), f"Version file is missing or isn't a regular file: {version_file}"
    assert not changelog_file or (
        not os.path.exists(changelog_file) or os.path.isfile(changelog_file)
    ), f"Changelog file is missing or isn't a regular file: {changelog_file}"

    major_verbs = normalize_verbs(major_verbs, ["major", "breaking", "break"])
    minor_verbs = normalize_verbs(minor_verbs, ["minor", "feature", "add", "new"])
    patch_verbs = normalize_verbs(patch_verbs, ["patch", "fix", "bug", "improve", "docs"])

    last_tag = get_last_tag(repository_path)
    assert last_tag, f"No tags found in the repository: {repository_path}"

    current_version = parse_version(last_tag)
    if verbose:
        print(f"Current version: {current_version[0]}.{current_version[1]}.{current_version[2]}")

    commits_hashes, commits_messages = get_commits_since_tag(repository_path, last_tag)
    assert len(commits_hashes), f"No new commits since the last {last_tag} tag, aborting."

    if verbose:
        print(f"? Commits since last tag: {len(commits_hashes)}")
        for hash, commit in zip(commits_hashes, commits_messages):
            print(f"# {hash}: {commit}")

    major_commits, minor_commits, patch_commits = group_commits(commits_messages, major_verbs, minor_verbs, patch_verbs)
    assert (
        len(major_commits) + len(minor_commits) + len(patch_commits)
    ), "No commit categories found to bump the version: " + ", ".join(commits_messages)

    if len(major_commits):
        bump_type = "major"
    elif len(minor_commits):
        bump_type = "minor"
    else:
        bump_type = "patch"
    new_version = bump_version(current_version, bump_type)
    if verbose:
        print(f"Next version: {new_version[0]}.{new_version[1]}.{new_version[2]} (type: {bump_type})")

    new_version_str = f"{new_version[0]}.{new_version[1]}.{new_version[2]}"
    if version_file:
        patch_with_regex(version_file, r"(.*)", new_version_str, dry_run=dry_run, verbose=verbose)

    if changelog_file:
        now = datetime.now()
        changes = f"\n## {now:%B %d, %Y}: v{new_version_str}\n"
        if len(major_commits):
            changes += f"\n### Major\n\n" + "\n".join(f"- {c}" for c in major_commits) + "\n"
        if len(minor_commits):
            changes += f"\n### Minor\n\n" + "\n".join(f"- {c}" for c in minor_commits) + "\n"
        if len(patch_commits):
            changes += f"\n### Patch\n\n" + "\n".join(f"- {c}" for c in patch_commits) + "\n"

        print(f"Will update file: {changelog_file}")
        if verbose:
            changes_lines = changes.count("\n") + 1
            print(f"? Appending {changes_lines} lines")

        if not dry_run:
            with open(changelog_file, "a") as file:
                file.write(changes)

    if update_version_in:
        for file_path, regex_pattern in update_version_in:
            patch_with_regex(file_path, regex_pattern, new_version_str, dry_run=dry_run, verbose=verbose)
    if bump_type in ["major"] and update_major_version_in:
        for file_path, regex_pattern in update_major_version_in:
            patch_with_regex(file_path, regex_pattern, str(new_version[0]), dry_run=dry_run, verbose=verbose)
    if bump_type in ["major", "minor"] and update_minor_version_in:
        for file_path, regex_pattern in update_minor_version_in:
            patch_with_regex(file_path, regex_pattern, str(new_version[1]), dry_run=dry_run, verbose=verbose)
    if bump_type in ["major", "minor", "patch"] and update_patch_version_in:
        for file_path, regex_pattern in update_patch_version_in:
            patch_with_regex(file_path, regex_pattern, str(new_version[2]), dry_run=dry_run, verbose=verbose)

    if not dry_run:
        create_tag(
            repository_path=repository_path,
            version=new_version,
            user_name=git_user_name,
            user_email=git_user_email,
            github_token=github_token,
            github_repository=github_repository,
            push=push,
        )


def main():
    if 'GITHUB_ACTIONS' not in os.environ:
        parser = argparse.ArgumentParser(description="Tiny Semantic Versioning tool")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Do not create a new tag",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            default=False,
            help="Print more informations",
        )
        parser.add_argument(
            "--push",
            action="store_true",
            default=False,
            help="Push the new tag to the repository",
        )
        parser.add_argument(
            "--major-verbs",
            help="Comma-separated list of major verbs, like 'breaking,break,major'",
        )
        parser.add_argument(
            "--minor-verbs",
            help="Comma-separated list of minor verbs, like 'feature,minor,add,new'",
        )
        parser.add_argument(
            "--patch-verbs",
            help="Comma-separated list of patch verbs, like 'fix,patch,bug,improve,docs'",
        )
        parser.add_argument(
            "--changelog-file",
            help="Path to the changelog file, like 'CHANGELOG.md'",
        )
        parser.add_argument(
            "--version-file",
            help="Path to the version file, like 'VERSION'",
        )
        parser.add_argument(
            "--update-version-in",
            nargs=2,
            action="append",
            metavar=("FILE", "REGEX"),
            help="File path and regex pattern to update version",
        )
        parser.add_argument(
            "--update-major-version-in",
            nargs=2,
            action="append",
            metavar=("FILE", "REGEX"),
            help="File path and regex pattern to update major version",
        )
        parser.add_argument(
            "--update-minor-version-in",
            nargs=2,
            action="append",
            metavar=("FILE", "REGEX"),
            help="File path and regex pattern to update minor version",
        )
        parser.add_argument(
            "--update-patch-version-in",
            nargs=2,
            action="append",
            metavar=("FILE", "REGEX"),
            help="File path and regex pattern to update patch version",
        )
        parser.add_argument(
            "--path",
            default=".",
            help="Path to the git repository",
        )
        parser.add_argument(
            "--git-user-name",
            default="TinySemVer",
            help="Git user name for commits",
        )
        parser.add_argument(
            "--git-user-email",
            default="tinysemver@ashvardanian.com",
            help="Git user email for commits",
        )
        parser.add_argument(
            "--github-token",
            help="GitHub access token to push to protected branches, if not set will use GH_TOKEN env var",
        )
        parser.add_argument(
            "--github-repository",
            help="GitHub repository in the 'owner/repo' format, if not set will use GH_REPOSITORY env var",
        )
        args = parser.parse_args()
    else:
        args.dry_run = os.environ.get('DRY_RUN', '').lower() == 'true'
        args.verbose = os.environ.get('VERBOSE', '').lower() == 'true'
        args.push = os.environ.get('PUSH', '').lower() == 'true'
        args.major_verbs = os.environ.get('MAJOR_VERBS')
        args.minor_verbs = os.environ.get('MINOR_VERBS')
        args.patch_verbs = os.environ.get('PATCH_VERBS')
        args.changelog_file = os.environ.get('CHANGELOG_FILE')
        args.version_file = os.environ.get('VERSION_FILE')
        args.update_version_in = [tuple(item.split(',')) for item in os.environ.get('UPDATE_VERSION_IN', '').split(';') if item]
        args.update_major_version_in = [tuple(item.split(',')) for item in os.environ.get('UPDATE_MAJOR_VERSION_IN', '').split(';') if item]
        args.update_minor_version_in = [tuple(item.split(',')) for item in os.environ.get('UPDATE_MINOR_VERSION_IN', '').split(';') if item]
        args.update_patch_version_in = [tuple(item.split(',')) for item in os.environ.get('UPDATE_PATCH_VERSION_IN', '').split(';') if item]
        args.path = os.environ.get('PATH', '.')
        args.git_user_name = os.environ.get('GIT_USER_NAME', 'TinySemVer')
        args.git_user_email = os.environ.get('GIT_USER_EMAIL', 'tinysemver@ashvardanian.com')
        args.github_token = os.environ.get('GITHUB_TOKEN')
        args.github_repository = os.environ.get('GITHUB_REPOSITORY')

    try:
        bump(
            path=args.path,
            dry_run=args.dry_run,
            verbose=args.verbose,
            major_verbs=args.major_verbs,
            minor_verbs=args.minor_verbs,
            patch_verbs=args.patch_verbs,
            changelog_file=args.changelog_file,
            version_file=args.version_file,
            update_version_in=args.update_version_in,
            update_major_version_in=args.update_major_version_in,
            update_minor_version_in=args.update_minor_version_in,
            update_patch_version_in=args.update_patch_version_in,
            git_user_name=args.git_user_name,
            git_user_email=args.git_user_email,
            github_token=args.github_token,
            github_repository=args.github_repository,
            push=args.push,
        )
    except AssertionError as e:
        print(f"! {e}")
        exit(1)
    except Exception as e:
        traceback.print_exc(e)
        exit(1)


if __name__ == "__main__":
    main()
