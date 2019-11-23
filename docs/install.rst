Installation
============

You can install via `pip <https://pypi.org/project/pip/>`_:

.. code-block::

    pip install recipemd


.. _install_completions:

Install completions
-------------------

Completion installation depends on your shell. Read the `argcomplete documentation <https://github.com/kislyuk/argcomplete>`_ for more detail.

Bash
~~~~

.. code-block:: shell

   activate-global-python-argcomplete

Zsh
~~~

.. code-block:: shell

   autoload -U bashcompinit
   bashcompinit
   eval "$(register-python-argcomplete recipemd)"

Tcsh
~~~~

.. code-block:: shell

   eval `register-python-argcomplete --shell tcsh recipemd`

Fish
~~~~

.. code-block:: none

   register-python-argcomplete --shell fish recipemd > ~/.config/fish/completions/recipemd.fish
