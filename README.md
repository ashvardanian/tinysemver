# Tiny Sem Ver

Minimalistic [Semantic Versioning](https://semver.org/) package for projects following [Conventional Commits](https://www.conventionalcommits.org/) in a single short Python file.
In English, if your commit messages look like `feat: add new feature` or `fix: bugfix`, this package will automate releasing new "GIT tags" based on the commit messages.
Here is how to integrate it into your project CI:

```sh
$ pip install tinysemver
$ tinysemver --dry-run --verbose
> Current version: 1.2.2
> Next version: 1.3.0
```

The `--dry-run` flag will only print the next version without changing any files.
Great for pre-release CI pipelines.
If you need more control over the default specification, here is a list of all available options:

```sh
$ tinysemver --dry-run --verbose \
    --major-verbs 'breaking,break,major' \ 
    --minor-verbs 'feature,minor,add,new' \
    --patch-verbs 'fix,patch,bug,improve' \
    --changelog-file 'CHANGELOG.md' \
    --version-file 'VERSION' \
    --patch-file '"version": "(.*)"' 'package.json' \
    --patch-file '^version: (.*)' 'CITATION.cff'
> Current version: 1.2.2
> Next version: 1.3.0
> ✓ Found changelog file: CHANGELOG.md
> ✓ Found version file: VERSION
> ✓ Found patch file: package.json
>   Will update line 5 with "1.2.2" to:
>   "version": "1.3.0",
> ✓ Found patch file: CITATION.cff
>   Will update line 7 with "1.2.2" to:
>   version: 1.3.0
```

Alternatively, you can just ask for `--help`:

```sh
$ tinysemver --help
```

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
