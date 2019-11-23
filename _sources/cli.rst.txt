CLI
===

The package :mod:`recipemd` provides two CLI applications:

* :ref:`cli_recipemd` performs actions with a single recipe in RecipeMD format.
* :ref:`cli_recipemd_find` performs actions on a folder of RecipeMD recipes.

.. _cli_examples:

Usage Examples
--------------

Display and validate a recipe:

.. code-block:: shell

   recipemd <path/to/recipe.md>

Get recipe title:

.. code-block:: shell

   recipemd <path/to/recipe.md> -t

Get recipe ingredients, e.g. to pipe to `shoppinglist-cli <https://github.com/AberDerBart/shoppinglist-cli>`_\ :

.. code-block:: shell

   recipemd <path/to/recipe.md> -i

Multiply recipe by a factor:

.. code-block:: shell

   recipemd <path/to/recipe.md> -m 5.5

Scale recipe for a given yield (e.g. number of servings, volume, mass, amount):

.. code-block:: shell

   recipemd <path/to/recipe.md> -y "10 servings"

Get all tags of all recipes in the current folder:

.. code-block:: shell

   recipemd-find tags

Get recipes by tag:

.. code-block:: shell

   recipemd-find -e "tag:cheese or tag:summer" recipes


Command reference
-----------------

.. _cli_recipemd:

.. autoprogram:: recipemd.cli.main:parser
   :prog: recipemd

.. _cli_recipemd_find:

.. autoprogram:: recipemd.cli.find:parser
   :prog: recipemd-find
