Recommended Tools
=================

On this pages we summarize some tools that work nicely with RecipeMD recipes.

Pandoc
------

`Pandoc <https://pandoc.org>`_ is a tool that can be used to convert files between difference markup formats, for example from Markdown to lots of other formats.

Convert a recipe to pdf:

.. code-block:: shell

    recipemd <path/to/recipe.md> | pandoc --pdf-engine=xelatex  -V geometry:margin=2cm -V geometry:a4paper -o <path/to/recipe.pdf>

Convert a folder of recipes to pdfs:

.. code-block:: shell

    ls *.md | xargs -P10 -I{} bash -c 'pandoc --pdf-engine=xelatex  -V geometry:margin=2cm -V geometry:a4paper {} -o $(basename {} md)pdf'

Note that you can specify the `latex template <https://pandoc.org/MANUAL.html#templates>`_ used by pandoc to adopt the output to your taste.

GitLab Markdown Viewer
----------------------

`GitLab Markdown Viewer <https://addons.mozilla.org/en-US/firefox/addon/gitlab-markdown-viewer/>`_ is an add-on for Firefox that allows it to render Markdown recipe. This allows you to use Firefox to navigate your recipe collection.

Other Tools
-----------

If you use any other tools with RecipeMD recipes, we'd like to include them here. Please `send a pull request <https://github.com/tstehr/recipemd/edit/master/docs/recommended_tools.rst>`_ or `open an issue <https://github.com/tstehr/recipemd/issues>`_ to add to this page.