import setuptools

from recipemd import __version__

tests_require = [
    'pytest==9.0.3',
    'pytest-cov==7.1.0',
    'tox==4.53.1',
    'jsonschema==4.23.0',
]

docs_require = [
    'Sphinx==8.2.3',
    'm2r2==0.3.4',
    'sphinxcontrib.autoprogram==0.1.9',
    'sphinx_autodoc_typehints==3.2.0',
    'sphinxcontrib.apidoc==0.6.0',
    'sphinx-autobuild==2024.10.3'
]

release_requires = [
    'twine==3.1.1',
    'wheel'
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
    python_requires='>=3.10,<4',
    install_requires=[
        'dataclasses-json>=0.5.2,<0.6.0',
        'yarl>=1.3.0,<2.0.0',
        'argcomplete>=1.10.0,<2.0.0',
        'pyparsing~=2.4.2',
        'markdown-it-py>=2.1.0,<3.0.0',
        'typing_extensions>=4.3.0,<5.0.0',
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
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        "Topic :: Text Processing :: Markup",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    ],
    project_urls={
        'Documentation': 'https://recipemd.org/reference_implementation.html',
        'Source': 'https://github.com/RecipeMD/RecipeMD',
    },
)
