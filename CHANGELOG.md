# TinySemVer Change Log

## June 2, 2024: v1.0.0

- Add: Initial implementation
- Add: `--update-version-in` support

## June 13, 2024: v1.1.0

### Minor

- Add: Flag for partial SemVer updates

### Patch

- Improve: Log file patches
- Improve: Grouping CHANGELOG
- Improve: `assert`-s instead of `print`-s
- Fix: Filtering empty lines from commit logs
- Fix: Entry-point resolution## June 13, 2024: v1.1.0

## June 13, 2024: v1.1.2

### Patch

- Fix: `create_commit` before `create_tag`

## June 13, 2024: v1.1.3

### Patch

- Improve: Push by default

## June 13, 2024: v1.2.0

### Minor

- Add: `--github-repository` for push

### Patch

- Fix: Extra space in command
- Make: Drop `setup.py`

## June 13, 2024: v1.2.1

### Patch

- Improve: Log after push

## June 13, 2024: v1.2.2

### Patch

- Fix: `push` URL resolution

## June 13, 2024: v1.2.3

### Patch

- Fix: Default `push` argument

## June 13, 2024: v1.2.4

### Patch

- Fix: Lowercase project name

## June 17, 2024: v1.2.6

### Patch

- Improve: List docs updates as patches
- Improve: Detect lacking capture groups
- Docs: Recommend `\d+.\d+.\d+.` wildcards

## June 17, 2024: v1.2.6

### Patch

- Improve: List docs updates as patches
- Improve: Detect lacking capture groups
- Docs: Recommend `\d+.\d+.\d+.` wildcards

## June 17, 2024: v1.2.6

### Patch

- Improve: List docs updates as patches
- Improve: Detect lacking capture groups
- Docs: Recommend `\d+.\d+.\d+.` wildcards

## June 17, 2024: v1.2.7

### Patch

- Improve: Push all tags

## June 17, 2024: v1.2.8

### Patch

- Improve: Rebase before push

## June 17, 2024: v1.2.9

### Patch

- Fix: Avoid rebase

## June 17, 2024: v1.2.10

### Patch

- Docs: Fix project name


## August 05, 2024: v1.3.0

### Minor

- feature: implement GitHub Action

### Patch

- Fix: Finalize the GitHub Action (#6)
- Fix: Replacing slices
- Fix: Lowercase name
- Docs: Links and instructions
- Fix: Remove repeated `pyproject.toml` lines
- Improve: Log failed push URL

## August 05, 2024: v1.3.1

### Patch

- Improve: Use `skip ci` to avoid recursive calls

## August 05, 2024: v1.3.2

### Patch

- Fix: Checkout from `main`

## August 05, 2024: v1.3.3

### Patch

- Improve: Trigger minor releases for docs
- Docs: Providing examples

## August 05, 2024: v1.4.0

### Minor

- Add: Pre-release dry run

## August 05, 2024: v1.4.1

### Patch

- Improve: add authors and icon to Action

## August 05, 2024: v2.0.0

### Major

- Break: Multi-line YAML arguments

## August 05, 2024: v2.0.1

### Patch

- Improve: Ignore subsequent colons

## August 14, 2024: v2.0.2

### Patch

- Docs: Describe arguments

## August 14, 2024: v2.0.3

### Patch

- Docs: Cleaner `README.md`
- Make: Bump Python CI version

## August 15, 2024: v2.0.4

### Patch

- Improve: Add bug report
- Fix: Put `tinysemver.py` into `.tar.gz`

## August 15, 2024: v2.0.5

### Patch

- Fix: Indicate a package with `__init__.py`

## August 15, 2024: v2.0.6

### Patch

- Make: Fix path to the local script
- Fix: Change entrypoint
- Make: Change directory structure

## August 18, 2024: v2.0.7

### Patch

- Improve: Exit with code `0`, if no commits are found
