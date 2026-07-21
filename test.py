#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive tests for TinySemVer.

Run with:
    pytest test.py -v
    pytest test.py -v --cov=tinysemver --cov-report=html
"""
import os
import re
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest

from tinysemver.tinysemver import (
    parse_version,
    bump_version,
    commit_starts_with_verb,
    normalize_verbs,
    group_commits,
    convert_commits_to_message,
    patch_with_regex,
    get_last_tag,
    get_commits_since_tag,
    get_diff_for_commit,
    Commit,
    NoNewCommitsError,
    bump,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_git_repo() -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True
        )

        # Create initial files
        (repo_path / "VERSION").write_text("0.1.0\n")
        (repo_path / "CHANGELOG.md").write_text("# Changelog\n\n")

        # Initial commit
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add: Initial files"], cwd=repo_path, check=True, capture_output=True
        )

        # Create initial tag
        subprocess.run(["git", "tag", "v0.1.0"], cwd=repo_path, check=True, capture_output=True)

        yield repo_path


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a sample file for regex patching tests."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text(
        'version = "1.2.3"\n'
        "# Some content\n"
        'another_version = "1.2.3"\n'
        "VERSION_MAJOR = 1\n"
        "VERSION_MINOR = 2\n"
        "VERSION_PATCH = 3\n"
    )
    return file_path


# ============================================================================
# Unit Tests - Version Parsing and Bumping
# ============================================================================


class TestVersionParsing:
    """Tests for version parsing and bumping functions."""

    def test_parse_version_with_v_prefix(self):
        assert parse_version("v1.2.3") == (1, 2, 3)

    def test_parse_version_without_v_prefix(self):
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_parse_version_with_leading_zeros(self):
        assert parse_version("v0.0.1") == (0, 0, 1)

    def test_parse_version_large_numbers(self):
        assert parse_version("v10.20.30") == (10, 20, 30)

    def test_parse_version_invalid_format(self):
        with pytest.raises(ValueError):
            parse_version("invalid")

    def test_parse_version_missing_components(self):
        with pytest.raises(ValueError):
            parse_version("v1.2")

    def test_bump_major(self):
        assert bump_version((1, 2, 3), "major") == (2, 0, 0)

    def test_bump_minor(self):
        assert bump_version((1, 2, 3), "minor") == (1, 3, 0)

    def test_bump_patch(self):
        assert bump_version((1, 2, 3), "patch") == (1, 2, 4)

    def test_bump_major_resets_minor_and_patch(self):
        assert bump_version((5, 10, 20), "major") == (6, 0, 0)

    def test_bump_minor_resets_patch(self):
        assert bump_version((5, 10, 20), "minor") == (5, 11, 0)


# ============================================================================
# Unit Tests - Commit Parsing
# ============================================================================


class TestCommitParsing:
    """Tests for commit message parsing and grouping."""

    def test_commit_starts_with_verb_exact_match(self):
        assert commit_starts_with_verb("fix: bug", "fix")
        assert commit_starts_with_verb("Fix: bug", "fix")
        assert commit_starts_with_verb("FIX: bug", "fix")

    def test_commit_starts_with_verb_with_space(self):
        assert commit_starts_with_verb("fix something", "fix")

    def test_commit_starts_with_verb_with_colon(self):
        assert commit_starts_with_verb("fix: something", "fix")

    def test_commit_starts_with_verb_no_match(self):
        assert not commit_starts_with_verb("fixed something", "fix")
        assert not commit_starts_with_verb("prefix fix", "fix")

    def test_commit_starts_with_verb_partial_word(self):
        # Should not match if verb is part of a larger word
        assert not commit_starts_with_verb("fixable", "fix")

    def test_normalize_verbs_from_string(self):
        result = normalize_verbs("major,breaking,break", [])
        assert result == ["major", "breaking", "break"]

    def test_normalize_verbs_with_quotes(self):
        result = normalize_verbs('"major","breaking"', [])
        assert result == ["major", "breaking"]

    def test_normalize_verbs_from_list(self):
        result = normalize_verbs(["major", "breaking"], [])
        assert result == ["major", "breaking"]

    def test_normalize_verbs_none_uses_defaults(self):
        defaults = ["default1", "default2"]
        result = normalize_verbs(None, defaults)
        assert result == defaults

    def test_group_commits_major(self):
        commits = [
            Commit("abc123", "breaking: remove API"),
            Commit("def456", "feat: add feature"),
            Commit("ghi789", "fix: bug"),
        ]
        major, minor, patch = group_commits(commits, ["breaking"], ["feat"], ["fix"])

        assert len(major) == 1
        assert major[0].message == "breaking: remove API"
        assert len(minor) == 1
        assert minor[0].message == "feat: add feature"
        assert len(patch) == 1
        assert patch[0].message == "fix: bug"

    def test_group_commits_multiple_verbs(self):
        commits = [
            Commit("abc", "break: API change"),
            Commit("def", "major: version bump"),
            Commit("ghi", "add: new feature"),
            Commit("jkl", "feature: another feature"),
        ]
        major, minor, patch = group_commits(
            commits, ["break", "major", "breaking"], ["add", "feature", "feat"], ["fix", "bug"]
        )

        assert len(major) == 2
        assert len(minor) == 2
        assert len(patch) == 0

    def test_group_commits_case_insensitive(self):
        commits = [
            Commit("abc", "Fix: bug"),
            Commit("def", "FIX: another bug"),
            Commit("ghi", "fix: yet another"),
        ]
        _, _, patch = group_commits(commits, [], [], ["fix"])
        assert len(patch) == 3

    def test_convert_commits_to_message(self):
        major = [Commit("abc", "breaking: remove API")]
        minor = [Commit("def", "feat: add feature")]
        patch = [Commit("ghi", "fix: bug")]

        message = convert_commits_to_message(major, minor, patch)

        assert "### Major" in message
        assert "breaking: remove API (abc)" in message
        assert "### Minor" in message
        assert "feat: add feature (def)" in message
        assert "### Patch" in message
        assert "fix: bug (ghi)" in message

    def test_convert_commits_to_message_empty(self):
        message = convert_commits_to_message([], [], [])
        assert message == ""

    def test_convert_commits_to_message_partial(self):
        patch = [Commit("ghi", "fix: bug")]
        message = convert_commits_to_message([], [], patch)

        assert "### Major" not in message
        assert "### Minor" not in message
        assert "### Patch" in message


# ============================================================================
# Unit Tests - Regex Patching
# ============================================================================


class TestRegexPatching:
    """Tests for file patching with regex."""

    def test_patch_with_regex_simple_version(self, sample_file):
        patch_with_regex(sample_file, r'version = "(.*)"', "2.0.0", dry_run=False, verbose=False)
        content = sample_file.read_text()
        assert 'version = "2.0.0"' in content
        # Should only replace first match
        assert 'another_version = "1.2.3"' in content

    def test_patch_with_regex_dry_run(self, sample_file):
        original = sample_file.read_text()
        patch_with_regex(sample_file, r'version = "(.*)"', "2.0.0", dry_run=True, verbose=False)
        assert sample_file.read_text() == original

    def test_patch_with_regex_no_match(self, sample_file):
        with pytest.raises(AssertionError, match="No matches found"):
            patch_with_regex(sample_file, r'nonexistent = "(.*)"', "2.0.0", dry_run=False, verbose=False)

    def test_patch_with_regex_multiple_capture_groups(self, sample_file):
        with pytest.raises(AssertionError, match="Must contain exactly one capturing group"):
            patch_with_regex(sample_file, r'version = "(.*)\.(.*)\..*"', "2.0.0", dry_run=False, verbose=False)

    def test_patch_with_regex_integer_version(self, sample_file):
        patch_with_regex(sample_file, r"VERSION_MAJOR = (\d+)", "5", dry_run=False, verbose=False)
        content = sample_file.read_text()
        assert "VERSION_MAJOR = 5" in content

    def test_patch_with_regex_multiline(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("version:\n  major: 1\n  minor: 2\n")

        patch_with_regex(file_path, r"major: (\d+)", "5", dry_run=False, verbose=False)
        content = file_path.read_text()
        assert "major: 5" in content

    def test_patch_with_regex_missing_file(self, tmp_path):
        nonexistent = tmp_path / "nonexistent.txt"
        with pytest.raises(AssertionError, match="File missing"):
            patch_with_regex(nonexistent, r"(.*)", "test", dry_run=False, verbose=False)

    def test_patch_with_regex_all_occurrences(self, tmp_path):
        """count=0 rewrites every match, not just the first."""
        file_path = tmp_path / "README.md"
        file_path.write_text('dep = "1.2.3"\ndep = "1.2.3"\ndep = "1.2.3"\n')
        patch_with_regex(file_path, r'^dep = "(\d+\.\d+\.\d+)"', "2.0.0", dry_run=False, verbose=False, count=0)
        content = file_path.read_text()
        assert content.count('dep = "2.0.0"') == 3
        assert "1.2.3" not in content

    def test_patch_with_regex_default_first_only(self, tmp_path):
        """The default count leaves later matches alone - what the single-line version file relies on."""
        file_path = tmp_path / "README.md"
        file_path.write_text('dep = "1.2.3"\ndep = "1.2.3"\n')
        patch_with_regex(file_path, r'^dep = "(\d+\.\d+\.\d+)"', "2.0.0", dry_run=False, verbose=False)
        content = file_path.read_text()
        assert content.count('dep = "2.0.0"') == 1
        assert content.count('dep = "1.2.3"') == 1


# ============================================================================
# Unit Tests - Git Operations
# ============================================================================


class TestGitOperations:
    """Tests for git-related operations."""

    def test_get_last_tag(self, temp_git_repo):
        tag = get_last_tag(temp_git_repo)
        assert tag == "v0.1.0"

    def test_get_last_tag_multiple_tags(self, temp_git_repo):
        # Add more commits and tags
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add: file"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "tag", "v0.2.0"], cwd=temp_git_repo, check=True, capture_output=True)

        tag = get_last_tag(temp_git_repo)
        assert tag == "v0.2.0"

    def test_get_last_tag_ignores_moving_aliases(self, temp_git_repo):
        # The moving `v0` and `v0.1` aliases point at the same commit as the real release and are
        # newer annotated tags, exactly as `push_moving_tags` leaves them - they must never win.
        subprocess.run(
            ["git", "tag", "-a", "v0", "-m", "Update v0 to v0.1.0", "v0.1.0^{}"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "tag", "-a", "v0.1", "-m", "Update v0.1 to v0.1.0", "v0.1.0^{}"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        tag = get_last_tag(temp_git_repo)
        assert tag == "v0.1.0"

    def test_get_last_tag_no_tags(self, tmp_path):
        # Create a repo without tags
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)

        tag = get_last_tag(tmp_path)
        assert tag is None

    def test_get_commits_since_tag(self, temp_git_repo):
        # Add some commits
        (temp_git_repo / "file1.txt").write_text("content1")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: add file1"], cwd=temp_git_repo, check=True, capture_output=True
        )

        (temp_git_repo / "file2.txt").write_text("content2")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: bug"], cwd=temp_git_repo, check=True, capture_output=True)

        commits = get_commits_since_tag(temp_git_repo, "v0.1.0")

        assert len(commits) == 2
        assert commits[0].message == "fix: bug"  # Most recent first
        assert commits[1].message == "feat: add file1"
        assert len(commits[0].hash) > 0

    def test_get_commits_since_tag_no_new_commits(self, temp_git_repo):
        commits = get_commits_since_tag(temp_git_repo, "v0.1.0")
        assert len(commits) == 0

    def test_get_diff_for_commit(self, temp_git_repo):
        # Add a commit with changes
        (temp_git_repo / "file.txt").write_text("line1\nline2\n")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add: file"], cwd=temp_git_repo, check=True, capture_output=True)

        # Get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=temp_git_repo, capture_output=True, text=True, check=True
        )
        commit_hash = result.stdout.strip()

        diff = get_diff_for_commit(temp_git_repo, commit_hash)

        assert "file.txt" in diff
        assert "+line1" in diff
        assert "+line2" in diff


# ============================================================================
# Integration Tests - Full Workflow
# ============================================================================


class TestFullWorkflow:
    """Integration tests for complete bump workflow."""

    def test_bump_dry_run(self, temp_git_repo):
        """Test dry-run mode doesn't modify anything."""
        # Add a commit
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: new feature"], cwd=temp_git_repo, check=True, capture_output=True
        )

        original_version = (temp_git_repo / "VERSION").read_text()
        original_changelog = (temp_git_repo / "CHANGELOG.md").read_text()

        # Run dry-run
        new_version = bump(
            path=temp_git_repo,
            dry_run=True,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            push=False,
        )

        # Verify version was calculated
        assert new_version == (0, 2, 0)

        # Verify files weren't modified
        assert (temp_git_repo / "VERSION").read_text() == original_version
        assert (temp_git_repo / "CHANGELOG.md").read_text() == original_changelog

    def test_bump_patch_version(self, temp_git_repo):
        """Test patch version bump."""
        # Add a patch commit
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: bug"], cwd=temp_git_repo, check=True, capture_output=True)

        # Run bump
        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            push=False,
        )

        assert new_version == (0, 1, 1)
        assert (temp_git_repo / "VERSION").read_text().strip() == "0.1.1"

        changelog = (temp_git_repo / "CHANGELOG.md").read_text()
        assert "v0.1.1" in changelog
        assert "fix: bug" in changelog

    def test_bump_minor_version(self, temp_git_repo):
        """Test minor version bump."""
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: new feature"], cwd=temp_git_repo, check=True, capture_output=True
        )

        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            push=False,
        )

        assert new_version == (0, 2, 0)
        assert (temp_git_repo / "VERSION").read_text().strip() == "0.2.0"

    def test_bump_major_version(self, temp_git_repo):
        """Test major version bump."""
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "breaking: API change"], cwd=temp_git_repo, check=True, capture_output=True
        )

        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            push=False,
        )

        assert new_version == (1, 0, 0)
        assert (temp_git_repo / "VERSION").read_text().strip() == "1.0.0"

    def test_update_version_in_bumps_every_occurrence(self, temp_git_repo):
        """Every line an `update_version_in` pattern matches is bumped, not just the first - the
        ForkUnion README case where the dependency is shown several times and one snippet was left
        pinning a stale version."""
        readme = temp_git_repo / "README.md"
        readme.write_text(
            'dep = "0.1.0"\n'
            'dep = { version = "0.1.0", features = ["portable"] }\n'
            'dep = { version = "0.1.0", features = ["numa"] }\n'
        )
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: bug"], cwd=temp_git_repo, check=True, capture_output=True)

        bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            update_version_in=[(str(readme), r'^dep = \{ version = "(\d+\.\d+\.\d+)"')],
            push=False,
        )

        content = readme.read_text()
        assert content.count('{ version = "0.1.1"') == 2  # both table-form lines moved together
        assert '{ version = "0.1.0"' not in content        # neither left pinning the stale version
        assert 'dep = "0.1.0"' in content                  # the bare-string line the pattern skips is untouched

    def test_bump_priority_major_over_minor(self, temp_git_repo):
        """Test that major takes priority when multiple commit types exist."""
        (temp_git_repo / "file1.txt").write_text("content1")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: new feature"], cwd=temp_git_repo, check=True, capture_output=True
        )

        (temp_git_repo / "file2.txt").write_text("content2")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "breaking: API change"], cwd=temp_git_repo, check=True, capture_output=True
        )

        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            push=False,
        )

        # Should bump major, not minor
        assert new_version == (1, 0, 0)

    def test_bump_with_update_version_in(self, temp_git_repo):
        """Test updating version in additional files."""
        # Create a package.json
        package_json = temp_git_repo / "package.json"
        package_json.write_text('{\n  "version": "0.1.0"\n}\n')

        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: bug"], cwd=temp_git_repo, check=True, capture_output=True)

        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            update_version_in=[(package_json, r'"version": "(.*)"')],
            push=False,
        )

        assert new_version == (0, 1, 1)
        assert '"version": "0.1.1"' in package_json.read_text()

    def test_bump_no_new_commits_raises_error(self, temp_git_repo):
        """Test that no new commits raises appropriate error."""
        with pytest.raises(NoNewCommitsError):
            bump(
                path=temp_git_repo,
                dry_run=False,
                verbose=False,
                version_file=temp_git_repo / "VERSION",
                changelog_file=temp_git_repo / "CHANGELOG.md",
                push=False,
            )

    def test_bump_custom_verbs(self, temp_git_repo):
        """Test custom verb configuration."""
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "update: something"], cwd=temp_git_repo, check=True, capture_output=True
        )

        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            minor_verbs=["update", "add"],
            version_file=temp_git_repo / "VERSION",
            changelog_file=temp_git_repo / "CHANGELOG.md",
            push=False,
        )

        assert new_version == (0, 2, 0)

    def test_bump_unrecognized_commit_fails(self, temp_git_repo):
        """Test that commits not matching any verb category fail."""
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "random: unrecognized commit"], cwd=temp_git_repo, check=True, capture_output=True
        )

        with pytest.raises(AssertionError, match="No commit categories found"):
            bump(
                path=temp_git_repo,
                dry_run=False,
                verbose=False,
                version_file=temp_git_repo / "VERSION",
                changelog_file=temp_git_repo / "CHANGELOG.md",
                push=False,
            )


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_bump_without_version_file(self, temp_git_repo):
        """Test bumping without updating version file."""
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: bug"], cwd=temp_git_repo, check=True, capture_output=True)

        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=None,  # No version file
            changelog_file=temp_git_repo / "CHANGELOG.md",
            push=False,
        )

        assert new_version == (0, 1, 1)
        # Original version file should be unchanged
        assert (temp_git_repo / "VERSION").read_text().strip() == "0.1.0"

    def test_bump_without_changelog(self, temp_git_repo):
        """Test bumping without updating changelog."""
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: bug"], cwd=temp_git_repo, check=True, capture_output=True)

        original_changelog = (temp_git_repo / "CHANGELOG.md").read_text()

        new_version = bump(
            path=temp_git_repo,
            dry_run=False,
            verbose=False,
            version_file=temp_git_repo / "VERSION",
            changelog_file=None,  # No changelog
            push=False,
        )

        assert new_version == (0, 1, 1)
        # Changelog should be unchanged
        assert (temp_git_repo / "CHANGELOG.md").read_text() == original_changelog

    def test_bump_not_a_git_repo(self, tmp_path):
        """Test that non-git directory raises error."""
        with pytest.raises(AssertionError, match="Not a Git repository"):
            bump(
                path=tmp_path,
                dry_run=False,
                verbose=False,
                push=False,
            )

    def test_bump_no_tags(self, tmp_path):
        """Test repo without any tags raises error."""
        # Create git repo without tags
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)

        (tmp_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: bug"], cwd=tmp_path, check=True, capture_output=True)

        with pytest.raises(AssertionError, match="No tags found"):
            bump(
                path=tmp_path,
                dry_run=False,
                verbose=False,
                push=False,
            )


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
