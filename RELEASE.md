# Creating a New Release 

1. Update the version number in `__init__.py` according to [semantic
   versioning](https://semver.org) rules.

2. Update the changelog (`CHANGELOG.md`) for the new version.

3. Run tests with `tox`

4. Create release commit, tag with `v<newversion>`

5. Create the release files with `rm -rf dist; python setup.py sdist bdist_wheel`

6. Upload release to pypi with `twine upload --username <username> dist/*`

6. Create a new release [on Github](https://github.com/tstehr/RecipeMD/releases/new). Attach the release files, and put the changelog for the new version in the description.