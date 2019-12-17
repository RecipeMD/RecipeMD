.. recipemd documentation master file, created by
   sphinx-quickstart on Tue Oct  1 00:16:36 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

RecipeMD
========

A :doc:`standard format <specification>` for recipes as `Markdown <https://commonmark.org>`_ files and a
:doc:`python reference implementation <reference_implementation>`. The reference implementation can be used as a
:doc:`CLI program <cli>` and as a :doc:`python library <_apidoc/recipemd>`.

Quick Start
-----------

1. Install the tool: ``pip install recipemd`` (optionally you can also :ref:`install shell completions<install_completions>`)
2. Look at some `example recipes <https://github.com/tstehr/RecipeMD/tree/master/examples>`_ or start with a
   `recipe template <https://github.com/tstehr/RecipeMD/tree/master/examples/template.md>`_ to create your own recipes
3. Learn how to use the CLI tool with some :ref:`example calls <cli_examples>`

Specification
-------------

We provide a  :doc:`specification <specification>` for RecipeMD so other tools can use the format. The specification
also comes with a set of `testcases <https://github.com/tstehr/RecipeMD/tree/master/testcases>`_.

Resources
---------

You can use `recipemd-extract <https://github.com/AberDerBart/recipemd-extract>`_ to fetch and extract recipes from the web. We also maintain a :doc:`list of recommended tools <recommended_tools>` that work nicely with RecipeMD recipes.

Some RecipeMD repositories:

* `AberDerBart <https://github.com/AberDerBart/recipes>`_
* `dadada <https://github.com/dadada/recipes>`_
* `dasnessie <https://github.com/dasnessie/recipes>`_
* `fscholdei <https://github.com/fscholdei/recipes>`_
* `mist <https://github.com/mist/recipes>`_
* `p3tr0sh <https://github.com/p3tr0sh/recipe>`_
* `sonea-pm8 <https://github.com/sonea-pm8/recipes>`_
* `tstehr <https://github.com/tstehr/recipes>`_


License
-------

The specification and the reference implementation are licensed under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation, either version 3 of the License, or any later version.

.. toctree::
   :hidden:

   Home <self>
   Specification <specification>
   Python Implementation <reference_implementation>
   Recommended Tools <recommended_tools>


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
