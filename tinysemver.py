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
        --patch-file '"version": "(.*)"' 'package.json' \
        --patch-file '^version: (.*)' 'CITATION.cff'
    
    Multiple "--patch-file" arguments can be passed to update multiple files.
    Each of them must be followed by a RegEx pattern and a file path.
    The RegEx pattern must contain a capturing group to extract the version number,
    that will be replaced by the new version number.
"""
import argparse
import subprocess
import re
import os

from typing import List, Tuple, Literal, Union
from datetime import datetime

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


def get_commits_since_tag(repository_path: PathLike, tag: str) -> List[str]:
    result = subprocess.run(
        ["git", "log", f"{tag}..HEAD", "--pretty=format:%s"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=repository_path,
    )
    if result.returncode != 0:
        return []

    # Filter out empty lines and lines with only one character
    lines = result.stdout.strip().decode("utf-8").split("\n")
    lines = [line.strip() for line in lines if line.strip()]
    lines = [line for line in lines if len(line) > 1]
    return lines


def parse_version(tag: str) -> SemVer:
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        raise ValueError(f"Tag {tag} is not in a recognized version format")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def commit_starts_with_verb(commit: str, verb: str) -> bool:
    if commit.lower().startswith(verb):
        if (
            len(commit) == len(verb)
            or commit[len(verb)].isspace()
            or commit[len(verb)] == ":"
        ):
            return True
    return False


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


def create_tag(repository_path: PathLike, version: SemVer, push: bool = False) -> None:
    tag = f"v{version[0]}.{version[1]}.{version[2]}"
    subprocess.run(["git", "tag", tag], cwd=repository_path)
    if push:
        subprocess.run(["git", "push", "origin", tag], cwd=repository_path)
    print(f"Created new tag: {tag}")


def update_file_with_regex(
    file_path: str,
    regex_pattern: str,
    new_version: str,
) -> None:
    with open(file_path, "r") as file:
        content = file.read()

    new_content = re.sub(regex_pattern, new_version, content)

    with open(file_path, "w") as file:
        file.write(new_content)

    print(f"Updated file {file_path} with new version {new_version}")


def bump(
    dry_run: bool = False,
    verbose: bool = False,
    major_verbs: List[str] = ["breaking", "break", "major"],
    minor_verbs: List[str] = ["feature", "minor", "add", "new"],
    patch_verbs: List[str] = ["fix", "patch", "bug", "improve"],
    path: PathLike = None,  # takes current directory as default
    changelog_file: PathLike = "CHANGELOG.md",  # relative or absolute path to the changelog file
    version_file: PathLike = "VERSION",  # relative or absolute path to the version file
    patch_files: List[Tuple[str, PathLike]] = None,
) -> SemVer:

    # Check that the repository indeed contains a .git folder
    repository_path = os.path.abspath(path) if path else os.getcwd()
    assert os.path.isdir(
        os.path.join(repository_path, ".git")
    ), f"Not a Git repository: {repository_path}"

    # Ensure paths are relative to the provided working directory
    def normalize_path(file_path: str) -> str:
        if not file_path:
            return None
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(repository_path, file_path)

    changelog_file = normalize_path(changelog_file)
    version_file = normalize_path(version_file)
    if patch_files:
        patch_files = [(pattern, normalize_path(file)) for pattern, file in patch_files]

    assert not version_file or (
        not os.path.exists(version_file) or os.path.isfile(version_file)
    ), f"Version file is missing or isn't a regular file: {version_file}"
    assert not changelog_file or (
        not os.path.exists(changelog_file) or os.path.isfile(changelog_file)
    ), f"Changelog file is missing or isn't a regular file: {changelog_file}"

    # Normalizing the input arguments
    if isinstance(major_verbs, str):
        major_verbs = major_verbs.split(",")
    elif major_verbs is None:
        major_verbs = ["breaking", "break", "major"]
    if isinstance(minor_verbs, str):
        minor_verbs = minor_verbs.split(",")
    elif minor_verbs is None:
        minor_verbs = ["feature", "minor", "add", "new"]
    if isinstance(patch_verbs, str):
        patch_verbs = patch_verbs.split(",")
    elif patch_verbs is None:
        patch_verbs = ["fix", "patch", "bug", "improve"]

    # The actual logic begins here
    last_tag = get_last_tag(repository_path)
    assert last_tag, f"No tags found in the repository: {repository_path}"

    commits = get_commits_since_tag(repository_path, last_tag)
    assert len(commits), f"No new commits since the last {last_tag} tag, aborting."

    if verbose:
        print("Commits since last tag:")
        for commit in commits:
            print(f"  {commit}")

    current_version = parse_version(last_tag)
    if verbose:
        print(
            f"Current version: {current_version[0]}.{current_version[1]}.{current_version[2]}"
        )

    # Unzip commits history to infer the type of version bump,
    # and prepare changelogs down the road.
    major_commits, minor_commits, patch_commits = group_commits(
        commits, major_verbs, minor_verbs, patch_verbs
    )
    assert (
        len(major_commits) + len(minor_commits) + len(patch_commits)
    ), "No commit categories found to bump the version: " + ", ".join(commits)

    # Determine the type of version bump
    if len(major_commits):
        bump_type = "major"
    elif len(minor_commits):
        bump_type = "minor"
    else:
        bump_type = "patch"
    new_version = bump_version(current_version, bump_type)
    if verbose:
        print(
            f"Bumping version to: {new_version[0]}.{new_version[1]}.{new_version[2]} (type: {bump_type})"
        )

    # Update the version file
    new_version_str = f"{new_version[0]}.{new_version[1]}.{new_version[2]}"
    if version_file:
        if not dry_run:
            update_file_with_regex(version_file, r"(.*)", new_version_str)

    # Update the changelog file
    if changelog_file:
        now = datetime.now()
        changes = f"## {now:%B %d, %Y}: v{new_version_str}\n"
        if len(major_commits):
            changes += f"\n### Major\n" + "\n".join(f"- {c}" for c in major_commits)
        if len(minor_commits):
            changes += f"\n### Minor\n" + "\n".join(f"- {c}" for c in minor_commits)
        if len(patch_commits):
            changes += f"\n### Patch\n" + "\n".join(f"- {c}" for c in patch_commits)

        if not dry_run:
            with open(changelog_file, "a") as file:
                file.write(changes)
            if verbose:
                print(f"Updated changelog file {changelog_file}")
        else:
            print(f"Changelog updates:\n{changes}")

    # Update all patch files
    if patch_files:
        for regex_pattern, file_path in patch_files:
            if not dry_run:
                update_file_with_regex(file_path, regex_pattern, new_version_str)

    if not dry_run:
        create_tag(repository_path, new_version)


def main():
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
        help="Print more information",
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
        help="Comma-separated list of patch verbs, like 'fix,patch,bug,improve'",
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
        "--patch-file",
        nargs=2,
        action="append",
        metavar=("REGEX", "FILE"),
        help="Regex pattern and file path to update version",
    )
    parser.add_argument(
        "--path",
        help="Path to the git repository",
        default=".",
    )

    args = parser.parse_args()

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
            patch_files=args.patch_file,
        )
    except Exception as e:
        print(f"Failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
