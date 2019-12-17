# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import inspect
import os
import sys
from os.path import relpath, dirname
from pprint import pprint

import recipemd

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../recipemd'))


# -- Project information -----------------------------------------------------

project = 'RecipeMD'
copyright = '2019, Tilman Stehr and contributors'
author = 'Tilman Stehr and contributors'

# The full version, including alpha/beta/rc tags
release = recipemd.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.linkcode",
    'sphinx.ext.githubpages',
    'm2r',
    'sphinxcontrib.fulltoc',
    'sphinxcontrib.autoprogram',
    'sphinx_autodoc_typehints',
    'sphinxcontrib.apidoc',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for extensions -------------------------------------------------

# autodoc settings
autodoc_inherit_docstrings = True
#autodoc_member_order = 'bysource'
autodoc_default_options = {
    'exclude-members': 'schema,from_dict,to_dict',
}

# autodoc_typehings settings
always_document_param_types = True

# apidoc settings
os.environ['SPHINX_APIDOC_OPTIONS'] = 'members,undoc-members,show-inheritance'
apidoc_module_dir = '../recipemd'
apidoc_output_dir = '_apidoc'
apidoc_separate_modules = True
apidoc_toc_file = False
apidoc_module_first = True


# linkcode, based on numpy source (https://github.com/numpy/numpy/blob/master/doc/source/conf.py#L313)
def linkcode_resolve(domain, info):
    """
    Determine the URL corresponding to Python object
    """
    if domain != 'py':
        return None

    modname = info['module']
    fullname = info['fullname']

    submod = sys.modules.get(modname)
    if submod is None:
        return None

    obj = submod
    for part in fullname.split('.'):
        try:
            obj = getattr(obj, part)
        except Exception:
            return None

    # strip decorators, which would resolve to the source of the decorator
    # possibly an upstream bug in getsourcefile, bpo-1764286
    try:
        unwrap = inspect.unwrap
    except AttributeError:
        pass
    else:
        obj = unwrap(obj)

    try:
        fn = inspect.getsourcefile(obj)
    except Exception:
        fn = None
    if not fn:
        return None

    try:
        source, lineno = inspect.getsourcelines(obj)
    except Exception:
        lineno = None

    if lineno:
        linespec = "#L%d-L%d" % (lineno, lineno + len(source) - 1)
    else:
        linespec = ""

    module_folder = dirname(recipemd.__file__)
    if os.path.commonpath([module_folder, fn]) != module_folder:
        return None
    fn = relpath(fn, start=module_folder)

    # get branch (set by github when running in action, else by the makefile)
    try:
        branch = os.environ['GITHUB_REF'].split('/')[-1]
    except:
        branch = "master"

    return f"https://github.com/tstehr/RecipeMD/blob/{branch}/recipemd/{fn}{linespec}"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'alabaster'

# add edit_on_github
html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
        "edit_on_github.html",
    ]
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static', '../logo']

html_favicon = '_static/favicon.ico'

# needed to create CNAME file
html_baseurl = 'https://recipemd.org'


# -- Alabaster -------------------------------------------------

html_theme_options = {
    'logo': 'recipemd-mark.svg',
    'logo_name': True,
    'logo_text_align': 'center',
    'fixed_sidebar': False,
    'github_user': 'tstehr',
    'github_repo': 'recipemd',
    'github_banner': True,
    'github_button': False,
    'github_type': 'star',
}

# -- Edit on Github -------------------------------------------------
html_context = {
    # The path (relative to root) for your documentation
    "doc_path": "docs",
}