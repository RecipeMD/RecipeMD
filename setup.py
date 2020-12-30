import setuptools
from recipemd import __version__

tests_require = [
    'pytest==5.3.1',
    'pytest-cov==2.8.1',
    'tox==3.20.1',
]

docs_require = [
    'Sphinx==2.2.2',
    'm2r==0.2.1',
    'sphinxcontrib.fulltoc==1.2.0',
    'sphinxcontrib.autoprogram==0.1.5',
    'sphinx_autodoc_typehints==1.10.3',
    'sphinxcontrib.apidoc==0.3.0',
    'sphinx-autobuild==0.7.1'
]

release_requires = [
    'twine==3.1.1',
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
        'dataclasses-json>=0.5.2,<0.6.0',
        'yarl~=1.3.0',
        # commonmarkextension has to be vendorized due to #28. This can be removed once GovReady/CommonMark-py-Extensions#5  or we
        # remove or dependency on commonmarkextensions altogether
        # 'commonmarkextensions==0.0.5',
        'commonmark>=0.9.1,<1.0.0',
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
        'Source': 'https://github.com/tstehr/recipemd',
    },
)
