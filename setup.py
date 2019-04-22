import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="recipemd",
    version="2.2.0",
    author="Tilman Stehr",
    author_email="tilman@tilman.ninja",
    description="Reference implementation of recipemd",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tstehr/recipemd",
    packages=setuptools.find_packages(),
    python_requires='>=3.7,<4',
    install_requires=[
        'CommonMark==0.7.5',
        'commonmarkextensions==0.0.3'
    ],
    entry_points={
        'console_scripts': [
            'recipemd=recipemd.cli:main',
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