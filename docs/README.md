# Generating Local Documentation with Sphinx-Automodapi

Sphinx is a popular tool for creating technical documentation using reStructuredText and its extensions.
When working on our Python project, we use `sphinx-automodapi` to easily generate API documentation based on your code. This guide explains how to set up and run the process locally for testing purposes.

### Build outputs and release pipeline

Keep documentation sources in `docs/source`. The generated `docs/build` directory
is ignored and can be regenerated locally; stale HTML and Sphinx caches are not
checked into the repository. Windows executables are built and verified by
[GitHub Actions](../.github/workflows/windows-release.yml).

### Prerequisite
Install the current package with the "documentation" optional dependency using `pip install .[documentation]`.

## Generating Automatic API Documentation
1. Navigate to the `docs` directory, which by default is the root folder for Sphinx documentation generation.
2. Run `python docs\automodapi.py awesome_project docs`, replacing "awesome_project" with the current module source file in your project structure. If you use the "src" workflow folder, replace it with `"src/awesome_project"` or similar. This command generates all required .rst files for API documentation based on the package's structure.
3. The `docs/source` directory now contains .rst files for your project's API documentation.

## Manual Documentation Addition

You can modify the `doc/source/index.rst` file or create additional manual .rst files in the `docs/source` folder to add usage instructions, tutorials, or other informational sections. Learn about creating Sphinx .rst files here: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html

## Build and Serve the Documentation Locally

1. Run `python -m sphinx -b html docs\source docs\build` from your project's root directory. This command builds the documentation, using the specified source folder (`.docs/source`) and destination build folder (`.docs/build`).
2. Check for potential errors or warnings in the Sphinx build output.
3. To open the generated documentation, navigate to `docs/build` and open `index.html` with your navigator.

Note: You can store images in `docs/source/_static/images`, while other media should go into the `docs/source/_static` folder if needed.
