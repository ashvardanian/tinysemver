# Tiny Sem Ver

Minimalistic [Semantic Versioning](https://semver.org/) package for projects following [Conventional Commits](https://www.conventionalcommits.org/) in a single short Python file.
In plain English, if your commit messages look like `feat: add new feature` or `fix: bugfix`, this package will automate releasing new "GIT tags" based on the commit messages.
Here is how to integrate it into your project CI:

```sh
$ pip install tinysemver
$ tinysemver --dry-run --verbose
> Current version: 1.2.2
> Next version: 1.3.0
```

The `--dry-run` flag will only print the next version without changing any files.
Great for pre-release CI pipelines.
If you need more control over the default specification, here are more options you can run against the files in this repository:

```sh
# This won't push
$ tinysemver --verbose \
    --major-verbs 'breaking,break,major' \
    --minor-verbs 'feature,minor,add,new' \
    --patch-verbs 'fix,patch,bug,improve,docs' \
    --changelog-file 'CHANGELOG.md' \
    --version-file 'VERSION' \
    --update-version-in 'pyproject.toml' '^version = "(\d+\.\d+\.\d+)"' \
    --github-repository 'ashvardanian/tinysemver'
# Revert to the previous commit
$ git reset --soft HEAD~1                         
```

It's recommended to use strict version matching with `\d+\.\d+\.\d+` instead of a generic wildcard like `.*`, but both would work.
Here is an example of passing even more parameters for a project like `stringzilla`:

```sh
$ tinysemver --verbose \
    --major-verbs 'breaking,break,major' \
    --minor-verbs 'feature,minor,add,new' \
    --patch-verbs 'fix,patch,bug,improve,docs' \
    --changelog-file 'CHANGELOG.md' \
    --version-file 'VERSION' \
    --update-version-in 'pyproject.toml' '^version = "(\d+\.\d+\.\d+)"' \
    --update-version-in 'package.json' '"version": "(.*)"' \
    --update-version-in 'CITATION.cff' '^version: (.*)' \
    --update-major-version-in 'include/stringzilla/stringzilla.h' '^#define STRINGZILLA_VERSION_MAJOR (.*)' \
    --update-minor-version-in 'include/stringzilla/stringzilla.h' '^#define STRINGZILLA_VERSION_MINOR (.*)' \
    --update-patch-version-in 'include/stringzilla/stringzilla.h' '^#define STRINGZILLA_VERSION_PATCH (.*)' \
    --github-repository 'ashvardanian/stringzilla' \
    --push
> Current version: 1.2.2
> ? Commits since last tag: 3                   # Only in verbose mode
> # 5579972: Improve: Log file patches          # Only in verbose mode
> # de645ea: Improve: Grouping CHANGELOG        # Only in verbose mode
> Next version: 1.3.0
> Will update file: VERSION:0
> - 1.2.2                                       # Only in verbose mode
> + 1.3.0                                       # Only in verbose mode
> Will update file: package.json:5
> - "version": "1.2.2"                          # Only in verbose mode
> + "version": "1.3.0"                          # Only in verbose mode
> Will update file: pyproject.toml:7
> - version = "1.2.2"                           # Only in verbose mode
> + version = "1.3.0"                           # Only in verbose mode
> Will update file: CITATION.cff:7
> - version: 1.2.2                              # Only in verbose mode
> + version: 1.3.0                              # Only in verbose mode
> Appending to changelog file: CHANGELOG.md
> = skipping 250 lines                          # Only in verbose mode
> + addng 30 lines                              # Only in verbose mode
```

Alternatively, you can just ask for `--help`:

```sh
$ tinysemver --help
```

## GitHub CI Action

TinySemVer can be easily integrated into your GitHub Actions CI pipeline.
Assuming the differences between YAML and shell notation, some arguments are passed in a different form, like `--update-version-in`.

```yaml
name: Release

on:
  push:
    branches: [ main ]

jobs:
  semver:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        persist-credentials: false # Only if main branch if protected

    - name: Run TinySemVer
      uses: ashvardanian/tinysemver@v2.0.1
      with:
        major-verbs: 'breaking,break,major'
        minor-verbs: 'feature,minor,add,new'
        patch-verbs: 'fix,patch,bug,improve,docs'
        changelog-file: 'CHANGELOG.md'
        version-file: 'VERSION'
        update-version-in: 'pyproject.toml:version = "(.*)"' # Use colon instead of space
        git-user-name: 'GitHub Actions'
        git-user-email: 'actions@github.com'
        github-token: ${{ secrets.GITHUB_TOKEN }}
        verbose: 'true'
        push: 'true'
        create-release: 'true'
        dry-run: 'false'

  publish:
    needs: semver # Depends on the previous job
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          ref: main # Take the most recent updated version
```

Every team has a different workflow, but a common pattern is to have one `release.yml` for the `main` branch and another `prerelease.yml` for the `main-dev` branch used as a staging area.
The latter would run with `dry-run: 'true'` and `push: 'false'` to prevent pushing changes to the main repository.
The `create-release` flag is optional and can be set to `false` if you don't want to create a new release on GitHub.
If you need to update the version in multiple files, pass a multiline string with the `|` operator:

```yaml
        update-version-in: |
          pyproject.toml:version = "(.*)"
          package.json:"version": "(.*)"
          CITATION.cff:version: "(.*)"
```

For examples, consider checking StringZilla, USearch, and other libraries using TinySemVer.

### Security Considerations

If your default branch is protected with a "pull request before merging" rule:

1. A repository-scoped Personal Access Token (PAT) is required to push to the branch.
2. Set `persist-credentials: false` in the `actions/checkout` step.

Also keep in mind:

- The default `GITHUB_TOKEN` cannot be used with protected branches.
- Using a PAT instead of `GITHUB_TOKEN` poses security risks:
  - Workflows from any branch can access secret variables.
  - This could allow non-protected branches to use elevated permissions.
- Mitigation:
  - Use a fine-grained PAT with minimal necessary permissions.
  - Prefer the `pull_request` workflow trigger, which limits permissions.
  - Be cautious: users with write access could still potentially exploit workflows to expose the PAT.

> [!TIP]
> Always follow the principle of least privilege when setting up tokens and permissions.

For more information on CI configurations and pushing changes in GitHub Actions, see the [semantic-release GitHub Actions guide](https://github.com/semantic-release/semantic-release/blob/master/docs/recipes/ci-configurations/github-actions.md#pushing-packagejson-changes-to-a-master-branch).

## Why?

In the past I was using [semantic-release](https://github.com/semantic-release/semantic-release) for my 10+ projects.
At some point, a breaking change in the dependencies broke all my projects CI pipelines for a month, affecting dozens of tech companies using those libraries.
I felt miserable trying to trace the issue and reluctant to go through 363K lines of low-quality JavaScript code to find the bug.
Yes, it's 363K lines of code:

```sh
$ .../node_modules$ cloc .
   10751 text files.
    7809 unique files.                                          
    3498 files ignored.

github.com/AlDanial/cloc v 1.90  T=2.96 s (2450.6 files/s, 300331.1 lines/s)
--------------------------------------------------------------------------------
Language                      files          blank        comment           code
--------------------------------------------------------------------------------
JavaScript                     4902          48080          81205         363424
TypeScript                      732           7008          73034          79367
Markdown                        633          26835              0          66869
JSON                            599             58              0          64808
HTML                             86           1821              0          25365
Python                           57           4985           9193          23704
CSS                              97           1360            739           6346
YAML                             73             79             51           1198
CoffeeScript                     18            193             16           1122
EJS                               1             67              0            521
Lua                              22             95             29            434
Handlebars                       11             30              0            188
C#                                1             55              9            186
Bourne Shell                      7             30             11            168
Bourne Again Shell                2             22             24             84
TOML                              1              8             31             80
make                              3             17             11             57
PowerShell                        2             12              4             48
DOS Batch                         5              9              0             42
Fish Shell                        1              5             14             21
C++                               2             12             19             20
Nix                               1              1              0             19
--------------------------------------------------------------------------------
SUM:                           7256          90782         164390         634071
--------------------------------------------------------------------------------
```

Here is the `cloc` output for `tinysemver`:

```sh
$ tinysemver$ cloc .
      11 text files.
       6 unique files.                              
       6 files ignored.

github.com/AlDanial/cloc v 1.96  T=0.01 s (660.7 files/s, 44267.6 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Python                           1             45             27            194
Markdown                         1             13              0             71
TOML                             1              6              2             33
Text                             3              1              0             10
-------------------------------------------------------------------------------
SUM:                             6             65             29            308
-------------------------------------------------------------------------------
```

## What's Missing?

- Optional commit scopes, like `feat(scope): add new feature`. Doesn't make sense for most projects.
- Pre-release versions, like `1.2.3-alpha.1`. Not needed for most projects.
- GenAI.

For reference, according to SemVer 2.0, all [following versions](https://regex101.com/r/Ly7O1x/3/) are valid:

```
1.1.2-prerelease+meta
1.1.2+meta
1.1.2+meta-valid
1.0.0-alpha
1.0.0-beta
1.0.0-alpha.beta.1
1.0.0-alpha.1
1.0.0-alpha0.valid
1.0.0-alpha.0valid
1.0.0-alpha-a.b-c-somethinglong+build.1-aef.1-its-okay
1.0.0-rc.1+build.1
2.0.0-rc.1+build.123
1.2.3-beta
10.2.3-DEV-SNAPSHOT
1.2.3-SNAPSHOT-123
2.0.0+build.1848
2.0.1-alpha.1227
1.0.0-alpha+beta
1.2.3----RC-SNAPSHOT.12.9.1--.12+788
1.2.3----R-S.12.9.1--.12+meta
1.2.3----RC-SNAPSHOT.12.9.1--.12
1.0.0+0.build.1-rc.10000aaa-kk-0.1
1.0.0-0A.is.legal
```

Probably very useful for 2-3 projects, I didn't need to support any of them yet.

## Examples

Assembling RegEx queries can be hard.
Luckily, there aren't too many files to update in most projects.
Below is an example of a pipeline for the USearch project, that has bindings to 10 programming languages.
Feel free to add other sources and examples.

```sh
$ mkdir -p example

$ wget https://github.com/unum-cloud/usearch/raw/main/VERSION -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/CHANGELOG.md -P example/ # Missing
$ wget https://github.com/unum-cloud/usearch/raw/main/CITATION.cff -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/CMakeLists.txt -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/Cargo.toml -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/package.json -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/conanfile.py -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/README.md -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/wasmer.toml -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/csharp/nuget/nuget-package.props -P example/
$ wget https://github.com/unum-cloud/usearch/raw/main/include/usearch/index.hpp -P example/

# You can match the semantic version part with a generic wildcard like: .*
# But it's recommended to stick to a stricter format: \d+\.\d+\.\d+
$ tinysemver --dry-run --verbose \
    --major-verbs 'breaking,break,major' \
    --minor-verbs 'feature,minor,add,new' \
    --patch-verbs 'fix,patch,bug,improve,docs' \
    --version-file 'example/VERSION' \
    --changelog-file 'example/CHANGELOG.md' \
    --update-version-in 'example/CITATION.cff' '^version: (\d+\.\d+\.\d+)' \
    --update-version-in 'example/CMakeLists.txt' '\sVERSION (\d+\.\d+\.\d+)' \
    --update-version-in 'example/Cargo.toml' '^version = "(\d+\.\d+\.\d+)"' \
    --update-version-in 'example/package.json' '"version": "(\d+\.\d+\.\d+)"' \
    --update-version-in 'example/conanfile.py' '\sversion = "(\d+\.\d+\.\d+)"' \
    --update-version-in 'example/README.md' '^version = \{(\d+\.\d+\.\d+)\}' \
    --update-version-in 'example/wasmer.toml' '^version = "(\d+\.\d+\.\d+)"' \
    --update-version-in 'example/nuget-package.props' '(\d+\.\d+\.\d+)\<\/Version\>' \
    --update-major-version-in 'example/index.hpp' '^#define USEARCH_VERSION_MAJOR (\d+)' \
    --update-minor-version-in 'example/index.hpp' '^#define USEARCH_VERSION_MINOR (\d+)' \
    --update-patch-version-in 'example/index.hpp' '^#define USEARCH_VERSION_PATCH (\d+)' \
    --path .
```

## Contributing

Feel free to open an issue or a pull request.
If you need to bump the version of `tinysemver` itself:

```sh
tinysemver --verbose \
    --version-file 'VERSION' \
    --changelog-file 'CHANGELOG.md' \
    --update-version-in 'pyproject.toml' 'version = "(.*)"' \
    --github-repository 'ashvardanian/tinysemver' --push
```
