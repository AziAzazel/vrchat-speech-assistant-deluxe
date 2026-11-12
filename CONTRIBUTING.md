# Contributing

Discuss the change you wish to make via a GitHub issue with appropriate label(s).
Then, if you want to contribute to this project:

- Fork the repository.
- Make a new branch from `master`.
- Comment your code, follow our docstring style (numpy), and documentation if needed.
- Every commit message must have one of the prefixes in the table below.
- Test your code as much as possible.
- Create a pull request to `master`.
- Thank your for your contribution :)

## Commit

Following [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

| **Type**             | Description                                                                                                                               |
|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| **build:**           | changes that affect the build system or external dependencies (npm, make ...)                                                             |
| **ci:**              | changes to integration or configuration files and scripts (Travis, Ansible, BrowserStack ...)                                             |
| **feat:**            | addition of a new feature                                                                                                                 |
| **fix:**             | bug fix                                                                                                                                   |
| **perf:**            | performance improvement                                                                                                                   |
| **refactor:**        | modification that does not bring new functionality or performance improvement                                                             |
| **style:**           | change that does not bring any functional or semantic alteration (indentation, formatting, addition of space, renaming of a variable ...) |
| **docs:**            | writing or updating documentation                                                                                                         |
| **test:**            | addition or modification of tests                                                                                                         |
| **BREAKING CHANGE:** | major changes.                                                                                                                            |

## Coding style

### Pylint and Black formatting

Please review your python code performance with pylint.
The active Windows/test/release workflow is `.github/workflows/windows-release.yml`.
Run `PYTHONPATH=src python scripts/run_tests_ci.py` locally. Release tags must match
`src/vrchat_speech_assistant/_version.py`; there is no GitLab semantic-release pipeline.
Format your code using Black.

### Pydocstyle

In order to auto generate a wiki page using python sphinx follow the docstring style as below:

#### One line docstring

```python
def my_function():
    """Make something for my_function."""
    pass
```

With a capital letter, imperative, and a dot at the end.

#### Multi line docstring

```python
def my_function(arg):
    """Make something for my_function.

    Parameters
    ----------
    arg : type
     Description of parameter `arg`.

    Returns
    -------
    type
     Description of returned object.
    """


return
```

With a capital letter, imperative, and a dot at the end. One blank line between short description and
Parameters.

## Release process

- The provided GitLab pipeline auto release every push with the prefix `feat, fix, perf` commit.
- It will also generate a release changelog and tags based on the commit.
- Branches are continuously checked out from `main`  and then merged.
- Releases are tagged on `main`.
