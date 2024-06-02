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

from typing import List, Tuple, Literal

SemVer = Tuple[int, int, int]
BumpType = Literal["major", "minor", "patch"]


def get_last_tag() -> str:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip().decode("utf-8")


def get_commits_since_tag(tag) -> List[str]:
    result = subprocess.run(
        ["git", "log", f"{tag}..HEAD", "--pretty=format:%s"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return []
    return result.stdout.strip().decode("utf-8").split("\n")


def parse_version(tag: str) -> SemVer:
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        raise ValueError(f"Tag {tag} is not in a recognized version format")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def determine_version_bump(commits: List[str]) -> BumpType:
    major_bump = re.compile(r"^\[major\]")
    minor_bump = re.compile(r"^\[minor\]")
    patch_bump = re.compile(r"^\[patch\]")

    major = minor = patch = False

    for commit in commits:
        if major_bump.match(commit):
            major = True
        elif minor_bump.match(commit):
            minor = True
        elif patch_bump.match(commit):
            patch = True

    if major:
        return "major"
    if minor:
        return "minor"
    if patch:
        return "patch"

    return "patch"  # Default to patch if no prefix found


def bump_version(version: SemVer, bump_type: BumpType) -> SemVer:
    major, minor, patch = version
    if bump_type == "major":
        return major + 1, 0, 0
    elif bump_type == "minor":
        return major, minor + 1, 0
    elif bump_type == "patch":
        return major, minor, patch + 1


def create_tag(version: SemVer, push: bool = False) -> None:
    tag = f"v{version[0]}.{version[1]}.{version[2]}"
    subprocess.run(["git", "tag", tag])
    if push:
        subprocess.run(["git", "push", "origin", tag])
    print(f"Created new tag: {tag}")


def main(
    path: str = ".",
    dry_run: bool = False,
    verbose: bool = False,
    major_verbs: list = ["breaking", "break", "major"],
    minor_verbs: list = ["feature", "minor", "add", "new"],
    patch_verbs: list = ["fix", "patch", "bug", "improve"],
    changelog_file: str = "CHANGELOG.md",  # relative or absolute path to the changelog file
    version_file: str = "VERSION",  # relative or absolute path to the version file
) -> None:

    # Check that the repository indeed contains a .git folder
    if not os.path.isdir(".git"):
        print("No .git folder found in the repository.")
        return

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
    last_tag = get_last_tag()
    if not last_tag:
        print("No tags found in the repository.")
        return

    commits = get_commits_since_tag(last_tag)
    if not commits:
        print("No new commits since the last tag.")
        return

    if verbose:
        print("Commits since last tag:")
        for commit in commits:
            print(f"  {commit}")

    current_version = parse_version(last_tag)
    if verbose:
        print(
            f"Current version: {current_version[0]}.{current_version[1]}.{current_version[2]}"
        )

    bump_type = determine_version_bump(commits)
    new_version = bump_version(current_version, bump_type)
    if verbose:
        print(
            f"Bumping version to: {new_version[0]}.{new_version[1]}.{new_version[2]} (type: {bump_type})"
        )

    if not dry_run:
        create_tag(new_version)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Tiny SemVer")
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not create a new tag"
    )
    parser.add_argument("--verbose", action="store_true", help="Print more information")
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
        "--changelog-file", help="Path to the changelog file, like 'CHANGELOG.md'"
    )
    parser.add_argument(
        "--version-file", help="Path to the version file, like 'VERSION'"
    )

    args = parser.parse_args()

    main(dry_run=args.dry_run, verbose=args.verbose)
