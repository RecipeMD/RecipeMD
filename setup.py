import setuptools
from recipemd import __version__

tests_require = [
    'pytest',
    'pytest-cov',
]

docs_require = [
    'Sphinx',
    'm2r',
    'sphinxcontrib.fulltoc',
    'sphinxcontrib.autoprogram',
    'sphinx_autodoc_typehints',
    'sphinxcontrib.apidoc',
    'sphinx-autobuild'
]

release_requires = [
    'twine',
]

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="recipemd",
    version=__version__,
    author="Tilman Stehr",
    author_email="tilman@tilman.ninja",
    description="Markdown recipe manager, reference implementation of RecipeMD",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://recipemd.org",
    packages=setuptools.find_packages(),
    python_requires='>=3.7,<4',
    install_requires=[
        'dataclasses-json>=0.3.0,<0.4.0',
        'yarl~=1.3.0',
        # has broken before and is still unstable, so pin exact version
        'commonmarkextensions==0.0.5',
        # commonmark version needs to match the version required by commonmarkextensions
        'commonmark>=0.8.0,<=0.8.1',
        'argcomplete~=1.10.0',
        'pyparsing~=2.4.2',
    ],
    extras_require={
        'tests': tests_require,
        'docs': docs_require,
        'release': release_requires,
        'dev': tests_require+docs_require+release_requires
    },
    entry_points={
        'console_scripts': [
            'recipemd=recipemd.cli.main:main',
            'recipemd-find=recipemd.cli.find:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        "Operating System :: OS Independent",
    ],
)
